# Search evaluation

How search quality is measured, the current numbers, how they got there, and what they do
not prove.

## Method

**Query set:** [`tests/eval/queries.yaml`](../tests/eval/queries.yaml), 83 queries over the
owner's real data (local folders, Google Drive, GitHub). Each positive query lists the file
names that count as relevant; any listed file counts, and order does not matter. **Negative**
queries (12) must return nothing.

| Subset | Queries | What it tests |
|---|---|---|
| non-visual | documents and audio (names, topics, typos, punctuation, numbers, natural language) | text retrieval, filename search, transcripts |
| code | GitHub source files described in words | MiniLM on code |
| visual-only (images) | images whose file name shares **no** word with the query | CLIP visual evidence |
| visual-video | videos whose file name and transcript share no content word with the query | frame evidence |
| negatives | nonsense ("xqzv wplk qqq") and absent topics ("ferris wheel") | false positives |

**Harness:** [`scripts/eval_search.py`](../scripts/eval_search.py) runs every query through the
real `POST /search/` of a running backend as the owner (a token is minted in-process, never
printed). Results go to `docs/eval/<timestamp>-<label>.json`.

**Metrics:**

| Metric | Definition |
|---|---|
| precision@5 | relevant results in the top 5 / min(5, number of relevant files) |
| recall@10 | relevant results in the top 10 / number of relevant files |
| MRR | mean of 1 / rank of the first relevant result (0 if none) |
| negative false positives | results returned for negative queries |
| latency p50 / p95 | HTTP round trip per query, warm |
| possible tier | missed targets the low-confidence tier recovers, and its noise per query |

**Rule:** a ranking or extraction change is accepted only if **no subset regresses**. Since
Phase 7A.5, also **no single query's first-relevant rank may drop by more than 1**
([`scripts/compare_eval.py`](../scripts/compare_eval.py)).

The harness excludes this repository's own eval/test files when they come back through the
GitHub connector, because they contain every query verbatim (`--include-self` keeps them).

## Current numbers (owner's index, latest run `20261008-215156-possible-tier.json`)

| Subset | precision@5 | MRR | negative false positives |
|---|---|---|---|
| non-visual | **0.935** | 0.935 | 0 |
| visual-only images | **0.719** | 0.740 | 1 |
| visual-video | **0.500** | 0.500 | 0 |
| code | 0.357 | 0.191 | 0 |
| all 83 queries | 0.662 | 0.634 | 1 query with results (of 12) |

- **Latency:** p50 0.18 s, p95 0.21 s (warm, local machine).
- **Possible tier:** recovers 2 of 9 missed visual-video targets and 4 of 8 missed image targets,
  with 0.53 non-matching items per query on average (max 3, the cap).
- The remaining image false positive is "elephant" → a Java document whose text mentions
  elephants: a true content match that the eval labels wrong.

## History

| Run | Change | Queries | P@5 (all) | Negatives FP | Notes |
|---|---|---|---|---|---|
| `20261005-102023-baseline` | Phase 4 start | 39 | 0.858 | **61** | every negative returned junk; p50 0.31 s |
| `20261005-103512-after` | hybrid retrieval + calibrated text gate | 39 | 0.903 | 1 | p50 0.20 s |
| `20261005-211322-phase5` | connectors, OCR for scanned PDFs | 40 | 0.906 | 1 | |
| `20261006-214949-visual-before` | added visual-only image queries | 48 | 0.500 | 1 | visual-only P@5 **0.062**: image search only worked through file names |
| `20261006-215737-visual-after` | CLIP margin gate 0.030 | 48 | 0.846 | 1 | visual-only P@5 **0.719** |
| `20261007-125840/125925-code-*` | code semantic gate 0.52 | 62 | 0.717 | 4 → 1 | "kubernetes helm chart" 3 junk results → 0 |
| `20261007-221505-video-before` | added visual-video queries | 83 | 0.535 | 1 | visual-video P@5 **0.000** |
| `20261007-222029-video-after` | frames as evidence (per-video null, z ≥ 5.3) | 83 | 0.662 | 1 | visual-video P@5 **0.500** |
| `20261008-215156-possible-tier` | low-confidence tier | 83 | 0.662 | 1 | main metrics unchanged by design |
| `20261009-*-perf-*` | Phase 7A.5 quality check | 83 | 0.418 | 2 | scratch index from a copy of `data/` (no Drive/GitHub): before = after |

