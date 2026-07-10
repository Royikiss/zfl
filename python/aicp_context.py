#!/usr/bin/env python3
import argparse
import json
import os
import re
import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

IGNORE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "dist", "build", "target", "coverage",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "venv", ".next", ".turbo",
    ".idea", ".vscode", ".cache",
}

IGNORE_FILES = {
    ".DS_Store", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb",
    "Cargo.lock", "poetry.lock",
}

INCLUDE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".swift", ".c", ".h", ".cpp", ".hpp",
    ".sh", ".zsh", ".bash", ".ps1",
    ".md", ".txt", ".rst",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".conf", ".env", ".sql",
    ".html", ".css", ".scss", ".xml",
}

NAME_WHITELIST = {
    "Dockerfile", "Makefile", "README", "README.md", "README.zh-CN.md", "LICENSE",
}

IGNORE_FILE_NAME = ".ignore"

LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "tsx",
    ".jsx": "jsx", ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
    ".sh": "bash", ".zsh": "bash", ".bash": "bash", ".ps1": "powershell",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".md": "markdown", ".sql": "sql", ".html": "html", ".css": "css",
    ".cpp": "cpp", ".c": "c", ".h": "c", ".hpp": "cpp",
}

DOC_FILE_EXTS = {
    ".md", ".rst", ".adoc", ".asciidoc", ".org", ".tex", ".txt",
    ".dox", ".doxygen", ".chm",
}

DOC_FILE_NAMES = {
    "doxyfile", "mkdocs.yml", "mkdocs.yaml",
    "readme", "readme.md", "readme.rst",
    "changelog", "changelog.md", "history.md", "release-notes.md",
    "contributing", "contributing.md", "code_of_conduct.md",
    "license", "license.md", "copying",
}

DOC_DIR_MARKERS = {
    "doc", "docs", "documentation", "wiki", "manual", "man", "guides", "guide",
    "reference", "references", "apidoc", "apidocs",
}


@dataclass
class ModeConfig:
    max_total_chars: int
    max_file_chars: int
    max_files: int
    snippet_head_lines: int
    include_snippets: bool


MODE_MAP: Dict[str, ModeConfig] = {
    "fast": ModeConfig(45000, 1200, 180, 80, False),
    "balanced": ModeConfig(120000, 3500, 260, 140, True),
    "deep": ModeConfig(220000, 7000, 360, 220, True),
    "full": ModeConfig(999999999, 999999999, 999999, 9999999, True),
}


def safe_read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return ""


def is_probably_text(path: Path) -> bool:
    try:
        data = path.read_bytes()[:4096]
    except Exception:
        return False
    if not data:
        return True
    return b"\x00" not in data


def path_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def is_ignored(path: Path) -> bool:
    if path.name in IGNORE_FILES:
        return True
    if any(part in IGNORE_DIRS for part in path.parts):
        return True
    return False


def should_include(path: Path) -> bool:
    if not path.is_file() or is_ignored(path):
        return False
    if path.name in NAME_WHITELIST:
        return True
    suffix = path.suffix.lower()
    if suffix in INCLUDE_EXTS:
        return True
    if path.name.startswith(".") and suffix in {".env", ".conf"}:
        return True
    return False


def should_include_text(path: Path) -> bool:
    """Include any text file for --mode full (no extension whitelist)."""
    if not path.is_file():
        return False
    if path.name in IGNORE_FILES:
        return False
    if any(part in IGNORE_DIRS for part in path.parts):
        return False
    return is_probably_text(path)


def iter_files_under(directory: Path, full_mode: bool = False) -> Iterable[Path]:
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        root_path = Path(root)
        for f in files:
            p = root_path / f
            if full_mode:
                if should_include_text(p):
                    yield p
            else:
                if should_include(p):
                    yield p


