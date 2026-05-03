# Contributing to ClawTeam-OpenClaw

Thank you for your interest in contributing to ClawTeam-OpenClaw! This document provides guidelines and instructions for contributing.

---

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone. We do not tolerate harassment or discrimination of any kind.

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- tmux (optional, for Linux/macOS)
- Redis (optional, for Redis transport)

### Fork and Clone

```bash
# Fork the repository on GitHub

# Clone your fork
git clone https://github.com/YOUR_USERNAME/ClawTeam-OpenClaw.git
cd ClawTeam-OpenClaw

# Add upstream remote
git remote add upstream https://github.com/YintaTriss/ClawTeam-OpenClaw.git
```

### Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -e ".[dev]"

# Or use poetry
poetry install
```

### Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_team.py

# Run with coverage
pytest --cov=clawteam tests/

# Run linting
ruff check clawteam/
ruff format --check clawteam/
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/my-new-feature
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Write clean, readable code
- Follow the existing code style (PEP 8)
- Add type hints where possible
- Write docstrings for public APIs

### 3. Write Tests

```bash
# Create test file
touch tests/test_my_feature.py

# Run tests for your feature
pytest tests/test_my_feature.py -v
```

**Test Guidelines:**
- All new features should have tests
- Bug fixes should include a test that reproduces the bug
- Use descriptive test names: `test_<feature>_<behavior>`
- Keep tests focused and independent

### 4. Run the Full Test Suite

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=clawteam --cov-report=html tests/

# Run linting
ruff check clawteam/
ruff format --check clawteam/

# Type checking
pyright clawteam/
```

### 5. Commit Your Changes

```bash
# Stage changes
git add .

# Commit with conventional commit format
git commit -m "feat(module): add new feature"

# Or for bug fixes
git commit -m "fix(module): resolve issue with..."
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, whitespace)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### 6. Push and Create PR

```bash
# Push to your fork
git push origin feature/my-new-feature

# Create pull request on GitHub
# Target: YintaTriss/ClawTeam-OpenClaw main branch
```

---

## Pull Request Guidelines

### PR Description

Include in your PR description:
- **Summary**: Brief description of changes
- **Motivation**: Why this change is needed
- **Changes**: Detailed list of changes
- **Testing**: How you tested the changes
- **Screenshots**: For UI changes

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows the style guidelines
- [ ] Documentation updated (if applicable)
- [ ] Changes are atomic (one logical change per PR)
- [ ] PR description is complete

### Review Process

1. Automated checks must pass (CI/CD)
2. At least one review approval required
3. Address all review comments
4. Keep PR focused and small when possible

---

## Project Structure

```
ClawTeam-OpenClaw/
├── clawteam/           # Main source code
│   ├── api/           # REST API
│   ├── board/         # Web dashboard
│   ├── cli/           # CLI commands
│   ├── collaboration/  # Collaboration features
│   ├── database/      # Database layer
│   ├── events/        # Event tracking
│   ├── notifications/  # Notification system
│   ├── orchestrator/  # Task orchestration
│   ├── spawn/         # Agent spawning
│   ├── team/          # Team management
│   ├── transport/     # Message transport
│   └── utils/         # Utilities
├── tests/             # Test suite
├── docs/              # Documentation
├── examples/          # Example configurations
└── scripts/           # Build/utility scripts
```

---

## Coding Standards

### Python Style

- Follow PEP 8
- Line length: 88 characters (Black default)
- Use type hints for function signatures
- Docstrings: Google style

**Example:**
```python
def process_agent_message(
    agent_id: str,
    message: str,
    team_name: str = "default"
) -> dict[str, Any]:
    """Process a message from an agent.

    Args:
        agent_id: Unique identifier for the agent.
        message: The message content to process.
        team_name: Name of the team (default: "default").

    Returns:
        Dictionary containing the processing result.

    Raises:
        ValueError: If agent_id is empty.
        RuntimeError: If processing fails.
    """
    if not agent_id:
        raise ValueError("agent_id cannot be empty")
    
    # Implementation...
    return {"status": "processed", "agent_id": agent_id}
```

### Error Handling

- Use specific exception types
- Include context in error messages
- Log errors at appropriate level
- Never expose sensitive information in errors

### Logging

```python
from clawteam.utils.logger import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debug information")
logger.info("General informational message")
logger.warning("Warning about potential issue")
logger.error("Error occurred", exc_info=True)
```

---

## Documentation Guidelines

### Code Documentation

- Public APIs must have docstrings
- Complex logic should have inline comments
- Keep comments up-to-date with code

### README Updates

If your changes affect:
- Installation process → Update README.md
- New features → Update CAPABILITIES.md
- Breaking changes → Document in README.md

### API Documentation

If your changes add/modify API endpoints:
- Update API.md with endpoint details
- Include request/response examples
- Document error codes

---

## Testing Guidelines

### Test Structure

```python
import pytest
from clawteam.team.manager import TeamManager

class TestTeamManager:
    """Tests for TeamManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = TeamManager()
        self.test_team = "test-team"
    
    def teardown_method(self):
        """Clean up after tests."""
        self.manager.cleanup()
    
    def test_create_team(self):
        """Test team creation."""
        result = self.manager.create_team(self.test_team)
        assert result["name"] == self.test_team
        assert result["status"] == "active"
    
    def test_create_duplicate_team(self):
        """Test creating a team that already exists."""
        self.manager.create_team(self.test_team)
        with pytest.raises(TeamExistsError):
            self.manager.create_team(self.test_team)
```

### Fixtures

```python
@pytest.fixture
def temp_team():
    """Create a temporary team for testing."""
    team = create_test_team()
    yield team
    cleanup_team(team)

@pytest.fixture
def mock_agent():
    """Mock agent for testing."""
    return MockAgent(name="test-agent")
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_agent_spawn():
    """Test async agent spawning."""
    agent = await spawn_agent_async("test-agent")
    assert agent.status == "running"
    await agent.terminate()
```

---

## Performance Guidelines

### Profiling

```bash
# Profile a specific operation
python -m cProfile -o output.prof scripts/my_script.py

# View profile results
python -m pstats output.prof
```

### Benchmarking

```python
import time

def benchmark(func, iterations=1000):
    """Benchmark a function."""
    start = time.perf_counter()
    for _ in range(iterations):
        func()
    elapsed = time.perf_counter() - start
    print(f"{iterations} iterations in {elapsed:.2f}s")
    print(f"Average: {elapsed/iterations*1000:.2f}ms")
```

---

## Security Guidelines

### No Secrets in Code

- Never commit API keys, tokens, or passwords
- Use environment variables or config files
- Add secrets to `.gitignore`

### Input Validation

- Validate all user input
- Sanitize data before database operations
- Use parameterized queries

### Authentication

- All API endpoints require authentication
- Use secure token generation
- Implement rate limiting

---

## Reporting Issues

### Bug Reports

Include:
- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Python version
- OS/platform
- Relevant logs or screenshots

### Feature Requests

Include:
- Clear description of the feature
- Use case / motivation
- Potential implementation ideas
- Any constraints or considerations

---

## Questions?

- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For questions and community discussion
- **Discord**: OpenClaw community server

---

## License

By contributing to ClawTeam-OpenClaw, you agree that your contributions will be licensed under the MIT License.

---

*Thank you for contributing!*
