#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Description: Parse and expand skill groups and skill names, and provide interfaces to manage groups

import os
import sys
import json
import re
import unicodedata

# Ensure skill_engine can be imported
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from skill_engine._display import (
    IS_ZH, LANG, strip_ansi, clean_item_id, circled_num,
    get_display_width, pad_display, truncate_display
)
from skill_engine._store import safe_input, atomic_save_json, GROUPS_FILE
from skill_engine._frontmatter import parse_yaml_frontmatter as parse_frontmatter
from skill_engine import (
    get_all_groups, get_group, save_group_definition, delete_group,
    resolve_group_targets, get_groups_completion_data,
    find_groups_for_skill, find_groups_for_skills,
    add_skills_to_group, remove_skill_from_group, remove_skill_from_all_groups,
    get_project_skills_dir, get_connected_skills
)

def load_groups():
    """Compatibility wrapper: return all groups from skill_engine."""
    return get_all_groups()

def save_groups(groups):
    """Compatibility wrapper: save groups via atomic store."""
    return atomic_save_json(GROUPS_FILE, groups)

def interactive_set(selected_args):
    # Filter out empty arguments or option arguments
    skills = []
    groups = load_groups()
    detected_gkeys = []
    
    # Expand any selected group to its member skills
    for raw_item in selected_args:
        item = clean_item_id(raw_item)
        if not item or item.startswith("-"):
            continue
        if item.startswith("group:"):
            gkey = item[6:]
            if gkey in groups:
                detected_gkeys.append(gkey)
                ginfo = groups[gkey]
                skills.extend(ginfo.get("skills", []) if isinstance(ginfo, dict) else ginfo)
        elif item in groups:
            detected_gkeys.append(item)
            ginfo = groups[item]
            skills.extend(ginfo.get("skills", []) if isinstance(ginfo, dict) else ginfo)
        else:
            skills.append(item)
            
    # Default group key if editing a single existing group
    default_gkey = detected_gkeys[0] if len(detected_gkeys) == 1 and len(selected_args) == 1 else ""
    current_ordered = None
    if default_gkey and default_gkey in groups:
        ginfo = groups[default_gkey]
        if isinstance(ginfo, dict):
            current_ordered = ginfo.get("ordered", False)

    # Deduplicate skills while preserving order
    unique_skills = []
    seen = set()
    for s in skills:
        if s not in seen:
            seen.add(s)
            unique_skills.append(s)
            
    if not unique_skills:
        if IS_ZH:
            print("\033[1;31m╭─────────────────────────────────────────────────────────╮\033[0m")
            print("\033[1;31m│  [✗] 错误: 未选中任何技能，请先使用空格键在列表中选择技能！│\033[0m")
            print("\033[1;31m╰─────────────────────────────────────────────────────────╯\033[0m")
            safe_input("\n按回车键返回 FZF...")
        else:
            print("\033[1;31m╭─────────────────────────────────────────────────────────╮\033[0m")
            print("\033[1;31m│  [✗] Error: No skills selected. Select with Space first!│\033[0m")
            print("\033[1;31m╰─────────────────────────────────────────────────────────╯\033[0m")
            safe_input("\nPress Enter to return to FZF...")
        return

    # If user selected skills (not directly focusing on an existing group node) and groups exist:
    if not default_gkey and groups:
        print("\033[1;36m╭──────────────── 🛠️  技能分组管理 ────────────────╮\033[0m")
        if IS_ZH:
            print(f"\033[1;32m│  已选中 {len(unique_skills)} 个技能：\033[0m")
            for i, s in enumerate(unique_skills[:8], 1):
                print(f"│    {i}) \033[1;37m{s}\033[0m")
            if len(unique_skills) > 8:
                print(f"│    ... 等共 {len(unique_skills)} 个技能")
            print("│")
            print("│  \033[1;33m请选择分组操作:\033[0m")
            print("│    \033[1;37m1)\033[0m 加入已有分组 (追加至选定分组)")
            print("│    \033[1;37m2)\033[0m 移动到已有分组 (移入并从原分组移出)")
            print("│    \033[1;37m3)\033[0m 创建全新技能分组")
            print("\033[1;36m╰─────────────────────────────────────────────────╯\033[0m")
            action_prompt = "请选择操作模式 (1:加入 / 2:移动 / 3:新建，直接回车使用 1):"
        else:
            print(f"\033[1;32m│  Selected {len(unique_skills)} skill(s):\033[0m")
            for i, s in enumerate(unique_skills[:8], 1):
                print(f"│    {i}) \033[1;37m{s}\033[0m")
            if len(unique_skills) > 8:
                print(f"│    ... and {len(unique_skills) - 8} more")
            print("│")
            print("│  \033[1;33mSelect Action:\033[0m")
            print("│    \033[1;37m1)\033[0m Add to existing group (append)")
            print("│    \033[1;37m2)\033[0m Move to existing group (remove from old)")
            print("│    \033[1;37m3)\033[0m Create a new skill group")
            print("\033[1;36m╰─────────────────────────────────────────────────╯\033[0m")
            action_prompt = "Select action (1:Add / 2:Move / 3:New, Enter for 1):"

        action_ans = safe_input(action_prompt).strip()
        if not action_ans:
            action_ans = "1"

        if action_ans in ("1", "2"):
            sorted_gkeys = sorted(groups.keys())
            print("\033[1;36m╭──────────────── 📁 选择目标已有分组 ────────────────╮\033[0m")
            for idx, gk in enumerate(sorted_gkeys, 1):
                gdata = groups[gk]
                gtitle = gdata.get("name", gk) if isinstance(gdata, dict) else gk
                gcount = len(gdata.get("skills", [])) if isinstance(gdata, dict) else len(gdata)
                count_str = f"{gcount} 个技能" if IS_ZH else f"{gcount} skills"
                disp_title = f" ({gtitle})" if gtitle != gk else ""
                print(f"│  {idx}) \033[1;33m{gk}\033[0m{disp_title} · \033[0;36m{count_str}\033[0m")
            print("\033[1;36m╰───────────────────────────────────────────────────╯\033[0m")

            pick_prompt = "请输入目标分组序号或名称 (回车取消):" if IS_ZH else "Enter group number or name (Enter to cancel):"
            pick_ans = safe_input(pick_prompt).strip()
            if not pick_ans:
                if IS_ZH:
                    print("\033[1;33m[*] 操作已取消。\033[0m")
                    safe_input("\n按回车键返回 FZF...")
                else:
                    print("\033[1;33m[*] Operation cancelled.\033[0m")
                    safe_input("\nPress Enter to return to FZF...")
                return

            target_gkey = None
            try:
                pick_idx = int(pick_ans) - 1
                if 0 <= pick_idx < len(sorted_gkeys):
                    target_gkey = sorted_gkeys[pick_idx]
            except ValueError:
                clean_target = clean_item_id(pick_ans).removeprefix("group:")
                if clean_target in groups:
                    target_gkey = clean_target

            if not target_gkey:
                if IS_ZH:
                    print(f"\033[1;31m[✗] 未找到指定分组: '{pick_ans}'\033[0m")
                    safe_input("\n按回车键返回 FZF...")
                else:
                    print(f"\033[1;31m[✗] Group not found: '{pick_ans}'\033[0m")
                    safe_input("\nPress Enter to return to FZF...")
                return

            if action_ans == "2":
                for s in unique_skills:
                    remove_skill_from_all_groups(s)
                action_word = "移动到" if IS_ZH else "moved to"
            else:
                action_word = "加入" if IS_ZH else "added to"

            if add_skills_to_group(target_gkey, unique_skills):
                s_str = ", ".join(f"'{s}'" for s in unique_skills)
                if IS_ZH:
                    print(f"\n\033[1;32m[✓] 成功将技能 {s_str} {action_word}分组 '{target_gkey}'！\033[0m")
                    safe_input("\n按回车键返回 FZF...")
                else:
                    print(f"\n\033[1;32m[✓] Successfully {action_word} skill(s) {s_str} group '{target_gkey}'!\033[0m")
                    safe_input("\nPress Enter to return to FZF...")
                return
            else:
                if IS_ZH:
                    print(f"\n\033[1;33m[*] 所选技能已全部在分组 '{target_gkey}' 中，无需重复添加。\033[0m")
                    safe_input("\n按回车键返回 FZF...")
                else:
                    print(f"\n\033[1;33m[*] Skill(s) already in group '{target_gkey}', nothing changed.\033[0m")
                    safe_input("\nPress Enter to return to FZF...")
                return

    # --- Step 1: Show selected skills and allow reordering by index ---
    print("\033[1;36m╭──────────────── 🛠️  技能分组配置向导 ────────────────╮\033[0m")
    if default_gkey:
        if IS_ZH:
            print(f"\033[1;33m│  当前正在编辑分组: {default_gkey}\033[0m")
        else:
            print(f"\033[1;33m│  Editing existing group: {default_gkey}\033[0m")
    if IS_ZH:
        print(f"\033[1;32m│  已选中 {len(unique_skills)} 个技能：\033[0m")
    else:
        print(f"\033[1;32m│  Selected {len(unique_skills)} skills:\033[0m")
    for i, s in enumerate(unique_skills, 1):
        print(f"│    {i}) \033[1;37m{s}\033[0m")
    print("\033[1;36m╰─────────────────────────────────────────────────────╯\033[0m")

    try:
        if IS_ZH:
            reorder_input = safe_input('请输入新的排列顺序（如 "3 1 2"，直接回车保持现有顺序）:')
        else:
            reorder_input = safe_input('Enter new order (e.g. "3 1 2", or press Enter to keep current):')
        if reorder_input:
            try:
                indices = [int(x) - 1 for x in reorder_input.split()]
                if sorted(indices) == list(range(len(unique_skills))):
                    unique_skills = [unique_skills[i] for i in indices]
                    if IS_ZH:
                        print("\033[1;32m[✓] 已按新顺序排列：\033[0m")
                    else:
                        print("\033[1;32m[✓] Reordered:\033[0m")
                    for i, s in enumerate(unique_skills, 1):
                        print(f"    {i}) {s}")
                else:
                    if IS_ZH:
                        print("\033[1;33m[*] 序号不合法，已忽略，保持原有顺序。\033[0m")
                    else:
                        print("\033[1;33m[*] Invalid indices, keeping original order.\033[0m")
            except ValueError:
                if IS_ZH:
                    print("\033[1;33m[*] 输入有误，已忽略，保持原有顺序。\033[0m")
                else:
                    print("\033[1;33m[*] Invalid input, keeping original order.\033[0m")

        # --- Step 2: Ask if this group is ordered ---
        if current_ordered is True:
            prompt_ordered = "是否设为有序分组（即按上方顺序依次调用）？(Y/n，直接回车保持当前【有序】):" if IS_ZH else "Mark as ordered group? (Y/n, Enter to keep current [Ordered]):"
            ordered_ans = safe_input(prompt_ordered).lower()
            is_ordered = False if ordered_ans in ('n', 'no') else True
        elif current_ordered is False:
            prompt_ordered = "是否设为有序分组（即按上方顺序依次调用）？(y/N，直接回车保持当前【无序】):" if IS_ZH else "Mark as ordered group? (y/N, Enter to keep current [Unordered]):"
            ordered_ans = safe_input(prompt_ordered).lower()
            is_ordered = True if ordered_ans in ('y', 'yes') else False
        else:
            prompt_ordered = "是否设为有序分组（即按上方顺序依次调用）？(y/N):" if IS_ZH else "Mark as ordered group (recommended call order)? (y/N):"
            ordered_ans = safe_input(prompt_ordered).lower()
            is_ordered = ordered_ans in ('y', 'yes')

        # --- Step 3: Ask for group name ---
        if default_gkey:
            prompt_name = f"请输入分组标识名 (直接回车保持 '{default_gkey}'):" if IS_ZH else f"Please enter group key (Press Enter to keep '{default_gkey}'):"
            gname = safe_input(prompt_name)
            if not gname:
                gname = default_gkey
        else:
            prompt_name = "请输入要创建的分组名称 (或按回车键取消):" if IS_ZH else "Please enter group name to create (or press Enter to cancel):"
            gname = safe_input(prompt_name)
            if not gname:
                if IS_ZH:
                    print("\033[1;33m[*] 操作已取消。\033[0m")
                    safe_input("\n按回车键返回 FZF...")
                else:
                    print("\033[1;33m[*] Operation cancelled.\033[0m")
                    safe_input("\nPress Enter to return to FZF...")
                return
            
        disp_name = gname
        if gname in groups and isinstance(groups[gname], dict):
            disp_name = groups[gname].get("name", gname)
        elif default_gkey and default_gkey == gname and default_gkey in groups and isinstance(groups[default_gkey], dict):
            disp_name = groups[default_gkey].get("name", gname)

        if IS_ZH:
            prompt_disp = f"请输入分组展示名/说明 (直接回车保持 '{disp_name}'):"
        else:
            prompt_disp = f"Please enter group display title (Press Enter to keep '{disp_name}'):"
        disp_input = safe_input(prompt_disp).strip()
        if disp_input:
            disp_name = disp_input

        # If renamed from an existing group, remove the old key to avoid stale duplicates
        if default_gkey and default_gkey != gname:
            delete_group(default_gkey)
            
        if save_group_definition(gname, unique_skills, is_ordered=is_ordered, display_name=disp_name):
            ordered_label = ("有序" if IS_ZH else "ordered") if is_ordered else ("无序" if IS_ZH else "unordered")
            if IS_ZH:
                print(f"\n\033[1;32m[✓] 成功保存{ordered_label}分组 '{gname}' (包含 {len(unique_skills)} 个技能)！\033[0m")
            else:
                print(f"\n\033[1;32m[✓] Successfully saved {ordered_label} group '{gname}' ({len(unique_skills)} skills)!\033[0m")
        else:
            if IS_ZH:
                print("\n\033[1;31m[✗] 保存失败。\033[0m")
            else:
                print("\n\033[1;31m[✗] Failed to save.\033[0m")
    except KeyboardInterrupt:
        if IS_ZH:
            print("\n\033[1;33m[*] 操作已取消。\033[0m")
        else:
            print("\n\033[1;33m[*] Operation cancelled.\033[0m")
        
    if IS_ZH:
        safe_input("\n按回车键返回 FZF...")
    else:
        safe_input("\nPress Enter to return to FZF...")

