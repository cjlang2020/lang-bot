# Lang-Bot QQ机器人

一个基于Python开发的QQ机器人，通过QQ发送消息到本项目，项目接收后转发给支持OpenAI协议的第三方大模型，大模型返回数据后再次返回给QQ用户。

## 功能特性

- **私聊消息处理**：接收QQ私聊消息，支持上下文对话
- **多模态图片理解**：支持发送图片，AI可分析图片内容
- **工具调用**：AI可调用工具执行文件操作、系统命令等
- **会话持久化**：对话历史保存到文件，程序重启后自动恢复
- **会话管理**：支持清理会话、查看会话统计等指令

## 项目结构

```
lang-bot/
├── start_listener.py      # 主入口文件
├── .env                   # 环境变量配置
├── README.md
├── CLAUDE.md
└── src/
    ├── __init__.py
    ├── config.py          # 配置和常量
    ├── bot_client.py      # QQ机器人客户端
    ├── ai_client.py       # AI API调用
    ├── session_manager.py # 会话管理
    ├── image_handler.py   # 图片处理
    └── windows_tools.py   # Windows工具函数
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
| `/清理` | 清空当前会话的所有历史记录 |
| `/会话` | 查看当前会话统计信息（消息数、图片数、Token预估、当前模型） |

## AI工具调用

AI可调用以下工具：

| 工具 | 说明 |
|------|------|
| `list_directory` | 列出目录内容 |
| `read_file` | 读取文件内容 |
| `create_file` | 创建新文件 |
| `write_to_file` | 写入文件 |
| `execute_command` | 执行安全shell命令 |
| `search_files` | 搜索文件 |
| `get_system_info` | 获取系统信息 |

## 配置说明

在 `src/config.py` 中可修改以下配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `AI_API_BASE_URL` | `http://127.0.0.1:9900/v1` | AI API地址 |
| `MAX_CONCURRENT_REQUESTS` | 10 | 最大并发请求数 |
| `SESSION_EXPIRE_TIME` | 0 | 会话过期时间（0=永不过期） |
| `MAX_HISTORY_LENGTH` | 20000 | 历史记录最大长度 |

## 数据存储

- `data/memory.json`：会话历史持久化存储
- `data/YYYY-MM/`：按月份存储的图片文件

## 数据流程

```
QQ用户发送消息 → bot_client.py 接收 → 生成 session_id
       ↓
检查是否为指令 → 是 → 执行指令，返回结果
       ↓ 否
检查是否有图片 → 下载图片到 data/ 目录
       ↓
ai_client.py → 加载历史对话 → 构建消息 → 调用大模型
       ↓
大模型返回 → 保存历史 → 返回给QQ用户
```

## 开发说明

- 模块化设计，各功能独立
- 支持热重载历史会话
- 图片自动转Base64发送给大模型
- 支持引用历史图片进行分析

## License

MIT
