"""Overview and stats mixin for the board handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class OverviewMixin:
    """Mixin for overview and stats functionality."""

    def handle_get_overview(self) -> None:
        """Handle GET /api/overview.

        Returns overview data for all teams.
        """
        try:
            from agentteam.board.utils import _get_collector

            collector = _get_collector()
            overview = collector.collect_overview()
            self._serve_json({"teams": overview})

        except Exception as e:
            self.send_error(500, str(e))

    def handle_get_usage_summary(self) -> None:
        """Handle GET /api/usage/summary.

        Returns token usage summary.
        """
        try:
            from agentteam.board.utils import _get_collector

            collector = _get_collector()
            usage = collector.collect_usage_summary()
            self._serve_json(usage)

        except Exception as e:
            # Fallback to empty data
            self._serve_json(
                {
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "by_model": {},
                    "by_team": {},
                }
            )

    def handle_get_usage_trend(self) -> None:
        """Handle GET /api/usage/trend.

        Returns token usage trend data.
        """
        try:
            from agentteam.board.utils import _get_collector

            collector = _get_collector()
            trend = collector.collect_usage_trend()
            self._serve_json(trend)

        except Exception as e:
            # Fallback to empty data
            self._serve_json(
                {
                    "trend": [],
                    "period": "daily",
                }
            )

    def handle_get_provider_stats(self) -> None:
        """Handle GET /api/usage/providers.

        Returns provider usage statistics.
        """
        try:
            from agentteam.board.utils import _get_collector

            collector = _get_collector()
            stats = collector.collect_provider_stats()
            self._serve_json(stats)

        except Exception as e:
            # Fallback to empty data
            self._serve_json(
                {
                    "providers": [],
                    "total_calls": 0,
                    "total_cost": 0.0,
                }
            )

    def handle_get_profiler_stats(self) -> None:
        """Handle GET /api/profiler/stats.

        Returns performance profiler statistics.
        """
        try:
            from agentteam.profiler import get_profiler

            profiler = get_profiler()
            stats = profiler.get_stats()

            self._serve_json(
                {
                    "profiles": stats,
                    "count": len(stats),
                }
            )

        except Exception as e:
            # Fallback to empty data
            self._serve_json(
                {
                    "profiles": [],
                    "count": 0,
                }
            )

    def handle_get_concurrency_limits(self) -> None:
        """Handle GET /api/concurrency/limits.

        Returns concurrency limits configuration.
        """
        try:
            import os

            limits = {
                "max_agents": int(os.environ.get("AGENTTEAM_MAX_AGENTS", "10")),
                "max_parallel_tasks": int(os.environ.get("AGENTTEAM_MAX_PARALLEL", "5")),
                "max_queue_size": int(os.environ.get("AGENTTEAM_MAX_QUEUE", "100")),
            }

            self._serve_json(limits)

        except Exception as e:
            self._serve_json(
                {
                    "max_agents": 10,
                    "max_parallel_tasks": 5,
                    "max_queue_size": 100,
                }
            )
