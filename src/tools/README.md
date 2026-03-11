# 工具模块说明

## 概述

本项目的所有AI可调用工具都已模块化，按功能分类放在 `src/tools/` 目录下。这种设计使得代码更加清晰、易于维护和扩展。

## 模块结构

```
src/tools/
├── __init__.py           # 工具包初始化，导出统一接口
├── file_system.py        # 文件系统工具
├── search.py             # 搜索工具
├── system.py             # 系统工具
├── network.py            # 网络工具
├── time.py               # 时间工具
└── tool_registry.py      # 工具注册表（聚合所有工具）
```

## 模块说明

### 1. file_system.py - 文件系统工具

提供基本的文件和目录操作。

**工具列表：**

| 工具名 | 说明 | 必填参数 | 可选参数 |
|--------|------|----------|----------|
| `list_directory` | 列出目录内容 | path | recursive, show_details |
| `read_file` | 读取文件内容 | path | start_line, end_line, encoding |
| `create_file` | 创建新文件 | path, content | overwrite |
| `write_to_file` | 写入文件 | path, content | mode |

**使用示例：**
```json
{
  "name": "list_directory",
  "arguments": {
    "path": "D:\\projects",
    "recursive": false,
    "show_details": true
  }
}
```

---

### 2. search.py - 搜索工具

使用 Ripgrep 进行高效文件搜索，支持按文件名和内容搜索。

**工具列表：**

| 工具名 | 说明 | 必填参数 | 可选参数 |
|--------|------|----------|----------|
| `search_files` | 按文件名搜索 | pattern | directory, max_results |
| `search_content` | 按内容搜索 | pattern | directory, file_type, ignore_case, max_results, show_context |

**使用示例：**
```json
// 按文件名搜索
{
  "name": "search_files",
  "arguments": {
    "pattern": "*.py",
    "directory": "D:\\projects",
    "max_results": 50
  }
}

// 按内容搜索
{
  "name": "search_content",
  "arguments": {
    "pattern": "TODO",
    "directory": "D:\\projects",
    "file_type": "py",
    "ignore_case": true,
    "max_results": 20
  }
}
```

**搜索模式说明：**
- `*.pdf` - 所有 PDF 文件
- `*.py` - 所有 Python 文件
- `关键词` - 搜索包含该词的文件名或内容
- `正则表达式` - 支持完整正则表达式

---

### 3. system.py - 系统工具

提供Windows系统操作功能。

**工具列表：**

| 工具名 | 说明 | 必填参数 | 可选参数 |
|--------|------|----------|----------|
| `execute_command` | 执行系统命令 | command | shell, timeout |
| `get_system_info` | 获取系统信息 | info_type | - |
| `get_process_list` | 获取进程列表 | - | filter_name, show_details, max_results |

**使用示例：**
```json
{
  "name": "execute_command",
  "arguments": {
    "command": "dir",
    "shell": "cmd",
    "timeout": 30
  }
}

{
  "name": "get_system_info",
  "arguments": {
    "info_type": "all"
  }
}
```

---

### 4. network.py - 网络工具

提供网络相关功能。

**工具列表：**

| 工具名 | 说明 | 必填参数 | 可选参数 |
|--------|------|----------|----------|
| `get_network_info` | 获取网络信息 | - | detail_level |
| `ping_host` | Ping主机 | host | count |

**使用示例：**
```json
{
  "name": "ping_host",
  "arguments": {
    "host": "www.baidu.com",
    "count": 4
  }
}
```

---

### 5. time.py - 时间工具

获取当前时间信息。

**工具列表：**

| 工具名 | 说明 | 必填参数 | 可选参数 |
|--------|------|----------|----------|
| `get_current_time` | 获取当前时间 | - | format |

**使用示例：**
```json
{
  "name": "get_current_time",
  "arguments": {
    "format": "full"
  }
}
```

**格式选项：**
- `full` - 完整日期时间（默认）
- `date` - 仅日期
- `time` - 仅时间
- `timestamp` - 时间戳

---

## 统一接口

所有工具通过 `src/tools/tool_registry.py` 统一管理和导出。

### 导入方式

```python
from src.tools import TOOLS, TOOL_FUNCTIONS, process_tool_calls

# TOOLS: 所有工具的定义列表（用于AI Function Calling）
# TOOL_FUNCTIONS: 工具名称到函数的映射
# process_tool_calls: 工具调用处理函数
```

### 工具定义格式

每个工具定义遵循 OpenAI Function Calling 标准：

```json
{
  "type": "function",
  "function": {
    "name": "工具名称",
    "description": "工具描述",
    "parameters": {
      "type": "object",
      "properties": {
        "参数名": {
          "type": "类型",
          "description": "参数描述",
          "default": "默认值（可选）"
        }
      },
      "required": ["必填参数列表"]
    }
  }
}
```

---

## 扩展工具

### 添加新工具步骤

1. **选择合适的模块文件**，或创建新的模块文件
2. **定义工具函数**，使用 `async def` 异步函数
3. **定义工具Schema**，添加到 `TOOL_DEFINITIONS` 列表
4. **更新工具映射**，在 `TOOL_FUNCTIONS` 字典中添加映射
5. **tool_registry.py** 会自动聚合所有工具

### 示例：添加新工具

在 `file_system.py` 中添加新工具：

```python
# 1. 定义工具函数
async def delete_file_tool(path: str) -> str:
    """删除文件"""
    try:
        os.remove(path)
        return f"✅ 文件已删除: {path}"
    except Exception as e:
        return f"❌ 删除失败: {str(e)}"

# 2. 定义工具Schema
TOOL_DEFINITIONS.append({
    "type": "function",
    "function": {
        "name": "delete_file",
        "description": "删除指定文件",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"}
            },
            "required": ["path"]
        }
    }
})

# 3. 更新工具映射
TOOL_FUNCTIONS["delete_file"] = delete_file_tool
```

---

## 优势

### 模块化设计的优势

1. **代码清晰**：每个模块只负责一个功能领域
2. **易于维护**：修改某个工具不影响其他工具
3. **易于测试**：可以单独测试每个工具模块
4. **易于扩展**：添加新工具只需在对应模块中添加
5. **职责分离**：工具定义、工具函数、工具注册表分离

### 相比单文件的优势

- ✅ 减少单个文件代码行数（从700+行减少到每个模块100-200行）
- ✅ 更好的命名空间管理
- ✅ 更清晰的依赖关系
- ✅ 更容易找到特定功能的代码
- ✅ 更适合团队协作开发

---

## 测试工具

运行以下命令测试 Ripgrep 搜索功能：

```bash
python test_ripgrep.py
```

---

## 注意事项

1. **工具名称唯一性**：所有工具的 `name` 字段必须唯一
2. **参数验证**：工具函数应该处理参数验证和错误处理
3. **返回格式**：工具函数应该返回字符串结果，错误时也返回错误信息
4. **异步执行**：所有工具函数都应该是异步的（`async def`）
5. **安全性**：执行系统命令或文件操作时要注意安全性

---

## 相关文档

- [CLAUDE.md](../CLAUDE.md) - 项目详细说明
- [README.md](../README.md) - 项目使用指南
- [搜索工具更新说明.md](../搜索工具更新说明.md) - Ripgrep搜索替换说明
- [Ripgrep搜索工具使用指南.md](../Ripgrep搜索工具使用指南.md) - Ripgrep使用指南
