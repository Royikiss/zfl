#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 描述: 负责解析并展开技能分组及具体技能名称，同时提供分组增删查管理接口

import os
import sys
import json

GROUPS_FILE = os.path.expanduser("~/.cache/zsh/skills_groups.json")

DEFAULT_GROUPS = {
    "startup": {
        "name": "极简创业者 (Startup)",
        "skills": [
            "validate-idea",
            "find-community",
            "first-customers",
            "marketing-plan",
            "pricing",
            "processize",
            "grow-sustainably",
            "minimalist-review"
        ]
    },
    "dev": {
        "name": "日常开发协作 (Development)",
        "skills": [
            "prototype",
            "improve-codebase-architecture",
            "gemini-prompt-optimizer",
            "grill-me",
            "grill-with-docs",
            "handoff",
            "nuwa-skill"
        ]
    }
}

def load_groups():
    """
    Load group configurations from ~/.cache/zsh/skills_groups.json.
    If it doesn't exist, create it with default groups.
    """
    if not os.path.exists(GROUPS_FILE):
        try:
            os.makedirs(os.path.dirname(GROUPS_FILE), exist_ok=True)
            with open(GROUPS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_GROUPS, f, indent=2, ensure_ascii=False)
            return DEFAULT_GROUPS
        except Exception:
            return DEFAULT_GROUPS
    try:
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}

