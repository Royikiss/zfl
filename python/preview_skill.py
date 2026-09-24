#!/usr/bin/env python3
import os
import sys
import re
import json
import urllib.request
import urllib.parse

# Ensure skill_engine can be imported
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from skill_engine._display import strip_ansi, clean_item_id, circled_num, IS_ZH
from skill_engine._store import get_zfl_data_dir, atomic_save_json, DATA_DIR
from skill_engine._translations import DEFAULT_TRANSLATIONS, load_user_translations
from skill_engine._groups import resolve_group_targets

def translate_via_google(text, to_lang='zh-CN'):
    """
    Backend 1: Google public GTX API (1.5s timeout).
    Returns translated string or None on failure.
    """
    url = ("https://translate.googleapis.com/translate_a/single"
           "?client=gtx&sl=auto&tl=" + to_lang
           + "&dt=t&q=" + urllib.parse.quote(text))
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=1.5) as response:
            body = response.read().decode('utf-8')
            # Google returns HTML "Sorry..." when rate-limited — detect and bail
            if body.lstrip().startswith('<'):
                return None
            res = json.loads(body)
            translated = "".join([item[0] for item in res[0] if item[0]])
            return translated if translated else None
    except Exception:
        return None


def translate_via_mymemory(text, to_lang='zh-CN'):
    """
    Backend 2: MyMemory free API (no key, ~1000 words/day/IP, 3s timeout).
    Returns translated string or None on failure.
    """
    # MyMemory uses 'en|zh-CN' style langpair
    langpair = "en|" + to_lang
    url = ("https://api.mymemory.translated.net/get"
           "?q=" + urllib.parse.quote(text)
           + "&langpair=" + urllib.parse.quote(langpair))
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            res = json.loads(response.read().decode('utf-8'))
            if res.get('responseStatus') == 200:
                translated = res.get('responseData', {}).get('translatedText', '')
                # MyMemory echoes the source when it fails
                if translated and translated.lower() != text.lower():
                    return translated
            return None
    except Exception:
        return None


def translate_text(text, to_lang='zh-CN'):
    """
    Unified translation entry point with automatic fallback chain:
      1. Google GTX  (fastest, sometimes rate-limited)
      2. MyMemory    (free, no auth, ~500 chars/request limit)
    For long texts (>450 chars), splits into sentence-boundary chunks
    so MyMemory can handle them, then rejoins the results.
    Returns translated string, or None if all backends fail.
    """
    raw_text = text.strip()
    # --- Try Google first (handles any length) ---
    result = translate_via_google(raw_text, to_lang)
    if result and result.strip():
        if result.strip().lower() != raw_text.lower():
            return result.strip()

    # --- Fallback: MyMemory with chunking for long texts ---
    CHUNK_LIMIT = 450
    if len(raw_text) <= CHUNK_LIMIT:
        res = translate_via_mymemory(raw_text, to_lang)
        if res and res.strip():
            return res.strip()

    # If it is a hyphenated/underscored identifier (e.g. template-skill), try replacing with spaces
    if ("-" in raw_text or "_" in raw_text) and " " not in raw_text:
        cleaned = raw_text.replace("-", " ").replace("_", " ")
        res = translate_via_google(cleaned, to_lang) or translate_via_mymemory(cleaned, to_lang)
        if res and res.strip():
            return res.strip()

    # Split into sentences at '. ', '! ', '? ', '; ' boundaries
    import re as _re
    sentences = _re.split(r'(?<=[.!?;])\s+', text.strip())
    chunks, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= CHUNK_LIMIT:
            current = (current + " " + sent).strip() if current else sent
        else:
            if current:
                chunks.append(current)
            # If a single sentence exceeds limit, hard-split by word
            if len(sent) > CHUNK_LIMIT:
                words = sent.split()
                part = ""
                for w in words:
                    if len(part) + len(w) + 1 <= CHUNK_LIMIT:
                        part = (part + " " + w).strip() if part else w
                    else:
                        if part:
                            chunks.append(part)
                        part = w
                current = part
            else:
                current = sent
    if current:
        chunks.append(current)

    translated_parts = []
    for chunk in chunks:
        part = translate_via_mymemory(chunk, to_lang)
        translated_parts.append(part if part else chunk)

    return " ".join(translated_parts) if translated_parts else None

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


