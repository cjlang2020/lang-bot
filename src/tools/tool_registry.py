"""
工具注册表
聚合所有工具定义和函数映射
"""

import json
from typing import Dict, Any, List
from botpy import logging

_log = logging.get_logger()

# 导入所有工具模块
from .file_system import TOOL_DEFINITIONS as FILE_SYSTEM_TOOLS, TOOL_FUNCTIONS as FILE_SYSTEM_FUNCTIONS
from .search import TOOL_DEFINITIONS as SEARCH_TOOLS, TOOL_FUNCTIONS as SEARCH_FUNCTIONS
from .system import TOOL_DEFINITIONS as SYSTEM_TOOLS, TOOL_FUNCTIONS as SYSTEM_FUNCTIONS
from .network import TOOL_DEFINITIONS as NETWORK_TOOLS, TOOL_FUNCTIONS as NETWORK_FUNCTIONS
from .time import TOOL_DEFINITIONS as TIME_TOOLS, TOOL_FUNCTIONS as TIME_FUNCTIONS


# 聚合所有工具定义
TOOLS = (
    FILE_SYSTEM_TOOLS +
    SEARCH_TOOLS +
    SYSTEM_TOOLS +
    NETWORK_TOOLS +
    TIME_TOOLS
)

# 聚合所有工具函数映射
TOOL_FUNCTIONS = {
    **FILE_SYSTEM_FUNCTIONS,
    **SEARCH_FUNCTIONS,
    **SYSTEM_FUNCTIONS,
    **NETWORK_FUNCTIONS,
    **TIME_FUNCTIONS,
}


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
