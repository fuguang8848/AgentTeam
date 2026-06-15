# syntax=docker/dockerfile:1
FROM python:3.10-slim

LABEL maintainer="AgentTeam"
LABEL description="Multi-agent swarm coordination for CLI coding agents"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only dependency files first for better caching
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 agentteam && \
    chown -R agentteam:agentteam /app
USER agentteam

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV AGENTEAM_HOME=/app

# Default command - start the board server
CMD ["python", "-m", "agentteam.board.server"]

# Expose default ports
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/')" || exit 1
