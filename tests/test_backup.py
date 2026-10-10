"""Phase 7A-C8: backup archive format (encryption, integrity) and restore guards.

The full round trip against real Postgres/Qdrant runs in the Docker stack
(docs/DEPLOYMENT.md, "Backups"); these tests cover the parts that can fail silently.
"""

import importlib.util
import io
import json
import struct
import sys
import tarfile
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

backup = importlib.import_module("backup")
restore = importlib.import_module("restore")


@pytest.fixture
def key():

    return Fernet.generate_key().decode()


def roundtrip(data: bytes, key: str, decrypt_key: str | None = None) -> bytes:

    sealed = io.BytesIO()
    backup.encrypt_stream(io.BytesIO(data), sealed, key)
    opened = io.BytesIO()
    backup.decrypt_stream(io.BytesIO(sealed.getvalue()), opened, decrypt_key or key)
    return opened.getvalue()


@pytest.mark.parametrize("size", [0, 1, backup.CHUNK - 1, backup.CHUNK, 2 * backup.CHUNK + 5])
def test_encryption_roundtrips_any_size(key, size):

    data = bytes(range(256)) * (size // 256) + bytes(size % 256)
    assert roundtrip(data, key) == data


def test_the_archive_is_not_readable_without_the_key(key):

    sealed = io.BytesIO()
    backup.encrypt_stream(io.BytesIO(b"postgres secret rows"), sealed, key)

    assert b"postgres secret rows" not in sealed.getvalue()
    with pytest.raises(ValueError, match="wrong BACKUP_ENCRYPTION_KEY"):
        roundtrip(b"x", key, decrypt_key=Fernet.generate_key().decode())


def _chunks(blob: bytes):

    body, chunks = blob[len(backup.MAGIC):], []
    while body:
        size = struct.unpack(">I", body[:4])[0]
        chunks.append(body[:4 + size])
        body = body[4 + size:]
    return chunks


def test_truncation_reordering_and_tampering_are_detected(key, monkeypatch):

    monkeypatch.setattr(backup, "CHUNK", 4)   # several chunks from a tiny input
    sealed = io.BytesIO()
    backup.encrypt_stream(io.BytesIO(b"abcdefghijkl"), sealed, key)
    chunks = _chunks(sealed.getvalue())
    assert len(chunks) == 3

    def opens(blob):
        backup.decrypt_stream(io.BytesIO(blob), io.BytesIO(), key)

    with pytest.raises(ValueError, match="truncated"):
        opens(backup.MAGIC + chunks[0] + chunks[1])          # last chunk dropped
    with pytest.raises(ValueError, match="out of order"):
        opens(backup.MAGIC + chunks[1] + chunks[0] + chunks[2])
    tampered = bytearray(sealed.getvalue())
    tampered[-10] ^= 1
    with pytest.raises(ValueError, match="corrupted"):
        opens(bytes(tampered))
    with pytest.raises(ValueError, match="bad header"):
        opens(b"PK\x03\x04" + sealed.getvalue())


def test_a_missing_or_invalid_key_stops_before_any_work():

    with pytest.raises(SystemExit, match="not set"):
        backup._fernet("")
    with pytest.raises(SystemExit, match="not a valid"):
        backup._fernet("abc")


def _archive(tmp_path, key, files, manifest_override=None):

    content = tmp_path / "content"
    content.mkdir()
    manifest = {"format": backup.FORMAT, "created_at": "2026-10-08T00:00:00+00:00", "database": "cogniseek",
                "prefix": "cogniseek_v2", "files": {}, "collections": {}}
    for name, data in files.items():
        (content / name).parent.mkdir(parents=True, exist_ok=True)
        (content / name).write_bytes(data)
        manifest["files"][name] = {"sha256": backup.sha256_file(content / name), "bytes": len(data)}
    manifest.update(manifest_override or {})
    (content / "manifest.json").write_text(json.dumps(manifest))

    plain = tmp_path / "a.tar"
    with tarfile.open(plain, "w") as tar:
        for path in content.rglob("*"):
            if path.is_file():
                tar.add(path, arcname=path.relative_to(content).as_posix())
    sealed = tmp_path / "a.tar.enc"
    with open(plain, "rb") as source, open(sealed, "wb") as sink:
        backup.encrypt_stream(source, sink, key)
    return sealed


def test_restore_verifies_every_checksum(tmp_path, key):

    sealed = _archive(tmp_path, key, {"postgres.dump": b"PGDMP", "qdrant/x.snapshot": b"snap"})
    out = tmp_path / "out"
    out.mkdir()
    assert restore.extract(sealed, out, key)["prefix"] == "cogniseek_v2"

    (tmp_path / "b").mkdir()
    bad = _archive(tmp_path / "b", key, {"postgres.dump": b"PGDMP"},
                   {"files": {"postgres.dump": {"sha256": "0" * 64, "bytes": 5}}})
    out2 = tmp_path / "out2"
    out2.mkdir()
    with pytest.raises(ValueError, match="checksum mismatch"):
        restore.extract(bad, out2, key)


def test_restore_renames_collections_to_the_target_prefix():

    assert restore.renamed("cogniseek_v2_video_frames", "cogniseek_v2", "restorecheck") == "restorecheck_video_frames"
    with pytest.raises(ValueError):
        restore.renamed("other_text", "cogniseek_v2", "x")


def test_restoring_onto_live_names_needs_yes(tmp_path, key, monkeypatch):

    sealed = _archive(tmp_path, key, {"postgres.dump": b"PGDMP"})
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", key)
    monkeypatch.setattr(restore, "list_dump", lambda *a: 3)
    monkeypatch.setattr(restore, "restore_postgres", lambda *a: pytest.fail("must not restore"))

    with pytest.raises(SystemExit, match="--yes"):
        restore.main([str(sealed), "--database-url", "postgresql://u:p@h/cogniseek"])

    assert restore.main([str(sealed), "--dry-run", "--database-url", "postgresql://u:p@h/cogniseek"]) == 0


def test_secrets_never_reach_error_messages():

    url = "postgresql://postgres:s3cretpw@postgres:5432/cogniseek"
    assert "s3cretpw" not in backup._safe(f'connection to "{url}" failed', url)


def test_prune_keeps_the_newest(tmp_path):

    for stamp in ("20260101T000000Z", "20260102T000000Z", "20260103T000000Z"):
        (tmp_path / f"cogniseek-{stamp}.tar.enc").write_bytes(b"x")

    removed = backup.prune(tmp_path, keep=2)

    assert [p.name for p in removed] == ["cogniseek-20260101T000000Z.tar.enc"]
    assert len(list(tmp_path.glob("*.tar.enc"))) == 2


def test_snapshot_upload_keeps_its_multipart_content_type(monkeypatch, tmp_path):

    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b'{"result": true}'

    def fake_urlopen(request, timeout):
        seen["content_type"] = request.get_header("Content-type")
        seen["api_key"] = request.get_header("Api-key")
        return Response()

    monkeypatch.setattr(backup.urllib.request, "urlopen", fake_urlopen)
    snapshot = tmp_path / "x.snapshot"
    snapshot.write_bytes(b"snap")

    restore.upload_snapshot(backup.Qdrant("http://qdrant:6333", "k"), "restorecheck_text", snapshot)

    assert seen["content_type"].startswith("multipart/form-data; boundary=")
    assert seen["api_key"] == "k"
