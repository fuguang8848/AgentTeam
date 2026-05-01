"""
Security utilities for ClawTeam

Provides security checking utilities for:
- SQL injection detection
- Command injection detection
- Path traversal detection
- Input validation
- Rate limiting
"""
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from clawteam.utils.logger import get_logger

logger = get_logger(__name__)


# Patterns for detecting malicious input
SQL_INJECTION_PATTERNS = [
    # Common SQL injection patterns
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION)\b)",
    r"(--|#|/\*|\*/)",
    r"(\bOR\b.*\b=\b|\bAND\b.*\b=\b)",
    r"('|;|\\|\bUNION\b)",
    r"(\bWAITFOR\b|\bBENCHMARK\b|\bSLEEP\b)",
]

COMMAND_INJECTION_PATTERNS = [
    # Command injection patterns
    r"[;&|`$]",
    r"\b(cat|ls|dir|rm|mv|cp|wget|curl|nc|bash|sh|python|perl)\b",
    r"(\|\||&&)",
    r"(\b2>&1\b|>\s*/dev/null)",
    r"[\$\{]",
    r"(\\x[0-9a-fA-F]{2})+",
]

PATH_TRAVERSAL_PATTERNS = [
    # Path traversal patterns
    r"\.\./",
    r"\.\.\\",
    r"(/|\\)\.\.(/|\\)",
    r"%2e%2e",
    r"\.\.%2f",
    r"\.\.%5c",
]


@dataclass
class SecurityCheckResult:
    """Result of a security check"""
    safe: bool
    threat_type: Optional[str] = None
    threat_details: Optional[str] = None
    matched_pattern: Optional[str] = None
    
    def __bool__(self) -> bool:
        return self.safe


class SecurityChecker:
    """
    Security checker for detecting common security threats
    
    Example:
        checker = SecurityChecker()
        
        # Check for SQL injection
        result = checker.check_sql_injection("SELECT * FROM users")
        if not result.safe:
            print(f"SQL injection detected: {result.threat_details}")
        
        # Check for command injection
        result = checker.check_command_injection("cat /etc/passwd")
        if not result.safe:
            print(f"Command injection detected: {result.threat_details}")
        
        # Check for path traversal
        result = checker.check_path_traversal("../../etc/passwd")
        if not result.safe:
            print(f"Path traversal detected: {result.threat_details}")
    """
    
    def __init__(self):
        self._sql_patterns = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
        self._cmd_patterns = [re.compile(p, re.IGNORECASE) for p in COMMAND_INJECTION_PATTERNS]
        self._path_patterns = [re.compile(p, re.IGNORECASE) for p in PATH_TRAVERSAL_PATTERNS]
    
    def check_sql_injection(self, user_input: str) -> SecurityCheckResult:
        """
        Check for SQL injection patterns in user input
        
        Returns:
            SecurityCheckResult with safe=True if no threat detected
        """
        if not user_input:
            return SecurityCheckResult(safe=True)
        
        for pattern in self._sql_patterns:
            match = pattern.search(user_input)
            if match:
                logger.warning(f"SQL injection pattern detected: {match.group()}")
                return SecurityCheckResult(
                    safe=False,
                    threat_type="sql_injection",
                    threat_details=f"SQL keyword or operator detected: {match.group()}",
                    matched_pattern=pattern.pattern,
                )
        
        return SecurityCheckResult(safe=True)
    
    def check_command_injection(self, user_input: str) -> SecurityCheckResult:
        """
        Check for command injection patterns in user input
        
        Returns:
            SecurityCheckResult with safe=True if no threat detected
        """
        if not user_input:
            return SecurityCheckResult(safe=True)
        
        for pattern in self._cmd_patterns:
            match = pattern.search(user_input)
            if match:
                logger.warning(f"Command injection pattern detected: {match.group()}")
                return SecurityCheckResult(
                    safe=False,
                    threat_type="command_injection",
                    threat_details=f"Command character or operator detected: {match.group()}",
                    matched_pattern=pattern.pattern,
                )
        
        return SecurityCheckResult(safe=True)
    
    def check_path_traversal(self, user_input: str) -> SecurityCheckResult:
        """
        Check for path traversal patterns in user input
        
        Returns:
            SecurityCheckResult with safe=True if no threat detected
        """
        if not user_input:
            return SecurityCheckResult(safe=True)
        
        # Normalize the input
        normalized = user_input.replace("\\", "/")
        
        for pattern in self._path_patterns:
            match = pattern.search(normalized)
            if match:
                logger.warning(f"Path traversal pattern detected: {match.group()}")
                return SecurityCheckResult(
                    safe=False,
                    threat_type="path_traversal",
                    threat_details=f"Path traversal sequence detected: {match.group()}",
                    matched_pattern=pattern.pattern,
                )
        
        return SecurityCheckResult(safe=True)
    
    def check_all(self, user_input: str) -> list[SecurityCheckResult]:
        """
        Run all security checks on user input
        
        Returns:
            List of SecurityCheckResult (empty if all safe)
        """
        results = []
        
        sql_result = self.check_sql_injection(user_input)
        if not sql_result.safe:
            results.append(sql_result)
        
        cmd_result = self.check_command_injection(user_input)
        if not cmd_result.safe:
            results.append(cmd_result)
        
        path_result = self.check_path_traversal(user_input)
        if not path_result.safe:
            results.append(path_result)
        
        return results


