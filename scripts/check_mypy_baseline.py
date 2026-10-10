"""mypy with a baseline: fail only on errors that are not in mypy-baseline.txt.

    python scripts/check_mypy_baseline.py            # check (CI)
    python scripts/check_mypy_baseline.py --update   # rewrite the baseline (after fixing errors)

Errors are compared without line numbers ("path: message [code]"), so edits
that move code do not count as new errors. Most baseline entries come from the
legacy `Column(...)` declarative models (typed as Column[...] instead of the
value type); migrating the models to `Mapped[...]` would clear them.
"""

import argparse
import collections
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "mypy-baseline.txt"
LINE = re.compile(r"^(?P<path>[^:]+):\d+(?::\d+)?: error: (?P<message>.*)$")


def current_errors() -> collections.Counter:

    result = subprocess.run([sys.executable, "-m", "mypy"], cwd=ROOT, capture_output=True, text=True)
    errors = collections.Counter()
    for line in result.stdout.splitlines():
        match = LINE.match(line.strip())
        if match:
            errors[f"{match['path'].replace(chr(92), '/')}: {match['message']}"] += 1
    return errors


def main() -> int:

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()

    errors = current_errors()

    if args.update:
        BASELINE.write_text("".join(f"{e}\n" for e in sorted(errors.elements())), encoding="utf-8", newline="\n")
        print(f"baseline written: {sum(errors.values())} errors")
        return 0

    baseline = collections.Counter(line for line in BASELINE.read_text(encoding="utf-8").splitlines() if line)
    new = errors - baseline
    fixed = baseline - errors

    print(
        f"mypy: {sum(errors.values())} errors (baseline {sum(baseline.values())}); "
        f"{sum(new.values())} new, {sum(fixed.values())} fixed since the baseline"
    )
    in_ci = bool(os.environ.get("GITHUB_ACTIONS"))
    for error in sorted(new.elements()):
        print(f"  NEW {error}")
        if in_ci:  # surfaces in the run summary / PR checks as an annotation
            print(f"::error title=New mypy error::{error}")
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
