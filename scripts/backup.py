"""Encrypted backup of Postgres + every Qdrant collection of this deployment.

Docker deployment (the "backup" tools service has pg_dump matching the server
and sits on the internal network):

    docker compose run --rm backup                 # -> ./backups/cogniseek-<UTC>.tar.enc

Development (services on localhost; Postgres in a container without pg_dump on PATH):

    python scripts/backup.py --pg-container cogniseek-postgres --qdrant-url http://localhost:6333

The archive is a tar (postgres.dump in pg_dump custom format, one Qdrant snapshot
per collection, manifest.json with SHA-256 checksums) encrypted with
BACKUP_ENCRYPTION_KEY (Fernet, AES-128-CBC + HMAC-SHA256) in authenticated 8 MiB
chunks, so a truncated, reordered or modified file is rejected on restore.
Restore with scripts/restore.py (use --dry-run first). Secrets are never printed.
"""

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


MAGIC = b"COGNISEEK-BACKUP-1\n"
CHUNK = 8 * 1024 * 1024
FORMAT = "cogniseek-backup-v1"


# ---------------------------------------------------------------------------
# Encryption: framed Fernet chunks. Each plaintext chunk is prefixed with its
# index and a "last" flag, so chunks cannot be dropped, reordered or truncated.
# ---------------------------------------------------------------------------

def _fernet(key: str):

    from cryptography.fernet import Fernet

    if not key:
        raise SystemExit("BACKUP_ENCRYPTION_KEY is not set (python scripts/generate_secrets.py).")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError):
        raise SystemExit("BACKUP_ENCRYPTION_KEY is not a valid Fernet key.") from None


def encrypt_stream(source, target, key: str) -> None:

    fernet = _fernet(key)
    target.write(MAGIC)
    index = 0
    chunk = source.read(CHUNK)

    while True:
        following = source.read(CHUNK)
        last = not following
        token = fernet.encrypt(struct.pack(">QB", index, 1 if last else 0) + chunk)
        target.write(struct.pack(">I", len(token)) + token)
        if last:
            return
        chunk, index = following, index + 1


def decrypt_stream(source, target, key: str) -> None:

    from cryptography.fernet import InvalidToken

    fernet = _fernet(key)
    if source.read(len(MAGIC)) != MAGIC:
        raise ValueError("not a CogniSeek backup (bad header)")

    expected = 0
    while True:
        size = source.read(4)
        if len(size) < 4:
            raise ValueError("backup is truncated")
        token = source.read(struct.unpack(">I", size)[0])
        try:
            plain = fernet.decrypt(token)
        except InvalidToken:
            raise ValueError("wrong BACKUP_ENCRYPTION_KEY or corrupted backup") from None
        index, last = struct.unpack(">QB", plain[:9])
        if index != expected:
            raise ValueError("backup chunks are out of order")
        target.write(plain[9:])
        if last:
            if source.read(1):
                raise ValueError("unexpected data after the last chunk")
            return
        expected += 1


def sha256_file(path: Path) -> str:

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Postgres
# ---------------------------------------------------------------------------

def pg_command(tool: str, database_url: str, pg_container: str, *args: str) -> list:
    """pg_dump/pg_restore/psql, locally or through `docker exec` (the URL then
    refers to the container's own view, e.g. postgresql://user:pw@localhost/db)."""

    if pg_container:
        return ["docker", "exec", "-i", pg_container, tool, "--dbname", database_url, *args]
    return [tool, "--dbname", database_url, *args]


