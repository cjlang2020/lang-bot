# CLAUDE.md

这是一个QQ机器人项目，通过QQ发送信息到本项目，项目接收后转发给支持OPENAI协议的第三方大模型，大模型返回数据后再次返回给QQ用户。

## 项目简介

技术是python开发。
环境是conda创建的，pyhton3.12版本的，路径是：D:\AI\botpy-master\envs
做测试必须使用这个环境

项目分析时忽略envs、data、qq-api等文件夹

涉及到的代码如果有扩展代码，也就是不能所有代码放一个文件，需要分开，代码可放在src目录下


## 项目结构

```
lang-bot/
├── start_listener.py          # 主入口文件
├── .env                       # 环境变量配置（QQ机器人凭证）
├── .gitignore
├── CLAUDE.md
├── README.md
├── test_ripgrep.py            # Ripgrep测试脚本
├── 搜索工具更新说明.md
├── Ripgrep搜索工具使用指南.md
└── src/
    ├── __init__.py
    ├── config.py              # 配置和常量
    ├── bot_client.py          # QQ机器人客户端
    ├── ai_client.py           # AI API调用（基于finish_reason的智能体循环）
    ├── session_manager.py     # 会话管理（单用户模式）
    ├── image_handler.py       # 图片处理
    ├── search_tools.py        # Ripgrep搜索工具核心实现
    ├── windows_tools.py       # Windows工具（向后兼容，已迁移到src/tools）
    └── tools/                 # AI工具模块（按功能拆分）
        ├── __init__.py
        ├── file_system.py     # 文件系统工具（列表、读写文件）
        ├── search.py          # 文件搜索工具（Ripgrep）
        ├── system.py          # 系统工具（命令、进程、系统信息）
        ├── network.py         # 网络工具（网络信息、Ping）
        ├── time.py            # 时间工具
        └── tool_registry.py   # 工具注册表（聚合所有工具）
```

## 主要功能

- 接收QQ私聊消息
- 支持图片消息的多模态处理
- 支持工具调用（文件操作、系统命令、网络操作、进程管理等）
- 会话历史管理，支持上下文对话
- 图片历史记忆，用户可以引用之前的图片
- **智能体循环机制**：基于finish_reason的自动循环，让模型自己决定何时完成任务
- **中间过程可见**：每次工具调用和结果都会实时发送给QQ用户
- **Ripgrep高效搜索**：支持按文件名和内容搜索（替代Everything）
- **模块化工具设计**：所有工具按功能分类，易于维护和扩展

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
- `MAX_HISTORY_LENGTH`: 历史记录最大长度 (20条)
- `SYSTEM_PROMPT`: 系统提示词

### src/bot_client.py
机器人客户端模块，核心类 `MyClient`：
- `on_ready()`: 启动时获取可用模型
- `on_c2c_message_create()`: 处理私聊消息
- `handle_command()`: 处理 `/清理`、`/会话` 指令
- `send_intermediate_result()`: 发送中间结果回调（带消息去重延迟）

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
- `last_ai_messages`: 最后一次发送给大模型的完整消息
- `last_images`: 最后发送的图片路径
- `get_history_messages()`: 获取历史对话（不含系统提示词，限制20条）
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

### src/windows_tools.py
Windows工具模块（向后兼容，实际功能已迁移到 `src/tools/` 目录）

### src/tools/ (新增)
工具模块目录，按功能分类拆分所有AI可调用的工具函数：

**src/tools/file_system.py - 文件系统工具**
- `list_directory`: 列出目录内容
- `read_file`: 读取文件内容
- `create_file`: 创建新文件
- `write_to_file`: 写入文件

**src/tools/search.py - 搜索工具（使用Ripgrep）**
- `search_files`: 按文件名搜索（支持通配符和正则）
- `search_content`: 按内容搜索文件内部文本

**src/tools/system.py - 系统工具**
- `execute_command`: 执行CMD/PowerShell命令
- `get_system_info`: 获取系统信息（CPU/内存/磁盘/网络）
- `get_process_list`: 获取进程列表

**src/tools/network.py - 网络工具**
- `get_network_info`: 获取网络信息
- `ping_host`: Ping主机

**src/tools/time.py - 时间工具**
- `get_current_time`: 获取当前时间

**src/tools/tool_registry.py - 工具注册表**
- 聚合所有工具定义和函数映射
- 提供统一的工具调用接口

## 大模型相关

### API调用格式
使用OpenAI兼容协议，调用 `/v1/chat/completions` 端点。

### 请求参数
```json
{
  "model": "模型名称",
  "messages": [...],
  "temperature": 0.7,
  "max_tokens": 128000,
  "tools": [...],
  "tool_choice": "auto"
}
```

### 支持的功能
- 多轮对话历史
- 多模态图片理解（Base64编码）
- Function Calling 工具调用
- 文本格式工具调用解析（Qwen格式：`<function=name>...</function>`）

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

基于 finish_reason 的 ReAct (Reasoning + Acting) 模式：

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

### 中间消息发送
每次循环过程中的以下信息都会实时发送给QQ用户：
- `🔧 调用工具: xxx`
- `📋 [工具名] 工具结果: xxx`

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
- `py-everything`: Everything文件搜索（可选，需要Everything软件运行）

安装命令：
```bash
pip install qq-botpy aiohttp python-dotenv psutil py-everything
```

## 数据存储

- `data/memory.json`: 会话历史持久化存储（单用户模式）
- `data/YYYY-MM/`: 按月份存储的图片文件

## 指令系统

| 指令 | 说明 |
|------|------|
| `/清理` | 清空对话历史（洗脑） |
| `/会话` | 查看会话统计信息（消息数、图片数、Token预估、模型信息） |