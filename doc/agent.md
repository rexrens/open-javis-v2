# Open-Javis Agent 配置指南

本文档介绍如何在 Open-Javis 中创建和配置自定义 Agent 模板。

## 目录

- [概述](#概述)
- [Agent 目录结构](#agent-目录结构)
- [Agent 配置文件](#agent-配置文件)
- [权限系统](#权限系统)
- [创建自定义 Agent](#创建自定义-agent)
- [Skills 系统](#skills-系统)
- [示例](#示例)

## 概述

Open-Javis 使用基于 TOML 的配置文件来定义 Agent 模板。每个 Agent 模板位于 `agents/<agent_name>/` 目录下，包含一个 `agent.toml` 配置文件。

### 关键特性

- **基于权限的访问控制** - 细粒度的权限管理系统
- **独立工作空间** - 每个 Agent 拥有独立的文件系统隔离
- **可配置的 LLM 参数** - Agent 可以覆盖全局 LLM 设置
- **Skill 集成** - 支持指定必需和首选的 Skills
- **会话管理** - 支持自定义的会话记忆配置

## Agent 目录结构

```
agents/
├── assistant/           # 默认助手 Agent
│   └── agent.toml      # Agent 配置文件
├── coder/              # 代码助手 Agent
│   └── agent.toml
└── researcher/         # 研究助手 Agent
    └── agent.toml
```

每个 Agent 目录必须包含一个 `agent.toml` 文件。

## Agent 配置文件

Agent 配置文件采用 TOML 格式，包含以下主要部分：

### [agent] - 基本信息表

```toml
[agent]
name = "assistant"
description = "A helpful personal assistant"
```

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| name | string | 是 | Agent 的唯一标识符 |
| description | string | 否 | Agent 的描述信息 |

### [permissions] - 权限配置表

```toml
[permissions]
granted = ["*"]
```

**granted** 字段是一个权限列表，支持的权限包括：

| 权限 | 说明 |
|------|------|
| `*` | 所有权限（超级用户） |
| `tools.basic` | 只读工具权限 |
| `tools.exec` | 执行工具权限 |
| `tools.write` | 写入工具权限 |
| `tools.system` | 系统级工具权限 |
| `llm.read` | 读取 LLM |
| `llm.write` | 写入 LLM |
| `llm.stream` | 流式 LLM |
| `memory.read` | 读取记忆 |
| `memory.write` | 写入记忆 |
| `memory.delete` | 删除记忆 |
| `channel.read` | 读取通道 |
| `channel.write` | 写入通道 |
| `fs.read` | 读取文件系统 |
| `fs.write` | 写入文件系统 |
| `fs.delete` | 删除文件系统 |

权限支持通配符匹配：
- `tools.*` - 匹配所有工具权限
- `memory.*` - 匹配所有记忆权限

### [workspace] - 工作空间配置表

```toml
[workspace]
inherit_identity_from = "default"
```

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| inherit_identity_from | string | 否 | - | 继承身份的 Agent 名称 |

### [llm] - LLM 配置表

Agent 可以覆盖全局 LLM 配置：

```toml
[llm]
model = "claude-sonnet-4-20250514"
temperature = 0.7
max_tokens = 4096
```

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| model | string | 否 | 全局配置 | 指定使用的 LLM 模型 |
| temperature | float | 否 | 全局配置 | 采样温度 (0-2) |
| max_tokens | int | 否 | 全局配置 | 最大输出 token 数 |

### [memory] - 记忆配置表

```toml
[memory]
session_max_messages = 200
```

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| session_max_messages | int | 否 | 200 | 每个会话保留的最大消息数 |

### [skills] - Skills 配置表

```toml
[skills]
required = []
preferred = []
```

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| required | array | 否 | [] | 必需加载的 Skills 列表 |
| preferred | array | 否 | [] | 首选加载的 Skills 列表 |

## 权限系统

Open-Javis 实现了基于能力的权限系统，确保 Agent 只能执行被授权的操作。

### 权限检查示例

```python
from src.core.agent import Permission

# 检查权限
if Permission.has_permission(
    ["tools.basic", "tools.exec"],
    "tools.exec"
):
    # 允许执行工具操作
    pass
```

### 安全建议

1. **最小权限原则** - 只授予 Agent 所需的最低权限
2. **避免使用 `*`** - 除非绝对必要，不要授予所有权限
3. **文件系统隔离** - 谨慎授予 `fs.write` 和 `fs.delete` 权限
4. **系统权限** - `tools.system` 仅用于受信任的 Agent

## 创建自定义 Agent

### 步骤 1: 创建 Agent 目录

```bash
mkdir -p agents/my-agent
```

### 步骤 2: 创建配置文件

创建 `agents/my-agent/agent.toml`:

```toml
[agent]
name = "my-agent"
description = "My custom agent for specific tasks"

[permissions]
granted = [
    "tools.basic",
    "tools.exec",
    "llm.read",
    "llm.write",
    "memory.read",
    "memory.write",
]

[llm]
temperature = 0.5
max_tokens = 2048

[memory]
session_max_messages = 100
```

### 步骤 3: 重启系统

Agent 会在系统启动时自动加载。

## Skills 系统

Skills 是轻量级的功能模块，用于扩展 Agent 的能力。

### Skill 文件格式

Skills 存储在 `skills/` 目录下，使用 Markdown 格式：

```markdown
---
name: coding-assistant
description: Helps with coding tasks
---

When helping with code, follow these best practices:
- Write clean, readable code
- Add comments for complex logic
- Consider edge cases
- Provide examples
```

### Skill 元数据

| 字段 | 必需 | 说明 |
|------|------|------|
| name | 是 | Skill 的唯一标识符 |
| description | 是 | Skill 的描述 |

### 提示注入防护

系统会自动扫描 Skills 中的潜在提示注入模式，确保安全。

## 示例

### 示例 1: 代码助手 Agent

```toml
# agents/coder/agent.toml

[agent]
name = "coder"
description = "A coding assistant with file system access"

[permissions]
granted = [
    "tools.basic",
    "tools.exec",
    "tools.write",
    "llm.read",
    "llm.write",
    "memory.read",
    "memory.write",
    "fs.read",
    "fs.write",
]

[llm]
temperature = 0.3
max_tokens = 4096

[skills]
required = ["coding-best-practices"]
preferred = ["documentation", "debugging"]
```

### 示例 2: 只读研究员 Agent

```toml
# agents/researcher/agent.toml

[agent]
name = "researcher"
description = "A research agent with read-only access"

[permissions]
granted = [
    "tools.basic",
    "llm.read",
    "memory.read",
    "memory.write",
    "fs.read",
]

[llm]
temperature = 0.8
max_tokens = 8192

[memory]
session_max_messages = 500

[skills]
required = ["research-methodology"]
```

### 示例 3: 受限助手 Agent

```toml
# agents/limited-assistant/agent.toml

[agent]
name = "limited-assistant"
description = "A limited assistant with minimal permissions"

[permissions]
granted = [
    "tools.basic",
    "llm.read",
    "memory.read",
]

[llm]
temperature = 0.7
max_tokens = 1024

[memory]
session_max_messages = 50
```

## CLI 命令

### 列出所有 Agent

```bash
python main.py agent-list
```

### 发送消息给 Agent

```bash
python main.py chat "Hello, how can you help me?"
python main.py chat --agent <agent_id> "Help me with coding"
```

### 终止 Agent

```bash
python main.py agent-kill <agent_id>
```

### 列出可用工具

```bash
python main.py tools-list
```

## 配置验证

系统在加载 Agent 配置时会进行基本验证。确保：

1. 所有必需字段都存在
2. 权限名称有效
3. 数值在合理范围内（如 temperature 在 0-2 之间）
4. Skills 名称在 skills 目录中存在

## 故障排除

### Agent 未加载

- 检查配置文件是否位于正确的目录
- 确认文件名为 `agent.toml`
- 检查 TOML 语法是否正确

### 权限被拒绝

- 确认权限拼写正确
- 检查是否授予了足够的权限
- 验证权限列表格式

### Skills 不可用

- 确保 Skills 文件位于 `skills/` 目录
- 检查 Skill 文件名和元数据
- 验证 Skill 内容没有触发注入防护

## 相关文档

- [主配置文件](../config/javis.toml.example) - 全局系统配置
- [Kernel 模块](../src/core/kernel.py) - 核心 Agent 管理系统
- [Agent 模块](../src/core/agent.py) - Agent 生命周期和权限系统
- [Skills 模块](../src/tools/skills.py) - Skills 加载和管理系统