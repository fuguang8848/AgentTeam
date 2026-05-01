# ClawTeam Makefile
# Common development commands

.PHONY: help install test lint format clean docker-build docker-run docker-stop

# Default target
help:
	@echo "ClawTeam Development Commands"
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
	poetry run pytest tests/ --cov=clawteam --cov-report=html

# Run linters
lint:
	poetry run ruff check clawteam/

# Format code
format:
	poetry run ruff format clawteam/

# Clean temporary files
clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache
	rm -rf htmlcov .coverage
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build Docker image
docker-build:
	docker build -t clawteam .

# Run Docker container (foreground)
docker-run:
	docker run -p 8080:8080 --env-file .env clawteam

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