def format_markdown_line(line):
    """Format markdown line with syntax highlights for terminal preview."""
    # Headers
    if line.startswith("# "):
        return f"\033[1;36m■ {line[2:].strip()}\033[0m"
    if line.startswith("## "):
        return f"\033[1;34m▶ {line[3:].strip()}\033[0m"
    if line.startswith("### "):
        return f"\033[1;33m◆ {line[4:].strip()}\033[0m"
    if line.startswith("#### "):
        return f"\033[1;35m▪ {line[5:].strip()}\033[0m"
    # Blockquotes / Alerts
    if line.startswith("> [!NOTE]") or line.startswith("> [!TIP]"):
        return f"\033[1;36m  💡 {line[2:].strip()}\033[0m"
    if line.startswith("> [!IMPORTANT]") or line.startswith("> [!WARNING]"):
        return f"\033[1;33m  ⚠️  {line[2:].strip()}\033[0m"
    if line.startswith("> "):
        return f"\033[0;90m  │ {line[2:].strip()}\033[0m"
    # List items
    if re.match(r"^[-*]\s+", line):
        return f"\033[0;32m  • \033[0;37m{line[2:].strip()}\033[0m"
    m_num = re.match(r"^(\d+)\.\s+(.*)", line)
    if m_num:
        return f"\033[0;33m  {m_num.group(1)}. \033[0;37m{m_num.group(2)}\033[0m"
    # Code block marker
    if line.startswith("```"):
        return f"\033[0;90m  ───────────────────────────────────────────\033[0m"
    return f"  {line}"

def print_hotkeys_footer(is_zh):
    CYAN = "\033[1;36m"
    WHITE = "\033[1;37m"
    YELLOW = "\033[1;33m"
    GREEN = "\033[1;32m"
    GREY = "\033[0;90m"
    RESET = "\033[0m"

    if is_zh:
        print(f"\n{CYAN}╭───────────────────────── ⌨️  快捷键操作全览 ─────────────────────────╮{RESET}")
        print(f"{CYAN}│{RESET}  {YELLOW}🌿 浏览:{RESET}  {WHITE}[Tab / → / ←]{RESET} 折叠/展开组  │  {WHITE}[Ctrl-O]{RESET} 全展/全折  │  {WHITE}[空格]{RESET} 多选")
        print(f"{CYAN}│{RESET}  {YELLOW}⚡ 管理:{RESET}  {WHITE}[Ctrl-G]{RESET} 分组/移入    │  {WHITE}[Ctrl-D]{RESET} 移出/解散组  │  {WHITE}[Ctrl-N]{RESET} 安装新技能")
        print(f"{CYAN}│{RESET}           {WHITE}[Ctrl-U]{RESET} 检查更新    │  {WHITE}[Ctrl-B]{RESET} 解绑Git     │  {WHITE}[Ctrl-T]{RESET} 重新翻译")
        print(f"{CYAN}│{RESET}           {WHITE}[Ctrl-E]{RESET} 编辑SKILL   │  {WHITE}[Ctrl-X]{RESET} 项目解挂    │  {WHITE}[Ctrl-V]{RESET} 预览折行")
        print(f"{CYAN}│{RESET}  {GREEN}🚀 执行:{RESET}  {WHITE}[Enter]{RESET} 软链接到项目  │  {WHITE}[Alt-C]{RESET} 拷贝实体副本")
        print(f"{CYAN}╰─────────────────────────────────────────────────────────────────────╯{RESET}")
    else:
        print(f"\n{CYAN}╭───────────────────────── ⌨️  Hotkeys Reference ──────────────────────╮{RESET}")
        print(f"{CYAN}│{RESET}  {YELLOW}🌿 Browse:{RESET} {WHITE}[Tab / → / ←]{RESET} Toggle Group │ {WHITE}[Ctrl-O]{RESET} Toggle All │ {WHITE}[Space]{RESET} Multi")
        print(f"{CYAN}│{RESET}  {YELLOW}⚡ Manage:{RESET} {WHITE}[Ctrl-G]{RESET} Groups/Add    │ {WHITE}[Ctrl-D]{RESET} Remove/Disband │ {WHITE}[Ctrl-N]{RESET} Install")
        print(f"{CYAN}│{RESET}           {WHITE}[Ctrl-U]{RESET} Update        │ {WHITE}[Ctrl-B]{RESET} Unbind Git   │ {WHITE}[Ctrl-T]{RESET} Translate")
        print(f"{CYAN}│{RESET}           {WHITE}[Ctrl-E]{RESET} Edit SKILL    │ {WHITE}[Ctrl-X]{RESET} Unlink Proj  │ {WHITE}[Ctrl-V]{RESET} Wrap Preview")
        print(f"{CYAN}│{RESET}  {GREEN}🚀 Action:{RESET} {WHITE}[Enter]{RESET} Symlink        │ {WHITE}[Alt-C]{RESET} Copy Entity")
        print(f"{CYAN}╰─────────────────────────────────────────────────────────────────────╯{RESET}")

