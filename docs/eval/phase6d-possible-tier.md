# Phase 6D — "Possible visual matches" tier and frame sampling rate

## Tier floors (measured before choosing; approved: video z 3.0, image margin 0.015, shared cap 3)

Real retrieval + ranking over all 86 eval queries (this repo's own files excluded); only candidates
that are *not* already results count. "Noise" = non-matching items the tier would show per query.

| video floor (z, below 5.3) | relevant video pairs added | noise per query avg / max |
|---|---|---|
| **3.0** | 2 of 18 (+ "river", z 3.495) | 0.27 / 2 |
| 3.5 | 2 of 18 (misses "river") | 0.13 / 1 |
| 4.0 | 1 of 18 | 0.10 / 1 |
| 4.5 | 1 of 18 | 0.05 / 1 |

| image floor (margin, below 0.030) | relevant image pairs added | noise per query avg / max |
|---|---|---|
| 0.010 | 6 of 21 | 0.41 / 3 |
| **0.015** | 4 of 21 | 0.27 / 3 |
| 0.020 | 2 of 21 | 0.18 / 2 |
| 0.025 | 1 of 21 | 0.06 / 2 |

Eval with the tier on (`20261008-215156-possible-tier.json`): the main metrics are unchanged (they are
computed on `results` only); the tier recovers 2 of 9 missed visual-video targets and 4 of 8 missed
visual-image targets, with 0.53 non-matching items per query on average (max 3, the cap).

## Frame sampling: 2 s vs 5 s (measured, not adopted)

Forest Bathing (4.6 min), re-extracted into a scratch Qdrant collection (deleted afterwards):

| | 5 s (kept) | 2 s |
|---|---|---|
| frames | 55 (12/min) | 138 (30/min) |
| frame extraction (decodes every frame) | 22.3 s | 20.3 s |
| CLIP embedding | 3.0 s | 7.2 s |
| "river" | z 3.49 (best frame 0:20) | **z 3.12** (same frame) |
| "a river flowing through a forest" | z 4.32 | z 4.29 |
| "waterfall" | z 0.98 | z 1.92 |

Denser sampling does not help: the best frame is already sampled at 5 s, while more frames also raise
the video's own null (more chances for an unrelated prompt to match), so z drops. Cost: 2.5× frames
and storage, 2.4× CLIP time.
