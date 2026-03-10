# CLAUDE.md

这是一个QQ机器人项目，通过QQ发送信息到本项目，项目接收后转发给支持OPENAI协议的第三方大模型，大模型返回数据后再次返回给QQ用户

## 项目简介

技术是python开发。
环境是conda创建的，pyhton3.12版本的，路径是：D:\AI\botpy-master\envs
通过：conda activate D:\AI\botpy-master\envs 激活

项目分析时忽略envs和data等文件夹

涉及到的代码如果有扩展代码，也就是不能所有代码放一个文件，需要分开，代码可放在src目录下

## 项目结构

```
lang-bot/
├── start_listener.py      # 主入口文件
├── .env                   # 环境变量配置（QQ机器人凭证）
├── .gitignore
├── CLAUDE.md
└── src/
    ├── __init__.py
    ├── config.py          # 配置和常量
    ├── bot_client.py      # QQ机器人客户端
    ├── ai_client.py       # AI API调用
    ├── session_manager.py # 会话管理
    ├── image_handler.py   # 图片处理
    ├── windows_tools.py   # Windows工具函数
    └── main.py            # 备用入口（未使用）
```

## 主要功能

- 接收QQ私聊消息
- 支持图片消息的多模态处理
- 支持工具调用（文件操作、系统命令等）
- 会话历史管理，支持上下文对话
- 图片历史记忆，用户可以引用之前的图片

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
│  │              生成 session_id (c2c_xxx)                               │   │
│  │                          ↓                                          │   │
│  │              检查是否有图片附件                                       │   │
│  │                          ↓                                          │   │
│  │              调用 process_image_attachment() 下载图片                 │   │
│  │                          ↓                                          │   │
│  │              调用 process_message_with_ai() 处理消息                  │   │
│  └──────────────────────────┼──────────────────────────────────────────┘   │
│                             ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        ai_client.py                                  │   │
│  │                                                                      │   │
│  │  1. 加载系统提示词 (SYSTEM_PROMPT)                                    │   │
│  │  2. 从 session_manager 加载历史对话                                   │   │
│  │  3. 检查是否需要附带历史图片                                           │   │
│  │  4. 构建消息列表，处理图片为Base64                                     │   │
│  │  5. 调用 call_ai_api() 请求大模型                                     │   │
│  │     ├── 如果AI返回工具调用 → process_tool_calls() 执行工具            │   │
│  │     │   └── 再次调用AI，传入工具结果                                   │   │
│  │     └── 如果AI返回普通回复 → 直接返回                                  │   │
│  │  6. 保存对话历史到 session_manager                                    │   │
│  └──────────────────────────┼──────────────────────────────────────────┘   │
│                             ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        bot_client.py                                 │   │
│  │              回复AI结果给QQ用户                                        │   │
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
- `SESSION_EXPIRE_TIME`: 会话过期时间 (3600秒)
- `MAX_HISTORY_LENGTH`: 历史记录最大长度 (20条)
- `SYSTEM_PROMPT`: 系统提示词

### src/bot_client.py
机器人客户端模块，核心类 `MyClient`：
- `on_ready()`: 启动时获取可用模型
- `on_c2c_message_create()`: 处理私聊消息，使用用户openid作为会话ID

### src/ai_client.py
AI客户端模块，处理与大模型的交互：
- `fetch_available_models()`: 从API获取可用模型列表
- `call_ai_api()`: 调用AI API（支持多模态和工具调用）
- `process_message_with_ai()`: 处理消息的主入口函数
- 支持图片关键词检测，自动附带历史图片

### src/session_manager.py
会话管理模块：
- `session_histories`: 全局会话缓存字典
- `get_session()`: 获取会话历史
- `add_to_session()`: 添加消息到会话
- `get_last_images()`: 获取会话中最后的图片
- `set_last_images()`: 保存图片路径
- `cleanup_expired_sessions()`: 清理过期会话

### src/image_handler.py
图片处理模块：
- `get_month_folder()`: 获取按月份分类的存储目录 (data/YYYY-MM/)
- `download_image()`: 异步下载图片
- `encode_image_to_base64()`: 图片转Base64编码
- `process_image_attachment()`: 处理消息中的图片附件

### src/windows_tools.py
Windows工具模块，提供AI可调用的工具函数：

**文件系统工具：**
- `list_directory`: 列出目录内容
- `read_file`: 读取文件内容
- `create_file`: 创建新文件
- `write_to_file`: 写入文件
- `search_files`: 搜索文件

**系统工具：**
- `execute_command`: 执行CMD/PowerShell命令
- `get_system_info`: 获取系统信息（CPU/内存/磁盘/网络）
- `get_process_list`: 获取进程列表

**网络工具：**
- `get_network_info`: 获取网络信息
- `ping_host`: Ping主机

**时间工具：**
- `get_current_time`: 获取当前时间

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