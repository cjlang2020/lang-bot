"""
搜索工具模块 - 使用 ripgrep 进行高效文件搜索
支持多种搜索方式，包括内容搜索、文件名搜索、正则匹配等
"""

import os
import subprocess
import json
from typing import List, Dict, Optional
from datetime import datetime


def ripgrep_search(
    pattern: str,
    path: str = ".",
    file_type: Optional[str] = None,
    glob: Optional[str] = None,
    ignore_case: bool = False,
    max_depth: Optional[int] = None,
    hidden: bool = False,
    follow: bool = False,
    max_count: Optional[int] = None,
    context: int = 0,
) -> List[Dict]:
    """
    使用 ripgrep 搜索文件内容

    Args:
        pattern: 搜索模式（正则表达式）
        path: 搜索目录，默认当前目录
        file_type: 文件类型，如 "js", "py", "rust"
        glob: glob 模式过滤，如 "*.js"
        ignore_case: 是否忽略大小写
        max_depth: 最大搜索深度
        hidden: 是否包含隐藏文件
        follow: 是否跟随符号链接
        max_count: 每个文件最大匹配数
        context: 显示上下文行数

    Returns:
        匹配结果列表，格式为 [{"path": str, "line": int, "text": str}, ...]
    """
    # 使用 UTF-8 编码，设置环境变量
    env = os.environ.copy()
    env['LANG'] = 'en_US.UTF-8'
    env['LC_ALL'] = 'en_US.UTF-8'

    cmd = ["rg", "--json", "--with-filename", "--line-number"]

    if ignore_case:
        cmd.append("--ignore-case")

    if file_type:
        cmd.extend(["--type", file_type])

    if glob:
        cmd.extend(["--glob", glob])

    if max_depth is not None:
        cmd.extend(["--max-depth", str(max_depth)])

    if hidden:
        cmd.append("--hidden")

    if follow:
        cmd.append("--follow")

    if context > 0:
        cmd.extend(["--context", str(context)])

    if max_count is not None:
        cmd.extend(["--max-count", str(max_count)])

    cmd.append(pattern)
    cmd.append(path)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )

        matches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            if data["type"] == "match":
                for submatch in data["data"]["submatches"]:
                    matches.append({
                        "path": data["data"]["path"]["text"],
                        "line": data["data"]["line_number"],
                        "text": data["data"]["lines"]["text"],
                        "match": submatch["match"]["text"],
                        "start": submatch["start"],
                        "end": submatch["end"],
                    })

        return matches

    except subprocess.CalledProcessError as e:
        # rg 返回码 1 表示没有匹配
        if e.returncode == 1:
            return []
        raise


def ripgrep_files(
    path: str = ".",
    glob: Optional[str] = None,
    hidden: bool = False,
    max_depth: Optional[int] = None,
) -> List[str]:
    """
    使用 ripgrep 列出文件

    Args:
        path: 搜索目录
        glob: glob 模式过滤
        hidden: 是否包含隐藏文件
        max_depth: 最大搜索深度

    Returns:
        文件路径列表
    """
    env = os.environ.copy()
    env['LANG'] = 'en_US.UTF-8'
    env['LC_ALL'] = 'en_US.UTF-8'

    cmd = ["rg", "--files"]

    if hidden:
        cmd.append("--hidden")

    if glob:
        cmd.extend(["--glob", glob])

    if max_depth is not None:
        cmd.extend(["--max-depth", str(max_depth)])

    cmd.append(path)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def ripgrep_count(
    pattern: str,
    path: str = ".",
    file_type: Optional[str] = None,
    glob: Optional[str] = None,
) -> Dict[str, int]:
    """
    统计每个文件的匹配数量

    Returns:
        {"文件路径": 匹配数量}
    """
    env = os.environ.copy()
    env['LANG'] = 'en_US.UTF-8'
    env['LC_ALL'] = 'en_US.UTF-8'

    cmd = ["rg", "--count", "--with-filename"]

    if file_type:
        cmd.extend(["--type", file_type])

    if glob:
        cmd.extend(["--glob", glob])

    cmd.append(pattern)
    cmd.append(path)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )

        counts = {}
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            # 格式: filepath:count
            parts = line.rsplit(":", 1)
            if len(parts) == 2:
                filepath, count = parts
                counts[filepath] = int(count)

        return counts

    except subprocess.CalledProcessError:
        return {}


