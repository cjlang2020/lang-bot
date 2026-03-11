"""
时间工具
- 获取当前时间
"""

from datetime import datetime


TOOL_DEFINITIONS = [
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


# 工具函数映射
TOOL_FUNCTIONS = {
    "get_current_time": get_current_time_tool,
}
