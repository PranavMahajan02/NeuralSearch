# Indexing performance (Phase 7A.5)

**Goal:** a faster first index with no loss of search quality. Method: measure first,
fix the biggest bottlenecks the profile shows, prove the speed-up and prove
equivalence. Raw data: `docs/perf/*.json` (`scripts/bench_indexing.py`,
`scripts/compare_bench.py`, `scripts/compare_eval.py`).

## Summary (for an interview)

> I profiled our indexing pipeline before changing anything. One stage, OCR on scanned
> PDF pages, took 61% of the time, while the GPU sat idle 86% of the time. So I moved
> OCR to the GPU, made video frame extraction seek to each sampled frame instead of
> decoding every frame, had Whisper read video audio directly, and processed four files
> at once so CPU work overlaps GPU work. A fixed set of 69 files now indexes in
> **93 s instead of 347 s (3.7× faster)**. Half of the files are searchable after
> **31 s instead of 191 s (6×)**, because small documents now go first. On our full
> 164-file corpus with an hour of video: **817 s → 239 s**. I re-ran the search
> evaluation on indexes built before and after: no query got worse and one improved.
> Every chunk count and frame count is identical. I also measured and rejected three
> ideas that looked good on paper, including one that made it slower.

## Setup

- **Machine:** Intel 12th-gen laptop CPU (8 cores / 12 threads), NVIDIA RTX 3050 Laptop
  GPU (4 GB), Windows 11. Postgres and Qdrant run in Docker on the same machine.
- **Benchmark set:** 69 files, 211 MB, 7.8 audio-minutes, 15.7 video-minutes
  ([benchmark-set.md](benchmark-set.md)).
- **Path under test:** the real worker path (`IndexingWorker.run_once` → `LocalPlatform`
  → pipeline), with a throwaway user, a scratch database and a scratch Qdrant prefix.
- **Measurement:** models are loaded and warmed before the clock starts. Each run uses
  a fresh user, so every file is indexed.
- **Medians:** baseline is the median of 2 runs. "After" is the median of 3 interleaved
  rounds (`docs/perf/ab/`).

## Before → after (benchmark set, 69 files)

