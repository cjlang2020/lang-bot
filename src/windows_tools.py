"""
Windows代理工具模块 - 提供Windows系统操作的各种工具函数
支持文件系统操作、系统管理、网络操作、注册表操作等功能
"""

import os
import asyncio
import subprocess
import json
import platform
import shutil
import winreg
from typing import Dict, Any, List
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None

# 日志记录
from botpy import logging
_log = logging.get_logger()


# ==================== 工具定义列表 ====================
TOOLS = [
    # 文件系统工具
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
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "在指定目录中搜索文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "搜索目录"},
                    "pattern": {"type": "string", "description": "文件名模式（支持通配符）"},
                    "recursive": {"type": "boolean", "description": "是否递归搜索", "default": True},
                    "max_results": {"type": "integer", "description": "最大结果数", "default": 50}
                },
                "required": ["directory", "pattern"]
            }
        }
    },
    # Windows系统工具
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "执行系统命令（cmd或powershell）",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"},
                    "shell": {"type": "string", "enum": ["cmd", "powershell"], "description": "使用的shell", "default": "cmd"},
                    "timeout": {"type": "integer", "description": "超时时间（秒）", "default": 30}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "获取Windows系统信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "info_type": {"type": "string", "enum": ["os", "cpu", "memory", "disk", "network", "all"], "description": "信息类型"}
                },
                "required": ["info_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_process_list",
            "description": "获取进程列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "进程名过滤器"},
                    "show_details": {"type": "boolean", "description": "显示详细信息", "default": True},
                    "max_results": {"type": "integer", "description": "最大结果数", "default": 30}
                }
            }
        }
    },
    # 网络工具
    {
        "type": "function",
        "function": {
            "name": "get_network_info",
            "description": "获取网络信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "detail_level": {"type": "string", "enum": ["basic", "detailed"], "description": "详细程度", "default": "basic"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ping_host",
            "description": "Ping指定主机",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "主机地址"},
                    "count": {"type": "integer", "description": "Ping次数", "default": 4}
                },
                "required": ["host"]
            }
        }
    },
    # 时间工具
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["full", "date", "time", "timestamp"], "description": "时间格式", "default": "full"}
                }
            }
        }
    },
]


# ==================== 工具函数实现 ====================

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


async def search_files_tool(directory: str, pattern: str, recursive: bool = True, max_results: int = 50) -> str:
    """搜索文件"""
    try:
        abs_dir = os.path.abspath(directory) if os.path.isabs(directory) else os.path.join(os.getcwd(), directory)

        if not os.path.exists(abs_dir):
            return f"❌ 目录不存在: {abs_dir}"

        import fnmatch
        matches = []

        if recursive:
            for root, dirs, files in os.walk(abs_dir):
                for filename in files:
                    if fnmatch.fnmatch(filename, pattern):
                        matches.append(os.path.join(root, filename))
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
        else:
            for filename in os.listdir(abs_dir):
                if fnmatch.fnmatch(filename, pattern):
                    matches.append(os.path.join(abs_dir, filename))
                    if len(matches) >= max_results:
                        break

        result = f"🔍 搜索: {pattern} in {abs_dir}\n"
        result += f"找到 {len(matches)} 个文件:\n"
        result += "\n".join([f"  - {m}" for m in matches])

        if len(matches) >= max_results:
            result += f"\n... 还有更多文件（已限制显示{max_results}个）"

        return result
    except Exception as e:
        return f"❌ 搜索失败: {str(e)}"


