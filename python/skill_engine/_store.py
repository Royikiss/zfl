"""Shared storage, persistence, and data directory management for the skill engine."""

import os
import sys
import json
import shutil

SKILLS_DIR = os.path.expanduser("~/.agents/skills")


def get_zfl_data_dir():
    """Resolve ZFL data directory with legacy migration support."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        base = os.path.join(xdg_data, "zfl")
    else:
        base = os.path.expanduser("~/.local/share/zfl")
    os.makedirs(base, exist_ok=True)

    # Auto-migration from legacy ~/.cache/zsh
    legacy_cache = os.path.expanduser("~/.cache/zsh")
    if os.path.exists(legacy_cache):
        for item in ["skills_groups.json", "skills_zh.json", "skills_manifest.json", "skill_sources"]:
            old_p = os.path.join(legacy_cache, item)
            new_p = os.path.join(base, item)
            if os.path.exists(old_p) and not os.path.exists(new_p):
                try:
                    if os.path.isdir(old_p):
                        shutil.copytree(old_p, new_p)
                    else:
                        shutil.copy2(old_p, new_p)
                except Exception:
                    pass
    return base


DATA_DIR = get_zfl_data_dir()
SOURCES_DIR = os.path.join(DATA_DIR, "skill_sources")
MANIFEST_FILE = os.path.join(DATA_DIR, "skills_manifest.json")
GROUPS_FILE = os.path.join(DATA_DIR, "skills_groups.json")
TRANSLATIONS_FILE = os.path.join(DATA_DIR, "skills_zh.json")


def atomic_save_json(file_path, data):
    """Atomically save data as JSON using a temporary file and os.replace."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        tmp_path = f"{file_path}.tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, file_path)
        return True
    except Exception as e:
        from ._display import c_print
        c_print("1;31", f"Error saving {file_path}: {e}", file=sys.stderr)
        return False


def load_manifest():
    """Load skills manifest mapping skill_name to repository metadata."""
    if not os.path.exists(MANIFEST_FILE):
        return {}
    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_manifest(manifest):
    """Save skills manifest atomically."""
    return atomic_save_json(MANIFEST_FILE, manifest)


def load_groups():
    """Load group configurations from skills_groups.json."""
    if not os.path.exists(GROUPS_FILE):
        return {}
    try:
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_groups(groups):
    """Save group configurations to skills_groups.json atomically."""
    return atomic_save_json(GROUPS_FILE, groups)


def safe_input(prompt_msg=""):
    """Safely print prompt and read input avoiding readline backspace glitches."""
    if prompt_msg:
        sys.stdout.write(f"{prompt_msg}\n")
        sys.stdout.flush()
    try:
        return input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""
