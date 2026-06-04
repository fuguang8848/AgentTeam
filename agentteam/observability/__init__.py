"""
AgentTeam Observability Module

Provides OpenTelemetry integration for distributed tracing,
metrics collection, and structured logging.

Usage:
    from agentteam.observability import tracer, meter, get_logger
    
    # Tracing
    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("key", "value")
        # do work
    
    # Metrics
    counter = meter.create_counter("requests_total")
    counter.add(1, {"route": "/api"})
    
    # Logging
    logger = get_logger(__name__)
    logger.info("Operation completed", extra={"duration_ms": 123})
"""

from agentteam.observability.tracer import tracer, TracerWrapper
from agentteam.observability.meter import meter, MeterWrapper
from agentteam.observability.logger import get_logger, StructuredLogger
from agentteam.observability.exporter import (
    setup_exporter,
    ExporterType,
    get_tracer_provider,
    get_meter_provider,
)

__all__ = [
    # Tracer
    "tracer",
    "TracerWrapper",
    # Meter
    "meter",
    "MeterWrapper",
    # Logger
    "get_logger",
    "StructuredLogger",
    # Exporter
    "setup_exporter",
    "ExporterType",
    "get_tracer_provider",
    "get_meter_provider",
]

# Default span names for AgentTeam operations
SPAN_TEAM_CREATE = "agentteam.team.create"
SPAN_AGENT_SPAWN = "agentteam.agent.spawn"
SPAN_TASK_EXECUTE = "agentteam.task.execute"
SPAN_MESSAGE_SEND = "agentteam.message.send"
SPAN_TOOL_INVOKE = "agentteam.tool.invoke"

# Default metric names
METRIC_AGENTS_TOTAL = "agentteam_agents_total"
METRIC_TASKS_TOTAL = "agentteam_tasks_total"
METRIC_MESSAGES_TOTAL = "agentteam_messages_total"
METRIC_TASK_DURATION = "agentteam_task_duration_seconds"
METRIC_AGENT_SPAWN_DURATION = "agentteam_agent_spawn_duration_seconds"
