# AgentTeam-OpenClaw Deployment Guide

> **Version**: v0.5.1

---

## Overview

AgentTeam-OpenClaw can be deployed in various configurations:

- **Development**: Single machine, local testing
- **Production**: Multi-machine, high availability
- **Cloud**: AWS, GCP, Azure, or other cloud providers
- **Docker**: Containerized deployment

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 10 GB | 50+ GB |
| OS | Ubuntu 20.04 / macOS 12 / Windows 10 | Ubuntu 22.04 |

### Software Requirements

- Python 3.10+
- Git
- tmux (Linux/macOS for tmux backend)
- Redis (optional, for Redis transport)

---

## Installation

### From PyPI (Stable Release)

```bash
pip install AgentTeam-openclaw

# Verify installation
agentteam --version
```

### From Source (Development)

```bash
# Clone repository
git clone https://github.com/YintaTriss/AgentTeam-OpenClaw.git
cd AgentTeam-OpenClaw

# Install in development mode
pip install -e ".[dev]"

# Or use poetry
poetry install
```

### Docker

```bash
# Pull from Docker Hub
docker pull yintatriss/AgentTeam-openclaw:latest

# Run container
docker run -d \
  --name agentteam \
  -p 8080:8080 \
  -v ~/.agentteam:/root/.agentteam \
  yintatriss/AgentTeam-openclaw:latest
```

---

## Configuration

### Basic Configuration

Create `config.yaml` in the working directory:

```yaml
# Application settings
app:
  name: AgentTeam
  debug: false

# Team defaults
team:
  default_backend: tmux
  default_transport: file

# Agent settings
agents:
  max_concurrent: 10
  spawn_timeout: 60
  retry_attempts: 3

# Logging
logging:
  level: info
  file: logs/agentteam.log

# API settings
api:
  host: 0.0.0.0
  port: 8080
  auth_token: your-secret-token

# Database
database:
  type: sqlite
  path: data/agentteam.db

# Alerts
alerts:
  enabled: false
  webhook_url: ""
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AgentTeam_DATA_DIR` | Data directory | `~/.agentteam` |
| `AgentTeam_CONFIG` | Config file path | `./config.yaml` |
| `AgentTeam_AUTH_TOKEN` | API auth token | (none) |
| `AgentTeam_LOG_LEVEL` | Log level | `info` |
| `AgentTeam_DB_PATH` | Database path | `data/agentteam.db` |

---

## Deployment Modes

### Standalone (Development)

```bash
# Start web board
agentteam board serve --port 8080 --auth your-token

# In another terminal, create a team
agentteam team create my-team

# Spawn an agent
agentteam spawn --team my-team --agent-name worker \
  --prompt "Analyze data"
```

### Production Deployment

#### Using systemd (Linux)

```ini
# /etc/systemd/system/agentteam.service
[Unit]
Description=AgentTeam-OpenClaw
After=network.target

[Service]
Type=simple
User=agentteam
WorkingDirectory=/opt/agentteam
ExecStart=/opt/agentteam/venv/bin/agentteam board serve --port 8080 --auth your-token
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Install service
sudo systemctl daemon-reload
sudo systemctl enable agentteam
sudo systemctl start agentteam

# Check status
sudo systemctl status agentteam
```

#### Using pm2 (Node.js process manager alternative)

```bash
# Install pm2
npm install -g pm2

# Create start script
echo '#!/bin/bash
agentteam board serve --port 8080 --auth $AUTH_TOKEN' > start.sh
chmod +x start.sh

# Start with pm2
pm2 start start.sh --name agentteam

# Save process list
pm2 save

# Setup startup script
pm2 startup
```

---

## Docker Deployment

### Docker Compose (Recommended for Production)

```yaml
# docker-compose.yml
version: '3.8'

services:
  agentteam:
    image: yintatriss/AgentTeam-openclaw:latest
    container_name: agentteam
    ports:
      - "8080:8080"
    volumes:
      - ./data:/root/.agentteam
      - ./config.yaml:/app/config.yaml:ro
    environment:
      - AgentTeam_AUTH_TOKEN=${AUTH_TOKEN}
      - AgentTeam_LOG_LEVEL=info
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/board/status"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: agentteam-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f agentteam

# Scale agents
docker-compose up -d --scale agentteam=3
```

### Production Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 agentteam
USER agentteam

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/board/status || exit 1

# Run application
CMD ["agentteam", "board", "serve", "--port", "8080", "--auth", "${AUTH_TOKEN}"]
```

---

## Cloud Deployment

### AWS (EC2 + ECS)

```bash
# Build Docker image
docker build -t agentteam:latest .

# Tag for ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
docker tag agentteam:latest $ECR_REGISTRY/AgentTeam:latest
docker push $ECR_REGISTRY/AgentTeam:latest

# Deploy to ECS using docker-compose.ecs.yml
```

### Google Cloud Platform

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/$PROJECT_ID/AgentTeam:latest

# Deploy to Cloud Run
gcloud run deploy agentteam \
    --image gcr.io/$PROJECT_ID/AgentTeam:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

### Azure

```bash
# Build and push to ACR
az acr build --registry $ACR_NAME --image agentteam:latest .