def interactive_rm(focused_item):
    cleaned = clean_item_id(focused_item)
    if not cleaned:
        return

    if not cleaned.startswith("group:"):
        # The user focused on a skill node instead of a group node!
        in_groups = find_groups_for_skill(cleaned)
        if not in_groups:
            if IS_ZH:
                print("\033[1;33m╭─────────────────────────────────────────────────────────╮\033[0m")
                print(f"\033[1;33m│  [*] 提示: 技能 '{cleaned}' 当前不属于任何技能分组。     │\033[0m")
                print("\033[1;33m╰─────────────────────────────────────────────────────────╯\033[0m")
                safe_input("\n按回车键返回 FZF...")
            else:
                print("\033[1;33m╭─────────────────────────────────────────────────────────╮\033[0m")
                print(f"\033[1;33m│  [*] Notice: Skill '{cleaned}' does not belong to groups.│\033[0m")
                print("\033[1;33m╰─────────────────────────────────────────────────────────╯\033[0m")
                safe_input("\nPress Enter to return to FZF...")
            return

        if len(in_groups) == 1:
            target_grp = in_groups[0]
            print("\033[1;33m╭──────────────── ⚠️  从分组中移除技能确认 ────────────────╮\033[0m")
            if IS_ZH:
                print(f"\033[1;37m│  确定要将技能 '\033[1;33m{cleaned}\033[1;37m' 从分组 '\033[1;36m{target_grp}\033[1;37m' 中移除吗？\033[0m")
                print("\033[1;90m│  (仅从分组定义中移除，不会删除技能本地文件)\033[0m")
            else:
                print(f"\033[1;37m│  Remove skill '\033[1;33m{cleaned}\033[1;37m' from group '\033[1;36m{target_grp}\033[1;37m'?\033[0m")
                print("\033[1;90m│  (Only removes from group, does not delete skill files)\033[0m")
            print("\033[1;33m╰─────────────────────────────────────────────────────────╯\033[0m")

            confirm = safe_input("请输入 y 确认移除 (或按回车键取消):" if IS_ZH else "Enter y to confirm (or Enter to cancel):").lower()
            if confirm in ('y', 'yes'):
                if remove_skill_from_group(target_grp, cleaned):
                    if IS_ZH:
                        print(f"\n\033[1;32m[✓] 技能 '{cleaned}' 已成功从分组 '{target_grp}' 中移除！\033[0m")
                    else:
                        print(f"\n\033[1;32m[✓] Skill '{cleaned}' removed from group '{target_grp}'!\033[0m")
                else:
                    if IS_ZH:
                        print("\n\033[1;31m[✗] 移除失败。\033[0m")
                    else:
                        print("\n\033[1;31m[✗] Removal failed.\033[0m")
            else:
                if IS_ZH:
                    print("\n\033[1;33m[*] 操作已取消。\033[0m")
                else:
                    print("\n\033[1;33m[*] Operation cancelled.\033[0m")
            safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
            return
        else:
            print("\033[1;33m╭──────────────── ⚠️  从分组中移除技能 ────────────────╮\033[0m")
            if IS_ZH:
                print(f"\033[1;37m│  技能 '\033[1;33m{cleaned}\033[1;37m' 当前属于以下多个分组：\033[0m")
                for idx, g in enumerate(in_groups, 1):
                    print(f"│    {idx}) \033[1;36m{g}\033[0m")
                print("\033[1;90m│  (仅从分组定义中移除，不会删除技能本地文件)\033[0m")
                print("\033[1;33m╰─────────────────────────────────────────────────────╯\033[0m")
                pick_prompt = "请选择要移出的分组 (输入序号如 '1' / a: 全部移出 / 回车取消):"
            else:
                print(f"\033[1;37m│  Skill '\033[1;33m{cleaned}\033[1;37m' belongs to multiple groups:\033[0m")
                for idx, g in enumerate(in_groups, 1):
                    print(f"│    {idx}) \033[1;36m{g}\033[0m")
                print("\033[1;90m│  (Only removes from group, does not delete skill files)\033[0m")
                print("\033[1;33m╰─────────────────────────────────────────────────────╯\033[0m")
                pick_prompt = "Select group to remove from (index '1' / a: all / Enter to cancel):"

            pick_ans = safe_input(pick_prompt).strip().lower()
            if not pick_ans:
                if IS_ZH:
                    print("\n\033[1;33m[*] 操作已取消。\033[0m")
                    safe_input("\n按回车键返回 FZF...")
                else:
                    print("\n\033[1;33m[*] Operation cancelled.\033[0m")
                    safe_input("\nPress Enter to return to FZF...")
                return

            if pick_ans in ('a', 'all'):
                remove_skill_from_all_groups(cleaned)
                if IS_ZH:
                    print(f"\n\033[1;32m[✓] 技能 '{cleaned}' 已成功从所有分组中移除！\033[0m")
                    safe_input("\n按回车键返回 FZF...")
                else:
                    print(f"\n\033[1;32m[✓] Skill '{cleaned}' removed from all groups!\033[0m")
                    safe_input("\nPress Enter to return to FZF...")
                return

            try:
                pick_idx = int(pick_ans) - 1
                if 0 <= pick_idx < len(in_groups):
                    target_grp = in_groups[pick_idx]
                    if remove_skill_from_group(target_grp, cleaned):
                        if IS_ZH:
                            print(f"\n\033[1;32m[✓] 技能 '{cleaned}' 已成功从分组 '{target_grp}' 中移除！\033[0m")
                        else:
                            print(f"\n\033[1;32m[✓] Skill '{cleaned}' removed from group '{target_grp}'!\033[0m")
                    else:
                        if IS_ZH:
                            print("\n\033[1;31m[✗] 移除失败。\033[0m")
                        else:
                            print("\n\033[1;31m[✗] Removal failed.\033[0m")
                else:
                    if IS_ZH:
                        print("\n\033[1;31m[✗] 无效的序号。\033[0m")
                    else:
                        print("\n\033[1;31m[✗] Invalid index.\033[0m")
            except ValueError:
                if IS_ZH:
                    print("\n\033[1;31m[✗] 输入有误。\033[0m")
                else:
                    print("\n\033[1;31m[✗] Invalid input.\033[0m")

            safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
            return
        
    gkey = cleaned[6:]
    groups = load_groups()
    if gkey not in groups:
        if IS_ZH:
            print(f"\033[1;31m[✗] 错误: 分组 '{gkey}' 不存在。\033[0m")
            safe_input("\n按回车键返回 FZF...")
        else:
            print(f"\033[1;31m[✗] Error: Group '{gkey}' does not exist.\033[0m")
            safe_input("\nPress Enter to return to FZF...")
        return
        
    print("\033[1;31m╭──────────────── ⚠️  删除技能分组确认 ────────────────╮\033[0m")
    if IS_ZH:
        print(f"\033[1;37m│  确定要删除技能分组 '\033[1;31m{gkey}\033[1;37m' 吗？\033[0m")
        print("\033[1;90m│  (仅删除分组定义，不会删除任何技能本体文件)\033[0m")
    else:
        print(f"\033[1;37m│  Are you sure you want to delete group '\033[1;31m{gkey}\033[1;37m'?\033[0m")
        print("\033[1;90m│  (Only removes group definition, preserves skill files)\033[0m")
    print("\033[1;31m╰─────────────────────────────────────────────────────╯\033[0m")
    
    try:
        if IS_ZH:
            confirm = safe_input("请输入 y 确认删除 (或按回车键取消):").lower()
        else:
            confirm = safe_input("Please enter y to confirm deletion (or press Enter to cancel):").lower()
        if confirm in ('y', 'yes'):
            if delete_group(gkey):
                if IS_ZH:
                    print(f"\n\033[1;32m[✓] 分组 '{gkey}' 已成功删除！\033[0m")
                else:
                    print(f"\n\033[1;32m[✓] Group '{gkey}' deleted successfully!\033[0m")
            else:
                if IS_ZH:
                    print("\n\033[1;31m[✗] 删除失败。\033[0m")
                else:
                    print("\n\033[1;31m[✗] Deletion failed.\033[0m")
        else:
            if IS_ZH:
                print("\n\033[1;33m[*] 操作已取消。\033[0m")
            else:
                print("\n\033[1;33m[*] Operation cancelled.\033[0m")
    except KeyboardInterrupt:
        if IS_ZH:
            print("\n\033[1;33m[*] 操作已取消。\033[0m")
        else:
            print("\n\033[1;33m[*] Operation cancelled.\033[0m")
    if IS_ZH:
        safe_input("\n按回车键返回 FZF...")
    else:
        safe_input("\nPress Enter to return to FZF...")

