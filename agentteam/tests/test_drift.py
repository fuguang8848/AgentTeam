"""Tests for agentteam.team.drift — drift detection between task intent and output."""

import pytest

from agentteam.team.drift import (
    _extract_keywords,
    _jaccard_similarity,
    _semantic_signal_score,
    check_task_drift,
    detect_drift,
)
from agentteam.team.models import DriftAlert, TaskItem, TaskPriority, TaskStatus


# ── Keyword extraction ──────────────────────────────────────────────


class TestExtractKeywords:
    def test_english_text(self):
        kw = _extract_keywords("Build a REST API for user authentication")
        assert "build" in kw
        assert "rest" in kw
        assert "api" in kw
        assert "authentication" in kw
        # stop words filtered
        assert "a" not in kw

    def test_chinese_text(self):
        kw = _extract_keywords("实现用户登录功能的API接口")
        # CJK uses bigram+trigram segmentation
        assert "实现" in kw  # bigram
        assert "用户" in kw  # bigram
        assert "登录" in kw  # bigram
        assert "api" in kw  # Western word extracted separately

    def test_mixed_text(self):
        kw = _extract_keywords("Add /api/login endpoint for user authentication 用户登录")
        assert "add" in kw
        assert "api" in kw
        assert "login" in kw
        assert "用户" in kw
        assert "登录" in kw

    def test_empty_text(self):
        assert _extract_keywords("") == set()
        assert _extract_keywords(None) == set()

    def test_short_words_filtered(self):
        kw = _extract_keywords("a I x go do")
        # all are stop words or single char
        assert len(kw) == 0

    def test_numbers_included(self):
        kw = _extract_keywords("Fix bug #1234 in module 5")
        assert "1234" in kw
        assert "5" not in kw  # single char


# ── Jaccard similarity ──────────────────────────────────────────────


class TestJaccardSimilarity:
    def test_identical_sets(self):
        s = {"a", "b", "c"}
        assert _jaccard_similarity(s, s) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        assert _jaccard_similarity({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)

    def test_empty_sets(self):
        assert _jaccard_similarity(set(), set()) == 0.0
        assert _jaccard_similarity({"a"}, set()) == 0.0


# ── Semantic signal score ──────────────────────────────────────────


class TestSemanticSignalScore:
    def test_perfect_match(self):
        score = _semantic_signal_score("build user API", "build user API")
        assert score >= 0.7

    def test_completely_different(self):
        score = _semantic_signal_score(
            "build user authentication API",
            "write documentation for the kitchen recipe system",
        )
        assert score < 0.3

    def test_no_original_intent(self):
        score = _semantic_signal_score("", "some output")
        assert score == 1.0

    def test_key_term_boost(self):
        # Long unique terms should boost the score more
        score = _semantic_signal_score(
            "implement microservices architecture for distributed systems",
            "implement microservices architecture for distributed systems",
        )
        assert score >= 0.7


# ── Drift detection ─────────────────────────────────────────────────


class TestDetectDrift:
    def _make_task(self, subject="Build user API", description="REST API for authentication"):
        return TaskItem(
            subject=subject,
            description=description,
            status=TaskStatus.completed,
        )

    def test_aligned_output_no_alert(self):
        task = self._make_task()
        result = detect_drift(task, "Built REST API with user authentication endpoints")
        assert result is None

    def test_drifted_output_returns_alert(self):
        task = self._make_task()
        result = detect_drift(task, "Wrote documentation for the kitchen recipe system")
        assert result is not None
        assert isinstance(result, DriftAlert)
        assert result.severity in ("low", "medium", "high", "critical")

    def test_empty_output_no_alert(self):
        task = self._make_task()
        result = detect_drift(task, "")
        assert result is None

    def test_whitespace_only_output_no_alert(self):
        task = self._make_task()
        result = detect_drift(task, "   \n  ")
        assert result is None

    def test_alert_contains_task_info(self):
        task = self._make_task("Fix login bug", "Login returns 500 error")
        result = detect_drift(task, "Completely unrelated output here")
        assert result is not None
        assert result.original_subject == "Fix login bug"
        assert result.original_description == "Login returns 500 error"
        assert result.task_id == task.id

    def test_output_truncated(self):
        task = self._make_task()
        long_output = "unrelated " * 200
        result = detect_drift(task, long_output)
        assert result is not None
        assert len(result.actual_output) <= 500

    def test_severity_levels(self):
        task = self._make_task("build authentication system", "REST API user login")

        # low drift (0.5-0.7)
        r_low = detect_drift(task, "built some API with login features and auth")
        # Could be None if aligned enough, or low severity

        # high drift
        r_high = detect_drift(task, "baked cookies for the office party yesterday")
        assert r_high is not None
        assert r_high.severity in ("high", "critical")


# ── Full drift check ────────────────────────────────────────────────


class TestCheckTaskDrift:
    def _make_task(self, subject="Implement search feature", description="Elasticsearch full-text search"):
        return TaskItem(
            subject=subject,
            description=description,
            status=TaskStatus.completed,
        )

    def test_returns_aligned_flag(self):
        task = self._make_task()
        result = check_task_drift(task, "Implemented Elasticsearch full-text search with indexing")
        assert "aligned" in result
        assert "drift_score" in result

    def test_returns_keywords(self):
        task = self._make_task()
        result = check_task_drift(task, "Some output")
        assert "original_keywords" in result
        assert "actual_keywords" in result
        assert "missing_key_terms" in result
        assert "extra_key_terms" in result

    def test_threshold_parameter(self):
        task = self._make_task()
        # With very high threshold, even slightly different output triggers alert
        result = check_task_drift(task, "Different topic entirely", threshold=0.9)
        assert result["aligned"] is False
        assert result["alert"] is not None

    def test_jaccard_included(self):
        task = self._make_task()
        result = check_task_drift(task, "output")
        assert "jaccard_similarity" in result
        assert 0.0 <= result["jaccard_similarity"] <= 1.0

    def test_no_alert_when_aligned(self):
        task = self._make_task()
        result = check_task_drift(task, "Implemented elasticsearch search feature")
        assert result["alert"] is None


# ── Integration: drift detection on task completion ─────────────────


class TestDriftIntegration:
    """Test drift detection integrates with the task store flow."""

    def test_task_model_has_drift_alerts_field(self):
        task = TaskItem(subject="test")
        assert hasattr(task, "drift_alerts")
        assert task.drift_alerts == []

    def test_drift_alert_serialization(self):
        alert = DriftAlert(
            task_id="abc123",
            original_subject="Build API",
            original_description="REST endpoints",
            actual_output="Wrote docs",
            drift_score=0.2,
            severity="high",
        )
        dumped = alert.model_dump(by_alias=True)
        assert dumped["taskId"] == "abc123"
        assert dumped["driftScore"] == 0.2
        assert dumped["severity"] == "high"
        assert "detectedAt" in dumped

    def test_drift_alert_deserialization(self):
        data = {
            "taskId": "xyz789",
            "originalSubject": "Test",
            "originalDescription": "Desc",
            "actualOutput": "Output",
            "driftScore": 0.5,
            "severity": "medium",
        }
        alert = DriftAlert.model_validate(data)
        assert alert.task_id == "xyz789"
        assert alert.drift_score == 0.5
