"""Provider selector with intelligent routing and automatic fallback.

This module provides:
- Provider selection based on task type and capabilities
- Quota/limit detection and management
- Automatic fallback when providers hit limits
- Provider health tracking and availability monitoring

Inspired by SpectrAI's providerAvailability.ts and AdapterRegistry.ts.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from clawteam.fileutil import atomic_write_text
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import get_data_dir

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _provider_root(team_name: str) -> Path:
    """Get the provider data directory for a team."""
    d = ensure_within_root(
        get_data_dir() / "providers", validate_identifier(team_name, "team name")
    )
    d.mkdir(parents=True, exist_ok=True)
    return d


class ProviderStatus(str, Enum):
    """Status of a provider."""

    available = "available"
    degraded = "degraded"  # Partially available, may have issues
    unavailable = "unavailable"  # Completely unavailable
    quota_exceeded = "quota_exceeded"  # Hit rate limit or quota
    cooldown = "cooldown"  # Temporarily disabled after failures


class TaskType(str, Enum):
    """Types of tasks for provider matching."""

    architecture = "architecture"  # System design, planning
    code_generation = "code_generation"  # Writing code
    code_review = "code_review"  # Reviewing code quality
    debugging = "debugging"  # Finding and fixing bugs
    documentation = "documentation"  # Writing docs
    analysis = "analysis"  # Analyzing data or code
    testing = "testing"  # Writing tests
    refactoring = "refactoring"  # Improving code structure
    research = "research"  # Information gathering
    general = "general"  # General-purpose tasks


@dataclass
class ProviderInfo:
    """Information about a provider."""

    name: str
    adapter_type: str  # claude, codex, gemini, kimi, qwen, opencode, openclaw
    status: ProviderStatus = ProviderStatus.available
    priority: int = 0  # Higher priority = preferred

    # Capabilities
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_images: bool = False
    max_context_tokens: int = 100000
    supports_long_context: bool = False

    # Task type preferences (score 0-100)
    task_scores: dict[str, int] = field(default_factory=dict)

    # Health metrics
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    last_success_at: str = ""
    last_failure_at: str = ""
    consecutive_failures: int = 0

    # Quota info
    quota_remaining: int = -1  # -1 = unknown/unlimited
    quota_reset_at: str = ""
    rate_limit_remaining: int = -1

    def get_task_score(self, task_type: TaskType) -> int:
        """Get the score for a task type (default 50 if not specified)."""
        return self.task_scores.get(task_type.value, 50)


class QuotaInfo(BaseModel):
    """Quota information for a provider."""

    model_config = {"populate_by_name": True}

    provider_name: str = Field(alias="providerName")
    quota_limit: int = Field(default=-1, alias="quotaLimit")  # -1 = unlimited
    quota_used: int = Field(default=0, alias="quotaUsed")
    quota_remaining: int = Field(default=-1, alias="quotaRemaining")
    quota_reset_at: str = Field(default="", alias="quotaResetAt")
    rate_limit_per_minute: int = Field(default=-1, alias="rateLimitPerMinute")
    requests_this_minute: int = Field(default=0, alias="requestsThisMinute")
    last_updated: str = Field(default_factory=_now_iso, alias="lastUpdated")


class SelectionResult(BaseModel):
    """Result of provider selection."""

    model_config = {"populate_by_name": True}

    success: bool
    provider_name: str | None = None
    adapter_type: str | None = None
    reason: str = ""
    fallback_chain: list[str] = Field(default_factory=list, alias="fallbackChain")
    confidence: float = 0.0
    task_type: str = ""
    estimated_latency_ms: float = 0.0


class FallbackChain(BaseModel):
    """Fallback chain configuration."""

    model_config = {"populate_by_name": True}

    name: str
    providers: list[str] = Field(default_factory=list)
    task_type: str | None = None  # Optional task-specific chain

    @classmethod
    def default_chain(cls) -> "FallbackChain":
        """Get the default fallback chain."""
        return cls(
            name="default",
            providers=["claude", "gemini", "codex", "opencode", "qwen", "kimi"],
        )

    @classmethod
    def code_generation_chain(cls) -> "FallbackChain":
        """Get the code generation fallback chain."""
        return cls(
            name="code_generation",
            providers=["codex", "claude", "gemini", "opencode"],
            task_type="code_generation",
        )

    @classmethod
    def architecture_chain(cls) -> "FallbackChain":
        """Get the architecture fallback chain."""
        return cls(
            name="architecture",
            providers=["claude", "gemini", "opencode"],
            task_type="architecture",
        )

    @classmethod
    def long_context_chain(cls) -> "FallbackChain":
        """Get the long context fallback chain."""
        return cls(
            name="long_context",
            providers=["gemini", "claude", "opencode"],
            task_type="analysis",
        )


# Default provider configurations
DEFAULT_PROVIDERS: dict[str, ProviderInfo] = {
    "claude": ProviderInfo(
        name="claude",
        adapter_type="claude",
        priority=100,
        supports_streaming=True,
        supports_tools=True,
        supports_images=True,
        max_context_tokens=200000,
        supports_long_context=True,
        task_scores={
            "architecture": 95,
            "code_generation": 85,
            "code_review": 90,
            "debugging": 90,
            "documentation": 80,
            "analysis": 85,
            "testing": 80,
            "refactoring": 85,
            "research": 75,
            "general": 90,
        },
    ),
    "codex": ProviderInfo(
        name="codex",
        adapter_type="codex",
        priority=90,
        supports_streaming=True,
        supports_tools=True,
        supports_images=False,
        max_context_tokens=100000,
        supports_long_context=False,
        task_scores={
            "architecture": 70,
            "code_generation": 95,
            "code_review": 85,
            "debugging": 80,
            "documentation": 60,
            "analysis": 70,
            "testing": 90,
            "refactoring": 90,
            "research": 50,
            "general": 75,
        },
    ),
    "gemini": ProviderInfo(
        name="gemini",
        adapter_type="gemini",
        priority=85,
        supports_streaming=True,
        supports_tools=True,
        supports_images=True,
        max_context_tokens=1000000,  # 1M tokens
        supports_long_context=True,
        task_scores={
            "architecture": 80,
            "code_generation": 75,
            "code_review": 70,
            "debugging": 75,
            "documentation": 90,
            "analysis": 95,
            "testing": 70,
            "refactoring": 70,
            "research": 90,
            "general": 80,
        },
    ),
    "kimi": ProviderInfo(
        name="kimi",
        adapter_type="kimi",
        priority=70,
        supports_streaming=True,
        supports_tools=False,
        supports_images=False,
        max_context_tokens=200000,
        supports_long_context=True,
        task_scores={
            "architecture": 65,
            "code_generation": 70,
            "code_review": 60,
            "debugging": 65,
            "documentation": 85,
            "analysis": 80,
            "testing": 60,
            "refactoring": 65,
            "research": 85,
            "general": 70,
        },
    ),
    "qwen": ProviderInfo(
        name="qwen",
        adapter_type="qwen",
        priority=75,
        supports_streaming=True,
        supports_tools=True,
        supports_images=False,
        max_context_tokens=100000,
        supports_long_context=False,
        task_scores={
            "architecture": 70,
            "code_generation": 80,
            "code_review": 75,
            "debugging": 70,
            "documentation": 75,
            "analysis": 75,
            "testing": 75,
            "refactoring": 75,
            "research": 70,
            "general": 75,
        },
    ),
    "opencode": ProviderInfo(
        name="opencode",
        adapter_type="opencode",
        priority=60,
        supports_streaming=True,
        supports_tools=True,
        supports_images=False,
        max_context_tokens=100000,
        supports_long_context=False,
        task_scores={
            "architecture": 60,
            "code_generation": 70,
            "code_review": 65,
            "debugging": 60,
            "documentation": 60,
            "analysis": 60,
            "testing": 65,
            "refactoring": 65,
            "research": 60,
            "general": 65,
        },
    ),
    "openclaw": ProviderInfo(
        name="openclaw",
        adapter_type="openclaw",
        priority=50,
        supports_streaming=True,
        supports_tools=True,
        supports_images=False,
        max_context_tokens=100000,
        supports_long_context=False,
        task_scores={
            "architecture": 55,
            "code_generation": 60,
            "code_review": 55,
            "debugging": 55,
            "documentation": 55,
            "analysis": 55,
            "testing": 55,
            "refactoring": 55,
            "research": 55,
            "general": 55,
        },
    ),
}


class ProviderSelector:
    """Intelligent provider selector with automatic fallback.

    Features:
    - Task-type based selection
    - Quota/limit detection
    - Automatic fallback on quota exceeded
    - Health tracking and cooldown
    - Configurable fallback chains
    """

    def __init__(
        self,
        team_name: str,
        providers: dict[str, ProviderInfo] | None = None,
        fallback_chains: list[FallbackChain] | None = None,
        cooldown_seconds: float = 60.0,
        failure_threshold: int = 3,
    ):
        """Initialize the provider selector.

        Args:
            team_name: Name of the team
            providers: Provider configurations (uses defaults if None)
            fallback_chains: Fallback chain configurations
            cooldown_seconds: Cooldown period after failures
            failure_threshold: Number of failures before cooldown
        """
        self.team_name = team_name
        self.providers = DEFAULT_PROVIDERS.copy() if providers is None else providers
        self.fallback_chains = fallback_chains or [
            FallbackChain.default_chain(),
            FallbackChain.code_generation_chain(),
            FallbackChain.architecture_chain(),
            FallbackChain.long_context_chain(),
        ]
        self.cooldown_seconds = cooldown_seconds
        self.failure_threshold = failure_threshold

        self._lock = threading.Lock()
        self._quota_info: dict[str, QuotaInfo] = {}
        self._request_times: dict[str, list[float]] = {}  # For rate limiting

    def _get_chain_for_task(self, task_type: TaskType) -> FallbackChain:
        """Get the appropriate fallback chain for a task type."""
        for chain in self.fallback_chains:
            if chain.task_type == task_type.value:
                return chain
        return FallbackChain.default_chain()

    def _is_in_cooldown(self, provider_name: str) -> bool:
        """Check if a provider is in cooldown."""
        provider = self.providers.get(provider_name)
        if not provider or provider.status != ProviderStatus.cooldown:
            return False

        # Check if cooldown has expired
        if provider.last_failure_at:
            try:
                last_failure = datetime.fromisoformat(
                    provider.last_failure_at.replace("Z", "+00:00")
                )
                elapsed = time.time() - last_failure.timestamp()
                if elapsed >= self.cooldown_seconds:
                    # Exit cooldown
                    provider.status = ProviderStatus.available
                    provider.consecutive_failures = 0
                    return False
            except (ValueError, TypeError):
                pass

        return True

    def _check_rate_limit(self, provider_name: str) -> bool:
        """Check if provider is within rate limits."""
        quota = self._quota_info.get(provider_name)
        if not quota:
            return True

        # Check per-minute rate limit
        if quota.rate_limit_per_minute > 0:
            now = time.time()
            times = self._request_times.get(provider_name, [])
            # Filter to last minute
            times = [t for t in times if now - t < 60]
            self._request_times[provider_name] = times

            if len(times) >= quota.rate_limit_per_minute:
                return False

        return True

    def _check_quota(self, provider_name: str) -> bool:
        """Check if provider has quota remaining."""
        quota = self._quota_info.get(provider_name)
        if not quota:
            return True

        # Check if quota is exceeded
        if quota.quota_remaining >= 0 and quota.quota_remaining <= 0:
            # Check if quota has reset
            if quota.quota_reset_at:
                try:
                    reset_time = datetime.fromisoformat(quota.quota_reset_at.replace("Z", "+00:00"))
                    if time.time() >= reset_time.timestamp():
                        # Quota should have reset
                        quota.quota_used = 0
                        quota.quota_remaining = quota.quota_limit
                        return True
                except (ValueError, TypeError):
                    pass
            return False

        return True

    def _is_available(self, provider_name: str) -> bool:
        """Check if a provider is available for use."""
        provider = self.providers.get(provider_name)
        if not provider:
            return False

        # Check status
        if provider.status == ProviderStatus.unavailable:
            return False

        # Check cooldown
        if self._is_in_cooldown(provider_name):
            return False

        # Check quota
        if not self._check_quota(provider_name):
            provider.status = ProviderStatus.quota_exceeded
            return False

        # Check rate limit
        if not self._check_rate_limit(provider_name):
            return False

        return True

    def select(
        self,
        task_type: TaskType = TaskType.general,
        preferred_provider: str | None = None,
        require_long_context: bool = False,
        require_images: bool = False,
        exclude_providers: list[str] | None = None,
    ) -> SelectionResult:
        """Select the best provider for a task.

        Args:
            task_type: Type of task
            preferred_provider: Optional preferred provider
            require_long_context: Require long context support
            require_images: Require image support
            exclude_providers: Providers to exclude

        Returns:
            SelectionResult with selected provider and fallback chain
        """
        exclude = set(exclude_providers or [])

        # Check preferred provider first
        if preferred_provider and preferred_provider not in exclude:
            if self._is_available(preferred_provider):
                provider = self.providers.get(preferred_provider)
                if provider:
                    # Check capability requirements
                    if require_long_context and not provider.supports_long_context:
                        pass  # Skip, doesn't meet requirements
                    elif require_images and not provider.supports_images:
                        pass  # Skip, doesn't meet requirements
                    else:
                        chain = self._get_chain_for_task(task_type)
                        return SelectionResult(
                            success=True,
                            provider_name=preferred_provider,
                            adapter_type=provider.adapter_type,
                            reason="Preferred provider selected",
                            fallback_chain=[
                                p
                                for p in chain.providers
                                if p != preferred_provider and self._is_available(p)
                            ],
                            confidence=1.0,
                            task_type=task_type.value,
                            estimated_latency_ms=provider.avg_latency_ms,
                        )

        # Get fallback chain for task type
        chain = self._get_chain_for_task(task_type)

        # Find best available provider from chain
        best_provider = None
        best_score = -1

        for provider_name in chain.providers:
            if provider_name in exclude:
                continue

            if not self._is_available(provider_name):
                continue

            provider = self.providers.get(provider_name)
            if not provider:
                continue

            # Check capability requirements
            if require_long_context and not provider.supports_long_context:
                continue
            if require_images and not provider.supports_images:
                continue

            # Calculate score
            task_score = provider.get_task_score(task_type)
            health_score = provider.success_rate * 20
            priority_score = provider.priority / 10

            total_score = task_score + health_score + priority_score

            if total_score > best_score:
                best_score = total_score
                best_provider = provider

        # Fallback: check all providers not in chain (manually added providers)
        if not best_provider:
            chain_names = set(chain.providers)
            for provider_name, provider in self.providers.items():
                if provider_name in chain_names or provider_name in exclude:
                    continue
                if not self._is_available(provider_name):
                    continue
                if require_long_context and not provider.supports_long_context:
                    continue
                if require_images and not provider.supports_images:
                    continue
                # Calculate score
                task_score = provider.get_task_score(task_type)
                health_score = provider.success_rate * 20
                priority_score = provider.priority / 10
                total_score = task_score + health_score + priority_score
                if total_score > best_score:
                    best_score = total_score
                    best_provider = provider

        if best_provider:
            # Build fallback chain (remaining available providers)
            fallback = [
                p
                for p in chain.providers
                if p != best_provider.name and self._is_available(p) and p not in exclude
            ]

            return SelectionResult(
                success=True,
                provider_name=best_provider.name,
                adapter_type=best_provider.adapter_type,
                reason=f"Selected based on task score ({best_score:.1f})",
                fallback_chain=fallback,
                confidence=min(best_score / 100, 1.0),
                task_type=task_type.value,
                estimated_latency_ms=best_provider.avg_latency_ms,
            )

        # No provider available
        return SelectionResult(
            success=False,
            reason="No available provider meets the requirements",
            fallback_chain=[],
            task_type=task_type.value,
        )

    def select_with_fallback(
        self,
        task_type: TaskType = TaskType.general,
        preferred_provider: str | None = None,
        max_fallback_attempts: int = 3,
    ) -> SelectionResult:
        """Select provider with automatic fallback on failure.

        This method combines select() and fallback() for a simpler API.
        Inspired by SpectrAI providerAvailability.ts design.

        Args:
            task_type: Type of task
            preferred_provider: Optional preferred provider
            max_fallback_attempts: Maximum fallback attempts

        Returns:
            SelectionResult with selected provider
        """
        # First attempt with preferred provider
        result = self.select(
            task_type=task_type,
            preferred_provider=preferred_provider,
        )

        if result.success:
            return result

        # Try fallback chain
        for i in range(max_fallback_attempts):
            if not result.fallback_chain:
                break

            next_provider = result.fallback_chain[0]
            result = self.select(
                task_type=task_type,
                preferred_provider=next_provider,
            )

            if result.success:
                result.reason = f"Fallback attempt {i + 1} successful"
                return result

        # All attempts failed
        return SelectionResult(
            success=False,
            reason=f"All {max_fallback_attempts + 1} attempts failed",
            fallback_chain=[],
            task_type=task_type.value,
        )

    def fallback(
        self, failed_provider: str, task_type: TaskType = TaskType.general
    ) -> SelectionResult:
        """Get a fallback provider after a failure.

        Args:
            failed_provider: The provider that failed
            task_type: Type of task

        Returns:
            SelectionResult with fallback provider
        """
        # Mark the failed provider
        self.record_failure(failed_provider)

        # Get chain and find next available
        chain = self._get_chain_for_task(task_type)

        for provider_name in chain.providers:
            if provider_name == failed_provider:
                continue

            if self._is_available(provider_name):
                provider = self.providers.get(provider_name)
                if provider:
                    remaining_fallback = [
                        p
                        for p in chain.providers
                        if p != provider_name and p != failed_provider and self._is_available(p)
                    ]

                    return SelectionResult(
                        success=True,
                        provider_name=provider_name,
                        adapter_type=provider.adapter_type,
                        reason=f"Fallback from {failed_provider}",
                        fallback_chain=remaining_fallback,
                        confidence=0.8,  # Lower confidence for fallback
                        task_type=task_type.value,
                        estimated_latency_ms=provider.avg_latency_ms,
                    )

        return SelectionResult(
            success=False,
            reason=f"No fallback available after {failed_provider} failure",
            fallback_chain=[],
            task_type=task_type.value,
        )

    def record_success(self, provider_name: str, latency_ms: float = 0.0) -> None:
        """Record a successful request.

        Args:
            provider_name: Provider that succeeded
            latency_ms: Request latency in milliseconds
        """
        with self._lock:
            provider = self.providers.get(provider_name)
            if provider:
                provider.success_rate = min(1.0, provider.success_rate + 0.05)
                provider.last_success_at = _now_iso()
                provider.consecutive_failures = 0
                provider.status = ProviderStatus.available

                if latency_ms > 0:
                    # Update average latency (simple moving average)
                    provider.avg_latency_ms = provider.avg_latency_ms * 0.9 + latency_ms * 0.1

            # Track request time for rate limiting
            now = time.time()
            times = self._request_times.get(provider_name, [])
            times.append(now)
            self._request_times[provider_name] = times

            # Update quota
            quota = self._quota_info.get(provider_name)
            if quota and quota.quota_remaining > 0:
                quota.quota_used += 1
                quota.quota_remaining -= 1
                quota.last_updated = _now_iso()

    def record_failure(self, provider_name: str, error_type: str = "unknown") -> None:
        """Record a failed request.

        Args:
            provider_name: Provider that failed
            error_type: Type of error (quota_exceeded, rate_limit, timeout, error)
        """
        with self._lock:
            provider = self.providers.get(provider_name)
            if provider:
                provider.success_rate = max(0.0, provider.success_rate - 0.1)
                provider.last_failure_at = _now_iso()
                provider.consecutive_failures += 1

                # Check if should enter cooldown
                if provider.consecutive_failures >= self.failure_threshold:
                    provider.status = ProviderStatus.cooldown
                    logger.warning(
                        f"Provider {provider_name} entering cooldown after {provider.consecutive_failures} failures"
                    )

                # Handle specific error types
                if error_type == "quota_exceeded":
                    provider.status = ProviderStatus.quota_exceeded
                    quota = self._quota_info.get(provider_name)
                    if quota:
                        quota.quota_remaining = 0
                        quota.last_updated = _now_iso()

                elif error_type == "rate_limit":
                    # Already handled by rate limit check
                    pass

            logger.info(f"Recorded failure for {provider_name}: {error_type}")

    def set_quota(self, provider_name: str, quota_info: QuotaInfo) -> None:
        """Set quota information for a provider.

        Args:
            provider_name: Provider name
            quota_info: Quota information
        """
        with self._lock:
            self._quota_info[provider_name] = quota_info

            # Update provider status if quota exceeded
            if quota_info.quota_remaining == 0:
                provider = self.providers.get(provider_name)
                if provider:
                    provider.status = ProviderStatus.quota_exceeded

    def get_quota(self, provider_name: str) -> QuotaInfo | None:
        """Get quota information for a provider."""
        with self._lock:
            return self._quota_info.get(provider_name)

    def update_provider_status(self, provider_name: str, status: ProviderStatus) -> None:
        """Manually update a provider's status."""
        with self._lock:
            provider = self.providers.get(provider_name)
            if provider:
                provider.status = status

    def get_provider_info(self, provider_name: str) -> ProviderInfo | None:
        """Get information about a provider."""
        return self.providers.get(provider_name)

    def get_all_providers(self) -> dict[str, ProviderInfo]:
        """Get all provider information."""
        return self.providers.copy()

    def get_available_providers(self) -> list[str]:
        """Get list of available provider names."""
        return [name for name, info in self.providers.items() if self._is_available(name)]

    def add_provider(self, provider: ProviderInfo) -> None:
        """Add a new provider configuration."""
        with self._lock:
            self.providers[provider.name] = provider

    def remove_provider(self, provider_name: str) -> bool:
        """Remove a provider configuration."""
        with self._lock:
            if provider_name in self.providers:
                del self.providers[provider_name]
                return True
            return False

    def save_state(self) -> None:
        """Save provider state to disk."""
        with self._lock:
            data = {
                "providers": {
                    name: {
                        "name": p.name,
                        "adapterType": p.adapter_type,
                        "status": p.status.value,
                        "priority": p.priority,
                        "successRate": p.success_rate,
                        "avgLatencyMs": p.avg_latency_ms,
                        "lastSuccessAt": p.last_success_at,
                        "lastFailureAt": p.last_failure_at,
                        "consecutiveFailures": p.consecutive_failures,
                    }
                    for name, p in self.providers.items()
                },
                "quotas": {
                    name: q.model_dump(by_alias=True) for name, q in self._quota_info.items()
                },
                "updatedAt": _now_iso(),
            }

        path = _provider_root(self.team_name) / "state.json"
        atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False))
        logger.info(f"Saved provider state to {path}")

    def load_state(self) -> None:
        """Load provider state from disk."""
        path = _provider_root(self.team_name) / "state.json"
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))

            with self._lock:
                # Load provider states
                for name, p_data in data.get("providers", {}).items():
                    if name in self.providers:
                        p = self.providers[name]
                        p.status = ProviderStatus(p_data.get("status", "available"))
                        p.success_rate = p_data.get("successRate", 1.0)
                        p.avg_latency_ms = p_data.get("avgLatencyMs", 0.0)
                        p.last_success_at = p_data.get("lastSuccessAt", "")
                        p.last_failure_at = p_data.get("lastFailureAt", "")
                        p.consecutive_failures = p_data.get("consecutiveFailures", 0)

                # Load quotas
                for name, q_data in data.get("quotas", {}).items():
                    self._quota_info[name] = QuotaInfo.model_validate(q_data)

            logger.info(f"Loaded provider state from {path}")
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.error(f"Failed to load provider state: {e}")

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of provider status."""
        available = self.get_available_providers()

        return {
            "totalProviders": len(self.providers),
            "availableProviders": len(available),
            "availableList": available,
            "providersByStatus": {
                status.value: [p.name for p in self.providers.values() if p.status == status]
                for status in ProviderStatus
            },
            "quotas": {
                name: {
                    "remaining": q.quota_remaining,
                    "used": q.quota_used,
                    "limit": q.quota_limit,
                }
                for name, q in self._quota_info.items()
            },
        }


def get_provider_selector(team_name: str) -> ProviderSelector:
    """Get a ProviderSelector instance with state loaded.

    Args:
        team_name: Name of the team

    Returns:
        ProviderSelector instance
    """
    selector = ProviderSelector(team_name)
    selector.load_state()
    return selector


class ProviderAutoSwitchManager:
    """Provider 自动切换管理器

    当 Provider 额度不足或失败时自动切换到备用 Provider。
    参考 SpectrAI 的 Provider 可用性检测和自动切换逻辑。
    """

    def __init__(self, team_name: str):
        self.team_name = team_name
        self.selector = get_provider_selector(team_name)
        self._current_provider: str | None = None
        self._switch_history: list[dict] = []
        self._lock = threading.Lock()

        # 自动切换配置
        self.auto_switch_enabled = True
        self.max_switch_attempts = 3  # 最大切换尝试次数
        self.switch_cooldown_seconds = 30  # 切换冷却时间

    def get_current_provider(self) -> str | None:
        """获取当前使用的 Provider"""
        with self._lock:
            return self._current_provider

    def set_current_provider(self, provider_name: str) -> None:
        """设置当前 Provider"""
        with self._lock:
            self._current_provider = provider_name

    def select_provider(
        self,
        task_type: TaskType = TaskType.general,
        preferred_provider: str | None = None,
        **kwargs,
    ) -> SelectionResult:
        """选择 Provider（支持自动切换）

        Args:
            task_type: 任务类型
            preferred_provider: 首选 Provider
            **kwargs: 其他选择参数

        Returns:
            SelectionResult
        """
        # 如果有首选 Provider 且可用，直接使用
        if preferred_provider and self.selector._is_available(preferred_provider):
            self.set_current_provider(preferred_provider)
            return self.selector.select(task_type, preferred_provider, **kwargs)

        # 如果当前 Provider 可用，继续使用
        current = self.get_current_provider()
        if current and self.selector._is_available(current):
            return self.selector.select(task_type, current, **kwargs)

        # 选择新的 Provider
        result = self.selector.select(task_type, preferred_provider, **kwargs)
        if result.success:
            self.set_current_provider(result.provider_name)

        return result

    def handle_quota_exceeded(
        self, provider_name: str, task_type: TaskType = TaskType.general
    ) -> SelectionResult:
        """处理额度不足情况

        当 Provider 额度不足时，自动切换到备用 Provider。

        Args:
            provider_name: 额度不足的 Provider
            task_type: 任务类型

        Returns:
            SelectionResult（切换后的 Provider）
        """
        logger.warning(f"Provider {provider_name} quota exceeded, attempting auto-switch")

        # 记录额度不足
        self.selector.record_failure(provider_name, "quota_exceeded")

        # 记录切换历史
        switch_record = {
            "from_provider": provider_name,
            "reason": "quota_exceeded",
            "timestamp": _now_iso(),
            "task_type": task_type.value,
        }

        # 尝试切换
        result = self.selector.fallback(provider_name, task_type)

        if result.success:
            switch_record["to_provider"] = result.provider_name
            switch_record["success"] = True
            self.set_current_provider(result.provider_name)
            logger.info(f"Auto-switched from {provider_name} to {result.provider_name}")
        else:
            switch_record["success"] = False
            switch_record["error"] = result.reason
            logger.error(f"Auto-switch failed: {result.reason}")

        with self._lock:
            self._switch_history.append(switch_record)

        return result

    def handle_rate_limit(
        self, provider_name: str, task_type: TaskType = TaskType.general
    ) -> SelectionResult:
        """处理速率限制情况

        当 Provider 达到速率限制时，自动切换到备用 Provider。

        Args:
            provider_name: 达到速率限制的 Provider
            task_type: 任务类型

        Returns:
            SelectionResult（切换后的 Provider）
        """
        logger.warning(f"Provider {provider_name} rate limit exceeded, attempting auto-switch")

        # 记录速率限制
        self.selector.record_failure(provider_name, "rate_limit")

        # 记录切换历史
        switch_record = {
            "from_provider": provider_name,
            "reason": "rate_limit",
            "timestamp": _now_iso(),
            "task_type": task_type.value,
        }

        # 尝试切换
        result = self.selector.fallback(provider_name, task_type)

        if result.success:
            switch_record["to_provider"] = result.provider_name
            switch_record["success"] = True
            self.set_current_provider(result.provider_name)
            logger.info(f"Auto-switched from {provider_name} to {result.provider_name}")
        else:
            switch_record["success"] = False
            switch_record["error"] = result.reason
            logger.error(f"Auto-switch failed: {result.reason}")

        with self._lock:
            self._switch_history.append(switch_record)

        return result

    def handle_error(
        self, provider_name: str, error_type: str, task_type: TaskType = TaskType.general
    ) -> SelectionResult:
        """处理错误情况

        当 Provider 发生错误时，根据错误类型决定是否切换。

        Args:
            provider_name: 发生错误的 Provider
            error_type: 错误类型
            task_type: 任务类型

        Returns:
            SelectionResult（切换后的 Provider）
        """
        logger.warning(f"Provider {provider_name} error: {error_type}")

        # 记录错误
        self.selector.record_failure(provider_name, error_type)

        # 检查是否需要切换
        provider = self.selector.get_provider_info(provider_name)
        if provider and provider.consecutive_failures >= self.selector.failure_threshold:
            # 连续失败次数达到阈值，需要切换
            return self.selector.fallback(provider_name, task_type)

        # 尝试继续使用当前 Provider（可能只是临时错误）
        current = self.get_current_provider()
        if current and self.selector._is_available(current):
            return self.selector.select(task_type, current)

        # 选择新的 Provider
        return self.selector.select(task_type)

    def get_switch_history(self, limit: int = 10) -> list[dict]:
        """获取切换历史"""
        with self._lock:
            return self._switch_history[-limit:]

    def get_switch_summary(self) -> dict:
        """获取切换统计摘要"""
        with self._lock:
            total_switches = len(self._switch_history)
            successful_switches = sum(1 for s in self._switch_history if s.get("success"))
            failed_switches = total_switches - successful_switches

            # 按原因统计
            by_reason = {}
            for s in self._switch_history:
                reason = s.get("reason", "unknown")
                by_reason[reason] = by_reason.get(reason, 0) + 1

            # 按Provider统计
            by_provider = {}
            for s in self._switch_history:
                from_provider = s.get("from_provider", "unknown")
                to_provider = s.get("to_provider", "unknown")
                if from_provider not in by_provider:
                    by_provider[from_provider] = {"switched_out": 0, "switched_in": 0}
                if to_provider not in by_provider:
                    by_provider[to_provider] = {"switched_out": 0, "switched_in": 0}
                by_provider[from_provider]["switched_out"] += 1
                if s.get("success"):
                    by_provider[to_provider]["switched_in"] += 1

            return {
                "totalSwitches": total_switches,
                "successfulSwitches": successful_switches,
                "failedSwitches": failed_switches,
                "successRate": successful_switches / total_switches if total_switches > 0 else 0,
                "byReason": by_reason,
                "byProvider": by_provider,
                "currentProvider": self._current_provider,
            }

    def reset_switch_history(self) -> None:
        """重置切换历史"""
        with self._lock:
            self._switch_history.clear()

    def check_and_recover(self) -> bool:
        """检查并恢复 Provider 状态

        检查是否有 Provider 从额度不足或冷却状态恢复。

        Returns:
            是否有 Provider 恢复
        """
        recovered = False

        for name, provider in self.selector.providers.items():
            if provider.status == ProviderStatus.quota_exceeded:
                # 检查额度是否恢复
                quota = self.selector.get_quota(name)
                if quota and quota.quota_reset_at:
                    try:
                        reset_time = datetime.fromisoformat(
                            quota.quota_reset_at.replace("Z", "+00:00")
                        )
                        if datetime.now(timezone.utc) > reset_time:
                            provider.status = ProviderStatus.available
                            quota.quota_remaining = quota.quota_limit
                            quota.quota_used = 0
                            recovered = True
                            logger.info(f"Provider {name} quota recovered")
                    except ValueError:
                        pass

            elif provider.status == ProviderStatus.cooldown:
                # 检查冷却是否结束
                if provider.last_failure_at:
                    try:
                        failure_time = datetime.fromisoformat(
                            provider.last_failure_at.replace("Z", "+00:00")
                        )
                        cooldown_end = failure_time.timestamp() + self.selector.cooldown_seconds
                        if time.time() > cooldown_end:
                            provider.status = ProviderStatus.available
                            provider.consecutive_failures = 0
                            recovered = True
                            logger.info(f"Provider {name} cooldown ended")
                    except ValueError:
                        pass

        return recovered

    def get_status_report(self) -> dict:
        """获取完整状态报告"""
        return {
            "teamName": self.team_name,
            "currentProvider": self._current_provider,
            "autoSwitchEnabled": self.auto_switch_enabled,
            "selectorSummary": self.selector.get_summary(),
            "switchSummary": self.get_switch_summary(),
            "availableProviders": self.selector.get_available_providers(),
        }


def get_auto_switch_manager(team_name: str) -> ProviderAutoSwitchManager:
    """获取 ProviderAutoSwitchManager 实例

    Args:
        team_name: 团队名称

    Returns:
        ProviderAutoSwitchManager 实例
    """
    return ProviderAutoSwitchManager(team_name)
