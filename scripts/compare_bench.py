"""Compare two bench_indexing.py results: timings, resources and per-file outputs.

    venv\\Scripts\\python scripts\\compare_bench.py docs/perf/baseline.json docs/perf/after-gpu-ocr.json

Prints the before -> after table and every per-file output difference above
--threshold (default 5%): chunk counts, extracted/OCR/transcript characters,
video frame counts, status changes.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIELDS = ("status", "chunks", "text_chars", "ocr_chars", "transcript_chars", "frames")


def pct(before, after) -> str:

    if not before:
        return "n/a"
    return f"{(after - before) / before * 100:+.0f}%"


def speedup(before, after) -> str:

    return f"{before / after:.1f}x" if after else "n/a"


def output_diffs(before: dict, after: dict, threshold: float) -> list:

    diffs = []
    for name in sorted(set(before) | set(after)):
        a, b = before.get(name), after.get(name)
        if a is None or b is None:
            diffs.append((name, "file", "missing" if b is None else "new", ""))
            continue
        for field in FIELDS:
            x, y = a.get(field), b.get(field)
            if x == y:
                continue
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                base = max(abs(x), 1)
                if abs(y - x) / base <= threshold:
                    continue
            diffs.append((name, field, x, y))
    return diffs


def main() -> int:

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--threshold", type=float, default=0.05)
    args = parser.parse_args()

    from app.core.timing import STAGES

    a = json.loads(Path(args.before).read_text(encoding="utf-8"))
    b = json.loads(Path(args.after).read_text(encoding="utf-8"))

    print(f"| Metric | {a['label']} | {b['label']} | Change |")
    print("|---|---|---|---|")
    for key, label in (
        ("wall_seconds", "Total wall time (s)"),
        ("time_to_50pct_searchable_s", "50% of files searchable after (s)"),
        ("time_to_100pct_searchable_s", "100% searchable after (s)"),
    ):
        print(f"| {label} | {a[key]:.1f} | {b[key]:.1f} | {speedup(a[key], b[key])} faster |")
    for t in sorted(set(a["by_type_seconds"]) | set(b["by_type_seconds"])):
        x, y = a["by_type_seconds"].get(t, 0), b["by_type_seconds"].get(t, 0)
        print(f"| {t} (stage seconds) | {x:.1f} | {y:.1f} | {pct(x, y)} |")
    for s in STAGES:
        x, y = a["stage_seconds"].get(s, 0), b["stage_seconds"].get(s, 0)
        if x or y:
            print(f"| stage: {s} | {x:.1f} | {y:.1f} | {pct(x, y)} |")
    for k in sorted(set(a["throughput_per_minute"]) | set(b["throughput_per_minute"])):
        x, y = a["throughput_per_minute"].get(k, 0), b["throughput_per_minute"].get(k, 0)
        print(f"| throughput: {k}/min | {x:.1f} | {y:.1f} | {speedup(y, x) if x else 'n/a'} |")
    for k in sorted(set(a["resources"]) | set(b["resources"])):
        print(f"| resource: {k} | {a['resources'].get(k)} | {b['resources'].get(k)} | |")

    diffs = output_diffs(a["files"], b["files"], args.threshold)
    print(f"\nPer-file output differences above {args.threshold:.0%}: {len(diffs)}")
    for name, field, x, y in diffs:
        print(f"  {name[:60]:60} {field:17} {x} -> {y}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
