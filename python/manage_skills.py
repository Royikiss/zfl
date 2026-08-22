#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Description: Core management engine for AI Agent skills (Install, Discover, Package, Update, Status)

import os
import sys
import json
import re
import shutil
import subprocess
import urllib.parse
from datetime import datetime

# Environment & Language
LANG = os.environ.get("ZFL_LANG") or os.environ.get("LANG", "en")
IS_ZH = LANG.startswith("zh")

SKILLS_DIR = os.path.expanduser("~/.agents/skills")

def get_zfl_data_dir():
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

def c_print(color_code, msg, file=sys.stdout):
    """Print message with ANSI color codes."""
    if hasattr(file, 'isatty') and file.isatty():
        file.write(f"\033[{color_code}m{msg}\033[0m\n")
    else:
        file.write(f"{msg}\n")
    file.flush()

def safe_input(prompt_msg=""):
    """Safely print prompt and read input avoiding readline backspace glitches."""
    if prompt_msg:
        sys.stdout.write(f"{prompt_msg}\n")
        sys.stdout.flush()
    try:
        return input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""

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
    """Save skills manifest."""
    try:
        os.makedirs(os.path.dirname(MANIFEST_FILE), exist_ok=True)
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        c_print("1;31", f"Error saving manifest: {e}", file=sys.stderr)
        return False

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
    """Save group configurations to skills_groups.json."""
    try:
        os.makedirs(os.path.dirname(GROUPS_FILE), exist_ok=True)
        with open(GROUPS_FILE, "w", encoding="utf-8") as f:
            json.dump(groups, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        c_print("1;31", f"Error saving groups: {e}", file=sys.stderr)
        return False


def parse_yaml_frontmatter(file_path):
    """Extract frontmatter dictionary from SKILL.md."""
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
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k:
                meta[k] = v
    return meta

def parse_repo_target(raw_input):
    """
    Parse various GitHub / Git URL formats into (repo_url, branch, subpath, cache_repo_name).
    Examples:
    - owner/repo -> https://github.com/owner/repo.git
    - https://github.com/owner/repo
    - https://github.com/owner/repo/tree/main/skills/my-skill
    - git@github.com:owner/repo.git
    """
    raw = raw_input.strip()
    if not raw:
        return None

    # Case 1: https://github.com/owner/repo/tree/branch/subpath...
    tree_match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/?(.*)$", raw)
    if tree_match:
        owner, repo, branch, subpath = tree_match.groups()
        repo = repo.removesuffix(".git")
        repo_url = f"https://github.com/{owner}/{repo}.git"
        cache_name = f"{owner}__{repo}"
        return {
            "repo_url": repo_url,
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "subpath": subpath.rstrip("/"),
            "cache_name": cache_name
        }

    # Case 2: Standard GitHub HTTPS or SSH
    http_match = re.match(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git|/)?$", raw)
    if http_match:
        owner, repo = http_match.groups()
        repo = repo.removesuffix(".git")
        return {
            "repo_url": f"https://github.com/{owner}/{repo}.git",
            "owner": owner,
            "repo": repo,
            "branch": None,
            "subpath": "",
            "cache_name": f"{owner}__{repo}"
        }

    ssh_match = re.match(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", raw)
    if ssh_match:
        owner, repo = ssh_match.groups()
        return {
            "repo_url": f"git@github.com:{owner}/{repo}.git",
            "owner": owner,
            "repo": repo,
            "branch": None,
            "subpath": "",
            "cache_name": f"{owner}__{repo}"
        }

    # Case 3: Shorthand owner/repo
    shorthand_match = re.match(r"^([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)$", raw)
    if shorthand_match:
        owner, repo = shorthand_match.groups()
        repo = repo.removesuffix(".git")
        return {
            "repo_url": f"https://github.com/{owner}/{repo}.git",
            "owner": owner,
            "repo": repo,
            "branch": None,
            "subpath": "",
            "cache_name": f"{owner}__{repo}"
        }

    # Fallback generic Git URL
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw)
    return {
        "repo_url": raw,
        "owner": "custom",
        "repo": safe_name,
        "branch": None,
        "subpath": "",
        "cache_name": safe_name
    }

def clone_or_fetch_repo(target_info):
    """
    Clone or fetch remote repository into ~/.cache/zsh/skill_sources/<cache_name>.
    Returns the local repository directory path or None on failure.
    """
    os.makedirs(SOURCES_DIR, exist_ok=True)
    cache_dir = os.path.join(SOURCES_DIR, target_info["cache_name"])
    repo_url = target_info["repo_url"]
    branch = target_info.get("branch")

    if not os.path.exists(os.path.join(cache_dir, ".git")):
        if IS_ZH:
            c_print("1;34", f"==> 正在克隆源仓库: {repo_url} ...")
        else:
            c_print("1;34", f"==> Cloning source repository: {repo_url} ...")
        
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["-b", branch])
        cmd.extend([repo_url, cache_dir])

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            c_print("1;31", f"Git clone failed:\n{res.stderr.strip()}", file=sys.stderr)
            return None
    else:
        if IS_ZH:
            c_print("1;34", f"==> 正在拉取源仓库最新变更: {target_info['cache_name']} ...")
        else:
            c_print("1;34", f"==> Fetching latest changes for: {target_info['cache_name']} ...")
        
        # Reset any local state in cache
        subprocess.run(["git", "-C", cache_dir, "reset", "--hard", "HEAD"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        cmd = ["git", "-C", cache_dir, "pull", "--ff-only"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            # Fallback to fetch origin
            subprocess.run(["git", "-C", cache_dir, "fetch", "--depth", "1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return cache_dir

def get_repo_head_commit(repo_dir):
    """Get the current HEAD commit hash of a git repository."""
    try:
        res = subprocess.run(["git", "-C", repo_dir, "rev-parse", "HEAD"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"

def get_repo_remote_commit(repo_dir, branch="HEAD"):
    """Get remote latest commit hash."""
    try:
        res = subprocess.run(["git", "-C", repo_dir, "rev-parse", f"origin/{branch}"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        # Fallback to HEAD
        return get_repo_head_commit(repo_dir)
    except Exception:
        return "unknown"

def scan_skills_in_dir(root_dir, limit_subpath=""):
    """
    Recursively scan root_dir (optionally restricted to limit_subpath) for all SKILL.md files.
    Returns a list of dicts with skill metadata and directory boundaries.
    """
    search_root = os.path.join(root_dir, limit_subpath) if limit_subpath else root_dir
    if not os.path.exists(search_root):
        return []

    discovered = []
    # If the search_root itself directly contains SKILL.md
    for dirpath, dirnames, filenames in os.walk(search_root):
        # Ignore hidden directories like .git
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        
        skill_file = None
        for f in filenames:
            if f.lower() == "skill.md":
                skill_file = os.path.join(dirpath, f)
                break

        if skill_file:
            rel_dir = os.path.relpath(dirpath, root_dir)
            if rel_dir == ".":
                rel_dir = ""
            
            frontmatter = parse_yaml_frontmatter(skill_file)
            fallback_name = os.path.basename(dirpath)
            if not fallback_name or fallback_name == os.path.basename(root_dir):
                fallback_name = frontmatter.get("name") or os.path.basename(root_dir)

            skill_name = frontmatter.get("name") or fallback_name
            skill_name = re.sub(r"[^a-zA-Z0-9_\-]", "-", skill_name.strip()).strip("-").lower()
            if not skill_name:
                skill_name = fallback_name.lower()

            desc = frontmatter.get("description") or ""

            # Count packaged files and subdirectories
            total_files = sum([len(files) for _, _, files in os.walk(dirpath)])
            has_scripts = os.path.isdir(os.path.join(dirpath, "scripts"))
            has_refs = os.path.isdir(os.path.join(dirpath, "references"))

            discovered.append({
                "name": skill_name,
                "dir_path": dirpath,
                "rel_subpath": rel_dir,
                "description": desc,
                "file_count": total_files,
                "has_scripts": has_scripts,
                "has_refs": has_refs
            })

    # Sort by subpath depth and name
    discovered.sort(key=lambda x: (x["rel_subpath"].count(os.sep), x["name"]))
    return discovered

def copy_skill_bundle(src_dir, dest_dir):
    """
    Safely and cleanly copy all contents of src_dir to dest_dir.
    Ensures complete packaging of scripts, references, etc.
    """
    os.makedirs(dest_dir, exist_ok=True)
    # Clear old files in destination directory to prevent stale files
    for item in os.listdir(dest_dir):
        item_path = os.path.join(dest_dir, item)
        if os.path.islink(item_path) or os.path.isfile(item_path):
            os.unlink(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

    # Copy tree
    for item in os.listdir(src_dir):
        if item.startswith(".git"):
            continue
        s = os.path.join(src_dir, item)
        d = os.path.join(dest_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=True, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

def prompt_auto_group_skills(installed_skill_names, target_info):
    """
    Prompt user whether to create an automatic skill group for multiple installed skills.
    """
    if len(installed_skill_names) <= 1:
        return

    print("\033[1;36m" + "=" * 60 + "\033[0m")
    if IS_ZH:
        c_print("1;35", f"💡 检测到本次共安装/更新了 {len(installed_skill_names)} 个技能：")
        for idx, sname in enumerate(installed_skill_names, 1):
            print(f"   {idx}) {sname}")
        ans = safe_input("是否将这些技能自动创建为一个新的技能分组，以便日后一键引用？(y/N):")
    else:
        c_print("1;35", f"💡 Detected {len(installed_skill_names)} skills installed/updated:")
        for idx, sname in enumerate(installed_skill_names, 1):
            print(f"   {idx}) {sname}")
        ans = safe_input("Would you like to create a skill group for these skills for easy batch reference? (y/N):")

    if ans.lower() not in ("y", "yes"):
        return

    # Derive default group name
    raw_default = target_info.get("repo") or target_info.get("cache_name") or ""
    default_gname = re.sub(r"[^a-zA-Z0-9_\-]", "-", raw_default.strip()).strip("-").lower()
    if not default_gname:
        default_gname = "my-group"

    if IS_ZH:
        gname_prompt = f"请输入分组名称 (直接回车使用默认: '{default_gname}', 或输入 'q' 取消):"
    else:
        gname_prompt = f"Please enter group name (Press Enter for default: '{default_gname}', or 'q' to cancel):"

    gname = safe_input(gname_prompt)
    if gname.lower() == 'q':
        return
    if not gname:
        gname = default_gname

    gname = re.sub(r"[^a-zA-Z0-9_\-]", "-", gname.strip()).strip("-").lower()
    if not gname:
        gname = default_gname

    if IS_ZH:
        ordered_ans = safe_input("是否设为有序分组（即按推荐顺序调用）？(y/N):").lower()
    else:
        ordered_ans = safe_input("Mark as ordered group (recommended call order)? (y/N):").lower()
    is_ordered = ordered_ans in ("y", "yes")

    groups = load_groups()
    disp_name = gname
    if gname in groups and isinstance(groups[gname], dict):
        disp_name = groups[gname].get("name", gname)

    groups[gname] = {
        "name": disp_name,
        "ordered": is_ordered,
        "skills": installed_skill_names
    }

    if save_groups(groups):
        ordered_label = ("有序" if IS_ZH else "ordered") if is_ordered else ("无序" if IS_ZH else "unordered")
        if IS_ZH:
            c_print("1;32", f"\n[✓] 成功创建/更新{ordered_label}技能分组 '{gname}' (包含 {len(installed_skill_names)} 个技能)！")
            c_print("0;33", f"💡 提示: 下次在任何项目根目录下直接运行 'mskill {gname}' 即可一键链接整组技能。")
        else:
            c_print("1;32", f"\n[✓] Successfully saved {ordered_label} skill group '{gname}' ({len(installed_skill_names)} skills)!")
            c_print("0;33", f"💡 Tip: Run 'mskill {gname}' in any project root to link all skills in this group at once.")
    else:
        if IS_ZH:
            c_print("1;31", "保存技能分组失败。", file=sys.stderr)
        else:
            c_print("1;31", "Failed to save skill group.", file=sys.stderr)
    print("\033[1;36m" + "=" * 60 + "\033[0m")

def install_skills_workflow(repo_input, specific_skills=None, branch=None, force=False):

    """Full workflow to install one or more skills from a repository source."""
    target_info = parse_repo_target(repo_input)
    if not target_info:
        c_print("1;31", f"Error: Invalid repository URL or shorthand '{repo_input}'", file=sys.stderr)
        return 1

    if branch:
        target_info["branch"] = branch

    cache_dir = clone_or_fetch_repo(target_info)
    if not cache_dir:
        return 1

    commit_hash = get_repo_head_commit(cache_dir)
    discovered = scan_skills_in_dir(cache_dir, target_info.get("subpath", ""))

    if not discovered:
        if IS_ZH:
            c_print("1;31", f"错误: 在目标仓库路径下未发现任何包含 SKILL.md 的技能包！", file=sys.stderr)
        else:
            c_print("1;31", f"Error: No valid skill packages with SKILL.md found in repository!", file=sys.stderr)
        return 1

    selected_skills = []
    if specific_skills:
        # Match requested skill names
        name_map = {item["name"].lower(): item for item in discovered}
        for req in specific_skills:
            req_l = req.lower()
            if req_l in name_map:
                selected_skills.append(name_map[req_l])
            else:
                # Try matching by subpath
                matched = [item for item in discovered if os.path.basename(item["rel_subpath"]).lower() == req_l]
                if matched:
                    selected_skills.extend(matched)
                else:
                    if IS_ZH:
                        c_print("1;33", f"警告: 仓库中未找到技能 '{req}'，已跳过。")
                    else:
                        c_print("1;33", f"Warning: Skill '{req}' not found in repository, skipped.")
    elif len(discovered) == 1:
        # Single skill repository -> install directly
        selected_skills = [discovered[0]]
    else:
        # Multi-skill repository -> interactive selection
        if IS_ZH:
            print("\033[1;36m" + "=" * 60 + "\033[0m")
            print(f"\033[1;32m在仓库中检测到 {len(discovered)} 个可用技能：\033[0m")
        else:
            print("\033[1;36m" + "=" * 60 + "\033[0m")
            print(f"\033[1;32mFound {len(discovered)} available skills in repository:\033[0m")
        
        for idx, item in enumerate(discovered, 1):
            scripts_flag = " [scripts]" if item["has_scripts"] else ""
            refs_flag = " [refs]" if item["has_refs"] else ""
            desc = item["description"]
            if len(desc) > 40:
                desc = desc[:37] + "..."
            print(f"  {idx}) \033[1;33m{item['name']}\033[0m ({item['file_count']} files{scripts_flag}{refs_flag}) - {desc}")
        print("\033[1;36m" + "=" * 60 + "\033[0m")

        if IS_ZH:
            ans = safe_input("请输入要安装的技能序号（如 '1 3'，输入 'all' 安装全部，直接回车取消）:")
        else:
            ans = safe_input("Enter indices to install (e.g. '1 3', 'all' for all, Enter to cancel):")

        if not ans:
            if IS_ZH:
                c_print("1;33", "操作已取消。")
            else:
                c_print("1;33", "Operation cancelled.")
            return 0

        if ans.strip().lower() == "all":
            selected_skills = discovered
        else:
            try:
                indices = [int(x) - 1 for x in ans.split()]
                for i in indices:
                    if 0 <= i < len(discovered):
                        selected_skills.append(discovered[i])
            except ValueError:
                c_print("1;31", "Invalid input.", file=sys.stderr)
                return 1

    if not selected_skills:
        c_print("1;33", "No skills selected for installation.")
        return 0

    manifest = load_manifest()
    os.makedirs(SKILLS_DIR, exist_ok=True)

    installed_count = 0
    for skill_info in selected_skills:
        s_name = skill_info["name"]
        dest_path = os.path.join(SKILLS_DIR, s_name)

        if os.path.exists(dest_path) and not force:
            if IS_ZH:
                c_print("1;33", f"[*] 技能 '{s_name}' 已存在于 ~/.agents/skills/，正在覆盖更新...")
            else:
                c_print("1;33", f"[*] Skill '{s_name}' already exists in ~/.agents/skills/, updating...")

        copy_skill_bundle(skill_info["dir_path"], dest_path)

        # Update manifest record
        manifest[s_name] = {
            "repo_url": target_info["repo_url"],
            "owner": target_info.get("owner", ""),
            "repo": target_info.get("repo", ""),
            "branch": target_info.get("branch") or "HEAD",
            "subpath": skill_info["rel_subpath"],
            "commit_hash": commit_hash,
            "installed_at": datetime.now().isoformat(),
            "cache_name": target_info["cache_name"]
        }
        installed_count += 1

        extras = []
        if skill_info["has_scripts"]:
            extras.append("scripts")
        if skill_info["has_refs"]:
            extras.append("references")
        extras_str = f" (packaged: {', '.join(extras)})" if extras else ""

        if IS_ZH:
            c_print("1;32", f"[✓] 成功安装技能: {s_name}{extras_str} -> ~/.agents/skills/{s_name}")
        else:
            c_print("1;32", f"[✓] Successfully installed: {s_name}{extras_str} -> ~/.agents/skills/{s_name}")

    save_manifest(manifest)
    if IS_ZH:
        c_print("1;32", f"\n完成！已成功安装/更新 {installed_count} 个技能。")
    else:
        c_print("1;32", f"\nDone! Successfully installed/updated {installed_count} skill(s).")

    # Prompt auto-grouping if multiple skills were installed
    if len(selected_skills) > 1:
        installed_names = [s["name"] for s in selected_skills]
        prompt_auto_group_skills(installed_names, target_info)

    return 0

def update_skills_workflow(target_skills=None, update_all=False):
    """
    Update installed skills using metadata stored in manifest.
    CRITICAL: Does NOT touch ~/.cache/zsh/skills_groups.json, ensuring all groups remain intact.
    """
    manifest = load_manifest()
    if not manifest:
        if IS_ZH:
            c_print("1;33", "提示: 当前没有通过 mskill 追踪安装的技能记录（或 manifest 为空）。")
            c_print("0", "如需管理现有本地技能，您可以重新执行 'mskill -i <repo>' 关联源。")
        else:
            c_print("1;33", "Notice: No skills currently tracked in manifest.")
            c_print("0", "You can install or re-link sources using 'mskill -i <repo>'.")
        return 0

    skills_to_update = []
    if update_all or not target_skills:
        skills_to_update = list(manifest.keys())
    else:
        for req in target_skills:
            if req in manifest:
                skills_to_update.append(req)
            else:
                if IS_ZH:
                    c_print("1;33", f"警告: 技能 '{req}' 没有可追溯的远程源仓库记录，已跳过。")
                else:
                    c_print("1;33", f"Warning: Skill '{req}' has no tracked source in manifest, skipped.")

    if not skills_to_update:
        return 0

    # Group skills by source repository cache to minimize git network operations
    repos_map = {}
    for s_name in skills_to_update:
        meta = manifest[s_name]
        c_name = meta.get("cache_name") or f"{meta.get('owner')}__{meta.get('repo')}"
        if c_name not in repos_map:
            repos_map[c_name] = {
                "meta": meta,
                "skills": []
            }
        repos_map[c_name]["skills"].append(s_name)

    updated_count = 0
    up_to_date_count = 0

    for c_name, item in repos_map.items():
        meta = item["meta"]
        repo_url = meta["repo_url"]
        branch = meta.get("branch") or "HEAD"
        cache_dir = os.path.join(SOURCES_DIR, c_name)

        target_info = {
            "repo_url": repo_url,
            "cache_name": c_name,
            "branch": branch if branch != "HEAD" else None
        }

        cache_dir = clone_or_fetch_repo(target_info)
        if not cache_dir:
            continue

        latest_commit = get_repo_head_commit(cache_dir)
        discovered = scan_skills_in_dir(cache_dir)
        discovered_by_subpath = {d["rel_subpath"]: d for d in discovered}
        discovered_by_name = {d["name"]: d for d in discovered}

        for s_name in item["skills"]:
            curr_meta = manifest[s_name]
            recorded_commit = curr_meta.get("commit_hash", "")
            subpath = curr_meta.get("subpath", "")

            # Locate the updated skill bundle in source repo
            skill_info = discovered_by_subpath.get(subpath) or discovered_by_name.get(s_name)
            if not skill_info:
                if IS_ZH:
                    c_print("1;31", f"[x] 更新失败: 源仓库中未能找到技能 '{s_name}' (路径: '{subpath}')。")
                else:
                    c_print("1;31", f"[x] Update failed: Skill '{s_name}' not found in source repo at '{subpath}'.")
                continue

            dest_path = os.path.join(SKILLS_DIR, s_name)
            if recorded_commit == latest_commit and os.path.exists(dest_path):
                up_to_date_count += 1
                if IS_ZH:
                    c_print("0;32", f"[=] 技能 '{s_name}' 已是最新版本 ({latest_commit[:7]})")
                else:
                    c_print("0;32", f"[=] Skill '{s_name}' is already up-to-date ({latest_commit[:7]})")
            else:
                # Copy updated bundle
                copy_skill_bundle(skill_info["dir_path"], dest_path)
                curr_meta["commit_hash"] = latest_commit
                curr_meta["updated_at"] = datetime.now().isoformat()
                updated_count += 1
                if IS_ZH:
                    c_print("1;32", f"[✓] 成功更新技能 '{s_name}' ({recorded_commit[:7]} -> {latest_commit[:7]})")
                else:
                    c_print("1;32", f"[✓] Successfully updated '{s_name}' ({recorded_commit[:7]} -> {latest_commit[:7]})")

    save_manifest(manifest)
    if IS_ZH:
        print("\033[1;36m" + "=" * 50 + "\033[0m")
        c_print("1;32", f"更新完成: {updated_count} 个已更新，{up_to_date_count} 个已是最新。")
        c_print("0;33", "提示: 所有技能分组配置已完整保留，项目端软链接即时同步生效。")
    else:
        print("\033[1;36m" + "=" * 50 + "\033[0m")
        c_print("1;32", f"Update complete: {updated_count} updated, {up_to_date_count} already up-to-date.")
        c_print("0;33", "Notice: All skill groups preserved intact, symlinks updated automatically.")
    return 0

def strip_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*m', '', s)

def clean_item_id(s):
    if not s:
        return ""
    s_clean = strip_ansi(s)
    # Strip tree prefixes, icons, whitespace
    s_clean = re.sub(r'^[ \t│├└─\-\+📦📁📂•▶▼\s]+', '', s_clean).strip()
    parts = s_clean.split()
    if not parts:
        return ""
    token = parts[0].strip("[](),:;")
    if "group:" in s_clean and not token.startswith("group:"):
        m = re.search(r'group:[^\s\[\]()]+', s_clean)
        if m:
            return m.group(0).strip("[](),:;")
    return token

def list_skills_status():
    """Display installation and version status of all skills in a sleek rounded table."""
    manifest = load_manifest()
    installed_dirs = []
    if os.path.exists(SKILLS_DIR):
        installed_dirs = [d for d in os.listdir(SKILLS_DIR) if os.path.isdir(os.path.join(SKILLS_DIR, d))]
        installed_dirs.sort()

    if not installed_dirs:
        if IS_ZH:
            c_print("1;33", "当前 ~/.agents/skills/ 目录下没有任何技能。")
        else:
            c_print("1;33", "No skills found under ~/.agents/skills/.")
        return 0

    CYAN = "\033[1;36m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[1;34m"
    MAGENTA = "\033[1;35m"
    WHITE = "\033[1;37m"
    GREY = "\033[0;90m"
    RESET = "\033[0m"

    tracked_count = sum(1 for d in installed_dirs if d in manifest)
    local_count = len(installed_dirs) - tracked_count

    print(f"{CYAN}╭──────────────────────── 📦 AI Agent 技能版本与来源状态 ────────────────────────╮{RESET}")
    if IS_ZH:
        stat_line = f"  总计安装: {WHITE}{len(installed_dirs)}{RESET} 个  │  {BLUE}📦 Git 追踪: {tracked_count} 个{RESET}  │  {GREY}🏷️ 本地自建: {local_count} 个{RESET}"
    else:
        stat_line = f"  Total: {WHITE}{len(installed_dirs)}{RESET}  │  {BLUE}📦 Tracked: {tracked_count}{RESET}  │  {GREY}🏷️ Local: {local_count}{RESET}"
    print(f"{CYAN}│{RESET}{stat_line}")
    print(f"{CYAN}├──────────────────────────┬──────────────┬──────────────┬────────────────────────┤{RESET}")
    if IS_ZH:
        print(f"{CYAN}│{RESET} {WHITE}{'技能名称 (Skill Name)':<24}{RESET} {CYAN}│{RESET} {WHITE}{'类型 (Type)':<12}{RESET} {CYAN}│{RESET} {WHITE}{'版本 (Commit)':<12}{RESET} {CYAN}│{RESET} {WHITE}{'来源仓库 (Source Repo)':<22}{RESET} {CYAN}│{RESET}")
    else:
        print(f"{CYAN}│{RESET} {WHITE}{'Skill Name':<24}{RESET} {CYAN}│{RESET} {WHITE}{'Type':<12}{RESET} {CYAN}│{RESET} {WHITE}{'Commit':<12}{RESET} {CYAN}│{RESET} {WHITE}{'Source Repo':<22}{RESET} {CYAN}│{RESET}")
    print(f"{CYAN}├──────────────────────────┼──────────────┼──────────────┼────────────────────────┤{RESET}")

    for s_name in installed_dirs:
        disp_name = s_name if len(s_name) <= 24 else s_name[:21] + "..."
        if s_name in manifest:
            meta = manifest[s_name]
            commit_short = meta.get("commit_hash", "unknown")[:7]
            repo_display = meta.get("repo_url", "")
            if "github.com/" in repo_display:
                repo_display = repo_display.split("github.com/")[-1].removesuffix(".git")
            if len(repo_display) > 22:
                repo_display = repo_display[:19] + "..."
            type_pill = f"{BLUE}Git 追踪{RESET}" if IS_ZH else f"{BLUE}Tracked{RESET}"
            print(f"{CYAN}│{RESET} {GREEN}{disp_name:<24}{RESET} {CYAN}│{RESET} {type_pill:<21} {CYAN}│{RESET} {YELLOW}{commit_short:<12}{RESET} {CYAN}│{RESET} {WHITE}{repo_display:<22}{RESET} {CYAN}│{RESET}")
        else:
            local_tag = f"{GREY}本地自建{RESET}" if IS_ZH else f"{GREY}Local{RESET}"
            dash = f"{GREY}-{RESET}"
            print(f"{CYAN}│{RESET} {WHITE}{disp_name:<24}{RESET} {CYAN}│{RESET} {local_tag:<21} {CYAN}│{RESET} {dash:<21} {CYAN}│{RESET} {dash:<31} {CYAN}│{RESET}")

    print(f"{CYAN}╰──────────────────────────┴──────────────┴──────────────┴────────────────────────╯{RESET}")
    if IS_ZH:
        print(f"{GREY}💡 提示: 运行 'mskill -u <名>' 更新技能，'mskill -b <名>' 解绑 Git 追踪。{RESET}\n")
    else:
        print(f"{GREY}💡 Tip: Run 'mskill -u <name>' to update, 'mskill -b <name>' to unbind Git.{RESET}\n")
    return 0

def uninstall_skill_workflow(skill_name):
    """Uninstall a skill and clean up its manifest entry."""
    s_name = clean_item_id(skill_name)
    dest_path = os.path.join(SKILLS_DIR, s_name)

    if not os.path.exists(dest_path):
        if IS_ZH:
            c_print("1;31", f"[✗] 错误: 技能 '{s_name}' 在 ~/.agents/skills/ 中不存在。", file=sys.stderr)
        else:
            c_print("1;31", f"[✗] Error: Skill '{s_name}' does not exist in ~/.agents/skills/.", file=sys.stderr)
        return 1

    if os.path.isdir(dest_path):
        shutil.rmtree(dest_path)
    elif os.path.isfile(dest_path) or os.path.islink(dest_path):
        os.unlink(dest_path)

    manifest = load_manifest()
    if s_name in manifest:
        del manifest[s_name]
        save_manifest(manifest)

    if IS_ZH:
        c_print("1;32", f"[✓] 成功卸载技能: {s_name}")
    else:
        c_print("1;32", f"[✓] Successfully uninstalled skill: {s_name}")
    return 0

def interactive_install_workflow():
    """Interactive workflow invoked from FZF or CLI to install a new skill."""
    print("\033[1;36m╭──────────────── 📥 安装/下载新的 AI Agent 技能 ────────────────╮\033[0m")
    if IS_ZH:
        print("\033[1;37m│  支持输入:\033[0m")
        print("\033[0;90m│    • GitHub 简写 (如 anthropics/anthropic-quickstarts)\033[0m")
        print("\033[0;90m│    • 完整仓库 URL (如 https://github.com/owner/repo)\033[0m")
        print("\033[0;90m│    • 目录直链 (如 https://github.com/owner/repo/tree/main/skills/video)\033[0m")
    else:
        print("\033[1;37m│  Supported formats:\033[0m")
        print("\033[0;90m│    • GitHub shorthand (e.g. anthropics/anthropic-quickstarts)\033[0m")
        print("\033[0;90m│    • Full URL (e.g. https://github.com/owner/repo)\033[0m")
        print("\033[0;90m│    • Subdirectory URL (e.g. https://github.com/owner/repo/tree/main/skills/video)\033[0m")
    print("\033[1;36m╰────────────────────────────────────────────────────────────────╯\033[0m")

    if IS_ZH:
        target = safe_input("请输入技能仓库地址或简写 (直接回车取消):")
    else:
        target = safe_input("Please enter repository URL or shorthand (Enter to cancel):")

    if not target:
        if IS_ZH:
            c_print("1;33", "[*] 操作已取消。")
            safe_input("\n按回车键返回 FZF...")
        else:
            c_print("1;33", "[*] Operation cancelled.")
            safe_input("\nPress Enter to return to FZF...")
        return 0

    ret = install_skills_workflow(target)
    if IS_ZH:
        safe_input("\n按回车键返回 FZF...")
    else:
        safe_input("\nPress Enter to return to FZF...")
    return ret

def interactive_update_workflow(focused_item):
    """Interactive workflow to update a focused skill or all skills from FZF."""
    s_name = clean_item_id(focused_item)
    if not s_name:
        return 0

    if s_name.startswith("group:"):
        gkey = s_name[6:]
        try:
            with open(GROUPS_FILE, "r", encoding="utf-8") as f:
                gdata = json.load(f)
                gskills = gdata.get(gkey, {}).get("skills", [])
        except Exception:
            gskills = []
        if not gskills:
            if IS_ZH:
                c_print("1;33", f"[*] 分组 '{gkey}' 中没有技能。")
            else:
                c_print("1;33", f"[*] No skills in group '{gkey}'.")
            safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
            return 0
        if IS_ZH:
            c_print("1;34", f"==> 正在更新分组 '{gkey}' 中的 {len(gskills)} 个技能...")
        else:
            c_print("1;34", f"==> Updating {len(gskills)} skills in group '{gkey}'...")
        ret = update_skills_workflow(target_skills=gskills)
    else:
        if IS_ZH:
            c_print("1;34", f"==> 正在检查并更新技能 '{s_name}'...")
        else:
            c_print("1;34", f"==> Checking and updating skill '{s_name}'...")
        ret = update_skills_workflow(target_skills=[s_name])

    if IS_ZH:
        safe_input("\n按回车键返回 FZF...")
    else:
        safe_input("\nPress Enter to return to FZF...")
    return ret

def unbind_skills_workflow(target_skills):
    """
    Unbind one or more skills from their remote Git repository tracking.
    Removes tracking metadata from manifest, converting them into local standalone skills.
    Skill directories, files, and group mappings are preserved intact.
    """
    if not target_skills:
        if IS_ZH:
            c_print("1;31", "错误: 需要指定要解绑 Git 关联的技能名称。", file=sys.stderr)
        else:
            c_print("1;31", "Error: Skill name(s) required for unbinding.", file=sys.stderr)
        return 1

    manifest = load_manifest()
    unbound_count = 0
    not_tracked_count = 0

    for raw_name in target_skills:
        s_name = clean_item_id(raw_name)
        if not s_name:
            continue
        dest_path = os.path.join(SKILLS_DIR, s_name)
        if not os.path.exists(dest_path):
            if IS_ZH:
                c_print("1;33", f"警告: 技能 '{s_name}' 在 ~/.agents/skills/ 中不存在，已跳过。")
            else:
                c_print("1;33", f"Warning: Skill '{s_name}' does not exist in ~/.agents/skills/, skipped.")
            continue

        if s_name in manifest:
            repo_url = manifest[s_name].get("repo_url", "remote git")
            del manifest[s_name]
            unbound_count += 1
            if IS_ZH:
                c_print("1;32", f"[✓] 成功解绑技能 '{s_name}' 的 Git 关联 ({repo_url})")
                c_print("0;36", f"    -> 已转为本地自建技能，本地文件完整保留，不再追踪远程更新。")
            else:
                c_print("1;32", f"[✓] Successfully unbound '{s_name}' from {repo_url}")
                c_print("0;36", f"    -> Converted to local skill; files preserved, remote updates stopped.")
        else:
            not_tracked_count += 1
            if IS_ZH:
                c_print("0;33", f"[*] 技能 '{s_name}' 本身即为本地自建技能（未绑定任何远程 Git 仓库）。")
            else:
                c_print("0;33", f"[*] Skill '{s_name}' is already a local skill (no remote Git tracking).")

    if unbound_count > 0:
        save_manifest(manifest)
    return 0

def interactive_unbind_workflow(focused_item):
    """Interactive workflow to unbind Git tracking for a focused skill or group from FZF."""
    s_name = clean_item_id(focused_item)
    if not s_name:
        return 0

    print("\033[1;36m╭──────────────── 🔗 解绑远程 Git 关联 ────────────────╮\033[0m")
    if s_name.startswith("group:"):
        gkey = s_name[6:]
        try:
            with open(GROUPS_FILE, "r", encoding="utf-8") as f:
                gdata = json.load(f)
                gskills = gdata.get(gkey, {}).get("skills", [])
        except Exception:
            gskills = []
        if not gskills:
            if IS_ZH:
                c_print("1;33", f"[*] 分组 '{gkey}' 中没有技能。")
            else:
                c_print("1;33", f"[*] No skills in group '{gkey}'.")
            safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
            return 0

        manifest = load_manifest()
        tracked = [s for s in gskills if s in manifest]
        if not tracked:
            if IS_ZH:
                c_print("1;33", f"[*] 分组 '{gkey}' 中的技能均为本地技能，无需解绑。")
            else:
                c_print("1;33", f"[*] All skills in group '{gkey}' are already local skills.")
            safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
            return 0

        if IS_ZH:
            print(f"\033[1;37m│  分组 '\033[1;33m{gkey}\033[1;37m' 下有 {len(tracked)} 个已绑定 Git 的技能:\033[0m")
            print(f"\033[0;90m│  {', '.join(tracked)}\033[0m")
            print("\033[1;36m╰─────────────────────────────────────────────────────╯\033[0m")
            ans = safe_input("确定要解绑该分组下所有技能的远程 Git 关联吗？(y/N):")
        else:
            print(f"\033[1;37m│  Group '\033[1;33m{gkey}\033[1;37m' has {len(tracked)} tracked skills:\033[0m")
            print(f"\033[0;90m│  {', '.join(tracked)}\033[0m")
            print("\033[1;36m╰─────────────────────────────────────────────────────╯\033[0m")
            ans = safe_input("Are you sure you want to unbind all skills in this group? (y/N):")

        if ans.lower() not in ("y", "yes"):
            if IS_ZH:
                c_print("1;33", "[*] 操作已取消。")
            else:
                c_print("1;33", "[*] Operation cancelled.")
            safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
            return 0

        ret = unbind_skills_workflow(tracked)
    else:
        manifest = load_manifest()
        if s_name not in manifest:
            if IS_ZH:
                c_print("0;33", f"[*] 技能 '{s_name}' 本身即为本地自建技能（未绑定任何远程 Git 仓库）。")
            else:
                c_print("0;33", f"[*] Skill '{s_name}' is already a local skill (no remote Git tracking).")
            safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
            return 0

        repo_url = manifest[s_name].get("repo_url", "remote git")
        if IS_ZH:
            print(f"\033[1;37m│  技能 '\033[1;32m{s_name}\033[1;37m' 当前绑定了远程仓库: \033[0;36m{repo_url}\033[0m")
            print("\033[1;36m╰─────────────────────────────────────────────────────╯\033[0m")
            ans = safe_input(f"确定要解绑技能 '{s_name}' 的 Git 关联吗？(y/N):")
        else:
            print(f"\033[1;37m│  Skill '\033[1;32m{s_name}\033[1;37m' is currently linked to: \033[0;36m{repo_url}\033[0m")
            print("\033[1;36m╰─────────────────────────────────────────────────────╯\033[0m")
            ans = safe_input(f"Are you sure you want to unbind Git tracking for '{s_name}'? (y/N):")

        if ans.lower() not in ("y", "yes"):
            if IS_ZH:
                c_print("1;33", "[*] 操作已取消。")
            else:
                c_print("1;33", "[*] Operation cancelled.")
            safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
            return 0

        ret = unbind_skills_workflow([s_name])

    if IS_ZH:
        safe_input("\n按回车键返回 FZF...")
    else:
        safe_input("\nPress Enter to return to FZF...")
    return ret

def main():
    if len(sys.argv) < 2:
        return list_skills_status()

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd in ("-i", "--install", "install"):
        if not args:
            c_print("1;31", "Usage: manage_skills.py --install <repo_url_or_shorthand> [skill_names...]", file=sys.stderr)
            return 1
        repo_input = args[0]
        specific_skills = args[1:] if len(args) > 1 else None
        return install_skills_workflow(repo_input, specific_skills=specific_skills)

    elif cmd in ("-u", "--update", "update"):
        target_skills = args if args else None
        return update_skills_workflow(target_skills=target_skills)

    elif cmd in ("--update-all", "update-all"):
        return update_skills_workflow(update_all=True)

    elif cmd in ("--status", "status", "-s"):
        return list_skills_status()

    elif cmd in ("-b", "--unbind", "--unbind-git", "unbind", "detach"):
        if not args:
            c_print("1;31", "Usage: manage_skills.py --unbind <skill_names...>", file=sys.stderr)
            return 1
        return unbind_skills_workflow(args)

    elif cmd in ("-d", "--uninstall", "--remove", "uninstall", "remove"):
        if not args:
            c_print("1;31", "Usage: manage_skills.py --uninstall <skill_name>", file=sys.stderr)
            return 1
        return uninstall_skill_workflow(args[0])

    elif cmd == "--interactive-install":
        return interactive_install_workflow()

    elif cmd == "--interactive-update":
        focused = args[0] if args else ""
        return interactive_update_workflow(focused)

    elif cmd == "--interactive-unbind":
        focused = args[0] if args else ""
        return interactive_unbind_workflow(focused)

    else:
        c_print("1;31", f"Unknown command: {cmd}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

