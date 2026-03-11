"""
Skill 服务模块
实现类似 OpenCode 的 Skill 系统：
1. 目录扫描发现 SKILL.md 文件
2. 解析 YAML frontmatter (name, description)
3. 缓存 skill 元数据
4. 按需加载 skill 内容
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Skill:
    """Skill 数据结构"""
    name: str
    description: str
    location: str  # 文件路径
    content: str = ""  # 完整内容（延迟加载）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 其他元数据


class SkillService:
    """
    Skill 发现和管理服务
    
    核心功能：
    - 扫描多个路径发现 SKILL.md 文件
    - 解析 YAML frontmatter
    - 缓存 skill 元数据
    - 按需加载完整内容
    """
    
    # 默认扫描路径（优先级从低到高）
    DEFAULT_SCAN_PATHS = [
        "skills",  # 项目根目录下的 skills 文件夹
    ]
    
    def __init__(self, additional_paths: Optional[List[str]] = None):
        """
        初始化 Skill 服务
        
        Args:
            additional_paths: 额外的扫描路径
        """
        self._skills: Dict[str, Skill] = {}
        self._scan_paths = list(self.DEFAULT_SCAN_PATHS)
        
        if additional_paths:
            self._scan_paths.extend(additional_paths)
    
    def scan(self, base_dir: Optional[str] = None) -> int:
        """
        扫描所有路径，发现并缓存 skills
        
        Args:
            base_dir: 基础目录，用于解析相对路径
            
        Returns:
            int: 发现的 skill 数量
        """
        if base_dir is None:
            # 获取项目根目录（src 的父目录）
            base_dir = str(Path(__file__).parent.parent.parent)
        
        discovered_count = 0
        
        for scan_path in self._scan_paths:
            # 解析路径
            if not os.path.isabs(scan_path):
                full_path = os.path.join(base_dir, scan_path)
            else:
                full_path = scan_path
            
            if not os.path.exists(full_path):
                continue
            
            # 扫描该路径下的所有 SKILL.md 文件
            count = self._scan_directory(full_path)
            discovered_count += count
        
        return discovered_count
    
    def _scan_directory(self, directory: str) -> int:
        """
        扫描单个目录，发现 SKILL.md 文件
        
        Args:
            directory: 要扫描的目录
            
        Returns:
            int: 发现的 skill 数量
        """
        discovered_count = 0
        
        for root, dirs, files in os.walk(directory):
            if "SKILL.md" in files:
                skill_file = os.path.join(root, "SKILL.md")
                skill = self._parse_skill_file(skill_file)
                
                if skill:
                    self._skills[skill.name] = skill
                    discovered_count += 1
        
        return discovered_count
    
    def _parse_skill_file(self, file_path: str) -> Optional[Skill]:
        """
        解析 SKILL.md 文件
        
        格式：
        ---
        name: skill-name
        description: skill description
        ---
        
        # Skill Content
        ...
        
        Args:
            file_path: SKILL.md 文件路径
            
        Returns:
            Skill 对象，解析失败返回 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 YAML frontmatter
            frontmatter, body = self._parse_frontmatter(content)
            
            if not frontmatter:
                return None
            
            name = frontmatter.get("name", "")
            description = frontmatter.get("description", "")
            
            if not name:
                return None
            
            # 提取其他元数据
            metadata = {k: v for k, v in frontmatter.items() 
                       if k not in ["name", "description"]}
            
            return Skill(
                name=name,
                description=description,
                location=file_path,
                content=body,  # 存储 body 内容
                metadata=metadata
            )
            
        except Exception as e:
            print(f"[SkillService] 解析 SKILL.md 失败: {file_path}, 错误: {e}")
            return None
    
    def _parse_frontmatter(self, content: str) -> tuple:
        """
        解析 YAML frontmatter
        
        Args:
            content: 文件内容
            
        Returns:
            (frontmatter_dict, body_content)
        """
        # 匹配 --- 包围的 frontmatter
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)
        
        if not match:
            return {}, content
        
        frontmatter_str = match.group(1)
        body = match.group(2)
        
        # 简单解析 YAML（不引入依赖）
        frontmatter = {}
        for line in frontmatter_str.split('\n'):
            line = line.strip()
            if not line or ':' not in line:
                continue
            
            # 处理多行描述（以引号开始的）
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()
            
            # 去除引号
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            
            frontmatter[key] = value
        
        return frontmatter, body
    
    def get(self, name: str) -> Optional[Skill]:
        """
        获取指定名称的 skill
        
        Args:
            name: skill 名称
            
        Returns:
            Skill 对象，不存在返回 None
        """
        return self._skills.get(name)
    
    def list(self) -> List[Skill]:
        """
        获取所有已发现的 skills
        
        Returns:
            Skill 列表
        """
        return list(self._skills.values())
    
    def list_names(self) -> List[str]:
        """
        获取所有 skill 名称
        
        Returns:
            skill 名称列表
        """
        return list(self._skills.keys())
    
    def get_tool_description(self) -> str:
        """
        生成 skill 工具的描述文本
        包含所有可用 skill 的列表，帮助 LLM 发现合适的 skill
        
        Returns:
            工具描述文本
        """
        if not self._skills:
            return "Load a specialized skill. No skills are currently available."
        
        skill_list = []
        for skill in self._skills.values():
            # 截断过长的描述
            desc = skill.description
            if len(desc) > 200:
                desc = desc[:200] + "..."
            skill_list.append(f"  - {skill.name}: {desc}")
        
        return f"""Load a specialized skill or get detailed instructions for a specific task.

Available skills:
{chr(10).join(skill_list)}

Usage:
- Use this tool when you need domain-specific instructions or guidance
- Pass the skill name to load its full content
- The skill content will be injected into your context for reference

Example: skill(name="pdf") to load PDF processing instructions"""


# 全局单例
_skill_service: Optional[SkillService] = None


def get_skill_service() -> SkillService:
    """
    获取全局 Skill 服务实例
    
    Returns:
        SkillService 实例
    """
    global _skill_service
    
    if _skill_service is None:
        _skill_service = SkillService()
    
    return _skill_service


def discover_skills() -> int:
    """
    发现并缓存所有 skills
    
    Returns:
        发现的 skill 数量
    """
    service = get_skill_service()
    return service.scan()


def get_skill(name: str) -> Optional[Skill]:
    """
    获取指定名称的 skill
    
    Args:
        name: skill 名称
        
    Returns:
        Skill 对象
    """
    return get_skill_service().get(name)


def list_skills() -> List[Skill]:
    """
    获取所有 skills
    
    Returns:
        Skill 列表
    """
    return get_skill_service().list()