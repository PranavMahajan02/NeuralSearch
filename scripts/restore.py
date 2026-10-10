"""Restore (or verify) a backup made by scripts/backup.py.

    # 1. Always first: decrypt, verify every checksum, list the dump. Writes nothing.
    docker compose run --rm backup python3 /scripts/restore.py --dry-run /backups/cogniseek-<UTC>.tar.enc

    # 2. Restore into a SCRATCH database and collection prefix (safe; e.g. to inspect or test):
    docker compose run --rm backup python3 /scripts/restore.py /backups/<file> \
        --database-url postgresql://postgres:<pw>@postgres/restore_check --create-database \
        --target-prefix restorecheck

    # 3. Disaster recovery onto the live names (stop the backend first):
    docker compose stop backend caddy
    docker compose run --rm backup python3 /scripts/restore.py /backups/<file> --yes
    docker compose up -d

Postgres: pg_restore --clean --if-exists --no-owner (objects are owned by the
connecting role). Qdrant: each snapshot is uploaded as <target-prefix>_<kind>,
replacing a collection of that name. Secrets are never printed.
"""

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backup import FORMAT, Qdrant, _safe, database_name, decrypt_stream, pg_command, sha256_file


def extract(archive: Path, workdir: Path, key: str) -> dict:

    plain = workdir / "archive.tar"
    with open(archive, "rb") as source, open(plain, "wb") as sink:
        decrypt_stream(source, sink, key)

    with tarfile.open(plain) as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.name.startswith(("/", "..")) or ".." in Path(member.name).parts:
                raise ValueError(f"unsafe archive member: {member.name!r}")
        try:
            tar.extractall(workdir / "content", filter="data")
        except TypeError:  # Python < 3.11.4: no filters; members were validated above
            tar.extractall(workdir / "content")
    plain.unlink()

    content = workdir / "content"
    manifest = json.loads((content / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT:
        raise ValueError(f"unsupported backup format: {manifest.get('format')!r}")

    for name, meta in manifest["files"].items():
        path = content / name
        if not path.is_file() or sha256_file(path) != meta["sha256"]:
            raise ValueError(f"checksum mismatch: {name}")

    return manifest


def renamed(collection: str, source_prefix: str, target_prefix: str) -> str:

    if not collection.startswith(source_prefix + "_"):
        raise ValueError(f"collection {collection!r} does not use prefix {source_prefix!r}")
    return target_prefix + collection[len(source_prefix) :]


def list_dump(dump: Path, pg_container: str) -> int:
    """pg_restore --list parses the whole table of contents: a corrupt dump fails here."""

    if pg_container:
        command = ["docker", "exec", "-i", pg_container, "pg_restore", "--list"]
        with open(dump, "rb") as handle:
            result = subprocess.run(command, stdin=handle, capture_output=True)
    else:
        result = subprocess.run(["pg_restore", "--list", str(dump)], capture_output=True)
    if result.returncode != 0:
        raise ValueError("pg_restore --list failed: " + result.stderr.decode(errors="replace")[-500:])
    return sum(1 for line in result.stdout.decode().splitlines() if line and not line.startswith(";"))


def create_database(database_url: str, pg_container: str) -> None:

    name = database_name(database_url)
    admin = urllib.parse.urlparse(database_url)._replace(path="/postgres").geturl()
    command = pg_command("psql", admin, pg_container, "-v", "ON_ERROR_STOP=1", "-c", f'CREATE DATABASE "{name}"')
    result = subprocess.run(command, capture_output=True)
    if result.returncode != 0 and b"already exists" not in result.stderr:
        raise SystemExit("CREATE DATABASE failed: " + _safe(result.stderr.decode(errors="replace"), database_url))


def restore_postgres(dump: Path, database_url: str, pg_container: str) -> None:

    command = pg_command(
        "pg_restore",
        database_url,
        pg_container,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
        "--exit-on-error",
        "--single-transaction",
    )
    with open(dump, "rb") as handle:
        result = subprocess.run(command, stdin=handle, capture_output=True)
    if result.returncode != 0:
        raise SystemExit("pg_restore failed: " + _safe(result.stderr.decode(errors="replace"), database_url))


def upload_snapshot(qdrant: Qdrant, collection: str, snapshot: Path) -> None:

    boundary = uuid.uuid4().hex
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="snapshot"; filename="{snapshot.name}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    body = head + snapshot.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    qdrant.request(
        "POST",
        f"/collections/{collection}/snapshots/upload?priority=snapshot&wait=true",
        body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=3600,
    )


def parse_args(argv=None):

    env = os.environ
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="decrypt and verify only; change nothing")
    parser.add_argument("--database-url", default=env.get("BACKUP_DATABASE_URL") or env.get("DATABASE_URL", ""))
    parser.add_argument("--create-database", action="store_true", help="CREATE DATABASE first (scratch restores)")
    parser.add_argument("--pg-container", default="")
    parser.add_argument(
        "--qdrant-url",
        default=env.get("QDRANT_URL")
        or f"http://{env.get('QDRANT_HOST', 'localhost')}:{env.get('QDRANT_PORT', '6333')}",
    )
    parser.add_argument("--qdrant-api-key", default=env.get("QDRANT_API_KEY", ""))
    parser.add_argument("--target-prefix", default="", help="collection prefix to restore into (default: the backup's)")
    parser.add_argument("--yes", action="store_true", help="required to overwrite the live database/collections")
    return parser.parse_args(argv)


def main(argv=None) -> int:

    args = parse_args(argv)
    key = os.environ.get("BACKUP_ENCRYPTION_KEY", "")
    started = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="cogniseek-restore-") as tmp:
        workdir = Path(tmp)
        manifest = extract(args.archive, workdir, key)
        content = workdir / "content"
        entries = list_dump(content / "postgres.dump", args.pg_container)

        print(
            f"backup {args.archive.name}: created {manifest['created_at']}, database {manifest['database']!r}, "
            f"{entries} dump entries, checksums OK"
        )
        for name, meta in manifest["collections"].items():
            print(f"  {name}: {meta['points']} points")

        if args.dry_run:
            print(f"dry run: nothing restored ({time.monotonic() - started:.1f}s)")
            return 0

        target_prefix = args.target_prefix or manifest["prefix"]
        live = target_prefix == manifest["prefix"] or database_name(args.database_url) == manifest["database"]
        if live and not args.yes:
            raise SystemExit(
                "This overwrites the live database/collections. Re-run with --yes "
                "(or use --target-prefix and a scratch --database-url)."
            )

        if args.create_database:
            create_database(args.database_url, args.pg_container)
        restore_postgres(content / "postgres.dump", args.database_url, args.pg_container)
        print(f"postgres restored into {database_name(args.database_url)!r}")

        qdrant = Qdrant(args.qdrant_url, args.qdrant_api_key)
        for name, meta in manifest["collections"].items():
            target = renamed(name, manifest["prefix"], target_prefix)
            upload_snapshot(qdrant, target, content / "qdrant" / f"{name}.snapshot")
            restored = qdrant.count(target)
            status = "OK" if restored == meta["points"] else "MISMATCH"
            print(f"  {target}: {restored} points ({status})")
            if restored != meta["points"]:
                raise SystemExit(f"point count mismatch in {target}")

    print(f"restore complete ({time.monotonic() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
