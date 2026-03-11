# OpenCode Skill 加载和使用原理分析

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Skill Discovery                          │
│  扫描多个路径 → 解析 SKILL.md → 内存缓存                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    SkillTool.define()                       │
│  动态生成工具描述，包含所有可用 skill 列表                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    LLM 调用 skill tool                       │
│  按需加载 → 注入 <skill_content> 到上下文                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Skill 文件格式

```markdown
---
name: my-skill
description: 描述何时使用此 skill（会在工具描述中展示）
---

# Skill 详细指令

具体的指令内容、示例、最佳实践等...
```

---

## 发现路径

优先级从低到高：

| 路径                           | 作用域   |
| ------------------------------ | -------- |
| `~/.claude/skills/**/SKILL.md` | 全局     |
| `~/.agents/skills/**/SKILL.md` | 全局     |
| `.opencode/skill/**/SKILL.md`  | 项目     |
| `.opencode/skills/**/SKILL.md` | 项目     |
| `.claude/skills/**/SKILL.md`   | 项目     |
| `.agents/skills/**/SKILL.md`   | 项目     |
| 配置文件 `skills.paths`        | 自定义   |
| 配置文件 `skills.urls`         | 远程下载 |

---

## 核心代码逻辑

### Skill 发现 (skill.ts:52-176)

扫描所有路径，解析 SKILL.md，构建 skill 缓存。

### Skill 工具定义 (tool/skill.ts:10-123)

- `init()` 时获取所有 skills，生成包含 skill 列表的工具描述
- `execute()` 时返回 `<skill_content>` 块

---

## 自己实现 Skill 系统的方案

### 核心原理

1. **声明式定义**：skill 是 Markdown + YAML frontmatter，便于编写和维护
2. **延迟加载**：只在需要时加载 skill 内容到上下文，节省 token
3. **动态工具描述**：工具描述包含所有可用 skill，帮助 LLM 发现合适的 skill

---

### 实现代码

```typescript
// 1. 定义 Skill 结构
interface Skill {
  name: string;
  description: string;
  location: string; // 文件路径
  content: string; // Markdown 内容
}

// 2. Skill 发现服务
class SkillService {
  private skills: Map<string, Skill> = new Map();

  // 扫描目录发现 skills
  async scan(baseDir: string) {
    const pattern = "**/SKILL.md";
    const files = await glob(pattern, { cwd: baseDir });

    for (const file of files) {
      const content = await fs.readFile(file, "utf-8");
      const { data, content: body } = parseFrontmatter(content);

      if (data.name && data.description) {
        this.skills.set(data.name, {
          name: data.name,
          description: data.description,
          location: file,
          content: body,
        });
      }
    }
  }

  get(name: string) {
    return this.skills.get(name);
  }
  list() {
    return Array.from(this.skills.values());
  }
}

// 3. 动态生成工具定义
async function createSkillTool(skillService: SkillService) {
  const skills = skillService.list();

  return {
    name: "skill",
    description: generateDescription(skills), // 包含所有 skill 列表
    parameters: { name: { type: "string" } },
    execute: async (params: { name: string }) => {
      const skill = skillService.get(params.name);
      if (!skill) throw new Error(`Skill not found: ${params.name}`);

      return {
        output: `<skill_content name="${skill.name}">
${skill.content}
</skill_content>`,
      };
    },
  };
}

function generateDescription(skills: Skill[]): string {
  const skillList = skills
    .map((s) => `  - ${s.name}: ${s.description}`)
    .join("\n");

  return `Load a specialized skill. Available skills:
${skillList}

Use this tool when you need domain-specific instructions.`;
}
```

---

### 使用案例

假设你有一个代码助手智能体：

```
项目结构：
your-project/
├── .skills/
│   ├── code-review/
│   │   └── SKILL.md
│   └── testing/
│       └── SKILL.md
```

**SKILL.md 示例**：

```markdown
---
name: code-review
description: Use when reviewing pull requests or code changes
---

# Code Review Guidelines

1. Check for security vulnerabilities
2. Verify error handling
3. Look for performance issues
   ...
```

**工作流程**：

1. 启动时扫描 `.skills/` 目录，缓存所有 skill
2. 生成工具描述时，列出所有可用 skill
3. 用户问"帮我 review 这个 PR"
4. LLM 识别匹配，调用 `skill` 工具加载 `code-review`
5. skill 内容注入上下文，LLM 按照指令执行 review

---

### 关键设计点

| 要点             | 说明                                         |
| ---------------- | -------------------------------------------- |
| Frontmatter 解析 | 使用 gray-matter 或类似库解析 YAML           |
| 多路径支持       | 支持全局、项目、远程三种来源                 |
| 权限控制         | 可根据 agent 权限过滤可用 skill              |
| 文件引用         | skill 可引用目录下的其他文件（脚本、模板等） |
| 远程 skill       | 通过 index.json 发现和缓存远程 skill         |

---

## 配置示例

在 `opencode.json` 中配置：

```json
{
  "skills": {
    "paths": ["~/my-skills", "./custom-skills"],
    "urls": ["https://example.com/.well-known/skills/"]
  }
}
```

---

## 总结

OpenCode 的 skill 系统核心思想：

1. **目录即配置**：放在约定目录下的 SKILL.md 自动被发现
2. **描述驱动发现**：description 字段帮助 LLM 自动选择合适的 skill
3. **按需注入**：只有调用时才加载完整内容，避免上下文膨胀
4. **可扩展**：支持本地、远程、自定义路径多种来源
