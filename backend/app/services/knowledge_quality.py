"""Knowledge Quality Pipeline — deterministic text cleaning and quality metadata (P6.5).

All rules are conservative (prefer under-cleaning to over-cleaning), local-only
(no external services), and stable (same input always produces same output).

Runs between extract_text_from_upload and chunk_document in the upload pipeline.
"""

import hashlib
import re

QUALITY_PIPELINE_VERSION = "knowledge_quality.det_v1"

# ── page number / header / footer patterns ──

_PAGE_NUM_RE = re.compile(
    r"^\s*(?:page\s*)?\d{1,4}\s*(?:of\s*\d{1,4})?\s*$|"
    r"^\s*(?:第\s*)?\d{1,4}\s*(?:页|／|/\s*\d{1,4}\s*页)?\s*$",
    re.IGNORECASE,
)
_HEADER_FOOTER_KEYWORDS = re.compile(
    r"confidential|strictly\s+private|all\s+rights?\s+reserved|"
    r"copyright\s+©|www\.|http[s]?://|"
    r"^\s*(?:©|®|™)\s*",
    re.IGNORECASE,
)

MIN_LINE_LEN = 6       # lines shorter than this are candidates for removal
MAX_NOISE_REPEAT = 4   # if a line repeats more than this many times in a doc, treat as header/footer
NOISE_REMOVAL_RATIO = 0.20  # warn if >20% of raw content was removed


# ── helpers ──

