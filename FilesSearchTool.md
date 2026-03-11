# Python 中使用 Ripgrep 搜索工具

## 概述

ripgrep (rg) 是一个极速的命令行搜索工具，用 Rust 编写。在 Python 中有 4 种主要使用方式。

## 方式一：subprocess 直接调用

最简单直接的方式，通过 Python 的 subprocess 模块调用 ripgrep 命令。

### 基础封装函数

```python
import subprocess
import json
from typing import List, Dict, Optional

def ripgrep_search(
    pattern: str,
    path: str = ".",
    file_type: Optional[str] = None,
    glob: Optional[str] = None,
    ignore_case: bool = False,
) -> List[Dict]:
    """
    使用 ripgrep 搜索文件内容

    Returns:
        [{"path": str, "line": int, "text": str, "match": str}, ...]
    """
    cmd = ["rg", "--json", "--with-filename", "--line-number"]

    if ignore_case:
        cmd.append("--ignore-case")
    if file_type:
        cmd.extend(["--type", file_type])
    if glob:
        cmd.extend(["--glob", glob])

    cmd.extend([pattern, path])

    result = subprocess.run(cmd, capture_output=True, text=True)

    matches = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        data = json.loads(line)
        if data["type"] == "match":
            match_data = data["data"]
            matches.append({
                "path": match_data["path"]["text"],
                "line": match_data["line_number"],
                "text": match_data["lines"]["text"],
            })

    return matches

# 使用
matches = ripgrep_search("TODO", path="./src", file_type="py")
```

### 完整封装类

```python
import subprocess
import json
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class RipgrepMatch:
    path: str
    line_number: int
    text: str
    matched_text: str

class Ripgrep:
    def __init__(self, rg_path: str = "rg"):
        self.rg_path = rg_path

    def search(
        self,
        pattern: str,
        path: str = ".",
        file_type: Optional[str] = None,
        glob: Optional[str] = None,
        ignore_case: bool = False,
    ) -> List[RipgrepMatch]:
        """搜索文件内容"""
        cmd = [self.rg_path, "--json", "--with-filename", "--line-number"]

        if ignore_case:
            cmd.append("--ignore-case")
        if file_type:
            cmd.extend(["--type", file_type])
        if glob:
            cmd.extend(["--glob", glob])

        cmd.extend([pattern, path])

        result = subprocess.run(cmd, capture_output=True, text=True)

        matches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            if data["type"] == "match":
                match_data = data["data"]
                for submatch in match_data["submatches"]:
                    matches.append(RipgrepMatch(
                        path=match_data["path"]["text"],
                        line_number=match_data["line_number"],
                        text=match_data["lines"]["text"].rstrip(),
                        matched_text=submatch["match"]["text"],
                    ))

        return matches

    def files(self, path: str = ".", glob: Optional[str] = None) -> List[str]:
        """列出文件"""
        cmd = [self.rg_path, "--files"]
        if glob:
            cmd.extend(["--glob", glob])
        cmd.append(path)

        result = subprocess.run(cmd, capture_output=True, text=True)
        return [f for f in result.stdout.strip().split("\n") if f]

    def count(self, pattern: str, path: str = ".") -> int:
        """统计匹配数"""
        cmd = [self.rg_path, "--count-matches", pattern, path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return sum(int(line.split(":")[-1]) for line in result.stdout.strip().split("\n") if line)

# 使用
rg = Ripgrep()
matches = rg.search("TODO", path="./src", file_type="py")
files = rg.files(path=".", glob="*.py")
total = rg.count("def", path=".", file_type="py")
```

## 方式二：ripgrepy 库

第三方 Python 库，提供更友好的 API。

### 安装

```bash
pip install ripgrepy
```

### 使用

```python
from ripgrepy import Ripgrepy

# 基本搜索
results = Ripgrepy(".", "TODO").type("py").run()

# 忽略大小写
results = Ripgrepy(".", "pattern").i().run()

# 指定文件类型
results = Ripgrepy(".", "function").type("js").run()

# 使用 glob
results = Ripgrepy(".", "pattern").glob("*.py").run()

# 显示上下文
results = Ripgrepy(".", "error").context(3).run()

# 只显示文件名
files = Ripgrepy(".", "pattern").files_with_matches().run()

# 统计数量
count = Ripgrepy(".", "pattern").count().run()
```

