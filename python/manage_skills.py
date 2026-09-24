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
import unicodedata
from collections import Counter
from datetime import datetime

# Ensure skill_engine can be imported
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from skill_engine._display import (
    IS_ZH, LANG, c_print, strip_ansi, clean_item_id,
    get_display_width, pad_display, truncate_display
)
from skill_engine._store import (
    SKILLS_DIR, DATA_DIR, SOURCES_DIR, MANIFEST_FILE, GROUPS_FILE,
    get_zfl_data_dir, safe_input, atomic_save_json,
    load_manifest, save_manifest, load_groups, save_groups
)
from skill_engine._frontmatter import parse_yaml_frontmatter
from skill_engine._repo import (
    parse_repo_target, clone_or_fetch_repo,
    get_repo_head_commit, get_repo_remote_commit,
    scan_skills_in_dir, reconcile_skills_manifest
)
from skill_engine._groups import (
    get_all_groups, get_group, save_group_definition, delete_group,
    resolve_group_targets, find_groups_for_skills, find_groups_for_skill,
    add_skills_to_group, remove_skill_from_group
)
from skill_engine._mount import (
    get_project_skills_dir, get_connected_skills,
    mount_skills_to_project, unlink_skills_from_project,
    eject_skills_in_project, export_project_manifest, read_project_manifest
)

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
    default_gname = re.sub(r"[^\w\-]", "-", raw_default.strip()).strip("-").lower()
    if not default_gname:
        default_gname = "my-group"

    if IS_ZH:
        gname_prompt = f"请输入分组名称 (直接回车使用默认: '{default_gname}', 或输入 'q' 取消):"
    else:
        gname_prompt = f"Please enter group name (Press Enter for default: '{default_gname}', or 'q' to cancel):"

    user_input = safe_input(gname_prompt).strip()
    if user_input.lower() == 'q':
        return
    if not user_input:
        user_input = default_gname

    # Support Chinese and Unicode group names; replace spaces and invalid punctuation with hyphens
    gname = re.sub(r"[^\w\-]", "-", user_input).strip("-")
    if not gname:
        gname = default_gname

    if IS_ZH:
        ordered_ans = safe_input("是否设为有序分组（即按推荐顺序调用）？(y/N):").lower()
    else:
        ordered_ans = safe_input("Mark as ordered group (recommended call order)? (y/N):").lower()
    is_ordered = ordered_ans in ("y", "yes")

    groups = load_groups()
    disp_name = user_input
    if gname in groups and isinstance(groups[gname], dict) and user_input == default_gname:
        disp_name = groups[gname].get("name", gname)

    if IS_ZH:
        disp_prompt = f"请输入分组展示名/说明 (直接回车保持 '{disp_name}'):"
    else:
        disp_prompt = f"Please enter group display title (Press Enter for '{disp_name}'):"
    disp_input = safe_input(disp_prompt).strip()
    if disp_input:
        disp_name = disp_input

    groups[gname] = {
        "name": disp_name,
        "ordered": is_ordered,
        "skills": installed_skill_names
    }

    if save_groups(groups):
        ordered_label = ("有序" if IS_ZH else "ordered") if is_ordered else ("无序" if IS_ZH else "unordered")
        name_desc = f"'{gname}' ({disp_name})" if gname != disp_name else f"'{gname}'"
        if IS_ZH:
            c_print("1;32", f"\n[✓] 成功创建/更新{ordered_label}技能分组 {name_desc} (包含 {len(installed_skill_names)} 个技能)！")
            c_print("0;33", f"💡 提示: 下次在任何项目根目录下直接运行 'mskill {gname}' 即可一键链接整组技能。")
        else:
            c_print("1;32", f"\n[✓] Successfully saved {ordered_label} skill group {name_desc} ({len(installed_skill_names)} skills)!")
            c_print("0;33", f"💡 Tip: Run 'mskill {gname}' in any project root to link all skills in this group at once.")
    else:
        if IS_ZH:
            c_print("1;31", "保存技能分组失败。", file=sys.stderr)
        else:
            c_print("1;31", "Failed to save skill group.", file=sys.stderr)
    print("\033[1;36m" + "=" * 60 + "\033[0m")

def prompt_install_new_skills(newly_available_by_repo):
    """
    Interactively prompt the user to install newly discovered skills from upstream repositories.
    """
    if not newly_available_by_repo or not sys.stdin.isatty():
        return

    manifest = load_manifest()
    total_new = sum(len(item["skills"]) for item in newly_available_by_repo.values())
    if total_new == 0:
        return

    print("\033[1;36m" + "=" * 60 + "\033[0m")
    if IS_ZH:
        c_print("1;35", f"✨ 检测到已追踪的源仓库中共有 {total_new} 个新上架的可用技能：")
    else:
        c_print("1;35", f"✨ Detected {total_new} newly available skill(s) in tracked repositories:")

    flat_list = []
    for c_name, repo_data in newly_available_by_repo.items():
        meta = repo_data["meta"]
        repo_display = meta.get("repo_url", "")
        if "github.com/" in repo_display:
            repo_display = repo_display.split("github.com/")[-1].removesuffix(".git")
        elif not repo_display:
            repo_display = c_name

        for s in repo_data["skills"]:
            flat_list.append({
                "repo_name": repo_display,
                "cache_name": c_name,
                "meta": meta,
                "latest_commit": repo_data["latest_commit"],
                "skill": s
            })

    for idx, item in enumerate(flat_list, 1):
        s = item["skill"]
        s_name = s["name"]
        desc = s.get("description", "")
        if len(desc) > 40:
            desc = desc[:37] + "..."
        scripts_tag = " [scripts]" if s.get("has_scripts") else ""
        refs_tag = " [refs]" if s.get("has_refs") else ""
        repo_tag = f"\033[0;34m[{item['repo_name']}]\033[0m"

        repo_data = newly_available_by_repo.get(item["cache_name"], {})
        cur_skills = repo_data.get("current_skills", [])
        matched = find_groups_for_skills(cur_skills)
        grp_tag = f" \033[0;35m(现属分组: {', '.join(matched.keys())})\033[0m" if matched and IS_ZH else (
            f" \033[0;35m(in groups: {', '.join(matched.keys())})\033[0m" if matched else ""
        )
        print(f"  {idx}) \033[1;33m{s_name}\033[0m {repo_tag}{grp_tag} ({s.get('file_count', 1)} files{scripts_tag}{refs_tag}) - {desc}")

    print("\033[1;36m" + "=" * 60 + "\033[0m")
    if IS_ZH:
        prompt = "是否直接安装这些新技能？(y: 全部安装 / 输入序号如 '1 3' / 直接回车跳过):"
    else:
        prompt = "Install these new skills? (y: install all / enter indices like '1 3' / Enter to skip):"

    ans = safe_input(prompt)
    if not ans:
        return

    selected_items = []
    ans_lower = ans.strip().lower()
    if ans_lower in ("y", "yes", "all"):
        selected_items = flat_list
    else:
        try:
            indices = [int(x) - 1 for x in ans.split()]
            for i in indices:
                if 0 <= i < len(flat_list):
                    selected_items.append(flat_list[i])
        except ValueError:
            if IS_ZH:
                c_print("1;31", "输入格式有误，已跳过新技能安装。")
            else:
                c_print("1;31", "Invalid input, skipped installing new skills.")
            return

    if not selected_items:
        return

    os.makedirs(SKILLS_DIR, exist_ok=True)
    installed_names = []
    for item in selected_items:
        s = item["skill"]
        s_name = s["name"]
        dest_path = os.path.join(SKILLS_DIR, s_name)
        meta = item["meta"]

        copy_skill_bundle(s["dir_path"], dest_path)
        manifest[s_name] = {
            "repo_url": meta.get("repo_url", ""),
            "owner": meta.get("owner", ""),
            "repo": meta.get("repo", ""),
            "branch": meta.get("branch", "main"),
            "subpath": s.get("rel_subpath", ""),
            "commit_hash": item["latest_commit"],
            "installed_at": datetime.now().isoformat(),
            "cache_name": item["cache_name"],
            "updated_at": datetime.now().isoformat()
        }
        installed_names.append(s_name)
        if IS_ZH:
            c_print("1;32", f"[✓] 成功安装新技能: '{s_name}' ({item['latest_commit'][:7]})")
        else:
            c_print("1;32", f"[✓] Successfully installed new skill: '{s_name}' ({item['latest_commit'][:7]})")

    save_manifest(manifest)
    if IS_ZH:
        c_print("1;32", f"\n✨ 共完成 {len(installed_names)} 个新上架技能的安装！")
    else:
        c_print("1;32", f"\n✨ Successfully installed {len(installed_names)} new skill(s)!")

    # Check if newly installed skills belong to repos whose current skills are already in groups
    installed_by_repo = {}
    for item in selected_items:
        s_name = item["skill"]["name"]
        c_name = item["cache_name"]
        installed_by_repo.setdefault(c_name, []).append(s_name)

    remaining_ungrouped = []
    for c_name, s_names in installed_by_repo.items():
        repo_data = newly_available_by_repo.get(c_name, {})
        cur_skills = repo_data.get("current_skills", [])
        matched = find_groups_for_skills(cur_skills)
        if matched and sys.stdin.isatty():
            for gname in matched.keys():
                s_str = ", ".join(f"'{s}'" for s in s_names)
                if IS_ZH:
                    c_print("1;36", f"\n💡 检测到该仓库现有技能在分组 '{gname}' 中。")
                    add_ans = safe_input(f"是否将新产生的技能 {s_str} 自动加入分组 '{gname}'？(y/N): ")
                else:
                    c_print("1;36", f"\n💡 Detected existing skills of this repo are in group '{gname}'.")
                    add_ans = safe_input(f"Add new skill(s) {s_str} to group '{gname}'? (y/N): ")
                if add_ans.strip().lower() in ("y", "yes"):
                    add_skills_to_group(gname, s_names)
                    if IS_ZH:
                        c_print("1;32", f"[✓] 成功将技能 {s_str} 加入分组 '{gname}'！")
                    else:
                        c_print("1;32", f"[✓] Added skill(s) {s_str} to group '{gname}'!")
        else:
            remaining_ungrouped.extend(s_names)

    # Prompt user to group them if multiple installed and not already added to an existing group
    if len(remaining_ungrouped) > 1 and sys.stdin.isatty():
        prompt_auto_group_skills(remaining_ungrouped, selected_items[0]["meta"])

