"""One-time migration: old global Qdrant collections -> v2 per-user index.

    venv\\Scripts\\python scripts\\migrate_to_v2_index.py                       # list owner candidates, stop
    venv\\Scripts\\python scripts\\migrate_to_v2_index.py --owner-email X --dry-run
    venv\\Scripts\\python scripts\\migrate_to_v2_index.py --owner-email X

- Reads the OLD collections (cogniseek, cogniseek_image, cogniseek_audio,
  cogniseek_video, cogniseek_video_frames). They are never modified: they and
  the *.pkl files are the rollback.
- Writes the v2 collections (settings.QDRANT_COLLECTION_PREFIX) and the
  indexed_files ledger, all owned by --owner-email.
- Local points whose file no longer exists are dropped (orphans).
- Duplicates collapse: per source only the newest version is kept, chunks
  are de-duplicated by text, and point ids are deterministic, so running the
  script twice gives the same result (idempotent).
- This is the only place in the code base that may read the old pickles:
  video transcript text missing from a payload is looked up in
  video_index.pkl.
"""

import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from qdrant_client.models import PointStruct  # noqa: E402

from app.core.clock import utcnow  # noqa: E402
from app.database.db import SessionLocal  # noqa: E402
from app.database.models import IndexedFile, LocalStorageFolder, PlatformConnection, User  # noqa: E402
from app.services.indexing_pipeline import github_source_id, local_source_id  # noqa: E402
from app.vectorstore.client import get_client  # noqa: E402
from app.vectorstore.config import collection_for_type  # noqa: E402
from app.vectorstore.schema import ensure_collections, point_id  # noqa: E402

OLD_COLLECTIONS = {
    "cogniseek": "document",
    "cogniseek_image": "image",
    "cogniseek_audio": "audio",
    "cogniseek_video": "video",
    "cogniseek_video_frames": "video_frame",
}

FILE_TYPE = {"document": "document", "image": "image", "audio": "audio", "video": "video", "video_frame": "video"}

FRAME_RE = re.compile(r"frame\s+(\d+)", re.IGNORECASE)

BATCH = 256


# ----------------------------------------------------------------------
# Owner
# ----------------------------------------------------------------------


def owner_candidates(db):

    rows = []

    for user in db.query(User).order_by(User.email):
        folders = db.query(LocalStorageFolder).filter(LocalStorageFolder.user_id == user.id).count()
        connections = sorted(
            c.platform
            for c in db.query(PlatformConnection).filter(
                PlatformConnection.user_id == user.id, PlatformConnection.connected.is_(True)
            )
        )
        if folders or connections:
            rows.append((user.email, str(user.id), folders, connections))

    return rows


# ----------------------------------------------------------------------
# Old data
# ----------------------------------------------------------------------


def scroll_all(client, name):

    offset = None

    while True:
        points, offset = client.scroll(name, limit=1000, offset=offset, with_payload=True, with_vectors=True)
        yield from points
        if offset is None:
            break


def load_video_pickle():
    """Fallback text for video points without a chunk (rarely needed)."""

    path = ROOT / "video_index.pkl"

    if not path.exists():
        return {}

    import pickle  # one-time migration only

    with open(path, "rb") as f:
        items = pickle.load(f)

    lookup = defaultdict(list)

    for item in items:
        key = item.get("file_id") or item.get("path")
        if key and item.get("chunk"):
            lookup[key].append(item["chunk"])

    return lookup


