"""Tests for agentteam.team.dag — DAG dependency resolution."""

import pytest

from agentteam.team.dag import (
    CycleDetectedError,
    detect_cycle,
    get_blocking_tasks,
    get_execution_order,
    get_ready_tasks,
    topological_sort,
)
from agentteam.team.models import TaskItem, TaskPriority, TaskStatus


def _task(id: str, status: TaskStatus = TaskStatus.pending, depends_on: list[str] | None = None, **kwargs) -> TaskItem:
    """Helper to create a TaskItem with a fixed ID."""
    return TaskItem(
        id=id,
        subject=kwargs.get("subject", f"Task {id}"),
        status=status,
        depends_on=depends_on or [],
        priority=kwargs.get("priority", TaskPriority.medium),
    )


class TestTopologicalSort:
    """Tests for topological_sort()."""

    def test_empty_list(self):
        """Empty task list returns empty result."""
        result = topological_sort([])
        assert result == []

    def test_single_task(self):
        """Single task with no dependencies returns as-is."""
        tasks = [_task("a")]
        result = topological_sort(tasks)
        assert len(result) == 1
        assert result[0].id == "a"

    def test_no_dependencies(self):
        """Tasks with no dependencies are returned in sorted order."""
        tasks = [_task("c"), _task("a"), _task("b")]
        result = topological_sort(tasks)
        ids = [t.id for t in result]
        assert ids == ["a", "b", "c"]  # deterministic sorted order

    def test_linear_chain(self):
        """A → B → C: C depends on B, B depends on A."""
        tasks = [
            _task("c", depends_on=["b"]),
            _task("b", depends_on=["a"]),
            _task("a"),
        ]
        result = topological_sort(tasks)
        ids = [t.id for t in result]
        assert ids == ["a", "b", "c"]

    def test_diamond_dependency(self):
        """A → B, A → C, B → D, C → D: D depends on both B and C."""
        tasks = [
            _task("d", depends_on=["b", "c"]),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["a"]),
            _task("a"),
        ]
        result = topological_sort(tasks)
        ids = [t.id for t in result]
        # a must come first, d must come last
        assert ids[0] == "a"
        assert ids[-1] == "d"
        # b and c must be in the middle (order between them doesn't matter)
        assert set(ids[1:3]) == {"b", "c"}

    def test_cycle_raises_error(self):
        """A → B → C → A: cycle should raise CycleDetectedError."""
        tasks = [
            _task("a", depends_on=["c"]),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["b"]),
        ]
        with pytest.raises(CycleDetectedError):
            topological_sort(tasks)

    def test_external_dependency_ignored(self):
        """Dependencies on non-existent tasks are ignored (external tasks)."""
        tasks = [
            _task("b", depends_on=["a", "external_task"]),
            _task("a"),
        ]
        result = topological_sort(tasks)
        ids = [t.id for t in result]
        assert ids == ["a", "b"]


class TestDetectCycle:
    """Tests for detect_cycle()."""

    def test_no_cycle(self):
        """Linear chain has no cycle."""
        tasks = [
            _task("b", depends_on=["a"]),
            _task("a"),
        ]
        assert detect_cycle(tasks) is False

    def test_simple_cycle(self):
        """A → B → A is a cycle."""
        tasks = [
            _task("a", depends_on=["b"]),
            _task("b", depends_on=["a"]),
        ]
        assert detect_cycle(tasks) is True

    def test_self_cycle(self):
        """A → A is a cycle."""
        tasks = [_task("a", depends_on=["a"])]
        assert detect_cycle(tasks) is True

    def test_empty_list(self):
        """Empty list has no cycle."""
        assert detect_cycle([]) is False

    def test_complex_no_cycle(self):
        """Complex DAG without cycle."""
        tasks = [
            _task("e", depends_on=["c", "d"]),
            _task("d", depends_on=["b"]),
            _task("c", depends_on=["a", "b"]),
            _task("b", depends_on=["a"]),
            _task("a"),
        ]
        assert detect_cycle(tasks) is False