def translate_all_workflow(is_zh):
    skills_dir = os.path.expanduser("~/.agents/skills")
    if not os.path.exists(skills_dir):
        print("未检测到 ~/.agents/skills 目录。" if is_zh else "No ~/.agents/skills found.")
        return 0
    cache_path = os.path.join(DATA_DIR, "skills_zh.json")
    user_translations = load_user_translations()
    all_skills = [d for d in sorted(os.listdir(skills_dir)) if os.path.isdir(os.path.join(skills_dir, d))]
    
    untranslated = [
        s for s in all_skills 
        if (s not in user_translations or user_translations[s].get("name_zh") in (None, "", s) or not user_translations[s].get("desc_zh"))
    ]
    if not untranslated:
        print("\033[1;32m[✓] 所有本地技能均已具备中文翻译缓存！\033[0m" if is_zh else "\033[1;32m[✓] All skills already translated!\033[0m")
        return 0
        
    print(f"\033[1;36m==> 正在为 {len(untranslated)} 个尚未翻译的技能批量拉取中文译名与描述...\033[0m" if is_zh else f"\033[1;36m==> Translating {len(untranslated)} skills...\033[0m")
    success = 0
    for s in untranslated:
        en_path = os.path.join(skills_dir, s, "SKILL.md")
        en_meta, _ = parse_md_content(en_path)
        if not en_meta:
            continue
        en_name = en_meta.get("name") or s
        en_desc = en_meta.get("description") or ""
        zh_name = translate_text(en_name)
        zh_desc = translate_text(en_desc)
        if zh_name or zh_desc:
            user_translations[s] = {
                "name_zh": zh_name or en_name,
                "desc_zh": zh_desc or en_desc
            }
            success += 1
            print(f"  \033[1;32m✓\033[0m {s} -> {zh_name or en_name}")
        else:
            print(f"  \033[1;33m-\033[0m {s} (超时/跳过)")
            
    atomic_save_json(cache_path, user_translations)
    print(f"\033[1;32m\n批量翻译完成！已成功入库 {success}/{len(untranslated)} 个技能。\033[0m" if is_zh else f"\033[1;32m\nTranslation complete! {success}/{len(untranslated)} translated.\033[0m")
    return 0

def cmd_translate_all(is_zh=True):
    return translate_all_workflow(is_zh)

def cmd_force_translate(raw_items):
    if not raw_items:
        return 0
    if isinstance(raw_items, str):
        raw_items = [raw_items]

    skills = resolve_group_targets(raw_items)
    if not skills:
        return 0

    skills_dir = os.path.expanduser("~/.agents/skills")
    cache_path = os.path.join(DATA_DIR, "skills_zh.json")
    user_translations = load_user_translations()
    changed = False

    for skill in skills:
        skill_dir = os.path.join(skills_dir, skill)
        en_path = os.path.join(skill_dir, "SKILL.md")
        if not os.path.exists(en_path):
            continue
        en_meta, _ = parse_md_content(en_path)
        if not en_meta:
            continue
        en_name = en_meta.get("name") or skill
        en_desc = en_meta.get("description") or ""
        zh_name = translate_text(en_name)
        zh_desc = translate_text(en_desc)
        if zh_name or zh_desc:
            user_translations[skill] = {
                "name_zh": zh_name or en_name,
                "desc_zh": zh_desc or en_desc
            }
            changed = True

    if changed:
        atomic_save_json(cache_path, user_translations)
    return 0