def view_connected():
    list_connected_skills()


def find_connected_dir():
    """Find .agents/skills in current directory or parent directories up to git root."""
    return get_project_skills_dir()

def list_connected_skills():
    """Display skills currently connected in project with sleek modern streamlined layout."""
    connected_dir = get_project_skills_dir()
    connected_list = get_connected_skills()
    if not os.path.exists(connected_dir) or not os.path.isdir(connected_dir):
        if IS_ZH:
            print("[mskill] 当前项目下未检测到已连接的技能目录 (.agents/skills)。")
            print("\033[0;90m💡 提示: 在项目根目录下运行 'mskill' 即可选择并引入所需技能。\033[0m\n")
        else:
            print("[mskill] No connected skills found in current project (.agents/skills).")
            print("\033[0;90m💡 Tip: Run 'mskill' in project root to select and connect skills.\033[0m\n")
        return

    if not connected_list:
        if IS_ZH:
            print("[mskill] 当前项目已连接技能目录为空。")
        else:
            print("[mskill] Project .agents/skills directory is currently empty.")
        return

    # Load translations if available
    translations = {}
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import preview_skill
        translations = preview_skill.load_user_translations()
    except Exception:
        pass

    # Count symlinks vs copies
    symlink_count = sum(1 for item in connected_list if item.get("is_link"))
    copy_count = len(connected_list) - symlink_count

    # ANSI Palette
    CYAN = "\033[1;36m"
    GREEN = "\033[1;32m"
    BLUE = "\033[1;34m"
    MAGENTA = "\033[1;35m"
    WHITE = "\033[1;37m"
    GREY = "\033[0;90m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    import shutil
    term_width = shutil.get_terminal_size((100, 24)).columns

    # Header badge bar
    if IS_ZH:
        print(f"\n  {BOLD}{WHITE}🔗 项目已挂载技能清单 (Connected Skills){RESET}  "
              f"{CYAN}[总计: {WHITE}{len(connected_list)}{CYAN}]{RESET}  "
              f"{BLUE}[🔗 软链接: {WHITE}{symlink_count}{BLUE}]{RESET}  "
              f"{MAGENTA}[📁 实体副本: {WHITE}{copy_count}{MAGENTA}]{RESET}\n")
    else:
        print(f"\n  {BOLD}{WHITE}🔗 Connected Project Skills{RESET}  "
              f"{CYAN}[Total: {WHITE}{len(connected_list)}{CYAN}]{RESET}  "
              f"{BLUE}[🔗 Symlinks: {WHITE}{symlink_count}{BLUE}]{RESET}  "
              f"{MAGENTA}[📁 Copies: {WHITE}{copy_count}{MAGENTA}]{RESET}\n")

    header_name = "技能名称 (Skill Name)" if IS_ZH else "Skill Name"
    header_mode = "挂载方式" if IS_ZH else "Mount Mode"
    header_desc = "说明 / 中文描述" if IS_ZH else "Description"

    max_name_len = max((len(item["name"]) for item in connected_list), default=20)
    col_name_w = max(get_display_width(header_name), min(max_name_len, 32))
    col_mode_w = 14

    h_name = pad_display(f"{BOLD}{WHITE}{header_name}{RESET}", col_name_w)
    h_mode = pad_display(f"{BOLD}{WHITE}{header_mode}{RESET}", col_mode_w)
    h_desc = f"{BOLD}{WHITE}{header_desc}{RESET}"

    divider_w = min(term_width - 4, col_name_w + col_mode_w + 45)
    print(f"  {h_name}  {h_mode}  {h_desc}")
    print(f"  {GREY}{'─' * divider_w}{RESET}")

    for item in connected_list:
        skill = item["name"]
        full_path = item["path"]
        is_link = item.get("is_link", False)
        badge = f"{BLUE}🔗 软链接{RESET}" if is_link else f"{MAGENTA}📁 实体副本{RESET}" if IS_ZH else (f"{BLUE}🔗 Symlink{RESET}" if is_link else f"{MAGENTA}📁 Physical Copy{RESET}")

        name_zh = translations.get(skill, {}).get("name_zh", "")
        desc_zh = translations.get(skill, {}).get("desc_zh", "")

        # Fallback to local SKILL.md frontmatter if translation missing
        if (not name_zh or not desc_zh) and os.path.isdir(full_path):
            for doc_name in ["SKILL.zh.md", "SKILL.zh-CN.md", "SKILL.md"]:
                doc_path = os.path.join(full_path, doc_name)
                if os.path.exists(doc_path):
                    fm = parse_frontmatter(doc_path)
                    if fm:
                        if not name_zh:
                            name_zh = fm.get("name", "")
                        if not desc_zh:
                            desc_zh = fm.get("description", "")
                        break

        c_name = pad_display(f"{GREEN}{skill}{RESET}", col_name_w)
        c_mode = pad_display(badge, col_mode_w)
        c_desc = f"{WHITE}{name_zh}{RESET}" if name_zh else f"{GREY}—{RESET}"

        print(f"  {c_name}  {c_mode}  {c_desc}")
        if desc_zh:
            desc_single = " ".join([l.strip() for l in desc_zh.split("\n") if l.strip()])
            desc_cut = truncate_display(desc_single, term_width - 8)
            print(f"    {GREY}↳ {desc_cut}{RESET}")

    print(f"  {GREY}{'─' * divider_w}{RESET}")
    if IS_ZH:
        print(f"  {GREY}💡 快捷指令: 'mskill <名称>' 软链接 | 'mskill -c <名称>' 实体拷贝 | 'mskill' 打开 FZF{RESET}\n")
    else:
        print(f"  {GREY}💡 Shortcuts: 'mskill <name>' symlink | 'mskill -c <name>' copy | 'mskill' open FZF{RESET}\n")

