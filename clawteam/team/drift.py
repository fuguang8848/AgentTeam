"""Drift detection: compare original task intent vs actual agent output.

Uses keyword overlap + semantic signals to detect when an agent's work
diverges from the original task goal.
"""

from __future__ import annotations

import re
from typing import Any

from clawteam.team.models import DriftAlert, TaskItem


# Common English and Chinese stop words to filter out
STOP_WORDS = frozenset(
    {
        # English
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "because",
        "but",
        "and",
        "or",
        "if",
        "while",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "about",
        "up",
        "down",
        "go",
        "get",
        "do",
        "make",
        "take",
        "come",
        "let",
        "say",
        "goes",
        "went",
        "gone",
        "going",
        # Chinese
        "的",
        "了",
        "在",
        "是",
        "我",
        "有",
        "和",
        "与",
        "或",
        "不",
        "也",
        "就",
        "都",
        "而",
        "及",
        "已",
        "至",
        "者",
        "之",
        "其",
        "这",
        "那",
        "但",
        "还",
        "因",
        "并",
        "或",
        "对",
        "于",
        "以",
        "被",
        "从",
        "上",
        "下",
        "中",
        "等",
        "把",
        "让",
        "向",
        "往",
        "所",
        "若",
        "如",
        "此",
        "该",
        "它",
        "们",
        "个",
        "么",
        "吗",
        "呢",
        "啊",
        "呀",
        "哦",
        "嗯",
        "吧",
        "嘛",
        "啦",
    }
)


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text (lowercase, no stop words).

    Handles both Western languages (whitespace-delimited) and CJK languages
    (character-level n-grams for meaningful segments).
    """
    if not text:
        return set()
    text_lower = text.lower()
    keywords: set[str] = set()

    # Extract Western words (Latin + digits)
    western_words = re.findall(r"[a-z0-9]+", text_lower)
    for w in western_words:
        if w not in STOP_WORDS and len(w) >= 2:
            keywords.add(w)

    # Extract CJK characters and use bigram/trigram segmentation
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text_lower)
    if cjk_chars:
        cjk_text = "".join(cjk_chars)
        # Bigrams (2-char segments) capture most meaningful Chinese words
        for i in range(len(cjk_text) - 1):
            bigram = cjk_text[i : i + 2]
            if bigram not in STOP_WORDS:
                keywords.add(bigram)
        # Trigrams for longer phrases
        for i in range(len(cjk_text) - 2):
            trigram = cjk_text[i : i + 3]
            if trigram not in STOP_WORDS:
                keywords.add(trigram)

    return keywords


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not a or not b:
        return 0.0
    intersection = a & b
    union = a | b
    return len(intersection) / len(union) if union else 0.0


def _semantic_signal_score(original: str, actual: str) -> float:
    """Heuristic score based on structural similarity signals.

    Checks:
    - Same verb/action words present
    - Same technical/domain terms present
    - Similar sentence structure (rough)
    - Partial matching (prefix/suffix overlap for inflected words)
    """
    orig_kw = _extract_keywords(original)
    act_kw = _extract_keywords(actual)

    if not orig_kw:
        return 1.0  # No original intent to drift from
    if not act_kw:
        return 0.0

    # 1. Jaccard similarity (baseline)
    jaccard = _jaccard_similarity(orig_kw, act_kw)

    # 2. Recall: what fraction of original keywords appear in actual?
    recall = len(orig_kw & act_kw) / len(orig_kw) if orig_kw else 0.0

    # 3. Partial matching: check if original words are prefixes of actual words
    #    (e.g., "implement" matches "implemented", "build" matches "built" via prefix)
    partial_matches = 0
    for orig_word in orig_kw:
        if len(orig_word) >= 3:
            for act_word in act_kw:
                if act_word.startswith(orig_word[: max(3, len(orig_word) - 1)]):
                    partial_matches += 1
                    break
    partial_ratio = partial_matches / len(orig_kw) if orig_kw else 0.0

    # 4. Key term overlap (longer words = more meaningful)
    key_terms = {w for w in orig_kw if len(w) >= 4}
    if key_terms:
        key_overlap = len(key_terms & act_kw) / len(key_terms)
        # Weighted: 25% Jaccard + 30% recall + 20% partial + 25% key terms
        score = 0.25 * jaccard + 0.30 * recall + 0.20 * partial_ratio + 0.25 * key_overlap
    else:
        score = 0.4 * jaccard + 0.3 * recall + 0.3 * partial_ratio

    return round(score, 3)


def detect_drift(task: TaskItem, actual_output: str) -> DriftAlert | None:
    """Detect drift between original task intent and actual agent output.

    Args:
        task: The completed task with original subject/description
        actual_output: The agent's completion report, commit message,
                       or deliverable description

    Returns:
        DriftAlert if drift_score < 0.5, else None
    """
    if not actual_output or not actual_output.strip():
        return None

    original_text = f"{task.subject} {task.description}"
    drift_score = _semantic_signal_score(original_text, actual_output)

    # Determine severity based on drift score
    if drift_score >= 0.6:
        return None  # Well aligned, no alert
    elif drift_score >= 0.45:
        severity = "low"
    elif drift_score >= 0.3:
        severity = "medium"
    elif drift_score >= 0.15:
        severity = "high"
    else:
        severity = "critical"

    return DriftAlert(
        task_id=task.id,
        original_subject=task.subject,
        original_description=task.description,
        actual_output=actual_output[:500],  # Truncate for storage
        drift_score=drift_score,
        severity=severity,
    )


def check_task_drift(
    task: TaskItem,
    actual_output: str,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Full drift check with detailed breakdown.

    Returns:
        Dict with drift_score, severity, keywords, and alert (if any)
    """
    original_text = f"{task.subject} {task.description}"
    orig_kw = _extract_keywords(original_text)
    act_kw = _extract_keywords(actual_output)

    jaccard = _jaccard_similarity(orig_kw, act_kw)
    drift_score = _semantic_signal_score(original_text, actual_output)

    # Key terms that were expected but missing
    key_terms = {w for w in orig_kw if len(w) >= 4}
    missing_key = key_terms - _extract_keywords(actual_output)
    extra_key = _extract_keywords(actual_output) - key_terms

    alert = None
    if drift_score < threshold:
        alert = detect_drift(task, actual_output)

    return {
        "task_id": task.id,
        "subject": task.subject,
        "drift_score": drift_score,
        "jaccard_similarity": round(jaccard, 3),
        "threshold": threshold,
        "aligned": drift_score >= threshold,
        "original_keywords": sorted(orig_kw),
        "actual_keywords": sorted(act_kw),
        "missing_key_terms": sorted(missing_key),
        "extra_key_terms": sorted(extra_key),
        "alert": alert.model_dump(by_alias=True) if alert else None,
    }
