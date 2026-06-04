# Deployment Guide

## Quick Start with Docker

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### 1. Clone and Setup

```bash
git clone https://github.com/YOUR_USERNAME/AgentTeam-OpenClaw.git
cd AgentTeam-OpenClaw
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 3. Build and Run

```bash
# Build Docker image
docker build -t agentteam .

# Run with Docker Compose (includes optional Redis)
docker-compose up -d

# Or run standalone (no Redis)
docker run -p 8080:8080 agentteam
```

### 4. Verify

Open http://localhost:8080 in your browser.

## Manual Installation

### Prerequisites
- Python 3.10+
- pip or poetry

### 1. Install Dependencies

```bash
pip install poetry
poetry install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run

```bash
# Start the board server
python -m agentteam.board.server

# Or use the CLI
agentteam board serve --port 8080
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENCLAW_GATEWAY_TOKEN` | OpenClaw Gateway token | No |
| `OPENCLAW_GATEWAY_URL` | OpenClaw Gateway URL | No |
| `BAILIAN_API_KEY` | Bailian/LLM API key | No |
| `BOCHA_API_KEY` | Bocha search API key | No |
| `REDIS_URL` | Redis URL for message transport | No |

## Production Deployment

### Using systemd

```ini
[Unit]
Description=AgentTeam Board Server
After=network.target

[Service]
Type=simple
User=agentteam
WorkingDirectory=/opt/agentteam
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/agentteam/venv/bin/python -m agentteam.board.server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Using Supervisor

```ini
[program:agentteam]
command=/opt/agentteam/venv/bin/python -m agentteam.board.server
directory=/opt/agentteam
user=agentteam
autostart=true
autorestart=true
stderr_logfile=/var/log/agentteam.err.log
stdout_logfile=/var/log/agentteam.out.log
```

## Docker Compose Profiles

### Default (with Redis)
```bash
docker-compose up -d
```

### Minimal (no Redis)
```bash
docker-compose up -d agentteam
```

### With Redis Commander (debugging)
```bash
docker-compose --profile debug up -d
```

## Health Checks

### Docker Health Check
```bash
docker inspect --format='{{.State.Health.Status}}' agentteam-agentteam-1
```

### API Health Check
```bash
curl http://localhost:8080/api/overview
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs agentteam

# Check environment
docker-compose exec agentteam env
```

### Port Already in Use
```bash
# Change port in docker-compose.yml or
docker-compose down
docker-compose up -d
```

### Permission Denied
```bash
# Fix ownership
sudo chown -R 1000:1000 ./data ./tmp
```