def list_groups_detailed():
    groups = load_groups()
    if not groups:
        if IS_ZH:
            print("\n  \033[1;33m没有定义任何技能分组。\033[0m\n")
        else:
            print("\n  \033[1;33mNo skill groups defined.\033[0m\n")
        return

    import shutil
    term_width = shutil.get_terminal_size((100, 24)).columns

    GREEN = "\033[1;32m"
    CYAN = "\033[1;36m"
    YELLOW = "\033[1;33m"
    MAGENTA = "\033[1;35m"
    WHITE = "\033[1;37m"
    GREY = "\033[0;90m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    translations = {}
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import preview_skill
        translations = preview_skill.load_user_translations()
    except Exception:
        pass

    if IS_ZH:
        print(f"\n  {BOLD}{WHITE}📂 AI Agent 技能分组清单{RESET}  {CYAN}[共 {len(groups)} 个分组]{RESET}\n")
    else:
        print(f"\n  {BOLD}{WHITE}📂 AI Agent Skill Groups{RESET}  {CYAN}[Total: {len(groups)} groups]{RESET}\n")

    for gid, info in sorted(groups.items()):
        if isinstance(info, dict):
            name = info.get("name", gid)
            skills = info.get("skills", [])
            is_ordered = info.get("ordered", False)
        else:
            name = gid
            skills = info
            is_ordered = False

        ordered_badge = f"{YELLOW}[⚑ 推荐调用顺序 · 有序]{RESET}" if is_ordered else f"{MAGENTA}[⚡ 组合集合 · 无序]{RESET}"
        if not IS_ZH:
            ordered_badge = f"{YELLOW}[⚑ Ordered Workflow]{RESET}" if is_ordered else f"{MAGENTA}[⚡ Unordered Skill Set]{RESET}"

        display_header = f"  📂 {GREEN}{gid}{RESET} {WHITE}({name}){RESET}  {ordered_badge}  {GREY}({len(skills)} 个技能){RESET}" if IS_ZH else f"  📂 {GREEN}{gid}{RESET} {WHITE}({name}){RESET}  {ordered_badge}  {GREY}({len(skills)} skills){RESET}"
        print(display_header)
        divider_w = min(term_width - 4, get_display_width(display_header) + 4)
        divider_w = max(divider_w, 48)
        print(f"  {GREY}{'─' * divider_w}{RESET}")

        for idx, s in enumerate(skills, 1):
            s_zh = translations.get(s, {}).get("name_zh", "")
            s_title = f" {GREY}({s_zh}){RESET}" if s_zh else ""
            if is_ordered:
                prefix = f"{YELLOW}{circled_num(idx)}{RESET}"
            else:
                prefix = f"{GREEN}•{RESET}"
            print(f"    {prefix} {WHITE}{s}{RESET}{s_title}")

        if IS_ZH:
            print(f"    {GREY}↳ 一键引用: mskill {gid} (软链接) │ mskill -c {gid} (实体拷贝){RESET}")
        else:
            print(f"    {GREY}↳ Quick link: mskill {gid} (symlink) │ mskill -c {gid} (copy entity){RESET}")
        print()

