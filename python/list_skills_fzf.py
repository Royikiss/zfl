#!/usr/bin/env python3
import os
import sys
import json
import re

def parse_md_frontmatter(path):
    """
    Parse YAML frontmatter from a markdown file.
    """
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

def main():
    skills_dir = os.path.expanduser("~/.agents/skills")
    if not os.path.exists(skills_dir):
        print(f"Error: {skills_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    # Path to the static translation DB
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "skills_zh.json")
    
    translations = {}
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                translations = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load skills_zh.json: {e}", file=sys.stderr)

    # Path to the user cache translation DB
    cache_path = os.path.expanduser("~/.cache/zsh/skills_zh.json")
    user_translations = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                user_translations = json.load(f)
        except Exception:
            pass

    # Scan available skills
    skills = []
    for entry in sorted(os.listdir(skills_dir)):
        entry_path = os.path.join(skills_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        skills.append(entry)

    for skill in skills:
        name_display = skill
        desc_display = ""
        
        # 1. Check static database first
        if skill in translations:
            name_display = translations[skill].get("name_zh", skill)
            desc_display = translations[skill].get("desc_zh", "")
        # 2. Check user-specific cache
        elif skill in user_translations:
            name_display = user_translations[skill].get("name_zh") or user_translations[skill].get("name", skill)
            desc_display = user_translations[skill].get("desc_zh") or user_translations[skill].get("description", "")
        else:
            # 3. Check local SKILL.zh.md or SKILL.zh-CN.md
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
                # 4. Fallback to English SKILL.md
                en_path = os.path.join(skills_dir, skill, "SKILL.md")
                en_data = parse_md_frontmatter(en_path)
                if en_data:
                    name_display = en_data.get("name") or skill
                    desc_display = en_data.get("description") or ""

        # Make description single line and truncate if necessary
        desc_single = " ".join([l.strip() for l in desc_display.split("\n") if l.strip()])
        if len(desc_single) > 80:
            desc_single = desc_single[:77] + "..."

        print(f"{skill} | [{name_display}] {desc_single}")

if __name__ == "__main__":
    main()
