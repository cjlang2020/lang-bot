# AGENTS.md

## 项目概述

这是一个QQ机器人项目，通过QQ私聊消息与大模型交互，支持工具调用和专业技能(Skill)加载。

## AI代理行为规范

### 核心能力

作为本项目的AI代理，具备以下能力：

1. **基础工具调用**：文件操作、系统命令、网络操作、搜索等
2. **Skill技能加载**：根据任务类型自动加载专业技能指南
3. **多模态理解**：支持图片分析和处理
4. **上下文记忆**：维护对话历史，支持连续对话

### 工具使用优先级

当用户请求涉及特定领域任务时，优先加载对应的Skill：

| 任务类型 | 应加载的Skill |
|----------|---------------|
| PDF文件处理 | `skill(name="pdf")` |
| Excel表格处理 | `skill(name="xlsx")` |
| PPT演示文稿 | `skill(name="pptx")` |
| Web应用测试 | `skill(name="webapp-testing")` |
| 创建新Skill | `skill(name="skill-creator")` |

### 用户询问"有哪些skill"时的处理

当用户询问"你有哪些skill"、"你有什么技能"、"你有什么能力"时：
1. **必须**调用 `skill()` 工具（不传参数）
2. 返回所有可用技能的完整列表
3. 简要介绍每个技能的用途

### 工具调用流程

```
1. 分析用户请求
2. 判断是否需要加载Skill
   - 专业领域任务 → 先加载对应Skill
   - 通用任务 → 直接使用基础工具
3. 执行工具调用
4. 返回结果给用户
```

## 项目架构

```
src/
├── config.py           # 配置（API地址、循环上限、系统提示词）
├── bot_client.py       # QQ机器人客户端（消息接收、指令处理）
├── ai_client.py        # AI客户端（API调用、智能体循环）
├── session_manager.py  # 会话管理（历史对话持久化）
├── image_handler.py    # 图片处理（下载、Base64编码）
├── skills/             # Skill系统
│   └── skill_service.py # Skill发现和缓存服务
└── tools/              # 工具模块
    ├── file_system.py  # 文件操作
    ├── search.py       # 文件搜索
    ├── system.py       # 系统命令
    ├── network.py      # 网络工具
    ├── time.py         # 时间工具
    ├── skill.py        # Skill工具
    └── tool_registry.py # 工具注册表
```

## Skill系统

### 工作原理

1. **启动扫描**：程序启动时自动扫描 `skills/` 目录
2. **解析元数据**：从每个 `SKILL.md` 文件的YAML frontmatter中提取name和description
3. **动态描述**：工具描述包含所有可用skill列表，帮助AI发现合适的skill
4. **按需加载**：AI调用时才加载完整skill内容，节省token

### Skill文件格式

```markdown
---
name: skill-name
description: 描述何时使用此skill（会在工具描述中展示）
---

# Skill 详细指令

具体的指令内容、示例、最佳实践等...
```

### 当前可用Skills

| Skill | 触发场景 |
|-------|----------|
| `pdf` | 用户提到.pdf文件或需要PDF处理 |
| `xlsx` | 用户提到.xlsx/.csv文件或需要表格处理 |
| `pptx` | 用户提到.pptx文件或需要PPT处理 |
| `webapp-testing` | 用户需要测试Web应用 |
| `skill-creator` | 用户需要创建或优化Skill |
| `frontend-slides` | 用户需要创建HTML演示文稿 |

### 扩展Skill

只需将包含 `SKILL.md` 的文件夹放入 `skills/` 目录，重启程序即可自动发现。无需修改任何代码。

## 智能体循环

基于 `finish_reason` 的 ReAct 模式：

```python
while step < MAX_STEPS:
    response = call_ai_api(messages, tools)
    
    if response.finish_reason == "tool_calls":
        # 执行工具，继续循环
        results = execute_tools(response.tool_calls)
        messages.append(results)
        continue
    
    if response.finish_reason in ["stop", "end_turn"]:
        # 任务完成，退出循环
        return response.content
```

## 用户指令

| 指令 | 说明 |
|------|------|
| `/清理` | 清空对话历史（洗脑） |
| `/会话` | 查看会话统计信息 |

## 技术规范

### 开发环境
- Python 3.12
- Conda环境路径：`D:\AI\botpy-master\envs`

### 代码风格
- 模块化设计，功能独立
- 异步函数使用 `async def`
- 工具函数返回字符串结果
- 错误信息以 `❌` 开头

### 忽略目录
- `envs/`：虚拟环境
- `data/`：运行时数据
- `qq-api/`：API相关

## 配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `AI_API_BASE_URL` | `http://127.0.0.1:9900/v1` | AI API地址 |
| `MAX_CONCURRENT_REQUESTS` | 10 | 最大并发请求数 |
| `MAX_STEPS` | 50 | 智能体循环上限 |

## 调试

运行Skill系统测试：
```bash
python test_skill_system.py
```