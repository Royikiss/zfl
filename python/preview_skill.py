#!/usr/bin/env python3
import os
import sys
import re
import json
import urllib.request
import urllib.parse

def translate_via_google(text, to_lang='zh-CN'):
    """
    Using public GTX Translate API to translate text.
    """
    url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=" + to_lang + "&dt=t&q=" + urllib.parse.quote(text)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res = json.loads(response.read().decode('utf-8'))
            translated = "".join([item[0] for item in res[0] if item[0]])
            return translated
    except Exception:
        return None

def parse_md_content(path):
    """
    Parse a markdown file into YAML frontmatter dict and body text.
    """
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None, None

    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if m:
        frontmatter = m.group(1)
        body = content[m.end():]
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
        return {"name": name, "description": desc}, body
    return None, content

def main():
    if len(sys.argv) < 2:
        print("Usage: preview_skill.py <skill_name>")
        sys.exit(1)

    skill = sys.argv[1]
    skills_dir = os.path.expanduser("~/.agents/skills")
    skill_dir = os.path.join(skills_dir, skill)
    en_path = os.path.join(skill_dir, "SKILL.md")

    if not os.path.exists(en_path):
        print(f"\033[1;31mError: SKILL.md not found for skill '{skill}'\033[0m")
        print(f"Path searched: {en_path}")
        sys.exit(0)

    # 1. Load static translation DB
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "skills_zh.json")
    translations = {}
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                translations = json.load(f)
        except Exception:
            pass

    # 2. Load user cache translation DB from ~/.cache/zsh/skills_zh.json
    cache_dir = os.path.expanduser("~/.cache/zsh")
    cache_path = os.path.join(cache_dir, "skills_zh.json")
    user_translations = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                user_translations = json.load(f)
        except Exception:
            pass

    # 3. Check if a local Chinese translation file exists (in skill directory)
    zh_paths = [
        os.path.join(skill_dir, "SKILL.zh.md"),
        os.path.join(skill_dir, "SKILL.zh-CN.md")
    ]
    zh_path = None
    for p in zh_paths:
        if os.path.exists(p):
            zh_path = p
            break

    en_meta, en_body = parse_md_content(en_path)
    zh_meta, zh_body = None, None
    if zh_path:
        zh_meta, zh_body = parse_md_content(zh_path)

    # 4. Dynamic translation if not found in static DB, user cache, or local SKILL.zh.md
    cached_to_file = False
    if not zh_meta and skill not in translations and skill not in user_translations and en_meta:
        en_name = en_meta.get("name") or skill
        en_desc = en_meta.get("description") or ""
        
        zh_name_trans = translate_via_google(en_name)
        zh_desc_trans = translate_via_google(en_desc)
        
        if zh_name_trans or zh_desc_trans:
            # Save into user_translations dict
            user_translations[skill] = {
                "name_zh": zh_name_trans or en_name,
                "desc_zh": zh_desc_trans or en_desc
            }
            # Attempt to write the cache file to ~/.cache/zsh/skills_zh.json
            try:
                os.makedirs(cache_dir, exist_ok=True)
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(user_translations, f, indent=2, ensure_ascii=False)
                cached_to_file = True
            except Exception:
                pass

    # Extract display information
    name_en = en_meta.get("name") if en_meta else skill
    desc_en = en_meta.get("description") if en_meta else ""
    
    name_zh = ""
    desc_zh = ""
    usage_zh = ""
    
    if skill in translations:
        name_zh = translations[skill].get("name_zh")
        desc_zh = translations[skill].get("desc_zh")
        usage_zh = translations[skill].get("usage_zh")
    elif skill in user_translations:
        name_zh = user_translations[skill].get("name_zh")
        desc_zh = user_translations[skill].get("desc_zh")
    elif zh_meta:
        name_zh = zh_meta.get("name")
        desc_zh = zh_meta.get("description")

    # Clean description lists
    desc_en_lines = [l.strip() for l in desc_en.split("\n") if l.strip()]
    desc_zh_lines = [l.strip() for l in desc_zh.split("\n") if l.strip()] if desc_zh else []

    # Print layout
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    if name_zh:
        print(f"\033[1;32m Skill: \033[1;37m{name_en} ({name_zh})\033[0m")
    else:
        print(f"\033[1;32m Skill: \033[1;37m{name_en}\033[0m")
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    
    # Chinese Description
    if desc_zh_lines:
        print("\033[1;33m功能描述 (中文):\033[0m")
        for line in desc_zh_lines:
            print(f"  {line}")
        print("\033[1;36m" + "-" * 55 + "\033[0m")

    # English Description
    if desc_en_lines:
        print("\033[1;33mDescription (EN):\033[0m")
        for line in desc_en_lines:
            print(f"  {line}")
        print("\033[1;36m" + "-" * 55 + "\033[0m")

    # Usage Tips
    if usage_zh:
        print("\033[1;35m💡 使用场景与指南 (中文):\033[0m")
        print(f"  {usage_zh}")
        print("\033[1;36m" + "-" * 55 + "\033[0m")

    # Content Preview (bilingual body if zh exists)
    print("\033[1;34m内容预览 (Content Preview):\033[0m")
    body_to_print = zh_body if zh_body else en_body
    if body_to_print:
        body_lines = body_to_print.strip().split("\n")
        printed_lines = 0
        for line in body_lines:
            if printed_lines >= 25:
                break
            print(f"  {line}")
            printed_lines += 1
        if len(body_lines) > 25:
            print("\033[1;30m  ... (more content below) ...\033[0m")
            
    if cached_to_file:
        print("\033[1;30m  *已自动翻译元数据并缓存至 ~/.cache/zsh/skills_zh.json*\033[0m")

if __name__ == "__main__":
    main()
