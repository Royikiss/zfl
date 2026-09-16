#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZFL Metadata Engine Module — Single Source of Truth for #? function metadata.

Handles parsing, alias canonicalization, type coercion, validation, and
zero-fork cache compilation for the ZFL framework.
"""

from __future__ import annotations

import os
import sys
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple, Union

# Canonical field names
FIELD_NAME = "name"
FIELD_DESC = "description"
FIELD_AUTHOR = "author"
FIELD_VERSION = "version"
FIELD_DEPS = "deps"
FIELD_USAGE = "usage"
FIELD_EXAMPLE = "example"
FIELD_PROTECTED = "protected"
FIELD_QUIET = "quiet"

# Multilingual Alias Mapping (Normalized lower-case keys -> canonical field)
ALIAS_MAP: Dict[str, str] = {
    # Name
    "name": FIELD_NAME,
    "名称": FIELD_NAME,
    # Description
    "description": FIELD_DESC,
    "desc": FIELD_DESC,
    "描述": FIELD_DESC,
    # Author
    "author": FIELD_AUTHOR,
    "作者": FIELD_AUTHOR,
    # Version
    "version": FIELD_VERSION,
    "版本": FIELD_VERSION,
    # Dependencies
    "deps": FIELD_DEPS,
    "dependencies": FIELD_DEPS,
    "依赖": FIELD_DEPS,
    "依赖项": FIELD_DEPS,
    # Usage
    "usage": FIELD_USAGE,
    "用法": FIELD_USAGE,
    # Example
    "example": FIELD_EXAMPLE,
    "示例": FIELD_EXAMPLE,
    # Protected
    "protected": FIELD_PROTECTED,
    "受保护": FIELD_PROTECTED,
    # Quiet / Lazy loading suppression
    "quiet": FIELD_QUIET,
    "lazy_quiet": FIELD_QUIET,
    "lazy_silent": FIELD_QUIET,
    "静默": FIELD_QUIET,
    "免提示": FIELD_QUIET,
}

# The 7 standard mandatory header fields required by ZFL
REQUIRED_FIELDS: Sequence[Tuple[str, str]] = (
    (FIELD_NAME, "name/名称"),
    (FIELD_DESC, "description/描述"),
    (FIELD_AUTHOR, "author/作者"),
    (FIELD_VERSION, "version/版本"),
    (FIELD_DEPS, "deps/依赖"),
    (FIELD_USAGE, "usage/用法"),
    (FIELD_EXAMPLE, "example/示例"),
)

TRUE_VALUES: Set[str] = {"true", "1", "yes", "on", "y", "是", "真"}
FALSE_VALUES: Set[str] = {"false", "0", "no", "off", "n", "否", "假"}


def parse_bool(val: Union[str, bool, None], default: bool = False) -> bool:
    """Coerce string or boolean value to strict bool."""
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    cleaned = str(val).strip().lower()
    if cleaned in TRUE_VALUES:
        return True
    if cleaned in FALSE_VALUES:
        return False
    return default


def parse_deps(val: Union[str, Sequence[str], None]) -> Tuple[str, ...]:
    """Tokenize dependency string (comma or whitespace separated) into clean tuple."""
    if not val:
        return ()
    if isinstance(val, (tuple, list)):
        return tuple(str(d).strip() for d in val if str(d).strip())

    cleaned = str(val).strip()
    if not cleaned:
        return ()
    # Replace commas with spaces, then split
    parts = cleaned.replace(",", " ").split()
    return tuple(p.strip() for p in parts if p.strip())


@dataclass(frozen=True)
class MetadataRecord:
    """Canonical, immutable representation of a function's parsed metadata."""
    name: str
    description: str
    author: str
    version: str
    deps: Tuple[str, ...]
    usage: str
    example: str
    is_protected: bool
    is_quiet: bool
    raw_fields: Dict[str, str] = field(default_factory=dict)
    declared_canonical_fields: Set[str] = field(default_factory=set)
    filepath: Optional[Path] = None

    def get(self, field_name: str, default: str = "") -> str:
        """Query canonical field or fallback."""
        if field_name == FIELD_NAME:
            return self.name
        if field_name in (FIELD_DESC, "desc"):
            return self.description
        if field_name == FIELD_AUTHOR:
            return self.author
        if field_name == FIELD_VERSION:
            return self.version
        if field_name == FIELD_DEPS:
            return ", ".join(self.deps)
        if field_name == FIELD_USAGE:
            return self.usage
        if field_name == FIELD_EXAMPLE:
            return self.example
        if field_name == FIELD_PROTECTED:
            return "true" if self.is_protected else "false"
        if field_name == FIELD_QUIET:
            return "true" if self.is_quiet else "false"
        return self.raw_fields.get(field_name, default)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str  # "error" or "warning"
    field: str
    message: str
    line_number: Optional[int] = None


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    record: MetadataRecord
    issues: Tuple[ValidationIssue, ...]

    @property
    def errors(self) -> Tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> Tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "warning")


