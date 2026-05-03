# ClawTeam-OpenClaw Deployment Guide

> **Version**: v0.5.1

---

## Overview

ClawTeam-OpenClaw can be deployed in various configurations:

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
pip install clawteam-openclaw

# Verify installation
clawteam --version
```

### From Source (Development)

```bash
# Clone repository
git clone https://github.com/YintaTriss/ClawTeam-OpenClaw.git
cd ClawTeam-OpenClaw

# Install in development mode
pip install -e ".[dev]"

# Or use poetry
poetry install
```

### Docker

```bash
# Pull from Docker Hub
docker pull yintatriss/clawteam-openclaw:latest

# Run container
docker run -d \
  --name clawteam \
  -p 8080:8080 \
  -v ~/.clawteam:/root/.clawteam \
  yintatriss/clawteam-openclaw:latest
```

---

## Configuration

### Basic Configuration

Create `config.yaml` in the working directory:

```yaml
# Application settings
app:
  name: ClawTeam
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
  file: logs/clawteam.log

# API settings
api:
  host: 0.0.0.0
  port: 8080
  auth_token: your-secret-token

# Database
database:
  type: sqlite
  path: data/clawteam.db

# Alerts
alerts:
  enabled: false
  webhook_url: ""
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAWTEAM_DATA_DIR` | Data directory | `~/.clawteam` |
| `CLAWTEAM_CONFIG` | Config file path | `./config.yaml` |
| `CLAWTEAM_AUTH_TOKEN` | API auth token | (none) |
| `CLAWTEAM_LOG_LEVEL` | Log level | `info` |
| `CLAWTEAM_DB_PATH` | Database path | `data/clawteam.db` |

---

## Deployment Modes

### Standalone (Development)

```bash
# Start web board
clawteam board serve --port 8080 --auth your-token

# In another terminal, create a team
clawteam team create my-team

# Spawn an agent
clawteam spawn --team my-team --agent-name worker \
  --prompt "Analyze data"
```

### Production Deployment

#### Using systemd (Linux)

```ini
# /etc/systemd/system/clawteam.service
[Unit]
Description=ClawTeam-OpenClaw
After=network.target

[Service]
Type=simple
User=clawteam
WorkingDirectory=/opt/clawteam
ExecStart=/opt/clawteam/venv/bin/clawteam board serve --port 8080 --auth your-token
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Install service
sudo systemctl daemon-reload
sudo systemctl enable clawteam
sudo systemctl start clawteam

# Check status
sudo systemctl status clawteam
```

#### Using pm2 (Node.js process manager alternative)

```bash
# Install pm2
npm install -g pm2

# Create start script
echo '#!/bin/bash
clawteam board serve --port 8080 --auth $AUTH_TOKEN' > start.sh
chmod +x start.sh

# Start with pm2
pm2 start start.sh --name clawteam

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
  clawteam:
    image: yintatriss/clawteam-openclaw:latest
    container_name: clawteam
    ports:
      - "8080:8080"
    volumes:
      - ./data:/root/.clawteam
      - ./config.yaml:/app/config.yaml:ro
    environment:
      - CLAWTEAM_AUTH_TOKEN=${AUTH_TOKEN}
      - CLAWTEAM_LOG_LEVEL=info
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/board/status"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: clawteam-redis
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
docker-compose logs -f clawteam

# Scale agents
docker-compose up -d --scale clawteam=3
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
RUN useradd -m -u 1000 clawteam
USER clawteam

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/board/status || exit 1

# Run application
CMD ["clawteam", "board", "serve", "--port", "8080", "--auth", "${AUTH_TOKEN}"]
```

---

## Cloud Deployment

### AWS (EC2 + ECS)

```bash
# Build Docker image
docker build -t clawteam:latest .

# Tag for ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
docker tag clawteam:latest $ECR_REGISTRY/clawteam:latest
docker push $ECR_REGISTRY/clawteam:latest

# Deploy to ECS using docker-compose.ecs.yml
```

### Google Cloud Platform

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/$PROJECT_ID/clawteam:latest

# Deploy to Cloud Run
gcloud run deploy clawteam \
    --image gcr.io/$PROJECT_ID/clawteam:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

### Azure

```bash
# Build and push to ACR
az acr build --registry $ACR_NAME --image clawteam:latest .

# Deploy to Azure Container Instances
az container create \
    --resource-group $RG \
    --name clawteam \
    --image $ACR_NAME.azurecr.io/clawteam:latest \
    --dns-name-label clawteam-$RANDOM \
    --ports 8080
```

---

## High Availability

### Multi-Node Setup

For high availability, deploy multiple ClawTeam instances:

```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (LB)      │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │ Node 1  │      │ Node 2  │      │ Node 3  │
    │ClawTeam │      │ClawTeam │      │ClawTeam │
    └────┬────┘      └────┬────┘      └────┬────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    │  (Shared)   │
                    └─────────────┘
```

**Requirements:**
- Shared Redis for message transport
- NFS/shared storage for agent workspaces
- Load balancer for API requests

### Nginx Configuration

```nginx
upstream clawteam {
    least_conn;
    server node1:8080;
    server node2:8080;
    server node3:8080;
}

server {
    listen 80;
    server_name clawteam.example.com;

    location / {
        proxy_pass http://clawteam;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://clawteam;
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
clawteam board serve --auth $(openssl rand -hex 32)
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
sudo certbot --nginx -d clawteam.example.com

# Or reverse proxy with SSL termination
```

### Secrets Management

```bash
# Use environment variables for secrets
export CLAWTEAM_AUTH_TOKEN="your-secure-token"
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
  - job_name: 'clawteam'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/api/v1/metrics'
```

### Logging

```bash
# View logs (systemd)
journalctl -u clawteam -f

# View logs (Docker)
docker logs -f clawteam

# View logs (direct)
tail -f logs/clawteam.log
```

---

## Backup and Recovery

### Database Backup

```bash
# SQLite
cp ~/.clawteam/data/clawteam.db backup/clawteam-$(date +%Y%m%d).db

# PostgreSQL (if using)
pg_dump -U clawteam clawteam > backup/clawteam-$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
# SQLite
cp backup/clawteam-20260504.db ~/.clawteam/data/clawteam.db

# PostgreSQL
psql -U clawteam clawteam < backup/clawteam-20260504.sql
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
sudo chown -R $(whoami) ~/.clawteam
```

**tmux not found (Linux):**
```bash
# Install tmux
sudo apt-get install tmux

# Or use openclaw_sdk backend instead
clawteam team create my-team --backend openclaw_sdk
```

### Debug Mode

```bash
# Enable debug logging
export CLAWTEAM_LOG_LEVEL=debug
clawteam board serve --debug

# Or in config.yaml
logging:
  level: debug
```

### Reset Installation

```bash
# Stop all services
pkill -f clawteam

# Backup data
cp -r ~/.clawteam ~/.clawteam.backup

# Remove data directory
rm -rf ~/.clawteam

# Reinstall
pip install --force-reinstall clawteam-openclaw
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
sqlite3 ~/.clawteam/data/clawteam.db "VACUUM;"
sqlite3 ~/.clawteam/data/clawteam.db "PRAGMA journal_mode=WAL;"
```

### Memory Usage

Monitor memory and adjust based on workload:
```bash
watch -n 1 'free -h'
```

---

## Support

- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: https://github.com/YintaTriss/ClawTeam-OpenClaw#readme
- **Discord**: OpenClaw community server

---

*Last updated: 2026-05-04*
