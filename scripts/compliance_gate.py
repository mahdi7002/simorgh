#!/usr/bin/env python3
"""Machine-checkable compliance/release gate for SIMORGH.

Default mode is evidence collection. ``--release`` is intentionally strict and
fails closed until rights, core third-party licensing, privacy documentation,
security invariants, SBOM evidence, and human signoff are all verified.
Optional integrations have their own feature-specific gate via
``--include-optional`` and must not be treated as shipped core dependencies
unless they are actually selected for a release.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / "LICENSE",
    ROOT / "SECURITY.md",
    ROOT / "docs" / "LEGAL_AND_COMPLIANCE.md",
    ROOT / "compliance" / "ASSET_RIGHTS.csv",
    ROOT / "compliance" / "THIRD_PARTY_LICENSES.csv",
    ROOT / "compliance" / "PRIVACY_DATA_MAP.md",
    ROOT / "compliance" / "GLOBAL_JURISDICTION_MATRIX.md",
    ROOT / "compliance" / "PROHIBITED_USE_POLICY.md",
    ROOT / "compliance" / "RISK_REGISTER.md",
    ROOT / "compliance" / "RELEASE_SIGNOFF.md",
]

RISKY_PATTERNS = {
    "hardcoded_auth_default": re.compile(r"SIMORGH_KEY\s*=\s*os\.environ\.get\([^\n]*,"),
    "shell_true": re.compile(r"shell\s*=\s*True"),
    "os_system": re.compile(r"\bos\.system\s*\("),
    "dynamic_exec": re.compile(r"\b(?:eval|exec)\s*\("),
    "legacy_secret": re.compile(r"simorgh[0-9]{3}|hf_demo_key"),
}

REQUIREMENT_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*(?:\[.*?\])?\s*(?:[<>=!~].*)?$")


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value.strip().lower())


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def rights_coverage(files: list[str]) -> tuple[list[str], list[str]]:
    rows = read_csv(ROOT / "compliance" / "ASSET_RIGHTS.csv")
    specs = [(str(row.get("path", "")).strip(), row) for row in rows if row.get("path")]
    assets = [p for p in files if p == "catalog.json" or p.startswith(("data/", "quran/", "music/"))]
    missing: list[str] = []
    unverified: list[str] = []
    for asset in assets:
        matches = [
            row for prefix, row in specs
            if prefix and (asset == prefix or (prefix.endswith("/") and asset.startswith(prefix)))
        ]
        if not matches:
            missing.append(asset)
            continue
        if not any(row.get("status", "").strip().upper() == "VERIFIED" for row in matches):
            unverified.append(asset)
    return missing, unverified


def declared_requirements(filename: str) -> set[str]:
    result: set[str] = set()
    path = ROOT / filename
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = REQUIREMENT_RE.match(line)
        if match:
            result.add(normalize_name(match.group(1)))
    return result


def third_party_state(include_optional: bool = False) -> list[str]:
    rows = read_csv(ROOT / "compliance" / "THIRD_PARTY_LICENSES.csv")
    indexed = {normalize_name(row.get("component", "")): row for row in rows if row.get("component")}
    required = declared_requirements("requirements.txt")
    if include_optional:
        required |= declared_requirements("requirements-optional.txt")
    missing: list[str] = []
    unverified: list[str] = []
    for component in sorted(required):
        row = indexed.get(component)
        if not row:
            missing.append(component)
        elif row.get("status", "").strip().upper() != "VERIFIED":
            unverified.append(row.get("component", component))
    return missing + unverified


def scan_source(files: list[str]) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {name: [] for name in RISKY_PATTERNS}
    extensions = {".py", ".sh", ".yml", ".yaml", ".toml", ".ini", ".env", ".cfg"}
    excluded = {"scripts/compliance_gate.py", "scripts/generate_sbom.py"}
    for rel in files:
        if rel in excluded:
            continue
        path = ROOT / rel
        if path.suffix not in extensions or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, pattern in RISKY_PATTERNS.items():
            if pattern.search(text):
                findings[name].append(rel)
    return {k: v for k, v in findings.items() if v}


def sbom_state(path: Path) -> tuple[bool, list[str]]:
    if not path.is_file():
        return False, [f"SBOM_NOT_FOUND:{path}"]
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"SBOM_INVALID:{type(exc).__name__}"]

    problems: list[str] = []
    if document.get("spdxVersion") != "SPDX-2.3":
        problems.append("SBOM_BAD_SPDX_VERSION")
    packages = document.get("packages")
    if not isinstance(packages, list) or not packages:
        problems.append("SBOM_NO_PACKAGES")
        return False, problems

    indexed = {}
    for package in packages:
        name = package.get("name")
        version = package.get("versionInfo")
        if not name or not version:
            problems.append("SBOM_PACKAGE_WITHOUT_NAME_OR_VERSION")
            continue
        key = normalize_name(name)
        if key in indexed:
            problems.append(f"SBOM_DUPLICATE_PACKAGE:{name}")
        indexed[key] = package

    for required in sorted(declared_requirements("requirements.txt")):
        package = indexed.get(required)
        if not package:
            problems.append(f"SBOM_MISSING_CORE_PACKAGE:{required}")
            continue
        license_declared = str(package.get("licenseDeclared", "")).strip()
        if not license_declared or license_declared == "NOASSERTION":
            problems.append(f"SBOM_NO_LICENSE_METADATA:{package.get('name', required)}")

    return not problems, problems


def implementation_invariants() -> dict[str, bool]:
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    voice_text = (ROOT / "core" / "voice_endpoint.py").read_text(encoding="utf-8")
    return {
        "external_bind_fail_closed": all(x in main_text for x in ("EXTERNAL_BIND", "Refusing non-loopback bind", "SIMORGH_KEY")),
        "external_token_verification": all(x in main_text for x in ("secrets.compare_digest", 'request.headers.get("x-token"', "status_code=401")),
        "hosted_session_isolation": all(x in main_text for x in ("x-simorgh-session", "hashlib.sha256", "MAX_SESSION_HEADER")),
        "ai_disclosure": all(x in main_text for x in ("AI_DISCLOSURE", "ai_disclosure", "X-SIMORGH-AI-GENERATED")),
        "voice_size_bound": all(x in voice_text for x in ("SIMORGH_MAX_VOICE_BYTES", "Voice payload too large")),
        "voice_header_privacy": "X-User-Text" not in voice_text and "X-Response-Text" not in voice_text,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--include-optional", action="store_true", help="include optional feature dependencies in the license gate")
    parser.add_argument("--sbom", type=Path, default=None)
    args = parser.parse_args()

    print("SIMORGH compliance gate")
    print("mode:", "RELEASE" if args.release else "AUDIT")
    print("dependency_scope:", "core+optional" if args.include_optional else "core")

    missing_docs = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.exists()]
    files = tracked_files()
    missing_assets, unverified_assets = rights_coverage(files)
    unverified_deps = third_party_state(include_optional=args.include_optional)
    findings = scan_source(files)
    invariants = implementation_invariants()

    checks = {
        "required_documents": not missing_docs,
        "asset_rights_ledger_coverage": not missing_assets,
        "asset_rights_verified": not unverified_assets,
        "third_party_license_verified": not unverified_deps,
        "dangerous_runtime_patterns": not findings,
        **invariants,
    }

    if args.sbom is not None:
        sbom_ok, sbom_problems = sbom_state(args.sbom)
        checks["sbom_core_dependency_metadata"] = sbom_ok
        if sbom_problems:
            print("sbom_problems:", ", ".join(sbom_problems))
    elif args.release:
        checks["sbom_core_dependency_metadata"] = False
        print("sbom_problems: SBOM_REQUIRED_FOR_RELEASE")
    else:
        print("sbom_check: not supplied in audit mode")

    for name, ok in checks.items():
        print(f"[{ 'PASS' if ok else 'BLOCK' }] {name}")
    if missing_docs:
        print("missing_documents:", ", ".join(missing_docs))
    if missing_assets:
        print("missing_asset_ledger_entries:", ", ".join(missing_assets[:20]))
    if unverified_assets:
        print("unverified_assets:", len(unverified_assets), "items")
    if unverified_deps:
        print("unverified_dependencies:", ", ".join(unverified_deps))
    if findings:
        for name, paths in findings.items():
            print(name + ":", ", ".join(paths))

    if args.release:
        signoff = (ROOT / "compliance" / "RELEASE_SIGNOFF.md").read_text(encoding="utf-8")
        if "Release decision: `APPROVED`" not in signoff:
            print("[BLOCK] human_release_signoff")
            return 1
        if not all(checks.values()):
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