def save_groups(groups):
    """
    Save group configurations back to ~/.cache/zsh/skills_groups.json.
    """
    try:
        os.makedirs(os.path.dirname(GROUPS_FILE), exist_ok=True)
        with open(GROUPS_FILE, "w", encoding="utf-8") as f:
            json.dump(groups, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving groups file: {e}", file=sys.stderr)
        return False

def interactive_set(selected_args):
    # Filter out empty arguments or option arguments
    skills = []
    groups = load_groups()
    
    # Expand any selected group to its member skills
    for item in selected_args:
        if not item or item.startswith("-"):
            continue
        if item.startswith("group:"):
            gkey = item[6:]
            if gkey in groups:
                ginfo = groups[gkey]
                skills.extend(ginfo.get("skills", []) if isinstance(ginfo, dict) else ginfo)
        elif item in groups:
            ginfo = groups[item]
            skills.extend(ginfo.get("skills", []) if isinstance(ginfo, dict) else ginfo)
        else:
            skills.append(item)
            
    # Deduplicate skills while preserving order
    unique_skills = []
    seen = set()
    for s in skills:
        if s not in seen:
            seen.add(s)
            unique_skills.append(s)
            
    if not unique_skills:
        print("\033[1;31m错误：未选中任何技能，请先使用空格键在列表中选择技能！\033[0m")
        input("\n按回车键返回 FZF...")
        return
        
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    print("\033[1;32m即将为以下技能创建/更新分组：\033[0m")
    for s in unique_skills:
        print(f"  • {s}")
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    
    try:
        gname = input("请输入要创建/修改的分组名称 (或按回车键取消): ").strip()
        if not gname:
            print("\033[1;33m操作已取消。\033[0m")
            input("\n按回车键返回 FZF...")
            return
            
        disp_name = gname
        if gname in groups and isinstance(groups[gname], dict):
            disp_name = groups[gname].get("name", gname)
            
        groups[gname] = {
            "name": disp_name,
            "skills": unique_skills
        }
        if save_groups(groups):
            print(f"\n\033[1;32m成功保存分组 '{gname}'，包含 {len(unique_skills)} 个技能！\033[0m")
        else:
            print("\n\033[1;31m保存失败。\033[0m")
    except KeyboardInterrupt:
        print("\n\033[1;33m操作已取消。\033[0m")
        
    input("\n按回车键返回 FZF...")

def interactive_rm(focused_item):
    if not focused_item.startswith("group:"):
        print("\033[1;31m错误：当前所选项不是一个技能分组，无法删除！\033[0m")
        print(f"所选项: {focused_item}")
        input("\n按回车键返回 FZF...")
        return
        
    gkey = focused_item[6:]
    groups = load_groups()
    if gkey not in groups:
        print(f"\033[1;31m错误：分组 '{gkey}' 不存在。\033[0m")
        input("\n按回车键返回 FZF...")
        return
        
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    print(f"\033[1;31m确定要删除技能分组 '{gkey}' 吗？\033[0m")
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    
    try:
        confirm = input("请输入 y 确认删除 (或按回车键取消): ").strip().lower()
        if confirm in ('y', 'yes'):
            del groups[gkey]
            if save_groups(groups):
                print(f"\n\033[1;32m分组 '{gkey}' 已成功删除！\033[0m")
            else:
                print("\n\033[1;31m删除失败。\033[0m")
        else:
            print("\n\033[1;33m操作已取消。\033[0m")
    except KeyboardInterrupt:
        print("\n\033[1;33m操作已取消。\033[0m")
        
    input("\n按回车键返回 FZF...")

def print_help():
    print("Usage: resolve_skills.py [options] [inputs...]")
    print("Options:")
    print("  --list-groups              List all group IDs (one per line)")
    print("  --list-groups-detailed     Show details of all groups and their skills")
    print("  --set-group <name> <sk...> Create or update a group with specified skills")
    print("  --rm-group <name>          Remove a group")
    print("  --interactive-set <sk...>  Interactive group creation in FZF")
    print("  --interactive-rm <name>    Interactive group removal in FZF")
    print("  --help                     Show this help message")

def main():
    groups = load_groups()

    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    arg1 = sys.argv[1]

    if arg1 == "--help" or arg1 == "-h":
        print_help()
        sys.exit(0)

    elif arg1 == "--list-groups":
        for gid in sorted(groups.keys()):
            print(gid)
        sys.exit(0)

    elif arg1 == "--list-groups-detailed":
        if not groups:
            print("没有定义任何技能分组。")
            sys.exit(0)
        # ANSI colors
        GREEN = "\033[1;32m"
        CYAN = "\033[1;36m"
        RESET = "\033[0m"
        print(f"{CYAN}=== 技能分组列表 ==={RESET}")
        for gid, info in sorted(groups.items()):
            if isinstance(info, dict):
                name = info.get("name", gid)
                skills = info.get("skills", [])
            else:
                name = gid
                skills = info
            skills_str = ", ".join(skills)
            print(f"{GREEN}• {gid}{RESET} ({name}):")
            print(f"  包含技能: {skills_str}")
        sys.exit(0)

    elif arg1 == "--set-group":
        if len(sys.argv) < 3:
            print("Error: --set-group requires a group name", file=sys.stderr)
            sys.exit(1)
        gname = sys.argv[2]
        skills = sys.argv[3:]
        if not skills:
            print("Error: Please provide at least one skill name", file=sys.stderr)
            sys.exit(1)
        
        # Preserve original name if group already exists
        disp_name = gname
        if gname in groups and isinstance(groups[gname], dict):
            disp_name = groups[gname].get("name", gname)

        groups[gname] = {
            "name": disp_name,
            "skills": skills
        }
        if save_groups(groups):
            print(f"成功保存分组 '{gname}'，包含 {len(skills)} 个技能。")
            sys.exit(0)
        else:
            sys.exit(1)

    elif arg1 == "--rm-group":
        if len(sys.argv) < 3:
            print("Error: --rm-group requires a group name", file=sys.stderr)
            sys.exit(1)
        gname = sys.argv[2]
        if gname in groups:
            del groups[gname]
            if save_groups(groups):
                print(f"已成功删除分组 '{gname}'。")
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            print(f"错误: 分组 '{gname}' 不存在。", file=sys.stderr)
            sys.exit(1)

    elif arg1 == "--interactive-set":
        interactive_set(sys.argv[2:])
        sys.exit(0)

    elif arg1 == "--interactive-rm":
        if len(sys.argv) < 3:
            print("Error: --interactive-rm requires focused item name", file=sys.stderr)
            sys.exit(1)
        interactive_rm(sys.argv[2])
        sys.exit(0)

    # Otherwise, resolve the list of inputs
    inputs = sys.argv[1:]
    resolved = []
    for item in inputs:
        # Check if it starts with group:
        if item.startswith("group:"):
            gkey = item[len("group:"):]
            if gkey in groups:
                ginfo = groups[gkey]
                skills = ginfo.get("skills", []) if isinstance(ginfo, dict) else ginfo
                resolved.extend(skills)
            else:
                # Group doesn't exist, treat it as a literal skill
                resolved.append(item)
        elif item in groups:
            ginfo = groups[item]
            skills = ginfo.get("skills", []) if isinstance(ginfo, dict) else ginfo
            resolved.extend(skills)
        else:
            resolved.append(item)

    # Deduplicate while preserving order
    seen = set()
    for skill in resolved:
        if skill not in seen:
            seen.add(skill)
            print(skill)

if __name__ == "__main__":
    main()
