"""One scoring model for every modality.

Each candidate source gets three normalized signals in [0, 1]:

  semantic  meaning match from the embeddings, calibrated (see calibration.py)
            - text (documents, audio, video transcripts): MiniLM margin
            - images: the absolute CLIP margin (cosine minus the neutral
              baseline); the z-score among this query's images only orders
              images, it never decides whether one is returned
            - video frames: a small boost only (frames alone are too noisy)
  name      the query terms found in the file name (exact, prefix, typo)
            or the pg_trgm file-name similarity
  content   the query terms found in the retrieved chunks
            (document text, OCR text, transcripts)

A candidate is returned only with real evidence: a strong semantic signal or
a lexical hit. The final score is a noisy-OR of the signals, so it stays in
[0, 1], rises with every independent piece of evidence, and is comparable
across modalities - which lets all results be merged into one sorted list.

The thresholds below were chosen on the evaluation set (tests/eval) and the
margin distributions measured on the owner's data; see docs/eval.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from rapidfuzz import fuzz

from app.config.file_types import CODE_EXTENSIONS
from app.search.normalize import normalize_name, normalize_text, query_terms, tokens


# ---- calibration constants (measured; see the Phase 4 report) -------------

# MiniLM margin: negatives peak at ~0.32, relevant documents reach 0.3-0.65.
TEXT_MARGIN_FLOOR = 0.10        # semantic signal starts here
TEXT_MARGIN_FULL = 0.60         # ... and saturates here
TEXT_MARGIN_EVIDENCE = 0.35     # alone enough to return a result
# Code/config files (Phase 6, docs/eval/phase6-code-gate.md): MiniLM separates
# them poorly. Irrelevant code candidates: p99 0.351, max 0.502 over 33
# negative queries; the target file of 14 descriptive code queries: 0.18-0.45.
# Set above the irrelevant max, so code files need a name or content match in
# practice; the semantic signal still ranks them.
TEXT_MARGIN_EVIDENCE_CODE = 0.52

# CLIP image margin (cosine - neutral baseline), measured on 33 image queries
# (Phase 5, docs/eval): relevant images median 0.044, p10 0.012; irrelevant
# images (n=873) median -0.047, p99 0.021; visual negatives' best <= -0.003.
# 0.030 keeps 70% of relevant images and passes 0.5% of irrelevant ones.
IMAGE_MARGIN_EVIDENCE = 0.030   # alone enough to return an image
IMAGE_MARGIN_FLOOR = 0.0
IMAGE_MARGIN_FULL = 0.10
# z-score among the query's images: ordering only (a small share of the signal).
IMAGE_Z_FLOOR = 1.0
IMAGE_Z_FULL = 5.0
IMAGE_Z_SHARE = 0.25
# Photos of documents (screenshots, scanned forms) match any text-like query in
# CLIP: on 10 text-like negative queries every image above the margin threshold
# had >= 44 OCR words, every visual-eval image <= 2. For these, CLIP alone is
# not evidence - they are found through their OCR text and file name.
DOCUMENT_PHOTO_OCR_WORDS = 20
_OCR_WORD = re.compile(r"[^\W\d_]{2,}", re.UNICODE)

# Video frames: weak boost only.
FRAME_MARGIN_FLOOR = 0.03
FRAME_MARGIN_FULL = 0.15
FRAME_WEIGHT = 0.5

# Video frames as evidence on their own (Phase 6C, docs/eval/phase6c-video-gate.md):
# z = (best-frame margin - the video's null mean) / null std. 18 visual-only video
# queries vs 367 negative (query, video) pairs: positives median 5.03, the
# negatives' max 5.27 -> 5.3 passes 9/18 positives and no negative.
VIDEO_FRAME_Z_EVIDENCE = 5.3

# "Possible visual matches" (a separate, low-confidence tier; never in results/total).
# Floors approved from docs/eval/phase6d-possible-tier.md: ~0.27 non-matching
# items per query for each tier, capped at POSSIBLE_LIMIT together.
POSSIBLE_VIDEO_Z_FLOOR = 3.0
POSSIBLE_IMAGE_MARGIN_FLOOR = 0.015
POSSIBLE_LIMIT = 3
VIDEO_FRAME_Z_FLOOR = 3.0
VIDEO_FRAME_Z_FULL = 9.0

# Lexical evidence.
NAME_EVIDENCE = 0.5             # half of the query terms in the file name
CONTENT_EVIDENCE = 0.6          # most of the query terms in the content
TRIGRAM_NAME_FLOOR = 0.6        # pg_trgm similarity counted as a name match

# Noisy-OR weights.
W_SEMANTIC = 0.80
W_NAME = 0.70
W_CONTENT = 0.50

MAX_CONTENT_CHUNKS = 8
SNIPPET_LENGTH = 200


@dataclass
class Scored:

    candidate: object
    score: float
    semantic: float
    name: float
    content: float
    reasons: List[str] = field(default_factory=list)
    match: Dict = field(default_factory=dict)


# ----------------------------------------------------------------------
# Lexical matching
# ----------------------------------------------------------------------

def term_match(term: str, word: str) -> float:
    """1.0 exact, 0.9 prefix (format/formatted), 0.85 typo (jva/java), else 0."""

    if term == word:
        return 1.0

    if term.isdigit() or word.isdigit():
        return 0.0                      # numbers must match exactly

    shorter, longer = sorted((term, word), key=len)

    if len(shorter) >= 5 and longer.startswith(shorter) and len(shorter) / len(longer) >= 0.6:
        return 0.9

    if len(term) >= 3 and abs(len(term) - len(word)) <= (1 if len(term) == 3 else 2):
        if fuzz.ratio(term, word) >= 85:
            return 0.85

    return 0.0


def coverage(terms: Sequence[str], words: Sequence[str], phrase: str, text: str) -> Tuple[float, List[str]]:
    """Share of query terms present in `words` (best match per term), and the
    words that matched. A contiguous phrase match counts as full coverage."""

    if not terms or not words:
        return 0.0, []

    vocabulary = set(words)
    total = 0.0
    matched = []

    for term in terms:
        best, best_word = 0.0, None
        if term in vocabulary:
            best, best_word = 1.0, term
        else:
            for word in vocabulary:
                score = term_match(term, word)
                if score > best:
                    best, best_word = score, word
        total += best
        if best_word:
            matched.append(best_word)

    score = total / len(terms)

    if len(terms) >= 2 and phrase and phrase in text:
        score = 1.0

    return score, matched


def _scale(value: Optional[float], floor: float, full: float) -> float:

    if value is None:
        return 0.0

    return float(min(1.0, max(0.0, (value - floor) / (full - floor))))


# ----------------------------------------------------------------------
# Snippets
# ----------------------------------------------------------------------

def _word_pattern(word: str) -> str:
    """Whole-word match where '_' and '-' count as separators (file names)."""

    return r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])"


def _highlights(snippet: str, words: Sequence[str]) -> List[List[int]]:

    spans = []
    lowered = snippet.lower()

    for word in set(words):
        for m in re.finditer(_word_pattern(word), lowered):
            spans.append([m.start(), m.end()])

    spans.sort()

    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    return merged


def make_snippet(text: str, words: Sequence[str]) -> Tuple[str, List[List[int]]]:
    """Up to 200 chars around the first matched word; highlight offsets."""

    clean = re.sub(r"\s+", " ", text or "").strip()

    if not clean:
        return "", []

    lowered = clean.lower()
    first = min(
        (m.start() for w in words for m in [re.search(_word_pattern(w), lowered)] if m),
        default=0
    )

    start = max(0, first - 60)
    snippet = clean[start:start + SNIPPET_LENGTH]

    return snippet, _highlights(snippet, words)


# ----------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------

CONTENT_FIELD = {"document": "content", "image": "ocr", "audio": "transcript", "video": "transcript"}


def image_zscores(candidates) -> Dict[Tuple[str, str], float]:
    """z-score of each image candidate's CLIP margin among this query's images."""

    images = [c for c in candidates if c.file_type == "image" and c.clip_margin is not None]

    if len(images) < 3:
        return {}

    values = np.asarray([c.clip_margin for c in images], dtype=np.float64)
    mean, std = values.mean(), values.std() or 1e-6

    return {c.key: float((c.clip_margin - mean) / std) for c in images}


def text_evidence_threshold(candidate) -> float:

    extension = os.path.splitext(candidate.file or "")[1].lower()

    return TEXT_MARGIN_EVIDENCE_CODE if extension in CODE_EXTENSIONS else TEXT_MARGIN_EVIDENCE


def name_for_matching(candidate) -> str:
    """The normalized file name; for repository files also the folders inside
    the repo ('extension/manifest.json' -> 'extension manifest'), which name a
    code file as much as its base name does."""

    name = normalize_name(candidate.file)

    if candidate.platform == "github" and ":" in (candidate.source_id or ""):
        folders = candidate.source_id.split(":", 1)[1].split("/")[:-1]
        name = " ".join([normalize_name(folder) for folder in folders] + [name]).strip()

    return name


def frame_z(candidate) -> Optional[float]:
    """Best retrieved frame vs this video's null distribution (None without frames or null)."""

    if candidate.clip_margin is None or candidate.frame_null_mean is None or not candidate.frame_null_std:
        return None

    return (candidate.clip_margin - candidate.frame_null_mean) / candidate.frame_null_std


