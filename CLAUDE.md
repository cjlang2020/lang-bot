# CLAUDE.md

这是一个QQ机器人项目，通过QQ发送信息到本项目，项目接收后转发给支持OPENAI协议的第三方大模型，大模型返回数据后再次返回给QQ用户。

## 项目简介

技术是Python开发。
环境是conda创建的，python3.12版本的，路径是：D:\AI\botpy-master\envs
做测试必须使用这个环境

项目分析时忽略envs、data、qq-api等文件夹

涉及到的代码如果有扩展代码，也就是不能所有代码放一个文件，需要分开，代码可放在src目录下

## 项目结构

```
lang-bot/
├── start_listener.py          # 主入口文件
├── .env                       # 环境变量配置（QQ机器人凭证）
├── .gitignore
├── CLAUDE.md                  # 项目技术文档
├── AGENTS.md                  # AI代理说明文档
├── README.md                  # 用户使用文档
├── test_skill_system.py       # Skill系统测试脚本
├── skills/                    # Skill技能目录（自动扫描）
│   ├── pdf/SKILL.md           # PDF处理技能
│   ├── xlsx/SKILL.md          # Excel处理技能
│   ├── pptx/SKILL.md          # PowerPoint处理技能
│   ├── webapp-testing/SKILL.md
│   ├── skill-creator/SKILL.md
│   └── frontend-slides/SKILL.md
└── src/
    ├── __init__.py
    ├── config.py              # 配置和常量
    ├── bot_client.py          # QQ机器人客户端
    ├── ai_client.py           # AI API调用（基于finish_reason的智能体循环）
    ├── session_manager.py     # 会话管理（单用户模式）
    ├── image_handler.py       # 图片处理
    ├── search_tools.py        # Ripgrep搜索工具核心实现
    ├── windows_tools.py       # Windows工具（向后兼容）
    ├── skills/                # Skill系统模块
    │   ├── __init__.py
    │   └── skill_service.py   # Skill发现和缓存服务
    └── tools/                 # AI工具模块（按功能拆分）
        ├── __init__.py
        ├── file_system.py     # 文件系统工具
        ├── search.py          # 搜索工具（Ripgrep）
        ├── system.py          # 系统工具
        ├── network.py         # 网络工具
        ├── time.py            # 时间工具
        ├── skill.py           # Skill工具（AI可调用）
        └── tool_registry.py   # 工具注册表
```

## 主要功能

- 接收QQ私聊消息
- 支持图片消息的多模态处理
- 支持工具调用（文件操作、系统命令、网络操作、进程管理等）
- 会话历史管理，支持上下文对话
- 图片历史记忆，用户可以引用之前的图片
- **智能体循环机制**：基于finish_reason的自动循环，让模型自己决定何时完成任务
- **中间过程可见**：每次工具调用和结果都会实时发送给QQ用户
- **Ripgrep高效搜索**：支持按文件名和内容搜索
- **模块化工具设计**：所有工具按功能分类，易于维护和扩展
- **Skill技能系统**：支持加载专业技能指南，零配置扩展

## 数据流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              QQ用户发送消息                                   │
│                                   ↓                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        bot_client.py                                 │   │
│  │  ┌──────────────────────┐                                           │   │
│  │  │ on_c2c_message_create│                                           │   │
│  │  │    (私聊消息)         │                                           │   │
│  │  └──────────┬───────────┘                                           │   │
│  │             │                                                        │   │
│  │             ↓                                                        │   │
│  │              检查是否是指令 (/清理, /会话)                             │   │
│  │                          ↓                                          │   │
│  │              检查是否有图片附件                                       │   │
│  │                          ↓                                          │   │
│  │              调用 process_message_with_ai() 处理消息                  │   │
│  │                          ↓                                          │   │
│  │              通过回调函数发送中间结果给用户                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                             ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        ai_client.py                                  │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │              Agent Loop (基于 finish_reason)                   │   │   │
│  │  │                                                              │   │   │
│  │  │  1. 加载系统提示词 + 历史对话 (最多20条)                         │   │   │
│  │  │  2. 构建消息列表，处理图片为Base64                              │   │   │
│  │  │  3. 调用 AI API 请求大模型                                     │   │   │
│  │  │  4. 检查 finish_reason:                                       │   │   │
│  │  │     ├── tool_calls → 执行工具 → 推送结果给用户 → 继续循环       │   │   │
│  │  │     ├── stop / end_turn → 推送回复给用户 → 退出循环             │   │   │
│  │  │     └── 其他 → 推送回复给用户 → 退出循环                        │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  5. 保存对话历史到 session_manager (memory.json)                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 模块功能说明

### start_listener.py
主入口文件，负责：
- 加载 `.env` 环境变量
- 初始化QQ机器人客户端
- 启动监听服务

