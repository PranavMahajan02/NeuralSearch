# Phase 5 — CLIP image gate calibration (bug #3)

Measured 2026-10-06 on the owner's index (`pranav2@gmail.com`), all image candidates of the
33 image queries in `tests/eval/queries.yaml` (16 visual-only, 3 visual negatives, the rest
image queries with name hits). Margin = CLIP cosine − neutral-prompt baseline.

| | n | min | p10 | median | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| relevant images | 27 | −0.021 | 0.012 | 0.044 | | | 0.112 |
| irrelevant images | 873 | | | −0.047 | −0.007 | 0.021 | 0.052 |

Best image for each visual negative (elephant, laptop keyboard, soccer ball): ≤ −0.003.

| threshold | relevant kept | irrelevant passing |
|---|---|---|
| 0.030 | 70% | 4 |
| 0.040 | 59% | 3 |
| 0.050 | 33% | 1 |
| 0.055 | 33% | 0 |

**Chosen: `IMAGE_MARGIN_EVIDENCE = 0.030`.** The old gate (z ≥ 4.4) rejected relevant
top images whose z ranged from 2.4 to 4.4. The z-score is now only a 25% share of the image
signal, used for ordering.

**Photos of documents.** On 10 text-like negative queries (tax form, invoice, timetable …),
every image above the margin threshold had ≥ 44 OCR words, and every visual-eval image had ≤ 2.
Images with ≥ 20 OCR words (`DOCUMENT_PHOTO_OCR_WORDS`) therefore need OCR or file-name
evidence; CLIP alone is not enough for them.

Runs: `20261006-214949-visual-before.json`, `20261006-215737-visual-after.json`.
