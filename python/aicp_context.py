#!/usr/bin/env python3
import argparse
import json
import os
import re
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


def iter_files_under(directory: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        root_path = Path(root)
        for f in files:
            p = root_path / f
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


def collect_files(root: Path, all_mode: bool, targets: List[str], max_files: int) -> List[Path]:
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
        if not should_include(rp):
            return
        if not is_probably_text(rp):
            return
        seen.add(rp)
        result.append(rp)

    if all_mode:
        for p in iter_files_under(root):
            add_file(p)
    else:
        for t in targets:
            candidate = Path(t)
            target = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
            if not target.exists() or not path_under(target, root):
                continue
            if target.is_file():
                add_file(target)
            elif target.is_dir():
                for p in iter_files_under(target):
                    add_file(p)

    result.sort(key=lambda p: str(p.relative_to(root)))
    return result[:max_files]


def build_tree(files: List[Path], root: Path) -> str:
    tree: Dict[str, dict] = {}

    for f in files:
        rel = f.relative_to(root)
        node = tree
        for part in rel.parts:
            node = node.setdefault(part, {})

    lines = [f"{root.name}/"]

    def walk(node: Dict[str, dict], prefix: str):
        keys = sorted(node.keys())
        for i, k in enumerate(keys):
            is_last = i == len(keys) - 1
            branch = "└── " if is_last else "├── "
            lines.append(prefix + branch + k)
            nxt = node[k]
            if nxt:
                walk(nxt, prefix + ("    " if is_last else "│   "))

    walk(tree, "")
    return "\n".join(lines)


def extract_symbols(path: Path, text: str, max_symbols: int = 12) -> List[str]:
    ext = path.suffix.lower()
    syms: List[str] = []
    if ext == ".py":
        syms += re.findall(r"^\s*class\s+([A-Za-z_]\w*)", text, flags=re.M)
        syms += re.findall(r"^\s*def\s+([A-Za-z_]\w*)\s*\(", text, flags=re.M)
    elif ext in {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}:
        syms += re.findall(r"function\s+([A-Za-z_]\w*)\s*\(", text)
        syms += re.findall(r"class\s+([A-Za-z_]\w*)", text)
        syms += re.findall(r"const\s+([A-Za-z_]\w*)\s*=\s*\(", text)
    elif ext == ".go":
        syms += re.findall(r"func\s+([A-Za-z_]\w*)\s*\(", text)
        syms += re.findall(r"type\s+([A-Za-z_]\w*)\s+struct", text)
    elif ext in {".zsh", ".sh", ".bash"}:
        syms += re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{", text, flags=re.M)

    uniq = []
    seen = set()
    for s in syms:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq[:max_symbols]


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

    hay = (str(rel) + "\n" + text[:16000]).lower()
    for q in keywords:
        if q.lower() in hay:
            return True

    if regexes:
        sample = str(rel) + "\n" + text[:30000]
        for reg in regexes:
            if reg.search(sample):
                return True

    return False


def match_exclude(rel: Path, text: str, keywords: List[str], regexes: List[re.Pattern]) -> bool:
    if not keywords and not regexes:
        return False

    hay = (str(rel) + "\n" + text[:16000]).lower()
    for q in keywords:
        if q.lower() in hay:
            return True

    if regexes:
        sample = str(rel) + "\n" + text[:30000]
        for reg in regexes:
            if reg.search(sample):
                return True

    return False


def find_match_line_numbers(text: str, keywords: List[str], regexes: List[re.Pattern], max_hits: int = 20) -> List[int]:
    if not keywords and not regexes:
        return []

    lines = text.splitlines()
    hits: List[int] = []

    for i, line in enumerate(lines, start=1):
        ll = line.lower()
        hit = False
        for q in keywords:
            if q.lower() in ll:
                hit = True
                break
        if not hit:
            for reg in regexes:
                if reg.search(line):
                    hit = True
                    break
        if hit:
            hits.append(i)
            if len(hits) >= max_hits:
                break

    return hits


def merge_windows(windows: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not windows:
        return []
    windows.sort()
    merged = [windows[0]]
    for s, e in windows[1:]:
        ps, pe = merged[-1]
        if s <= pe + 1:
            merged[-1] = (ps, max(pe, e))
        else:
            merged.append((s, e))
    return merged


def snippet_around_matches(
    text: str,
    max_chars: int,
    context_lines: int,
    keywords: List[str],
    regexes: List[re.Pattern],
    fallback_head_lines: int,
) -> str:
    lines = text.splitlines()
    total = len(lines)
    hits = find_match_line_numbers(text, keywords, regexes)
    if not hits:
        return trim_snippet(text, max_chars, fallback_head_lines)

    windows = []
    for ln in hits:
        s = max(1, ln - context_lines)
        e = min(total, ln + context_lines)
        windows.append((s, e))

    merged = merge_windows(windows)

    out_parts: List[str] = []
    used = 0

    for idx, (s, e) in enumerate(merged, start=1):
        header = f"# window-{idx} lines {s}-{e}\n"
        block_lines = [f"{i:04d}|{lines[i-1]}" for i in range(s, e + 1)]
        block = header + "\n".join(block_lines) + "\n"

        if used + len(block) > max_chars:
            remain = max_chars - used
            if remain > 100:
                out_parts.append(block[:remain] + "\n...<truncated>")
            break

        out_parts.append(block)
        used += len(block)

        if idx < len(merged):
            sep = "\n...<skipped>...\n"
            if used + len(sep) > max_chars:
                break
            out_parts.append(sep)
            used += len(sep)

    if not out_parts:
        return trim_snippet(text, max_chars, fallback_head_lines)

    return "".join(out_parts).rstrip()


def is_documentation_file(rel: Path) -> bool:
    parts = [p.lower() for p in rel.parts]
    name = rel.name.lower()
    suffix = rel.suffix.lower()

    if any(p in DOC_DIR_MARKERS for p in parts):
        return True

    if name in DOC_FILE_NAMES:
        return True

    if suffix in DOC_FILE_EXTS:
        return True

    if name.startswith(("readme", "changelog", "contributing", "license", "history")):
        return True

    return False


def mode_name_of(mode_cfg: ModeConfig) -> str:
    for k, v in MODE_MAP.items():
        if v == mode_cfg:
            return k
    return "custom"


def build_payload(
    root: Path,
    files: List[Path],
    mode_cfg: ModeConfig,
    include_keywords: List[str],
    include_regex_patterns: List[str],
    exclude_keywords: List[str],
    exclude_regex_patterns: List[str],
    ignore_docs: bool,
    changed_only: bool,
    changed_from: str,
    changed_commit_range: str,
    prompt: str,
    snippet_around_query: bool,
    snippet_context_lines: int,
) -> Dict:
    rel_files = [f.relative_to(root) for f in files]
    include_regexes = compile_regexes(include_regex_patterns)
    exclude_regexes = compile_regexes(exclude_regex_patterns)

    stats = {
        "candidate_files": len(files),
        "empty_or_unreadable": 0,
        "filtered_by_include": 0,
        "filtered_by_exclude": 0,
        "filtered_by_docs": 0,
        "indexed_files": 0,
        "snippet_files": 0,
        "snippet_truncated_files": 0,
        "snippet_budget_truncated": False,
        "global_truncated": False,
    }

    file_index = []
    content_map: Dict[Path, str] = {}
    total_size = 0

    for rel, abs_path in zip(rel_files, files):
        text = safe_read_text(abs_path)
        if not text.strip():
            stats["empty_or_unreadable"] += 1
            continue
        if not match_include(rel, text, include_keywords, include_regexes):
            stats["filtered_by_include"] += 1
            continue
        if match_exclude(rel, text, exclude_keywords, exclude_regexes):
            stats["filtered_by_exclude"] += 1
            continue
        if ignore_docs and is_documentation_file(rel):
            stats["filtered_by_docs"] += 1
            continue

        content_map[rel] = text
        size = abs_path.stat().st_size
        total_size += size
        line_count = text.count("\n") + 1
        symbols = extract_symbols(abs_path, text)
        file_index.append({
            "path": str(rel),
            "bytes": size,
            "lines": line_count,
            "symbols": symbols,
        })

    stats["indexed_files"] = len(content_map)

    snippets = []
    if mode_cfg.include_snippets:
        ranked = sorted(content_map.items(), key=lambda kv: (-file_priority(kv[0]), len(kv[1]), str(kv[0])))
        used = 0

        for rel, text in ranked:
            suffix = rel.suffix.lower()
            lang = LANG_MAP.get(suffix, suffix.lstrip("."))

            if snippet_around_query and (include_keywords or include_regexes):
                body = snippet_around_matches(
                    text=text,
                    max_chars=mode_cfg.max_file_chars,
                    context_lines=snippet_context_lines,
                    keywords=include_keywords,
                    regexes=include_regexes,
                    fallback_head_lines=mode_cfg.snippet_head_lines,
                )
            else:
                body = trim_snippet(text, mode_cfg.max_file_chars, mode_cfg.snippet_head_lines)

            entry = {"path": str(rel), "lang": lang, "content": body}
            est_len = len(body) + len(str(rel)) + 64
            if used + est_len > mode_cfg.max_total_chars:
                stats["snippet_budget_truncated"] = True
                break
            snippets.append(entry)
            used += est_len
            if "...<truncated>" in body:
                stats["snippet_truncated_files"] += 1

    stats["snippet_files"] = len(snippets)

    meta = {
        "root": str(root),
        "files_indexed": len(content_map),
        "total_size_bytes": total_size,
        "mode": mode_name_of(mode_cfg),
        "changed_only": changed_only,
        "changed_from": changed_from or "(none)",
        "changed_commit_range": changed_commit_range or "(none)",
        "query": include_keywords,
        "query_regex": include_regex_patterns,
        "exclude": exclude_keywords,
        "exclude_regex": exclude_regex_patterns,
        "ignore_docs": ignore_docs,
        "snippet_strategy": "around-query" if snippet_around_query else "head",
        "snippet_context_lines": snippet_context_lines,
    }

    payload = {
        "meta": meta,
        "task_prompt": prompt.strip() if prompt else "请先根据 FILE INDEX 概括模块关系，再结合 CODE SNIPPETS 回答问题。",
        "project_tree": build_tree([root / r for r in content_map.keys()], root) if content_map else "(empty)",
        "file_index": file_index,
        "snippets": snippets,
        "quality_report": stats,
    }
    return payload


def render_markdown(payload: Dict, mode_cfg: ModeConfig, with_quality: bool) -> str:
    m = payload["meta"]
    lines = [
        "=== AI CONTEXT PACK ===",
        f"root: {m['root']}",
        f"files_indexed: {m['files_indexed']}",
        f"total_size: {m['total_size_bytes']} bytes",
        f"mode: {m['mode']}",
        f"changed_only: {'yes' if m['changed_only'] else 'no'}",
        f"changed_from: {m['changed_from']}",
        f"changed_commit_range: {m['changed_commit_range']}",
        f"query: {', '.join(m['query']) if m['query'] else '(none)'}",
        f"query_regex: {', '.join(m['query_regex']) if m['query_regex'] else '(none)'}",
        f"exclude: {', '.join(m['exclude']) if m['exclude'] else '(none)'}",
        f"exclude_regex: {', '.join(m['exclude_regex']) if m['exclude_regex'] else '(none)'}",
        f"ignore_docs: {'yes' if m['ignore_docs'] else 'no'}",
        f"snippet_strategy: {m['snippet_strategy']}",
        f"snippet_context_lines: {m['snippet_context_lines']}",
    ]

    sections = ["\n".join(lines)]
    sections.append("=== TASK PROMPT ===\n" + payload["task_prompt"])
    sections.append("=== PROJECT TREE ===\n" + payload["project_tree"])

    fi_lines = []
    for x in payload["file_index"]:
        syms = ", ".join(x["symbols"]) if x["symbols"] else "-"
        fi_lines.append(f"- {x['path']} | {x['bytes']} bytes | {x['lines']} lines | symbols: {syms}")
    sections.append("=== FILE INDEX ===\n" + ("\n".join(fi_lines) if fi_lines else "(empty)"))

    if mode_cfg.include_snippets:
        sblocks = []
        for s in payload["snippets"]:
            sblocks.append(f"\n## FILE: {s['path']}\n```{s['lang']}\n{s['content']}\n```\n")
        sections.append("=== CODE SNIPPETS ===\n" + ("".join(sblocks).strip() if sblocks else "(budget exceeded or empty)"))

    if with_quality:
        q = payload["quality_report"]
        q_lines = [
            "=== QUALITY REPORT ===",
            f"candidate_files: {q['candidate_files']}",
            f"empty_or_unreadable: {q['empty_or_unreadable']}",
            f"filtered_by_include: {q['filtered_by_include']}",
            f"filtered_by_exclude: {q['filtered_by_exclude']}",
            f"indexed_files: {q['indexed_files']}",
            f"snippet_files: {q['snippet_files']}",
            f"snippet_truncated_files: {q['snippet_truncated_files']}",
            f"snippet_budget_truncated: {'yes' if q['snippet_budget_truncated'] else 'no'}",
        ]
        sections.append("\n".join(q_lines))

    result = "\n\n".join(sections)
    if len(result) > mode_cfg.max_total_chars:
        result = result[: mode_cfg.max_total_chars] + "\n\n...<global truncated>"
        payload["quality_report"]["global_truncated"] = True
    return result


def render_plain(payload: Dict, mode_cfg: ModeConfig, with_quality: bool) -> str:
    m = payload["meta"]
    out = []
    out.append("AI CONTEXT PACK")
    out.append(f"root={m['root']}")
    out.append(f"files_indexed={m['files_indexed']}")
    out.append(f"total_size_bytes={m['total_size_bytes']}")
    out.append(f"mode={m['mode']}")
    out.append(f"changed_only={m['changed_only']}")
    out.append(f"changed_from={m['changed_from']}")
    out.append(f"changed_commit_range={m['changed_commit_range']}")
    out.append(f"query={','.join(m['query']) if m['query'] else '(none)'}")
    out.append(f"query_regex={','.join(m['query_regex']) if m['query_regex'] else '(none)'}")
    out.append(f"exclude={','.join(m['exclude']) if m['exclude'] else '(none)'}")
    out.append(f"exclude_regex={','.join(m['exclude_regex']) if m['exclude_regex'] else '(none)'}")
    out.append(f"ignore_docs={m['ignore_docs']}")
    out.append("")
    out.append("TASK PROMPT")
    out.append(payload["task_prompt"])
    out.append("")
    out.append("PROJECT TREE")
    out.append(payload["project_tree"])
    out.append("")
    out.append("FILE INDEX")
    for x in payload["file_index"]:
        syms = ",".join(x["symbols"]) if x["symbols"] else "-"
        out.append(f"{x['path']} | {x['bytes']} bytes | {x['lines']} lines | symbols: {syms}")

    if mode_cfg.include_snippets:
        out.append("")
        out.append("CODE SNIPPETS")
        for s in payload["snippets"]:
            out.append(f"----- FILE: {s['path']} ({s['lang']}) -----")
            out.append(s["content"])
            out.append("----- END FILE -----")

    if with_quality:
        q = payload["quality_report"]
        out.append("")
        out.append("QUALITY REPORT")
        for k in [
            "candidate_files", "empty_or_unreadable", "filtered_by_include", "filtered_by_exclude", "filtered_by_docs",
            "indexed_files", "snippet_files", "snippet_truncated_files", "snippet_budget_truncated"
        ]:
            out.append(f"{k}={q[k]}")

    result = "\n".join(out)
    if len(result) > mode_cfg.max_total_chars:
        result = result[: mode_cfg.max_total_chars] + "\n...<global truncated>"
        payload["quality_report"]["global_truncated"] = True
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build AI context text from project files")
    p.add_argument("--root", default=".", help="Project root")
    p.add_argument("--mode", choices=["fast", "balanced", "deep"], default="balanced")
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


def main() -> int:
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

    files = collect_files(root, args.all, args.target, mode_cfg.max_files)

    changed_enabled = args.changed or bool(args.changed_from) or bool(args.changed_commit_range)
    if changed_enabled:
        changed = git_changed_files(root, args.changed_from or None, args.changed_commit_range or None)
        files = [f for f in files if f in changed]

    if not files:
        print("[aicp] 未找到可用的文本代码文件。")
        return 2

    ctx_lines = max(1, min(args.snippet_context_lines, 200))

    payload = build_payload(
        root=root,
        files=files,
        mode_cfg=mode_cfg,
        include_keywords=args.query,
        include_regex_patterns=args.query_regex,
        exclude_keywords=args.exclude,
        exclude_regex_patterns=args.exclude_regex,
        ignore_docs=args.ignore_docs,
        changed_only=changed_enabled,
        changed_from=args.changed_from,
        changed_commit_range=args.changed_commit_range,
        prompt=args.prompt,
        snippet_around_query=args.snippet_around_query,
        snippet_context_lines=ctx_lines,
    )

    if args.output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.output_format == "plain":
        out = render_plain(payload, mode_cfg, with_quality=args.quality_report)
    else:
        out = render_markdown(payload, mode_cfg, with_quality=args.quality_report)

    if "AI CONTEXT PACK" not in out:
        print("[aicp] 生成结果异常。")
        return 3

    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