def prefetch_translations(skill_names, is_zh=True):
    """Prefetch translations for specified skills."""
    if not skill_names or not is_zh:
        return
    skills_dir = os.path.expanduser("~/.agents/skills")
    cache_path = os.path.join(DATA_DIR, "skills_zh.json")
    user_translations = load_user_translations()
    changed = False
    for s in skill_names:
        if s in user_translations and user_translations[s].get("name_zh") and user_translations[s].get("name_zh") != s:
            continue
        en_path = os.path.join(skills_dir, s, "SKILL.md")
        if not os.path.exists(en_path):
            continue
        en_meta, _ = parse_md_content(en_path)
        if not en_meta:
            continue
        en_name = en_meta.get("name") or s
        en_desc = en_meta.get("description") or ""
        zh_name = translate_text(en_name)
        zh_desc = translate_text(en_desc)
        if zh_name or zh_desc:
            if s not in user_translations:
                user_translations[s] = {}
            user_translations[s]["name_zh"] = zh_name or en_name
            user_translations[s]["desc_zh"] = zh_desc or en_desc
            changed = True
    if changed:
        atomic_save_json(cache_path, user_translations)

def main():
    lang = os.environ.get("ZFL_LANG") or os.environ.get("LANG", "en")
    is_zh = lang.startswith("zh")

    if "--translate-all" in sys.argv:
        return translate_all_workflow(is_zh)

    force_translate = False
    if "--force-translate" in sys.argv:
        force_translate = True
        sys.argv.remove("--force-translate")

    show_full = False
    if "--full" in sys.argv:
        show_full = True
        sys.argv.remove("--full")

    import shutil
    # Detect fzf preview window size to decide whether to show full text
    fzf_preview_cols = int(os.environ.get('FZF_PREVIEW_COLUMNS', '0'))
    total_cols = int(os.environ.get('COLUMNS', '0') or os.environ.get('FZF_COLUMNS', '0') or '0')
    if total_cols == 0:
        total_cols = shutil.get_terminal_size().columns

    if fzf_preview_cols > 0 and total_cols > 0:
        ratio = fzf_preview_cols / total_cols
        if ratio > 0.7:
            show_full = True

    if len(sys.argv) < 2:
        print("Usage: preview_skill.py [--force-translate] [--full] <skill_name>")
        sys.exit(1)

    raw_arg = sys.argv[1]
    skill = clean_item_id(raw_arg)
    if not skill:
        skill = raw_arg.strip()
    
    if force_translate and skill.startswith("group:"):
        sys.exit(0)
    
    lang = os.environ.get("ZFL_LANG") or os.environ.get("LANG", "en")
    is_zh = lang.startswith("zh")

    # ANSI Colors
    CYAN = "\033[1;36m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[1;34m"
    MAGENTA = "\033[1;35m"
    WHITE = "\033[1;37m"
    GREY = "\033[0;90m"
    RESET = "\033[0m"

    if skill.startswith("group:"):
        # Group preview logic
        gkey = skill[6:]
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            import resolve_skills
            groups = resolve_skills.load_groups()
        except Exception:
            groups = {}
        
        if gkey not in groups:
            if is_zh:
                print(f"\033[1;31m╭─────────────────────────────────────────────────────────╮\033[0m")
                print(f"\033[1;31m│  [✗] 错误：未找到分组 '{gkey}'                         │\033[0m")
                print(f"\033[1;31m╰─────────────────────────────────────────────────────────╯\033[0m")
            else:
                print(f"\033[1;31m╭─────────────────────────────────────────────────────────╮\033[0m")
                print(f"\033[1;31m│  [✗] Error: Group '{gkey}' not found                   │\033[0m")
                print(f"\033[1;31m╰─────────────────────────────────────────────────────────╯\033[0m")
            sys.exit(0)
            
        ginfo = groups[gkey]
        if isinstance(ginfo, dict):
            gname = ginfo.get("name", gkey)
            gskills = ginfo.get("skills", [])
            is_ordered = ginfo.get("ordered", False)
        else:
            gname = gkey
            gskills = info
            is_ordered = False

        ordered_pill = f"{YELLOW}[⚑ 有序推荐顺序]{RESET}" if is_ordered else f"{MAGENTA}[⚡ 组合技能集合]{RESET}"
        if not is_zh:
            ordered_pill = f"{YELLOW}[⚑ Recommended Order]{RESET}" if is_ordered else f"{MAGENTA}[⚡ Skill Set]{RESET}"

        print(f"{CYAN}╭──────────────────────── 📂 技能分组卡片 ────────────────────────╮{RESET}")
        if is_zh:
            print(f"{CYAN}│{RESET}  📂 技能分组: {GREEN}{gname}{RESET} {WHITE}({gkey}){RESET}  {ordered_pill}")
            print(f"{CYAN}│{RESET}  📊 规模: 包含 {WHITE}{len(gskills)}{RESET} 个技能")
            print(f"{CYAN}├─────────────────────────────────────────────────────────────────┤{RESET}")
            if is_ordered:
                print(f"{CYAN}│{RESET}  {YELLOW}⚑ 推荐按以下顺序依次调用此组技能：{RESET}\n{CYAN}│{RESET}")
            else:
                print(f"{CYAN}│{RESET}  {MAGENTA}💡 该分组包含以下技能 (回车键一键全量批量链接)：{RESET}\n{CYAN}│{RESET}")
        else:
            print(f"{CYAN}│{RESET}  📂 Skill Group: {GREEN}{gname}{RESET} {WHITE}({gkey}){RESET}  {ordered_pill}")
            print(f"{CYAN}│{RESET}  📊 Total Skills: {WHITE}{len(gskills)}{RESET}")
            print(f"{CYAN}├─────────────────────────────────────────────────────────────────┤{RESET}")
            if is_ordered:
                print(f"{CYAN}│{RESET}  {YELLOW}⚑ Recommended execution order:{RESET}\n{CYAN}│{RESET}")
            else:
                print(f"{CYAN}│{RESET}  {MAGENTA}💡 Skills contained in this group (Enter to bulk link):{RESET}\n{CYAN}│{RESET}")
        
        user_translations = load_user_translations()
        skills_dir = os.path.expanduser("~/.agents/skills")
        for idx, s in enumerate(gskills):
            name_display = s
            desc_display = ""
            
            if is_zh:
                if s in user_translations:
                    name_display = user_translations[s].get("name_zh") or user_translations[s].get("name", s)
                    desc_display = user_translations[s].get("desc_zh") or user_translations[s].get("description", "")
                else:
                    zh_paths = [
                        os.path.join(skills_dir, s, "SKILL.zh.md"),
                        os.path.join(skills_dir, s, "SKILL.zh-CN.md")
                    ]
                    zh_data = None
                    for p in zh_paths:
                        if os.path.exists(p):
                            zh_data = parse_md_content(p)[0]
                            if zh_data:
                                break
                    if zh_data:
                        name_display = zh_data.get("name") or s
                        desc_display = zh_data.get("description") or ""
                    else:
                        en_path = os.path.join(skills_dir, s, "SKILL.md")
                        en_data = parse_md_content(en_path)[0]
                        if en_data:
                            name_display = en_data.get("name") or s
                            desc_display = en_data.get("description") or ""
            else:
                en_path = os.path.join(skills_dir, s, "SKILL.md")
                en_data = parse_md_content(en_path)[0]
                if en_data:
                    name_display = en_data.get("name") or s
                    desc_display = en_data.get("description") or ""
            
            if is_ordered:
                bullet = f"{YELLOW}{circled_num(idx + 1)}{RESET}"
            else:
                bullet = f"{GREEN}•{RESET}"
            
            title_part = f" {WHITE}({name_display}){RESET}" if name_display and name_display != s else ""
            print(f"{CYAN}│{RESET}  {bullet} {GREEN}{s}{RESET}{title_part}")
            if desc_display:
                desc_single = " ".join([l.strip() for l in desc_display.split("\n") if l.strip()])
                if len(desc_single) > 60:
                    desc_single = desc_single[:57] + "..."
                print(f"{CYAN}│{RESET}     {GREY}↳ {desc_single}{RESET}")
            print(f"{CYAN}│{RESET}")

        print(f"{CYAN}╰─────────────────────────────────────────────────────────────────╯{RESET}")
        print_hotkeys_footer(is_zh)
        sys.exit(0)

    # Single skill preview logic
    skills_dir = os.path.expanduser("~/.agents/skills")
    skill_dir = os.path.join(skills_dir, skill)
    en_path = os.path.join(skill_dir, "SKILL.md")

    if not os.path.exists(en_path):
        if is_zh:
            print(f"\033[1;31m╭─────────────────────────────────────────────────────────╮\033[0m")
            print(f"\033[1;31m│  [✗] 错误：未找到技能 '{skill}' 的 SKILL.md 文件       │\033[0m")
            print(f"\033[1;31m╰─────────────────────────────────────────────────────────╯\033[0m")
        else:
            print(f"\033[1;31m╭─────────────────────────────────────────────────────────╮\033[0m")
            print(f"\033[1;31m│  [✗] Error: SKILL.md not found for '{skill}'           │\033[0m")
            print(f"\033[1;31m╰─────────────────────────────────────────────────────────╯\033[0m")
        sys.exit(0)

    # 1. Load user cache translation DB
    cache_path = os.path.join(DATA_DIR, "skills_zh.json")
    user_translations = load_user_translations()

    # 2. Check if local Chinese translation file exists
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

    # 3. Dynamic translation if not found
    cached_to_file = False
    if (is_zh or force_translate) and not zh_meta and en_meta and (skill not in user_translations or force_translate):
        en_name = en_meta.get("name") or skill
        en_desc = en_meta.get("description") or ""
        
        zh_name_trans = translate_text(en_name)
        zh_desc_trans = translate_text(en_desc)
        
        if zh_name_trans or zh_desc_trans:
            if skill not in user_translations:
                user_translations[skill] = {}
            user_translations[skill]["name_zh"] = zh_name_trans or en_name
            user_translations[skill]["desc_zh"] = zh_desc_trans or en_desc
            try:
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
    
    if is_zh:
        if skill in user_translations:
            name_zh = user_translations[skill].get("name_zh")
            desc_zh = user_translations[skill].get("desc_zh")
            usage_zh = user_translations[skill].get("usage_zh", "")
        elif zh_meta:
            name_zh = zh_meta.get("name")
            desc_zh = zh_meta.get("description")

    desc_en_lines = [l.strip() for l in desc_en.split("\n") if l.strip()]
    desc_zh_lines = [l.strip() for l in desc_zh.split("\n") if l.strip()] if desc_zh else []

    # Manifest Source Metadata
    manifest_meta = None
    manifest_path = os.path.join(DATA_DIR, "skills_manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                mdata = json.load(f)
                if skill in mdata:
                    manifest_meta = mdata[skill]
        except Exception:
            pass

    # 1. Header Banner
    print(f"{CYAN}╭──────────────────────── 🏷️  技能卡片 (Skill Card) ────────────────────────╮{RESET}")
    if is_zh:
        if name_zh:
            print(f"{CYAN}│{RESET}  🏷️  技能: {GREEN}{name_zh}{RESET} {WHITE}({name_en}){RESET}")
        else:
            print(f"{CYAN}│{RESET}  🏷️  技能: {GREEN}{name_en}{RESET}")
    else:
        print(f"{CYAN}│{RESET}  🏷️  Skill: {GREEN}{name_en}{RESET}")

    # Project mount status detection
    proj_skills_dir = os.path.join(os.getcwd(), ".agents", "skills")
    proj_badge = ""
    if os.path.exists(proj_skills_dir):
        p_dest = os.path.join(proj_skills_dir, skill)
        if os.path.islink(p_dest):
            proj_badge = f"  │  {CYAN}🔗 当前项目: 已软链{RESET}" if is_zh else f"  │  {CYAN}🔗 Project: Linked{RESET}"
        elif os.path.isdir(p_dest):
            proj_badge = f"  │  {GREEN}📄 当前项目: 独立实体{RESET}" if is_zh else f"  │  {GREEN}📄 Project: Copied{RESET}"
        else:
            proj_badge = f"  │  {GREY}▫️ 当前项目: 未引入{RESET}" if is_zh else f"  │  {GREY}▫️ Project: Not linked{RESET}"

    # Metadata bar
    if manifest_meta:
        srepo = manifest_meta.get("repo_url", "")
        if "github.com/" in srepo:
            srepo = srepo.split("github.com/")[-1].removesuffix(".git")
        scommit = manifest_meta.get("commit_hash", "unknown")[:7]
        sdate = manifest_meta.get("installed_at", "")[:10]
        if is_zh:
            print(f"{CYAN}│{RESET}  {BLUE}📦 来源: {srepo}{RESET}  │  {YELLOW}🔖 版本: {scommit}{RESET}  │  {GREY}📅 安装: {sdate}{RESET}{proj_badge}")
        else:
            print(f"{CYAN}│{RESET}  {BLUE}📦 Source: {srepo}{RESET}  │  {YELLOW}🔖 Commit: {scommit}{RESET}  │  {GREY}📅 Installed: {sdate}{RESET}{proj_badge}")
    else:
        local_tag = "本地自建技能 (Local Standalone)" if is_zh else "Local Standalone Skill"
        print(f"{CYAN}│{RESET}  {GREY}🏷️  类型: {local_tag}{RESET}{proj_badge}")

    print(f"{CYAN}╰──────────────────────────────────────────────────────────────────────────╯{RESET}")

    # 2. Chinese Description Card
    if is_zh and desc_zh_lines:
        print(f"{YELLOW}╭─ 🇨🇳 功能描述 (中文) ───────────────────────────────────────────────────╮{RESET}")
        for line in desc_zh_lines:
            print(f"{YELLOW}│{RESET}  {WHITE}{line}{RESET}")
        print(f"{YELLOW}╰─────────────────────────────────────────────────────────────────────────╯{RESET}")

    # 3. English Description Card
    if desc_en_lines:
        title_en = "功能描述 (英文)" if is_zh else "Functional Description"
        print(f"{CYAN}╭─ 🇬🇧 {title_en} ───────────────────────────────────────────────────╮{RESET}")
        for line in desc_en_lines:
            print(f"{CYAN}│{RESET}  {WHITE}{line}{RESET}")
        print(f"{CYAN}╰─────────────────────────────────────────────────────────────────────────╯{RESET}")

    # 4. Usage Scenarios & Guide Card
    if is_zh and usage_zh:
        print(f"{MAGENTA}╭─ 💡 使用场景与操作指南 ─────────────────────────────────────────────────╮{RESET}")
        print(f"{MAGENTA}│{RESET}  {WHITE}{usage_zh}{RESET}")
        print(f"{MAGENTA}╰─────────────────────────────────────────────────────────────────────────╯{RESET}")

    # 5. Body Markdown Content Preview Card
    title_content = "正文内容预览 (SKILL.md)" if is_zh else "Content Preview (SKILL.md)"
    print(f"{BLUE}╭─ 📄 {title_content} ───────────────────────────────────────────╮{RESET}")
    body_to_print = zh_body if (is_zh and zh_body) else en_body
    if body_to_print:
        body_lines = body_to_print.strip().split("\n")
        printed_lines = 0
        for line in body_lines:
            if not show_full and printed_lines >= 30:
                break
            formatted = format_markdown_line(line)
            print(f"{BLUE}│{RESET}{formatted}")
            printed_lines += 1
        if not show_full and len(body_lines) > 30:
            print(f"{BLUE}│{RESET}  {GREY}... (剩余 {len(body_lines) - 30} 行内容已折叠，按 Ctrl-V 展开预览) ...{RESET}")
    print(f"{BLUE}╰─────────────────────────────────────────────────────────────────────────╯{RESET}")
            
    if is_zh and cached_to_file:
        print(f"{GREY}*已自动翻译元数据并持久化至 {DATA_DIR}/skills_zh.json*{RESET}")

    print_hotkeys_footer(is_zh)

if __name__ == "__main__":
    main()

