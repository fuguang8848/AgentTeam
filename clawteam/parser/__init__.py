"""Output parsing engine for ClawTeam multi-agent teams.

Parses AI provider outputs, detects activity events, estimates token usage,
and supports multiple provider formats (Claude Code, Codex, Gemini, etc.).

Inspired by SpectrAI's OutputParser.ts.
"""

from clawteam.parser.output_parser import OutputParser, get_parser, parse_output
from clawteam.parser.types import (
    ActivityEvent,
    ActivityEventType,
    ParserState,
    ParserRule,
    ConfirmationDetection,
    UsageSummary,
)
from clawteam.parser.rules import PARSER_RULES
from clawteam.parser.confirmation_detector import (
    ConfirmationDetector,
    ProviderConfirmationConfig,
    detect_confirmation,
    get_default_detector,
)
from clawteam.parser.usage_estimator import UsageEstimator
from clawteam.parser.integration import (
    ClawTeamIntegration,
    get_integration,
    parse_and_notify,
    remove_integration,
)

__all__ = [
    # Core parser
    "OutputParser",
    "get_parser",
    "parse_output",
    # Types
    "ActivityEvent",
    "ActivityEventType",
    "ParserState",
    "ParserRule",
    "ConfirmationDetection",
    "UsageSummary",
    # Rules
    "PARSER_RULES",
    # Confirmation detector
    "ConfirmationDetector",
    "ProviderConfirmationConfig",
    "detect_confirmation",
    "get_default_detector",
    # Usage estimator
    "UsageEstimator",
    # Integration
    "ClawTeamIntegration",
    "get_integration",
    "parse_and_notify",
    "remove_integration",
]