def cmd_list_groups_completion():
    for line in get_groups_completion_data():
        print(line)
    return 0

def cmd_list_groups_detailed():
    list_groups_detailed()
    return 0

def cmd_set_group(args):
    if not args:
        print("Error: --set-group requires a group name", file=sys.stderr)
        return 1
    rest_args = list(args)
    is_ordered = False
    if "--ordered" in rest_args:
        is_ordered = True
        rest_args = [a for a in rest_args if a != "--ordered"]
    gname = rest_args[0] if rest_args else ""
    skills = [clean_item_id(a) for a in rest_args[1:] if clean_item_id(a)]
    if not gname:
        print("Error: --set-group requires a group name", file=sys.stderr)
        return 1
    if not skills:
        print("Error: Please provide at least one skill name", file=sys.stderr)
        return 1

    if save_group_definition(gname, skills, is_ordered=is_ordered):
        ordered_label = ("有序" if IS_ZH else "ordered ") if is_ordered else ""
        if IS_ZH:
            print(f"[✓] 成功保存{ordered_label}分组 '{gname}'，包含 {len(skills)} 个技能。")
        else:
            print(f"[✓] Successfully saved {ordered_label}group '{gname}' containing {len(skills)} skills.")
        return 0
    return 1

def cmd_rm_group(raw_gname):
    if not raw_gname:
        print("Error: --rm-group requires a group name", file=sys.stderr)
        return 1
    gname = clean_item_id(raw_gname).removeprefix("group:")
    if delete_group(gname):
        if IS_ZH:
            print(f"[✓] 已成功删除分组 '{gname}'。")
        else:
            print(f"[✓] Successfully deleted group '{gname}'.")
        return 0
    else:
        if IS_ZH:
            print(f"[✗] 错误: 分组 '{gname}' 不存在或删除失败。", file=sys.stderr)
        else:
            print(f"[✗] Error: Group '{gname}' does not exist or deletion failed.", file=sys.stderr)
        return 1

