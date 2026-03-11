# Ripgrep 搜索工具使用指南

## 概述

本项目现在使用 **ripgrep (rg)** 作为主要的文件搜索工具，提供了两种搜索方式：

1. **按文件名搜索**: 搜索文件名称（类似于原来的 Everything 搜索）
2. **按内容搜索**: 搜索文件内部的文本内容（新增功能）

## 安装

### 安装 Ripgrep

**推荐使用 Scoop (Windows):**
```bash
scoop install ripgrep
```

**或使用 Chocolatey:**
```bash
choco install ripgrep
```

**或手动下载:**
从 [GitHub Releases](https://github.com/BurntSushi/ripgrep/releases) 下载并添加到系统 PATH

### 验证安装

```bash
rg --version
```

如果显示版本信息，说明安装成功。

## 使用方法

### 1. 按文件名搜索

用于查找特定名称或类型的文件。

**AI 工具调用:**
```json
{
  "name": "search_files",
  "arguments": {
    "pattern": "*.pdf",
    "directory": "D:\\documents",
    "max_results": 50
  }
}
```

**参数说明:**
- `pattern` (必需): 搜索模式
  - `*.pdf` - 所有 PDF 文件
  - `*.py` - 所有 Python 文件
  - `config` - 包含 "config" 关键词的文件
  - `.*\.txt$` - 正则表达式，匹配所有 .txt 文件
- `directory` (可选): 搜索目录，不填则当前目录
- `max_results` (可选): 最大结果数，默认 50

**示例:**
```
/search_files pattern="*.py" directory="D:\\projects"
/search_files pattern="README" directory="." max_results=10
```

### 2. 按内容搜索

用于查找包含特定文本的文件（新功能！）。

**AI 工具调用:**
```json
{
  "name": "search_content",
  "arguments": {
    "pattern": "API_KEY",
    "directory": "D:\\projects",
    "file_type": "py",
    "ignore_case": true,
    "max_results": 20,
    "show_context": 1
  }
}
```

**参数说明:**
- `pattern` (必需): 要搜索的文本或正则表达式
  - `TODO` - 搜索包含 TODO 的文件
  - `def main` - 搜索包含 def main 的文件
  - `error.*timeout` - 正则表达式
- `directory` (可选): 搜索目录，不填则当前目录
- `file_type` (可选): 文件类型，如 "py", "txt", "md"
- `ignore_case` (可选): 是否忽略大小写，默认 false
- `max_results` (可选): 最大结果数，默认 50
- `show_context` (可选): 显示匹配行的上下文行数，默认 0

**示例:**
```
/search_content pattern="TODO" directory="D:\\projects"
/search_content pattern="import os" directory="." file_type="py" ignore_case=true
/search_content pattern="error" directory="D:\\logs" show_context=2
```

## 实际应用场景

### 场景 1: 查找配置文件
```
/search_files pattern="config" directory="D:\\projects"
```

### 场景 2: 查找所有 Python 文件
```
/search_files pattern="*.py" directory="D:\\projects"
```

### 场景 3: 查找包含 API 密钥的文件
```
/search_content pattern="API_KEY" directory="D:\\projects" file_type="py"
```

### 场景 4: 查找代码中的 TODO 注释
```
/search_content pattern="TODO" directory="D:\\projects" file_type="py" show_context=1
```

### 场景 5: 查找错误日志
```
/search_content pattern="error" directory="D:\\logs" ignore_case=true show_context=2
```

### 场景 6: 查找特定函数定义
```
/search_content pattern="def main" directory="D:\\projects" file_type="py"
```

## 对比 Everything

| 功能 | Everything | Ripgrep |
|------|------------|---------|
| 安装 | 需要安装大型软件 | 只需一个可执行文件 |
| 后台服务 | 需要运行 | 不需要 |
| 按文件名搜索 | ✅ | ✅ |
| **按内容搜索** | ❌ | ✅ |
| 正则表达式 | 有限支持 | 完整支持 |
| 跨平台 | Windows 专用 | ✅ 全平台 |
| 性能 | ⚡ 极快（索引） | 🚀 很快（实时） |

## 常见问题

### Q: 搜索很慢怎么办？
A: 尝试以下优化：
1. 使用 `glob` 参数限制搜索范围：`*.py` 只搜索 Python 文件
2. 限制搜索目录：不要搜索整个 C 盘
3. 使用 `max_depth` 限制目录深度

### Q: 找不到文件怎么办？
A: 检查：
1. 路径是否正确（使用绝对路径）
2. 文件是否被 .gitignore 排除
3. 是否需要包含隐藏文件（添加 `hidden=true`）

### Q: 搜索中文乱码怎么办？
A: 确保文件是 UTF-8 编码，ripgrep 默认使用 UTF-8

### Q: 如何搜索多个文件类型？
A: 使用多个搜索，或使用正则：`.*\.(py|txt|md)$`

## 高级用法

### 组合搜索
先按文件名搜索，再按内容筛选：
```
1. /search_files pattern="*.py" directory="D:\\projects"
2. /search_content pattern="TODO" directory="上一步的结果目录"
```

### 正则表达式
```
/search_content pattern="error.*timeout" directory="D:\\logs" ignore_case=true
```

### 通配符
```
/search_files pattern="log*2025*.txt" directory="D:\\logs"
```

## 技术细节

- 搜索工具实现在 `src/search_tools.py`
- 集成到 `src/windows_tools.py` 作为工具函数
- 支持异步搜索，不会阻塞主程序
- 自动限制结果数量，避免返回过多数据
- 格式化输出，易于阅读

## 故障排查

运行测试脚本验证安装：
```bash
python test_ripgrep.py
```

如果测试失败，请检查：
1. ripgrep 是否正确安装
2. `rg` 命令是否在 PATH 中
3. 是否有权限访问搜索目录

## 反馈

如有问题或建议，请创建 Issue。