def identify(payload):
    """(platform, source_id, display_path, version, owner, repo) or None + reason."""

    platform = payload.get("platform") or "local"

    if platform == "local":
        path = payload.get("path")
        if not path or not os.path.isfile(path):
            return None, "orphan"
        real = os.path.realpath(path)
        version = payload.get("last_modified")
        return (
            platform,
            local_source_id(path),
            real,
            None if version is None else repr(float(version)),
            None,
            None,
        ), None

    if platform == "google_drive":
        file_id = payload.get("file_id")
        if not file_id:
            return None, "invalid"
        version = payload.get("sha") or payload.get("last_modified")
        return (
            platform,
            file_id,
            payload.get("file") or file_id,
            None if version is None else str(version),
            None,
            None,
        ), None

    if platform == "github":
        owner, repo, path = payload.get("owner"), payload.get("repo"), payload.get("file_id")
        if not (owner and repo and path):
            return None, "invalid"
        return (
            platform,
            github_source_id(owner, repo, path),
            f"{owner}/{repo}/{path}",
            payload.get("sha"),
            owner,
            repo,
        ), None

    return None, "invalid"


def newest_version(platform, versions: Counter):

    if platform == "github":
        # SHAs are not ordered: keep the version with the most points.
        return versions.most_common(1)[0][0]

    keyed = [v for v in versions if v is not None]

    if not keyed:
        return None

    if platform == "local":
        return max(keyed, key=float)

    return max(keyed)


# ----------------------------------------------------------------------
# Plan
# ----------------------------------------------------------------------


def plan(client, owner_id, video_fallback):

    report = {}
    sources = {}  # (platform, source_id) -> ledger fields
    planned = defaultdict(list)  # point_type -> [PointStruct]

    for old_name, point_type in OLD_COLLECTIONS.items():
        groups = defaultdict(list)
        stats = Counter()

        for point in scroll_all(client, old_name):
            stats["old"] += 1
            payload = point.payload or {}
            identity, reason = identify(payload)

            if identity is None:
                stats[reason] += 1
                continue

            groups[identity[:2]].append((identity, payload, point.vector))

        kept = 0

        for (platform, source_id), items in groups.items():
            versions = Counter(identity[3] for identity, _, _ in items)
            version = newest_version(platform, versions)
            current = [item for item in items if item[0][3] == version]
            stats["older_versions"] += len(items) - len(current)

            identity = current[0][0]
            _, _, display_path, _, owner, repo = identity
            payload0 = current[0][1]

            chunks = {}

            for _identity, payload, vector in current:
                text = payload.get("chunk") or payload.get("ocr_text") or ""

                if point_type == "video" and not text:
                    fallback = video_fallback.get(payload.get("file_id") or payload.get("path"), [])
                    text = fallback[0] if fallback else ""

                if point_type == "video_frame":
                    match = FRAME_RE.search(text)
                    key = int(match.group(1)) if match else len(chunks)
                else:
                    key = text

                chunks.setdefault(key, (text, vector))

            stats["duplicates"] += len(current) - len(chunks)

            ordered = sorted(chunks.items(), key=lambda kv: kv[0] if point_type == "video_frame" else str(kv[0]))

            for index, (key, (text, vector)) in enumerate(ordered):
                frame_number = key if point_type == "video_frame" else None
                chunk_index = frame_number if point_type == "video_frame" else index

                payload = {
                    "user_id": owner_id,
                    "platform": platform,
                    "source_id": source_id,
                    "file": payload0.get("file") or os.path.basename(display_path),
                    "path": display_path,
                    "type": point_type,
                    "version": float(version) if platform == "local" and version else version,
                    "chunk_index": chunk_index,
                    "chunk": text if point_type != "video_frame" else f"Frame {frame_number}",
                }

                if frame_number is not None:
                    payload["frame_number"] = frame_number

                if platform == "github":
                    payload["owner"] = owner
                    payload["repo"] = repo

                planned[point_type].append(
                    PointStruct(
                        id=point_id(owner_id, platform, source_id, point_type, chunk_index, frame_number),
                        vector=list(vector),
                        payload=payload,
                    )
                )
                kept += 1

            ledger = sources.setdefault(
                (platform, source_id),
                {
                    "platform": platform,
                    "source_id": source_id,
                    "file_name": payload0.get("file") or os.path.basename(display_path),
                    "display_path": display_path,
                    "file_type": FILE_TYPE[point_type],
                    "version": version,
                    "owner": owner,
                    "repo": repo,
                    "chunk_count": 0,
                },
            )
            ledger["chunk_count"] += len(chunks)

        stats["new"] = kept
        report[old_name] = stats

    return report, sources, planned