The `perf-*` runs use a different corpus (local copies only), so compare them with each other,
not with the owner's index: they proved the 7A.5 speed-ups changed nothing (0/83 queries
changed on CPU OCR; 1 query improved with GPU OCR).

## Calibration methods

Raw similarities cannot be thresholded directly: CLIP gives almost every image–text pair a cosine
of about 0.2–0.3, and MiniLM scores depend on the query. Every threshold is a **margin**: the score
minus a query-specific baseline, measured on labelled data.

### Text margin (MiniLM)

- **Baseline:** the query's similarity to a fixed set of neutral prompts
  (`app/search/calibration.py`).
- **Signal:** the margin rises from 0.10 to full strength at 0.60.
- **Evidence:** a margin of **≥ 0.35** alone is enough to return a prose document
  (`TEXT_MARGIN_EVIDENCE`). Chosen in Phase 4 on the eval set: it took negatives from 61 junk
  results to 1, without losing the document queries.

### Code threshold

- **0.52** (`TEXT_MARGIN_EVIDENCE_CODE`), from [phase6-code-gate.md](eval/phase6-code-gate.md).
- Over 33 negative queries, 3,587 irrelevant code candidates reached a maximum margin of 0.502.
- The relevant code files' margins overlap heavily with that, because a MiniLM vector of code says
  little about what the code does.
- So code is returned on a file-name or content match. The semantic margin still adds to the score.

### CLIP image margin

- **0.030** (`IMAGE_MARGIN_EVIDENCE`), from [phase5-clip-gate.md](eval/phase5-clip-gate.md).
  The margin is the CLIP cosine minus the query's baseline over neutral prompts.
- It keeps 70% of the relevant images and lets 4 of 873 irrelevant images through (0.46%).
- **Document-photo rule:** images with **20 or more OCR words** need OCR or file-name evidence.
  Every text-like negative that passed the visual gate had at least 44 OCR words; every visual-eval
  image had at most 2.

### Per-video null for frames

- **z ≥ 5.3** (`VIDEO_FRAME_Z_EVIDENCE`), from [phase6c-video-gate.md](eval/phase6c-video-gate.md).
- **The problem:** a video's best-frame margin is the maximum over many noisy frames, so it rises
  with the frame count and with generic footage. A space documentary "looks like" everything.
- **The null:** the best-frame margin of **12 unrelated prompts** (bicycle, sandwich, guitar, …)
  over all of that video's frames. It is computed at index time and stored on every frame point.
- **The score:** a query's best frame becomes z = (margin − null mean) / null std, comparable
  across videos.
- **Result:** at 5.3, 50% recall with 0 false positives on 367 negative (query, video) pairs.
  The best raw-margin statistic managed 44%.

### Frame sampling

- One frame every 5 seconds.
- Sampling every 2 s was measured and rejected: 2.5× the frames and 2.4× the CLIP time, while
  "river" scored lower (z 3.49 → 3.12) because more frames also raise the video's own null.

## Possible-matches tier

A separate, labelled list of weaker visual matches:
- **Videos:** z between 3.0 and 5.3.
- **Images:** margin between 0.015 and 0.030.
- **Cap:** at most 3 items.

These items are never mixed into the results or the count. The floors were measured on all 86
eval queries ([phase6d-possible-tier.md](eval/phase6d-possible-tier.md)): video z 3.0 adds "river"
(z 3.495) and 2 of 18 targets at 0.27 noise items per query. Example: "river" shows the Forest
Bathing video as *Low confidence · frame at 0:20*.

## Limits (what these numbers do not prove)

- **Small and personal:**
  - 83 queries over one person's files, labelled by that person.
  - That's enough to catch regressions and calibrate thresholds, not to claim general
    retrieval quality.
- **Overfitting risk:**
  - The thresholds were fitted on the same data the eval measures.
  - The visual-only and visual-video subsets were added specifically to stop the eval
    overfitting to file names (the "dog returned nothing" bug), but there is no held-out test set.
- **Label noise:** e.g. there *is* an elephant in the baby-animals video, yet the eval counts it as a negative.
- **Exact-name relevance:** a result counts only if its file name is listed; a near-duplicate
  copy counts as wrong.
- **Visual recall is modest:**
  - About 70% of relevant images and 50% of visual-only video queries are found.
  - Short or background details are missed.
  - There is no query expansion ("government documents" does not find "Aadhaar").