def parse_string(content: str, filepath: Optional[Union[str, Path]] = None) -> MetadataRecord:
    """
    Parse metadata lines (#? ...) from script header content.
    Halts immediately upon encountering the first non-comment, non-blank line.
    """
    path_obj = Path(filepath) if filepath else None
    default_name = path_obj.stem if path_obj else ""

    raw_fields: Dict[str, str] = {}
    declared_canonical: Set[str] = set()

    for line in content.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        # Stop parsing metadata once we leave the header comment section
        if not trimmed.startswith("#"):
            break

        # Check for metadata line: #? key: val
        if trimmed.startswith("#?"):
            body = trimmed[2:].strip()
            if ":" in body:
                k, v = body.split(":", 1)
                k_clean = k.strip().lower()
                v_clean = v.strip()
                raw_fields[k.strip()] = v_clean

                canonical_k = ALIAS_MAP.get(k_clean)
                if canonical_k:
                    declared_canonical.add(canonical_k)
                    # Also store with canonical name
                    raw_fields[canonical_k] = v_clean

    name = raw_fields.get(FIELD_NAME, "").strip() or default_name
    description = raw_fields.get(FIELD_DESC, "").strip()
    author = raw_fields.get(FIELD_AUTHOR, "").strip()
    version = raw_fields.get(FIELD_VERSION, "").strip() or "1.0.0"
    deps = parse_deps(raw_fields.get(FIELD_DEPS, ""))
    usage = raw_fields.get(FIELD_USAGE, "").strip()
    example = raw_fields.get(FIELD_EXAMPLE, "").strip()
    is_protected = parse_bool(raw_fields.get(FIELD_PROTECTED), default=False)
    is_quiet = parse_bool(raw_fields.get(FIELD_QUIET), default=False)

    return MetadataRecord(
        name=name,
        description=description,
        author=author,
        version=version,
        deps=deps,
        usage=usage,
        example=example,
        is_protected=is_protected,
        is_quiet=is_quiet,
        raw_fields=raw_fields,
        declared_canonical_fields=declared_canonical,
        filepath=path_obj,
    )


def load(target: Union[str, Path], workspace_root: Optional[Path] = None) -> MetadataRecord:
    """
    Load and parse a metadata record from a file path or function name.
    """
    path = Path(target)
    if not path.is_file():
        # Treat as function name, search in workspace functions directories
        root = workspace_root or get_workspace_root()
        candidate = root / "functions" / f"{target}.zsh"
        if candidate.is_file():
            path = candidate
        else:
            candidate_custom = root / "custom_functions" / f"{target}.zsh"
            if candidate_custom.is_file():
                path = candidate_custom
            else:
                raise FileNotFoundError(f"Metadata file for function '{target}' not found.")

    content = path.read_text(encoding="utf-8", errors="replace")
    return parse_string(content, filepath=path)


def get_workspace_root() -> Path:
    """Resolve ZFL_HOME or directory relative to this script."""
    env_home = os.environ.get("ZFL_HOME")
    if env_home and os.path.isdir(env_home):
        return Path(env_home).resolve()
    # python/metadata_engine.py -> workspace root is parent
    return Path(__file__).resolve().parent.parent


def load_all(workspace_root: Optional[Path] = None) -> Dict[str, MetadataRecord]:
    """
    Scan all .zsh files in functions/ and custom_functions/ and parse their metadata.
    """
    root = workspace_root or get_workspace_root()
    records: Dict[str, MetadataRecord] = {}

    for dirname in ("functions", "custom_functions"):
        target_dir = root / dirname
        if not target_dir.is_dir():
            continue
        for entry in sorted(target_dir.glob("*.zsh")):
            if entry.is_file():
                try:
                    rec = load(entry, workspace_root=root)
                    records[rec.name] = rec
                except Exception:
                    pass
    return records


