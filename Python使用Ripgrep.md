# Python 中使用 Ripgrep

## 方式一：subprocess 直接调用

最简单直接的方式，通过 Python 的 subprocess 模块调用 ripgrep 命令。

### 基础示例

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
    context: int = 0,
    max_count: Optional[int] = None,
) -> List[Dict]:
    """
    使用 ripgrep 搜索文件内容

    Args:
        pattern: 搜索模式（正则表达式）
        path: 搜索目录，默认当前目录
        file_type: 文件类型，如 "js", "py", "rust"
        glob: glob 模式过滤，如 "*.js"
        ignore_case: 是否忽略大小写
        context: 显示上下文行数
        max_count: 最大匹配数

    Returns:
        匹配结果列表，格式为 [{"path": str, "line": int, "text": str}, ...]
    """
    cmd = ["rg", "--json", "--with-filename", "--line-number"]

    if ignore_case:
        cmd.append("--ignore-case")

    if file_type:
        cmd.extend(["--type", file_type])

    if glob:
        cmd.extend(["--glob", glob])

    if context > 0:
        cmd.extend(["--context", str(context)])

    if max_count:
        cmd.extend(["--max-count", str(max_count)])

    cmd.append(pattern)
    cmd.append(path)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
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
            check=True
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
            check=True
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


# 使用示例
if __name__ == "__main__":
    # 搜索函数定义
    matches = ripgrep_search(
        pattern=r"def\s+\w+",
        path="./src",
        file_type="py",
        ignore_case=True
    )
    print(f"找到 {len(matches)} 个函数定义")

    # 列出所有 Python 文件
    files = ripgrep_files(path=".", glob="*.py")
    print(f"找到 {len(files)} 个 Python 文件")

    # 统计 TODO 数量
    counts = ripgrep_count(pattern="TODO", path=".", glob="*.py")
    total = sum(counts.values())
    print(f"总共 {total} 个 TODO")
```

### 封装类版本

```python
import subprocess
import json
from dataclasses import dataclass
from typing import List, Optional, Iterator
from pathlib import Path


@dataclass
class RipgrepMatch:
    path: str
    line_number: int
    column: int
    text: str
    matched_text: str
    start: int
    end: int