async def search_content(
    pattern: str,
    path: str = ".",
    file_type: Optional[str] = None,
    ignore_case: bool = False,
    max_results: int = 50,
    show_context: int = 0,
) -> str:
    """
    按内容搜索文件（搜索文件内部的文本）

    Args:
        pattern: 搜索的文本或正则表达式
        path: 搜索目录
        file_type: 文件类型（如 "py", "txt", "md"）
        ignore_case: 是否忽略大小写
        max_results: 最大结果数
        show_context: 显示上下文行数

    Returns:
        格式化的搜索结果
    """
    abs_path = os.path.abspath(path) if os.path.isabs(path) else os.path.join(os.getcwd(), path)

    if not os.path.exists(abs_path):
        return f"❌ 搜索目录不存在: {abs_path}"

    # 限制每个文件的最大匹配数，避免结果过多
    max_per_file = max(1, max_results // 5)

    try:
        matches = ripgrep_search(
            pattern=pattern,
            path=abs_path,
            file_type=file_type,
            ignore_case=ignore_case,
            max_count=max_per_file,
            context=show_context
        )

        if not matches:
            return f"🔍 内容搜索: {pattern}\n❌ 未找到匹配的内容（搜索范围: {abs_path}）"

        # 限制总结果数
        matches = matches[:max_results]

        # 按文件分组
        results_by_file = {}
        for match in matches:
            filepath = match["path"]
            if filepath not in results_by_file:
                results_by_file[filepath] = []
            results_by_file[filepath].append(match)

        output = f"🔍 Ripgrep 内容搜索: {pattern}\n"
        output += f"📁 搜索目录: {abs_path}\n"
        if file_type:
            output += f"📝 文件类型: {file_type}\n"
        output += f"找到 {len(matches)} 个匹配:\n"
        output += "=" * 60 + "\n\n"

        for filepath, file_matches in results_by_file.items():
            output += f"📄 {filepath}\n"
            for match in file_matches:
                line_info = f"第{match['line']}行"
                if match['text'].strip():
                    # 高亮匹配的文本（简单标记）
                    highlighted = match['text']
                    output += f"  {line_info}: {highlighted}"
                else:
                    output += f"  {line_info}: （二进制文件或空行）\n"
            output += "\n"

        if len(matches) > max_results:
            output += f"\n... 已限制为 {max_results} 个结果"

        return output

    except Exception as e:
        return f"❌ 搜索失败: {str(e)}"


async def search_files_by_name(
    pattern: str,
    path: str = ".",
    glob: Optional[str] = None,
    hidden: bool = False,
    max_depth: Optional[int] = None,
    max_results: int = 50,
) -> str:
    """
    按文件名搜索（搜索文件名称，而不是内容）

    Args:
        pattern: 搜索的文件名模式（支持通配符）
        path: 搜索目录
        glob: glob 模式（如 "*.py"）
        hidden: 是否包含隐藏文件
        max_depth: 最大搜索深度
        max_results: 最大结果数

    Returns:
        格式化的搜索结果
    """
    abs_path = os.path.abspath(path) if os.path.isabs(path) else os.path.join(os.getcwd(), path)

    if not os.path.exists(abs_path):
        return f"❌ 搜索目录不存在: {abs_path}"

    try:
        files = ripgrep_files(
            path=abs_path,
            glob=glob,
            hidden=hidden,
            max_depth=max_depth
        )

        if not files:
            return f"🔍 文件名搜索: {pattern}\n❌ 未找到匹配的文件（搜索范围: {abs_path}）"

        # 筛选包含关键字的文件名
        keyword = pattern.replace("*", "").replace("?", "")
        if keyword:
            files = [f for f in files if keyword.lower() in os.path.basename(f).lower()]

        # 限制结果数
        files = files[:max_results]

        output = f"🔍 Ripgrep 文件搜索: {pattern}\n"
        output += f"📁 搜索目录: {abs_path}\n"
        if glob:
            output += f"🔍 Glob 模式: {glob}\n"
        output += f"找到 {len(files)} 个文件:\n"
        output += "=" * 60 + "\n"

        for filepath in files:
            is_dir = os.path.isdir(filepath)
            icon = "📁" if is_dir else "📄"

            size_str = ""
            if not is_dir:
                try:
                    size = os.path.getsize(filepath)
                    if size > 1024 * 1024:
                        size_str = f" ({size / (1024*1024):.1f} MB)"
                    elif size > 1024:
                        size_str = f" ({size / 1024:.1f} KB)"
                    else:
                        size_str = f" ({size} B)"
                except:
                    pass

            output += f"  {icon} {filepath}{size_str}\n"

        if len(files) > max_results:
            output += f"\n... 已限制为 {max_results} 个结果"

        return output

    except Exception as e:
        return f"❌ 搜索失败: {str(e)}"


async def count_matches(
    pattern: str,
    path: str = ".",
    file_type: Optional[str] = None,
    glob: Optional[str] = None,
) -> str:
    """
    统计匹配数量

    Args:
        pattern: 搜索模式
        path: 搜索目录
        file_type: 文件类型
        glob: glob 模式

    Returns:
        统计结果
    """
    abs_path = os.path.abspath(path) if os.path.isabs(path) else os.path.join(os.getcwd(), path)

    try:
        counts = ripgrep_count(
            pattern=pattern,
            path=abs_path,
            file_type=file_type,
            glob=glob
        )

        total_matches = sum(counts.values())
        total_files = len(counts)

        output = f"📊 Ripgrep 统计: {pattern}\n"
        output += f"📁 搜索目录: {abs_path}\n"
        if file_type:
            output += f"📝 文件类型: {file_type}\n"
        output += "=" * 60 + "\n"
        output += f"总匹配数: {total_matches}\n"
        output += f"涉及文件数: {total_files}\n\n"

        if counts:
            output += "各文件匹配数:\n"
            for filepath, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]:
                output += f"  {filepath}: {count} 个匹配\n"

        return output

    except Exception as e:
        return f"❌ 统计失败: {str(e)}"