def validate(target: Union[str, Path, MetadataRecord], is_zh: bool = True) -> ValidationResult:
    """
    Validate metadata against ZFL standards:
    1. Check presence of 7 required fields.
    2. Check 1:1 mapping between filename and function name.
    """
    if isinstance(target, MetadataRecord):
        rec = target
    else:
        rec = load(target)

    issues: List[ValidationIssue] = []

    # 1. Check required fields
    missing_fields = []
    for canonical_name, label in REQUIRED_FIELDS:
        if canonical_name not in rec.declared_canonical_fields:
            missing_fields.append(label)

    if missing_fields:
        if is_zh:
            msg = f"文件头部 #? 规范注释未显式写全，缺少字段: {', '.join(missing_fields)}"
        else:
            msg = f"File header #? metadata must be explicitly written in full. Missing: {', '.join(missing_fields)}"
        issues.append(ValidationIssue(severity="warning", field="headers", message=msg))

    # 2. Check 1:1 filename mapping if filepath is available
    if rec.filepath:
        expected_name = rec.filepath.stem
        if rec.name != expected_name:
            if is_zh:
                msg = f"元数据中的名称 '{rec.name}' 与文件名 '{expected_name}.zsh' 不匹配。"
            else:
                msg = f"Metadata name '{rec.name}' does not match file stem '{expected_name}'."
            issues.append(ValidationIssue(severity="error", field=FIELD_NAME, message=msg))

    is_valid = len(issues) == 0
    return ValidationResult(is_valid=is_valid, record=rec, issues=tuple(issues))


def get_default_cache_path() -> Path:
    """Determine default cache path: ~/.cache/zsh/metadata.zsh"""
    cache_home = os.environ.get("XDG_CACHE_HOME")
    if cache_home:
        base = Path(cache_home)
    else:
        base = Path.home() / ".cache"
    return base / "zsh" / "metadata.zsh"


def escape_zsh_single_quote(s: str) -> str:
    """Safely escape single quotes for Zsh single-quoted literals: ' -> '\\''"""
    return s.replace("'", "'\\''")


def compile_cache(output_file: Optional[Path] = None, workspace_root: Optional[Path] = None) -> Path:
    """
    Compile all functions metadata into an optimized Zsh associative array script.
    Performs atomic write via a temporary file to avoid half-read states.
    """
    out_path = output_file or get_default_cache_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    root = workspace_root or get_workspace_root()
    records = load_all(root)

    lines: List[str] = [
        "# Auto-generated by ZFL Metadata Engine. DO NOT EDIT DIRECTLY.",
        "# Timestamp: " + str(Path(__file__).stat().st_mtime),
        "",
        "typeset -gA ZFL_META_NAMES",
        "typeset -gA ZFL_META_DESC",
        "typeset -gA ZFL_META_AUTHOR",
        "typeset -gA ZFL_META_VERSION",
        "typeset -gA ZFL_META_DEPS",
        "typeset -gA ZFL_META_USAGE",
        "typeset -gA ZFL_META_EXAMPLE",
        "typeset -gA ZFL_META_PROTECTED",
        "typeset -gA ZFL_META_QUIET",
        "typeset -gA ZFL_META_FILE",
        "typeset -gA ZFL_META_SOURCE",
        "typeset -gA ZFL_META_VALID",
        "typeset -gA ZFL_META_WARNINGS",
        "typeset -gA ZFL_META_ERRORS",
        "",
    ]

    for name, rec in sorted(records.items()):
        source_type = "builtin"
        if rec.filepath and "custom_functions" in str(rec.filepath):
            source_type = "custom"

        val_res = validate(rec, is_zh=True)
        is_val = "1" if val_res.is_valid else "0"
        warn_str = escape_zsh_single_quote("; ".join(w.message for w in val_res.warnings))
        err_str = escape_zsh_single_quote("; ".join(e.message for e in val_res.errors))

        f_name = escape_zsh_single_quote(rec.name)
        f_desc = escape_zsh_single_quote(rec.description)
        f_auth = escape_zsh_single_quote(rec.author)
        f_ver = escape_zsh_single_quote(rec.version)
        f_deps = escape_zsh_single_quote(" ".join(rec.deps))
        f_usage = escape_zsh_single_quote(rec.usage)
        f_example = escape_zsh_single_quote(rec.example)
        f_prot = "1" if rec.is_protected else "0"
        f_quiet = "1" if rec.is_quiet else "0"
        f_file = escape_zsh_single_quote(str(rec.filepath) if rec.filepath else "")

        lines.append(f"ZFL_META_NAMES[{f_name}]='{f_name}'")
        lines.append(f"ZFL_META_DESC[{f_name}]='{f_desc}'")
        lines.append(f"ZFL_META_AUTHOR[{f_name}]='{f_auth}'")
        lines.append(f"ZFL_META_VERSION[{f_name}]='{f_ver}'")
        lines.append(f"ZFL_META_DEPS[{f_name}]='{f_deps}'")
        lines.append(f"ZFL_META_USAGE[{f_name}]='{f_usage}'")
        lines.append(f"ZFL_META_EXAMPLE[{f_name}]='{f_example}'")
        lines.append(f"ZFL_META_PROTECTED[{f_name}]='{f_prot}'")
        lines.append(f"ZFL_META_QUIET[{f_name}]='{f_quiet}'")
        lines.append(f"ZFL_META_FILE[{f_name}]='{f_file}'")
        lines.append(f"ZFL_META_SOURCE[{f_name}]='{source_type}'")
        lines.append(f"ZFL_META_VALID[{f_name}]='{is_val}'")
        lines.append(f"ZFL_META_WARNINGS[{f_name}]='{warn_str}'")
        lines.append(f"ZFL_META_ERRORS[{f_name}]='{err_str}'")
        lines.append("")

    content = "\n".join(lines) + "\n"

    # Atomic write
    temp_dir = out_path.parent
    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
        tf.write(content)
        temp_name = tf.name

    os.replace(temp_name, out_path)
    return out_path


