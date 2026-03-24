# Open-Javis 全局配置说明

本文档详细说明 Open-Javis 的全局配置文件 `config/javis.toml` 的结构和各配置选项。

## 目录

- [概述](#概述)
- [配置文件位置](#配置文件位置)
- [配置文件结构](#配置文件结构)
- [LLM 配置](#llm-配置)
- [通道配置](#通道配置)
- [数据库配置](#数据库配置)
- [Agent 配置](#agent-配置)
- [记忆配置](#记忆配置)
- [MCP 配置](#mcp-配置)
- [完整示例](#完整示例)
- [环境变量](#环境变量)

## 概述

Open-Javis 使用 TOML 格式的配置文件 `config/javis.toml` 来管理全局系统设置。配置文件支持以下主要模块：

- **LLM 配置** - 大语言模型提供商和参数设置
- **通道配置** - 消息通道（如 Feishu/Lark）设置
- **数据库配置** - 持久化存储路径
- **Agent 配置** - 默认 Agent 行为设置
- **记忆配置** - 会话和语义记忆设置
- **MCP 配置** - Model Context Protocol 服务器设置

## 配置文件位置

| 环境 | 路径 |
|------|------|
| 默认 | `config/javis.toml` |
| 示例文件 | `config/javis.toml.example` |

### 初始化配置

```bash
python main.py init
```

此命令会：
1. 创建 `config/` 目录（如果不存在）
2. 复制示例配置文件到 `config/javis.toml`
3. 创建 `skills/` 目录和示例 skill

## 配置文件结构

```toml
[llm]
# LLM provider and model settings

[channels.feishu]
# Feishu/Lark channel settings

[database]
# Database path settings

[agents.default]
# Default agent behavior settings

[memory]
# Memory and session settings

[mcp]
# MCP server settings
```

## LLM 配置

通过 LiteLLM 集成 100+ 个 LLM 提供商。

### 配置表

```toml
[llm]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"
# api_key = ""                    # 可选：直接设置 API 密钥
# base_url = ""                  # 可选：自定义 API 基础 URL
max_tokens = 4096
temperature = 0.7
timeout = 120
```

### 字段说明

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| provider | string | 否 | "anthropic" | LLM 提供商名称 |
| model | string | 否 | "claude-sonnet-4-20250514" | 模型标识符 |
| api_key | string | 否 | "" | API 密钥（不推荐） |
| api_key_env | string | 否 | "ANTHROPIC_API_KEY" | API 密钥环境变量名 |
| base_url | string | 否 | None | 自定义 API 基础 URL |
| max_tokens | int | 否 | 4096 | 最大输出 token 数 |
| temperature | float | 否 | 0.7 | 采样温度 (0-2) |
| timeout | int | 否 | 120 | 请求超时时间（秒） |

### 支持的提供商

LiteLLM 支持以下主流提供商：

| 提供商 | provider 值 | 示例模型 |
|--------|-------------|----------|
| Anthropic | "anthropic" | claude-sonnet-4-20250514 |
| OpenAI | "openai" | gpt-4, gpt-3.5-turbo |
| Google | "google" | gemini-pro |
| Cohere | "cohere" | command |
| Azure OpenAI | "azure" | gpt-4 |
| HuggingFace | "huggingface" | various |
| Ollama | "ollama" | llama2 |

完整的提供商列表请参考 [LiteLLM 文档](https://docs.litellm.ai/)。

### 安全建议

- **优先使用环境变量** - 使用 `api_key_env` 而非直接在配置中写入 `api_key`
- **限制 max_tokens** - 根据需求和预算设置合理的上限
- **调整 temperature** - 较低值（0.1-0.3）适用于编码/分析，较高值（0.7-1.0）适用于创意任务

## 通道配置

Open-Javis 支持可插拔的消息通道系统，当前支持 Feishu/Lark。

### Feishu/Lark 配置

```toml
[channels.feishu]
enabled = false
app_id = "cli_xxxx"
app_secret_env = "FEISHU_APP_SECRET"
# app_secret = ""                # 可选：直接设置应用密钥
region = "cn"                  # "cn" for Feishu, "intl" for Lark
verify_token = ""               # 可选：事件验证令牌
encrypt_key = ""                # 可选：AES 加密密钥
```

### 字段说明

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| enabled | bool | 否 | false | 是否启用此通道 |
| app_id | string | 是 | - | Feishu/Lark 应用 ID |
| app_secret | string | 否 | "" | 应用密钥（不推荐） |
| app_secret_env | string | 否 | "FEISHU_APP_SECRET" | 应用密钥环境变量名 |
| region | string | 否 | "cn" | 区域："cn"（飞书）或 "intl"（Lark） |
| verify_token | string | 否 | "" | 事件验证令牌 |
| encrypt_key | string | 否 | "" | AES 加密密钥 |

### 区域说明

| region 值 | 服务 | API 基础 URL | WebSocket 基础 URL |
|-----------|------|-------------|------------------|
| "cn" | 飞书 | https://open.feishu.cn | wss://open.feishu.cn |
| "intl" | Lark | https://open.larksuite.com | wss://open.larksuite.com |

### 如何获取 Feishu/Lark 凭证

1. 在 [飞书开放平台](https://open.feishu.cn/) 或 [Lark 开发者平台](https://open.larksuite.com/) 创建应用
2. 在应用设置中获取 `App ID` 和 `App Secret`
3. 配置事件订阅并获取 `Verify Token` 和 `Encrypt Key`（可选）
4. 将凭证通过环境变量或配置文件设置

## 数据库配置

Open-Javis 使用 SQLite 作为持久化存储。

### 配置表

```toml
[database]
path = "~/.javis/javis.db"
```

### 字段说明

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| path | string | 否 | "~/.javis/javis.db" | 数据库文件路径，支持 `~` 展开 |

### 路径说明

- 支持绝对路径：`/var/lib/javis/javis.db`
- 支持相对路径：`./data/javis.db`
- 支持用户目录扩展：`~/.javis/javis.db`

## Agent 配置

定义所有 Agent 的默认行为。

### 配置表

```toml
[agents.default]
system_prompt = "You are a helpful personal assistant."
max_iterations = 100
loop_guard_threshold = 50
```

### 字段说明

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| system_prompt | string | 否 | "You are a helpful personal assistant." | Agent 的系统提示词 |
| max_iterations | int | 否 | 100 | 每条消息的最大迭代次数 |
| loop_guard_threshold | int | 否 | 50 | 循环防护阈值（重复工具调用） |

### 参数说明

- **max_iterations** - 限制 Agent 在单条消息处理中调用工具和 LLM 的总次数，防止无限循环
- **loop_guard_threshold** - 检测重复工具调用的阈值，超过此次数会触发循环保护

## 记忆配置

控制 Agent 的记忆和会话管理行为。

### 配置表

```toml
[memory]
session_max_messages = 200
semantic_enabled = false
semantic_provider = "qdrant"
semantic_url = "http://localhost:6333"
knowledge_enabled = false
```

### 字段说明

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| session_max_messages | int | 否 | 200 | 每个会话保留的最大消息数 |
| semantic_enabled | bool | 否 | false | 是否启用语义/向量搜索 |
| semantic_provider | string | 否 | "qdrant" | 语义向量存储提供商 |
| semantic_url | string | 否 | "http://localhost:6333" | Qdrant 服务器 URL |
| knowledge_enabled | bool | 否 | false | 是否启用知识图谱 |

### 记忆系统说明

#### 会话记忆

- 存储对话历史
- 当消息数超过 `session_max_messages` 时，自动截断最旧的消息

#### 语义记忆

- 支持向量搜索和语义检索
- 当前支持的提供商：
  - **qdrant** - Qdrant 向量数据库
  - **inmemory** - 内存向量存储（测试用）

#### 知识图谱

- 用于构建和查询知识关系
- 可扩展的图存储系统

## MCP 配置

配置 Model Context Protocol (MCP) 服务器。

### 配置表

```toml
[mcp]
enabled_servers = []
timeout = 30
```

### 字段说明

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| enabled_servers | array | 否 | [] | 启用的 MCP 服务器名称列表 |
| timeout | int | 否 | 30 | MCP 客户端超时时间（秒） |

### MCP 服务器配置

MCP 服务器需要在单独的配置部分定义。服务器工具命名格式为 `mcp_{server_name}_{tool_name}`。

#### 示例配置

```toml
[mcp]
enabled_servers = ["filesystem", "github"]

[mcp.server.filesystem]
command = ["mcp-server-filesystem"]
args = ["--allow", "/home/user/work"]

[mcp.server.github]
command = ["mcp-server-github"]
env = { GITHUB_TOKEN = "ghp_xxxx" }
```

### MCP 工具命名

注册的 MCP 工具会自动添加命名空间前缀：

| 原始工具名 | 注册后名称 |
|-----------|-----------|
| read_file | mcp_filesystem_read_file |
| list_issues | mcp_github_list_issues |

这确保了不同服务器的工具名称不会冲突。

## 完整示例

### 最小配置

```toml
[llm]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"

[channels.feishu]
enabled = false

[database]
path = "~/.javis/javis.db"
```

### 完整配置

```toml
[llm]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"
max_tokens = 4096
temperature = 0.7
timeout = 120

[channels.feishu]
enabled = true
app_id = "cli_xxxxxxxxxxxxx"
app_secret_env = "FEISHU_APP_SECRET"
region = "cn"
verify_token = "my_verify_token"
encrypt_key = "my_encrypt_key"

[database]
path = "~/.javis/javis.db"

[agents.default]
system_prompt = "You are a helpful personal assistant with access to various tools."
max_iterations = 100
loop_guard_threshold = 50

[memory]
session_max_messages = 200
semantic_enabled = true
semantic_provider = "qdrant"
semantic_url = "http://localhost:6333"
knowledge_enabled = false

[mcp]
enabled_servers = ["filesystem", "github"]
timeout = 30
```

## 环境变量

Open-Javis 支持通过环境变量配置敏感信息。

### LLM 相关

| 环境变量 | 用途 |
|-----------|------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API 密钥 |
| `OPENAI_API_KEY` | OpenAI API 密钥 |
| `GOOGLE_API_KEY` | Google Gemini API 密钥 |
| `COHERE_API_KEY` | Cohere API 密钥 |

### 通道相关

| 环境变量 | 用途 |
|-----------|------|
| `FEISHU_APP_SECRET` | Feishu/Lark 应用密钥 |

### 自定义环境变量

可以在配置文件中指定任意环境变量：

```bash
export MY_CUSTOM_KEY="value"
python main.py start
```

然后在配置中使用：

```toml
[llm]
api_key_env = "MY_CUSTOM_KEY"
```

## 配置验证

系统在启动时会验证配置文件：

1. **TOML 语法检查** - 确保文件格式正确
2. **必需字段检查** - 验证必需的配置项存在
3. **类型验证** - 检查字段类型是否正确
4. **范围验证** - 数值字段（如 temperature）在合理范围内

### 常见配置错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| API key not found | `api_key_env` 指定的环境变量未设置 | 设置环境变量或使用 `api_key` |
| Invalid TOML | 配置文件语法错误 | 检查引号、缩进和数组格式 |
| Temperature out of range | temperature 不在 0-2 之间 | 调整到有效范围内 |

## CLI 命令与配置

### 指定配置文件

```bash
python main.py start --file /path/to/custom.toml
python main.py chat --config /path/to/custom.toml "Hello"
```

### 使用默认配置

```bash
python main.py start
```

## 相关文档

- [Agent 配置指南](agent.md) - Agent 模板配置
- [示例配置文件](../config/javis.toml.example) - 完整示例
- [LiteLLM 文档](https://docs.litellm.ai/) - 支持的 LLM 提供商
- [Feishu 开放平台](https://open.feishu.cn/) - 通道集成文档