def cmd_interactive_set(args):
    interactive_set(args)
    return 0

def cmd_interactive_rm(focused_item):
    if not focused_item:
        print("Error: --interactive-rm requires focused item name", file=sys.stderr)
        return 1
    if isinstance(focused_item, str):
        focused_item = [focused_item]

    cleaned_items = [clean_item_id(it) for it in focused_item if clean_item_id(it)]
    if not cleaned_items:
        return 0

    if len(cleaned_items) == 1:
        interactive_rm(cleaned_items[0])
        return 0

    # Multiple items selected: handle groups and skills cleanly
    groups = load_groups()
    group_keys_to_delete = []
    skills_to_remove = []

    for it in cleaned_items:
        if it.startswith("group:"):
            gkey = it[6:]
            if gkey in groups and gkey not in group_keys_to_delete:
                group_keys_to_delete.append(gkey)
        elif it in groups:
            if it not in group_keys_to_delete:
                group_keys_to_delete.append(it)
        else:
            if it not in skills_to_remove:
                skills_to_remove.append(it)

    # 1. If there are groups to delete
    if group_keys_to_delete:
        print("\033[1;31m╭──────────────── ⚠️  批量删除技能分组确认 ────────────────╮\033[0m")
        if IS_ZH:
            print(f"\033[1;37m│  确定要删除以下 {len(group_keys_to_delete)} 个技能分组吗？\033[0m")
            for g in group_keys_to_delete:
                print(f"│    • \033[1;31m{g}\033[0m")
            print("\033[1;90m│  (仅删除分组定义，不会删除任何技能本体文件)\033[0m")
        else:
            print(f"\033[1;37m│  Are you sure you want to delete {len(group_keys_to_delete)} group(s)?\033[0m")
            for g in group_keys_to_delete:
                print(f"│    • \033[1;31m{g}\033[0m")
            print("\033[1;90m│  (Only removes group definitions, preserves skill files)\033[0m")
        print("\033[1;31m╰────────────────────────────────────────────────────────╯\033[0m")

        confirm = safe_input("请输入 y 确认批量删除 (或按回车键取消):" if IS_ZH else "Enter y to confirm deletion (or Enter to cancel):").lower()
        if confirm in ('y', 'yes'):
            for g in group_keys_to_delete:
                delete_group(g)
            if IS_ZH:
                print(f"\n\033[1;32m[✓] 成功删除 {len(group_keys_to_delete)} 个技能分组！\033[0m")
            else:
                print(f"\n\033[1;32m[✓] Successfully deleted {len(group_keys_to_delete)} group(s)!\033[0m")
        else:
            if IS_ZH:
                print("\n\033[1;33m[*] 操作已取消。\033[0m")
            else:
                print("\n\033[1;33m[*] Operation cancelled.\033[0m")

    # 2. If there are skills to remove from groups
    if skills_to_remove:
        skill_group_map = {}
        for s in skills_to_remove:
            grps = find_groups_for_skill(s)
            if grps:
                skill_group_map[s] = grps

        if not skill_group_map:
            if IS_ZH:
                print("\033[1;33m[*] 所选技能均不属于任何技能分组。\033[0m")
            else:
                print("\033[1;33m[*] Selected skills do not belong to any groups.\033[0m")
        else:
            print("\033[1;33m╭──────────────── ⚠️  从分组中批量移除技能确认 ────────────────╮\033[0m")
            if IS_ZH:
                print(f"\033[1;37m│  检测到以下 {len(skill_group_map)} 个技能属于已有分组：\033[0m")
                for s, grps in skill_group_map.items():
                    print(f"│    • \033[1;33m{s}\033[0m \033[0;90m(现属分组: {', '.join(grps)})\033[0m")
                print("\033[1;90m│  (仅从分组定义中移除，不会删除技能本地文件)\033[0m")
            else:
                print(f"\033[1;37m│  Found {len(skill_group_map)} skill(s) belonging to groups:\033[0m")
                for s, grps in skill_group_map.items():
                    print(f"│    • \033[1;33m{s}\033[0m \033[0;90m(in groups: {', '.join(grps)})\033[0m")
                print("\033[1;90m│  (Only removes from groups, preserves local files)\033[0m")
            print("\033[1;33m╰────────────────────────────────────────────────────────────╯\033[0m")

            confirm = safe_input("请输入 y 确认从其所属的所有分组中移除 (或按回车键取消):" if IS_ZH else "Enter y to remove from all their groups (or Enter to cancel):").lower()
            if confirm in ('y', 'yes'):
                for s in skill_group_map:
                    remove_skill_from_all_groups(s)
                if IS_ZH:
                    print(f"\n\033[1;32m[✓] 已成功将所选技能从其所属分组中移除！\033[0m")
                else:
                    print(f"\n\033[1;32m[✓] Successfully removed selected skills from groups!\033[0m")
            else:
                if IS_ZH:
                    print("\n\033[1;33m[*] 操作已取消。\033[0m")
                else:
                    print("\n\033[1;33m[*] Operation cancelled.\033[0m")

    safe_input("\n按回车键返回 FZF..." if IS_ZH else "\nPress Enter to return to FZF...")
    return 0

