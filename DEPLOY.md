# Deployment Guide

## Quick Start with Docker

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### 1. Clone and Setup

```bash
git clone https://github.com/YOUR_USERNAME/ClawTeam-OpenClaw.git
cd ClawTeam-OpenClaw
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
docker build -t clawteam .

# Run with Docker Compose (includes optional Redis)
docker-compose up -d

# Or run standalone (no Redis)
docker run -p 8080:8080 clawteam
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
python -m clawteam.board.server

# Or use the CLI
clawteam board serve --port 8080
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
Description=ClawTeam Board Server
After=network.target

[Service]
Type=simple
User=clawteam
WorkingDirectory=/opt/clawteam
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/clawteam/venv/bin/python -m clawteam.board.server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Using Supervisor

```ini
[program:clawteam]
command=/opt/clawteam/venv/bin/python -m clawteam.board.server
directory=/opt/clawteam
user=clawteam
autostart=true
autorestart=true
stderr_logfile=/var/log/clawteam.err.log
stdout_logfile=/var/log/clawteam.out.log
```

## Docker Compose Profiles

### Default (with Redis)
```bash
docker-compose up -d
```

### Minimal (no Redis)
```bash
docker-compose up -d clawteam
```

### With Redis Commander (debugging)
```bash
docker-compose --profile debug up -d
```

## Health Checks

### Docker Health Check
```bash
docker inspect --format='{{.State.Health.Status}}' clawteam-clawteam-1
```

### API Health Check
```bash
curl http://localhost:8080/api/overview
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs clawteam

# Check environment
docker-compose exec clawteam env
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
