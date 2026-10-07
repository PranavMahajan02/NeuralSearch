"""Search evaluation harness (run against a live backend as the owner).

    venv\\Scripts\\python scripts\\eval_search.py [--base-url http://127.0.0.1:8000]
                                               [--email pranav2@gmail.com] [--label baseline]

Mints the owner's JWT in-process (never printed), runs tests/eval/queries.yaml
through POST /search/, and reports per query and in aggregate:

  precision@5 = relevant in top 5 / min(5, number of relevant)
  recall@10   = relevant in top 10 / number of relevant
  MRR         = mean of 1 / rank of the first relevant result (0 if none in the list)
  negatives   = results returned for negative queries (false positives)
  latency     = p50 / p95 over all queries (HTTP round trip, warm)

Relevance is judged by file name (case-insensitive, exact) or source_id.
Results are saved to docs/eval/<timestamp>-<label>.json.
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("PRELOAD_MODELS", "false")

import requests  # noqa: E402
import yaml  # noqa: E402

from app.auth.jwt_handler import create_access_token  # noqa: E402
from app.database.db import SessionLocal  # noqa: E402
from app.database.models import User  # noqa: E402


def owner_headers(email: str) -> dict:

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        token = create_access_token(str(user.id), user.token_version)

    return {"Authorization": f"Bearer {token}"}


def percentile(values, pct):

    if not values:
        return 0.0

    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct / 100 * (len(ordered) - 1))))

    return ordered[index]


def is_relevant(result: dict, expected: set) -> bool:

    return (result.get("file") or "").lower() in expected or (result.get("source_id") or "").lower() in expected


# The owner's GitHub index contains THIS repository, whose eval set, eval
# results and tests contain every eval query verbatim (true content matches).
# They are dropped from the measurement (and counted) unless --include-self.
# docs/QA_REPORT.md is the audit that defined the eval negatives (it quotes them).
SELF_ARTIFACT = re.compile(r"(^|/)(tests/eval/|docs/eval/|docs/QA_REPORT\.md$|tests/test_[^/]*\.py$|scripts/eval_search\.py$)")


def is_self_artifact(result: dict) -> bool:

    if result.get("platform") != "github":
        return False

    path = (result.get("source_id") or "").split(":", 1)[-1]

    return bool(SELF_ARTIFACT.search(path))


def run(base_url: str, headers: dict, queries: list, limit: int, include_self: bool = False) -> dict:

    per_query = []
    latencies = []

    # Warm-up (model load, caches), not measured.
    requests.post(f"{base_url}/search/", json={"query": "warm up"}, headers=headers, timeout=300)

    for item in queries:

        query = item["query"]
        body = {"query": query}
        if limit:
            body["limit"] = limit

        start = time.perf_counter()
        response = requests.post(f"{base_url}/search/", json=body, headers=headers, timeout=300)
        latency = time.perf_counter() - start
        latencies.append(latency)

        results = response.json().get("results", []) if response.status_code == 200 else []
        dropped = 0 if include_self else sum(1 for r in results if is_self_artifact(r))
        if not include_self:
            results = [r for r in results if not is_self_artifact(r)]
        files = [r.get("file") for r in results]

        record = {
            "query": query,
            "status": response.status_code,
            "latency_s": round(latency, 4),
            "returned": len(results),
            "top5": files[:5],
        }

        if dropped:
            record["self_artifacts_dropped"] = dropped

        if item.get("visual"):
            record["visual"] = True

        if item.get("code"):
            record["code"] = True

        if item.get("visual_video"):
            record["visual_video"] = True

        if item.get("negative"):
            record["negative"] = True
            record["false_positives"] = len(results)
        else:
            expected = {name.lower() for name in item["expected"]}
            flags = [is_relevant(r, expected) for r in results]
            first = next((i + 1 for i, hit in enumerate(flags) if hit), None)
            record.update({
                "modality": item.get("modality"),
                "precision_at_5": sum(flags[:5]) / min(5, len(expected)),
                "recall_at_10": sum(flags[:10]) / len(expected),
                "reciprocal_rank": 1 / first if first else 0.0,
                "first_relevant_rank": first,
            })

        per_query.append(record)

    aggregate = summarize(per_query, latencies)
    aggregate["visual_only"] = summarize([r for r in per_query if r.get("visual")], [])
    aggregate["non_visual"] = summarize([r for r in per_query if not r.get("visual") and not r.get("code") and not r.get("visual_video")], [])
    aggregate["code"] = summarize([r for r in per_query if r.get("code")], [])
    aggregate["visual_video"] = summarize([r for r in per_query if r.get("visual_video")], [])

    return {"aggregate": aggregate, "per_query": per_query}


def summarize(per_query: list, latencies: list) -> dict:

    positives = [r for r in per_query if not r.get("negative")]
    negatives = [r for r in per_query if r.get("negative")]

    if not positives:
        return {}

    aggregate = {
        "queries": len(per_query),
        "positive_queries": len(positives),
        "negative_queries": len(negatives),
        "precision_at_5": round(statistics.mean(r["precision_at_5"] for r in positives), 4),
        "recall_at_10": round(statistics.mean(r["recall_at_10"] for r in positives), 4),
        "mrr": round(statistics.mean(r["reciprocal_rank"] for r in positives), 4),
        "negative_false_positives": sum(r["false_positives"] for r in negatives),
        "negative_queries_with_results": sum(1 for r in negatives if r["false_positives"]),
        "latency_p50_s": round(percentile(latencies, 50), 4),
        "latency_p95_s": round(percentile(latencies, 95), 4),
    }

    return aggregate


def print_report(report: dict, label: str):

    print(f"\n=== {label} ===")
    print(f"{'query':40} {'P@5':>5} {'R@10':>5} {'rank':>5} {'n':>4} {'ms':>6}")

    for r in report["per_query"]:
        if r.get("negative"):
            print(f"{r['query'][:40]:40} {'neg':>5} {'':>5} {'':>5} {r['returned']:>4} {r['latency_s']*1000:>6.0f}  FP={r['false_positives']}")
        else:
            rank = r["first_relevant_rank"] or "-"
            print(f"{r['query'][:40]:40} {r['precision_at_5']:>5.2f} {r['recall_at_10']:>5.2f} {rank!s:>5} {r['returned']:>4} {r['latency_s']*1000:>6.0f}")

    for name, a in (("non-visual", report["aggregate"].get("non_visual")),
                    ("visual-only", report["aggregate"].get("visual_only")),
                    ("code", report["aggregate"].get("code")),
                    ("visual-video", report["aggregate"].get("visual_video"))):
        if a:
            print(f"{name:12} P@5 {a['precision_at_5']:.3f} | R@10 {a['recall_at_10']:.3f} | MRR {a['mrr']:.3f} | "
                  f"negatives FP {a['negative_false_positives']} ({a['negative_queries_with_results']}/{a['negative_queries']})")

    a = report["aggregate"]
    print(f"\nprecision@5 {a['precision_at_5']:.3f} | recall@10 {a['recall_at_10']:.3f} | MRR {a['mrr']:.3f} | "
          f"negatives FP {a['negative_false_positives']} ({a['negative_queries_with_results']}/{a['negative_queries']} queries) | "
          f"p50 {a['latency_p50_s']*1000:.0f} ms | p95 {a['latency_p95_s']*1000:.0f} ms")


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", default="pranav2@gmail.com")
    parser.add_argument("--label", default="run")
    parser.add_argument("--queries", default=str(ROOT / "tests" / "eval" / "queries.yaml"))
    parser.add_argument("--limit", type=int, default=0, help="send a limit (0 = server default)")
    parser.add_argument("--include-self", action="store_true",
                        help="keep results from this repo's own eval/test files (indexed via GitHub)")
    args = parser.parse_args()

    queries = yaml.safe_load(open(args.queries, encoding="utf-8"))["queries"]

    report = run(args.base_url, owner_headers(args.email), queries, args.limit, args.include_self)
    report["include_self"] = args.include_self
    report["label"] = args.label
    report["created_at"] = datetime.now().isoformat(timespec="seconds")

    out_dir = ROOT / "docs" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{args.label}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print_report(report, args.label)
    print(f"\nSaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