# --- CLI Interface for tooling & scripts ---

def _cli() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="ZFL Metadata Engine CLI")
    subparsers = parser.add_subparsers(dest="command")

    # compile
    compile_p = subparsers.add_parser("compile", help="Compile metadata cache for Zsh runtime")
    compile_p.add_argument("--output", "-o", type=Path, default=None, help="Target cache file path")

    # validate
    val_p = subparsers.add_parser("validate", help="Validate function header metadata")
    val_p.add_argument("targets", nargs="*", help="File paths or function names to validate")

    # info
    info_p = subparsers.add_parser("info", help="Display metadata for a function")
    info_p.add_argument("name", help="Function name or path")

    # list
    subparsers.add_parser("list", help="List all functions with metadata")

    args = parser.parse_args()

    if args.command == "compile":
        out = compile_cache(args.output)
        print(f"[metadata_engine] Compiled cache successfully to: {out}")
        return 0

    if args.command == "validate":
        targets = args.targets
        if not targets:
            records = load_all()
            targets = list(records.keys())
        any_err = False
        for t in targets:
            try:
                res = validate(t)
                status = "✓" if res.is_valid else "!"
                print(f"[{status}] {t}")
                for issue in res.issues:
                    print(f"    └─ [{issue.severity.upper()}] {issue.message}")
                if not res.is_valid:
                    any_err = True
            except Exception as e:
                print(f"[✗] {t}: {e}")
                any_err = True
        return 1 if any_err else 0

    if args.command == "info":
        rec = load(args.name)
        print(f"Name:        {rec.name}")
        print(f"Description: {rec.description}")
        print(f"Author:      {rec.author}")
        print(f"Version:     {rec.version}")
        print(f"Quiet:       {rec.is_quiet}")
        print(f"Protected:   {rec.is_protected}")
        print(f"Deps:        {', '.join(rec.deps) or 'None'}")
        print(f"Usage:       {rec.usage}")
        print(f"Example:     {rec.example}")
        print(f"Path:        {rec.filepath}")
        return 0

    if args.command == "list":
        records = load_all()
        print(f"Found {len(records)} functions:")
        for name, rec in sorted(records.items()):
            prot = " [P]" if rec.is_protected else ""
            quiet = " [Q]" if rec.is_quiet else ""
            print(f"  {name:20s}{prot}{quiet} {rec.description}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
