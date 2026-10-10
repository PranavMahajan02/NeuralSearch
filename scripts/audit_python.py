"""Python dependency audit for CI: fail only on HIGH/CRITICAL advisories that are
not in the documented allowlist (security/audit-allowlist.json -> SECURITY.md).

    python scripts/audit_python.py [--requirements backend/requirements-linux.lock]

pip-audit does not report severities, so each finding is looked up in OSV
(https://osv.dev): the GitHub advisory alias carries the severity
(LOW / MODERATE / HIGH / CRITICAL). An advisory whose severity cannot be found
is reported but does not fail the build (OSV lookups can be rate limited).
"""

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = ROOT / "security" / "audit-allowlist.json"
FAILING = {"HIGH", "CRITICAL"}


def osv(vuln_id: str) -> dict:
    try:
        with urllib.request.urlopen(f"https://api.osv.dev/v1/vulns/{vuln_id}", timeout=20) as response:
            return json.load(response)
    except Exception:
        return {}


def severity(vuln_id: str, aliases: list) -> str:
    for candidate in [vuln_id, *aliases]:
        record = osv(candidate)
        level = (record.get("database_specific") or {}).get("severity")
        if level:
            return str(level).upper()
        for alias in record.get("aliases", []):
            if alias.startswith("GHSA-") and alias != candidate:
                level = (osv(alias).get("database_specific") or {}).get("severity")
                if level:
                    return str(level).upper()
    return "UNKNOWN"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--requirements", action="append", default=None)
    args = parser.parse_args()
    requirements = args.requirements or ["backend/requirements-linux.lock", "requirements-test.txt"]

    allow = json.loads(ALLOWLIST.read_text(encoding="utf-8"))["python"]
    allowed_packages = {entry["package"].lower(): entry for entry in allow}

    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "--no-deps",
        "--disable-pip",
        "--progress-spinner",
        "off",
        "-f",
        "json",
    ]
    for path in requirements:
        command += ["-r", path]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    report = json.loads(result.stdout or "{}")

    failures, reported = [], 0
    for dependency in report.get("dependencies", []):
        for vuln in dependency.get("vulns") or []:
            reported += 1
            name = dependency["name"].lower()
            level = severity(vuln["id"], vuln.get("aliases", []))
            entry = allowed_packages.get(name)
            status = "allowlisted" if entry else ("FAIL" if level in FAILING else "ok (below HIGH)")
            print(f"{dependency['name']} {dependency['version']} {vuln['id']} {level}: {status}")
            if not entry and level in FAILING:
                failures.append(f"{dependency['name']} {vuln['id']} ({level})")

    print(f"\n{reported} advisories; {len(failures)} HIGH/CRITICAL not allowlisted")
    for failure in failures:
        print("  -", failure)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
