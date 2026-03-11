"""
网络工具
- 获取网络信息
- Ping主机
"""

import socket
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None


TOOL_DEFINITIONS = [
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
]


async def get_network_info_tool(detail_level: str = "basic") -> str:
    """获取网络信息"""
    try:
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
        import subprocess
        cmd = f"ping -n {count} {host}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return f"📤 Ping {host}:\n{result.stdout}"
    except Exception as e:
        return f"❌ Ping失败: {str(e)}"


# 工具函数映射
TOOL_FUNCTIONS = {
    "get_network_info": get_network_info_tool,
    "ping_host": ping_host_tool,
}