class Ripgrep:
    """Ripgrep Python 封装"""

    def __init__(self, rg_path: str = "rg"):
        """
        Args:
            rg_path: ripgrep 可执行文件路径，默认从 PATH 查找
        """
        self.rg_path = rg_path

    def search(
        self,
        pattern: str,
        path: str = ".",
        *,
        file_type: Optional[str] = None,
        glob: Optional[str] = None,
        ignore_case: bool = False,
        smart_case: bool = False,
        word: bool = False,
        fixed_strings: bool = False,
        max_count: Optional[int] = None,
        max_filesize: Optional[str] = None,
        max_depth: Optional[int] = None,
        hidden: bool = False,
        follow: bool = False,
        no_ignore: bool = False,
    ) -> List[RipgrepMatch]:
        """
        搜索文件内容

        Args:
            pattern: 搜索模式
            path: 搜索路径
            file_type: 文件类型
            glob: glob 模式
            ignore_case: 忽略大小写
            smart_case: 智能大小写
            word: 匹配完整单词
            fixed_strings: 字面匹配
            max_count: 每个文件最大匹配数
            max_filesize: 最大文件大小 (如 "10M", "1G")
            max_depth: 最大搜索深度
            hidden: 包含隐藏文件
            follow: 跟随符号链接
            no_ignore: 忽略 .gitignore

        Returns:
            匹配结果列表
        """
        cmd = [
            self.rg_path,
            "--json",
            "--with-filename",
            "--line-number",
            "--column",
        ]

        if ignore_case:
            cmd.append("--ignore-case")
        if smart_case:
            cmd.append("--smart-case")
        if word:
            cmd.append("--word-regexp")
        if fixed_strings:
            cmd.append("--fixed-strings")
        if hidden:
            cmd.append("--hidden")
        if follow:
            cmd.append("--follow")
        if no_ignore:
            cmd.append("--no-ignore")

        if file_type:
            cmd.extend(["--type", file_type])
        if glob:
            cmd.extend(["--glob", glob])
        if max_count is not None:
            cmd.extend(["--max-count", str(max_count)])
        if max_filesize:
            cmd.extend(["--max-filesize", max_filesize])
        if max_depth is not None:
            cmd.extend(["--max-depth", str(max_depth)])

        cmd.append(pattern)
        cmd.append(path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                return []
            raise

        matches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            data = json.loads(line)
            if data["type"] != "match":
                continue

            match_data = data["data"]
            for submatch in match_data["submatches"]:
                matches.append(RipgrepMatch(
                    path=match_data["path"]["text"],
                    line_number=match_data["line_number"],
                    column=submatch["start"] + 1,  # 转为 1-based
                    text=match_data["lines"]["text"].rstrip("\n"),
                    matched_text=submatch["match"]["text"],
                    start=submatch["start"],
                    end=submatch["end"],
                ))

        return matches

    def search_iter(
        self,
        pattern: str,
        path: str = ".",
        **kwargs
    ) -> Iterator[RipgrepMatch]:
        """
        流式搜索，逐个返回结果，适合大量结果
        """
        cmd = [
            self.rg_path,
            "--json",
            "--with-filename",
            "--line-number",
            "--column",
        ]

        # 添加其他参数（同 search 方法）
        for key, value in kwargs.items():
            if value is True:
                cmd.append(f"--{key.replace('_', '-')}")
            elif value is not None and value is not False:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        cmd.append(pattern)
        cmd.append(path)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        for line in process.stdout:
            if not line.strip():
                continue

            data = json.loads(line)
            if data["type"] != "match":
                continue

            match_data = data["data"]
            for submatch in match_data["submatches"]:
                yield RipgrepMatch(
                    path=match_data["path"]["text"],
                    line_number=match_data["line_number"],
                    column=submatch["start"] + 1,
                    text=match_data["lines"]["text"].rstrip("\n"),
                    matched_text=submatch["match"]["text"],
                    start=submatch["start"],
                    end=submatch["end"],
                )

        process.wait()

    def files(
        self,
        path: str = ".",
        *,
        glob: Optional[str] = None,
        hidden: bool = False,
        follow: bool = False,
        max_depth: Optional[int] = None,
    ) -> List[str]:
        """列出文件"""
        cmd = [self.rg_path, "--files"]

        if hidden:
            cmd.append("--hidden")
        if follow:
            cmd.append("--follow")
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
                check=True
            )
            return [f for f in result.stdout.strip().split("\n") if f]
        except subprocess.CalledProcessError:
            return []

    def count(
        self,
        pattern: str,
        path: str = ".",
        **kwargs
    ) -> int:
        """统计匹配总数"""
        cmd = [self.rg_path, "--count-matches"]

        # 添加参数
        for key, value in kwargs.items():
            if value is True:
                cmd.append(f"--{key.replace('_', '-')}")
            elif value is not None and value is not False:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        cmd.append(pattern)
        cmd.append(path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return sum(int(line.split(":")[-1]) for line in result.stdout.strip().split("\n") if line)
        except subprocess.CalledProcessError:
            return 0

    def replace(
        self,
        pattern: str,
        replacement: str,
        path: str = ".",
        **kwargs
    ) -> str:
        """
        替换文本（仅预览，不修改文件）

        Returns:
            替换后的预览文本
        """
        cmd = [self.rg_path, "--passthru", "-r", replacement]

        for key, value in kwargs.items():
            if value is True:
                cmd.append(f"--{key.replace('_', '-')}")
            elif value is not None and value is not False:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        cmd.append(pattern)
        cmd.append(path)

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout


# 使用示例
if __name__ == "__main__":
    rg = Ripgrep()

    # 搜索
    matches = rg.search(
        pattern=r"import\s+\w+",
        path="./src",
        file_type="py"
    )

    for match in matches[:5]:  # 显示前 5 个
        print(f"{match.path}:{match.line_number}: {match.matched_text}")

    # 流式搜索（适合大量结果）
    for match in rg.search_iter("TODO", path=".", glob="*.py"):
        print(f"{match.path}:{match.line_number}")

    # 列出文件
    files = rg.files(path=".", glob="*.py", max_depth=3)
    print(f"找到 {len(files)} 个文件")

    # 统计
    total = rg.count("def", path=".", file_type="py")
    print(f"总共 {total} 个函数定义")

    # 替换预览
    preview = rg.replace("old_name", "new_name", path="./src", file_type="py")
    print(preview)
```

## 方式二：使用 ripgrepy 库

第三方 Python 库，提供更友好的 API。

### 安装

```bash
pip install ripgrepy
```

### 基本使用

```python
from ripgrepy import Ripgrepy

# 创建搜索实例
rg = Ripgrepy(".", pattern="TODO")

# 执行搜索
results = rg.i().type("py").run()

for result in results:
    print(f"{result.file_path}:{result.line_number}: {result.line_text}")
```

### 完整示例

```python
from ripgrepy import Ripgrepy

# 基本搜索
results = Ripgrepy("/path/to/search", "pattern").run()

# 忽略大小写
results = Ripgrepy(".", "TODO").i().run()

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

# JSON 输出
results = Ripgrepy(".", "pattern").json().run()

# 流式输出
for result in Ripgrepy(".", "pattern").stream():
    print(result)
```

### 高级用法

```python
from ripgrepy import Ripgrepy

# 组合多个选项
results = (
    Ripgrepy("/project/src", r"def\s+\w+")
    .type("py")
    .i()
    .context(2)
    .max_count(100)
    .run()
)

# 使用正则
results = (
    Ripgrepy(".", r"import\s+\{[^}]+\}")
    .type("ts")
    .run()
)

# 排除目录
results = (
    Ripgrepy(".", "console.log")
    .glob("*.js")
    .glob("!node_modules")
    .glob("!dist")
    .run()
)

# 搜索隐藏文件
results = Ripgrepy(".", "pattern").hidden().run()

# 忽略 .gitignore
results = Ripgrepy(".", "pattern").no_ignore().run()
```

## 方式三：异步调用

使用 asyncio 提高性能，适合大量并发搜索。

```python
import asyncio
import subprocess
import json
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor


class AsyncRipgrep:
    """异步 Ripgrep 封装"""

    def __init__(self, rg_path: str = "rg", max_workers: int = 4):
        self.rg_path = rg_path
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def search(
        self,
        pattern: str,
        path: str = ".",
        **kwargs
    ) -> List[Dict]:
        """异步搜索"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_search,
            pattern,
            path,
            kwargs
        )

    def _sync_search(self, pattern: str, path: str, options: dict) -> List[Dict]:
        """同步搜索实现"""
        cmd = [self.rg_path, "--json", "--with-filename", "--line-number"]

        # 构建命令
        for key, value in options.items():
            if value is True:
                cmd.append(f"--{key.replace('_', '-')}")
            elif value is not None and value is not False:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        cmd.extend([pattern, path])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            matches = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                data = json.loads(line)
                if data["type"] == "match":
                    matches.append(data)

            return matches

        except subprocess.CalledProcessError:
            return []

    async def search_multiple(
        self,
        patterns: List[str],
        path: str = ".",
        **kwargs
    ) -> Dict[str, List[Dict]]:
        """并行搜索多个模式"""
        tasks = [
            self.search(pattern, path, **kwargs)
            for pattern in patterns
        ]
        results = await asyncio.gather(*tasks)
        return dict(zip(patterns, results))

    async def search_paths(
        self,
        pattern: str,
        paths: List[str],
        **kwargs
    ) -> Dict[str, List[Dict]]:
        """并行搜索多个路径"""
        tasks = [
            self.search(pattern, path, **kwargs)
            for path in paths
        ]
        results = await asyncio.gather(*tasks)
        return dict(zip(paths, results))


# 使用示例
async def main():
    rg = AsyncRipgrep()

    # 单次搜索
    results = await rg.search(
        "TODO",
        path="./src",
        file_type="py"
    )
    print(f"找到 {len(results)} 个结果")

    # 并行搜索多个模式
    patterns = ["TODO", "FIXME", "HACK"]
    results = await rg.search_multiple(
        patterns,
        path="./src",
        file_type="py"
    )
    for pattern, matches in results.items():
        print(f"{pattern}: {len(matches)} 个")

    # 并行搜索多个路径
    paths = ["./src", "./tests", "./docs"]
    results = await rg.search_paths(
        "import",
        paths=paths,
        file_type="py"
    )
    for path, matches in results.items():
        print(f"{path}: {len(matches)} 个导入")


if __name__ == "__main__":
    asyncio.run(main())
```

## 方式四：直接解析 JSON 输出

手动解析 ripgrep 的 JSON 输出，最灵活。

```python
import subprocess
import json
from typing import Iterator, Dict, Any


def ripgrep_json(pattern: str, path: str = ".", **options) -> Iterator[Dict[str, Any]]:
    """
    获取 ripgrep JSON 输出并解析

    Yields:
        解析后的 JSON 对象，类型可能是: begin, match, end, summary
    """
    cmd = ["rg", "--json"]

    for key, value in options.items():
        if value is True:
            cmd.append(f"--{key.replace('_', '-')}")
        elif value is not None and value is not False:
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    cmd.extend([pattern, path])

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    for line in process.stdout:
        if line.strip():
            yield json.loads(line)

    process.wait()


# 使用示例
if __name__ == "__main__":
    # 解析所有类型的输出
    for item in ripgrep_json("def", path=".", type="py"):
        if item["type"] == "begin":
            print(f"开始搜索: {item['data']['path']['text']}")

        elif item["type"] == "match":
            data = item["data"]
            print(f"{data['path']['text']}:{data['line_number']}")
            print(f"  {data['lines']['text'].strip()}")

            for submatch in data["submatches"]:
                print(f"    匹配: {submatch['match']['text']}")

        elif item["type"] == "end":
            stats = item["data"]["stats"]
            print(f"搜索完成: {stats['matches']} 个匹配")

        elif item["type"] == "summary":
            elapsed = item["data"]["elapsed_total"]
            print(f"总耗时: {elapsed['human']}")
```

## 实用工具函数

### 搜索并高亮显示

```python
from termcolor import colored
import subprocess
import json


def search_with_highlight(pattern: str, path: str = ".", **options):
    """搜索并高亮显示结果"""
    cmd = ["rg", "--json", "--color=never"]

    for key, value in options.items():
        if value is True:
            cmd.append(f"--{key.replace('_', '-')}")
        elif value is not None and value is not False:
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    cmd.extend([pattern, path])

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
            start = submatch["start"]
            end = submatch["end"]
            text = text[:start] + colored(text[start:end], "red", attrs=["bold"]) + text[end:]

        print(f"{filepath}:{line_num}: {text}")


# 使用
search_with_highlight("import", path="./src", type="py")
```

### 搜索并生成报告

```python
import subprocess
import json
from collections import defaultdict
from datetime import datetime


def generate_search_report(pattern: str, path: str = ".", **options):
    """生成搜索报告"""
    cmd = ["rg", "--json"]

    for key, value in options.items():
        if value is True:
            cmd.append(f"--{key.replace('_', '-')}")
        elif value is not None and value is not False:
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    cmd.extend([pattern, path])

    result = subprocess.run(cmd, capture_output=True, text=True)

    # 统计
    matches_by_file = defaultdict(list)
    total_matches = 0

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
            total_matches += 1

    # 生成报告
    report = []
    report.append(f"# 搜索报告")
    report.append(f"")
    report.append(f"- 模式: `{pattern}`")
    report.append(f"- 路径: `{path}`")
    report.append(f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"- 总匹配数: {total_matches}")
    report.append(f"- 涉及文件: {len(matches_by_file)}")
    report.append(f"")
    report.append(f"## 匹配详情")
    report.append(f"")

    for filepath, matches in sorted(matches_by_file.items()):
        report.append(f"### {filepath} ({len(matches)} 个匹配)")
        report.append(f"")
        for match in matches:
            report.append(f"- 行 {match['line']}: `{match['text']}`")
        report.append(f"")

    return "\n".join(report)


# 使用
report = generate_search_report("TODO", path="./src", type="py")
print(report)
```

### 搜索并导出 CSV

```python
import subprocess
import json
import csv
from io import StringIO


def search_to_csv(pattern: str, output_file: str, path: str = ".", **options):
    """搜索结果导出为 CSV"""
    cmd = ["rg", "--json", "--with-filename", "--line-number", "--column"]

    for key, value in options.items():
        if value is True:
            cmd.append(f"--{key.replace('_', '-')}")
        elif value is not None and value is not False:
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    cmd.extend([pattern, path])

    result = subprocess.run(cmd, capture_output=True, text=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['文件路径', '行号', '列号', '匹配文本', '整行内容'])

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
                        submatch["start"] + 1,
                        submatch["match"]["text"],
                        match_data["lines"]["text"].strip(),
                    ])

    print(f"已导出到 {output_file}")


# 使用
search_to_csv("function", "functions.csv", path="./src", type="js")
```

## 性能优化建议

### 1. 使用流式处理

```python
# ❌ 不好 - 一次性加载所有结果
results = list(ripgrep_json("pattern", path="."))

# ✅ 好 - 流式处理
for item in ripgrep_json("pattern", path="."):
    process(item)
```

### 2. 限制搜索范围

```python
# ❌ 不好 - 搜索整个项目
rg.search("pattern", path=".")

# ✅ 好 - 限制深度和类型
rg.search("pattern", path=".", max_depth=3, file_type="py")
```

### 3. 使用异步并发

```python
# ✅ 并发搜索多个路径
async def search_all():
    rg = AsyncRipgrep()
    paths = ["src", "tests", "docs"]
    results = await rg.search_paths("pattern", paths)
    return results
```

### 4. 缓存结果

```python
import hashlib
import pickle
from pathlib import Path
from functools import lru_cache


def cached_search(pattern: str, path: str = ".", **options):
    """带缓存的搜索"""
    # 生成缓存键
    cache_key = hashlib.md5(
        f"{pattern}:{path}:{sorted(options.items())}".encode()
    ).hexdigest()

    cache_file = Path(".cache") / f"{cache_key}.pkl"
    cache_file.parent.mkdir(exist_ok=True)

    # 尝试读取缓存
    if cache_file.exists():
        return pickle.loads(cache_file.read_bytes())

    # 执行搜索
    results = ripgrep_search(pattern, path, **options)

    # 写入缓存
    cache_file.write_bytes(pickle.dumps(results))

    return results
```

## 完整示例：代码分析工具

```python
import subprocess
import json
from dataclasses import dataclass
from typing import List, Dict
from collections import Counter


@dataclass
class CodeStats:
    total_functions: int
    total_classes: int
    total_imports: int
    total_lines: int
    total_files: int
    todos: int
    fixmes: int


class CodeAnalyzer:
    """代码分析工具"""

    def __init__(self, rg_path: str = "rg"):
        self.rg_path = rg_path

    def _search(self, pattern: str, path: str = ".", **options) -> List[Dict]:
        """执行搜索"""
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

    def analyze_python(self, path: str = ".") -> CodeStats:
        """分析 Python 代码"""
        return CodeStats(
            total_functions=len(self._search(r"def\s+\w+", path, type="py")),
            total_classes=len(self._search(r"class\s+\w+", path, type="py")),
            total_imports=len(self._search(r"import\s+", path, type="py")),
            total_lines=self._count_lines(path, glob="*.py"),
            total_files=len(self._list_files(path, glob="*.py")),
            todos=len(self._search("TODO", path, type="py")),
            fixmes=len(self._search("FIXME", path, type="py")),
        )

    def analyze_javascript(self, path: str = ".") -> CodeStats:
        """分析 JavaScript/TypeScript 代码"""
        return CodeStats(
            total_functions=len(self._search(r"function\s+\w+", path, glob="*.js")),
            total_classes=len(self._search(r"class\s+\w+", path, glob="*.{js,ts}")),
            total_imports=len(self._search(r"import\s+", path, glob="*.{js,ts}")),
            total_lines=self._count_lines(path, glob="*.{js,ts}"),
            total_files=len(self._list_files(path, glob="*.{js,ts}")),
            todos=len(self._search("TODO", path, glob="*.{js,ts}")),
            fixmes=len(self._search("FIXME", path, glob="*.{js,ts}")),
        )

    def find_duplicates(self, path: str = ".", min_lines: int = 5) -> Dict[str, List[str]]:
        """查找重复代码块"""
        # 这个需要更复杂的实现，这里只是示例
        pass

    def _count_lines(self, path: str, **options) -> int:
        """统计代码行数"""
        cmd = [self.rg_path, "--count-matches"]

        for key, value in options.items():
            if value is True:
                cmd.append(f"--{key.replace('_', '-')}")
            elif value is not None and value is not False:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        cmd.extend([".", path])

        result = subprocess.run(cmd, capture_output=True, text=True)
        total = 0
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.rsplit(":", 1)
                if len(parts) == 2:
                    total += int(parts[1])
        return total

    def _list_files(self, path: str, **options) -> List[str]:
        """列出文件"""
        cmd = [self.rg_path, "--files"]

        for key, value in options.items():
            if value is True:
                cmd.append(f"--{key.replace('_', '-')}")
            elif value is not None and value is not False:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        cmd.append(path)

        result = subprocess.run(cmd, capture_output=True, text=True)
        return [f for f in result.stdout.strip().split("\n") if f]


# 使用示例
if __name__ == "__main__":
    analyzer = CodeAnalyzer()

    # 分析 Python 代码
    python_stats = analyzer.analyze_python("./src")
    print("Python 代码统计:")
    print(f"  函数: {python_stats.total_functions}")
    print(f"  类: {python_stats.total_classes}")
    print(f"  导入: {python_stats.total_imports}")
    print(f"  行数: {python_stats.total_lines}")
    print(f"  文件: {python_stats.total_files}")
    print(f"  TODO: {python_stats.todos}")
    print(f"  FIXME: {python_stats.fixmes}")

    # 分析 JavaScript 代码
    js_stats = analyzer.analyze_javascript("./frontend")
    print("\nJavaScript/TypeScript 代码统计:")
    print(f"  函数: {js_stats.total_functions}")
    print(f"  类: {js_stats.total_classes}")
    print(f"  导入: {js_stats.total_imports}")
    print(f"  行数: {js_stats.total_lines}")
    print(f"  文件: {js_stats.total_files}")
    print(f"  TODO: {js_stats.todos}")
    print(f"  FIXME: {js_stats.fixmes}")
```

## 总结

在 Python 中使用 ripgrep 的方式：

1. **subprocess 直接调用** - 最简单直接，适合简单场景
2. **ripgrepy 库** - 提供更友好的 API，推荐用于生产环境
3. **异步调用** - 适合大量并发搜索，性能最优
4. **JSON 解析** - 最灵活，适合需要精细控制输出格式的场景

推荐方案：

- 简单脚本 → subprocess
- 生产项目 → ripgrepy 或自定义封装类
- 高并发场景 → asyncio + subprocess
- 复杂分析 → JSON 解析 + 自定义处理
