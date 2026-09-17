#!/usr/bin/env python3
import os
import sys
import json
import re
import unicodedata

# Ensure skill_engine can be imported
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from skill_engine._display import strip_ansi, clean_item_id, get_display_width, pad_display, circled_num
from skill_engine._store import get_zfl_data_dir, DATA_DIR
from skill_engine._frontmatter import parse_yaml_frontmatter as parse_md_frontmatter
from skill_engine._translations import DEFAULT_TRANSLATIONS, load_user_translations

STATE_FILE = os.path.expanduser("~/.cache/zsh/mskill_fzf_state.json")

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"expanded_groups": [], "expand_all": False}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"expanded_groups": [], "expand_all": False}

def save_state(state):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def get_skill_info(skill, skills_dir, is_zh, user_translations):
    name_display = skill
    desc_display = ""
    
    if is_zh:
        if skill in user_translations:
            name_display = user_translations[skill].get("name_zh") or user_translations[skill].get("name", skill)
            desc_display = user_translations[skill].get("desc_zh") or user_translations[skill].get("description", "")
        else:
            zh_paths = [
                os.path.join(skills_dir, skill, "SKILL.zh.md"),
                os.path.join(skills_dir, skill, "SKILL.zh-CN.md")
            ]
            zh_data = None
            for p in zh_paths:
                if os.path.exists(p):
                    zh_data = parse_md_frontmatter(p)
                    if zh_data:
                        break
            if zh_data:
                name_display = zh_data.get("name") or skill
                desc_display = zh_data.get("description") or ""
            else:
                en_path = os.path.join(skills_dir, skill, "SKILL.md")
                en_data = parse_md_frontmatter(en_path)
                if en_data:
                    name_display = en_data.get("name") or skill
                    desc_display = en_data.get("description") or ""
    else:
        en_path = os.path.join(skills_dir, skill, "SKILL.md")
        en_data = parse_md_frontmatter(en_path)
        if en_data:
            name_display = en_data.get("name") or skill
            desc_display = en_data.get("description") or ""

    desc_single = " ".join([l.strip() for l in desc_display.split("\n") if l.strip()]).strip('“"”')
    if len(desc_single) > 55:
        desc_single = desc_single[:52] + "..."

    return name_display, desc_single

def find_group_for_item(item_raw, groups):
    token = clean_item_id(item_raw)
    if token.startswith("group:"):
        gkey = token[6:]
        if gkey in groups:
            return gkey
    # Check if token is a member of any group
    for gkey, info in groups.items():
        gskills = info.get("skills", []) if isinstance(info, dict) else info
        if token in gskills:
            return gkey
    return None

def handle_action(action, arg, groups):
    state = load_state()
    expanded = set(state.get("expanded_groups", []))

    if action == "--init":
        save_state({"expanded_groups": [], "expand_all": False})
        return

    if action == "--toggle-all":
        if state.get("expand_all", False) or len(expanded) >= len(groups):
            save_state({"expanded_groups": [], "expand_all": False})
        else:
            save_state({"expanded_groups": list(groups.keys()), "expand_all": True})
        return

    gkey = find_group_for_item(arg, groups)
    if not gkey:
        return

    if action == "--toggle":
        if gkey in expanded:
            expanded.remove(gkey)
        else:
            expanded.add(gkey)
    elif action == "--expand":
        expanded.add(gkey)
    elif action == "--collapse":
        expanded.discard(gkey)

    save_state({
        "expanded_groups": list(expanded),
        "expand_all": (len(expanded) == len(groups) and len(groups) > 0)
    })

