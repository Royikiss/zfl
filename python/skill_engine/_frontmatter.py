"""Unified YAML frontmatter parser for SKILL.md files."""

import os
import re


def parse_yaml_frontmatter(file_path):
    """Extract frontmatter dictionary from a SKILL.md file.

    Handles standard YAML frontmatter between --- markers,
    multi-line values, list items, quoted values, and
    description blockquote markers.

    Returns a dict with keys like 'name', 'description', etc.
    Returns empty dict if file doesn't exist or has no frontmatter.
    """
    if not os.path.isfile(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(4096)
    except Exception:
        return {}

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}

    meta = {}
    current_key = None
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Continuation line (indented)
        if (line.startswith(" ") or line.startswith("\t")) and current_key:
            val = stripped
            if val.startswith("-"):
                meta[current_key] += "\n" + val
            else:
                meta[current_key] += " " + val
            continue

        # New key-value pair
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k:
                current_key = k
                meta[k] = v

    # Clean up description blockquote markers
    if "description" in meta:
        desc = meta["description"]
        if desc.startswith(">"):
            desc = desc[1:]
        desc = desc.replace("\n> ", "\n").replace("\n>", "\n").strip()
        meta["description"] = desc

    return meta
