# Phase 6C — video frames as evidence (visual-only video search)

Measured 2026-10-07 on the owner's index (5 videos, 618 frames; one frame every 5 s).
Ground truth: 18 visual-only queries written from contact sheets of the videos; no content
word of a query occurs in its video's file name or indexed transcript (checked automatically).
Negatives: every visual-video query against the *other* videos, plus every negative/image/
document/code eval query against all videos: 367 (query, video) pairs.

## Why not the raw max frame margin

The best frame of a video is the max of N noisy frame margins, so it grows with the number of
frames and with how generic the footage is (interviews, stock shots). The negatives' median
max-margin differs by video: 162-frame space documentary 0.0051, 133-frame podcast −0.0204.

| statistic | positives median | negatives p99 / max | recall at 0 negatives passing |
|---|---|---|---|
| max frame margin | 0.0477 | 0.0512 / 0.0603 | 0.44 (thr 0.060) |
| mean of top-3 frame margins | 0.0299 | 0.0362 / 0.0531 | 0.17 (thr 0.062) |
| **max margin vs the video's own null (z)** | **5.03** | **4.44 / 5.27** | **0.50 (thr 5.3)** |

**Chosen: z = (best-frame margin − null_mean) / null_std ≥ 5.3**, where the null is the best-frame
margin of 12 unrelated prompts (bicycle, sandwich, guitar, …) over *all* the video's frames
(`app/search/frame_null.py`). It removes both the frame-count bias and the per-video baseline.
The null depends only on the video: computed at index time and stored on every frame point
(`scripts/backfill_video_null.py` filled it for the 7 existing videos).

The top "negatives" include label noise (there *is* an elephant in the baby-animals video,
z 4.86); the highest true negative is "aadhaar government id" → the India documentary, z 5.27.

## Eval (`20261007-221505-video-before.json` → `20261007-222029-video-after.json`)

| subset | before P@5 / MRR / FP | after P@5 / MRR / FP |
|---|---|---|
| visual-video | 0.000 / 0.000 / 0 | **0.500 / 0.500 / 0** |
| non-visual | 0.935 / 0.935 / 0 | 0.935 / 0.935 / 0 |
| visual-only (images) | 0.719 / 0.740 / 1 | 0.719 / 0.740 / 1 |

Found now (all rank 1): polar bear cubs in the snow, chimpanzee in a tree, meerkat, sea lion pups on
rocks, swans on a pond, podcast studio with microphones, grey haired woman, sepia archive footage,
leaders shaking hands. Still below the threshold: penguins (z 3.85), misty valley (4.55), lake
reflecting mountains, glass skyscrapers, cheering audience in the dark, welding workshop,
laboratory clean room, postage stamp, mushroom cloud explosion. "river" ranks the right video
first at z 3.49 (a background stream in two frames); "waterfall" has no matching frame (z 0.98).
