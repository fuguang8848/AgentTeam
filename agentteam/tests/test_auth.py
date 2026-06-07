"""Tests for authentication functionality."""

from __future__ import annotations

import os
import pytest
import time

from agentteam.auth import (
    AuthManager,
    TokenPayload,
    auth_manager,
)


class TestTokenPayload:
    """Test TokenPayload dataclass."""

    def test_payload_creation(self):
        """Test creating a token payload."""
        payload = TokenPayload(user_id="user-1", username="testuser", role="admin", expires_at=time.time() + 3600)
        assert payload.user_id == "user-1"
        assert payload.username == "testuser"
        assert payload.role == "admin"

    def test_payload_is_expired_false(self):
        """Test that payload is not expired."""
        payload = TokenPayload(user_id="user-1", username="testuser", expires_at=time.time() + 3600)
        assert not payload.is_expired()

    def test_payload_is_expired_true(self):
        """Test that payload is expired."""
        payload = TokenPayload(user_id="user-1", username="testuser", expires_at=time.time() - 1)
        assert payload.is_expired()


class TestAuthManager:
    """Test AuthManager class."""

    def test_manager_initialization_no_api_key(self, monkeypatch):
        """Test manager initialization without API key."""
        monkeypatch.delenv("AGENTTEAM_API_KEY", raising=False)
        manager = AuthManager()
        assert not manager.is_auth_required()

    def test_manager_initialization_with_api_key(self, monkeypatch):
        """Test manager initialization with API key."""
        monkeypatch.setenv("AGENTTEAM_API_KEY", "test-api-key-123")
        manager = AuthManager()
        assert manager.is_auth_required()
        assert "admin" in manager._users

    def test_verify_api_key_correct(self, monkeypatch):
        """Test API key verification with correct key."""
        monkeypatch.setenv("AGENTTEAM_API_KEY", "test-api-key-123")
        manager = AuthManager()
        assert manager.verify_api_key("test-api-key-123")

    def test_verify_api_key_wrong(self, monkeypatch):
        """Test API key verification with wrong key."""
        monkeypatch.setenv("AGENTTEAM_API_KEY", "test-api-key-123")
        manager = AuthManager()
        assert not manager.verify_api_key("wrong-key")

    def test_create_token(self, monkeypatch):
        """Test creating a JWT token."""
        monkeypatch.delenv("AGENTTEAM_API_KEY", raising=False)
        manager = AuthManager()
        token = manager.create_token("testuser", "user")
        assert token is not None
        assert len(token) > 0
        assert "." in token

    def test_verify_token_valid(self, monkeypatch):
        """Test verifying a valid token."""
        monkeypatch.delenv("AGENTTEAM_API_KEY", raising=False)
        manager = AuthManager()
        token = manager.create_token("testuser", "user")
        payload = manager.verify_token(token)
        assert payload is not None
        assert payload.username == "testuser"

    def test_verify_token_invalid(self, monkeypatch):
        """Test verifying an invalid token."""
        monkeypatch.delenv("AGENTTEAM_API_KEY", raising=False)
        manager = AuthManager()
        payload = manager.verify_token("invalid-token")
        assert payload is None

    def test_login_with_api_key_success(self, monkeypatch):
        """Test login with correct API key."""
        monkeypatch.setenv("AGENTTEAM_API_KEY", "test-api-key-123")
        manager = AuthManager()
        token = manager.login_with_api_key("test-api-key-123")
        assert token is not None

    def test_login_with_api_key_failure(self, monkeypatch):
        """Test login with wrong API key."""
        monkeypatch.setenv("AGENTTEAM_API_KEY", "test-api-key-123")
        manager = AuthManager()
        token = manager.login_with_api_key("wrong-key")
        assert token is None

    def test_logout(self, monkeypatch):
        """Test logout functionality."""
        monkeypatch.delenv("AGENTTEAM_API_KEY", raising=False)
        manager = AuthManager()
        token = manager.create_token("testuser", "user")
        result = manager.logout(token)
        assert result
        assert token not in manager._tokens


class TestGlobalAuthManager:
    """Test global auth_manager instance."""

    def test_global_manager_exists(self):
        """Test that global manager exists."""
        assert auth_manager is not None
        assert isinstance(auth_manager, AuthManager)