class RateLimiter:
    """
    Simple rate limiter for API endpoints
    
    Example:
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        
        if not limiter.check(client_id):
            raise HTTPError(429, "Rate limit exceeded")
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}
        self._lock = __import__("threading").Lock()
    
    def check(self, client_id: str) -> bool:
        """
        Check if a client is within rate limits
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            True if client is within rate limits, False if limit exceeded
        """
        import threading
        with self._lock:
            now = time.time()
            window_start = now - self._window_seconds
            
            # Get or create request list for client
            if client_id not in self._requests:
                self._requests[client_id] = []
            
            # Filter to only requests within the window
            self._requests[client_id] = [
                t for t in self._requests[client_id] if t > window_start
            ]
            
            # Check if limit exceeded
            if len(self._requests[client_id]) >= self._max_requests:
                return False
            
            # Record this request
            self._requests[client_id].append(now)
            return True
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for a client in current window"""
        import threading
        with self._lock:
            if client_id not in self._requests:
                return self._max_requests
            
            now = time.time()
            window_start = now - self._window_seconds
            
            # Filter to only requests within the window
            recent_requests = [
                t for t in self._requests[client_id] if t > window_start
            ]
            
            return max(0, self._max_requests - len(recent_requests))
    
    def reset(self, client_id: str) -> None:
        """Reset rate limit for a client"""
        import threading
        with self._lock:
            if client_id in self._requests:
                del self._requests[client_id]
    
    def cleanup(self) -> int:
        """Remove expired entries, return count of removed clients"""
        import threading
        with self._lock:
            now = time.time()
            window_start = now - self._window_seconds
            
            removed = 0
            clients_to_remove = []
            
            for client_id, timestamps in self._requests.items():
                timestamps = [t for t in timestamps if t > window_start]
                if not timestamps:
                    clients_to_remove.append(client_id)
                else:
                    self._requests[client_id] = timestamps
            
            for client_id in clients_to_remove:
                del self._requests[client_id]
                removed += 1
            
            return removed


def validate_input(
    value: Any,
    allowed_chars: Optional[str] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate user input with various constraints
    
    Args:
        value: The input value to validate
        allowed_chars: String of allowed characters (e.g., "abc123")
        max_length: Maximum length of string
        pattern: Regex pattern to match
        
    Returns:
        (is_valid, error_message)
    """
    if value is None:
        return True, None  # None is allowed
    
    if not isinstance(value, str):
        value = str(value)
    
    if max_length and len(value) > max_length:
        return False, f"Input exceeds maximum length of {max_length}"
    
    if allowed_chars:
        invalid_chars = set(value) - set(allowed_chars)
        if invalid_chars:
            return False, f"Input contains invalid characters: {invalid_chars}"
    
    if pattern:
        if not re.match(pattern, value):
            return False, f"Input does not match required pattern"
    
    return True, None


# Global security checker instance
_security_checker: Optional[SecurityChecker] = None


def get_security_checker() -> SecurityChecker:
    """Get the global security checker instance"""
    global _security_checker
    if _security_checker is None:
        _security_checker = SecurityChecker()
    return _security_checker


# Convenience functions
def check_sql_injection(user_input: str) -> SecurityCheckResult:
    """Check for SQL injection"""
    return get_security_checker().check_sql_injection(user_input)


def check_command_injection(user_input: str) -> SecurityCheckResult:
    """Check for command injection"""
    return get_security_checker().check_command_injection(user_input)


def check_path_traversal(user_input: str) -> SecurityCheckResult:
    """Check for path traversal"""
    return get_security_checker().check_path_traversal(user_input)
