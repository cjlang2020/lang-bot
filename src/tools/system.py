"""
系统工具 - Windows系统操作
- 执行命令
- 获取系统信息
- 获取进程列表
"""

import os
import asyncio
import subprocess
import platform
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None


TOOL_DEFINITIONS = [
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
]


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


# 工具函数映射
TOOL_FUNCTIONS = {
    "execute_command": execute_command_tool,
    "get_system_info": get_system_info_tool,
    "get_process_list": get_process_list_tool,
}
