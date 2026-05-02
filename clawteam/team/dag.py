"""DAG (Directed Acyclic Graph) dependency resolution for ClawTeam tasks.

Provides topological sorting, cycle detection, ready-task identification,
and blocking-task analysis for task dependency graphs.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from clawteam.team.models import TaskItem, TaskStatus


class CycleDetectedError(Exception):
    """Raised when a cycle is detected in the task dependency graph."""

    pass


def topological_sort(tasks: list[TaskItem]) -> list[TaskItem]:
    """Return tasks in a valid topological order (dependencies first).

    Uses Kahn's algorithm. Raises CycleDetectedError if a cycle exists.

    Args:
        tasks: List of TaskItem with depends_on fields populated.

    Returns:
        Tasks ordered so every dependency appears before the dependent task.

    Raises:
        CycleDetectedError: If the dependency graph contains a cycle.
    """
    task_map: dict[str, TaskItem] = {t.id: t for t in tasks}
    # Build adjacency list and in-degree count
    in_degree: dict[str, int] = {t.id: 0 for t in tasks}
    dependents: dict[str, list[str]] = {t.id: [] for t in tasks}

    for t in tasks:
        for dep_id in t.depends_on:
            if dep_id not in task_map:
                # Dependency references a non-existent task — skip it
                # (it could be completed externally or simply not in scope)
                continue
            in_degree[t.id] = in_degree.get(t.id, 0) + 1
            dependents[dep_id].append(t.id)

    # Start with tasks that have no dependencies (in-degree 0)
    queue: deque[str] = deque()
    for t in tasks:
        if in_degree.get(t.id, 0) == 0:
            queue.append(t.id)

    result: list[TaskItem] = []
    while queue:
        # Sort for deterministic output (stable ordering by id)
        queue_list = sorted(queue)
        queue.clear()
        for tid in queue_list:
            queue.append(tid)

        node_id = queue.popleft()
        result.append(task_map[node_id])

        for dep_id in sorted(dependents.get(node_id, [])):
            in_degree[dep_id] -= 1
            if in_degree[dep_id] == 0:
                queue.append(dep_id)

    if len(result) != len(tasks):
        raise CycleDetectedError(
            f"Cycle detected in task dependencies. "
            f"Only {len(result)}/{len(tasks)} tasks could be ordered."
        )

    return result


def detect_cycle(tasks: list[TaskItem]) -> bool:
    """Detect whether the task dependency graph contains a cycle.

    Args:
        tasks: List of TaskItem with depends_on fields populated.

    Returns:
        True if a cycle exists, False otherwise.
    """
    try:
        topological_sort(tasks)
        return False
    except CycleDetectedError:
        return True


def get_ready_tasks(tasks: list[TaskItem]) -> list[TaskItem]:
    """Return all pending tasks whose dependencies are fully completed.

    A task is "ready" when:
    - Its status is 'pending'
    - All task IDs in its depends_on list are completed (or not in the task list)

    Args:
        tasks: List of TaskItem to evaluate.

    Returns:
        List of TaskItem that are ready to be started.
    """
    # Build a set of completed task IDs
    completed_ids: set[str] = {t.id for t in tasks if t.status == TaskStatus.completed}
    all_ids: set[str] = {t.id for t in tasks}

    ready: list[TaskItem] = []
    for t in tasks:
        if t.status != TaskStatus.pending:
            continue
        # Check all dependencies
        all_deps_met = True
        for dep_id in t.depends_on:
            # If dependency is in our task list, it must be completed
            # If not in our list, assume it's external/already done
            if dep_id in all_ids and dep_id not in completed_ids:
                all_deps_met = False
                break
        if all_deps_met:
            ready.append(t)

    return ready


def get_blocking_tasks(task: TaskItem, all_tasks: list[TaskItem]) -> list[TaskItem]:
    """Return the tasks that are blocking a given task from starting.

    A task blocks another when:
    - It appears in the blocked task's depends_on list
    - It is NOT in completed status

    Args:
        task: The task to check blockers for.
        all_tasks: Full list of tasks to look up dependencies.

    Returns:
        List of TaskItem that are blocking the given task.
    """
    task_map: dict[str, TaskItem] = {t.id: t for t in all_tasks}
    blockers: list[TaskItem] = []

    for dep_id in task.depends_on:
        if dep_id in task_map:
            dep_task = task_map[dep_id]
            if dep_task.status != TaskStatus.completed:
                blockers.append(dep_task)

    return blockers


def get_execution_order(tasks: list[TaskItem]) -> list[list[str]]:
    """Return tasks grouped by execution wave (parallelizable batches).

    Each wave contains task IDs that can execute in parallel (all their
    dependencies are satisfied by previous waves).

    Args:
        tasks: List of TaskItem with depends_on fields populated.

    Returns:
        List of lists, where each inner list contains task IDs for one wave.

    Raises:
        CycleDetectedError: If the dependency graph contains a cycle.
    """
    task_map: dict[str, TaskItem] = {t.id: t for t in tasks}
    all_ids: set[str] = set(task_map.keys())

    # Compute in-degree considering only in-scope dependencies
    in_degree: dict[str, int] = {}
    dependents: dict[str, list[str]] = {t.id: [] for t in tasks}

    for t in tasks:
        count = 0
        for dep_id in t.depends_on:
            if dep_id in all_ids:
                count += 1
                dependents[dep_id].append(t.id)
        in_degree[t.id] = count

    waves: list[list[str]] = []
    completed: set[str] = set()

    remaining = set(all_ids)
    while remaining:
        # Find all tasks with in-degree 0 among remaining
        wave = sorted(tid for tid in remaining if in_degree.get(tid, 0) == 0)
        if not wave:
            raise CycleDetectedError(f"Cycle detected: {len(remaining)} tasks remain unorderable.")
        waves.append(wave)
        for tid in wave:
            completed.add(tid)
            remaining.discard(tid)
            for dep_id in dependents.get(tid, []):
                if dep_id in remaining:
                    in_degree[dep_id] -= 1

    return waves