def dump_postgres(database_url: str, pg_container: str, target: Path) -> None:

    command = pg_command("pg_dump", database_url, pg_container, "--format=custom", "--no-owner", "--no-acl")
    with open(target, "wb") as handle:
        result = subprocess.run(command, stdout=handle, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise SystemExit("pg_dump failed: " + _safe(result.stderr.decode(errors="replace"), database_url))


def _safe(text: str, *secrets_: str) -> str:

    for secret in secrets_:
        if secret:
            text = text.replace(secret, "<redacted>")
    return text.strip()[-800:]


# ---------------------------------------------------------------------------
# Qdrant (HTTP API; stdlib only)
# ---------------------------------------------------------------------------

class Qdrant:

    def __init__(self, url: str, api_key: str = ""):

        self.url = url.rstrip("/")
        self.api_key = api_key

    def request(self, method: str, path: str, body=None, raw: bool = False, headers=None, timeout=600):

        request = urllib.request.Request(self.url + path, data=body, method=method, headers=dict(headers or {}))
        if self.api_key:
            request.add_header("api-key", self.api_key)
        # urllib stores header names as "Content-type": ask has_header(), not `in`.
        if body is not None and not request.has_header("Content-type"):
            request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
        return data if raw else json.loads(data or b"{}")

    def collections(self, prefix: str) -> list:

        names = [c["name"] for c in self.request("GET", "/collections")["result"]["collections"]]
        return sorted(n for n in names if n.startswith(prefix + "_"))

    def count(self, name: str) -> int:

        body = json.dumps({"exact": True}).encode()
        return self.request("POST", f"/collections/{name}/points/count", body)["result"]["count"]

    def snapshot(self, name: str, target: Path) -> None:

        created = self.request("POST", f"/collections/{name}/snapshots?wait=true")["result"]["name"]
        quoted = urllib.parse.quote(created)
        try:
            request = urllib.request.Request(f"{self.url}/collections/{name}/snapshots/{quoted}")
            if self.api_key:
                request.add_header("api-key", self.api_key)
            with urllib.request.urlopen(request, timeout=3600) as response, open(target, "wb") as handle:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    handle.write(block)
        finally:
            # The snapshot lives on the Qdrant volume; the copy is in our archive now.
            self.request("DELETE", f"/collections/{name}/snapshots/{quoted}?wait=true")


# ---------------------------------------------------------------------------

def database_name(database_url: str) -> str:

    return urllib.parse.urlparse(database_url).path.lstrip("/")


def build_archive(args, workdir: Path) -> dict:

    manifest = {"format": FORMAT, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "database": database_name(args.database_url), "prefix": args.prefix, "files": {}, "collections": {}}

    started = time.monotonic()
    dump = workdir / "postgres.dump"
    dump_postgres(args.database_url, args.pg_container, dump)
    manifest["files"]["postgres.dump"] = {"sha256": sha256_file(dump), "bytes": dump.stat().st_size}
    print(f"postgres: {dump.stat().st_size / 1e6:.1f} MB ({time.monotonic() - started:.1f}s)")

    qdrant = Qdrant(args.qdrant_url, args.qdrant_api_key)
    (workdir / "qdrant").mkdir()
    for name in qdrant.collections(args.prefix):
        started = time.monotonic()
        points = qdrant.count(name)
        path = workdir / "qdrant" / f"{name}.snapshot"
        qdrant.snapshot(name, path)
        manifest["collections"][name] = {"points": points}
        manifest["files"][f"qdrant/{name}.snapshot"] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
        print(f"qdrant {name}: {points} points, {path.stat().st_size / 1e6:.1f} MB ({time.monotonic() - started:.1f}s)")

    (workdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def prune(out_dir: Path, keep: int) -> list:

    archives = sorted(out_dir.glob("cogniseek-*.tar.enc"))
    old = archives[:-keep] if keep > 0 else []
    for path in old:
        path.unlink()
    return old


def parse_args(argv=None):

    env = os.environ
    default_db = env.get("BACKUP_DATABASE_URL") or env.get("DATABASE_URL", "")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=env.get("BACKUP_DIR", "backups"))
    parser.add_argument("--database-url", default=default_db, help="default: $BACKUP_DATABASE_URL or $DATABASE_URL")
    parser.add_argument("--pg-container", default="", help="run pg_dump via `docker exec` in this container")
    parser.add_argument("--qdrant-url",
                        default=env.get("QDRANT_URL") or f"http://{env.get('QDRANT_HOST', 'localhost')}:{env.get('QDRANT_PORT', '6333')}")
    parser.add_argument("--qdrant-api-key", default=env.get("QDRANT_API_KEY", ""))
    parser.add_argument("--prefix", default=env.get("QDRANT_COLLECTION_PREFIX", "cogniseek_v2"))
    parser.add_argument("--keep", type=int, default=int(env.get("BACKUP_KEEP", "14")),
                        help="keep the newest N archives in --out-dir (0 = keep all)")
    return parser.parse_args(argv)


def main(argv=None) -> int:

    args = parse_args(argv)
    key = os.environ.get("BACKUP_ENCRYPTION_KEY", "")
    _fernet(key)   # fail fast, before any work
    if not args.database_url:
        raise SystemExit("No database URL (--database-url or DATABASE_URL).")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = out_dir / f"cogniseek-{stamp}.tar.enc"
    started = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="cogniseek-backup-") as tmp:
        workdir = Path(tmp)
        build_archive(args, workdir)

        plain = workdir.parent / f"{workdir.name}.tar"
        with tarfile.open(plain, "w") as tar:
            for path in sorted(workdir.rglob("*")):
                if path.is_file():
                    tar.add(path, arcname=path.relative_to(workdir).as_posix())
        try:
            partial = target.with_suffix(".partial")
            with open(plain, "rb") as source, open(partial, "wb") as sink:
                encrypt_stream(source, sink, key)
            partial.replace(target)
        finally:
            plain.unlink(missing_ok=True)

    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    removed = prune(out_dir, args.keep)
    print(f"backup written: {target} ({target.stat().st_size / 1e6:.1f} MB, {time.monotonic() - started:.1f}s)"
          + (f"; pruned {len(removed)} old archive(s)" if removed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
