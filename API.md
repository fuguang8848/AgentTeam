# ClawTeam-OpenClaw API Documentation

> **Version**: v0.5.1 | **Base URL**: `http://localhost:8080/api/v1`

---

## Overview

ClawTeam provides a RESTful API for team management, agent orchestration, and monitoring. All endpoints require authentication via `X-ClawTeam-Token` header.

### Authentication

```bash
curl -H "X-ClawTeam-Token: your-token" http://localhost:8080/api/v1/teams
```

### Response Format

All responses are JSON:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

### Error Format

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "TEAM_NOT_FOUND",
    "message": "Team 'my-team' not found"
  }
}
```

---

## Teams API

### List Teams

```
GET /api/v1/teams
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "name": "my-team",
      "created_at": "2026-05-04T02:00:00Z",
      "agents": ["agent-1", "agent-2"],
      "status": "active"
    }
  ]
}
```

### Create Team

```
POST /api/v1/teams
```

**Body:**
```json
{
  "name": "my-team",
  "backend": "tmux",
  "transport": "file"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "my-team",
    "created_at": "2026-05-04T02:00:00Z",
    "agents": [],
    "status": "active"
  }
}
```

### Get Team Details

```
GET /api/v1/teams/{team_name}
```

### Delete Team

```
DELETE /api/v1/teams/{team_name}
```

**Response:**
```json
{
  "success": true,
  "data": { "deleted": "my-team" }
}
```

---

## Agents API

### List Agents

```
GET /api/v1/teams/{team_name}/agents
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "name": "agent-1",
      "agent_id": "agent-uuid",
      "backend": "tmux",
      "status": "running",
      "started_at": "2026-05-04T02:00:00Z"
    }
  ]
}
```

### Spawn Agent

```
POST /api/v1/teams/{team_name}/agents
```

**Body:**
```json
{
  "agent_name": "worker",
  "agent_type": "general-purpose",
  "prompt": "Analyze code quality",
  "model": "gpt-4",
  "parent_agent": "leader-agent-id"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "agent_id": "agent-uuid",
    "name": "worker",
    "status": "spawned"
  }
}
```

### Send Message to Agent

```
POST /api/v1/teams/{team_name}/agents/{agent_name}/messages
```

**Body:**
```json
{
  "content": "Analyze the code in /path/to/project",
  "type": "task"
}
```

### Get Agent Inbox

```
GET /api/v1/teams/{team_name}/agents/{agent_name}/inbox
```

### Terminate Agent

```
DELETE /api/v1/teams/{team_name}/agents/{agent_name}
```

**Response:**
```json
{
  "success": true,
  "data": { "terminated": "worker" }
}
```

### Terminate All Children

```
DELETE /api/v1/teams/{team_name}/agents/{agent_name}/children
```

---

## Sessions API

### List Sessions

```
GET /api/v1/sessions
```

**Query Parameters:**
- `team`: Filter by team name
- `status`: Filter by status (running/completed/failed)

### Get Session Details

```
GET /api/v1/sessions/{session_id}
```

### Send Message to Session

```
POST /api/v1/sessions/{session_id}/messages
```

**Body:**
```json
{
  "content": "Your task message here"
}
```

---

## Events API

### List Events

```
GET /api/v1/teams/{team_name}/events
```

**Query Parameters:**
- `type`: Filter by event type
- `limit`: Max events to return (default: 100)
- `offset`: Pagination offset

**Event Types:**
- `team.created`
- `team.deleted`
- `agent.spawned`
- `agent.terminated`
- `agent.message`
- `agent.error`

### Get Event Stream (SSE)

```
GET /api/v1/teams/{team_name}/events/stream
```

Returns Server-Sent Events stream for real-time updates.

---

## Board API

### Get Board Status

```
GET /api/v1/board/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "active_sessions": 5,
    "peak_concurrent": 10,
    "concurrent_limit": 10,
    "utilization_pct": 50
  }
}
```

### Get Active Sessions

```
GET /api/v1/board/sessions
```

### Get Board Logs

```
GET /api/v1/board/logs
```

**Query Parameters:**
- `level`: Log level (debug/info/warning/error)
- `limit`: Max logs to return

---

## Metrics API

### Get Usage Metrics

```
GET /api/v1/metrics/usage
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_tokens": 1000000,
    "total_cost_usd": 25.50,
    "by_model": {
      "gpt-4": { "tokens": 800000, "cost": 20.00 },
      "gpt-4o-mini": { "tokens": 200000, "cost": 5.50 }
    }
  }
}
```

### Get Token Usage Trend

```
GET /api/v1/metrics/usage/trend
```

**Query Parameters:**
- `period`: `daily` | `weekly` | `monthly`

---

## Auth API

### Get Auth Status

```
GET /api/v1/auth/status
```

### Update Auth Token

```
PUT /api/v1/auth/token
```

**Body:**
```json
{
  "token": "new-token-here"
}
```

---

## Configuration API

### Get Config

```
GET /api/v1/config
```

### Update Config

```
PUT /api/v1/config
```

**Body:**
```json
{
  "agents": {
    "max_concurrent": 10
  },
  "alerts": {
    "enabled": true
  }
}
```

---

## WebSocket API

### Board WebSocket

```
ws://localhost:8080/ws/board
```

**Protocol:**
```json
// Client → Server
{ "type": "subscribe", "channel": "sessions" }
{ "type": "send_message", "to": "agent-1", "content": "Hello" }

// Server → Client
{ "type": "session_update", "data": { ... } }
{ "type": "message", "from": "agent-1", "content": "Hello back" }
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/api/v1/*` | 100 requests/minute |
| `/ws/*` | 10 connections/minute |

---

## Error Codes

| Code | Description |
|------|-------------|
| `TEAM_NOT_FOUND` | Team does not exist |
| `AGENT_NOT_FOUND` | Agent does not exist |
| `SESSION_NOT_FOUND` | Session does not exist |
| `AUTH_REQUIRED` | Authentication token missing or invalid |
| `RATE_LIMITED` | Too many requests |
| `VALIDATION_ERROR` | Request body validation failed |
| `INTERNAL_ERROR` | Internal server error |

---

*Last updated: 2026-05-04*
