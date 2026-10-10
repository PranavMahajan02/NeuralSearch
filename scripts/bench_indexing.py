"""Indexing benchmark: index a fixed file set for a throwaway user through the
REAL worker path (IndexingWorker.run_once -> LocalPlatform -> pipeline) and
report where the time went.

    venv\\Scripts\\python scripts\\bench_indexing.py --label baseline --runs 2
    venv\\Scripts\\python scripts\\bench_indexing.py --folder <dir> --label eval-corpus --keep

Isolation: a SCRATCH Postgres database (default cogniseek_bench, created and
migrated here) on the same server as DATABASE_URL, a SCRATCH Qdrant collection
prefix (default bench_v2) and a scratch TEMP_DIR. The owner's database,
collections and files are never written; source files are only copied.

Models are loaded and warmed BEFORE the clock starts (cold model loading is
excluded). Each run uses a new throwaway user, so every file is indexed.

Reports: wall time (total, per file type, per stage), files/min per type,
video- and audio-minutes per minute, time until 50% / 100% of the files are
searchable, GPU utilisation and memory (nvidia-smi), CPU %, peak RSS, peak
VRAM (torch) and peak temp-dir size, plus per-file outputs (chunk counts, OCR
text length, transcript length, frame count) for equivalence checks.
Writes docs/perf/<label>.json (median over --runs).
"""

import argparse
import contextlib
import json
import os
import secrets
import shutil
import statistics
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

MEDIA_TYPES = ("audio", "video")


# ---------------------------------------------------------------------------
# Isolation: must run before any app import (settings are read at import).
# ---------------------------------------------------------------------------