def install_skills_workflow(repo_input, specific_skills=None, branch=None, force=False):

    """Full workflow to install one or more skills from a repository source."""
    target_info = parse_repo_target(repo_input)
    if not target_info:
        c_print("1;31", f"Error: Invalid repository URL or shorthand '{repo_input}'", file=sys.stderr)
        return 1

    if branch:
        target_info["branch"] = branch

    cache_dir = clone_or_fetch_repo(target_info, update_if_exists=force)
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

    manifest = load_manifest()
    os.makedirs(SKILLS_DIR, exist_ok=True)

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
    elif target_info.get("subpath"):
        # Target specified a specific subpath: if exact match exists, pick it directly
        exact_subpath_matches = [item for item in discovered if item["rel_subpath"] == target_info["subpath"]]
        if len(exact_subpath_matches) == 1:
            selected_skills = exact_subpath_matches
        elif len(discovered) == 1:
            selected_skills = [discovered[0]]
    elif len(discovered) == 1:
        # Single skill repository -> install directly
        selected_skills = [discovered[0]]

    if not selected_skills:
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
            if len(desc) > 35:
                desc = desc[:32] + "..."
            is_installed = os.path.exists(os.path.join(SKILLS_DIR, item["name"]))
            status_tag = " \033[0;32m[已安装]\033[0m" if (is_installed and IS_ZH) else (" \033[0;32m[installed]\033[0m" if is_installed else "")
            path_hint = f" \033[0;90m[{item['rel_subpath']}]\033[0m" if item.get("rel_subpath") else ""
            print(f"  {idx}) \033[1;33m{item['name']}\033[0m{path_hint} ({item['file_count']} files{scripts_flag}{refs_flag}){status_tag} - {desc}")
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

    installed_count = 0
    skipped_count = 0
    for skill_info in selected_skills:
        s_name = skill_info["name"]
        dest_path = os.path.join(SKILLS_DIR, s_name)
        existing_meta = manifest.get(s_name)

        if os.path.exists(dest_path) and not force:
            if existing_meta and existing_meta.get("commit_hash") == commit_hash and commit_hash != "unknown":
                if IS_ZH:
                    c_print("0;32", f"[=] 技能 '{s_name}' 已安装且为最新版本 ({commit_hash[:7]})，跳过重复写入。")
                else:
                    c_print("0;32", f"[=] Skill '{s_name}' is already installed and up-to-date ({commit_hash[:7]}), skipping redundant write.")
                skipped_count += 1
                continue
            else:
                if IS_ZH:
                    c_print("1;33", f"[*] 技能 '{s_name}' 已存在于 ~/.agents/skills/，正在覆盖更新...")
                else:
                    c_print("1;33", f"[*] Skill '{s_name}' already exists in ~/.agents/skills/, updating...")

        copy_skill_bundle(skill_info["dir_path"], dest_path)

        # Update manifest record
        rec_repo_url = target_info["repo_url"]
        rec_branch = target_info.get("branch") or "HEAD"
        rec_commit = commit_hash
        if target_info.get("is_local"):
            rec_repo_url = f"local:{target_info['local_path']}"
            rec_branch = "local"
            if rec_commit == "unknown":
                rec_commit = "local"

        manifest[s_name] = {
            "repo_url": rec_repo_url,
            "owner": target_info.get("owner", ""),
            "repo": target_info.get("repo", ""),
            "branch": rec_branch,
            "subpath": skill_info["rel_subpath"],
            "commit_hash": rec_commit,
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

    if installed_count > 0:
        save_manifest(manifest)
        if IS_ZH:
            c_print("1;32", f"\n完成！已成功安装/更新 {installed_count} 个技能。")
        else:
            c_print("1;32", f"\nDone! Successfully installed/updated {installed_count} skill(s).")
    elif skipped_count > 0:
        if IS_ZH:
            c_print("0;32", f"\n所有选定技能均已是最新版本，无需重复操作。")
        else:
            c_print("0;32", f"\nAll selected skills are already up-to-date, nothing to do.")

    # Prompt auto-grouping if multiple skills were installed
    if len(selected_skills) > 1 and installed_count > 0:
        installed_names = [s["name"] for s in selected_skills]
        prompt_auto_group_skills(installed_names, target_info)

    # Automatically pre-fetch Chinese translations for newly installed skills
    if IS_ZH and installed_count > 0:
        try:
            from preview_skill import prefetch_translations
            installed_names = [s["name"] for s in selected_skills]
            prefetch_translations(installed_names, is_zh=True)
        except Exception:
            pass

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
    failed_count = 0
    deprecated_count = 0
    newly_available_by_repo = {}

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

        cache_dir = clone_or_fetch_repo(target_info, update_if_exists=True)
        if not cache_dir:
            failed_count += len(item["skills"])
            continue

        latest_commit = get_repo_head_commit(cache_dir)
        discovered = scan_skills_in_dir(cache_dir)
        discovered_by_subpath = {d["rel_subpath"]: d for d in discovered}
        discovered_by_name = {d["name"]: d for d in discovered}

        # Detect new skills added upstream in this source repo that the user has not installed
        all_local_dirs = set(os.listdir(SKILLS_DIR)) if os.path.exists(SKILLS_DIR) else set()

        # Check if any local skills exist in this repository but were untracked in manifest
        local_untracked = [
            d for d in discovered
            if d["name"] in all_local_dirs and d["name"] not in manifest
        ]
        if local_untracked:
            for d in local_untracked:
                manifest[d["name"]] = {
                    "repo_url": meta["repo_url"],
                    "owner": meta.get("owner", ""),
                    "repo": meta.get("repo", ""),
                    "branch": meta.get("branch") or "HEAD",
                    "subpath": d["rel_subpath"],
                    "commit_hash": latest_commit,
                    "installed_at": datetime.now().isoformat(),
                    "cache_name": c_name
                }
                if d["name"] not in item["skills"]:
                    item["skills"].append(d["name"])
            save_manifest(manifest)
            if IS_ZH:
                c_print("1;32", f"[*] 检测到本地存在同源技能并已自动对齐追踪: {', '.join(d['name'] for d in local_untracked)}")
            else:
                c_print("1;32", f"[*] Detected and reconciled untracked local skill(s): {', '.join(d['name'] for d in local_untracked)}")

        new_in_repo = [d for d in discovered if d["name"] not in all_local_dirs and d["name"] not in manifest]
        if new_in_repo:
            all_repo_skills = [
                name for name, m in manifest.items()
                if (m.get("cache_name") or f"{m.get('owner')}__{m.get('repo')}") == c_name
            ]
            newly_available_by_repo[c_name] = {
                "meta": meta,
                "cache_dir": cache_dir,
                "latest_commit": latest_commit,
                "skills": new_in_repo,
                "current_skills": all_repo_skills or item["skills"]
            }

        for s_name in item["skills"]:
            curr_meta = manifest[s_name]
            recorded_commit = curr_meta.get("commit_hash", "")
            subpath = curr_meta.get("subpath", "")

            # Locate the updated skill bundle in source repo
            skill_info = discovered_by_subpath.get(subpath) or discovered_by_name.get(s_name)
            if not skill_info:
                deprecated_count += 1
                if IS_ZH:
                    c_print("1;33", f"[!] 提示: 远程源仓库在新版本中已不包含技能 '{s_name}' (原路径: '{subpath}')。")
                    c_print("0;90", f"    -> 本地已保留现有副本继续可用。如需长期保留建议运行 'mskill -b {s_name}' 解绑 Git，或运行 'mskill -d {s_name}' 卸载。")
                else:
                    c_print("1;33", f"[!] Notice: Skill '{s_name}' is no longer present in source repo (path: '{subpath}').")
                    c_print("0;90", f"    -> Local copy preserved. Run 'mskill -b {s_name}' to convert to local or 'mskill -d {s_name}' to uninstall.")

                in_groups = find_groups_for_skill(s_name)
                if in_groups and sys.stdin.isatty():
                    g_str = ", ".join(f"'{g}'" for g in in_groups)
                    if IS_ZH:
                        del_grp = safe_input(f"    检测到技能 '{s_name}' 属于分组 {g_str}，是否将其从对应分组中删除？(y/N): ")
                    else:
                        del_grp = safe_input(f"    Skill '{s_name}' belongs to group(s) {g_str}. Remove it from these group(s)? (y/N): ")
                    if del_grp.strip().lower() in ("y", "yes"):
                        for g in in_groups:
                            remove_skill_from_group(g, s_name)
                        if IS_ZH:
                            c_print("1;32", f"    [✓] 已从分组 {g_str} 中移除技能 '{s_name}'。")
                        else:
                            c_print("1;32", f"    [✓] Removed skill '{s_name}' from group(s) {g_str}.")
                continue

            dest_path = os.path.join(SKILLS_DIR, s_name)
            is_intact = os.path.exists(dest_path) and os.path.exists(os.path.join(dest_path, "SKILL.md"))

            if recorded_commit == latest_commit and is_intact:
                up_to_date_count += 1
                if IS_ZH:
                    c_print("0;32", f"[=] 技能 '{s_name}' 已是最新版本 ({latest_commit[:7]})")
                else:
                    c_print("0;32", f"[=] Skill '{s_name}' is already up-to-date ({latest_commit[:7]})")
            else:
                # Copy updated bundle
                copy_skill_bundle(skill_info["dir_path"], dest_path)
                curr_meta["commit_hash"] = latest_commit
                curr_meta["subpath"] = skill_info["rel_subpath"]
                curr_meta["updated_at"] = datetime.now().isoformat()
                updated_count += 1
                commit_change = f"{recorded_commit[:7]} -> {latest_commit[:7]}" if recorded_commit else f"-> {latest_commit[:7]}"
                if IS_ZH:
                    c_print("1;32", f"[✓] 成功更新技能 '{s_name}' ({commit_change})")
                else:
                    c_print("1;32", f"[✓] Successfully updated '{s_name}' ({commit_change})")

    save_manifest(manifest)
    if IS_ZH:
        print("\033[1;36m" + "=" * 50 + "\033[0m")
        summary_parts = [f"{updated_count} 个已更新", f"{up_to_date_count} 个已是最新"]
        if deprecated_count:
            summary_parts.append(f"{deprecated_count} 个远程已废弃(已保留)")
        if failed_count:
            summary_parts.append(f"{failed_count} 个拉取失败")
        c_print("1;32", f"更新完成: {('，'.join(summary_parts))}。")
        if newly_available_by_repo and not sys.stdin.isatty():
            for c_repo, repo_data in newly_available_by_repo.items():
                s_names = [s["name"] for s in repo_data["skills"]]
                c_print("0;36", f"💡 提示: 源仓库 '{c_repo}' 新上架了 {len(s_names)} 个技能: {', '.join(s_names[:5])}{' 等' if len(s_names) > 5 else ''} (可用 'mskill -i <repo>' 安装)")
        c_print("0;33", "提示: 所有技能分组配置已完整保留，项目端软链接即时同步生效。")
    else:
        print("\033[1;36m" + "=" * 50 + "\033[0m")
        summary_parts = [f"{updated_count} updated", f"{up_to_date_count} already up-to-date"]
        if deprecated_count:
            summary_parts.append(f"{deprecated_count} missing upstream (preserved)")
        if failed_count:
            summary_parts.append(f"{failed_count} fetch failed")
        c_print("1;32", f"Update complete: {(', '.join(summary_parts))}.")
        if newly_available_by_repo and not sys.stdin.isatty():
            for c_repo, repo_data in newly_available_by_repo.items():
                s_names = [s["name"] for s in repo_data["skills"]]
                c_print("0;36", f"💡 Tip: Source repo '{c_repo}' has {len(s_names)} new skill(s): {', '.join(s_names[:5])}{'...' if len(s_names) > 5 else ''} (install via 'mskill -i <repo>')")
        c_print("0;33", "Notice: All skill groups preserved intact, symlinks updated automatically.")

    if newly_available_by_repo and sys.stdin.isatty():
        prompt_install_new_skills(newly_available_by_repo)

    return 0


def list_skills_status():
    """Display installation and version status of all skills in a modern streamlined table."""
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
    WHITE = "\033[1;37m"
    GREY = "\033[0;90m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    tracked_count = sum(1 for d in installed_dirs if d in manifest)
    local_count = len(installed_dirs) - tracked_count

    term_width = shutil.get_terminal_size((100, 24)).columns

    header_name = "技能名称 (Skill Name)" if IS_ZH else "Skill Name"
    header_type = "类型 (Type)" if IS_ZH else "Type"
    header_commit = "版本 (Commit)" if IS_ZH else "Commit"
    header_repo = "来源仓库 (Source Repo)" if IS_ZH else "Source Repo"

    max_name_len = max((len(d) for d in installed_dirs), default=20)
    col_name_w = max(get_display_width(header_name), min(max_name_len, max(24, int(term_width * 0.35))))
    col_type_w = max(get_display_width(header_type), 12)
    col_commit_w = max(get_display_width(header_commit), 13)
    col_repo_w = max(24, term_width - (col_name_w + col_type_w + col_commit_w + 10))

    if IS_ZH:
        print(f"\n  {BOLD}{WHITE}📦 AI Agent 技能状态清单{RESET}  "
              f"{CYAN}[总计: {WHITE}{len(installed_dirs)}{CYAN}]{RESET}  "
              f"{BLUE}[● Git 追踪: {WHITE}{tracked_count}{BLUE}]{RESET}  "
              f"{GREY}[○ 本地自建: {WHITE}{local_count}{GREY}]{RESET}\n")
    else:
        print(f"\n  {BOLD}{WHITE}📦 AI Agent Skills Status{RESET}  "
              f"{CYAN}[Total: {WHITE}{len(installed_dirs)}{CYAN}]{RESET}  "
              f"{BLUE}[● Tracked: {WHITE}{tracked_count}{BLUE}]{RESET}  "
              f"{GREY}[○ Local: {WHITE}{local_count}{GREY}]{RESET}\n")

    h_name = pad_display(f"{BOLD}{WHITE}{header_name}{RESET}", col_name_w)
    h_type = pad_display(f"{BOLD}{WHITE}{header_type}{RESET}", col_type_w)
    h_commit = pad_display(f"{BOLD}{WHITE}{header_commit}{RESET}", col_commit_w)
    h_repo = f"{BOLD}{WHITE}{header_repo}{RESET}"

    divider_w = min(term_width - 4, col_name_w + col_type_w + col_commit_w + col_repo_w + 6)
    print(f"  {h_name}  {h_type}  {h_commit}  {h_repo}")
    print(f"  {GREY}{'─' * divider_w}{RESET}")

    for s_name in installed_dirs:
        disp_name = truncate_display(s_name, col_name_w)
        if s_name in manifest:
            meta = manifest[s_name]
            commit_short = meta.get("commit_hash", "unknown")[:7]
            repo_display = meta.get("repo_url", "")
            if "github.com/" in repo_display:
                repo_display = repo_display.split("github.com/")[-1].removesuffix(".git")
            repo_disp = truncate_display(repo_display, col_repo_w)

            c_name = pad_display(f"{GREEN}{disp_name}{RESET}", col_name_w)
            type_pill = f"{BLUE}● Git 追踪{RESET}" if IS_ZH else f"{BLUE}● Tracked{RESET}"
            c_type = pad_display(type_pill, col_type_w)
            c_commit = pad_display(f"{YELLOW}{commit_short}{RESET}", col_commit_w)
            c_repo = f"{WHITE}{repo_disp}{RESET}"
        else:
            c_name = pad_display(f"{WHITE}{disp_name}{RESET}", col_name_w)
            type_pill = f"{GREY}○ 本地自建{RESET}" if IS_ZH else f"{GREY}○ Local{RESET}"
            c_type = pad_display(type_pill, col_type_w)
            c_commit = pad_display(f"{GREY}—{RESET}", col_commit_w)
            c_repo = f"{GREY}—{RESET}"

        print(f"  {c_name}  {c_type}  {c_commit}  {c_repo}")

    print(f"  {GREY}{'─' * divider_w}{RESET}")
    if IS_ZH:
        print(f"  {GREY}💡 提示: 运行 'mskill -u <名>' 更新技能，'mskill -b <名>' 解绑 Git 追踪。{RESET}\n")
    else:
        print(f"  {GREY}💡 Tip: Run 'mskill -u <name>' to update, 'mskill -b <name>' to unbind Git.{RESET}\n")
    return 0

def uninstall_skill_workflow(skill_name, prompt_group_cleanup=True):
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

    if prompt_group_cleanup and sys.stdin.isatty():
        in_groups = find_groups_for_skill(s_name)
        if in_groups:
            g_str = ", ".join(f"'{g}'" for g in in_groups)
            if IS_ZH:
                ans = safe_input(f"检测到技能 '{s_name}' 属于分组 {g_str}，是否将其从对应分组中删除？(y/N): ")
            else:
                ans = safe_input(f"Skill '{s_name}' belongs to group(s) {g_str}. Remove it from these group(s)? (y/N): ")
            if ans.strip().lower() in ("y", "yes"):
                for g in in_groups:
                    remove_skill_from_group(g, s_name)
                if IS_ZH:
                    c_print("1;32", f"[✓] 已从分组 {g_str} 中移除技能 '{s_name}'。")
                else:
                    c_print("1;32", f"[✓] Removed skill '{s_name}' from group(s) {g_str}.")
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

def interactive_update_workflow(target_items):
    """Interactive workflow to update focused skill(s) or all skills in group(s) from FZF."""
    if not target_items:
        return 0
    if isinstance(target_items, str):
        target_items = [target_items]

    skills = resolve_group_targets(target_items)
    if not skills:
        if IS_ZH:
            c_print("1;33", "[*] 未选择任何有效技能。")
        else:
            c_print("1;33", "[*] No valid skill selected.")
        safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
        return 0

    if len(skills) == 1:
        if IS_ZH:
            c_print("1;34", f"==> 正在检查并更新技能 '{skills[0]}'...")
        else:
            c_print("1;34", f"==> Checking and updating skill '{skills[0]}'...")
    else:
        if IS_ZH:
            c_print("1;34", f"==> 正在检查并更新选中的 {len(skills)} 个技能...")
        else:
            c_print("1;34", f"==> Checking and updating {len(skills)} selected skills...")

    ret = update_skills_workflow(target_skills=skills)
    safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
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

def interactive_unbind_workflow(target_items):
    """Interactive workflow to unbind Git tracking for focused skill(s) or group(s) from FZF."""
    if not target_items:
        return 0
    if isinstance(target_items, str):
        target_items = [target_items]

    skills = resolve_group_targets(target_items)
    if not skills:
        return 0

    manifest = load_manifest()
    tracked = [s for s in skills if s in manifest]
    if not tracked:
        if IS_ZH:
            c_print("0;33", "[*] 所选技能均为本地自建技能（未绑定任何远程 Git 仓库）。")
        else:
            c_print("0;33", "[*] Selected skill(s) are local skills (no remote Git tracking).")
        safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
        return 0

    print("\033[1;36m╭──────────────── 🔗 解绑远程 Git 关联 ────────────────╮\033[0m")
    if len(tracked) == 1:
        s_name = tracked[0]
        repo_url = manifest[s_name].get("repo_url", "remote git")
        if IS_ZH:
            print(f"\033[1;37m│  技能 '\033[1;32m{s_name}\033[1;37m' 当前绑定了远程仓库: \033[0;36m{repo_url}\033[0m")
            print("\033[1;36m╰─────────────────────────────────────────────────────╯\033[0m")
            ans = safe_input(f"确定要解绑技能 '{s_name}' 的 Git 关联吗？(y/N):")
        else:
            print(f"\033[1;37m│  Skill '\033[1;32m{s_name}\033[1;37m' is currently linked to: \033[0;36m{repo_url}\033[0m")
            print("\033[1;36m╰─────────────────────────────────────────────────────╯\033[0m")
            ans = safe_input(f"Are you sure you want to unbind Git tracking for '{s_name}'? (y/N):")
    else:
        if IS_ZH:
            print(f"\033[1;37m│  所选内容中共有 {len(tracked)} 个已绑定 Git 的技能:\033[0m")
            print(f"\033[0;90m│  {', '.join(tracked)}\033[0m")
            print("\033[1;36m╰─────────────────────────────────────────────────────╯\033[0m")
            ans = safe_input(f"确定要解绑这 {len(tracked)} 个技能的远程 Git 关联吗？(y/N):")
        else:
            print(f"\033[1;37m│  Found {len(tracked)} tracked skill(s) selected:\033[0m")
            print(f"\033[0;90m│  {', '.join(tracked)}\033[0m")
            print("\033[1;36m╰─────────────────────────────────────────────────────╯\033[0m")
            ans = safe_input(f"Are you sure you want to unbind these {len(tracked)} skills? (y/N):")

    if ans.lower() not in ("y", "yes"):
        if IS_ZH:
            c_print("1;33", "[*] 操作已取消。")
        else:
            c_print("1;33", "[*] Operation cancelled.")
        safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
        return 0

    ret = unbind_skills_workflow(tracked)
    safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
    return ret

    if IS_ZH:
        safe_input("\n按回车键返回 FZF...")
    else:
        safe_input("\nPress Enter to return to FZF...")
    return ret

def create_skill_scaffold(skill_name=None):
    """Scaffold a new standard AI Agent skill in ~/.agents/skills/<name>."""
    if not skill_name:
        if IS_ZH:
            skill_name = safe_input("请输入新技能名称 (如 my-awesome-skill):")
        else:
            skill_name = safe_input("Enter new skill name (e.g. my-awesome-skill):")
    
    if not skill_name:
        c_print("1;33", "操作已取消。" if IS_ZH else "Operation cancelled.")
        return 0

    s_name = re.sub(r"[^a-zA-Z0-9_\-]", "-", skill_name.strip()).strip("-").lower()
    if not s_name:
        c_print("1;31", "错误: 技能名称不合法。" if IS_ZH else "Error: Invalid skill name.", file=sys.stderr)
        return 1

    dest_dir = os.path.join(SKILLS_DIR, s_name)
    if os.path.exists(dest_dir):
        if IS_ZH:
            c_print("1;31", f"错误: 技能 '{s_name}' 已存在于 ~/.agents/skills/ 目录下！", file=sys.stderr)
        else:
            c_print("1;31", f"Error: Skill '{s_name}' already exists in ~/.agents/skills/!", file=sys.stderr)
        return 1

    if IS_ZH:
        desc = safe_input(f"请输入技能简短描述 (回车使用默认模板):")
    else:
        desc = safe_input(f"Enter brief description (Enter for default template):")
    if not desc:
        desc = f"AI Agent skill for {s_name}."

    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(os.path.join(dest_dir, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(dest_dir, "references"), exist_ok=True)

    skill_md_content = f"""---
name: {s_name}
description: {desc}
---

# {s_name}

## Overview
{desc}

## When to Use
- Describe when the AI agent should invoke or apply this skill.

## Guidelines
1. Step-by-step instructions for the AI Agent.
2. Best practices and edge-case handling.
"""

    skill_zh_content = f"""---
name: {s_name}
description: {desc}
---

# {s_name}

## 概述
{desc}

## 触发场景
- 描述 AI Agent 应当在何种场景下选用此技能。

## 指南与约束
1. 步骤说明。
2. 最佳实践与注意事项。
"""

    with open(os.path.join(dest_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_md_content)
    with open(os.path.join(dest_dir, "SKILL.zh.md"), "w", encoding="utf-8") as f:
        f.write(skill_zh_content)

    if IS_ZH:
        c_print("1;32", f"\n  ✓ 技能脚手架创建成功: ~/.agents/skills/{s_name}/")
        c_print("0;90", f"  {'─' * 55}")
        c_print("0;37", f"    • SKILL.md       (标准提示词与元数据骨架)")
        c_print("0;37", f"    • SKILL.zh.md    (中文双语说明与提示词)")
        c_print("0;37", f"    • scripts/       (伴生辅助脚本目录)")
        c_print("0;37", f"    • references/    (领域知识库与规范文档目录)")
        c_print("0;90", f"  {'─' * 55}")
        c_print("0;33", f"  💡 提示: 您可以直接在任意项目下运行 'mskill {s_name}' 引入该技能，或在 FZF 中按 Ctrl-E 实时编辑。\n")
    else:
        c_print("1;32", f"\n  ✓ Skill Scaffold Created: ~/.agents/skills/{s_name}/")
        c_print("0;90", f"  {'─' * 55}")
        c_print("0;37", f"    • SKILL.md       (Standard prompt & metadata)")
        c_print("0;37", f"    • SKILL.zh.md    (Bilingual documentation template)")
        c_print("0;37", f"    • scripts/       (Accompanying helper scripts)")
        c_print("0;37", f"    • references/    (Domain knowledge & reference docs)")
        c_print("0;90", f"  {'─' * 55}")
        c_print("0;33", f"  💡 Tip: Run 'mskill {s_name}' to link to your project, or press Ctrl-E in FZF to edit.\n")
    return 0

def doctor_workflow():
    """Diagnose skills health: dangling symlinks, corrupted skills, missing dependencies."""
    BOLD = "\033[1m"
    WHITE = "\033[1;37m"
    RESET = "\033[0m"

    title = "🩺 mskill 技能健康巡检与诊断" if IS_ZH else "🩺 mskill Health & Diagnostics Report"
    print(f"\n  {BOLD}{WHITE}{title}{RESET}")
    divider = "─" * 60
    print(f"  \033[0;90m{divider}\033[0m")

    issues_found = 0
    fixed_count = 0

    # 1. Project-level inspection
    proj_skills_dir = os.path.join(os.getcwd(), ".agents", "skills")
    if os.path.exists(proj_skills_dir):
        if IS_ZH:
            c_print("1;34", f"\n  [1/3] 检查当前项目挂载状态: {proj_skills_dir}")
        else:
            c_print("1;34", f"\n  [1/3] Checking project skills: {proj_skills_dir}")
        
        for item in sorted(os.listdir(proj_skills_dir)):
            item_path = os.path.join(proj_skills_dir, item)
            if os.path.islink(item_path):
                target = os.readlink(item_path)
                if not os.path.exists(item_path):
                    issues_found += 1
                    if IS_ZH:
                        c_print("1;31", f"    ✗ 发现悬空死链 (Broken symlink): {item} -> {target}")
                        ans = safe_input(f"      是否立即清理此死链？(Y/n):")
                    else:
                        c_print("1;31", f"    ✗ Broken symlink detected: {item} -> {target}")
                        ans = safe_input(f"      Remove this broken symlink? (Y/n):")
                    if ans.lower() not in ("n", "no"):
                        try:
                            os.unlink(item_path)
                            fixed_count += 1
                            c_print("1;32", f"      [✓] 已清理: {item}" if IS_ZH else f"      [✓] Removed: {item}")
                        except Exception as e:
                            c_print("1;31", f"      [✗] 清理失败: {e}", file=sys.stderr)
            elif os.path.isdir(item_path):
                if not os.path.exists(os.path.join(item_path, "SKILL.md")):
                    issues_found += 1
                    c_print("1;33", f"    ⚠️ 项目内实体技能缺少 SKILL.md: {item}" if IS_ZH else f"    ⚠️ Missing SKILL.md in project skill: {item}")
    else:
        if IS_ZH:
            c_print("0;90", "\n  [1/3] 当前目录未挂载 .agents/skills/，跳过项目级检测。")
        else:
            c_print("0;90", "\n  [1/3] No .agents/skills/ in current directory, skipping project inspection.")

    # 2. Global-level inspection
    if IS_ZH:
        c_print("1;34", f"\n  [2/3] 检查全局技能库: {SKILLS_DIR}")
    else:
        c_print("1;34", f"\n  [2/3] Checking global skills directory: {SKILLS_DIR}")

    missing_deps = {}
    if os.path.exists(SKILLS_DIR):
        for s_name in sorted(os.listdir(SKILLS_DIR)):
            s_path = os.path.join(SKILLS_DIR, s_name)
            if not os.path.isdir(s_path):
                continue
            skill_md = os.path.join(s_path, "SKILL.md")
            if not os.path.exists(skill_md):
                issues_found += 1
                c_print("1;31", f"    ✗ 全局技能缺少 SKILL.md: {s_name}" if IS_ZH else f"    ✗ Global skill missing SKILL.md: {s_name}")
                continue

            meta = parse_yaml_frontmatter(skill_md)
            if not meta.get("name") or not meta.get("description"):
                issues_found += 1
                c_print("1;33", f"    ⚠️ 技能 '{s_name}' frontmatter 缺少 name 或 description 字段" if IS_ZH else f"    ⚠️ Skill '{s_name}' frontmatter missing 'name' or 'description'")

            # Check declared dependencies
            deps_str = meta.get("deps") or meta.get("dependencies") or ""
            if deps_str:
                deps_list = [d.strip() for d in re.split(r"[,; \t]+", deps_str) if d.strip()]
                for dep in deps_list:
                    if not shutil.which(dep):
                        if dep not in missing_deps:
                            missing_deps[dep] = []
                        missing_deps[dep].append(s_name)

        # Reconcile any untracked skills matching git repositories or cached sources
        reconciled = reconcile_skills_manifest(auto_save=True)
        if reconciled:
            issues_found += len(reconciled)
            fixed_count += len(reconciled)
            names_str = ", ".join(sorted(reconciled.keys()))
            if IS_ZH:
                c_print("1;32", f"    ✓ 自动对齐并补全 {len(reconciled)} 个技能的 Git 追踪元数据: {names_str}")
            else:
                c_print("1;32", f"    ✓ Automatically reconciled Git metadata for {len(reconciled)} skill(s): {names_str}")

    # 3. Environment CLI Dependencies
    if IS_ZH:
        c_print("1;34", "\n  [3/3] 检查环境与系统依赖可用性:")
    else:
        c_print("1;34", "\n  [3/3] Checking system CLI dependencies:")

    for cli_cmd in ["git", "python3", "fzf"]:
        if shutil.which(cli_cmd):
            c_print("0;32", f"    ✓ 核心工具已就绪: {cli_cmd}")
        else:
            issues_found += 1
            c_print("1;31", f"    ✗ 缺少核心推荐工具: {cli_cmd}")

    if missing_deps:
        for dep, skills in missing_deps.items():
            issues_found += 1
            if IS_ZH:
                c_print("1;33", f"    ⚠️ 缺少技能声明的系统 CLI: '{dep}' (被以下技能引用: {', '.join(skills)})")
            else:
                c_print("1;33", f"    ⚠️ Missing CLI dependency: '{dep}' (declared in: {', '.join(skills)})")

    print(f"  \033[0;90m{divider}\033[0m")
    if issues_found == 0:
        c_print("1;32", "  🎉 恭喜！未检测到任何健康隐患，所有技能与环境均处于完美状态！\n" if IS_ZH else "  🎉 All clean! No health issues found.\n")
    else:
        c_print("1;33", f"  诊断完毕：共发现 {issues_found} 处隐患/异常，已自动修复 {fixed_count} 处。\n" if IS_ZH else f"  Diagnosis done: {issues_found} issue(s) detected, {fixed_count} fixed.\n")
def mount_project_skills(target_skills, copy_entity=False):
    """
    Mount (symlink or copy) global skills into current project directory (.agents/skills/).
    Delegates resolution and filesystem ops to skill_engine._mount.
    """
    if not target_skills:
        c_print("1;33", "提示: 未指定需要挂载的技能或分组名称。" if IS_ZH else "Notice: No skills or groups specified to mount.")
        return 0

    # Home directory protection: refuse to mount skills in ~
    cwd = os.path.abspath(os.getcwd())
    home = os.path.abspath(os.path.expanduser("~"))
    if cwd == home:
        if IS_ZH:
            c_print("1;33", "[mskill] 家目录保护：无法在家目录下执行链接/拷贝操作。")
            c_print("0;36", "  请 cd 到你的项目目录后再运行此操作。")
        else:
            c_print("1;33", "[mskill] Home dir protection: cannot link/copy skills in home directory.")
            c_print("0;36", "  Please cd to your project directory first.")
        return 1

    res = mount_skills_to_project(target_skills, copy_entity=copy_entity)
    if not res["resolved"]:
        no_action = "没有需要拷贝的有效技能。" if copy_entity else "没有需要链接的有效技能。"
        no_action_en = "No valid skills to copy." if copy_entity else "No valid skills to link."
        c_print("1;33", f"[mskill] {no_action if IS_ZH else no_action_en}")
        return 0

    GREEN = "\033[1;32m"
    CYAN = "\033[1;36m"
    RED = "\033[1;31m"
    GREY = "\033[0;90m"
    RESET = "\033[0m"

    success_skills = res["success"]
    failed_skills = res["failed"]

    if success_skills:
        action_name = "实体拷贝" if copy_entity else "软链接挂载"
        action_type = "实体副本" if copy_entity else "软链接"
        action_name_en = "Skill Entities Copied" if copy_entity else "Skills Symlinked"
        action_type_en = "copied entity" if copy_entity else "symlink"

        if IS_ZH:
            print(f"\n  {GREEN}✓ 技能{action_name}成功{RESET} (共 {len(success_skills)} 个技能已挂载至 {CYAN}.agents/skills/{RESET})")
            print(f"  {GREY}{'─' * 60}{RESET}")
            for skill in success_skills:
                print(f"    {GREEN}•{RESET} {skill} -> .agents/skills/{skill} ({action_type})")
            print(f"  {GREY}{'─' * 60}{RESET}\n")
        else:
            print(f"\n  {GREEN}✓ {action_name_en}{RESET} ({len(success_skills)} skills mounted to {CYAN}.agents/skills/{RESET})")
            print(f"  {GREY}{'─' * 60}{RESET}")
            for skill in success_skills:
                print(f"    {GREEN}•{RESET} {skill} -> .agents/skills/{skill} ({action_type_en})")
            print(f"  {GREY}{'─' * 60}{RESET}\n")

    if failed_skills:
        action_str = "拷贝" if copy_entity else "软链接"
        action_str_en = "copy" if copy_entity else "link"
        if IS_ZH:
            print(f"\n  {RED}✗ 操作部分失败{RESET} (以下技能{action_str}失败):", file=sys.stderr)
            print(f"  {GREY}{'─' * 60}{RESET}", file=sys.stderr)
            for f in failed_skills:
                print(f"    {RED}✗{RESET} {f['name']} ({f['error']})", file=sys.stderr)
            print(f"  {GREY}{'─' * 60}{RESET}\n", file=sys.stderr)
        else:
            print(f"\n  {RED}✗ Operation Failed{RESET} (Failed to {action_str_en} following skills):", file=sys.stderr)
            print(f"  {GREY}{'─' * 60}{RESET}", file=sys.stderr)
            for f in failed_skills:
                print(f"    {RED}✗{RESET} {f['name']} ({f['error']})", file=sys.stderr)
            print(f"  {GREY}{'─' * 60}{RESET}\n", file=sys.stderr)
        return 1

    return 0

def eject_project_skills(target_skills=None):
    """Convert symlinked skills in current project into standalone physical copies."""
    connected = get_connected_skills()
    if not connected:
        c_print("1;31", "错误: 当前项目下没有 .agents/skills/ 目录。" if IS_ZH else "Error: No .agents/skills/ in current project.", file=sys.stderr)
        return 1

    symlinked = [c for c in connected if c["is_link"]]
    if not symlinked:
        c_print("1;33", "提示: 当前项目下没有处于软链接状态的技能（均为实体副本或无技能）。" if IS_ZH else "Notice: No symlinked skills in current project.")
        return 0

    res = eject_skills_in_project(target_skills)
    for skipped in res["skipped"]:
        c_print("1;33", f"警告: '{skipped}' 在当前项目中不是软链接，已跳过。" if IS_ZH else f"Warning: '{skipped}' is not a symlink in current project, skipped.")

    for item in res["ejected"]:
        if IS_ZH:
            c_print("1;32", f"[✓] 技能 '{item}' 已原地脱壳为独立实体副本 (解除全局依赖)")
        else:
            c_print("1;32", f"[✓] Skill '{item}' ejected to standalone physical copy.")

    for f in res["failed"]:
        c_print("1;31", f"[✗] 脱壳失败 '{f['name']}': {f['error']}", file=sys.stderr)

    if IS_ZH:
        c_print("1;32", f"\n脱壳完成！共将 {len(res['ejected'])} 个技能转为项目内实体副本，在当前项目内修改不会影响全局。")
    else:
        c_print("1;32", f"\nEject complete! {len(res['ejected'])} skills converted to local copies.")
    return 0 if not res["failed"] else 1

def unlink_project_skills(target_skills=None, unlink_all=False):
    """Safely unlink or remove skills from current project without touching global directory."""
    if not unlink_all and not target_skills:
        c_print("1;31", "错误: 请指定要解挂的技能名称，或使用 --unlink-all 解挂全部。" if IS_ZH else "Error: Specify skill name(s) or use --unlink-all.", file=sys.stderr)
        return 1

    connected = get_connected_skills()
    if not connected:
        c_print("1;33", "提示: 当前项目没有连接任何技能。" if IS_ZH else "Notice: No skills connected in current project.")
        return 0

    res = unlink_skills_from_project(target_skills=target_skills, unlink_all=unlink_all)
    for name in res["removed"]:
        if IS_ZH:
            c_print("1;32", f"[✓] 已从当前项目中移除: {name}")
        else:
            c_print("1;32", f"[✓] Removed from project: {name}")

    for f in res["failed"]:
        c_print("1;31", f"[✗] 移除失败 '{f['name']}': {f['error']}", file=sys.stderr)

    if IS_ZH:
        c_print("1;32", f"\n成功从当前项目解挂 {len(res['removed'])} 个技能（全局技能库不受任何影响）。")
    else:
        c_print("1;32", f"\nSuccessfully unlinked {len(res['removed'])} skill(s) from project.")
    return 0 if not res["failed"] else 1

def interactive_unlink_workflow(target_items):
    """Interactive workflow to unlink focused skill(s) from current project (invoked via FZF Ctrl-X)."""
    if not target_items:
        return 0
    if isinstance(target_items, str):
        target_items = [target_items]

    skills = resolve_group_targets(target_items)
    if not skills:
        return 0

    connected = get_connected_skills()
    connected_map = {c["name"]: c for c in connected}
    to_unlink = [s for s in skills if s in connected_map]

    if not to_unlink:
        if len(skills) == 1:
            c_print("1;33", f"[*] 技能 '{skills[0]}' 当前并未挂载在当前项目中。" if IS_ZH else f"[*] Skill '{skills[0]}' is not mounted in the current project.")
        else:
            c_print("1;33", f"[*] 所选的 {len(skills)} 个技能均未在当前项目中引入。" if IS_ZH else f"[*] None of the {len(skills)} selected skills are mounted in current project.")
        safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
        return 0

    if len(to_unlink) == 1:
        s_name = to_unlink[0]
        type_str = "软链接" if connected_map[s_name]["is_link"] else "实体副本"
        type_str_en = "symlink" if connected_map[s_name]["is_link"] else "copied entity"
        ans = safe_input(f"确定要从当前项目中移除技能 '{s_name}' ({type_str}) 吗？(y/N):" if IS_ZH else f"Remove '{s_name}' ({type_str_en}) from current project? (y/N):")
    else:
        print("\033[1;33m╭──────────────── ⚠️  从当前项目移除技能 ────────────────╮\033[0m")
        if IS_ZH:
            print(f"\033[1;37m│  检测到所选内容中包含 {len(to_unlink)} 个已挂载技能：\033[0m")
            for s in to_unlink:
                mode_tag = "软链接" if connected_map[s]["is_link"] else "实体副本"
                print(f"│    • \033[1;33m{s}\033[0m \033[0;90m({mode_tag})\033[0m")
            print("\033[1;90m│  (仅从当前项目移除，全局技能库保持完好)\033[0m")
            print("\033[1;33m╰─────────────────────────────────────────────────────╯\033[0m")
            ans = safe_input(f"确定要从当前项目中移除这 {len(to_unlink)} 个技能吗？(y/N):")
        else:
            print(f"\033[1;37m│  Detected {len(to_unlink)} mounted skill(s) selected:\033[0m")
            for s in to_unlink:
                mode_tag = "symlink" if connected_map[s]["is_link"] else "copy"
                print(f"│    • \033[1;33m{s}\033[0m \033[0;90m({mode_tag})\033[0m")
            print("\033[1;90m│  (Only unlinks from project, global library untouched)\033[0m")
            print("\033[1;33m╰─────────────────────────────────────────────────────╯\033[0m")
            ans = safe_input(f"Remove these {len(to_unlink)} skills from project? (y/N):")

    if ans.lower() in ("y", "yes"):
        unlink_project_skills(to_unlink)
    else:
        if IS_ZH:
            c_print("1;33", "[*] 操作已取消。")
        else:
            c_print("1;33", "[*] Operation cancelled.")
    safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
    return 0

def interactive_edit_workflow(target_items):
    """Interactive workflow to edit SKILL.md of focused/selected skill(s) via $EDITOR."""
    if not target_items:
        return 0
    if isinstance(target_items, str):
        target_items = [target_items]

    skills = resolve_group_targets(target_items)
    if not skills:
        return 0

    target_files = []
    for s in skills:
        p = os.path.join(SKILLS_DIR, s, "SKILL.md")
        if os.path.exists(p):
            target_files.append(p)

    if not target_files:
        return 0

    editor = os.environ.get("EDITOR") or "vim"
    subprocess.run([editor] + target_files)
    return 0

def export_project_skills():
    """Export current project skills configuration into .skillsrc for declarative collaboration."""
    rc_data = export_project_manifest()
    if not rc_data:
        c_print("1;31", "错误: 当前项目下没有 .agents/skills/ 目录或无有效挂载技能，无法导出。" if IS_ZH else "Error: No skills found in current project to export.", file=sys.stderr)
        return 1

    rc_file = os.path.join(os.getcwd(), ".skillsrc")
    skills_map = rc_data.get("skills", {})
    if IS_ZH:
        c_print("1;32", f"\n  ✓ 技能清单导出成功: {rc_file}  [共 {len(skills_map)} 个技能]")
        c_print("0;90", f"  {'─' * 55}")
        for s, info in skills_map.items():
            c_print("0;37", f"    • {s:<24} [{info['mode']}] (source: {info['source']})")
        c_print("0;90", f"  {'─' * 55}")
        c_print("0;33", "  💡 提示: 您可以将 .skillsrc 提交至 Git 仓库，团队成员只需运行 'mskill sync' 即可一键拉取并对齐技能！\n")
    else:
        c_print("1;32", f"\n  ✓ Skills Manifest Exported: {rc_file}  [Total: {len(skills_map)} skills]")
        c_print("0;90", f"  {'─' * 55}")
        for s, info in skills_map.items():
            c_print("0;37", f"    • {s:<24} [{info['mode']}] (source: {info['source']})")
        c_print("0;90", f"  {'─' * 55}")
        c_print("0;33", "  💡 Tip: Commit .skillsrc to Git so team members can align via 'mskill sync'.\n")
    return 0

def sync_project_skills():
    """Read .skillsrc and align/install all required skills into current project."""
    rc_data = read_project_manifest()
    if not rc_data:
        c_print("1;31", "错误: 未在当前项目根目录下找到 .skillsrc 配置文件。" if IS_ZH else "Error: .skillsrc not found in current project.", file=sys.stderr)
        c_print("0;33", "提示: 您可以先运行 'mskill dump' 为当前项目生成 .skillsrc 配置。" if IS_ZH else "Tip: Run 'mskill dump' first to generate .skillsrc.")
        return 1

    skills_spec = rc_data.get("skills", {})
    if not skills_spec:
        c_print("1;33", "提示: .skillsrc 中没有定义任何技能依赖。" if IS_ZH else "Notice: No skills defined in .skillsrc.")
        return 0

    if IS_ZH:
        c_print("1;36", f"==> 开始同步当前项目技能依赖 (共 {len(skills_spec)} 个)...")
    else:
        c_print("1;36", f"==> Syncing {len(skills_spec)} project skills...")

    synced_count = 0
    for s_name, spec in skills_spec.items():
        mode = spec.get("mode", "symlink")
        source = spec.get("source", "")
        global_path = os.path.join(SKILLS_DIR, s_name)

        if not os.path.exists(global_path):
            if source and source != "local" and not source.startswith("local:"):
                if IS_ZH:
                    c_print("1;34", f"[*] 全局缺少技能 '{s_name}'，正在从远程源自动安装 ({source})...")
                else:
                    c_print("1;34", f"[*] Missing global skill '{s_name}', installing from {source}...")
                branch = spec.get("branch") if spec.get("branch") != "HEAD" else None
                ret = install_skills_workflow(source, specific_skills=[s_name], branch=branch)
                if ret != 0:
                    c_print("1;31", f"[✗] 自动拉取技能 '{s_name}' 失败，跳过。", file=sys.stderr)
                    continue
            else:
                c_print("1;31", f"[✗] 全局缺少技能 '{s_name}' 且无可用远程源，无法同步。", file=sys.stderr)
                continue

        mount_res = mount_skills_to_project([s_name], copy_entity=(mode == "copy"))
        if mount_res["success"]:
            type_str = "实体副本" if mode == "copy" else "软链接"
            if IS_ZH:
                c_print("0;32", f"  [✓] {s_name} -> {type_str}")
            else:
                c_print("0;32", f"  [✓] {s_name} -> {mode}")
            synced_count += 1
        else:
            c_print("1;31", f"  [✗] 挂载技能 '{s_name}' 失败", file=sys.stderr)

    if IS_ZH:
        c_print("1;32", f"\n[✓] 同步完成！成功将 {synced_count}/{len(skills_spec)} 个技能对齐引入当前项目。")
    else:
        c_print("1;32", f"\n[✓] Sync complete! {synced_count}/{len(skills_spec)} skills aligned.")
    return 0


def reconcile_manifest_workflow():
    """Scan and reconcile untracked local skills with upstream Git repositories."""
    if IS_ZH:
        c_print("1;36", "\n🔍 正在扫描未登记的本地技能并尝试与远程 Git 仓库对齐同步...")
    else:
        c_print("1;36", "\n🔍 Scanning untracked skills and reconciling with Git repositories...")

    reconciled = reconcile_skills_manifest(auto_save=True)
    if not reconciled:
        if IS_ZH:
            c_print("0;32", "  ✓ 所有具有远程 Git 来源的技能均已正确登记追踪，无需同步。\n")
        else:
            c_print("0;32", "  ✓ All skills with remote Git sources are already tracked.\n")
        return 0

    if IS_ZH:
        c_print("1;32", f"  [✓] 成功对齐并登记 {len(reconciled)} 个技能的远程 Git 追踪元数据：")
        for s_name, meta in sorted(reconciled.items()):
            repo_disp = meta.get("repo_url", "")
            if "github.com/" in repo_disp:
                repo_disp = repo_disp.split("github.com/")[-1].removesuffix(".git")
            subpath_disp = f" ({meta['subpath']})" if meta.get("subpath") else ""
            c_print("0;37", f"    • \033[1;33m{s_name}\033[0m -> \033[0;34m{repo_disp}\033[0m{subpath_disp}")
        c_print("0;90", f"\n  元数据已持久化至 {MANIFEST_FILE}\n")
    else:
        c_print("1;32", f"  [✓] Successfully reconciled {len(reconciled)} skill(s) with Git tracking:")
        for s_name, meta in sorted(reconciled.items()):
            repo_disp = meta.get("repo_url", "")
            if "github.com/" in repo_disp:
                repo_disp = repo_disp.split("github.com/")[-1].removesuffix(".git")
            subpath_disp = f" ({meta['subpath']})" if meta.get("subpath") else ""
            c_print("0;37", f"    • \033[1;33m{s_name}\033[0m -> \033[0;34m{repo_disp}\033[0m{subpath_disp}")
        c_print("0;90", f"\n  Persisted to {MANIFEST_FILE}\n")
    return 0


def is_in_home_dir():
    """Check if current working directory is user's home directory."""
    try:
        return os.path.abspath(os.getcwd()) == os.path.abspath(os.path.expanduser("~"))
    except Exception:
        return False


def show_home_protection_warning():
    """Display bilingual warning when a project-level command is run in $HOME."""
    if IS_ZH:
        c_print("1;33", "[mskill] 家目录保护：链接/拷贝/解挂等操作仅在项目目录下有效。", file=sys.stderr)
        c_print("0;37", "  在家目录下，请使用全局管理操作（如 \033[1;36mmskill -i/-u/-d/--status/--doctor\033[0m 等）。", file=sys.stderr)
        c_print("0;37", "  如需管理技能分组或查看已安装技能，请使用 \033[1;36mmskill -l / --status\033[0m。", file=sys.stderr)
    else:
        c_print("1;33", "[mskill] Home dir protection: link/copy/unlink/eject/dump/sync are project-level operations.", file=sys.stderr)
        c_print("0;37", "  In the home directory, use global management commands (e.g. \033[1;36mmskill -i/-u/-d/--status/--doctor\033[0m).", file=sys.stderr)
        c_print("0;37", "  To manage skill groups or view installed skills, use \033[1;36mmskill -l / --status\033[0m.", file=sys.stderr)


def is_repo_spec(candidate):
    """Detect if candidate string resembles a git repo URL, shorthand, or local dir path."""
    if not candidate or candidate.startswith("-"):
        return False
    if "://" in candidate or candidate.startswith("git@") or candidate.startswith("github.com/") or candidate.endswith(".git"):
        return True
    if "/" in candidate:
        global_skill_path = os.path.join(SKILLS_DIR, candidate)
        if not os.path.exists(global_skill_path):
            return True
    return False


def main():
    if len(sys.argv) < 2:
        return list_skills_status()

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # Help commands
    if cmd in ("-h", "--help"):
        print("Usage: mskill [options] [skill_name/group_name...]")
        print("Run 'mskill --help' from zsh for full documentation.")
        return 0

    # 1. Install & Lifecycle
    elif cmd in ("-i", "--install", "install"):
        if not args:
            return interactive_install_workflow()
        repo_input = args[0]
        specific_skills = args[1:] if len(args) > 1 else None
        return install_skills_workflow(repo_input, specific_skills=specific_skills)

    elif cmd in ("-u", "--update", "update"):
        target_skills = args if args else None
        return update_skills_workflow(target_skills=target_skills)

    elif cmd in ("--update-all", "update-all"):
        return update_skills_workflow(update_all=True)

    elif cmd in ("--status", "status"):
        return list_skills_status()

    elif cmd in ("-b", "--unbind", "--unbind-git", "unbind", "detach"):
        if not args:
            if IS_ZH:
                c_print("1;31", "[mskill] 错误: 需要指定要解绑 Git 关联的技能名称。", file=sys.stderr)
            else:
                c_print("1;31", "[mskill] Error: Skill name(s) required for unbinding.", file=sys.stderr)
            return 1
        return unbind_skills_workflow(args)

    elif cmd in ("-d", "--uninstall", "--remove", "uninstall", "remove"):
        if not args:
            if IS_ZH:
                c_print("1;31", "[mskill] 错误: 需要指定要卸载的技能名称。", file=sys.stderr)
            else:
                c_print("1;31", "[mskill] Error: Skill name required for uninstallation.", file=sys.stderr)
            return 1
        return uninstall_skill_workflow(args[0])

    elif cmd in ("--new", "new", "--create", "create"):
        skill_name = args[0] if args else None
        return create_skill_scaffold(skill_name)

    elif cmd in ("--doctor", "doctor", "--check", "check"):
        return doctor_workflow()

    # 2. Project-level mount operations (Enforce Home directory protection)
    elif cmd in ("--eject", "eject"):
        if is_in_home_dir():
            show_home_protection_warning()
            return 1
        target_skills = args if args else None
        return eject_project_skills(target_skills)

    elif cmd in ("--unlink", "unlink", "-X"):
        if is_in_home_dir():
            show_home_protection_warning()
            return 1
        return unlink_project_skills(target_skills=args)

    elif cmd in ("--unlink-all", "unlink-all"):
        if is_in_home_dir():
            show_home_protection_warning()
            return 1
        return unlink_project_skills(unlink_all=True)

    elif cmd in ("--dump", "dump", "--export", "export"):
        if is_in_home_dir():
            show_home_protection_warning()
            return 1
        return export_project_skills()

    elif cmd in ("--reconcile", "reconcile", "--sync-manifest"):
        return reconcile_manifest_workflow()

    elif cmd in ("--sync", "sync"):
        if is_in_home_dir() or not os.path.exists(os.path.join(os.getcwd(), ".skillsrc")):
            return reconcile_manifest_workflow()
        return sync_project_skills()

    elif cmd in ("--link", "link"):
        if is_in_home_dir():
            show_home_protection_warning()
            return 1
        return mount_project_skills(target_skills=args, copy_entity=False)

    elif cmd in ("-c", "--copy", "copy"):
        if is_in_home_dir():
            show_home_protection_warning()
            return 1
        if not args:
            c_print("1;31", "Usage: manage_skills.py --copy <skills...>", file=sys.stderr)
            return 1
        return mount_project_skills(target_skills=args, copy_entity=True)

    # 3. Interactive workflows (Called by FZF bindings)
    elif cmd == "--interactive-install":
        return interactive_install_workflow()

    elif cmd == "--interactive-update":
        return interactive_update_workflow(args)

    elif cmd == "--interactive-unbind":
        return interactive_unbind_workflow(args)

    elif cmd == "--interactive-unlink":
        return interactive_unlink_workflow(args)

    elif cmd == "--interactive-edit":
        return interactive_edit_workflow(args)

    # 4. Group Management
    elif cmd == "--list-groups-completion":
        import resolve_skills
        return resolve_skills.cmd_list_groups_completion()

    elif cmd in ("-l", "--group-list", "--list-groups", "--list-groups-detailed"):
        import resolve_skills
        return resolve_skills.cmd_list_groups_detailed()

    elif cmd in ("-s", "--group-set", "--set-group"):
        import resolve_skills
        return resolve_skills.cmd_set_group(args)

    elif cmd in ("-r", "--group-rm", "--rm-group"):
        import resolve_skills
        gname = args[0] if args else ""
        return resolve_skills.cmd_rm_group(gname)

    elif cmd in ("--group-add", "group-add"):
        import resolve_skills
        return resolve_skills.cmd_group_add(args)

    elif cmd in ("--group-remove", "--group-rm-skill", "group-remove"):
        import resolve_skills
        return resolve_skills.cmd_group_remove(args)

    elif cmd in ("-v", "--view", "--view-connected", "view"):
        import resolve_skills
        return resolve_skills.cmd_view_connected()

    elif cmd == "--interactive-group-set":
        import resolve_skills
        return resolve_skills.cmd_interactive_set(args)

    elif cmd == "--interactive-group-rm":
        import resolve_skills
        return resolve_skills.cmd_interactive_rm(args)

    # 5. Translation Management
    elif cmd in ("--translate-all", "translate-all"):
        import preview_skill
        return preview_skill.cmd_translate_all(IS_ZH)

    elif cmd == "--interactive-translate":
        import preview_skill
        return preview_skill.cmd_force_translate(args)

    # 6. Smart auto-detect or Positional Skills
    elif cmd.startswith("-"):
        if IS_ZH:
            c_print("1;31", f"[mskill] 未知参数: {cmd}", file=sys.stderr)
            print("请使用 --help 查看用法。", file=sys.stderr)
        else:
            c_print("1;31", f"[mskill] Unknown option: {cmd}", file=sys.stderr)
            print("Please use --help to view usage.", file=sys.stderr)
        return 2

    elif is_repo_spec(cmd):
        return install_skills_workflow(cmd, specific_skills=args if args else None)

    else:
        # Default positional skills / groups to link into project
        if is_in_home_dir():
            show_home_protection_warning()
            return 1
        all_targets = [cmd] + args
        return mount_project_skills(target_skills=all_targets, copy_entity=False)

if __name__ == "__main__":
    sys.exit(main())

