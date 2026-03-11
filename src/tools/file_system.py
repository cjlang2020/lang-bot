"""
文件系统工具
- 列出目录
- 读取文件
- 创建文件
- 写入文件
"""

import os
from datetime import datetime
from botpy import logging

_log = logging.get_logger()

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "列出指定目录下的所有文件和文件夹",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径"},
                    "recursive": {"type": "boolean", "description": "是否递归列出", "default": False},
                    "show_details": {"type": "boolean", "description": "是否显示详细信息", "default": False}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定文件的内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "start_line": {"type": "integer", "description": "开始行号"},
                    "end_line": {"type": "integer", "description": "结束行号"},
                    "encoding": {"type": "string", "description": "文件编码", "default": "utf-8"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "创建新文件并写入内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "文件内容"},
                    "overwrite": {"type": "boolean", "description": "是否覆盖已存在的文件", "default": False}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_to_file",
            "description": "向现有文件追加或覆盖写入内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "写入内容"},
                    "mode": {"type": "string", "enum": ["append", "overwrite"], "description": "写入模式", "default": "append"}
                },
                "required": ["path", "content"]
            }
        }
    },
]


async def list_directory_tool(path: str, recursive: bool = False, show_details: bool = False) -> str:
    """列出目录"""
    try:
        abs_path = os.path.abspath(path) if os.path.isabs(path) else os.path.join(os.getcwd(), path)

        if not os.path.exists(abs_path):
            return f"❌ 错误：路径不存在 - {abs_path}"

        if not os.path.isdir(abs_path):
            return f"❌ 错误：路径不是目录 - {abs_path}"

        items = []
        if recursive:
            for root, dirs, files in os.walk(abs_path):
                for d in dirs:
                    items.append(f"[DIR]  {os.path.join(root, d)}")
                for f in files:
                    if show_details:
                        full_path = os.path.join(root, f)
                        try:
                            stat = os.stat(full_path)
                            size = stat.st_size
                            mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                            items.append(f"[FILE] {full_path} ({size} bytes, {mtime})")
                        except:
                            items.append(f"[FILE] {full_path}")
                    else:
                        items.append(f"[FILE] {os.path.join(root, f)}")
        else:
            for item in os.listdir(abs_path):
                full_path = os.path.join(abs_path, item)
                if os.path.isdir(full_path):
                    items.append(f"[DIR]  {item}/")
                else:
                    if show_details:
                        try:
                            stat = os.stat(full_path)
                            size = stat.st_size
                            mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                            items.append(f"[FILE] {item} ({size} bytes, {mtime})")
                        except:
                            items.append(f"[FILE] {item}")
                    else:
                        items.append(f"[FILE] {item}")

        result = f"📁 目录: {abs_path}\n" + "\n".join(items[:100])
        if len(items) > 100:
            result += f"\n... 还有 {len(items) - 100} 项"
        return result
    except Exception as e:
        return f"❌ 列出目录失败: {str(e)}"


async def read_file_tool(path: str, start_line: int = None, end_line: int = None, encoding: str = "utf-8") -> str:
    """读取文件"""
    try:
        abs_path = os.path.abspath(path) if os.path.isabs(path) else os.path.join(os.getcwd(), path)

        if not os.path.exists(abs_path):
            return f"❌ 错误：文件不存在 - {abs_path}"

        if not os.path.isfile(abs_path):
            return f"❌ 错误：路径不是文件 - {abs_path}"

        with open(abs_path, 'r', encoding=encoding, errors='ignore') as f:
            lines = f.readlines()

        total_lines = len(lines)

        if start_line is None:
            start_line = 1
        if end_line is None or end_line > total_lines:
            end_line = total_lines

        start_line = max(1, start_line)
        end_line = min(total_lines, end_line)

        selected_lines = lines[start_line - 1:end_line]

        content = ''.join(selected_lines)
        if len(content) > 10000:
            content = content[:10000] + "\n...（内容过长，已截断）"

        return f"📄 {abs_path} (第{start_line}-{end_line}行，共{total_lines}行)\n{'='*60}\n{content}"
    except Exception as e:
        return f"❌ 读取文件失败: {str(e)}"


async def create_file_tool(path: str, content: str, overwrite: bool = False) -> str:
    """创建文件"""
    try:
        abs_path = os.path.abspath(path) if os.path.isabs(path) else os.path.join(os.getcwd(), path)

        if os.path.exists(abs_path):
            if not overwrite:
                return f"❌ 文件已存在: {abs_path}\n如需覆盖，请设置 overwrite=True"

        directory = os.path.dirname(abs_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            _log.info(f"已创建目录: {directory}")

        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)

        file_size = os.path.getsize(abs_path)
        return f"✅ 文件创建成功: {abs_path}\n📝 大小: {file_size} 字节"
    except Exception as e:
        return f"❌ 创建文件失败: {str(e)}"


async def write_to_file_tool(path: str, content: str, mode: str = "append") -> str:
    """写入文件"""
    try:
        abs_path = os.path.abspath(path) if os.path.isabs(path) else os.path.join(os.getcwd(), path)

        if not os.path.exists(abs_path):
            return f"❌ 文件不存在: {abs_path}"

        if not os.path.isfile(abs_path):
            return f"❌ 路径不是文件: {abs_path}"

        if mode == "overwrite":
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)
            action = "覆盖写入"
        else:
            with open(abs_path, 'a', encoding='utf-8') as f:
                f.write(content)
            action = "追加写入"

        file_size = os.path.getsize(abs_path)
        return f"✅ {action}成功: {abs_path}\n📝 大小: {file_size} 字节"
    except Exception as e:
        return f"❌ 写入文件失败: {str(e)}"


# 工具函数映射
TOOL_FUNCTIONS = {
    "list_directory": list_directory_tool,
    "read_file": read_file_tool,
    "create_file": create_file_tool,
    "write_to_file": write_to_file_tool,
}
