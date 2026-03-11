# -*- coding: utf-8 -*-
"""
测试 Skill 系统功能
验证 skill 发现、加载是否正常工作
"""

import asyncio
import sys
import os

# 设置控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.skills.skill_service import discover_skills, get_skill, list_skills, get_skill_service
from src.tools.skill import load_skill, get_skill_tool_definition


def test_skill_discovery():
    """测试 skill 发现功能"""
    print("\n" + "="*60)
    print("测试 1: Skill 发现")
    print("="*60)
    
    # 发现所有 skills
    count = discover_skills()
    print(f"发现 {count} 个 skills")
    
    # 列出所有 skill 名称
    skills = list_skills()
    print("\n已发现的 skills:")
    for skill in skills:
        print(f"  - {skill.name}")
        print(f"    描述: {skill.description[:100]}...")
        print(f"    位置: {skill.location}")
    
    return count > 0


def test_skill_loading():
    """测试 skill 加载功能"""
    print("\n" + "="*60)
    print("测试 2: Skill 加载")
    print("="*60)
    
    # 测试加载 pdf skill
    skill = get_skill("pdf")
    if skill:
        print(f"成功加载 skill: {skill.name}")
        print(f"内容长度: {len(skill.content)} 字符")
        print(f"内容预览:\n{skill.content[:500]}...")
        return True
    else:
        print("加载 pdf skill 失败")
        return False


async def test_skill_tool():
    """测试 skill 工具"""
    print("\n" + "="*60)
    print("测试 3: Skill 工具")
    print("="*60)
    
    # 测试工具定义
    tool_def = get_skill_tool_definition()
    print(f"工具名称: {tool_def['function']['name']}")
    print(f"工具描述:\n{tool_def['function']['description'][:500]}...")
    
    # 测试不传参数（列出所有 skills）
    result = await load_skill()
    print(f"\n调用 skill() 列出所有技能:\n{result}")
    
    # 测试加载 skill
    result = await load_skill("pdf")
    print(f"\n加载 pdf skill 结果:\n{result[:500]}...")
    
    # 测试加载不存在的 skill
    result = await load_skill("not_exist")
    print(f"\n加载不存在的 skill 结果:\n{result}")
    
    return True


def test_skill_tool_description():
    """测试 skill 工具描述生成"""
    print("\n" + "="*60)
    print("测试 4: Skill 工具描述")
    print("="*60)
    
    service = get_skill_service()
    description = service.get_tool_description()
    print(description)
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Skill 系统测试")
    print("="*60)
    
    results = []
    
    # 测试 1: Skill 发现
    results.append(("Skill 发现", test_skill_discovery()))
    
    # 测试 2: Skill 加载
    results.append(("Skill 加载", test_skill_loading()))
    
    # 测试 3: Skill 工具
    results.append(("Skill 工具", asyncio.run(test_skill_tool())))
    
    # 测试 4: Skill 工具描述
    results.append(("Skill 工具描述", test_skill_tool_description()))
    
    # 打印结果汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("所有测试通过！Skill 系统工作正常。")
    else:
        print("部分测试失败，请检查。")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)