class TestGetReadyTasks:
    """Tests for get_ready_tasks()."""

    def test_all_ready_no_deps(self):
        """All pending tasks with no deps are ready."""
        tasks = [_task("a"), _task("b"), _task("c")]
        ready = get_ready_tasks(tasks)
        assert len(ready) == 3
        assert {t.id for t in ready} == {"a", "b", "c"}

    def test_some_ready(self):
        """Only tasks with completed deps are ready."""
        tasks = [
            _task("a", status=TaskStatus.completed),
            _task("b", status=TaskStatus.completed),
            _task("c", depends_on=["a"]),
            _task("d", depends_on=["a", "b"]),
            _task("e"),
        ]
        ready = get_ready_tasks(tasks)
        ids = {t.id for t in ready}
        assert "c" in ids
        assert "d" in ids
        assert "e" in ids
        assert "a" not in ids  # already completed
        assert "b" not in ids  # already completed

    def test_none_ready_blocked(self):
        """No tasks ready when all deps are pending."""
        tasks = [
            _task("a"),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["b"]),
        ]
        ready = get_ready_tasks(tasks)
        assert len(ready) == 1  # only "a" is ready (no deps)
        assert ready[0].id == "a"

    def test_external_dep_assumed_met(self):
        """Dependencies on non-existent tasks are assumed met."""
        tasks = [
            _task("b", depends_on=["external"]),
        ]
        ready = get_ready_tasks(tasks)
        assert len(ready) == 1
        assert ready[0].id == "b"

    def test_in_progress_not_ready(self):
        """In-progress tasks are not considered ready."""
        tasks = [
            _task("a", status=TaskStatus.in_progress),
            _task("b"),
        ]
        ready = get_ready_tasks(tasks)
        assert len(ready) == 1
        assert ready[0].id == "b"


class TestGetBlockingTasks:
    """Tests for get_blocking_tasks()."""

    def test_no_blockers(self):
        """Task with no dependencies has no blockers."""
        task = _task("a")
        blockers = get_blocking_tasks(task, [task])
        assert blockers == []

    def test_one_blocker(self):
        """Task blocked by one pending task."""
        a = _task("a")
        b = _task("b", depends_on=["a"])
        blockers = get_blocking_tasks(b, [a, b])
        assert len(blockers) == 1
        assert blockers[0].id == "a"

    def test_multiple_blockers(self):
        """Task blocked by multiple incomplete tasks."""
        a = _task("a")
        b = _task("b")
        c = _task("c", status=TaskStatus.completed)
        d = _task("d", depends_on=["a", "b", "c"])
        blockers = get_blocking_tasks(d, [a, b, c, d])
        assert len(blockers) == 2
        assert {t.id for t in blockers} == {"a", "b"}

    def test_all_completed_no_blockers(self):
        """All deps completed means no blockers."""
        a = _task("a", status=TaskStatus.completed)
        b = _task("b", status=TaskStatus.completed)
        c = _task("c", depends_on=["a", "b"])
        blockers = get_blocking_tasks(c, [a, b, c])
        assert blockers == []

    def test_missing_dep_not_blocker(self):
        """Dependencies not in task list are not blockers."""
        b = _task("b", depends_on=["missing"])
        blockers = get_blocking_tasks(b, [b])
        assert blockers == []

    def test_in_progress_is_blocker(self):
        """In-progress tasks count as blockers."""
        a = _task("a", status=TaskStatus.in_progress)
        b = _task("b", depends_on=["a"])
        blockers = get_blocking_tasks(b, [a, b])
        assert len(blockers) == 1
        assert blockers[0].id == "a"


class TestGetExecutionOrder:
    """Tests for get_execution_order() (wave-based parallel execution)."""

    def test_all_parallel(self):
        """No dependencies → all tasks in one wave."""
        tasks = [_task("a"), _task("b"), _task("c")]
        waves = get_execution_order(tasks)
        assert len(waves) == 1
        assert waves[0] == ["a", "b", "c"]

    def test_linear_chain(self):
        """A → B → C → three waves."""
        tasks = [
            _task("c", depends_on=["b"]),
            _task("b", depends_on=["a"]),
            _task("a"),
        ]
        waves = get_execution_order(tasks)
        assert len(waves) == 3
        assert waves[0] == ["a"]
        assert waves[1] == ["b"]
        assert waves[2] == ["c"]

    def test_diamond(self):
        """Diamond: A → {B, C} → D → three waves."""
        tasks = [
            _task("d", depends_on=["b", "c"]),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["a"]),
            _task("a"),
        ]
        waves = get_execution_order(tasks)
        assert len(waves) == 3
        assert waves[0] == ["a"]
        assert waves[1] == ["b", "c"]  # B and C in parallel
        assert waves[2] == ["d"]

    def test_cycle_raises(self):
        """Cycle raises CycleDetectedError."""
        tasks = [
            _task("a", depends_on=["b"]),
            _task("b", depends_on=["a"]),
        ]
        with pytest.raises(CycleDetectedError):
            get_execution_order(tasks)
