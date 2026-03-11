"""
测试 ripgrep 搜索工具
"""

import asyncio
from src.search_tools import search_files_by_name, search_content, count_matches
import os


async def test_search_files():
    """测试按文件名搜索"""
    print("=" * 60)
    print("测试 1: 按文件名搜索 (*.py)")
    print("=" * 60)
    result = await search_files_by_name(
        pattern="*.py",
        path=".",
        glob="*.py",
        max_results=20
    )
    print(result)
    print()


async def test_search_by_keyword():
    """测试按关键词搜索"""
    print("=" * 60)
    print("测试 2: 按关键词搜索 (config)")
    print("=" * 60)
    result = await search_files_by_name(
        pattern="config",
        path=".",
        max_results=10
    )
    print(result)
    print()


async def test_search_content():
    """测试按内容搜索"""
    print("=" * 60)
    print("测试 3: 按内容搜索 (TODO)")
    print("=" * 60)
    result = await search_content(
        pattern="TODO",
        path=".",
        file_type="py",
        ignore_case=True,
        max_results=10,
        show_context=1
    )
    print(result)
    print()


async def test_search_in_src():
    """测试在 src 目录中搜索"""
    print("=" * 60)
    print("测试 4: 在 src 目录中搜索 (*.py)")
    print("=" * 60)
    result = await search_files_by_name(
        pattern="*.py",
        path="src",
        glob="*.py",
        max_results=20
    )
    print(result)
    print()


async def test_search_md_files():
    """测试搜索 Markdown 文件"""
    print("=" * 60)
    print("测试 5: 按文件名搜索 Markdown 文件 (*.md)")
    print("=" * 60)
    result = await search_files_by_name(
        pattern="*.md",
        path=".",
        glob="*.md",
        max_results=10
    )
    print(result)
    print()


async def test_count_matches():
    """测试统计匹配"""
    print("=" * 60)
    print("测试 6: 统计匹配数量")
    print("=" * 60)
    result = await count_matches(
        pattern="TODO",
        path=".",
        file_type="py"
    )
    print(result)
    print()


async def main():
    """运行所有测试"""
    print("\n🚀 开始测试 Ripgrep 搜索工具...\n")

    # 检查 ripgrep 是否可用
    try:
        import subprocess
        result = subprocess.run(["rg", "--version"], capture_output=True, text=True)
        print(f"✅ Ripgrep 可用: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Ripgrep 不可用: {e}")
        print("请先安装 ripgrep: scoop install ripgrep (或 choco install ripgrep)")
        return

    print()

    # 运行测试
    await test_search_files()
    await test_search_by_keyword()
    await test_search_content()
    await test_search_in_src()
    await test_search_md_files()
    await test_count_matches()

    print("=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