### src/config.py
配置模块，存储全局配置：
- `AI_API_BASE_URL`: AI API地址 (默认: http://127.0.0.1:9900/v1)
- `MAX_CONCURRENT_REQUESTS`: 最大并发请求数 (10)
- `MAX_STEPS`: 智能体循环最大步数 (50，安全上限)
- `SYSTEM_PROMPT`: 系统提示词（包含工具和skill说明）

### src/bot_client.py
机器人客户端模块，核心类 `MyClient`：
- `on_ready()`: 启动时获取可用模型
- `on_c2c_message_create()`: 处理私聊消息
- `handle_command()`: 处理 `/清理`、`/会话` 指令
- `send_intermediate_result()`: 发送中间结果回调

### src/ai_client.py
AI客户端模块，处理与大模型的交互：
- `fetch_available_models()`: 从API获取可用模型列表
- `AIResponse`: AI响应封装类，包含content、finish_reason、tool_calls
- `call_ai_api_single()`: 单次调用AI API，返回结构化响应
- `agent_loop()`: 基于finish_reason的智能体循环
- `process_message_with_ai()`: 处理消息的主入口函数
- `parse_text_tool_call()`: 解析文本格式的工具调用（支持Qwen格式）
- 支持图片关键词检测，自动附带历史图片

### src/session_manager.py
会话管理模块（单用户模式）：
- `get_history_messages()`: 获取历史对话（限制20条）
- `update_last_ai_messages()`: 更新并保存消息到 memory.json
- `get_last_images()`: 获取最后发送的图片
- `set_last_images()`: 保存图片路径
- `clear_history()`: 清空对话历史

### src/image_handler.py
图片处理模块：
- `get_month_folder()`: 获取按月份分类的存储目录 (data/YYYY-MM/)
- `download_image()`: 异步下载图片
- `encode_image_to_base64()`: 图片转Base64编码
- `process_image_attachment()`: 处理消息中的图片附件

### src/skills/ (Skill系统)
**skill_service.py - Skill发现和缓存服务**
- `SkillService`: Skill服务类，管理所有skill的发现和加载
- `discover_skills()`: 扫描skills目录，发现所有SKILL.md文件
- `get_skill()`: 获取指定skill
- `list_skills()`: 列出所有已发现的skills

**核心特性**：
- 目录扫描：自动扫描 `skills/` 目录下的所有 `SKILL.md` 文件
- 延迟加载：只在AI调用时才加载skill内容，节省token
- 动态工具描述：工具描述包含所有可用skill列表
- 零配置扩展：拷贝新skill到目录即可，无需修改代码

### src/tools/ (工具模块)
**file_system.py - 文件系统工具**
- `list_directory`: 列出目录内容
- `read_file`: 读取文件内容
- `create_file`: 创建新文件
- `write_to_file`: 写入文件

**search.py - 搜索工具**
- `search_files`: 按文件名搜索（支持通配符和正则）
- `search_content`: 按内容搜索文件内部文本

**system.py - 系统工具**
- `execute_command`: 执行CMD/PowerShell命令
- `get_system_info`: 获取系统信息
- `get_process_list`: 获取进程列表

**network.py - 网络工具**
- `get_network_info`: 获取网络信息
- `ping_host`: Ping主机

**time.py - 时间工具**
- `get_current_time`: 获取当前时间

**skill.py - Skill工具**
- `load_skill`: 加载指定skill或列出所有可用skill
- 支持无参数调用列出所有技能
- 支持按名称加载特定技能指南

**tool_registry.py - 工具注册表**
- 聚合所有工具定义和函数映射
- 提供统一的工具调用接口

## Skill 技能系统

### 概述
Skill系统类似OpenCode的技能系统，允许AI加载专业技能指南来处理特定类型的任务。

### 已集成的Skills

| Skill名称 | 说明 |
|-----------|------|
| `pdf` | PDF文件处理（读取、合并、分割、提取、OCR等） |
| `xlsx` | Excel表格处理（读写、公式、格式化、数据分析） |
| `pptx` | PowerPoint演示文稿处理（创建、编辑、转换） |
| `webapp-testing` | Web应用测试（Playwright自动化测试） |
| `skill-creator` | 创建和优化Skill |
| `frontend-slides` | 创建HTML演示文稿 |

### Skill文件格式
```markdown
---
name: skill-name
description: 描述何时使用此skill
---

# Skill 详细指令
具体的指令内容、示例、最佳实践等...
```

### 扩展方式
1. 在 `skills/` 目录下创建新文件夹
2. 添加 `SKILL.md` 文件（按上述格式）
3. 重启程序，自动发现

## 大模型相关

### API调用格式
使用OpenAI兼容协议，调用 `/v1/chat/completions` 端点。

### 支持的功能
- 多轮对话历史
- 多模态图片理解（Base64编码）
- Function Calling 工具调用
- 文本格式工具调用解析（Qwen格式）

### 工具调用格式
支持两种格式：
1. **原生Function Calling**：OpenAI标准格式
2. **文本格式**：Qwen风格
   ```
   <function=search_files>
   <parameter=pattern>
   zhanghao.txt
   </parameter>
   </function>
   ```

## 智能体循环机制

基于 finish_reason 的 ReAct 模式：

```
用户提问
    ↓
调用大模型
    ↓
检查 finish_reason
    ├── tool_calls → 执行工具 → 添加工具消息 → 继续循环
    ├── stop / end_turn → 结束循环，返回结果
    └── 其他 → 结束循环，返回结果
```

### finish_reason 决定是否继续

| finish_reason | 行为     | 含义                               |
| ------------- | -------- | ---------------------------------- |
| `tool_calls`  | 继续循环 | 模型调用了工具，需要执行后返回结果 |
| `stop`        | 退出循环 | 模型认为任务完成                   |
| `end_turn`    | 退出循环 | 回合结束                           |
| `length`      | 退出循环 | 达到token限制                      |

## 环境变量配置

在 `.env` 文件中配置：
```
QQ_BOT_APPID=你的机器人AppID
QQ_BOT_SECRET=你的机器人Secret
```

## 依赖项

主要依赖：
- `qq-botpy`: QQ机器人SDK
- `aiohttp`: 异步HTTP客户端
- `python-dotenv`: 环境变量加载
- `psutil`: 系统信息获取（可选）

安装命令：
```bash
pip install qq-botpy aiohttp python-dotenv psutil
```

## 数据存储

- `data/memory.json`: 会话历史持久化存储（单用户模式）
- `data/YYYY-MM/`: 按月份存储的图片文件

## 指令系统

| 指令 | 说明 |
|------|------|
| `/清理` | 清空对话历史（洗脑） |
| `/会话` | 查看会话统计信息（消息数、图片数、Token预估、模型信息） |