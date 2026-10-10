"""Compare two search-eval runs (docs/eval/*.json) query by query.

    venv\\Scripts\\python scripts\\compare_eval.py docs/eval/<before>.json docs/eval/<after>.json

Guardrail (Phase 7A.5): no subset may regress (non-visual, visual-only images,
visual-video, possible-tier recall) and no query's first relevant rank may drop
by more than 1. Exit code 1 when the guardrail is violated.
"""

import argparse
import json
import sys
from pathlib import Path

SUBSETS = ("non_visual", "visual_only", "visual_video", "code")
METRICS = ("precision_at_5", "recall_at_10", "mrr")
MISSING = 99   # "no relevant result" rank, for comparisons


def rank(entry) -> int:

    value = entry.get("first_relevant_rank")
    return value if value else MISSING


def main() -> int:

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("before")
    parser.add_argument("after")
    args = parser.parse_args()

    a = json.loads(Path(args.before).read_text(encoding="utf-8"))
    b = json.loads(Path(args.after).read_text(encoding="utf-8"))
    violations = []

    print(f"| Subset | Metric | {a['label']} | {b['label']} |")
    print("|---|---|---|---|")
    for subset in (*SUBSETS, "all"):
        before = a["aggregate"] if subset == "all" else a["aggregate"].get(subset, {})
        after = b["aggregate"] if subset == "all" else b["aggregate"].get(subset, {})
        for metric in METRICS:
            x, y = before.get(metric), after.get(metric)
            if x is None or y is None:
                continue
            flag = " (regressed)" if y < x - 1e-9 else ""
            if flag:
                violations.append(f"{subset} {metric} {x:.3f} -> {y:.3f}")
            print(f"| {subset} | {metric} | {x:.3f} | {y:.3f}{flag} |")
        fp_x, fp_y = before.get("negative_false_positives"), after.get("negative_false_positives")
        if fp_x is not None:
            flag = " (regressed)" if fp_y > fp_x else ""
            if flag:
                violations.append(f"{subset} negatives {fp_x} -> {fp_y}")
            print(f"| {subset} | negative false positives | {fp_x} | {fp_y}{flag} |")

    pa, pb = a["aggregate"].get("possible_tier", {}), b["aggregate"].get("possible_tier", {})
    for key in sorted(set(pa) | set(pb)):
        print(f"| possible tier | {key} | {pa.get(key)} | {pb.get(key)} |")
    for key in ("visual_video", "visual_image"):
        x = (pa.get(key) or {}).get("recovered_by_tier")
        y = (pb.get(key) or {}).get("recovered_by_tier")
        if x is not None and y is not None and y < x:
            violations.append(f"possible tier {key} recovered {x} -> {y}")

    by_query = {q["query"]: q for q in b["per_query"]}
    changed = []
    for q in a["per_query"]:
        other = by_query.get(q["query"])
        if other is None:
            violations.append(f"missing query {q['query']!r}")
            continue
        r1, r2 = rank(q), rank(other)
        if r1 != r2 or q.get("top5") != other.get("top5"):
            changed.append((q["query"], r1, r2, q.get("top5"), other.get("top5")))
        if r2 - r1 > 1:
            violations.append(f"rank drop {q['query']!r}: {r1} -> {r2}")

    print(f"\nQueries whose first relevant rank or top 5 changed: {len(changed)}")
    for query, r1, r2, _t1, _t2 in changed:
        show = lambda r: "-" if r == MISSING else r  # noqa: E731
        print(f"  {query[:40]:40} rank {show(r1)} -> {show(r2)}" + ("" if r1 != r2 else "  (same rank, top-5 order differs)"))

    print("\nGuardrail:", "PASS" if not violations else "FAIL")
    for v in violations:
        print("  -", v)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
