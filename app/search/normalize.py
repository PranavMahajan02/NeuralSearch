"""One normalization for every lexical comparison (query, names, content)."""

import os
import re
import unicodedata
from typing import List

_SPACE = re.compile(r"\s+")
_WORD = re.compile(r"\w+", re.UNICODE)
_NAME_SEPARATORS = re.compile(r"[_\-.()\[\]]+")
_EDGE_PUNCT = re.compile(r"^[\W_]+|[\W_]+$", re.UNICODE)

# Words that carry no meaning on their own; ignored by lexical matching.
STOPWORDS = frozenset("""
a an and are as at be by can do does for from how i in is it its me my of on or
should so that the this to was what when where which who why will with you your
find show get give
""".split())


def normalize_text(text: str) -> str:
    """NFKC, lower-case, collapse whitespace, strip surrounding punctuation:
    "  JAVA!!!@#$% " -> "java"."""

    text = unicodedata.normalize("NFKC", text or "").lower()
    text = _SPACE.sub(" ", text).strip()

    return _EDGE_PUNCT.sub("", text)


def tokens(text: str) -> List[str]:

    return _WORD.findall(normalize_text(text))


def query_terms(query: str) -> List[str]:
    """Meaningful query tokens (stopwords dropped unless nothing else is left)."""

    words = tokens(query)
    terms = [w for w in words if w not in STOPWORDS]

    return terms or words


def normalize_name(file_name: str) -> str:
    """'Hospital_Management-System (2).pptx' -> 'hospital management system 2'."""

    stem = os.path.splitext(file_name or "")[0]
    stem = _NAME_SEPARATORS.sub(" ", stem)

    return normalize_text(stem)
