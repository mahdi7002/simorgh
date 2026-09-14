#!/usr/bin/env python3
"""Generate an SPDX 2.3 JSON SBOM from the installed Python environment.

This records the exact environment used by CI/release packaging. It is not a
substitute for legal review of datasets, models, or non-Python assets.
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="compliance/sbom.spdx.json")
    args = parser.parse_args()

    dists = sorted(metadata.distributions(), key=lambda d: (d.metadata.get("Name") or "").lower())
    packages = []
    by_name: dict[str, str] = {}
    for dist in dists:
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

    relationships = []
    for dist in dists:
        name = dist.metadata.get("Name")
        if not name:
            continue
        src = by_name.get(_norm_name(name))
        if not src:
            continue
        for requirement in dist.requires or []:
            dep = requirement.split(";", 1)[0].strip()
            dep_name = dep.split("[", 1)[0]
            for marker in ("<", ">", "=", "!", "~"):
                dep_name = dep_name.split(marker, 1)[0]
            dst = by_name.get(_norm_name(dep_name.strip()))
            if dst:
                relationships.append(
                    {
                        "spdxElementId": src,
                        "relationshipType": "DEPENDS_ON",
                        "relatedSpdxElement": dst,
                    }
                )

    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    nonce = hashlib.sha256(f"{created}:{platform.python_version()}".encode()).hexdigest()[:16]
    document = {
        "spdxVersion": SPDX_VERSION,
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "SIMORGH Python environment",
        "documentNamespace": DOCUMENT_NAMESPACE_BASE + nonce,
        "creationInfo": {
            "created": created,
            "creators": [CREATOR],
            "licenseListVersion": SPDX_LICENSE_LIST_VERSION,
        },
        "packages": packages,
        "relationships": relationships,
        "comment": "Generated from the exact installed Python environment. Review dataset/model licenses separately.",
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SBOM written: {output} ({len(packages)} packages, {len(relationships)} dependency links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