## 方式三：异步调用

适合大量并发搜索，性能最优。

```python
import asyncio
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor

class AsyncRipgrep:
    def __init__(self, rg_path: str = "rg", max_workers: int = 4):
        self.rg_path = rg_path
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def search(self, pattern: str, path: str = ".", **kwargs) -> list:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_search,
            pattern,
            path,
            kwargs
        )

    def _sync_search(self, pattern: str, path: str, options: dict) -> list:
        cmd = [self.rg_path, "--json"]
        for key, value in options.items():
            if value is True:
                cmd.append(f"--{key.replace('_', '-')}")
            elif value is not None and value is not False:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])
        cmd.extend([pattern, path])

        result = subprocess.run(cmd, capture_output=True, text=True)
        matches = []
        for line in result.stdout.strip().split("\n"):
            if line:
                data = json.loads(line)
                if data["type"] == "match":
                    matches.append(data)
        return matches

    async def search_multiple(self, patterns: list, path: str = ".") -> dict:
        """并行搜索多个模式"""
        tasks = [self.search(p, path) for p in patterns]
        results = await asyncio.gather(*tasks)
        return dict(zip(patterns, results))

# 使用
async def main():
    rg = AsyncRipgrep()

    # 单次搜索
    results = await rg.search("TODO", path="./src", type="py")

    # 并行搜索
    patterns = ["TODO", "FIXME", "HACK"]
    results = await rg.search_multiple(patterns, path="./src")

asyncio.run(main())
```

## 方式四：直接解析 JSON

手动解析 ripgrep 的 JSON 输出，最灵活。

```python
import subprocess
import json
from typing import Iterator, Dict, Any

def ripgrep_json(pattern: str, path: str = ".", **options) -> Iterator[Dict[str, Any]]:
    """
    获取 ripgrep JSON 输出并解析

    Yields:
        JSON 对象，类型可能是: begin, match, end, summary
    """
    cmd = ["rg", "--json"]

    for key, value in options.items():
        if value is True:
            cmd.append(f"--{key.replace('_', '-')}")
        elif value is not None and value is not False:
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    cmd.extend([pattern, path])

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for line in process.stdout:
        if line.strip():
            yield json.loads(line)

    process.wait()

# 使用
for item in ripgrep_json("def", path=".", type="py"):
    if item["type"] == "match":
        data = item["data"]
        print(f"{data['path']['text']}:{data['line_number']}")
        print(f"  {data['lines']['text'].strip()}")
```

## 实用示例

### 1. 搜索并高亮

```python
from termcolor import colored
import subprocess
import json

def search_highlight(pattern: str, path: str = "."):
    cmd = ["rg", "--json", pattern, path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue

        data = json.loads(line)
        if data["type"] != "match":
            continue

        match_data = data["data"]
        filepath = colored(match_data["path"]["text"], "green")
        line_num = colored(str(match_data["line_number"]), "yellow")
        text = match_data["lines"]["text"].strip()

        # 高亮匹配部分
        for submatch in reversed(match_data["submatches"]):
            start, end = submatch["start"], submatch["end"]
            text = text[:start] + colored(text[start:end], "red", attrs=["bold"]) + text[end:]

        print(f"{filepath}:{line_num}: {text}")

search_highlight("import", path="./src")
```

### 2. 生成报告

```python
import subprocess
import json
from collections import defaultdict

def generate_report(pattern: str, path: str = "."):
    cmd = ["rg", "--json", pattern, path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    matches_by_file = defaultdict(list)

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        data = json.loads(line)
        if data["type"] == "match":
            match_data = data["data"]
            filepath = match_data["path"]["text"]
            matches_by_file[filepath].append({
                "line": match_data["line_number"],
                "text": match_data["lines"]["text"].strip(),
            })

    # 生成 Markdown 报告
    report = [f"# 搜索报告: `{pattern}`", ""]
    report.append(f"总文件数: {len(matches_by_file)}")
    report.append(f"总匹配数: {sum(len(m) for m in matches_by_file.values())}")
    report.append("")

    for filepath, matches in sorted(matches_by_file.items()):
        report.append(f"## {filepath} ({len(matches)} 个匹配)")
        for m in matches:
            report.append(f"- 行 {m['line']}: `{m['text']}`")
        report.append("")

    return "\n".join(report)

# 使用
report = generate_report("TODO", path="./src")
print(report)
```

