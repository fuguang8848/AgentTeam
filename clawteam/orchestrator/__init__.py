"""Orchestrator module for ClawTeam multi-agent teams.

This module provides:
- Provider selection with intelligent routing
- Automatic fallback when providers are unavailable
- Quota/limit detection and management
- Task orchestration and coordination
"""

from clawteam.orchestrator.provider_selector import (
    ProviderSelector,
    ProviderInfo,
    ProviderStatus,
    QuotaInfo,
    SelectionResult,
    FallbackChain,
)

__all__ = [
    "ProviderSelector",
    "ProviderInfo",
    "ProviderStatus",
    "QuotaInfo",
    "SelectionResult",
    "FallbackChain",
]
