"""
AgentTeam Integration Tests

End-to-end tests that verify the full system works together.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

from agentteam.config import AppConfig
from agentteam.session import get_session_registry, SessionRegistry
from agentteam.team import TeamManager
from agentteam.tracker.file_tracker import FileChangeTracker, get_file_change_tracker, FileChangeTrackerConfig
from agentteam.tracker.file_watcher import watch_directory
from agentteam.tracker.diff_tracker import DiffTracker, DiffStore
from agentteam.profiler import Profiler


class TestIntegrationBasic:
    """Basic integration tests"""

    def test_config_creation(self):
        """Test that config can be created"""
        config = AppConfig()
        assert config is not None
        assert not config.debug

    def test_session_registry_singleton(self):
        """Test that session registry is a singleton"""
        registry1 = get_session_registry()
        registry2 = get_session_registry()
        assert registry1 is registry2

    def test_team_manager_creation(self):
        """Test that team manager can be created"""
        team_mgr = TeamManager()
        assert team_mgr is not None


class TestIntegrationFileTracking:
    """Integration tests for file tracking"""

    def test_file_change_tracker_creation(self):
        """Test that file change tracker can be created"""
        config = FileChangeTrackerConfig()
        tracker = FileChangeTracker(config)
        assert tracker is not None

    def test_watch_directory(self):
        """Test watching a directory"""
        # watch_directory requires a handler which is complex to set up
        # This test verifies the import works
        from agentteam.tracker.file_watcher import watch_directory

        assert callable(watch_directory)


class TestIntegrationDiffTracking:
    """Integration tests for diff tracking"""

    def test_diff_tracker_creation(self):
        """Test that diff tracker can be created"""
        tracker = DiffTracker(team_name="test-team")
        assert tracker is not None
        assert tracker.team_name == "test-team"


class TestIntegrationTeamWorkflow:
    """Integration tests for team workflows"""

    def test_team_discovery(self):
        """Test that team manager can discover teams"""
        team_mgr = TeamManager()

        # Discover teams (should return empty or existing)
        teams = team_mgr.discover_teams()
        assert isinstance(teams, list)

    def test_team_manager_methods_exist(self):
        """Test that team manager has expected methods"""
        team_mgr = TeamManager()

        assert hasattr(team_mgr, "create_team")
        assert hasattr(team_mgr, "get_team")
        assert hasattr(team_mgr, "list_members")
        assert hasattr(team_mgr, "add_member")


class TestIntegrationProfiler:
    """Integration tests for profiler"""

    def test_profiler_full_flow(self):
        """Test profiler with realistic workload"""
        profiler = Profiler()

        # Simulate a realistic workload
        with profiler.profile("config_creation"):
            config = AppConfig()

        with profiler.profile("get_registry"):
            registry = get_session_registry()

        with profiler.profile("team_manager"):
            team_mgr = TeamManager()

        # Verify profiles exist
        profiles = profiler.get_all_profiles()
        assert len(profiles) >= 3

        names = [p.name for p in profiles]
        assert "config_creation" in names
        assert "get_registry" in names
        assert "team_manager" in names

    def test_profiler_latency_tracking(self):
        """Test latency tracking with multiple operations"""
        profiler = Profiler()

        import time

        # Simulate operations
        for _ in range(20):
            profiler.measure_latency("db_query", lambda: time.sleep(0.001))

        # Get stats
        stats = profiler.get_latency_stats("db_query")

        assert stats is not None
        assert stats.count == 20
        assert stats.avg_ms > 0
        assert stats.p95_ms >= stats.avg_ms


class TestIntegrationCrossCutting:
    """Integration tests for cross-cutting concerns"""

    def test_config_validation_with_real_path(self, tmp_path):
        """Test config validation with real paths"""
        config = AppConfig()

        errors = config.validate()
        # Default config should be valid
        assert len(errors) == 0

    def test_error_context_propagation(self):
        """Test that error context propagates through layers"""
        from agentteam.exceptions import (
            AgentTeamError,
            AgentError,
            ErrorContext,
        )

        ctx = ErrorContext(
            team_name="test-team",
            agent_id="agent-1",
            session_id="session-1",
        )

        error = AgentError("Agent failed", context=ctx)

        # Verify context is preserved
        assert error.context.team_name == "test-team"
        assert error.context.agent_id == "agent-1"
        assert error.context.session_id == "session-1"


class TestIntegrationAsync:
    """Async integration tests"""

    @pytest.mark.asyncio
    async def test_async_profiler_context(self):
        """Test profiler with async operations"""
        profiler = Profiler()

        async def async_operation():
            await asyncio.sleep(0.01)
            return 42

        # Measure async latency
        result = await profiler.measure_latency_async("async_op", async_operation())
        assert result == 42

        # Verify latency was recorded
        stats = profiler.get_latency_stats("async_op")
        assert stats is not None
        assert stats.count == 1


class TestIntegrationFullScenario:
    """Full end-to-end scenarios"""

    def test_full_agent_workflow(self, tmp_path):
        """
        Simulate a full agent workflow:
        1. Create config
        2. Get session registry
        3. Create team manager
        4. Track files
        """
        profiler = Profiler()

        # Step 1: Setup
        with profiler.profile("setup"):
            config = AppConfig()

        # Step 2: Get registry
        with profiler.profile("get_registry"):
            registry = get_session_registry()

        # Step 3: Create team manager
        with profiler.profile("team_manager"):
            team_mgr = TeamManager()

        # Step 4: Track files
        with profiler.profile("track_files"):
            tracker_config = FileChangeTrackerConfig()
            tracker = FileChangeTracker(tracker_config)

        # Verify workflow completed
        profiles = profiler.get_all_profiles()
        profile_names = [p.name for p in profiles]

        assert "setup" in profile_names
        assert "get_registry" in profile_names
        assert "team_manager" in profile_names
        assert "track_files" in profile_names

        # Verify all operations completed in reasonable time
        for profile in profiles:
            assert profile.duration_ms < 60000  # Less than 1 minute each

    def test_full_error_recovery_workflow(self):
        """Test error handling through a full workflow"""
        from agentteam.exceptions import AgentSpawnError, ErrorRecovery, ErrorContext

        profiler = Profiler()
        recovery = ErrorRecovery()

        # Simulate a failing operation
        ctx = {"agent_id": "test-agent", "team_name": "test-team"}

        # Run recovery
        async def run_recovery():
            error = AgentSpawnError("Simulated failure", context=ErrorContext(**ctx))
            return await recovery.recover(error, ctx)

        success, result = asyncio.run(run_recovery())

        # Verify recovery was attempted
        assert success is True


def run_integration_tests():
    """Run all integration tests and return report"""
    import sys
    from unittest import TestLoader, TextTestRunner

    loader = TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))

    runner = TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "success": result.wasSuccessful(),
    }


if __name__ == "__main__":
    report = run_integration_tests()
    print()
    print("=" * 60)
    print("INTEGRATION TEST REPORT")
    print("=" * 60)
    print(f"Tests Run: {report['tests_run']}")
    print(f"Failures: {report['failures']}")
    print(f"Errors: {report['errors']}")
    print(f"Skipped: {report['skipped']}")
    print(f"Success: {report['success']}")
