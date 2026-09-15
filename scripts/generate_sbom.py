#!/usr/bin/env python3
"""Generate an SPDX 2.3 SBOM for the installed dependency closure.

The generator intentionally scopes the SBOM to packages named by the supplied
requirements files and their installed transitive dependencies. This avoids
mistaking unrelated packages preinstalled on a CI runner for SIMORGH
requirements. It is not a substitute for legal review of datasets, models, or
non-Python assets.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from packaging.requirements import Requirement

SPDX_VERSION = "SPDX-2.3"
SPDX_LICENSE_LIST_VERSION = "3.28.0"
CREATOR = "Tool: SIMORGH SBOM generator"
DOCUMENT_NAMESPACE_BASE = "https://github.com/mahdi7002/simorgh/sbom/"


def _license(dist: metadata.Distribution) -> str:
    """Prefer modern PEP 639 License-Expression metadata, then legacy fields."""
    expression = dist.metadata.get("License-Expression")
    if expression:
        return expression.strip()

    values = dist.metadata.get_all("Classifier") or []
    for value in values:
        if value.startswith("License ::"):
            return value.split("::", 2)[-1].strip()

    value = dist.metadata.get("License")
    return value.strip() if value else "NOASSERTION"


def _home(dist: metadata.Distribution) -> str:
    value = dist.metadata.get("Home-page")
    if value:
        return value
    for item in dist.metadata.get_all("Project-URL") or []:
        if "," in item:
            _, url = item.split(",", 1)
            parsed = urlparse(url.strip())
            if parsed.scheme:
                return url.strip()
    return "NOASSERTION"


def _spdx_id(name: str, version: str) -> str:
    safe = "".join(ch if ch.isalnum() else "-" for ch in f"{name}-{version}")
    return f"SPDXRef-Package-{safe}"


def _norm_name(value: str) -> str:
    return value.lower().replace("_", "-").replace(".", "-")


def _seed_names(requirement_files: list[Path]) -> set[str]:
    names: set[str] = set()
    for path in requirement_files:
        if not path.is_file():
            raise FileNotFoundError(path)
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            try:
                requirement = Requirement(line)
            except Exception:
                continue
            names.add(_norm_name(requirement.name))
    return names


def _dependency_closure(seed_names: set[str], distributions: dict[str, metadata.Distribution]) -> set[str]:
    selected = set(seed_names)
    queue = list(seed_names)
    while queue:
        name = queue.pop()
        dist = distributions.get(name)
        if dist is None:
            continue
        for raw_requirement in dist.requires or []:
            try:
                requirement = Requirement(raw_requirement)
            except Exception:
                continue
            try:
                if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                    continue
            except Exception:
                continue
            dep_name = _norm_name(requirement.name)
            if dep_name not in selected and dep_name in distributions:
                selected.add(dep_name)
                queue.append(dep_name)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--requirements",
        action="append",
        type=Path,
        required=True,
        help="requirements file to include; may be repeated",
    )
    parser.add_argument("--output", default="compliance/sbom.spdx.json")
    args = parser.parse_args()

    all_distributions = {
        _norm_name(dist.metadata.get("Name", "")): dist
        for dist in metadata.distributions()
        if dist.metadata.get("Name")
    }
    seed_names = _seed_names(args.requirements)
    selected_names = _dependency_closure(seed_names, all_distributions)

    packages = []
    by_name: dict[str, str] = {}
    selected_dists = [all_distributions[name] for name in selected_names]
    selected_dists.sort(key=lambda d: (d.metadata.get("Name") or "").lower())

    for dist in selected_dists:
        name = dist.metadata.get("Name")
        version = dist.version
        if not name:
            continue
        sid = _spdx_id(name, version)
        by_name[_norm_name(name)] = sid
        packages.append(
            {
                "SPDXID": sid,
                "name": name,
                "versionInfo": version,
                "downloadLocation": _home(dist),
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": _license(dist),
                "copyrightText": "NOASSERTION",
                "supplier": "NOASSERTION",
            }
        )

    relationships = set()
    for dist in selected_dists:
        name = dist.metadata.get("Name")
        if not name:
            continue
        src = by_name.get(_norm_name(name))
        if not src:
            continue
        for raw_requirement in dist.requires or []:
            try:
                requirement = Requirement(raw_requirement)
            except Exception:
                continue
            try:
                if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                    continue
            except Exception:
                continue
            dst = by_name.get(_norm_name(requirement.name))
            if dst:
                relationships.add((src, dst))

    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    nonce = hashlib.sha256(f"{created}:{platform.python_version()}".encode()).hexdigest()[:16]
    document = {
        "spdxVersion": SPDX_VERSION,
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "SIMORGH declared Python dependency closure",
        "documentNamespace": DOCUMENT_NAMESPACE_BASE + nonce,
        "creationInfo": {
            "created": created,
            "creators": [CREATOR],
            "licenseListVersion": SPDX_LICENSE_LIST_VERSION,
        },
        "packages": packages,
        "relationships": [
            {
                "spdxElementId": src,
                "relationshipType": "DEPENDS_ON",
                "relatedSpdxElement": dst,
            }
            for src, dst in sorted(relationships)
        ],
        "comment": "Generated from the installed closure of the explicitly supplied requirements files. Review dataset/model licenses separately.",
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SBOM written: {output} ({len(packages)} packages, {len(relationships)} dependency links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
