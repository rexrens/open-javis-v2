# Open-Javis CLI Reference

Complete command-line interface reference for Open-Javis Personal Agent System.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [`javis init`](#javis-init)
  - [`javis start`](#javis-start)
  - [`javis agent-list`](#javis-agent-list)
  - [`javis agent-kill`](#javis-agent-kill)
  - [`javis chat`](#javis-chat)
  - [`javis tools-list`](#javis-tools-list)
  - [`javis shell`](#javis-shell)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

Open-Javis is a Python-based personal agent system with a pluggable channel architecture, multi-agent support, and extensive tool integration.

**Requirements:**
- Python >= 3.12
- Valid API keys for configured LLM providers

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/open-javis-v2.git
cd open-javis-v2

# Install dependencies
pip install -e .

# Or use the virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Quick Start

```bash
# 1. Initialize configuration
python main.py init

# 2. Edit config file to add your API keys
# Edit config/javis.toml and set your ANTHROPIC_API_KEY environment variable

# 3. Start the daemon
python main.py start

# 4. Or send a single message
python main.py chat "Hello, how can you help me?"
```

---

## Commands

### `javis init`

Initialize Javis configuration files and directories.

```bash
python main.py init
```

**Description:**
Creates the configuration directory structure and populates it with default settings.

**What it creates:**
- `config/javis.toml` - Main configuration file
- `skills/hello.md` - Example skill file
- `skills/` directory for custom skills

**Behavior:**
- If `config/javis.toml` already exists, prompts for confirmation before overwriting
- Copies from `config/javis.toml.example` if available
- Falls back to creating a minimal default config if example file is missing

**Example:**
```bash
$ python main.py init
Created config/javis.toml

Edit the config file to set your API keys and preferences.
Created skills/hello.md

Initialization complete!
```

---

### `javis start`

Start the Javis daemon in the foreground.

```bash
python main.py start [--file CONFIG_FILE]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--file` / `-f` | `config/javis.toml` | Path to configuration file |

**Description:**
Launches the Javis agent core which listens for incoming messages from configured channels (Feishu/Lark, etc.).

**Signals:**
- `Ctrl+C` - Gracefully shutdown the daemon

**Example:**
```bash
# Use default config
python main.py start

# Use custom config
python main.py start --file /path/to/custom-config.toml
```

---

### `javis agent-list`

List all active and terminated agents.

```bash
python main.py agent-list [--config CONFIG_FILE]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--config` / `-c` | `config/javis.toml` | Path to configuration file |

**Description:**
Displays a table of all agents with their ID, name, state, and session ID.

**Output columns:**
- **ID** - Agent identifier (first 8 characters)
- **Name** - Agent name
- **State** - Current state (Active/Terminated)
- **Session** - Session identifier (first 8 characters)

**Example:**
```bash
$ python main.py agent-list
┏━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
┃ ID      ┃ Name   ┃ State     ┃ Session ┃
┡━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
│ a1b2c3d4 │ agent1 │ active    │ x9y8z7w6│
└─────────┴────────┴───────────┴─────────┘

Total: 1 agent(s)
```

---

### `javis agent-kill`

Terminate a running agent.

```bash
python main.py agent-kill AGENT_ID [--config CONFIG_FILE]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `AGENT_ID` | Yes | Agent identifier to terminate |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--config` / `-c` | `config/javis.toml` | Path to configuration file |

**Description:**
Gracefully stops the specified agent. The agent's session is preserved but marked as terminated.

**Return values:**
- `Agent {id} killed.` - Success
- `Agent {id} not found.` - Agent doesn't exist

**Example:**
```bash
$ python main.py agent-kill a1b2c3d4
Agent a1b2c3d4 killed.
```

---

### `javis chat`

Send a message to an agent and receive a response.

```bash
python main.py chat MESSAGE [--agent AGENT_ID] [--config CONFIG_FILE]
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `MESSAGE` | Yes | The message to send |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--agent` / `-a` | `null` | Agent ID (creates new agent if not specified) |
| `--config` / `-c` | `config/javis.toml` | Path to configuration file |

**Description:**
Sends a message to the specified agent and prints the response. If no agent ID is provided, a new agent is created for the conversation.

**Example:**
```bash
# Send message to new agent
python main.py chat "What is the weather like today?"

# Send message to existing agent
python main.py chat "What did you just say?" --agent a1b2c3d4

# Multi-word message (no quotes needed in shell)
python main.py chat --agent a1b2c3d4 How do I write a Python function?
```

---

### `javis tools-list`

List all available tools.

```bash
python main.py tools-list [--config CONFIG_FILE]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--config` / `-c` | `config/javis.toml` | Path to configuration file |

**Description:**
Displays a table of all available tools with their name, category, and description.

**Tool categories:**
- `BUILTIN` - Core Javis tools
- `MCP` - MCP server tools
- `SKILL` - Custom skill tools

**Example:**
```bash
$ python main.py tools-list
┏━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name       ┃ Category ┃ Description                    ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ echo       │ BUILTIN  │ Echo text back                 │
│ list_agents│ BUILTIN  │ List all agents                │
│ ...        │ ...      │ ...                            │
└────────────┴──────────┴────────────────────────────────┘

Total: 15 tool(s)
```

---

### `javis shell`

Start an interactive shell for an agent.

```bash
python main.py shell AGENT_ID
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `AGENT_ID` | Yes | Agent identifier to attach to |

**Description:**
Opens an interactive REPL for the specified agent with command history support.

**Shell commands:**
- `exit` or `quit` - Exit the shell
- `Ctrl+C` - Clear current input (does not exit)

**History:**
Shell history is persisted to `~/.javis_history`

**Requirements:**
- `prompt-toolkit` package (install with `pip install prompt-toolkit`)

**Example:**
```bash
$ python main.py shell a1b2c3d4
Open-Javis Shell
Agent: a1b2c3d4
Type 'exit' to quit.

> Hello, how are you?
You: Hello, how are you?
Thinking...Response: I'm doing well, thank you!
Assistant: I'm doing well, thank you!

> What can you do?
You: What can you do?
Thinking...Response: I can help with...
Assistant: I can help with...

> exit
```

---

## Configuration

### Configuration File

The main configuration file is `config/javis.toml` (TOML format).

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes (if using Anthropic) |
| `OPENAI_API_KEY` | OpenAI API key | Yes (if using OpenAI) |
| `DEEPSEEK_API_KEY` | DeepSeek API key | Yes (if using DeepSeek) |
| `FEISHU_APP_SECRET` | Feishu app secret | Yes (if using Feishu channel) |

### Configuration Sections

#### `[llm]` - Language Model Settings
```toml
[llm]
provider = "anthropic"           # LLM provider
model = "claude-sonnet-4-20250514"  # Model identifier
api_key_env = "ANTHROPIC_API_KEY"   # API key env var
max_tokens = 4096                   # Max response tokens
temperature = 0.7                   # Sampling temperature
timeout = 120                       # Request timeout (seconds)
```

#### `[channels.feishu]` - Feishu/Lark Channel
```toml
[channels.feishu]
enabled = true
app_id = "cli_xxxx"
app_secret_env = "FEISHU_APP_SECRET"
region = "cn"                       # "cn" or "intl"
verify_token = ""
encrypt_key = ""
```

#### `[database]` - Database Settings
```toml
[database]
path = "~/.javis/javis.db"         # SQLite database path
```

#### `[agents.default]` - Default Agent Settings
```toml
[agents.default]
system_prompt = "You are a helpful personal assistant."
max_iterations = 100
loop_guard_threshold = 50
```

#### `[memory]` - Memory Settings
```toml
[memory]
session_max_messages = 200
semantic_enabled = false
semantic_provider = "qdrant"
semantic_url = "http://localhost:6333"
knowledge_enabled = false
```

#### `[mcp]` - MCP Server Settings
```toml
[mcp]
enabled_servers = []                # List of server names
timeout = 30                       # Client timeout (seconds)
```

---

## Examples

### Common Workflows

#### 1. First-time Setup
```bash
# Initialize
python main.py init

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Test with a simple chat
python main.py chat "Hello!"
```

#### 2. Managing Agents
```bash
# List all agents
python main.py agent-list

# Create a new agent and send a message
python main.py chat "Create a summary of today's news" > agent_output.txt

# Continue conversation with the same agent
python main.py chat "Make it shorter" --agent <AGENT_ID>

# Kill the agent when done
python main.py agent-kill <AGENT_ID>
```

#### 3. Using the Shell
```bash
# Create an agent via chat
python main.py chat "Start a new session about Python programming"

# Get the agent ID from agent-list
python main.py agent-list

# Attach interactive shell
python main.py shell <AGENT_ID>
```

#### 4. Different LLM Providers
```bash
# Using DeepSeek (edit config/javis.toml first)
[llm]
provider = "deepseek"
model = "deepseek-chat"
api_key_env = "DEEPSEEK_API_KEY"

python main.py chat "Write some code"

# Using OpenAI-compatible (e.g., Ollama)
[llm]
provider = "openai"
base_url = "http://localhost:11434/v1"
model = "llama2"

python main.py chat "Hello from local model"
```

### Advanced Examples

#### Pipe Output
```bash
# Stream response to file
python main.py chat "Generate a Python script" > script.py

# Process with other tools
python main.py chat "Explain this file" | tee explanation.txt
```

#### Batch Processing
```bash
#!/bin/bash
# Process multiple queries
queries=("Summarize this" "What's the key point?" "List action items")
for q in "${queries[@]}"; do
    echo "=== Query: $q ==="
    python main.py chat "$q"
    echo
done
```

---

## Troubleshooting

### Common Issues

#### Error: `Config file not found`
```bash
# Solution: Initialize first
python main.py init
```

#### Error: `API key not found`
```bash
# Solution: Set the environment variable
export ANTHROPIC_API_KEY="your-key-here"
# or add to ~/.bashrc or ~/.zshrc
```

#### Error: `prompt_toolkit is required for shell mode`
```bash
# Solution: Install the dependency
pip install prompt-toolkit
```

#### Agent not responding
```bash
# Check if agent exists
python main.py agent-list

# Verify configuration
python main.py tools-list

# Check logs for errors
python main.py start --debug
```

### Debugging

Enable verbose output by checking the agent core logs:

```bash
# Start with full logging (if supported)
python main.py start
```

### Getting Help

Each command has built-in help:
```bash
python main.py --help
python main.py chat --help
python main.py agent-list --help
```

---

## See Also

- [README.md](../README.md) - Project overview
- [Configuration Guide](./configuration.md) - Detailed configuration options
- [Agent System](./agents.md) - Agent architecture and behavior
- [Tools Reference](./tools.md) - Available tools and usage

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2024-03-24 | Initial release |
