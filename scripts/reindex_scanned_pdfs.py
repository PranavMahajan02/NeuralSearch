"""Re-index the PDFs that the per-page OCR rule affects (Phase 5, D3).

    venv\\Scripts\\python scripts\\reindex_scanned_pdfs.py --email pranav2@gmail.com [--dry-run]

Candidates: the user's indexed PDFs with few chunks (<= --max-chunks), i.e. the
ones that are likely scans. For each, the file is fetched (local disk, or the
user's Google Drive), checked page by page with the new OCR rule, and
re-indexed only if at least one page triggers OCR. Prints counts only (no
document text: these are often ID documents).
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.database.db import SessionLocal  # noqa: E402
from app.database.models import IndexedFile, User  # noqa: E402
from app.services.index_store import FileMeta  # noqa: E402
from app.vectorstore.client import get_client  # noqa: E402
from app.vectorstore.config import collection_for_type  # noqa: E402
from app.vectorstore.query import user_filter  # noqa: E402


ALNUM = re.compile(r"[A-Za-z0-9]")


def stored_alnum(user_id, row) -> int:

    points, _ = get_client().scroll(
        collection_for_type("document"),
        scroll_filter=user_filter(user_id, row.platform, source_id=row.source_id),
        limit=200, with_payload=True, with_vectors=False
    )

    return sum(len(ALNUM.findall(p.payload.get("chunk", ""))) for p in points)


def ocr_pages(path: str):

    import pdfplumber

    from app.extractors.pdf_extract import image_coverage, ocr_reason

    with pdfplumber.open(path) as pdf:
        return [
            (number, reason)
            for number, page in enumerate(pdf.pages, start=1)
            for reason in [ocr_reason(page.extract_text() or "", image_coverage(page))]
            if reason
        ]


def meta_of(row) -> FileMeta:

    return FileMeta(
        user_id=str(row.user_id), platform=row.platform, source_id=row.source_id,
        file_name=row.file_name, display_path=row.display_path, file_type=row.file_type,
        version=row.version, owner=row.owner, repo=row.repo,
        default_branch=row.default_branch, web_view_link=row.web_view_link
    )


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--max-chunks", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == args.email).one()
        user_id = str(user.id)
        rows = (
            db.query(IndexedFile)
            .filter(IndexedFile.user_id == user.id, IndexedFile.status.in_(("indexed", "failed")),
                    IndexedFile.file_name.ilike("%.pdf"), IndexedFile.chunk_count <= args.max_chunks)
            .order_by(IndexedFile.platform, IndexedFile.file_name)
            .all()
        )
        for row in rows:
            db.expunge(row)

    drive = None

    print(f"{len(rows)} candidate PDFs (<= {args.max_chunks} chunks)")
    print(f"{'platform':12} {'file':48} {'ocr pages':22} {'alnum before':>12} {'after':>8}")

    from app.services.indexing_pipeline import index_source

    with tempfile.TemporaryDirectory(prefix="reindex-") as tmp:

        for row in rows:

            if row.platform == "local":
                path = row.display_path
                if not os.path.isfile(path):
                    print(f"{row.platform:12} {row.file_name[:48]:48} missing on disk")
                    continue

            elif row.platform == "google_drive":
                if drive is None:
                    from app.platforms.google_drive.drive_service import client_for_user
                    drive = client_for_user(user_id)
                path = drive.download({"id": row.source_id, "mimeType": "application/pdf"},
                                      Path(tmp) / f"{abs(hash(row.source_id))}.pdf")
            else:
                continue

            pages = ocr_pages(path)
            before = stored_alnum(user_id, row)

            if not pages:
                continue

            summary = ",".join(f"{n}:{reason}" for n, reason in pages[:3]) + ("..." if len(pages) > 3 else "")

            if args.dry_run:
                print(f"{row.platform:12} {row.file_name[:48]:48} {summary:22} {before:>12} {'(dry)':>8}")
                continue

            index_source(meta_of(row), path, temp_dir=tmp, force=True)
            after = stored_alnum(user_id, row)

            print(f"{row.platform:12} {row.file_name[:48]:48} {summary:22} {before:>12} {after:>8}")


if __name__ == "__main__":
    main()