def cmd_group_add(args):
    """CLI handler: mskill --group-add <group> <skills...>"""
    if len(args) < 2:
        if IS_ZH:
            print("[mskill] 错误: 需要指定分组名称和至少一个技能名称。用法: mskill --group-add <组名> <技能...>", file=sys.stderr)
        else:
            print("[mskill] Error: Group name and at least one skill name required. Usage: mskill --group-add <group> <skills...>", file=sys.stderr)
        return 1
    gname = clean_item_id(args[0]).removeprefix("group:")
    skills = [clean_item_id(s) for s in args[1:] if clean_item_id(s)]
    if add_skills_to_group(gname, skills):
        s_str = ", ".join(f"'{s}'" for s in skills)
        if IS_ZH:
            print(f"[✓] 成功将技能 {s_str} 加入分组 '{gname}'。")
        else:
            print(f"[✓] Successfully added skill(s) {s_str} to group '{gname}'.")
        return 0
    else:
        if IS_ZH:
            print(f"[!] 分组 '{gname}' 不存在，或指定技能已全部在分组中。", file=sys.stderr)
        else:
            print(f"[!] Group '{gname}' does not exist, or skill(s) already in group.", file=sys.stderr)
        return 1

def cmd_group_remove(args):
    """CLI handler: mskill --group-remove <group> <skills...>"""
    if len(args) < 2:
        if IS_ZH:
            print("[mskill] 错误: 需要指定分组名称和至少一个技能名称。用法: mskill --group-remove <组名> <技能...>", file=sys.stderr)
        else:
            print("[mskill] Error: Group name and at least one skill name required. Usage: mskill --group-remove <group> <skills...>", file=sys.stderr)
        return 1
    gname = clean_item_id(args[0]).removeprefix("group:")
    skills = [clean_item_id(s) for s in args[1:] if clean_item_id(s)]
    removed_any = False
    for s in skills:
        if remove_skill_from_group(gname, s):
            removed_any = True
    if removed_any:
        s_str = ", ".join(f"'{s}'" for s in skills)
        if IS_ZH:
            print(f"[✓] 成功从分组 '{gname}' 中移除技能 {s_str}。")
        else:
            print(f"[✓] Successfully removed skill(s) {s_str} from group '{gname}'.")
        return 0
    else:
        if IS_ZH:
            print(f"[!] 分组 '{gname}' 中未找到指定的技能，或分组不存在。", file=sys.stderr)
        else:
            print(f"[!] Skill(s) not found in group '{gname}', or group does not exist.", file=sys.stderr)
        return 1