async def execute_command_tool(command: str, shell: str = "cmd", timeout: int = 30) -> str:
    """执行命令"""
    try:
        if shell == "cmd":
            full_cmd = f'cmd /c "{command}"'
        else:
            full_cmd = f'powershell -Command "{command}"'

        process = await asyncio.create_subprocess_shell(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

            output = stdout.decode('gbk', errors='ignore') or stdout.decode('utf-8', errors='ignore')
            error = stderr.decode('gbk', errors='ignore') or stderr.decode('utf-8', errors='ignore')

            result = f"💻 执行命令 ({shell}): {command}\n"
            result += f"Exit Code: {process.returncode}\n"
            if output:
                result += f"\n📋 标准输出:\n{output[:3000]}"
            if error:
                result += f"\n⚠️  错误输出:\n{error[:3000]}"

            return result
        except asyncio.TimeoutError:
            process.kill()
            return f"❌ 命令执行超时（{timeout}秒）: {command}"

    except Exception as e:
        return f"❌ 执行命令失败: {str(e)}"


async def get_system_info_tool(info_type: str) -> str:
    """获取系统信息"""
    try:
        result = f"🖥️  Windows 系统信息 - {info_type}\n\n"

        if info_type == "os" or info_type == "all":
            result += "=== 操作系统 ===\n"
            result += f"  系统: {platform.system()} {platform.release()}\n"
            result += f"  版本: {platform.version()}\n"
            result += f"  架构: {platform.machine()}\n"
            result += f"  主机名: {platform.node()}\n\n"

        if psutil:
            if info_type == "cpu" or info_type == "all":
                result += "=== CPU ===\n"
                result += f"  核心数: {psutil.cpu_count(logical=False)} 物理 / {psutil.cpu_count(logical=True)} 逻辑\n"
                result += f"  使用率: {psutil.cpu_percent(interval=1)}%\n\n"

            if info_type == "memory" or info_type == "all":
                mem = psutil.virtual_memory()
                result += "=== 内存 ===\n"
                result += f"  总内存: {mem.total / (1024**3):.2f} GB\n"
                result += f"  已使用: {mem.used / (1024**3):.2f} GB ({mem.percent}%)\n"
                result += f"  可用: {mem.available / (1024**3):.2f} GB\n\n"

            if info_type == "disk" or info_type == "all":
                result += "=== 磁盘 ===\n"
                for part in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        result += f"  {part.device} ({part.mountpoint}): {usage.percent}% 已使用, {usage.free / (1024**3):.2f} GB 可用\n"
                    except:
                        pass
                result += "\n"

            if info_type == "network" or info_type == "all":
                result += "=== 网络 ===\n"
                net_io = psutil.net_io_counters()
                result += f"  发送: {net_io.bytes_sent / (1024**2):.2f} MB\n"
                result += f"  接收: {net_io.bytes_recv / (1024**2):.2f} MB\n\n"

        return result
    except Exception as e:
        return f"❌ 获取系统信息失败: {str(e)}"


async def get_process_list_tool(filter_name: str = None, show_details: bool = True, max_results: int = 30) -> str:
    """获取进程列表"""
    try:
        if not psutil:
            return "❌ 需要安装psutil: pip install psutil"

        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if filter_name and filter_name.lower() not in proc.info['name'].lower():
                    continue
                processes.append(proc.info)
            except:
                pass

        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        processes = processes[:max_results]

        result = f"📋 进程列表（共 {len(processes)} 个）:\n"
        result += f"{'PID':<8} {'Name':<30} {'CPU%':<8} {'MEM%':<8}\n"
        result += "-" * 60 + "\n"

        for proc in processes:
            if show_details:
                result += f"{proc['pid']:<8} {proc['name']:<30} {proc['cpu_percent']:<8.2f} {proc['memory_percent']:<8.2f}\n"
            else:
                result += f"{proc['pid']:<8} {proc['name']}\n"

        return result
    except Exception as e:
        return f"❌ 获取进程列表失败: {str(e)}"


async def get_network_info_tool(detail_level: str = "basic") -> str:
    """获取网络信息"""
    try:
        import socket
        result = "🌐 网络信息:\n"

        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)

        result += f"  主机名: {hostname}\n"
        result += f"  IP地址: {ip}\n"

        if detail_level == "detailed" and psutil:
            net_io = psutil.net_io_counters()
            result += f"  发送总量: {net_io.bytes_sent / (1024**2):.2f} MB\n"
            result += f"  接收总量: {net_io.bytes_recv / (1024**2):.2f} MB\n"

        return result
    except Exception as e:
        return f"❌ 获取网络信息失败: {str(e)}"


async def ping_host_tool(host: str, count: int = 4) -> str:
    """Ping主机"""
    try:
        cmd = f"ping -n {count} {host}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return f"📤 Ping {host}:\n{result.stdout}"
    except Exception as e:
        return f"❌ Ping失败: {str(e)}"


async def get_current_time_tool(format: str = "full") -> str:
    """获取当前时间"""
    try:
        now = datetime.now()
        formats = {
            "full": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timestamp": str(int(now.timestamp()))
        }
        return f"🕐 {formats.get(format, formats['full'])}"
    except Exception as e:
        return f"❌ 获取时间失败: {str(e)}"


# ==================== 工具映射 ====================
TOOL_FUNCTIONS = {
    # 文件系统
    "list_directory": list_directory_tool,
    "read_file": read_file_tool,
    "create_file": create_file_tool,
    "write_to_file": write_to_file_tool,
    "search_files": search_files_tool,

    # Windows系统
    "execute_command": execute_command_tool,
    "get_system_info": get_system_info_tool,
    "get_process_list": get_process_list_tool,

    # 网络
    "get_network_info": get_network_info_tool,
    "ping_host": ping_host_tool,

    # 时间
    "get_current_time": get_current_time_tool,
}


# ==================== 工具调用处理 ====================
async def process_tool_calls(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    处理AI的工具调用请求

    Args:
        tool_calls: AI返回的工具调用列表

    Returns:
        List[Dict]: 工具调用结果列表
    """
    tool_results = []

    for tool_call in tool_calls:
        tool_name = tool_call["function"]["name"]
        tool_args = tool_call["function"]["arguments"]

        try:
            args = json.loads(tool_args)

            if tool_name in TOOL_FUNCTIONS:
                tool_func = TOOL_FUNCTIONS[tool_name]
                tool_result = await tool_func(**args)

                tool_results.append({
                    "role": "tool",
                    "content": tool_result,
                    "tool_call_id": tool_call["id"]
                })
            else:
                error_msg = f"❌ 工具不存在: {tool_name}"
                tool_results.append({
                    "role": "tool",
                    "content": error_msg,
                    "tool_call_id": tool_call["id"]
                })
        except Exception as e:
            error_msg = f"❌ 工具执行异常: {str(e)}"
            tool_results.append({
                "role": "tool",
                "content": error_msg,
                "tool_call_id": tool_call["id"]
            })

    return tool_results


# ==================== 导出接口 ====================
__all__ = [
    "TOOLS",
    "TOOL_FUNCTIONS",
    "process_tool_calls",
]