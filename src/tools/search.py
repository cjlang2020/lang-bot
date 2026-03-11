"""
搜索工具 - 使用 ripgrep 进行高效文件搜索
支持按文件名搜索和按内容搜索
"""

import os
from typing import Optional
from src.search_tools import search_files_by_name, search_content

# Ripgrep 模块可用性检查
try:
    from src.search_tools import search_files_by_name, search_content
    RIPGREP_AVAILABLE = True
except ImportError:
    RIPGREP_AVAILABLE = False


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "使用 Ripgrep 高效搜索文件（按文件名搜索，支持通配符和正则）",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "搜索关键词（支持通配符和正则）：*.pdf=所有PDF文件；*.py=所有Python文件；关键词=搜索包含该词的文件名；也可以使用正则表达式"},
                    "directory": {"type": "string", "description": "限制搜索的目录路径（可选，不填则当前目录）"},
                    "max_results": {"type": "integer", "description": "最大结果数", "default": 50}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_content",
            "description": "使用 Ripgrep 按内容搜索文件（搜索文件内部的文本）",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "搜索的文本或正则表达式，用于匹配文件内容"},
                    "directory": {"type": "string", "description": "限制搜索的目录路径（可选，不填则当前目录）"},
                    "file_type": {"type": "string", "description": "文件类型（如 'py', 'txt', 'md'），可选"},
                    "ignore_case": {"type": "boolean", "description": "是否忽略大小写", "default": False},
                    "max_results": {"type": "integer", "description": "最大结果数", "default": 50},
                    "show_context": {"type": "integer", "description": "显示上下文行数", "default": 0}
                },
                "required": ["pattern"]
            }
        }
    },
]


async def search_files_tool(pattern: str, directory: str = None, max_results: int = 50) -> str:
    """
    使用 Ripgrep 高效搜索文件（按文件名搜索）
    """
    try:
        if RIPGREP_AVAILABLE:
            search_dir = directory if directory else "."
            return await search_files_by_name(
                pattern=pattern,
                path=search_dir,
                glob=pattern if ('*' in pattern or '?' in pattern) else None,
                hidden=False,
                max_depth=None,
                max_results=max_results
            )
        else:
            return await _search_files_fallback(pattern, directory, max_results)
    except Exception as e:
        return f"❌ 搜索失败: {str(e)}"


async def _search_files_fallback(pattern: str, directory: str = None, max_results: int = 50) -> str:
    """递归搜索的回退方案（当Ripgrep不可用时）"""
    import fnmatch
    from concurrent.futures import ThreadPoolExecutor
    import asyncio

    def _do_search():
        search_dir = directory if directory else "D:\\"
        search_dir = os.path.abspath(search_dir)

        if not os.path.exists(search_dir):
            return f"❌ 目录不存在: {search_dir}"

        results = []
        pattern_lower = pattern.lower()

        # 支持通配符
        if '*' in pattern or '?' in pattern:
            for root, dirs, files in os.walk(search_dir):
                for name in files:
                    if fnmatch.fnmatch(name.lower(), pattern_lower):
                        full_path = os.path.join(root, name)
                        results.append(full_path)
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break
        else:
            # 精确或部分匹配
            for root, dirs, files in os.walk(search_dir):
                for name in files:
                    if pattern_lower in name.lower():
                        full_path = os.path.join(root, name)
                        results.append(full_path)
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break

        if not results:
            return f"🔍 递归搜索: {pattern}\n❌ 未找到匹配的文件（搜索范围: {search_dir}）"

        output = f"🔍 递归搜索: {pattern}\n"
        output += f"📁 搜索目录: {search_dir}\n"
        output += f"找到 {len(results)} 个结果:\n"
        output += "=" * 60 + "\n"

        for p in results:
            is_dir = os.path.isdir(p)
            icon = "📁" if is_dir else "📄"

            size_str = ""
            if not is_dir:
                try:
                    size = os.path.getsize(p)
                    if size > 1024 * 1024:
                        size_str = f" ({size / (1024*1024):.1f} MB)"
                    elif size > 1024:
                        size_str = f" ({size / 1024:.1f} KB)"
                except:
                    pass

            output += f"  {icon} {p}{size_str}\n"

        return output

    # 使用线程池执行耗时的文件搜索
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = await loop.run_in_executor(executor, _do_search)
        return result


async def search_content_tool(
    pattern: str,
    directory: str = None,
    file_type: str = None,
    ignore_case: bool = False,
    max_results: int = 50,
    show_context: int = 0
) -> str:
    """
    按内容搜索文件（搜索文件内部的文本）
    """
    try:
        if RIPGREP_AVAILABLE:
            search_dir = directory if directory else "."
            return await search_content(
                pattern=pattern,
                path=search_dir,
                file_type=file_type,
                ignore_case=ignore_case,
                max_results=max_results,
                show_context=show_context
            )
        else:
            return "❌ Ripgrep 未安装或不可用"
    except Exception as e:
        return f"❌ 按内容搜索失败: {str(e)}"


# 工具函数映射
TOOL_FUNCTIONS = {
    "search_files": search_files_tool,
    "search_content": search_content_tool,
}
