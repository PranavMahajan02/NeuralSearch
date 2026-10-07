# Phase 6 — semantic evidence threshold for code files (A1)

Measured 2026-10-07 on the owner's full index (`pranav2@gmail.com`, 879 GitHub files), MiniLM
text margin (cosine − neutral baseline) of code/config candidates (`CODE_EXTENSIONS`: the
DOCUMENTS set minus .pdf .docx .pptx .txt .md .markdown .csv). This repo's own eval/test files
are excluded (see `scripts/eval_search.py`).

| | n | values |
|---|---|---|
| target file of 14 descriptive code queries (no path word in the query) | 13 found | 0.017, 0.18–0.45, median ≈ 0.26 |
| irrelevant code candidates over 33 negative queries | 3587 | median 0.038, p95 0.191, p99 0.351, **max 0.502** |

| threshold | relevant (semantic-only) kept | irrelevant passing |
|---|---|---|
| 0.35 (old, shared with prose) | 3 / 13 | 38 |
| 0.45 | 1 / 13 | 6 |
| 0.50 | 0 / 13 | 1 |
| **0.52 (chosen)** | 0 / 13 | 0 |

The distributions overlap: a code chunk's MiniLM vector says little about what the code does.
**`TEXT_MARGIN_EVIDENCE_CODE = 0.52`** — above every irrelevant margin seen — so code files are
returned on a file-name or content match; the semantic margin still contributes to their score.
Prose documents keep 0.35.

| run | non-visual P@5 / MRR / FP | visual-only P@5 / MRR / FP | code P@5 / MRR |
|---|---|---|---|
| before (`20261007-125840-code-before.json`) | 0.935 / 0.935 / **3** | 0.719 / 0.740 / 1 | 0.357 / 0.226 |
| after (`20261007-125925-code-after.json`) | 0.935 / 0.935 / **0** | 0.719 / 0.740 / 1 | 0.357 / 0.191 |

Changed: "kubernetes helm chart deployment" 3 results → 0; "traffic jam forecast" rank 2 → not
found (its only evidence was a 0.379 semantic margin).
