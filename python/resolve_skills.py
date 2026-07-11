#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Description: Parse and expand skill groups and skill names, and provide interfaces to manage groups

import os
import sys
import json

# Detect language
LANG = os.environ.get("ZFL_LANG") or os.environ.get("LANG", "en")
IS_ZH = LANG.startswith("zh")

GROUPS_FILE = os.path.expanduser("~/.cache/zsh/skills_groups.json")

DEFAULT_GROUPS = {
    "startup": {
        "name": "极简创业者" if IS_ZH else "Minimalist Entrepreneur",
        "ordered": True,
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
        "name": "日常开发协作" if IS_ZH else "Daily Development Collaboration",
        "ordered": False,
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

def circled_num(n):
    """Return a circled number character for n (1-20), else fallback to (n)."""
    if 1 <= n <= 20:
        return chr(0x245F + n)  # U+2460 = ①
    return f"({n})"

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
                migrated = False
                # Migrate default names based on current language preference
                for k in ("startup", "dev"):
                    if k in data and isinstance(data[k], dict):
                        curr_name = data[k].get("name")
                        if not IS_ZH and curr_name in ("极简创业者", "极简创业者 (Startup)"):
                            data[k]["name"] = "Minimalist Entrepreneur"
                            migrated = True
                        elif not IS_ZH and curr_name in ("日常开发协作", "日常开发协作 (Development)"):
                            data[k]["name"] = "Daily Development Collaboration"
                            migrated = True
                        elif IS_ZH and curr_name in ("Minimalist Entrepreneur", "极简创业者 (Startup)"):
                            data[k]["name"] = "极简创业者"
                            migrated = True
                        elif IS_ZH and curr_name in ("Daily Development Collaboration", "日常开发协作 (Development)"):
                            data[k]["name"] = "日常开发协作"
                            migrated = True
                if migrated:
                    save_groups(data)
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
        if IS_ZH:
            print("\033[1;31m错误：未选中任何技能，请先使用空格键在列表中选择技能！\033[0m")
            input("\n按回车键返回 FZF...")
        else:
            print("\033[1;31mError: No skills selected. Please select skills using Space first!\033[0m")
            input("\nPress Enter to return to FZF...")
        return
    
    # --- Step 1: Show selected skills and allow reordering by index ---
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    if IS_ZH:
        print(f"\033[1;32m已选中 {len(unique_skills)} 个技能：\033[0m")
    else:
        print(f"\033[1;32mSelected {len(unique_skills)} skills:\033[0m")
    for i, s in enumerate(unique_skills, 1):
        print(f"  {i}) {s}")
    print("\033[1;36m" + "=" * 55 + "\033[0m")

    try:
        if IS_ZH:
            reorder_input = input('请输入新的排列顺序（如 "3 1 2"，直接回车保持现有顺序）: ').strip()
        else:
            reorder_input = input('Enter new order (e.g. "3 1 2", or press Enter to keep current): ').strip()
        if reorder_input:
            try:
                indices = [int(x) - 1 for x in reorder_input.split()]
                if sorted(indices) == list(range(len(unique_skills))):
                    unique_skills = [unique_skills[i] for i in indices]
                    if IS_ZH:
                        print("\033[1;32m已重新排列：\033[0m")
                    else:
                        print("\033[1;32mReordered:\033[0m")
                    for i, s in enumerate(unique_skills, 1):
                        print(f"  {i}) {s}")
                else:
                    if IS_ZH:
                        print("\033[1;33m序号不合法，已忽略，保持原有顺序。\033[0m")
                    else:
                        print("\033[1;33mInvalid indices, keeping original order.\033[0m")
            except ValueError:
                if IS_ZH:
                    print("\033[1;33m输入有误，已忽略，保持原有顺序。\033[0m")
                else:
                    print("\033[1;33mInvalid input, keeping original order.\033[0m")

        # --- Step 2: Ask if this group is ordered ---
        if IS_ZH:
            ordered_ans = input("是否设为有序分组（即上方顺序为推荐调用顺序）？(y/N): ").strip().lower()
        else:
            ordered_ans = input("Mark as ordered group (above order = recommended call order)? (y/N): ").strip().lower()
        is_ordered = ordered_ans in ('y', 'yes')

        # --- Step 3: Ask for group name ---
        if IS_ZH:
            gname = input("请输入要创建/修改的分组名称 (或按回车键取消): ").strip()
        else:
            gname = input("Please enter group name to create/modify (or press Enter to cancel): ").strip()
        if not gname:
            if IS_ZH:
                print("\033[1;33m操作已取消。\033[0m")
                input("\n按回车键返回 FZF...")
            else:
                print("\033[1;33mOperation cancelled.\033[0m")
                input("\nPress Enter to return to FZF...")
            return
            
        disp_name = gname
        if gname in groups and isinstance(groups[gname], dict):
            disp_name = groups[gname].get("name", gname)
            
        groups[gname] = {
            "name": disp_name,
            "ordered": is_ordered,
            "skills": unique_skills
        }
        if save_groups(groups):
            ordered_label = ("有序" if IS_ZH else "ordered") if is_ordered else ("无序" if IS_ZH else "unordered")
            if IS_ZH:
                print(f"\n\033[1;32m成功保存{ordered_label}分组 '{gname}'，包含 {len(unique_skills)} 个技能！\033[0m")
            else:
                print(f"\n\033[1;32mSuccessfully saved {ordered_label} group '{gname}' containing {len(unique_skills)} skills!\033[0m")
        else:
            if IS_ZH:
                print("\n\033[1;31m保存失败。\033[0m")
            else:
                print("\n\033[1;31mFailed to save.\033[0m")
    except KeyboardInterrupt:
        if IS_ZH:
            print("\n\033[1;33m操作已取消。\033[0m")
        else:
            print("\n\033[1;33mOperation cancelled.\033[0m")
        
    if IS_ZH:
        input("\n按回车键返回 FZF...")
    else:
        input("\nPress Enter to return to FZF...")

def interactive_rm(focused_item):
    if not focused_item.startswith("group:"):
        if IS_ZH:
            print("\033[1;31m错误：当前所选项不是一个技能分组，无法删除！\033[0m")
            print(f"所选项: {focused_item}")
            input("\n按回车键返回 FZF...")
        else:
            print("\033[1;31mError: Current item is not a skill group, cannot delete!\033[0m")
            print(f"Selected item: {focused_item}")
            input("\nPress Enter to return to FZF...")
        return
        
    gkey = focused_item[6:]
    groups = load_groups()
    if gkey not in groups:
        if IS_ZH:
            print(f"\033[1;31m错误：分组 '{gkey}' 不存在。\033[0m")
            input("\n按回车键返回 FZF...")
        else:
            print(f"\033[1;31mError: Group '{gkey}' does not exist.\033[0m")
            input("\nPress Enter to return to FZF...")
        return
        
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    if IS_ZH:
        print(f"\033[1;31m确定要删除技能分组 '{gkey}' 吗？\033[0m")
    else:
        print(f"\033[1;31mAre you sure you want to delete skill group '{gkey}'?\033[0m")
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    
    try:
        if IS_ZH:
            confirm = input("请输入 y 确认删除 (或按回车键取消): ").strip().lower()
        else:
            confirm = input("Please enter y to confirm deletion (or press Enter to cancel): ").strip().lower()
        if confirm in ('y', 'yes'):
            del groups[gkey]
            if save_groups(groups):
                if IS_ZH:
                    print(f"\n\033[1;32m分组 '{gkey}' 已成功删除！\033[0m")
                else:
                    print(f"\n\033[1;32mGroup '{gkey}' deleted successfully!\033[0m")
            else:
                if IS_ZH:
                    print("\n\033[1;31m删除失败。\033[0m")
                else:
                    print("\n\033[1;31mDeletion failed.\033[0m")
        else:
            if IS_ZH:
                print("\n\033[1;33m操作已取消。\033[0m")
            else:
                print("\n\033[1;33mOperation cancelled.\033[0m")
    except KeyboardInterrupt:
        if IS_ZH:
            print("\n\033[1;33m操作已取消。\033[0m")
        else:
            print("\n\033[1;33mOperation cancelled.\033[0m")
        
    if IS_ZH:
        input("\n按回车键返回 FZF...")
    else:
        input("\nPress Enter to return to FZF...")

def view_connected():
    """
    View currently connected skills under the current project's .agents/skills/ directory.
    Display each skill with its Chinese translation loaded from the translation cache.
    """
    connected_dir = "./.agents/skills"
    if not os.path.exists(connected_dir) or not os.path.isdir(connected_dir):
        if IS_ZH:
            print(f"\033[1;33m[link_skills] 当前项目下未检测到已连接的技能目录 (.agents/skills)。\033[0m")
        else:
            print(f"\033[1;33m[link_skills] No connected skills directory found for the current project (.agents/skills).\033[0m")
        return

    # List all subdirectories or symlinks under connected_dir
    skills = []
    try:
        for item in sorted(os.listdir(connected_dir)):
            full_path = os.path.join(connected_dir, item)
            # Check if it is a directory or a symlink to a directory
            if os.path.isdir(full_path):
                skills.append(item)
    except Exception as e:
        if IS_ZH:
            print(f"\033[1;31m[link_skills] 读取已连接技能时出错: {e}\033[0m")
        else:
            print(f"\033[1;31m[link_skills] Error reading connected skills: {e}\033[0m")
        return

    if not skills:
        if IS_ZH:
            print(f"\033[1;33m[link_skills] 当前项目未连接任何技能。\033[0m")
        else:
            print(f"\033[1;33m[link_skills] No skills connected to the current project.\033[0m")
        return

    # Load translations from cache
    translations = {}
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import preview_skill
        translations = preview_skill.load_user_translations()
    except Exception:
        pass

    # ANSI colors
    GREEN = "\033[1;32m"
    CYAN = "\033[1;36m"
    YELLOW = "\033[1;33m"
    RESET = "\033[0m"
    GREY = "\033[1;30m"

    if IS_ZH:
        print(f"{CYAN}=== 当前项目已连接的技能 (共 {len(skills)} 个) ==={RESET}")
    else:
        print(f"{CYAN}=== Connected Skills for Current Project (Total: {len(skills)}) ==={RESET}")

    for idx, skill in enumerate(skills, 1):
        name_zh = ""
        desc_zh = ""
        if skill in translations:
            name_zh = translations[skill].get("name_zh")
            desc_zh = translations[skill].get("desc_zh")
            
        # Display format
        if name_zh:
            print(f"  🔗 {GREEN}{skill}{RESET} ({name_zh})")
        else:
            if IS_ZH:
                print(f"  🔗 {GREEN}{skill}{RESET} (无缓存翻译)")
            else:
                print(f"  🔗 {GREEN}{skill}{RESET} (No cached translation)")
        
        if desc_zh:
            # Clean up the description
            desc_single = " ".join([l.strip() for l in desc_zh.split("\n") if l.strip()])
            if IS_ZH:
                print(f"     {GREY}描述: {desc_single}{RESET}")
            else:
                print(f"     {GREY}Description: {desc_single}{RESET}")
        print()

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
            if IS_ZH:
                print("没有定义任何技能分组。")
            else:
                print("No skill groups defined.")
            sys.exit(0)
        # ANSI colors
        GREEN = "\033[1;32m"
        CYAN = "\033[1;36m"
        YELLOW = "\033[1;33m"
        RESET = "\033[0m"
        if IS_ZH:
            print(f"{CYAN}=== 技能分组列表 ==={RESET}")
        else:
            print(f"{CYAN}=== Skill Groups List ==={RESET}")
        for gid, info in sorted(groups.items()):
            if isinstance(info, dict):
                name = info.get("name", gid)
                skills = info.get("skills", [])
                is_ordered = info.get("ordered", False)
            else:
                name = gid
                skills = info
                is_ordered = False
            ordered_tag = (f" {YELLOW}[有序]{RESET}" if IS_ZH else f" {YELLOW}[ordered]{RESET}") if is_ordered else ""
            print(f"{GREEN}• {gid}{RESET} ({name}){ordered_tag}:")
            if is_ordered:
                numbered = " ".join(f"{circled_num(i+1)}{s}" for i, s in enumerate(skills))
                if IS_ZH:
                    print(f"  推荐调用顺序: {numbered}")
                else:
                    print(f"  Recommended call order: {numbered}")
            else:
                skills_str = ", ".join(skills)
                if IS_ZH:
                    print(f"  包含技能: {skills_str}")
                else:
                    print(f"  Contains skills: {skills_str}")
        sys.exit(0)

    elif arg1 == "--set-group":
        if len(sys.argv) < 3:
            print("Error: --set-group requires a group name", file=sys.stderr)
            sys.exit(1)
        # Support optional --ordered flag after --set-group
        rest_args = sys.argv[2:]
        is_ordered = False
        if "--ordered" in rest_args:
            is_ordered = True
            rest_args = [a for a in rest_args if a != "--ordered"]
        gname = rest_args[0] if rest_args else ""
        skills = rest_args[1:]
        if not gname:
            print("Error: --set-group requires a group name", file=sys.stderr)
            sys.exit(1)
        if not skills:
            print("Error: Please provide at least one skill name", file=sys.stderr)
            sys.exit(1)
        
        disp_name = gname
        if gname in groups and isinstance(groups[gname], dict):
            disp_name = groups[gname].get("name", gname)

        groups[gname] = {
            "name": disp_name,
            "ordered": is_ordered,
            "skills": skills
        }
        if save_groups(groups):
            ordered_label = ("有序" if IS_ZH else "ordered ") if is_ordered else ""
            if IS_ZH:
                print(f"成功保存{ordered_label}分组 '{gname}'，包含 {len(skills)} 个技能。")
            else:
                print(f"Successfully saved {ordered_label}group '{gname}' containing {len(skills)} skills.")
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
                if IS_ZH:
                    print(f"已成功删除分组 '{gname}'。")
                else:
                    print(f"Successfully deleted group '{gname}'.")
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            if IS_ZH:
                print(f"错误: 分组 '{gname}' 不存在。", file=sys.stderr)
            else:
                print(f"Error: Group '{gname}' does not exist.", file=sys.stderr)
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

    elif arg1 == "--view-connected":
        view_connected()
        sys.exit(0)

    # Otherwise, resolve the list of inputs
    inputs = sys.argv[1:]
    resolved = []
    for item in inputs:
        if item.startswith("group:"):
            gkey = item[len("group:"):]
            if gkey in groups:
                ginfo = groups[gkey]
                skills = ginfo.get("skills", []) if isinstance(ginfo, dict) else ginfo
                resolved.extend(skills)
            else:
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

