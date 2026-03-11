# Lang-Bot QQ机器人

一个基于Python开发的QQ机器人，通过QQ发送消息到本项目，项目接收后转发给支持OpenAI协议的第三方大模型，大模型返回数据后再次返回给QQ用户。

## 功能特性

- **私聊消息处理**：接收QQ私聊消息，支持上下文对话
- **多模态图片理解**：支持发送图片，AI可分析图片内容
- **模块化工具调用**：按功能分类的工具系统（文件、搜索、系统、网络、时间）
- **Ripgrep高效搜索**：支持按文件名和内容搜索，替代Everything
- **智能体循环**：AI自动评估回复有效性，最多循环5次直到获得满意结果
- **中间过程可见**：每次AI回复、工具调用、模拟问话都会实时发送给用户
- **会话持久化**：对话历史保存到文件，程序重启后自动恢复

## 项目结构

```
lang-bot/
├── start_listener.py      # 主入口文件
├── .env                   # 环境变量配置
├── README.md
├── CLAUDE.md
├── data/                  # 数据目录
│   ├── memory.json        # 会话历史
│   └── YYYY-MM/           # 按月份存储的图片
└── src/
    ├── __init__.py
    ├── config.py          # 配置和常量
    ├── bot_client.py      # QQ机器人客户端
    ├── ai_client.py       # AI API调用（支持循环评估）
    ├── session_manager.py # 会话管理（单用户模式）
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

可选依赖（Everything文件搜索）：
```bash
pip install py-everything
```
注意：使用Everything搜索需要先安装并运行 [Everything软件](https://www.voidtools.com/)

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

AI可调用以下工具：

| 工具 | 说明 |
|------|------|
| `list_directory` | 列出目录内容 |
| `read_file` | 读取文件内容 |
| `create_file` | 创建新文件 |
| `write_to_file` | 写入文件 |
| `search_files` | 使用Everything快速搜索文件 |
| `execute_command` | 执行CMD/PowerShell命令 |
| `get_system_info` | 获取系统信息 |
| `get_process_list` | 获取进程列表 |
| `get_network_info` | 获取网络信息 |
| `ping_host` | Ping主机 |
| `get_current_time` | 获取当前时间 |

## 智能体循环机制

机器人会自动评估AI回复的有效性，最多循环5次：

```
用户提问
    ↓
调用大模型
    ↓
评估回复是否有效
    ├── 有效 → 返回结果
    └── 无效 → 智能体追问 → 再次调用大模型
```

### 中间消息示例

用户可以实时看到AI的思考过程：
```
🤖 正在思考...
🔧 调用工具: search_files
📋 工具结果: 找到3个文件...
🤖 AI回复: 文件已找到...
🔄 第2次尝试...
💭 智能体追问: 你的回答似乎没有解决问题...
```

## 配置说明

在 `src/config.py` 中可修改以下配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `AI_API_BASE_URL` | `http://127.0.0.1:9900/v1` | AI API地址 |
| `MAX_CONCURRENT_REQUESTS` | 10 | 最大并发请求数 |
| `MAX_LOOP_COUNT` | 5 | 智能体循环最大次数 |
| `MAX_HISTORY_LENGTH` | 20 | 历史记录最大条数 |

## 数据存储

- `data/memory.json`：会话历史持久化存储（单用户模式）
- `data/YYYY-MM/`：按月份存储的图片文件

## 数据流程

```
QQ用户发送消息 → bot_client.py 接收
       ↓
检查是否为指令 → 是 → 执行指令，返回结果
       ↓ 否
检查是否有图片 → 下载图片到 data/ 目录
       ↓
ai_client.py → 加载历史对话 → 构建消息 → 调用大模型
       ↓
智能体循环（最多5次）：
  - 发送中间结果给用户
  - 评估回复有效性
  - 无效则构建模拟问话继续
       ↓
保存历史 → 返回最终结果给QQ用户
```

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
- 消息去重延迟，避免QQ API限制

## License

MIT