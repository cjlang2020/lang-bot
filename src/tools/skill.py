"""
Skill 工具模块
提供 AI 调用 skill 的接口
"""

from typing import Dict, Callable, Awaitable, Any, Optional
from ..skills.skill_service import get_skill_service, discover_skills


# 初始化时发现所有 skills
_skill_service = get_skill_service()
discover_skills()


async def load_skill(name: Optional[str] = None) -> str:
    """
    加载指定 skill 的完整内容，或列出所有可用的 skills
    
    Args:
        name: skill 名称，不传则列出所有可用的 skills
        
    Returns:
        skill 内容或技能列表
    """
    # 如果没有传入 name，返回所有可用的 skills 列表
    if name is None or name == "":
        skills = _skill_service.list()
        if not skills:
            return "当前没有可用的 skills。"
        
        result = "📋 **可用的 Skills 列表：**\n\n"
        for skill in skills:
            result += f"**{skill.name}**: {skill.description[:150]}{'...' if len(skill.description) > 150 else ''}\n\n"
        result += "\n使用 skill(name=\"技能名\") 加载具体的技能指南。"
        return result
    
    skill = _skill_service.get(name)
    
    if not skill:
        available = _skill_service.list_names()
        if available:
            return f"❌ Skill '{name}' 不存在。\n\n可用的 skills: {', '.join(available)}\n\n使用 skill() 查看所有可用技能。"
        else:
            return f"❌ Skill '{name}' 不存在。当前没有可用的 skills。"
    
    # 返回格式化的 skill 内容
    return f"""<skill_content name="{skill.name}">
{skill.content}
</skill_content>"""


def get_skill_tool_definition() -> Dict[str, Any]:
    """
    动态生成 skill 工具定义
    描述中包含所有可用的 skill 列表
    
    Returns:
        工具定义字典
    """
    # 获取所有 skills
    skills = _skill_service.list()
    
    # 构建描述
    if not skills:
        description = """加载专业技能指南。当前没有可用的 skills。

不传参数时返回所有可用技能列表。"""
    else:
        skill_list = []
        for skill in skills:
            desc = skill.description[:100] + "..." if len(skill.description) > 100 else skill.description
            skill_list.append(f"  - **{skill.name}**: {desc}")
        
        description = f"""加载专业技能指南。当用户问"有哪些skill"或需要特定领域指导时使用此工具。

**不传参数时返回所有可用技能列表。**

当前可用的 skills:
{chr(10).join(skill_list)}

使用方式:
- skill() - 列出所有可用技能
- skill(name="pdf") - 加载 PDF 处理指南
- skill(name="xlsx") - 加载 Excel 处理指南"""

    return {
        "type": "function",
        "function": {
            "name": "skill",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "要加载的 skill 名称（可选）。不传则返回所有可用技能列表。例如: pdf, xlsx, pptx"
                    }
                },
                "required": []  # name 不是必填
            }
        }
    }


# 工具定义列表
TOOL_DEFINITIONS = [get_skill_tool_definition()]

# 工具函数映射
TOOL_FUNCTIONS: Dict[str, Callable[..., Awaitable[str]]] = {
    "skill": load_skill,
}


def refresh_skill_tool():
    """
    刷新 skill 工具定义
    当添加新的 skill 后调用此函数更新工具描述
    """
    global TOOL_DEFINITIONS
    TOOL_DEFINITIONS = [get_skill_tool_definition()]