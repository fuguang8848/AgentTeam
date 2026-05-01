"""Authentication module for ClawTeam Web UI."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import Optional
import secrets
import base64
import json

# JWT-like token implementation (no external dependencies)
@dataclass
class TokenPayload:
    """Token payload data."""
    user_id: str
    username: str
    role: str = "user"
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at,
            "expires_at": self.expires_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> TokenPayload:
        return cls(
            user_id=data.get("user_id", ""),
            username=data.get("username", ""),
            role=data.get("role", "user"),
            created_at=data.get("created_at", 0.0),
            expires_at=data.get("expires_at", 0.0)
        )


class AuthManager:
    """Manages authentication for the Web UI."""
    
    def __init__(self):
        self._api_key = os.environ.get("CLAWTEAM_API_KEY", "")
        self._jwt_secret = os.environ.get("CLAWTEAM_JWT_SECRET", secrets.token_hex(32))
        self._token_expiry = int(os.environ.get("CLAWTEAM_TOKEN_EXPIRY", "86400"))  # 24 hours
        self._users: dict[str, dict] = {}
        self._tokens: dict[str, TokenPayload] = {}
        
        # Initialize default admin if API key is set
        if self._api_key:
            self._users["admin"] = {
                "user_id": "admin",
                "username": "admin",
                "role": "admin",
                "api_key_hash": self._hash_api_key(self._api_key)
            }
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _encode_token(self, payload: TokenPayload) -> str:
        """Encode a token payload into a JWT-like string."""
        # Header
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode()
        
        # Payload
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload.to_dict()).encode()).decode()
        
        # Signature
        signature = hmac.new(
            self._jwt_secret.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode()
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def _decode_token(self, token: str) -> Optional[TokenPayload]:
        """Decode and verify a token."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Verify signature
            expected_signature = hmac.new(
                self._jwt_secret.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256
            ).digest()
            expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode()
            
            if signature_b64 != expected_signature_b64:
                return None
            
            # Decode payload
            payload_json = base64.urlsafe_b64decode(payload_b64).decode()
            payload = TokenPayload.from_dict(json.loads(payload_json))
            
            return payload
        except Exception:
            return None
    
    def verify_api_key(self, api_key: str) -> bool:
        """Verify an API key."""
        if not self._api_key:
            return True  # No API key set, allow all
        
        return api_key == self._api_key
    
    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """Verify a JWT token."""
        payload = self._decode_token(token)
        if payload and not payload.is_expired():
            return payload
        return None
    
    def create_token(self, username: str, role: str = "user") -> str:
        """Create a new JWT token for a user."""
        user_id = username.lower().replace(" ", "_")
        payload = TokenPayload(
            user_id=user_id,
            username=username,
            role=role,
            expires_at=time.time() + self._token_expiry
        )
        token = self._encode_token(payload)
        self._tokens[token] = payload
        return token
    
    def login_with_api_key(self, api_key: str) -> Optional[str]:
        """Login using API key and return a token."""
        if self.verify_api_key(api_key):
            return self.create_token("admin", "admin")
        return None
    
    def login_with_credentials(self, username: str, password: str) -> Optional[str]:
        """Login using username/password and return a token."""
        # For simplicity, we only support API key authentication
        # This can be extended for database-backed user authentication
        return None
    
    def logout(self, token: str) -> bool:
        """Logout and invalidate a token."""
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False
    
    def get_user(self, token: str) -> Optional[dict]:
        """Get user info from a token."""
        payload = self.verify_token(token)
        if payload:
            return payload.to_dict()
        return None
    
    def is_auth_required(self) -> bool:
        """Check if authentication is required."""
        return bool(self._api_key)


# Global auth manager instance
auth_manager = AuthManager()


def require_auth():
    """Decorator to require authentication for an endpoint."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Check if auth is required
            if not auth_manager.is_auth_required():
                return func(*args, **kwargs)
            
            # Get token from headers or kwargs
            request = args[0] if args else None
            if hasattr(request, 'headers'):
                token = request.headers.get('X-API-Key', '')
                if auth_manager.verify_api_key(token):
                    return func(*args, **kwargs)
                
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]
                    if auth_manager.verify_token(token):
                        return func(*args, **kwargs)
            
            # Return 401 Unauthorized
            if hasattr(request, 'send_error'):
                request.send_error(401, "Unauthorized")
                return None
            
            raise ValueError("Unauthorized")
        
        return wrapper
    return decorator