def cmd_view_connected():
    view_connected()
    return 0

def print_help():
    print("Usage: resolve_skills.py [options] [inputs...]")
    print("Options:")
    print("  --list-groups              List all group IDs (one per line)")
    print("  --list-groups-detailed     Show details of all groups and their skills")
    print("  --set-group <name> <sk...> Create or update a group with specified skills")
    print("  --rm-group <name>          Remove a group")
    print("  --interactive-set <sk...>  Interactive group creation in FZF")
    print("  --interactive-rm <name>    Interactive group removal in FZF")
    print("  --view-connected           View connected skills with Chinese translation")
    print("  --help                     Show this help message")

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    arg1 = sys.argv[1]

    if arg1 in ("--help", "-h"):
        print_help()
        sys.exit(0)

    elif arg1 == "--list-groups":
        for gid in sorted(get_all_groups().keys()):
            print(gid)
        sys.exit(0)

    elif arg1 == "--list-groups-completion":
        sys.exit(cmd_list_groups_completion())

    elif arg1 == "--list-groups-detailed":
        sys.exit(cmd_list_groups_detailed())

    elif arg1 == "--set-group":
        sys.exit(cmd_set_group(sys.argv[2:]))

    elif arg1 == "--rm-group":
        gname = sys.argv[2] if len(sys.argv) >= 3 else ""
        sys.exit(cmd_rm_group(gname))

    elif arg1 == "--interactive-set":
        sys.exit(cmd_interactive_set(sys.argv[2:]))

    elif arg1 == "--interactive-rm":
        focused = sys.argv[2] if len(sys.argv) >= 3 else ""
        sys.exit(cmd_interactive_rm(focused))

    elif arg1 == "--view-connected":
        sys.exit(cmd_view_connected())

    # Otherwise, resolve the list of inputs
    for skill in resolve_group_targets(sys.argv[1:]):
        print(skill)

if __name__ == "__main__":
    main()


