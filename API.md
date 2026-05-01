# ClawTeam API Reference

## Board Server API

The ClawTeam Board Server provides a REST API for managing teams, tasks, and sessions.

**Base URL**: `http://localhost:8080`

### Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve web UI |
| GET | `/api/overview` | Get system overview |
| GET | `/api/team/{name}` | Get team details |
| POST | `/api/team/{name}/task` | Create task |
| PATCH | `/api/team/{name}/task/{id}` | Update task |
| DELETE | `/api/team/{name}/task/{id}` | Delete task |
| GET | `/api/team/{name}/events` | Get team events (SSE) |
| POST | `/api/chat` | AI chat endpoint |
| GET | `/api/usage/summary` | Token usage summary |
| GET | `/api/usage/trend` | Token usage trend |
| GET | `/api/usage/providers` | Provider usage breakdown |

---

## Authentication

Most endpoints don't require authentication. For AI features:

```bash
# Set gateway token in environment
export OPENCLAW_GATEWAY_TOKEN="your-token"
export OPENCLAW_GATEWAY_URL="http://localhost:18789"
```

---

## Endpoints

### GET /

Serves the web UI HTML page.

**Response**: HTML page

---

### GET /api/overview

Get system overview including all teams and their status.

**Response**:
```json
{
  "teams": [
    {
      "name": "my-team",
      "description": "My team",
      "active_sessions": 2,
      "session_count": 10,
      "tasks": {
        "total": 5,
        "todo": 1,
        "in_progress": 2,
        "done": 2
      },
      "members": [
        {
          "name": "leader",
          "status": "active",
          "inbox_count": 0
        }
      ]
    }
  ],
  "summary": {
    "total_teams": 1,
    "active_sessions": 2
  }
}
```

---

### GET /api/team/{name}

Get detailed team information.

**Parameters**:
- `name` (path): Team name

**Response**:
```json
{
  "name": "my-team",
  "description": "Team description",
  "active_sessions": 2,
  "session_count": 10,
  "created_at": "2026-05-01T10:00:00Z",
  "tasks": [...],
  "members": [...],
  "events": [...]
}
```

---

### POST /api/team/{name}/task

Create a new task in a team.

**Parameters**:
- `name` (path): Team name

**Request Body**:
```json
{
  "title": "Task title",
  "description": "Task description",
  "priority": "medium",
  "owner": "agent-name"
}
```

**Response**:
```json
{
  "id": "task-123",
  "title": "Task title",
  "status": "todo",
  "priority": "medium",
  "owner": "agent-name",
  "created_at": "2026-05-01T10:00:00Z"
}
```

---

### PATCH /api/team/{name}/task/{id}

Update a task's status or attributes.

**Parameters**:
- `name` (path): Team name
- `id` (path): Task ID

**Request Body**:
```json
{
  "status": "in_progress",
  "owner": "new-owner"
}
```

**Response**:
```json
{
  "id": "task-123",
  "status": "in_progress",
  "owner": "new-owner"
}
```

---

### DELETE /api/team/{name}/task/{id}

Delete a task.

**Parameters**:
- `name` (path): Team name
- `id` (path): Task ID

**Response**:
```json
{
  "status": "ok"
}
```

---

### GET /api/team/{name}/events

Server-Sent Events (SSE) endpoint for real-time team updates.

**Parameters**:
- `name` (path): Team name

**Response**: SSE stream with events:
```
event: task_update
data: {"task_id": "123", "status": "done"}

event: member_joined
data: {"member": "alice"}
```

---

### POST /api/chat

AI chat endpoint for conversational interaction.

**Request Body**:
```json
{
  "message": "Hello, create a new team for me",
  "history": [
    {"role": "user", "text": "Hi"},
    {"role": "assistant", "text": "Hello! How can I help?"}
  ]
}
```

**Response**:
```json
{
  "response": "Sure, I can help you create a team. What would you like to name it?",
  "message": "Hello, create a new team for me",
  "timestamp": "2026-05-01T10:00:00Z"
}
```

---

### GET /api/usage/summary

Get token usage summary across all providers.

**Response**:
```json
{
  "total_tokens": 150000,
  "total_cost": 0.45,
  "by_provider": {
    "minimax": {"tokens": 100000, "cost": 0.30},
    "bailian": {"tokens": 50000, "cost": 0.15}
  }
}
```

---

### GET /api/usage/trend

Get token usage trend over time.

**Query Parameters**:
- `days` (optional): Number of days to look back (default: 7)

**Response**:
```json
{
  "trend": [
    {"date": "2026-05-01", "tokens": 5000},
    {"date": "2026-05-02", "tokens": 7500}
  ]
}
```

---

### GET /api/usage/providers

Get detailed usage breakdown by provider.

**Response**:
```json
{
  "providers": {
    "minimax": {
      "calls": 150,
      "tokens": 100000,
      "cost": 0.30
    }
  }
}
```

---

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request
```json
{
  "error": "Invalid request parameters",
  "details": "Missing required field: name"
}
```

### 404 Not Found
```json
{
  "error": "Team not found",
  "team": "nonexistent-team"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "details": "Database connection failed"
}
```

---

## Rate Limiting

Currently no rate limiting is enforced. Future versions may implement per-IP or per-token rate limits.

---

## WebSocket (Future)

WebSocket support for bidirectional communication is planned for future versions.

---

## CLI Reference

For command-line usage, see [CLI.md](CLI.md).
