"""Prometheus metrics (GET /metrics, internal only: Caddy never proxies it).

HTTP latency/count come from prometheus-fastapi-instrumentator; search latency
and job outcomes are recorded here.
"""

from prometheus_client import Counter, Histogram


SEARCH_LATENCY = Histogram(
    "cogniseek_search_seconds",
    "Time to answer a search request.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8, 16),
)

JOBS_FINISHED = Counter(
    "cogniseek_index_jobs_total",
    "Indexing jobs that reached a final status.",
    ["platform", "status"],
)

FILES_INDEXED = Counter(
    "cogniseek_index_files_total",
    "Files processed by indexing jobs, by outcome.",
    ["platform", "outcome"],
)


def record_job(job) -> None:

    JOBS_FINISHED.labels(job.platform, job.status).inc()
    FILES_INDEXED.labels(job.platform, "succeeded").inc(job.succeeded_files or 0)
    FILES_INDEXED.labels(job.platform, "failed").inc(job.failed_files or 0)
    FILES_INDEXED.labels(job.platform, "skipped").inc(job.skipped_files or 0)


def install(app) -> None:

    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator(
        excluded_handlers=["/metrics", "/health", "/ready"],
        should_group_status_codes=True,
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
