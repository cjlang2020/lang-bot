"""
Windows工具模块 - 保留向后兼容性
实际功能已拆分到 src/tools 目录下
"""

# 向后兼容：导入工具模块
from src.tools import (
    TOOLS,
    TOOL_FUNCTIONS,
    process_tool_calls
)

__all__ = [
    "TOOLS",
    "TOOL_FUNCTIONS",
    "process_tool_calls",
]