# Deploy to Azure Container Instances
az container create \
    --resource-group $RG \
    --name agentteam \
    --image $ACR_NAME.azurecr.io/AgentTeam:latest \
    --dns-name-label AgentTeam-$RANDOM \
    --ports 8080
```

---

## High Availability

### Multi-Node Setup

For high availability, deploy multiple AgentTeam instances:

```
                    âââââââââââââââ?
                    â?  Nginx     â?
                    â? (LB)      â?
                    ââââââââ¬âââââââ?
                           â?
         âââââââââââââââââââ¼ââââââââââââââââââ?
         â?                â?                â?
    ââââââ¼âââââ?     ââââââ¼âââââ?     ââââââ¼âââââ?
    â?Node 1  â?     â?Node 2  â?     â?Node 3  â?
    âAgentTeam â?     âAgentTeam â?     âAgentTeam â?
    ââââââ¬âââââ?     ââââââ¬âââââ?     ââââââ¬âââââ?
         â?                â?                â?
         âââââââââââââââââââ¼ââââââââââââââââââ?
                           â?
                    ââââââââ¼âââââââ?
                    â?   Redis    â?
                    â? (Shared)   â?
                    âââââââââââââââ?
```

**Requirements:**
- Shared Redis for message transport
- NFS/shared storage for agent workspaces
- Load balancer for API requests

### Nginx Configuration

```nginx
upstream agentteam {
    least_conn;
    server node1:8080;
    server node2:8080;
    server node3:8080;
}

server {
    listen 80;
    server_name agentteam.example.com;

    location / {
        proxy_pass http://agentteam;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://agentteam;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Security

### Authentication

Always set an auth token:

```bash
agentteam board serve --auth $(openssl rand -hex 32)
```

### Firewall

```bash
# UFW example (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### SSL/TLS

```bash
# Using certbot (Let's Encrypt)
sudo certbot --nginx -d agentteam.example.com

# Or reverse proxy with SSL termination
```

### Secrets Management

```bash
# Use environment variables for secrets
export AgentTeam_AUTH_TOKEN="your-secure-token"
export DATABASE_URL="postgresql://user:pass@host/db"

# Or use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
```

---

## Monitoring

### Health Check Endpoint

```bash
# Check health
curl http://localhost:8080/api/v1/board/status

# Expected response
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

### Prometheus Metrics

If metrics are enabled:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'agentteam'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/api/v1/metrics'
```

### Logging

```bash
# View logs (systemd)
journalctl -u agentteam -f

# View logs (Docker)
docker logs -f agentteam

# View logs (direct)
tail -f logs/agentteam.log
```

---

## Backup and Recovery

### Database Backup

```bash
# SQLite
cp ~/.agentteam/data/agentteam.db backup/agentteam-$(date +%Y%m%d).db

# PostgreSQL (if using)
pg_dump -U agentteam agentteam > backup/agentteam-$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
# SQLite
cp backup/agentteam-20260504.db ~/.agentteam/data/agentteam.db

# PostgreSQL
psql -U agentteam agentteam < backup/agentteam-20260504.sql
```

### Disaster Recovery Plan

1. **Database**: Nightly backups, retain 30 days
2. **Configuration**: Store in Git, version controlled
3. **Workspaces**: Use shared storage with snapshots
4. **Recovery Time Objective (RTO)**: < 1 hour
5. **Recovery Point Objective (RPO)**: < 24 hours

---

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Find and kill process using port 8080
lsof -i :8080
kill -9 <PID>
```

**Permission denied:**
```bash
# Fix data directory permissions
sudo chown -R $(whoami) ~/.agentteam
```

**tmux not found (Linux):**
```bash
# Install tmux
sudo apt-get install tmux

# Or use openclaw_sdk backend instead
agentteam team create my-team --backend openclaw_sdk
```

### Debug Mode

```bash
# Enable debug logging
export AgentTeam_LOG_LEVEL=debug
agentteam board serve --debug

# Or in config.yaml
logging:
  level: debug
```

### Reset Installation

```bash
# Stop all services
pkill -f agentteam

# Backup data
cp -r ~/.agentteam ~/.agentteam.backup

# Remove data directory
rm -rf ~/.agentteam

# Reinstall
pip install --force-reinstall AgentTeam-openclaw
```

---

## Performance Tuning

### Agent Pool Size

```yaml
# config.yaml
agents:
  max_concurrent: 20  # Increase for more parallelism
  spawn_timeout: 120  # Increase for slower operations
```

### Database Optimization

```bash
# SQLite optimization
sqlite3 ~/.agentteam/data/agentteam.db "VACUUM;"
sqlite3 ~/.agentteam/data/agentteam.db "PRAGMA journal_mode=WAL;"
```

### Memory Usage

Monitor memory and adjust based on workload:
```bash
watch -n 1 'free -h'
```

---

## Support

- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: https://github.com/YintaTriss/AgentTeam-OpenClaw#readme
- **Discord**: OpenClaw community server

---

*Last updated: 2026-05-04*