| | Baseline | After, default install (CPU OCR) | **After, GPU OCR** |
|---|---|---|---|
| Total wall time | 347.1 s | 291.9 s (1.2×) | **92.8 s (3.7×)** |
| 50% of files searchable after | 191.3 s | 69.3 s (2.8×) | **31.1 s (6.2×)** |
| 100% searchable after | 347.0 s | 291.8 s | **92.8 s** |
| GPU busy (share of 1 s samples > 10%) | 14% | 16% | 55% |
| CPU mean | 71% | 89% | 41% |
| Peak RSS (bench process) | 3.2 GB | 4.8 GB | 3.4 GB |
| Peak VRAM (torch, this process) | 827 MB | 866 MB | 863 MB (+482 MB Paddle) |
| Peak GPU memory used (whole GPU, incl. the owner's running server) | 2.35 GB | 2.46 GB | 2.28–3.09 GB |
| Peak temp dir | 11.3 MB | 11.3 MB | 11.3 MB |

"GPU OCR" means the CUDA build of Paddle is installed (opt-in, `requirements-gpu.txt`).
`OCR_DEVICE=auto` picks the GPU when it is present. Everything else in this phase is
on by default.

**Full corpus** (the owner's `data/` copy, 164 files, about 61 video-minutes; used for
the quality check): baseline 817 s → CPU OCR 573 s → **GPU OCR 239 s (3.4×)**. Half
searchable at 294 s → 140 s → **53 s**.

### Per stage (sequential run, so each stage's time is its own)

The parallel run overlaps stages, so its per-stage seconds include contention. The
clean comparison uses the GPU-OCR build with `INDEX_IO_WORKERS=1`.

| Stage | Baseline | After | Change | Why |
|---|---|---|---|---|
| OCR | 212.4 s | 27.1 s | −87% | GPU PaddleOCR |
| Video frame extraction | 35.9 s | 6.7 s | −81% | seek per sampled frame |
| Whisper | 31.3 s | 31.3 s | 0% | already VAD + fp16; batched rejected (below) |
| Text extraction | 23.1 s | 25.6 s | +11% | unchanged code (noise) |
| PDF page rendering | 18.7 s | 13.7 s | −27% | one Poppler call per page run |
| CLIP image / frame embeddings | 9.2 s | 6.5 s | −30% | frames batched 32 at a time |
| MiniLM text embeddings | 6.0 s | 3.2 s | −46% | GPU less contended |
| Audio export from video (moviepy WAV) | 5.9 s | 0 s | −100% | Whisper decodes the video directly |
| Qdrant upsert | 2.8 s | 3.2 s | | |
| Ledger | 0.9 s | 0.9 s | | |
| **Total (sequential)** | **347.1 s** | **119.0 s** | **2.9×** | the parallel pipeline brings it to 92.8 s |

### Throughput (sequential, GPU OCR)

| Type | Baseline | After |
|---|---|---|
| Documents | 10.5 files/min | 37.6 files/min |
| Images | 65.9 files/min | 271.8 files/min |
| Audio | 42.3 audio-min/min | 46.8 audio-min/min |
| Video | 13.4 video-min/min | 28.0 video-min/min |

## What was done, and the evidence

| # | Change | Micro-benchmark (same inputs) | Output check |
|---|---|---|---|
| A | **Stage timing**: self-time spans per stage and file type, stored on the job (`stage_timings`) and shown in the Indexing Center ("Where the time went"). Waiting for a model another thread is using is its own stage (`model_wait`). | 3 µs per span (measured, 200k spans); about 800 spans per benchmark run = 2.4 ms | — |
| B1 | **Video frames**: OpenCV seeks to each sampled frame number `k·int(fps·5)` instead of decoding every frame | Forest Bathing 16.1 s → 2.45 s; Raj Shamani 17.9 s → 3.7 s | pixel-identical frames (max diff 0.00), same frame numbers → same timestamps |
| B2b | **GPU OCR** (Paddle 2.6.2 CUDA + cuDNN 8 next to torch's CUDA 12 DLLs; torch-before-paddle import order kept) | 37 OCR inputs: 72.0 s → 9.3 s | 30/37 identical, rest ≥ 0.947 similar; eval: no regression, 1 query better |
| B2c | **PDF pages rendered in runs** (one pdftoppm call per contiguous run, up to 4 processes) | 20 pages: 3.5 s → 2.0 s | identical pixels; identical text on all 5 scanned PDFs |
| B3 | **Whisper reads video audio directly** (PyAV), no moviepy WAV export | Forest 5.0 s → 3.1 s; Raj 18.2 s → 15.6 s | transcript similarity 1.000 / 0.989 (Whisper itself varies about 4% between identical runs) |
| B4 | **Parallel pipeline**: 4 files at once (`INDEX_IO_WORKERS`), at most 8 in flight (`INDEX_PREFETCH`); per-model locks; a shared cool-down gate for 429 / rate limits | sequential 121.6 s → parallel 92.8 s (−24%) | cancel / error isolation / ordering tested |
| B5 | **CLIP frames batched** (32 per forward pass) | 55 frames: 1.92 s → 1.14 s | cosine ≥ 0.99997 |
| B6 | **Smallest-first schedule**: documents → images → audio → video, then by size | 50% searchable 191 s → 31 s | same files indexed |

## Tried and rejected (with numbers)

| Idea | Result | Decision |
|---|---|---|
| Paddle MKLDNN on CPU | 72.0 s vs 73.1 s on the 37 OCR inputs | No gain; dropped |
| ffmpeg CLI per frame (`-ss` before `-i`) | 7.4 s / 12.0 s vs OpenCV seek 2.45 s / 3.7 s; small pixel differences | Slower (one process per frame), not identical |
| Hardware decode (`-hwaccel auto`) | 29.1 s / 61.9 s | Much slower (device init per process) |
| Image OCR pre-check (skip text-free images) | PaddleOCR already runs detection first and recognition only on detected boxes. Text-free images cost 0.35 s each, about 5 s of 347 s (1.4%) | No room left for a cheaper check to save time, and any heuristic risks false negatives |
| Batched Whisper (`BatchedInferencePipeline`, batch 8) | 3× faster in isolation, but the full corpus took **323 s vs 239 s**: it competes for the 4 GB GPU. Transcript similarity 0.89–0.96 | Off (`WHISPER_BATCH_SIZE=0`); kept as an option |
| One lock for all GPU work (`GPU_SERIALIZE`) | 115.1 s vs 92.8 s with per-model locks (3 interleaved rounds) | Off: different models overlapping on the GPU is faster |
| Swapping pdfplumber for a faster PDF library | text extraction is 7% of the time; a different library changes the extracted text and so the embeddings | Not worth the quality risk; the parallel pipeline overlaps it instead |
| Cross-file MiniLM batching | MiniLM is 6 s (1.7%) and already batched per file | Not significant |

## Quality: proven equivalent

**Search eval.** The full corpus was indexed three times into separate scratch indexes:
the baseline code (commit `67f1285`), the new code with CPU OCR, and the new code with
GPU OCR. Then `tests/eval/queries.yaml` was run against each (83 queries) and compared
with `scripts/compare_eval.py`. Code queries are GitHub-only, so they score 0 in all
three and are unaffected by extraction.

| Subset | Baseline P@5 / MRR | After (CPU OCR) | After (GPU OCR) |
|---|---|---|---|
| Non-visual | 0.703 / 0.703 | 0.703 / 0.703 | 0.703 / **0.725** |
| Visual-only images | 0.719 / 0.677 | same | same |
| Visual-video | 0.111 / 0.083 | same | same |
| Negatives (false positives) | 2 | 2 | 2 |
| Possible tier recovered (video / image) | 1/16, 4/8 | same | same |

- **CPU OCR:** 0 of 83 queries changed rank or top-5.
- **GPU OCR:** 1 query changed: "Find my government documents" went from rank 2 to 1.
- **Guardrail** (no subset regresses, no rank drops by more than 1): **PASS** for both.

**Per-file outputs.** These are chunk counts, extracted text, OCR and transcript
lengths, and frame counts for all 164 corpus files.
- **No difference above 5%.** Chunk counts and frame counts are identical for every file.
- **CPU OCR:** 4 transcripts differ by under 0.6% (Whisper variance; the direct decode
  skips a resample).
- **GPU OCR:** 13 files differ by at most 18 characters (GPU vs CPU recognition, and
  the same transcripts).
- **Benchmark set:** the only difference above 5% is `pdf_extract.py`. That is one of
  the four repository source files used as code samples, and it was itself edited in
  this phase. The input changed, not the extraction.

## Resources

- **Memory and disk are bounded.** Peak temp disk is unchanged, peak VRAM stays under
  900 MB for torch (+482 MB for GPU Paddle), and peak RSS is 3.4 GB.
- **The CPU-OCR parallel run peaks higher (4.8 GB RSS):** four CPU Paddle/pdfplumber
  workers at once. Lower `INDEX_IO_WORKERS` on small machines.
- **The in-flight bound is the worker count.** Each in-flight file holds at most its
  own download and frame folder, deleted when the file is done. Large videos sit at the
  end of the schedule, so at most four are ever open at once.

## Docker (CPU image)

`scripts/bench_indexing.py` was run inside the rebuilt `cogniseek-backend:cpu` image, where
every model runs on the CPU (CPU torch, CPU Paddle). On the same 69 files: **333 s, 69/69 files
indexed, half searchable after 69 s**. ffmpeg (PyAV), Poppler and PaddleOCR all work in the
container (`docs/perf/docker-cpu.json`).

This run found a pre-existing image bug. The Linux lock had resolved PyAV 19, which removed
an argument faster-whisper 1.2.1 passes. Every audio and video transcription failed in the
container (6 of 69 files). PyAV is now pinned to 17.1.0, the same as the Windows dev venv,
with a test.