# ----------------------------------------------------------------------
# Write
# ----------------------------------------------------------------------


def write(client, owner_id, sources, planned):

    ensure_collections()

    for point_type, points in planned.items():
        name = collection_for_type(point_type)
        for start in range(0, len(points), BATCH):
            client.upsert(collection_name=name, points=points[start : start + BATCH], wait=True)

    now = utcnow()

    with SessionLocal() as db:
        for data in sources.values():
            row = (
                db.query(IndexedFile)
                .filter(
                    IndexedFile.user_id == owner_id,
                    IndexedFile.platform == data["platform"],
                    IndexedFile.source_id == data["source_id"],
                )
                .first()
            )

            if row is None:
                row = IndexedFile(user_id=owner_id, platform=data["platform"], source_id=data["source_id"])
                db.add(row)

            row.file_name = data["file_name"]
            row.display_path = data["display_path"]
            row.file_type = data["file_type"]
            row.version = data["version"]
            row.status = "indexed"
            row.chunk_count = data["chunk_count"]
            row.owner = data["owner"]
            row.repo = data["repo"]
            row.error = None
            row.indexed_at = row.indexed_at or now
            row.updated_at = now

        db.commit()


def print_report(report, sources, planned, client, owner_id, dry_run):

    print()
    print("Migration report" + (" (DRY RUN - nothing written)" if dry_run else ""))
    print(
        f"{'old collection':24} {'old':>7} {'orphans':>8} {'invalid':>8} {'old ver.':>8} {'dupes':>7} {'new':>7}  -> v2 collection"
    )

    for old_name, stats in report.items():
        point_type = OLD_COLLECTIONS[old_name]
        target = collection_for_type(point_type)
        print(
            f"{old_name:24} {stats['old']:>7} {stats['orphan']:>8} {stats['invalid']:>8} "
            f"{stats['older_versions']:>8} {stats['duplicates']:>7} {stats['new']:>7}  -> {target}"
        )

    if not dry_run:
        from app.vectorstore.query import user_filter

        print()
        print("v2 point counts for the owner (read back from Qdrant):")
        for point_type in OLD_COLLECTIONS.values():
            name = collection_for_type(point_type)
            count = client.count(name, count_filter=user_filter(owner_id), exact=True).count
            print(f"  {name:32} {count}")

    by = Counter((d["platform"], d["file_type"]) for d in sources.values())
    print()
    print("Ledger rows (indexed_files) by platform/type:")
    for (platform, file_type), count in sorted(by.items()):
        print(f"  {platform:14} {file_type:9} {count}")
    print(f"  total          {sum(by.values())}")


def main():

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--owner-email", help="user who owns all existing (pre-v2) data")
    parser.add_argument("--dry-run", action="store_true", help="compute and print the report, write nothing")
    args = parser.parse_args()

    client = get_client()

    with SessionLocal() as db:
        candidates = owner_candidates(db)

        if not args.owner_email:
            print("Owner candidates (users with local folders and/or connections):")
            for email, _user_id, folders, connections in candidates:
                print(f"  {email:30} folders={folders} connections={','.join(connections) or '-'}")
            print("\nRe-run with --owner-email <email> (and --dry-run first). Nothing was written.")
            return 2

        owner = db.query(User).filter(User.email == args.owner_email.strip().lower()).first()

        if owner is None:
            print(f"No user with email {args.owner_email!r}.")
            return 1

        owner_id = str(owner.id)

    print(f"Owner: {args.owner_email} ({owner_id})")
    print(f"Target prefix: {collection_for_type('document').rsplit('_', 1)[0]}")

    report, sources, planned = plan(client, owner_id, load_video_pickle())

    if not args.dry_run:
        write(client, owner_id, sources, planned)

    print_report(report, sources, planned, client, owner_id, args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
