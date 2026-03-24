# Development Guide

This document provides guidelines and rules for contributing to Open-Javis v2.

## Project Philosophy

- **Modularity**: Each subsystem should be independent and loosely coupled
- **Extensibility**: New providers, channels, and tools should be easy to add
- **Type Safety**: Use type hints for all public APIs
- **Async-First**: All I/O operations should be asynchronous

## Code Style

### Python

- **Python Version**: >= 3.12
- **Code Style**: PEP 8 compliant
- **Type Hints**: Required for all function signatures and class attributes
- **Docstrings**: Google-style docstrings for all public classes and methods

### Example

```python
from typing import Optional, AsyncIterator


class ExampleService:
    """Service for handling example operations.

    This service manages example workflows with async support.
    """

    def __init__(self, config: ExampleConfig):
        """Initialize the service.

        Args:
            config: Configuration for the service.
        """
        self.config = config

    async def process(self, input_data: str) -> AsyncIterator[str]:
        """Process input data and yield results.

        Args:
            input_data: The input data to process.

        Yields:
            Processed result chunks.

        Raises:
            ProcessError: If processing fails.
        """
        async for chunk in self._process_async(input_data):
            yield chunk
```

## Architecture Rules

### Directory Structure

```
src/
├── core/           # Core subsystems (AgentCore, Config, Agent)
├── channels/       # Channel adapters for different platforms
├── llm/            # LLM provider drivers
├── memory/         # Memory and storage subsystems
├── tools/          # Tool system (MCP, skills, builtins)
└── runtime/        # Agent runtime and loop management
```

### Module Organization

1. **Base Classes**: Define abstract interfaces in `base.py`
2. **Implementations**: Concrete implementations in separate files
3. **Exports**: Use `__init__.py` to expose public APIs
4. **Types**: Shared types in `types.py`

### Dependency Injection

Pass dependencies through constructors, not global variables:

```python
# Good
class Agent:
    def __init__(self, memory: MemorySubstrate, tools: ToolRegistry):
        self.memory = memory
        self.tools = tools

# Bad
class Agent:
    def __init__(self):
        self.memory = global_memory  # Avoid
```

## Adding New Features

### Adding a New Channel

1. Inherit from `ChannelAdapter` in `channels/base.py`
2. Implement required methods: `start()`, `send()`, `stop()`
3. Add configuration to `FeishuConfig` pattern in `config.py`
4. Register in `AgentCore.start()`

### Adding a New Tool

```python
from src.tools.base import Tool, ToolCategory

@Tool(name="my_tool", category=ToolCategory.UTILITY)
async def my_tool(arg1: str, arg2: int = 10) -> str:
    """Do something useful.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        The result description
    """
    return f"Processed {arg1} with {arg2}"
```

### Adding a New Agent

1. Create directory under `agents/your_agent/`
2. Create `agent.toml` with agent configuration
3. Define agent-specific skills in `skills/`

## Configuration Rules

1. **Environment Variables**: Use `api_key_env` for sensitive data
2. **Default Values**: Always provide sensible defaults
3. **Validation**: Use `__post_init__` for validation and expansion

```python
@dataclass
class LLMConfig:
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key_env: str = "ANTHROPIC_API_KEY"
    api_key: str = ""

    def __post_init__(self):
        if not self.api_key and self.api_key_env:
            self.api_key = os.environ.get(self.api_key_env, "")
```

## Error Handling

### Exception Hierarchy

```python
class JavisError(Exception):
    """Base exception for Open-Javis."""

class LLMError(JavisError):
    """Base LLM-related error."""

class AuthenticationError(LLMError):
    """Authentication failed."""

class RateLimitError(LLMError):
    """Rate limit exceeded."""
```

### Error Handling Pattern

```python
try:
    result = await operation()
except SpecificError as e:
    # Handle known error
    log.warning(f"Expected error: {e}")
    raise AppropriateError(str(e))
except Exception as e:
    # Handle unexpected error
    log.error(f"Unexpected error: {e}", exc_info=True)
    raise JavisError("Operation failed") from e
```

## Testing

### Test Structure

```
tests/
├── unit/
│   ├── test_agent.py
│   ├── test_memory.py
│   └── test_tools.py
├── integration/
│   ├── test_channels.py
│   └── test_llm.py
└── conftest.py
```

### Test Guidelines

- Use `pytest` for testing
- Mock external dependencies (LLM APIs, databases)
- Test both success and error paths
- Use fixtures for common setup

## Git Workflow

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(llm): add DeepSeek provider support
fix(kernel): handle channel connection errors
docs(readme): update installation instructions
refactor(agent): simplify state management
```

### Branching

- `main`: Production branch
- `feature/*`: New features
- `fix/*`: Bug fixes
- `docs/*`: Documentation updates

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The sum of a and b.

    Raises:
        ValueError: If inputs are negative.
    """
    if a < 0 or b < 0:
        raise ValueError("Inputs must be non-negative")
    return a + b
```

### Updating Documentation

1. Update relevant `.md` files in `doc/`
2. Update `README.md` for user-facing changes
3. Update `CLAUDE.md` for AI assistant context

## Performance Guidelines

1. **Async I/O**: Always use async for network/file operations
2. **Connection Pooling**: Reuse connections where possible
3. **Streaming**: Use streaming for LLM responses to reduce latency
4. **Caching**: Cache expensive operations (token counts, embeddings)

## Security

1. **No Secrets**: Never commit API keys or passwords
2. **Input Validation**: Validate all user inputs
3. **Sanitization**: Sanitize outputs from external systems
4. **Dependency Updates**: Keep dependencies updated for security patches

## Review Checklist

Before submitting a PR, verify:

- [ ] Code follows style guidelines
- [ ] Type hints are complete
- [ ] Docstrings are present
- [ ] Tests are added/updated
- [ ] Documentation is updated
- [ ] No secrets in code
- [ ] All tests pass
