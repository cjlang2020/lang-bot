# Lang-Bot QQ机器人

一个基于Python开发的QQ机器人，通过QQ发送消息到本项目，项目接收后转发给支持OpenAI协议的第三方大模型，大模型返回数据后再次返回给QQ用户。

## 功能特性

- **私聊消息处理**：接收QQ私聊消息，支持上下文对话
- **多模态图片理解**：支持发送图片，AI可分析图片内容
- **模块化工具调用**：按功能分类的工具系统（文件、搜索、系统、网络、时间）
- **Skill技能系统**：支持加载专业技能指南（PDF、Excel、PPT等）
- **Ripgrep高效搜索**：支持按文件名和内容搜索
- **智能体循环**：基于finish_reason自动循环，让模型决定何时完成任务
- **中间过程可见**：每次工具调用和结果都会实时发送给用户
- **会话持久化**：对话历史保存到文件，程序重启后自动恢复

## 项目结构

```
lang-bot/
├── start_listener.py          # 主入口文件
├── .env                       # 环境变量配置
├── README.md
├── CLAUDE.md
├── AGENTS.md
├── skills/                    # Skill技能目录
│   ├── pdf/                   # PDF处理技能
│   ├── xlsx/                  # Excel处理技能
│   ├── pptx/                  # PowerPoint处理技能
│   ├── webapp-testing/        # Web应用测试技能
│   ├── skill-creator/         # Skill创建工具
│   └── frontend-slides/       # HTML演示文稿技能
├── data/                      # 数据目录
│   ├── memory.json           # 会话历史
│   └── YYYY-MM/              # 按月份存储的图片
└── src/
    ├── config.py              # 配置和常量
    ├── bot_client.py          # QQ机器人客户端
    ├── ai_client.py           # AI API调用
    ├── session_manager.py     # 会话管理
    ├── image_handler.py       # 图片处理
    ├── skills/                # Skill系统模块
    │   └── skill_service.py   # Skill发现服务
    └── tools/                 # 工具模块
        ├── file_system.py     # 文件系统工具
        ├── search.py          # 搜索工具
        ├── system.py          # 系统工具
        ├── network.py         # 网络工具
        ├── time.py            # 时间工具
        ├── skill.py           # Skill工具
        └── tool_registry.py   # 工具注册表
```

## 快速开始

### 环境要求

- Python 3.12+
- Conda环境（推荐）

### 安装依赖

```bash
pip install qq-botpy aiohttp python-dotenv psutil
```

### 配置

在项目根目录创建 `.env` 文件：

```env
QQ_BOT_APPID=你的机器人AppID
QQ_BOT_SECRET=你的机器人Secret
```

### 运行

```bash
conda activate D:\AI\botpy-master\envs
python start_listener.py
```

## 指令系统

发送以 `/` 开头的消息可触发指令：

| 指令 | 说明 |
|------|------|
| `/清理` | 清空当前会话的所有历史记录（洗脑） |
| `/会话` | 查看当前会话统计信息（消息数、图片数、Token预估、当前模型信息） |

## AI工具调用

### 基础工具

| 工具 | 说明 |
|------|------|
| `list_directory` | 列出目录内容 |
| `read_file` | 读取文件内容 |
| `create_file` | 创建新文件 |
| `write_to_file` | 写入文件 |
| `search_files` | 搜索文件 |
| `execute_command` | 执行CMD/PowerShell命令 |
| `get_system_info` | 获取系统信息 |
| `get_process_list` | 获取进程列表 |
| `get_network_info` | 获取网络信息 |
| `ping_host` | Ping主机 |
| `get_current_time` | 获取当前时间 |

### Skill技能工具

AI可加载专业技能指南来处理特定类型任务：

| Skill | 说明 |
|-------|------|
| `pdf` | PDF文件处理（读取、合并、分割、提取、OCR） |
| `xlsx` | Excel表格处理（读写、公式、格式化、数据分析） |
| `pptx` | PowerPoint演示文稿处理（创建、编辑、转换） |
| `webapp-testing` | Web应用测试（Playwright自动化） |
| `skill-creator` | 创建和优化Skill |
| `frontend-slides` | 创建HTML演示文稿 |

**使用方式**：
- 问"你有哪些skill"或"你有什么技能" → AI会调用skill()列出所有技能
- 问"帮我处理这个PDF" → AI会自动加载pdf skill指南

## Skill 技能系统

### 概述
Skill系统允许AI加载专业技能指南，获取详细的处理指令和最佳实践。

### 扩展方式
添加新技能只需：
1. 在 `skills/` 目录下创建新文件夹（如 `my-skill/`）
2. 添加 `SKILL.md` 文件：

```markdown
---
name: my-skill
description: 描述何时使用此skill
---

# Skill 详细指令
具体的指令内容、示例、最佳实践等...
```

3. 重启程序，自动发现并加载

无需修改任何代码！

## 智能体循环机制

机器人基于 finish_reason 自动循环，让模型决定何时完成任务：

```
用户提问
    ↓
调用大模型
    ↓
检查 finish_reason
    ├── tool_calls → 执行工具 → 推送结果 → 继续循环
    ├── stop / end_turn → 返回结果
    └── 其他 → 返回结果
```

### 中间消息示例

用户可以实时看到AI的思考过程：
```
🔧 调用工具: search_files
📋 [search_files] 找到3个文件...
🔧 调用工具: read_file
📋 [read_file] 文件内容...
🤖 AI回复: 文件已找到，内容如下...
```

## 配置说明

在 `src/config.py` 中可修改以下配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `AI_API_BASE_URL` | `http://127.0.0.1:9900/v1` | AI API地址 |
| `MAX_CONCURRENT_REQUESTS` | 10 | 最大并发请求数 |
| `MAX_STEPS` | 50 | 智能体循环最大步数 |

## 数据存储

- `data/memory.json`：会话历史持久化存储
- `data/YYYY-MM/`：按月份存储的图片文件

## 支持的模型

支持所有兼容OpenAI API协议的大模型，包括：
- Qwen系列（支持文本格式工具调用）
- Llama系列
- 其他支持Function Calling的模型

## 开发说明

- 模块化设计，各功能独立
- 单用户模式，简化会话管理
- 支持热重载历史会话
- 图片自动转Base64发送给大模型
- 支持引用历史图片进行分析
- Skill系统零配置扩展

## License

MIT