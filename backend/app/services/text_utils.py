"""Shared text-matching utilities — CJK bigram + whitespace token overlap scoring.

These are the deterministic relevance primitives used by both Context Builder
(service matching) and Knowledge Retriever (knowledge item matching).  Single
source of truth: both modules import from here.
"""


def bigrams(s: str) -> set[str]:
    s = s.replace(" ", "")
    return {s[i:i + 2] for i in range(len(s) - 1)}


def overlap_score(text: str, hay: str) -> int:
    """Deterministic relevance: shared whitespace tokens (latin/tags) + CJK bigram overlap."""
    if not text or not hay:
        return 0
    t, h = text.lower(), hay.lower()
    tset = {w for w in t.split() if len(w) >= 2}
    hset = {w for w in h.split() if len(w) >= 2}
    score = len(tset & hset) * 2
    score += len(bigrams(t) & bigrams(h))
    return score


def as_text_list(v) -> str:
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return ""