def content_fingerprint(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()[:16]


def _looks_like_page_number(line: str) -> bool:
    return bool(_PAGE_NUM_RE.match(line.strip()))


def _looks_like_header_footer(line: str) -> bool:
    s = line.strip()
    if len(s) < 4 or len(s) > 120:
        return False
    if _HEADER_FOOTER_KEYWORDS.search(s):
        return True
    return False


# ── step 1: normalize ──

def normalize_text(text: str) -> tuple[str, dict]:
    """Normalize whitespace, collapse blank lines, normalize line endings."""
    raw_len = len(text)
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines into single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing/leading whitespace per line (keep paragraph indent for now)
    lines = text.split("\n")
    lines = [l.rstrip() for l in lines]  # only right-strip (left may have indent)
    clean = "\n".join(lines).strip()
    meta = {"raw_length": raw_len, "clean_length": len(clean), "blank_lines_removed": max(0, len(lines) - len(clean.split("\n")))}
    return clean, meta


# ── step 2: remove noise lines ──

def remove_noise_lines(text: str) -> tuple[str, dict]:
    """Remove page numbers, header/footer lines (detected by repeat count), and over-short noise."""
    lines = text.split("\n")
    # Count repeats to detect header/footer lines
    stripped = [l.strip() for l in lines]
    from collections import Counter
    counts = Counter(stripped)
    removed = 0
    kept: list[str] = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            kept.append(line)
            continue
        # Page number patterns
        if _looks_like_page_number(s):
            removed += 1
            continue
        # Short noise lines (single word, stray punctuation, etc.)
        if len(s) < MIN_LINE_LEN and not any(c.isalpha() for c in s):
            removed += 1
            continue
        # Repeating header/footer (appears > MAX_NOISE_REPEAT times in the doc)
        if counts[s] > MAX_NOISE_REPEAT and _looks_like_header_footer(s):
            removed += 1
            continue
        kept.append(line)
    clean = "\n".join(kept).strip()
    return clean, {"noise_lines_removed": removed, "header_footer_candidates": sum(1 for v in counts.values() if v > MAX_NOISE_REPEAT)}


# ── step 3: merge broken lines ──

def merge_broken_lines(text: str) -> tuple[str, dict]:
    """Merge short lines that look like they were broken by PDF/DOCX line-wrapping.

    A line is a candidate for merging if it does NOT end with sentence-ending
    punctuation and the next line starts with a lowercase letter or CJK character.
    """
    lines = text.split("\n")
    merged_count = 0
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            result.append(line)
            i += 1
            continue
        # Merge if: current line doesn't end with sentence ender, and next line exists
        stripped = line.rstrip()
        ends_sentence = stripped.endswith((".", "。", "！", "？", "!", "?", "”", "]", ")", "」"))
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
        next_stripped = next_line.strip()
        if (not ends_sentence and next_stripped
                and not next_stripped.startswith(("#", "-", "*", "•", "1.", "2.", "3."))):
            # Merge: join with a space if both contain CJK or non-latin chars, else newline
            result.append(stripped + " " + next_stripped.lstrip())
            merged_count += 1
            i += 2
        else:
            result.append(line)
            i += 1
    return "\n".join(result).strip(), {"broken_lines_merged": merged_count}


# ── step 4: dedupe consecutive repeated paragraphs ──

def dedupe_repeated_paragraphs(text: str) -> tuple[str, dict]:
    """Remove consecutive duplicate paragraphs (same-fingerprint"). First occurrence kept."""
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    kept: list[str] = []
    dupes = 0
    prev_fp = None
    for p in paragraphs:
        fp = content_fingerprint(p)
        if fp == prev_fp:
            dupes += 1
            continue
        kept.append(p)
        prev_fp = fp
    clean = "\n\n".join(kept)
    return clean, {"duplicate_paragraphs_removed": dupes}


# ── orchestrator ──

def clean_extracted_text(text: str) -> dict:
    """Apply all cleaning steps. Returns {clean_text, raw_text, metadata, warnings}."""
    if not text or not text.strip():
        return {
            "raw_text": text or "",
            "clean_text": "",
            "metadata": {"quality_pipeline_version": QUALITY_PIPELINE_VERSION,
                         "raw_text_length": len(text or ""), "clean_text_length": 0,
                         "removed_line_count": 0, "removed_paragraph_count": 0,
                         "normalized_break_count": 0, "duplicate_block_count": 0},
            "warnings": ["cleaning_removed_all_content"],
        }

    raw_len = len(text)
    warnings: list[str] = []

    clean, norm_meta = normalize_text(text)
    norm_count = norm_meta.get("blank_lines_removed", 0)

    clean, noise_meta = remove_noise_lines(clean)
    noise_removed = noise_meta.get("noise_lines_removed", 0)

    clean, merge_meta = merge_broken_lines(clean)
    merged = merge_meta.get("broken_lines_merged", 0)

    clean, dedup_meta = dedupe_repeated_paragraphs(clean)
    dupes = dedup_meta.get("duplicate_paragraphs_removed", 0)

    removed_total = noise_removed + dupes
    if raw_len > 0 and removed_total > 0 and (removed_total / max(raw_len, 1)) > NOISE_REMOVAL_RATIO:
        warnings.append("high_noise_removed")

    if not clean.strip():
        warnings.append("cleaning_removed_all_content")

    metadata = {
        "quality_pipeline_version": QUALITY_PIPELINE_VERSION,
        "raw_text_length": raw_len,
        "clean_text_length": len(clean),
        "removed_line_count": noise_removed,
        "removed_paragraph_count": dupes,
        "normalized_break_count": norm_count,
        "duplicate_block_count": dupes,
    }

    return {"raw_text": text, "clean_text": clean, "metadata": metadata, "warnings": warnings}


# ── chunk quality ──

def build_chunk_quality_metadata(
    *,
    document_metadata: dict,
    chunk_text: str,
    chunk_index: int,
    chunk_count: int,
) -> dict:
    return {
        "quality_pipeline_version": QUALITY_PIPELINE_VERSION,
        "chunk_raw_text_length": len(chunk_text),
        "chunk_clean_text_length": len(chunk_text.strip()),
        "chunk_fingerprint": content_fingerprint(chunk_text),
        "chunk_index": chunk_index,
        "chunk_count": chunk_count,
    }


_WEAK_TITLES = frozenset({
    "服务介绍", "方案", "文档", "概述", "介绍", "简介", "说明", "背景",
    "summary", "introduction", "overview", "background", "未命名",
})


def build_quality_flags_for_clean_chunk(
    *,
    title: str | None,
    content: str,
    clean_result: dict,
) -> list[str]:
    """Return quality flags for a *cleaned* KnowledgeItem chunk."""
    flags: list[str] = []
    t = (title or "").strip()
    if not t or len(t) < 3 or t in _WEAK_TITLES:
        flags.append("weak_title")
    c = content.strip()
    if len(c) < 80:
        flags.append("very_short_after_cleaning")
    if "cleaning_removed_all_content" in clean_result.get("warnings", []):
        flags.append("cleaning_removed_all_content")
    if "high_noise_removed" in clean_result.get("warnings", []):
        flags.append("high_noise_removed")
    return flags