def isolate(db_name: str, prefix: str, temp_dir: Path, allowed_root: Path) -> str:

    from dotenv import dotenv_values

    base = os.environ.get("DATABASE_URL") or dotenv_values(ROOT / ".env").get("DATABASE_URL")
    parsed = urllib.parse.urlparse(base)
    if parsed.path.lstrip("/") == db_name:
        raise SystemExit("refusing: the scratch database name equals the live one")

    scratch = parsed._replace(path=f"/{db_name}").geturl()

    import sqlalchemy as sa

    admin = sa.create_engine(parsed._replace(path="/postgres").geturl(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(sa.text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name}).scalar()
        if not exists:
            conn.execute(sa.text(f'CREATE DATABASE "{db_name}"'))
    admin.dispose()

    os.environ.update(
        {
            "DATABASE_URL": scratch,
            "QDRANT_COLLECTION_PREFIX": prefix,
            "QDRANT_LOCATION": "",
            "TEMP_DIR": str(temp_dir),
            "PRELOAD_MODELS": "true",
            "COGNISEEK_DISABLE_WORKER": "1",
            # Exactly the folder being indexed (inside a container: a mounted path).
            "ALLOWED_LOCAL_ROOTS": str(allowed_root),
        }
    )

    from alembic.config import Config

    from alembic import command

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.attributes["database_url"] = scratch
    command.upgrade(config, "head")

    return scratch


# ---------------------------------------------------------------------------
# File set
# ---------------------------------------------------------------------------


def read_set(path: Path):

    groups, current = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("# ["):
            current = line[3 : line.index("]")]
        elif line and not line.startswith("#"):
            kind, rel = line.split(":", 1)
            source = (ROOT / "data" / rel) if kind == "data" else (ROOT / rel)
            groups.append((current, source))
    return groups


def copy_set(entries, target: Path) -> list:

    target.mkdir(parents=True, exist_ok=True)
    copied = []
    for group, source in entries:
        destination = target / source.name
        shutil.copy2(source, destination)
        copied.append((group, destination))
    return copied


def media_minutes(path: Path) -> float:

    try:
        if path.suffix.lower() in (".mp4", ".mov", ".mkv", ".avi", ".webm"):
            import cv2

            cap = cv2.VideoCapture(str(path))
            fps, frames = cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            return frames / fps / 60 if fps else 0.0
        from moviepy import AudioFileClip

        clip = AudioFileClip(str(path))
        try:
            return clip.duration / 60
        finally:
            clip.close()
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Resource sampling
# ---------------------------------------------------------------------------


class Sampler(threading.Thread):
    def __init__(self, temp_root: Path, interval: float = 1.0):

        super().__init__(daemon=True)
        import psutil

        self.process = psutil.Process()
        self.temp_root = temp_root
        self.interval = interval
        self.stop_event = threading.Event()
        self.gpu_util, self.gpu_mem, self.cpu, self.rss, self.temp = [], [], [], [], []
        self.has_gpu = shutil.which("nvidia-smi") is not None
        self.process.cpu_percent(None)

    def _dir_size(self) -> int:

        total = 0
        for dirpath, _, files in os.walk(self.temp_root):
            for name in files:
                with contextlib.suppress(OSError):
                    total += os.path.getsize(os.path.join(dirpath, name))
        return total

    def run(self):

        import psutil

        while not self.stop_event.wait(self.interval):
            self.cpu.append(psutil.cpu_percent(None))
            self.rss.append(self.process.memory_info().rss)
            self.temp.append(self._dir_size())
            if self.has_gpu:
                try:
                    out = (
                        subprocess.run(
                            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        .stdout.strip()
                        .splitlines()[0]
                    )
                    util, mem = (float(x) for x in out.split(","))
                    self.gpu_util.append(util)
                    self.gpu_mem.append(mem)
                except Exception:
                    pass

    def summary(self) -> dict:

        def mean(values):
            return round(statistics.fmean(values), 1) if values else None

        return {
            "cpu_percent_mean": mean(self.cpu),
            "cpu_percent_max": max(self.cpu, default=None),
            "peak_rss_mb": round(max(self.rss, default=0) / 2**20),
            "peak_temp_mb": round(max(self.temp, default=0) / 2**20, 1),
            "gpu_util_mean": mean(self.gpu_util),
            "gpu_util_samples": len(self.gpu_util),
            "gpu_busy_share": round(sum(1 for u in self.gpu_util if u > 10) / len(self.gpu_util), 2)
            if self.gpu_util
            else None,
            "gpu_mem_used_peak_mb": max(self.gpu_mem, default=None),
        }


# ---------------------------------------------------------------------------
# One run
# ---------------------------------------------------------------------------


def warm_models() -> None:

    from app.ai import embedder
    from app.ai.model_manager import model_manager
    from app.search import calibration
    from app.search.frame_null import null_matrix

    model_manager.preload()
    calibration.text_neutral_matrix()
    calibration.clip_neutral_matrix()
    null_matrix()
    embedder.embed_texts(["warm up"])


def create_user(email: str):

    from app.auth.password import hash_password
    from app.database.db import SessionLocal
    from app.database.models import User

    with SessionLocal() as db:
        user = User(
            email=email,
            full_name="Bench",
            password_hash=hash_password(secrets.token_urlsafe(16)),
            onboarding_completed=True,
        )
        db.add(user)
        db.commit()
        return user.id


def outputs_per_file(user_id) -> dict:
    """Per file: status, chunk count, extracted text length per point type, frames."""

    from app.database.db import SessionLocal
    from app.database.models import IndexedFile
    from app.vectorstore.client import get_client
    from app.vectorstore.config import all_collections
    from app.vectorstore.query import user_filter

    with SessionLocal() as db:
        rows = db.query(IndexedFile).filter(IndexedFile.user_id == user_id).all()
        files = {
            r.source_id: {
                "file": r.file_name,
                "type": r.file_type,
                "status": r.status,
                "chunks": r.chunk_count or 0,
                "indexed_at": r.indexed_at,
            }
            for r in rows
        }

    client = get_client()
    for name in all_collections():
        offset = None
        while True:
            points, offset = client.scroll(
                name,
                scroll_filter=user_filter(str(user_id), "all"),
                limit=512,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload
                entry = files.get(payload.get("source_id"))
                if entry is None:
                    continue
                kind = payload.get("type")
                key = {
                    "document": "text_chars",
                    "image": "ocr_chars",
                    "audio": "transcript_chars",
                    "video": "transcript_chars",
                    "video_frame": "frames",
                }.get(kind, kind)
                if kind == "video_frame":
                    entry["frames"] = entry.get("frames", 0) + 1
                else:
                    entry[key] = entry.get(key, 0) + len(payload.get("chunk") or "")
            if offset is None:
                break
    return files


def run_once(folder: Path, media: dict, temp_root: Path) -> dict:

    from app.database.db import SessionLocal
    from app.database.local_storage_service import add_local_folder
    from app.database.models import IndexingJob
    from app.scheduler.jobs import enqueue_jobs
    from app.scheduler.worker import IndexingWorker

    email = f"bench-{secrets.token_hex(4)}@example.com"
    user_id = create_user(email)

    with SessionLocal() as db:
        add_local_folder(db, user_id, str(folder))
        job_id = enqueue_jobs(db, user_id, "local", ["local"])[0].id

    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except Exception:
        pass

    sampler = Sampler(temp_root)
    sampler.start()
    started = time.perf_counter()
    IndexingWorker().run_once()
    wall = time.perf_counter() - started
    sampler.stop_event.set()
    sampler.join()

    with SessionLocal() as db:
        job = db.get(IndexingJob, job_id)
        timings, job_started = job.stage_timings or {}, job.started_at
        status = (job.status, job.succeeded_files, job.failed_files, job.skipped_files)

    files = outputs_per_file(user_id)

    # Searchable = the ledger row is written (points are upserted before it).
    done = sorted((f["indexed_at"] - job_started).total_seconds() for f in files.values() if f["indexed_at"])
    half = done[(len(done) - 1) // 2] if done else None

    by_type_wall = {t: round(sum(v.values()), 2) for t, v in timings.get("by_type", {}).items()}
    counts = {}
    for f in files.values():
        counts[f["type"]] = counts.get(f["type"], 0) + 1

    throughput = {t: round(counts[t] / by_type_wall[t] * 60, 2) for t in counts if by_type_wall.get(t)}
    for kind in MEDIA_TYPES:
        if by_type_wall.get(kind):
            throughput[f"{kind}_minutes_per_minute"] = round(media.get(kind, 0) / by_type_wall[kind] * 60, 2)

    try:
        import torch

        peak_vram = round(torch.cuda.max_memory_allocated() / 2**20) if torch.cuda.is_available() else None
    except Exception:
        peak_vram = None

    result = {
        "email": email,
        "user_id": str(user_id),
        "job_status": status,
        "wall_seconds": round(wall, 2),
        "time_to_50pct_searchable_s": round(half, 2) if half is not None else None,
        "time_to_100pct_searchable_s": round(done[-1], 2) if done else None,
        "stage_seconds": timings.get("seconds", {}),
        "stage_calls": timings.get("calls", {}),
        "by_type_stage_seconds": timings.get("by_type", {}),
        "by_type_seconds": by_type_wall,
        "files_per_type": counts,
        "throughput_per_minute": throughput,
        "resources": {**sampler.summary(), "peak_vram_torch_mb": peak_vram},
        "files": {f["file"]: {k: v for k, v in f.items() if k not in ("file", "indexed_at")} for f in files.values()},
    }
    return result


def delete_user(user_id) -> None:

    from app.database.db import SessionLocal
    from app.services.account_service import delete_account

    with SessionLocal() as db:
        delete_account(db, user_id, require_idle=False)


def median_of(runs: list) -> dict:
    """Numeric fields: median across runs (per key); everything else from run 1."""

    def merge(values):
        if not values:
            return None
        first = values[0]
        if isinstance(first, dict):
            keys = {k for v in values for k in v}
            return {k: merge([v.get(k) for v in values if v.get(k) is not None]) for k in sorted(keys)} if keys else {}
        if isinstance(first, (int, float)) and not isinstance(first, bool):
            return round(statistics.median(values), 3)
        return first

    return merge(runs)


def main() -> int:

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", default=str(ROOT / "docs/perf/benchmark-set.txt"))
    parser.add_argument("--folder", help="index this folder as-is instead of copying --set")
    parser.add_argument("--label", default="bench")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--db-name", default="cogniseek_bench")
    parser.add_argument("--prefix", default="bench_v2")
    parser.add_argument("--workdir", default=str(Path(os.environ.get("TEMP", "/tmp")) / "cogniseek-bench"))
    parser.add_argument("--out-dir", default=str(ROOT / "docs/perf"))
    parser.add_argument("--keep", action="store_true", help="keep the last run's user and index (for the eval)")
    args = parser.parse_args()

    workdir = Path(args.workdir)
    temp_root = workdir / "temp"
    temp_root.mkdir(parents=True, exist_ok=True)

    if args.folder:
        folder = Path(args.folder).resolve()
        files = [(None, p) for p in folder.rglob("*") if p.is_file()]
    else:
        folder = workdir / "set"
        if folder.exists():
            shutil.rmtree(folder)
        files = copy_set(read_set(Path(args.set)), folder)

    isolate(args.db_name, args.prefix, temp_root, folder)

    from app.config.file_types import file_type_for

    media = {}
    for _, path in files:
        kind = file_type_for(path.name)
        if kind in MEDIA_TYPES:
            media[kind] = media.get(kind, 0.0) + media_minutes(path)

    from app.vectorstore.schema import ensure_collections

    ensure_collections()

    print("warming models ...", flush=True)
    warm_models()

    runs = []
    for number in range(args.runs):
        print(f"run {number + 1}/{args.runs}: {len(files)} files", flush=True)
        result = run_once(folder, media, temp_root)
        runs.append(result)
        print(
            f"  wall {result['wall_seconds']}s, job {result['job_status']}, "
            f"50% searchable after {result['time_to_50pct_searchable_s']}s",
            flush=True,
        )
        if not (args.keep and number == args.runs - 1):
            delete_user(result["user_id"])

    summary = median_of(runs)
    summary.update(
        {
            "label": args.label,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "runs": len(runs),
            "run_walls": [r["wall_seconds"] for r in runs],
            "file_count": len(files),
            "media_minutes": {k: round(v, 2) for k, v in media.items()},
            "kept_user": runs[-1]["email"] if args.keep else None,
        }
    )
    if not args.keep:
        summary.pop("email", None)
    summary.pop("user_id", None)

    out = Path(args.out_dir) / f"{args.label}.json"
    out.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"saved {out}")
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "wall_seconds",
                    "time_to_50pct_searchable_s",
                    "by_type_seconds",
                    "stage_seconds",
                    "throughput_per_minute",
                    "resources",
                )
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