def is_document_photo(candidate) -> bool:
    """An image whose OCR text is substantial (a photo of a page or screen)."""

    words = max((len(_OCR_WORD.findall(ch.text)) for ch in candidate.chunks if ch.kind == "image"), default=0)

    return words >= DOCUMENT_PHOTO_OCR_WORDS


def score_candidates(candidates, query: str) -> List[Scored]:

    phrase = normalize_text(query)
    terms = query_terms(query)

    zscores = image_zscores(candidates)
    results = []

    for c in candidates:

        # --- semantic -------------------------------------------------------
        semantic_text = _scale(c.text_margin, TEXT_MARGIN_FLOOR, TEXT_MARGIN_FULL)
        text_evidence = text_evidence_threshold(c)
        evidence = c.text_margin is not None and c.text_margin >= text_evidence
        semantic = semantic_text
        visual = False

        if c.file_type == "image":
            visual_signal = ((1 - IMAGE_Z_SHARE) * _scale(c.clip_margin, IMAGE_MARGIN_FLOOR, IMAGE_MARGIN_FULL)
                             + IMAGE_Z_SHARE * _scale(zscores.get(c.key), IMAGE_Z_FLOOR, IMAGE_Z_FULL))
            semantic = max(semantic, visual_signal)
            if (c.clip_margin is not None and c.clip_margin >= IMAGE_MARGIN_EVIDENCE
                    and not is_document_photo(c)):
                evidence = visual = True

        elif c.file_type == "video":
            frame = FRAME_WEIGHT * _scale(c.clip_margin, FRAME_MARGIN_FLOOR, FRAME_MARGIN_FULL)
            semantic = 1 - (1 - semantic) * (1 - frame)
            z = frame_z(c)
            if z is not None and z >= VIDEO_FRAME_Z_EVIDENCE:
                semantic = max(semantic, _scale(z, VIDEO_FRAME_Z_FLOOR, VIDEO_FRAME_Z_FULL))
                evidence = visual = True

        # --- name -----------------------------------------------------------
        name_text = name_for_matching(c)
        name_cov, name_words = coverage(terms, name_text.split(), phrase, name_text)
        trigram = c.name_similarity if c.name_similarity >= TRIGRAM_NAME_FLOOR else 0.0
        name = max(name_cov, trigram)

        # --- content --------------------------------------------------------
        chunks = sorted(c.chunks, key=lambda ch: ch.score, reverse=True)[:MAX_CONTENT_CHUNKS]
        content_text = normalize_text(" ".join(ch.text for ch in chunks))
        content, content_words = coverage(terms, tokens(content_text), phrase, content_text)

        if name >= NAME_EVIDENCE or content >= CONTENT_EVIDENCE:
            evidence = True

        if not evidence:
            continue

        score = 1 - (1 - W_SEMANTIC * semantic) * (1 - W_NAME * name) * (1 - W_CONTENT * content)

        reasons = []
        if name >= NAME_EVIDENCE:
            reasons.append("filename")
        if content >= CONTENT_EVIDENCE:
            reasons.append(CONTENT_FIELD.get(c.file_type, "content"))
        if visual:
            reasons.append("visual")
        if c.text_margin is not None and c.text_margin >= text_evidence:
            reasons.append("semantic")

        match = _match(c, chunks, name_words, content_words, reasons)
        if visual and c.file_type == "video" and c.frame_time_s is not None:
            match["frame_time_s"] = c.frame_time_s   # "Looks similar (frame at mm:ss)"

        results.append(Scored(
            candidate=c, score=round(float(score), 4), semantic=semantic, name=name, content=content,
            reasons=reasons, match=match
        ))

    results.sort(key=lambda r: r.score, reverse=True)

    return results


