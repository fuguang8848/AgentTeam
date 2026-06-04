# AgentTeam Makefile
# Common development commands

.PHONY: help install test lint format clean docker-build docker-run docker-stop

# Default target
help:
	@echo "AgentTeam Development Commands"
	@echo ""
	@echo "  make install        Install dependencies"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linters"
	@echo "  make format         Format code"
	@echo "  make clean          Clean temporary files"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-run     Run Docker container"
	@echo "  make docker-stop    Stop Docker container"

# Install dependencies
install:
	poetry install

# Run tests
test:
	poetry run pytest tests/ -v

# Run tests with coverage
test-cov:
	poetry run pytest tests/ --cov=agentteam --cov-report=html

# Run linters
lint:
	poetry run ruff check agentteam/

# Format code
format:
	poetry run ruff format agentteam/

# Clean temporary files
clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache
	rm -rf htmlcov .coverage
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build Docker image
docker-build:
	docker build -t agentteam .

# Run Docker container (foreground)
docker-run:
	docker run -p 8080:8080 --env-file .env agentteam

# Run Docker Compose
docker-up:
	docker-compose up -d

# Stop Docker Compose
docker-stop:
	docker-compose down

# Docker development (with file watching)
docker-dev:
	docker-compose up --build

# Full development setup
dev: install test lint
	@echo "Development environment ready!"
