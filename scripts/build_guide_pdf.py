"""Render docs/PROJECT_GUIDE.md to docs/CogniSeek_Project_Guide.pdf.

    pip install markdown            # once (a docs-only tool, not an app dependency)
    python scripts/build_guide_pdf.py [--browser "C:/Program Files/Google/Chrome/Application/chrome.exe"]

Markdown -> a styled, self-contained HTML file -> headless Chrome/Edge
--print-to-pdf. No network access is needed.
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "PROJECT_GUIDE.md"
TARGET = ROOT / "docs" / "CogniSeek_Project_Guide.pdf"

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome",
    "chromium",
    "chromium-browser",
]

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1f2937; }
h1 { font-size: 22pt; color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 4px; }
h2 { font-size: 15pt; color: #1e3a8a; margin-top: 22px; break-after: avoid; }
h3 { font-size: 12pt; color: #374151; break-after: avoid; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9pt; background: #f3f4f6; padding: 1px 3px; border-radius: 3px; }
pre { background: #f3f4f6; padding: 8px 10px; border-radius: 4px; font-size: 8pt; line-height: 1.25; overflow: hidden; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8pt; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9pt; break-inside: avoid; }
th, td { border: 1px solid #d1d5db; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #eef2ff; }
blockquote { border-left: 4px solid #93c5fd; margin: 8px 0; padding: 4px 12px; background: #eff6ff; color: #1e3a8a; }
hr { border: none; border-top: 1px solid #e5e7eb; margin: 18px 0; }
"""


LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s")


def separate_lists(text: str) -> str:
    """Python-Markdown (unlike GitHub) needs a blank line before a list that
    follows a paragraph line; add it, outside code blocks."""

    out, fenced, previous = [], False, ""
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if (
            not fenced
            and LIST_ITEM.match(line)
            and previous.strip()
            and not LIST_ITEM.match(previous)
            and not previous.startswith((" ", "\t", "|", ">"))
        ):
            out.append("")
        out.append(line)
        previous = line
    return "\n".join(out)


def browser(explicit):
    for candidate in [explicit] if explicit else CANDIDATES:
        if candidate and (Path(candidate).exists() or shutil.which(candidate)):
            return candidate
    raise SystemExit("Chrome/Edge not found; pass --browser PATH")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--browser")
    args = parser.parse_args()

    try:
        import markdown
    except ImportError:
        raise SystemExit("pip install markdown") from None

    body = markdown.markdown(
        separate_lists(SOURCE.read_text(encoding="utf-8")), extensions=["tables", "fenced_code", "sane_lists"]
    )
    html = f'<!doctype html><html><head><meta charset="utf-8"><title>CogniSeek AI: Project Guide</title><style>{CSS}</style></head><body>{body}</body></html>'

    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "guide.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run(
            [
                browser(args.browser),
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={TARGET}",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )

    print(f"wrote {TARGET.relative_to(ROOT)} ({TARGET.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