def run_git(root: Path, args: List[str]) -> List[str]:
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return []
        return [x.strip() for x in proc.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def load_ignore_patterns(root: Path) -> Optional[List[str]]:
    """Load patterns from .ignore file at project root. Returns None if file doesn't exist or is empty."""
    ignore_file = root / IGNORE_FILE_NAME
    if not ignore_file.exists():
        return None
    patterns = []
    for line in ignore_file.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        patterns.append(line)
    return patterns if patterns else None


def match_ignore_patterns(rel_path: Path, patterns: Optional[List[str]]) -> bool:
    """
    Check if a relative path matches .ignore patterns (gitignore-style).

    Supports: #comments, blank lines, !negation, trailing / for directories,
    * and ? globs, patterns with and without slashes.
    """
    if not patterns:
        return False

    path_str = rel_path.as_posix()
    ignored = False

    for pattern in patterns:
        is_negation = pattern.startswith('!')
        pat = pattern[1:] if is_negation else pattern

        is_dir_only = pat.endswith('/')
        if is_dir_only:
            pat = pat.rstrip('/')

        matched = False

        # Patterns with / are matched against the full relative path
        if '/' in pat:
            if fnmatch.fnmatch(path_str, pat):
                matched = True
            elif fnmatch.fnmatch(path_str, '*/' + pat):
                matched = True
        else:
            # Patterns without / are matched against basename
            if fnmatch.fnmatch(rel_path.name, pat):
                matched = True
            # Directory-only patterns also match any path component
            if not matched and is_dir_only:
                if any(fnmatch.fnmatch(part, pat) for part in rel_path.parts):
                    matched = True

        if matched:
            ignored = not is_negation

    return ignored


def git_changed_files(root: Path, changed_from: Optional[str], changed_commit_range: Optional[str]) -> Set[Path]:
    changed: Set[Path] = set()

    if changed_commit_range:
        names = run_git(root, ["diff", "--name-only", changed_commit_range, "--"])
        names += run_git(root, ["ls-files", "--others", "--exclude-standard"])
    elif changed_from:
        names = run_git(root, ["diff", "--name-only", changed_from, "--"])
        names += run_git(root, ["ls-files", "--others", "--exclude-standard"])
    else:
        names = run_git(root, ["diff", "--name-only", "HEAD"])
        names += run_git(root, ["ls-files", "--others", "--exclude-standard"])

    for n in names:
        p = (root / n).resolve()
        if p.exists() and path_under(p, root):
            changed.add(p)
    return changed


def collect_files(root: Path, all_mode: bool, targets: List[str], max_files: int,
                  full_mode: bool = False, ignore_patterns: Optional[List[str]] = None) -> List[Path]:
    result: List[Path] = []
    seen = set()

    def add_file(p: Path):
        try:
            rp = p.resolve()
        except Exception:
            return
        if rp in seen:
            return
        if not path_under(rp, root):
            return
        if full_mode:
            # For full mode, iter_files_under already filtered; just binary check
            if not is_probably_text(rp):
                return
        else:
            if not should_include(rp):
                return
            if not is_probably_text(rp):
                return
        # Apply .ignore filtering (only for full mode)
        if full_mode and ignore_patterns:
            try:
                rel = rp.relative_to(root)
                if match_ignore_patterns(rel, ignore_patterns):
                    return
            except Exception:
                pass
        seen.add(rp)
        result.append(rp)

    if all_mode:
        for p in iter_files_under(root, full_mode=full_mode):
            add_file(p)
    else:
        for t in targets:
            candidate = Path(t)
            target = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
            if target.is_dir():
                for p in iter_files_under(target):
                    add_file(p)
            elif target.is_file():
                add_file(target)

    result_sorted = sorted(result)
    return result_sorted[:max_files]


def file_priority(rel: Path) -> int:
    name = rel.name.lower()
    s = str(rel).lower()
    score = 0
    if "readme" in name:
        score += 120
    if any(x in s for x in ["docs/", "doc/", "architecture", "design"]):
        score += 80
    if name in {"main.py", "app.py", "index.ts", "index.js", "base.zsh", "aicp.zsh"}:
        score += 70
    if rel.parts and rel.parts[0] in {"core", "src", "functions", "python"}:
        score += 20
    return score


def trim_snippet(text: str, max_chars: int, head_lines: int) -> str:
    lines = text.splitlines()
    head = "\n".join(lines[:head_lines])
    if len(head) <= max_chars:
        return head
    return head[:max_chars] + "\n...<truncated>"


def compile_regexes(patterns: List[str]) -> List[re.Pattern]:
    regs: List[re.Pattern] = []
    for p in patterns:
        try:
            regs.append(re.compile(p, re.IGNORECASE | re.MULTILINE))
        except re.error:
            continue
    return regs


def match_include(rel: Path, text: str, keywords: List[str], regexes: List[re.Pattern]) -> bool:
    if not keywords and not regexes:
        return True
    s = str(rel)
    for kw in keywords:
        if kw.lower() in s.lower() or kw.lower() in text.lower():
            return True
    for reg in regexes:
        if reg.search(s) or reg.search(text):
            return True
    return False


def match_exclude(rel: Path, text: str, keywords: List[str], regexes: List[re.Pattern]) -> bool:
    s = str(rel)
    for kw in keywords:
        if kw.lower() in s.lower() or kw.lower() in text.lower():
            return False
    for reg in regexes:
        if reg.search(s) or reg.search(text):
            return False
    return True


def is_doc_file(rel: Path) -> bool:
    if rel.suffix.lower() in DOC_FILE_EXTS:
        return True
    if rel.name.lower() in DOC_FILE_NAMES:
        return True
    for part in rel.parts:
        if part.lower() in DOC_DIR_MARKERS:
            return True
    return False


def snippet_around_matches(
    text: str,
    keywords: List[str],
    regexes: List[re.Pattern],
    context_lines: int,
    fallback_head_lines: int,
) -> str:
    if not text.strip():
        return ""

    lines = text.splitlines()
    hit_indices: Set[int] = set()

    for i, line in enumerate(lines):
        for kw in keywords:
            if kw.lower() in line.lower():
                hit_indices.add(i)
        for reg in regexes:
            if reg.search(line):
                hit_indices.add(i)

    if not hit_indices:
        return "\n".join(lines[:fallback_head_lines])

    snippet_lines: List[str] = []
    seen_intervals: Set[Tuple[int, int]] = set()

    for idx in sorted(hit_indices):
        start = max(0, idx - context_lines)
        end = min(len(lines), idx + context_lines + 1)

        merged = False
        for interval in list(seen_intervals):
            if start <= interval[1]:
                seen_intervals.remove(interval)
                start = min(start, interval[0])
                end = max(end, interval[1])
                seen_intervals.add((start, end))
                merged = True
                break
        if not merged:
            seen_intervals.add((start, end))

    for start, end in sorted(seen_intervals):
        if snippet_lines:
            snippet_lines.append("... (gap)")
        snippet_lines.extend(lines[start:end])

    return "\n".join(snippet_lines)


def is_doc_name(name: str) -> bool:
    return name.lower() in DOC_FILE_NAMES


def build_context(
    root: Path,
    mode_cfg: ModeConfig,
    all_mode: bool,
    targets: List[str],
    include_keywords: List[str],
    include_regexes: List[re.Pattern],
    exclude_keywords: List[str],
    exclude_regexes: List[re.Pattern],
    ignore_docs: bool,
    snippet_around_query: bool,
    snippet_context_lines: int,
    changed_files: Optional[Set[Path]],
    prompt: str,
    full_mode: bool = False,
    ignore_patterns: Optional[List[str]] = None,
) -> str:

    files: List[Path] = []
    if changed_files is not None:
        for p in sorted(changed_files, key=lambda x: x.name):
            if should_include(p) and is_probably_text(p):
                files.append(p)
    elif all_mode or targets:
        files = collect_files(root, all_mode, targets, mode_cfg.max_files,
                              full_mode=full_mode, ignore_patterns=ignore_patterns)
    files = files[: mode_cfg.max_files]

    filtered: List[Tuple[Path, int]] = []
    for f in files:
        rel = f.relative_to(root)
        text = safe_read_text(f)
        if not match_include(rel, text, include_keywords, include_regexes):
            continue
        if not match_exclude(rel, text, exclude_keywords, exclude_regexes):
            continue
        if ignore_docs and is_doc_file(rel):
            continue
        filtered.append((f, file_priority(rel)))
    filtered.sort(key=lambda x: (-x[1], str(x[0].relative_to(root))))

    tree_lines = build_tree(filtered, root)

    entries: List[dict] = []
    total_chars = 0
    index_chars = 0

    for f, _ in filtered:
        rel = f.relative_to(root)
        text = safe_read_text(f)
        lang = LANG_MAP.get(rel.suffix.lower(), "")
        name = rel.name

        if snippet_around_query and (include_keywords or include_regexes):
            body = snippet_around_matches(
                text=text,
                keywords=include_keywords,
                regexes=include_regexes,
                context_lines=snippet_context_lines,
                fallback_head_lines=mode_cfg.snippet_head_lines,
            )
        else:
            body = trim_snippet(text, mode_cfg.max_file_chars, mode_cfg.snippet_head_lines)

        entry = {"path": str(rel), "lang": lang, "content": body}
        est_len = len(body) + len(str(rel)) + 64
        if mode_cfg.include_snippets:
            if total_chars + est_len > mode_cfg.max_total_chars:
                break
            entries.append(entry)
            total_chars += est_len
        else:
            if index_chars + est_len > mode_cfg.max_total_chars:
                break
            entry["content"] = ""
            entries.append(entry)
            index_chars += est_len

    return format_output(entries, tree_lines, prompt, mode_cfg.include_snippets)


def build_tree(filtered: List[Tuple[Path, int]], root: Path) -> List[str]:
    tree_lines: List[str] = []
    dirs: Set[Path] = set()
    for f, _ in filtered:
        rel = f.relative_to(root)
        for parent in reversed(rel.parents):
            if parent != Path("."):
                dirs.add(parent)
        dirs.add(rel)
    sorted_dirs = sorted(dirs, key=lambda p: str(p))
    tree_lines.append(".")
    for d in sorted_dirs:
        indent = "  " * (len(d.parts) - 1) if d.parts else ""
        if d.suffix:
            tree_lines.append(f"{indent}{d.name}")
        else:
            tree_lines.append(f"{indent}{d.name}/")
    return tree_lines


def format_output(entries: List[dict], tree_lines: List[str], prompt: str, include_snippets: bool) -> str:
    parts: List[str] = []
    if prompt:
        parts.append(f"## Task\n\n{prompt}\n")
    parts.append("## Project Tree\n")
    parts.append("```\n" + "\n".join(tree_lines) + "\n```\n")
    parts.append("## File Index\n")
    for e in entries:
        p = e["path"]
        lang = e["lang"]
        if lang:
            parts.append(f"- {p} [{lang}]")
        else:
            parts.append(f"- {p}")
    if include_snippets:
        parts.append("\n")
        parts.append("## Code Snippets\n")
        for e in entries:
            if e["content"]:
                parts.append(f"### {e['path']}\n")
                parts.append(f"```{e['lang']}\n{e['content']}\n```\n")
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build AI context text from project files")
    p.add_argument("--root", default=".", help="Project root")
    p.add_argument("--mode", choices=["fast", "balanced", "deep", "full"], default="balanced")
    p.add_argument("--all", action="store_true", help="Scan all files under root")
    p.add_argument("--target", action="append", default=[], help="Specific file/dir target (repeatable)")
    p.add_argument("--query", action="append", default=[], help="Include by keyword (path/content, repeatable)")
    p.add_argument("--query-regex", action="append", default=[], help="Include by regex (repeatable)")
    p.add_argument("--exclude", action="append", default=[], help="Exclude by keyword (path/content, repeatable)")
    p.add_argument("--exclude-regex", action="append", default=[], help="Exclude by regex (repeatable)")
    p.add_argument("--ignore-docs", action="store_true", help="Ignore documentation files (doxygen/markdown/sphinx/wiki/manual etc.)")
    p.add_argument("--changed", action="store_true", help="Only include git changed/untracked files (vs HEAD)")
    p.add_argument("--changed-from", default="", help="Only include git changed/untracked files (vs ref)")
    p.add_argument("--changed-commit-range", default="", help="Only include git changed/untracked files (vs commit range, e.g. A..B)")
    p.add_argument("--prompt", default="", help="Task prompt prepend in output")
    p.add_argument("--snippet-around-query", action="store_true", help="Use query-hit neighborhood snippets instead of file head")
    p.add_argument("--snippet-context-lines", type=int, default=24, help="Context lines around query hits")
    p.add_argument("--output-format", choices=["markdown", "plain", "json"], default="markdown")
    p.add_argument("--max-files", type=int, default=0, help="Override per-run max files (0=mode default)")
    p.add_argument("--max-total-chars", type=int, default=0, help="Override per-run output max chars (0=mode default)")
    p.add_argument("--max-file-chars", type=int, default=0, help="Override per-file snippet max chars (0=mode default)")
    p.add_argument("--quality-report", action="store_true", help="Append quality report section (or include in JSON)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()

    base = MODE_MAP[args.mode]

    mode_cfg = ModeConfig(
        max_total_chars=max(1000, args.max_total_chars) if args.max_total_chars > 0 else base.max_total_chars,
        max_file_chars=max(200, args.max_file_chars) if args.max_file_chars > 0 else base.max_file_chars,
        max_files=max(1, args.max_files) if args.max_files > 0 else base.max_files,
        snippet_head_lines=base.snippet_head_lines,
        include_snippets=base.include_snippets,
    )

    include_keywords: List[str] = args.query
    include_regexes = compile_regexes(args.query_regex)
    exclude_keywords: List[str] = args.exclude
    exclude_regexes = compile_regexes(args.exclude_regex)

    changed_files: Optional[Set[Path]] = None
    if args.changed or args.changed_from or args.changed_commit_range:
        changed_files = git_changed_files(root, args.changed_from, args.changed_commit_range)

    ignore_patterns = load_ignore_patterns(root)
    full_mode = (args.mode == "full")

    context = build_context(
        root=root,
        mode_cfg=mode_cfg,
        all_mode=args.all,
        targets=args.target,
        include_keywords=include_keywords,
        include_regexes=include_regexes,
        exclude_keywords=exclude_keywords,
        exclude_regexes=exclude_regexes,
        ignore_docs=args.ignore_docs,
        snippet_around_query=args.snippet_around_query,
        snippet_context_lines=args.snippet_context_lines,
        changed_files=changed_files,
        prompt=args.prompt,
        full_mode=full_mode,
        ignore_patterns=ignore_patterns,
    )

    output_format = args.output_format
    if output_format == "plain":
        print(context)
    elif output_format == "json":
        print(json.dumps({"context": context}, ensure_ascii=False, indent=2))
    else:
        print(context)


if __name__ == "__main__":
    main()
