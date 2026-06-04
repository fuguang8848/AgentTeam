"""Shared fixtures for agentteam tests.

We redirect all file-based state to tmp_path so tests never touch the real ~/.agentteam.
"""


import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Point AGENTTEAM_DATA_DIR at a temp dir so every test gets a clean slate."""
    data_dir = tmp_path / ".agentteam"
    data_dir.mkdir()
    monkeypatch.setenv("AGENTTEAM_DATA_DIR", str(data_dir))
    # Also override HOME so config_path() doesn't hit real ~/.agentteam/config.json
    monkeypatch.setenv("HOME", str(tmp_path))
    # Patch Path.home() to return tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return data_dir


@pytest.fixture
def team_name():
    return "test-team"