def possible_visual_matches(candidates, returned_keys, limit: int = POSSIBLE_LIMIT) -> List[Scored]:
    """Images/videos just below the visual evidence gates: video floor <= z < threshold,
    image floor <= CLIP margin < threshold (document photos excluded, as in the gate).
    Only candidates that are not already results; best `limit` by score; match.confidence="low"."""

    possible = []

    for c in candidates:

        if c.key in returned_keys:
            continue

        if c.file_type == "video":
            z = frame_z(c)
            if z is None or not POSSIBLE_VIDEO_Z_FLOOR <= z < VIDEO_FRAME_Z_EVIDENCE:
                continue
            semantic = _scale(z, VIDEO_FRAME_Z_FLOOR, VIDEO_FRAME_Z_FULL)

        elif c.file_type == "image":
            m = c.clip_margin
            if m is None or not POSSIBLE_IMAGE_MARGIN_FLOOR <= m < IMAGE_MARGIN_EVIDENCE or is_document_photo(c):
                continue
            semantic = _scale(m, IMAGE_MARGIN_FLOOR, IMAGE_MARGIN_FULL)

        else:
            continue

        match = {"reasons": ["visual"], "field": "filename", "snippet": c.file,
                 "highlights": [], "confidence": "low"}
        if c.file_type == "video" and c.frame_time_s is not None:
            match["frame_time_s"] = c.frame_time_s

        possible.append(Scored(candidate=c, score=round(float(W_SEMANTIC * semantic), 4), semantic=semantic,
                               name=0.0, content=0.0, reasons=["visual"], match=match))

    possible.sort(key=lambda r: r.score, reverse=True)

    return possible[:limit]


def _match(c, chunks, name_words, content_words, reasons) -> Dict:

    best_chunk = None

    if content_words:
        best_chunk = max(
            chunks,
            key=lambda ch: (sum(1 for w in set(content_words) if w in ch.text.lower()), ch.score),
            default=None
        )
    elif chunks:
        best_chunk = chunks[0]

    if best_chunk is not None and best_chunk.text.strip():
        snippet, highlights = make_snippet(best_chunk.text, content_words)
        field_name = CONTENT_FIELD.get(c.file_type, "content")
    else:
        snippet, highlights = c.file, _highlights(c.file, name_words)
        field_name = "filename"

    return {
        "reasons": reasons,
        "field": field_name,
        "snippet": snippet,
        "highlights": highlights,
    }