def main():
    skills_dir = os.path.expanduser("~/.agents/skills")
    if not os.path.exists(skills_dir):
        print(f"Error: {skills_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    lang = os.environ.get("ZFL_LANG") or os.environ.get("LANG", "en")
    is_zh = lang.startswith("zh")

    # Load groups
    groups = {}
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import resolve_skills
        groups = resolve_skills.load_groups()
    except Exception:
        pass

    query = ""
    args = sys.argv[1:]
    if "--query" in args:
        q_idx = args.index("--query")
        query_parts = args[q_idx + 1:]
        query = " ".join(query_parts).strip()
        args = args[:q_idx]

    # Action handling (e.g. --toggle, --toggle-all, --expand, --collapse, --init)
    if len(args) > 0 and args[0].startswith("--"):
        action = args[0]
        arg = args[1] if len(args) > 1 else ""
        handle_action(action, arg, groups)
        sys.exit(0)

    user_translations = load_user_translations()
    state = load_state()
    expanded_groups = set(state.get("expanded_groups", []))
    expand_all = state.get("expand_all", False)

    # All installed skills
    all_skills = []
    if os.path.exists(skills_dir):
        for entry in sorted(os.listdir(skills_dir)):
            entry_path = os.path.join(skills_dir, entry)
            if os.path.isdir(entry_path):
                all_skills.append(entry)

    proj_skills_dir = os.path.join(os.getcwd(), ".agents", "skills")

    def get_mount_badge(s):
        if not os.path.exists(proj_skills_dir):
            return ""
        dest = os.path.join(proj_skills_dir, s)
        if os.path.islink(dest):
            return "\033[1;36m[🔗软链]\033[0m " if is_zh else "\033[1;36m[🔗linked]\033[0m "
        elif os.path.isdir(dest):
            return "\033[1;32m[📄拷贝]\033[0m " if is_zh else "\033[1;32m[📄copied]\033[0m "
        return ""

    def get_group_mount_stats(gskills):
        if not os.path.exists(proj_skills_dir) or not gskills:
            return ""
        total = len(gskills)
        if total == 0:
            return ""

        link_count = 0
        copy_count = 0
        for s in gskills:
            dest = os.path.join(proj_skills_dir, s)
            if os.path.islink(dest):
                link_count += 1
            elif os.path.isdir(dest):
                copy_count += 1

        if link_count == 0 and copy_count == 0:
            return ""

        link_pct = round(link_count / total * 100)
        copy_pct = round(copy_count / total * 100)

        badge_text = f"[🔗:{link_pct}%, 📦:{copy_pct}%]"
        if link_count > 0 and copy_count == 0:
            color = "\033[1;34m"  # 蓝色：全是软链接
        elif copy_count > 0 and link_count == 0:
            color = "\033[1;32m"  # 绿色：全是下载拷贝
        else:
            color = "\033[1;33m"  # 黄色：两者都有

        return f"{color}{badge_text}\033[0m "

    def skill_matches(s_id, s_name, s_desc, q):
        tokens = q.lower().split()
        if not tokens:
            return True
        text = f"{s_id} {s_name} {s_desc}".lower()
        return all(t in text for t in tokens)

    items = []
    skills_in_groups = set()

    # Build hierarchical group nodes & child skill nodes
    for gid, info in sorted(groups.items()):
        if isinstance(info, dict):
            name = info.get("name", gid)
            gskills = info.get("skills", [])
            is_ordered = info.get("ordered", False)
        else:
            name = gid
            gskills = info
            is_ordered = False

        for s in gskills:
            skills_in_groups.add(s)

        if query:
            # Search mode: directly search skills inside group, prioritize group content, display in expanded mode
            matched_gskills = []
            for s in gskills:
                s_name_display, s_desc_display = get_skill_info(s, skills_dir, is_zh, user_translations)
                if skill_matches(s, s_name_display, s_desc_display, query):
                    matched_gskills.append((s, s_name_display, s_desc_display))

            if not matched_gskills:
                continue

            toggle_icon = "\033[1;33m▼\033[0m"
            grp_badge = get_group_mount_stats(gskills)
            group_id_display = f"{toggle_icon} \033[1;36mgroup:{gid}\033[0m"
            name_bracket = f"{grp_badge}\033[1;33m[分组: {name}]\033[0m" if is_zh else f"{grp_badge}\033[1;33m[Group: {name}]\033[0m"
            match_stat = f"({len(matched_gskills)} 个匹配)" if is_zh else f"({len(matched_gskills)} matched)"
            desc_single = f"\033[0;35m⚑ 有序 · {match_stat}\033[0m" if is_ordered else f"\033[0;36m📂 分组 · {match_stat}\033[0m"

            items.append({
                "col1": group_id_display,
                "col2": name_bracket,
                "col3": desc_single
            })

            for idx, (skill, s_name_display, s_desc_display) in enumerate(matched_gskills):
                is_last = (idx == len(matched_gskills) - 1)
                tree_branch = "  └── " if is_last else "  ├── "
                mount_badge = get_mount_badge(skill)

                child_id_display = f"\033[0;90m{tree_branch}\033[0;32m{skill}\033[0m"
                child_name_bracket = f"{mount_badge}\033[1;37m[{s_name_display}]\033[0m"
                child_desc = f"\033[0;90m{s_desc_display}\033[0m" if s_desc_display else ""

                items.append({
                    "col1": child_id_display,
                    "col2": child_name_bracket,
                    "col3": child_desc
                })
        else:
            # Browse mode (no search query)
            is_expanded = expand_all or (gid in expanded_groups)
            toggle_icon = "\033[1;33m▼\033[0m" if is_expanded else "\033[1;34m▶\033[0m"
            grp_badge = get_group_mount_stats(gskills)
            group_id_display = f"{toggle_icon} \033[1;36mgroup:{gid}\033[0m"
            name_bracket = f"{grp_badge}\033[1;33m[分组: {name}]\033[0m" if is_zh else f"{grp_badge}\033[1;33m[Group: {name}]\033[0m"

            hint_pill = f" \033[0;90m[Tab折叠]\033[0m" if is_expanded else f" \033[0;90m[Tab展开]\033[0m"
            if not is_zh:
                hint_pill = f" \033[0;90m[Tab:collapse]\033[0m" if is_expanded else f" \033[0;90m[Tab:expand]\033[0m"

            if is_ordered:
                sub = gskills[:3]
                numbered = " ".join(f"{circled_num(i+1)} {s}" for i, s in enumerate(sub))
                if len(gskills) > 3:
                    numbered += " ..."
                desc_single = f"\033[0;35m⚑ 有序 · {len(gskills)} 个技能 ({numbered})\033[0m{hint_pill}" if is_zh else f"\033[0;35m⚑ Ordered · {len(gskills)} skills ({numbered})\033[0m{hint_pill}"
            else:
                sub = gskills[:3]
                gskills_summary = ", ".join(sub) + ("..." if len(gskills) > 3 else "")
                desc_single = f"\033[0;36m📂 包含 {len(gskills)} 个技能 ({gskills_summary})\033[0m{hint_pill}" if is_zh else f"\033[0;36m📂 Contains {len(gskills)} skills ({gskills_summary})\033[0m{hint_pill}"

            items.append({
                "col1": group_id_display,
                "col2": name_bracket,
                "col3": desc_single
            })

            # Output children only when this group is expanded
            if is_expanded:
                for idx, skill in enumerate(gskills):
                    is_last = (idx == len(gskills) - 1)
                    tree_branch = "  └── " if is_last else "  ├── "

                    s_name_display, s_desc_display = get_skill_info(skill, skills_dir, is_zh, user_translations)
                    mount_badge = get_mount_badge(skill)

                    child_id_display = f"\033[0;90m{tree_branch}\033[0;32m{skill}\033[0m"
                    child_name_bracket = f"{mount_badge}\033[1;37m[{s_name_display}]\033[0m"
                    child_desc = f"\033[0;90m{s_desc_display}\033[0m" if s_desc_display else ""

                    items.append({
                        "col1": child_id_display,
                        "col2": child_name_bracket,
                        "col3": child_desc
                    })

    # Ungrouped / standalone skills
    ungrouped_skills = [s for s in all_skills if s not in skills_in_groups]
    for skill in ungrouped_skills:
        s_name_display, s_desc_display = get_skill_info(skill, skills_dir, is_zh, user_translations)
        if query and not skill_matches(skill, s_name_display, s_desc_display, query):
            continue
        mount_badge = get_mount_badge(skill)
        
        standalone_id_display = f"\033[0;90m  \033[0;32m{skill}\033[0m"
        standalone_name_bracket = f"{mount_badge}\033[1;37m[{s_name_display}]\033[0m"
        standalone_desc = f"\033[0;90m{s_desc_display}\033[0m" if s_desc_display else ""

        items.append({
            "col1": standalone_id_display,
            "col2": standalone_name_bracket,
            "col3": standalone_desc
        })

    if not items:
        return

    # Calculate padding widths based on visible character widths (excluding ANSI)
    max_col1_w = max([get_display_width(x["col1"]) for x in items] + [32])
    col1_width = max_col1_w + 2

    max_col2_w = max([get_display_width(x["col2"]) for x in items] + [22])
    col2_width = max_col2_w + 2

    for item in items:
        c1 = pad_display(item["col1"], col1_width)
        c2 = pad_display(item["col2"], col2_width)
        c3 = item["col3"]
        print(f"{c1}{c2}{c3}")

if __name__ == "__main__":
    main()