### 3. 导出 CSV

```python
import subprocess
import json
import csv

def search_to_csv(pattern: str, output_file: str, path: str = "."):
    cmd = ["rg", "--json", pattern, path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['文件路径', '行号', '匹配文本', '整行内容'])

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            if data["type"] == "match":
                match_data = data["data"]
                for submatch in match_data["submatches"]:
                    writer.writerow([
                        match_data["path"]["text"],
                        match_data["line_number"],
                        submatch["match"]["text"],
                        match_data["lines"]["text"].strip(),
                    ])

# 使用
search_to_csv("function", "functions.csv", path="./src")
```

### 4. 代码统计工具

```python
from dataclasses import dataclass
from typing import List
import subprocess
import json

@dataclass
class CodeStats:
    total_functions: int
    total_classes: int
    total_imports: int
    total_files: int

class CodeAnalyzer:
    def __init__(self, rg_path: str = "rg"):
        self.rg_path = rg_path

    def _count(self, pattern: str, path: str, **options) -> int:
        cmd = [self.rg_path, "--count-matches"]
        for key, value in options.items():
            if value:
                cmd.extend([f"--{key}", str(value) if not isinstance(value, bool) else ""])
        cmd.extend([pattern, path])

        result = subprocess.run(cmd, capture_output=True, text=True)
        return sum(int(line.split(":")[-1]) for line in result.stdout.strip().split("\n") if line)

    def _list_files(self, path: str, **options) -> List[str]:
        cmd = [self.rg_path, "--files"]
        for key, value in options.items():
            if value:
                cmd.extend([f"--{key}", str(value) if not isinstance(value, bool) else ""])
        cmd.append(path)

        result = subprocess.run(cmd, capture_output=True, text=True)
        return [f for f in result.stdout.strip().split("\n") if f]

    def analyze_python(self, path: str = ".") -> CodeStats:
        return CodeStats(
            total_functions=self._count(r"def\s+\w+", path, type="py"),
            total_classes=self._count(r"class\s+\w+", path, type="py"),
            total_imports=self._count(r"import\s+", path, type="py"),
            total_files=len(self._list_files(path, glob="*.py")),
        )

    def analyze_javascript(self, path: str = ".") -> CodeStats:
        return CodeStats(
            total_functions=self._count(r"function\s+\w+", path, glob="*.js"),
            total_classes=self._count(r"class\s+\w+", path, glob="*.{js,ts}"),
            total_imports=self._count(r"import\s+", path, glob="*.{js,ts}"),
            total_files=len(self._list_files(path, glob="*.{js,ts}")),
        )

# 使用
analyzer = CodeAnalyzer()
stats = analyzer.analyze_python("./src")
print(f"函数: {stats.total_functions}, 类: {stats.total_classes}, 文件: {stats.total_files}")
```

## 性能优化建议

1. **使用流式处理** - 避免一次性加载所有结果
2. **限制搜索范围** - 使用 `max_depth`, `type`, `glob` 参数
3. **异步并发** - 大量搜索时使用 asyncio
4. **缓存结果** - 避免重复搜索

## 方式选择建议

- **简单脚本** → subprocess 直接调用
- **生产项目** → ripgrepy 库或自定义封装类
- **高并发场景** → asyncio + subprocess
- **复杂分析** → JSON 解析 + 自定义处理

## 核心参数速查

```python
# 文件类型
type="py", type="js", type="rust"

# Glob 模式
glob="*.py", glob="*.{js,ts}", glob="src/**"

# 忽略大小写
ignore_case=True

# 显示上下文
context=3  # 前后 3 行

# 隐藏文件
hidden=True

# 忽略 gitignore
no_ignore=True

# 最大深度
max_depth=3

# 最大匹配数
max_count=100
```

## 总结

ripgrep 在 Python 中使用非常灵活，可以根据场景选择合适的方式。推荐使用封装类或 ripgrepy 库，代码更清晰易维护。
