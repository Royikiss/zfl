#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Description: Parse and expand skill groups and skill names, and provide interfaces to manage groups

import os
import sys
import json
import re
import unicodedata

# Detect language
LANG = os.environ.get("ZFL_LANG") or os.environ.get("LANG", "en")
IS_ZH = LANG.startswith("zh")

def get_zfl_data_dir():
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        base = os.path.join(xdg_data, "zfl")
    else:
        base = os.path.expanduser("~/.local/share/zfl")
    os.makedirs(base, exist_ok=True)
    legacy_groups = os.path.expanduser("~/.cache/zsh/skills_groups.json")
    new_groups = os.path.join(base, "skills_groups.json")
    if os.path.exists(legacy_groups) and not os.path.exists(new_groups):
        try:
            import shutil
            shutil.copy2(legacy_groups, new_groups)
        except Exception:
            pass
    return base

DATA_DIR = get_zfl_data_dir()
GROUPS_FILE = os.path.join(DATA_DIR, "skills_groups.json")

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
    Save group configurations back to skills_groups.json atomically.
    """
    try:
        os.makedirs(os.path.dirname(GROUPS_FILE), exist_ok=True)
        tmp_file = f"{GROUPS_FILE}.tmp.{os.getpid()}"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(groups, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, GROUPS_FILE)
        return True
    except Exception:
        return False
def safe_input(prompt_msg=""):
    """
    Safely print prompt and read input using a clean ASCII '> ' prompt.
    Prevents CJK character backspace alignment bugs in terminal readline.
    """
    if prompt_msg:
        print(prompt_msg)
    return input("> ").strip()

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
        elif default_gkey and default_gkey in groups and isinstance(groups[default_gkey], dict):
            disp_name = groups[default_gkey].get("name", gname)

        # If renamed from an existing group, remove the old key to avoid stale duplicates
        if default_gkey and default_gkey != gname and default_gkey in groups:
            del groups[default_gkey]
            
        groups[gname] = {
            "name": disp_name,
            "ordered": is_ordered,
            "skills": unique_skills
        }
        if save_groups(groups):
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
    if not cleaned.startswith("group:"):
        if IS_ZH:
            print("\033[1;31m╭─────────────────────────────────────────────────────────╮\033[0m")
            print("\033[1;31m│  [✗] 错误: 当前所选项不是一个技能分组，无法删除！       │\033[0m")
            print(f"\033[1;31m│      所选项: {cleaned:<42}│\033[0m")
            print("\033[1;31m╰─────────────────────────────────────────────────────────╯\033[0m")
            safe_input("\n按回车键返回 FZF...")
        else:
            print("\033[1;31m╭─────────────────────────────────────────────────────────╮\033[0m")
            print("\033[1;31m│  [✗] Error: Selected item is not a skill group!        │\033[0m")
            print(f"\033[1;31m│      Item: {cleaned:<46}│\033[0m")
            print("\033[1;31m╰─────────────────────────────────────────────────────────╯\033[0m")
            safe_input("\nPress Enter to return to FZF...")
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
            del groups[gkey]
            if save_groups(groups):
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

ANSI_REGEX = re.compile(r'\033\[[0-9;]*[a-zA-Z]')

def strip_ansi(s):
    return ANSI_REGEX.sub('', s)

def get_display_width(s):
    s_clean = strip_ansi(s)
    w = 0
    for ch in s_clean:
        status = unicodedata.east_asian_width(ch)
        if status in ('F', 'W'):
            w += 2
        else:
            w += 1
    return w

def pad_display(s, target_width, align='left'):
    curr_w = get_display_width(s)
    pad_len = max(0, target_width - curr_w)
    if align == 'right':
        return " " * pad_len + s
    elif align == 'center':
        left = pad_len // 2
        right = pad_len - left
        return " " * left + s + " " * right
    else:
        return s + " " * pad_len

def truncate_display(s, max_w, suffix="…"):
    curr_w = get_display_width(s)
    if curr_w <= max_w:
        return s
    suffix_w = get_display_width(suffix)
    target = max_w - suffix_w
    if target <= 0:
        return suffix[:max_w]
    res = []
    w = 0
    for ch in s:
        cw = 2 if unicodedata.east_asian_width(ch) in ('F', 'W') else 1
        if w + cw > target:
            break
        res.append(ch)
        w += cw
    return "".join(res) + suffix

def parse_frontmatter(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if m:
        frontmatter = m.group(1)
        data = {}
        current_key = None
        for line in frontmatter.split("\n"):
            if not line.strip():
                continue
            if line.startswith(" ") or line.startswith("\t"):
                if current_key:
                    val = line.strip()
                    if val.startswith("-"):
                        data[current_key] += "\n" + val
                    else:
                        data[current_key] += " " + val
            else:
                if ":" in line:
                    key, val = line.split(":", 1)
                    current_key = key.strip()
                    data[current_key] = val.strip()
        name = data.get("name", "")
        desc = data.get("description", "")
        if desc.startswith(">"):
            desc = desc[1:]
        desc = desc.replace("\n> ", "\n").replace("\n>", "\n").strip()
        return {"name": name, "description": desc}
    return None

def find_connected_dir():
    """Find .agents/skills in current directory or parent directories up to git root."""
    curr = os.path.abspath(os.getcwd())
    while True:
        candidate = os.path.join(curr, ".agents", "skills")
        if os.path.exists(candidate) and os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        if os.path.exists(os.path.join(curr, ".git")):
            break
        curr = parent
    return os.path.join(os.getcwd(), ".agents", "skills")

def list_connected_skills():
    """Display skills currently connected in project with sleek modern streamlined layout."""
    connected_dir = find_connected_dir()
    if not os.path.exists(connected_dir) or not os.path.isdir(connected_dir):
        if IS_ZH:
            print("[mskill] 当前项目下未检测到已连接的技能目录 (.agents/skills)。")
            print("\033[0;90m💡 提示: 在项目根目录下运行 'mskill' 即可选择并引入所需技能。\033[0m\n")
        else:
            print("[mskill] No connected skills found in current project (.agents/skills).")
            print("\033[0;90m💡 Tip: Run 'mskill' in project root to select and connect skills.\033[0m\n")
        return

    skills = [
        s for s in sorted(os.listdir(connected_dir))
        if not s.startswith(".") and (os.path.isdir(os.path.join(connected_dir, s)) or os.path.islink(os.path.join(connected_dir, s)))
    ]
    if not skills:
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
    symlink_count = sum(1 for s in skills if os.path.islink(os.path.join(connected_dir, s)))
    copy_count = len(skills) - symlink_count

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
              f"{CYAN}[总计: {WHITE}{len(skills)}{CYAN}]{RESET}  "
              f"{BLUE}[🔗 软链接: {WHITE}{symlink_count}{BLUE}]{RESET}  "
              f"{MAGENTA}[📁 实体副本: {WHITE}{copy_count}{MAGENTA}]{RESET}\n")
    else:
        print(f"\n  {BOLD}{WHITE}🔗 Connected Project Skills{RESET}  "
              f"{CYAN}[Total: {WHITE}{len(skills)}{CYAN}]{RESET}  "
              f"{BLUE}[🔗 Symlinks: {WHITE}{symlink_count}{BLUE}]{RESET}  "
              f"{MAGENTA}[📁 Copies: {WHITE}{copy_count}{MAGENTA}]{RESET}\n")

    header_name = "技能名称 (Skill Name)" if IS_ZH else "Skill Name"
    header_mode = "挂载方式" if IS_ZH else "Mount Mode"
    header_desc = "说明 / 中文描述" if IS_ZH else "Description"

    max_name_len = max((len(s) for s in skills), default=20)
    col_name_w = max(get_display_width(header_name), min(max_name_len, 32))
    col_mode_w = 14

    h_name = pad_display(f"{BOLD}{WHITE}{header_name}{RESET}", col_name_w)
    h_mode = pad_display(f"{BOLD}{WHITE}{header_mode}{RESET}", col_mode_w)
    h_desc = f"{BOLD}{WHITE}{header_desc}{RESET}"

    divider_w = min(term_width - 4, col_name_w + col_mode_w + 45)
    print(f"  {h_name}  {h_mode}  {h_desc}")
    print(f"  {GREY}{'─' * divider_w}{RESET}")

    for skill in skills:
        full_path = os.path.join(connected_dir, skill)
        is_link = os.path.islink(full_path)
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

    if arg1 in ("--help", "-h"):
        print_help()
        sys.exit(0)

    elif arg1 == "--list-groups":
        for gid in sorted(groups.keys()):
            print(gid)
        sys.exit(0)

    elif arg1 == "--list-groups-detailed":
        list_groups_detailed()
        sys.exit(0)

    elif arg1 == "--set-group":
        if len(sys.argv) < 3:
            print("Error: --set-group requires a group name", file=sys.stderr)
            sys.exit(1)
        rest_args = sys.argv[2:]
        is_ordered = False
        if "--ordered" in rest_args:
            is_ordered = True
            rest_args = [a for a in rest_args if a != "--ordered"]
        gname = rest_args[0] if rest_args else ""
        skills = [clean_item_id(a) for a in rest_args[1:] if clean_item_id(a)]
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
                print(f"[✓] 成功保存{ordered_label}分组 '{gname}'，包含 {len(skills)} 个技能。")
            else:
                print(f"[✓] Successfully saved {ordered_label}group '{gname}' containing {len(skills)} skills.")
            sys.exit(0)
        else:
            sys.exit(1)

    elif arg1 == "--rm-group":
        if len(sys.argv) < 3:
            print("Error: --rm-group requires a group name", file=sys.stderr)
            sys.exit(1)
        gname = clean_item_id(sys.argv[2]).removeprefix("group:")
        if gname in groups:
            del groups[gname]
            if save_groups(groups):
                if IS_ZH:
                    print(f"[✓] 已成功删除分组 '{gname}'。")
                else:
                    print(f"[✓] Successfully deleted group '{gname}'.")
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            if IS_ZH:
                print(f"[✗] 错误: 分组 '{gname}' 不存在。", file=sys.stderr)
            else:
                print(f"[✗] Error: Group '{gname}' does not exist.", file=sys.stderr)
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
    raw_inputs = sys.argv[1:]
    resolved = []
    for raw in raw_inputs:
        item = clean_item_id(raw)
        if not item:
            continue
        if item.startswith("group:"):
            gkey = item[len("group:"):]
            if gkey in groups:
                ginfo = groups[gkey]
                skills = ginfo.get("skills", []) if isinstance(ginfo, dict) else ginfo
                resolved.extend(skills)
            else:
                resolved.append(gkey)
        elif item in groups:
            ginfo = groups[item]
            skills = ginfo.get("skills", []) if isinstance(ginfo, dict) else ginfo
            resolved.extend(skills)
        else:
            resolved.append(item)

    # Deduplicate while preserving order
    seen = set()
    for skill in resolved:
        clean_s = clean_item_id(skill)
        if clean_s and clean_s not in seen:
            seen.add(clean_s)
            print(clean_s)

if __name__ == "__main__":
    main()


