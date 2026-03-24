# Open-Javis v2

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-beta-yellow.svg)

**A powerful, extensible personal agent system**

[Features](#features) • [Installation](#installation) • [Quick Start](#quick-start) • [Configuration](#configuration) • [Documentation](#documentation)

</div>

Open-Javis is a Python-based personal agent system designed for extensibility and ease of use. It provides a unified interface for multiple LLM providers, pluggable channels, and a flexible tool system.

## Features

- 🤖 **Multi-LLM Support**: Anthropic, OpenAI, DeepSeek, and 100+ providers via LiteLLM
- 🔌 **Pluggable Channels**: Feishu/Lark integration, extensible to other platforms
- 🧩 **Tool System**: Built-in tools, MCP (Model Context Protocol) support, and custom skills
- 🧠 **Memory System**: Session management, semantic search, and knowledge graphs
- ⚡ **Async Architecture**: High-performance async/await throughout
- 🔧 **Flexible Configuration**: TOML-based config with environment variable support

## Installation

### Prerequisites

- Python 3.12 or higher
- `uv` package manager (recommended)

### Install with uv

```bash
# Clone the repository
git clone https://github.com/rexrens/open-javis-v2.git
cd open-javis-v2

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Install with pip

```bash
# Clone the repository
git clone https://github.com/rexrens/open-javis-v2.git
cd open-javis-v2

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

## Quick Start

### 1. Initialize Configuration

```bash
python main.py init
```

This creates a `config/javis.toml` file and a `skills/` directory.

### 2. Configure LLM Provider

Edit `config/javis.toml` and set your LLM provider:

```toml
[llm]
# For Anthropic (Claude)
provider = "anthropic"
model = "claude-sonnet-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"

# For DeepSeek
# provider = "deepseek"
# model = "deepseek-chat"
# api_key_env = "DEEPSEEK_API_KEY"

# For OpenAI Compatible (vLLM, Ollama, etc.)
# provider = "openai"
# base_url = "http://localhost:8000/v1"
# model = "your-model-name"
```

Set your API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 3. Start a Chat

```bash
python main.py chat "Hello, how are you?"
```

### 4. Start the Daemon

```bash
python main.py start
```

## Configuration

### LLM Providers

Open-Javis supports multiple LLM providers through LiteLLM:

#### Anthropic (Claude)

```toml
[llm]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"
```

#### DeepSeek

```toml
[llm]
provider = "deepseek"
model = "deepseek-chat"          # or deepseek-coder, deepseek-reasoner
api_key_env = "DEEPSEEK_API_KEY"
```

#### OpenAI Compatible

Compatible with vLLM, Ollama, LM Studio, and any OpenAI-compatible API:

```toml
[llm]
provider = "openai"
base_url = "http://localhost:8000/v1"
model = "your-model-name"
api_key_env = "OPENAI_API_KEY"  # Optional, omit if not needed
```

Common endpoints:
- **vLLM**: `http://localhost:8000/v1`
- **Ollama**: `http://localhost:11434/v1`
- **LM Studio**: `http://localhost:1234/v1`

#### OpenAI

```toml
[llm]
provider = "openai"
model = "gpt-4"
api_key_env = "OPENAI_API_KEY"
```

### Channel Configuration

Configure Feishu/Lark integration:

```toml
[channels.feishu]
enabled = true
app_id = "cli_xxxx"
app_secret_env = "FEISHU_APP_SECRET"
region = "cn"  # "cn" for Feishu, "intl" for Lark
verify_token = ""
encrypt_key = ""
```

### Memory Configuration

```toml
[memory]
session_max_messages = 200
semantic_enabled = false
semantic_provider = "qdrant"
semantic_url = "http://localhost:6333"
knowledge_enabled = false
```

## CLI Commands

### Initialize

```bash
python main.py init
```
Create configuration files and directories.

### Start

```bash
python main.py start [--file CONFIG]
```
Start the Javis daemon.

### Chat

```bash
python main.py chat MESSAGE [--agent AGENT_ID] [--config CONFIG]
```
Send a message to an agent.

### Shell

```bash
python main.py shell AGENT_ID
```
Interactive shell for an agent.

### Agent List

```bash
python main.py agent-list [--config CONFIG]
```
List all registered agents.

### Kill Agent

```bash
python main.py agent-kill AGENT_ID [--config CONFIG]
```
Terminate an agent.

### Tools List

```bash
python main.py tools-list [--config CONFIG]
```
List all available tools.

## Documentation

- [Configuration Guide](doc/config.md) - Detailed configuration options
- [Agent Documentation](doc/agent.md) - Understanding agents
- [Command Reference](doc/command.md) - Complete CLI reference
- [Development Guide](DEVELOPMENT.md) - Contributing guidelines

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for:
- Code style guidelines
- Architecture overview
- Adding new features
- Testing practices
- Contribution workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

## Project Structure

```
open-javis-v2/
├── main.py                 # CLI entry point
├── config/                 # Configuration files
├── doc/                    # Documentation
├── src/
│   ├── core/               # Core subsystems (AgentCore, Config)
│   ├── channels/           # Channel adapters
│   ├── llm/                # LLM drivers
│   ├── memory/             # Memory system
│   ├── tools/              # Tool system
│   └── runtime/            # Agent runtime
├── agents/                 # Agent definitions
└── skills/                 # Custom skills
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read [DEVELOPMENT.md](DEVELOPMENT.md) for guidelines.

## Acknowledgments

- [LiteLLM](https://github.com/BerriAI/litellm) for unified LLM interface
- The OpenAI community for the API standard
