#!/usr/bin/env python3
import os
import sys
import re
import json
import urllib.request
import urllib.parse

DEFAULT_TRANSLATIONS = {
  "find-community": {
    "name_zh": "寻找社区",
    "desc_zh": "帮助识别和评估社区，从而围绕其构建极简业务。适用于寻找创业点子、寻找目标社群或不知道该从何开始创业的场景。",
    "usage_zh": "当您想寻找契合的受众群体（如专业群体、兴趣社群、在线论坛等），并挖掘他们反复抱怨的痛点时使用。"
  },
  "first-customers": {
    "name_zh": "获取首批客户",
    "desc_zh": "使用极简创业者指南，制定向首批 100 个客户进行销售的策略。适用于已有产品 begging 客户，或在早期销售中遇到瓶颈的场景。",
    "usage_zh": "当您完成了初步产品/服务设计，需要制定从 0 到 1 再到 100 的手动冷启动销售与获客方案时使用。"
  },
  "gemini-prompt-optimizer": {
    "name_zh": "Gemini 提示词优化器",
    "desc_zh": "系统级技能，接收原始的人类意图，并将其编译成针对 Gemini (3.5 Flash / 3.1 Pro) 架构原生定制 of、高度结构化、缓存优化且开箱即用的提示词。",
    "usage_zh": "当您想让 Gemini 模型按极其规范、高效的格式运行，或需要将模糊的想法转化为结构化的系统 Prompt 时使用。"
  },
  "grill-me": {
    "name_zh": "方案烤问 (Grill Me)",
    "desc_zh": "对用户的计划或设计进行穷追不舍的探究与提问（烤问），直到达成共识并理清决策树的每个分支。适用于压力测试方案、完善细节设计或需要理清思路的场景。",
    "usage_zh": "当您提出了一个方案或设计，需要 AI 站在严苛的评审角度，通过一连串深入细节的问题来挑战并完善该方案时使用。"
  },
  "grill-with-docs": {
    "name_zh": "结合文档烤问",
    "desc_zh": "结合现有的领域模型挑战您的计划，提炼专业术语，并在决策明确时在线更新项目文档（如 CONTEXT.md、ADR 架构决策记录）。适用于对照项目已有规范与文档来压力测试新方案的场景。",
    "usage_zh": "当您有新设计但担心偏离项目既有的架构决策和领域模型时，用此技能让 AI 依据现有文档进行一致性审计和深度对齐。"
  },
  "grow-sustainably": {
    "name_zh": "可持续增长评估",
    "desc_zh": "站在可持续、盈利性增长的角度来评估商业决策。适用于用户在进行支出、招聘、融资或业务规模扩张等决策时。",
    "usage_zh": "当您考虑是否引入外部资金、招募新员工、或者进行大笔开支，需要评估其对企业健康度和长期生存的影响时使用。"
  },
  "handoff": {
    "name_zh": "对接文档整理 (Handoff)",
    "desc_zh": "将当前的对话上下文、状态和决策压缩并整理成一份对接文档，方便另一个 Agent（或您在新对话中）无缝接手后续工作。",
    "usage_zh": "当当前对话过长、Token 即将超限，或者需要将复杂任务移交给另一个特定角色的 Agent 时使用。"
  },
  "improve-codebase-architecture": {
    "name_zh": "优化代码库架构",
    "desc_zh": "根据项目领域语言和架构决策，发掘代码库中的深层优化机会。适用于想改进架构、寻找重构机会、合并紧耦合模块或提高代码测试友好性与 AI 易读性的场景。",
    "usage_zh": "当项目规模扩大、代码变得混乱，或者需要提升代码结构规范性与可测试性时，使用此技能让 AI 给出针对性的架构重构方案。"
  },
  "marketing-plan": {
    "name_zh": "极简营销计划",
    "desc_zh": "制定一个专注于通过内容（而非广告）来构建受众群体的极简营销计划。适用于已验证产品-市场契合度（约 100 个客户）并希望通过营销进行排期扩张，或需要内容策的场景。",
    "usage_zh": "当您不想花大笔预算打广告，希望通过输出有价值的专业内容、社群运营来有机获取长期客户时使用。"
  },
  "minimalist-review": {
    "name_zh": "极简主义商业评审",
    "desc_zh": "从极简创业者的视角来评审任何商业决策、计划或策略。适用于用户需要对商业决策进行直觉核准、想要简化复杂方法或需要在多种方案间进行抉择的场景。",
    "usage_zh": "当您觉得自己的商业计划过于复杂、成本过高，想要进行“奥卡姆剃刀”式的精简以确保生存和效率时使用。"
  },
  "nuwa-skill": {
    "name_zh": "女娲造 Skill (Nuwa)",
    "desc_zh": "输入人物名、主题或模糊需求，自动进行深度调研与思维框架提炼，生成可直接运行的 Agent 人物技能包（Skill）。",
    "usage_zh": "当您想让 AI 模拟某位历史名人、行业专家（如乔布斯、马斯克）的决策视角，或需要定制一个特定的思维顾问时使用。"
  },
  "pricing": {
    "name_zh": "极简定价策略",
    "desc_zh": "运用极简创业者原则，协助制定产品或服务的价格。适用于设定价格、考虑价格调整或纠结于如何收费的场景。",
    "usage_zh": "当您不知道该怎么定位收费，或者想从“按时间收费”转向“按价值收费”时，使用此技能以获取极简而有效的定价指导。"
  },
  "processize": {
    "name_zh": "流程化交付 (Processize)",
    "desc_zh": "将产品创意转化为“人工先行”的服务流程，让您今天就可以开始交付价值。适用于有想法但在写任何代码前，想先通过纯人工方式跑通闭环、验证价值的场景。",
    "usage_zh": "当您想遵循极简创业“代码未动，服务先行”的原则，先手动把价值交到客户手里以防盲目开发时使用。"
  },
  "prototype": {
    "name_zh": "快速原型设计 (Prototype)",
    "desc_zh": "在正式开发前构建一个可抛弃的原型以充实和推敲设计。支持两条路线：运行于终端的交互式应用（用于验证状态和业务逻辑），或者通过单路由切换展示的多种截然不同的 UI 变体。适用于要快速体验核心流程或对比不同设计方案的场景。",
    "usage_zh": "当您需要快速产出可操作的视觉或逻辑 demo，以此来决定最佳设计方向、验证数据模型或响应用户试用反馈时使用。"
  },
  "validate-idea": {
    "name_zh": "创意可行性验证",
    "desc_zh": "使用极简创业者框架来验证商业点子。适用于有了创业想法，并想在投入精力构建任何东西之前测试其是否值得追求的场景。",
    "usage_zh": "当您产生了一个“伟大的想法”，但需要系统地评估其市场痛点、付费意愿以及自身竞争优势，判断是否应该真正开始时使用。"
  }
}

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

def load_user_translations():
    cache_dir = os.path.expanduser("~/.cache/zsh")
    cache_path = os.path.join(cache_dir, "skills_zh.json")
    if not os.path.exists(cache_path):
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_TRANSLATIONS, f, indent=2, ensure_ascii=False)
            return DEFAULT_TRANSLATIONS
        except Exception:
            return DEFAULT_TRANSLATIONS
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Auto-merge defaults if missing
            updated = False
            for k, v in DEFAULT_TRANSLATIONS.items():
                if k not in data:
                    data[k] = v
                    updated = True
            if updated:
                try:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass
            return data
    except Exception:
        return DEFAULT_TRANSLATIONS

def main():
    force_translate = False
    if "--force-translate" in sys.argv:
        force_translate = True
        sys.argv.remove("--force-translate")

    show_full = False
    if "--full" in sys.argv:
        show_full = True
        sys.argv.remove("--full")

    if len(sys.argv) < 2:
        print("Usage: preview_skill.py [--force-translate] [--full] <skill_name>")
        sys.exit(1)

    skill = sys.argv[1]
    
    if force_translate and skill.startswith("group:"):
        sys.exit(0)
    
    lang = os.environ.get("ZFL_LANG") or os.environ.get("LANG", "en")
    is_zh = lang.startswith("zh")

    if skill.startswith("group:"):
        # Group preview logic
        gkey = skill[6:]
        # Load groups
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            import resolve_skills
            groups = resolve_skills.load_groups()
        except Exception:
            groups = {}
        
        if gkey not in groups:
            if is_zh:
                print(f"\033[1;31m错误：未找到分组 '{gkey}'\033[0m")
            else:
                print(f"\033[1;31mError: Group '{gkey}' not found\033[0m")
            sys.exit(0)
            
        ginfo = groups[gkey]
        if isinstance(ginfo, dict):
            gname = ginfo.get("name", gkey)
            gskills = ginfo.get("skills", [])
            is_ordered = ginfo.get("ordered", False)
        else:
            gname = gkey
            gskills = ginfo
            is_ordered = False

        def circled_num(n):
            return chr(0x245F + n) if 1 <= n <= 20 else f"({n})"

        print("\033[1;36m" + "=" * 55 + "\033[0m")
        if is_zh:
            print(f"\033[1;32m 技能分组: \033[1;37m{gname} ({gkey})\033[0m")
            print("\033[1;36m" + "=" * 55 + "\033[0m")
            if is_ordered:
                print(f"\033[1;33m⚑ 有序分组 — 推荐按以下顺序依次调用：\033[0m\n")
            else:
                print(f"\033[1;35m💡 该分组包含以下 {len(gskills)} 个技能 (空格键多选，Enter 键批量链接):\033[0m\n")
        else:
            print(f"\033[1;32m Skill Group: \033[1;37m{gname} ({gkey})\033[0m")
            print("\033[1;36m" + "=" * 55 + "\033[0m")
            if is_ordered:
                print(f"\033[1;33m⚑ Ordered group — recommended call order:\033[0m\n")
            else:
                print(f"\033[1;35m💡 This group contains the following {len(gskills)} skills (Space to multi-select, Enter to bulk link):\033[0m\n")
        
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
                bullet = f"\033[1;33m{circled_num(idx + 1)}\033[0m"
            else:
                bullet = "\033[1;32m•\033[0m"
            print(f"  {bullet} \033[1;32m{s}\033[0m ({name_display})")
            if desc_display:
                desc_single = " ".join([l.strip() for l in desc_display.split("\n") if l.strip()])
                if is_zh:
                    print(f"    \033[1;30m描述: {desc_single}\033[0m")
                else:
                    print(f"    \033[1;30mDescription: {desc_single}\033[0m")
            print()
        sys.exit(0)

    skills_dir = os.path.expanduser("~/.agents/skills")
    skill_dir = os.path.join(skills_dir, skill)
    en_path = os.path.join(skill_dir, "SKILL.md")

    if not os.path.exists(en_path):
        if is_zh:
            print(f"\033[1;31m错误：未找到技能 '{skill}' 的 SKILL.md 文件\033[0m")
            print(f"搜索路径: {en_path}")
        else:
            print(f"\033[1;31mError: SKILL.md file not found for skill '{skill}'\033[0m")
            print(f"Search path: {en_path}")
        sys.exit(0)

    # 1. Load user cache translation DB
    cache_dir = os.path.expanduser("~/.cache/zsh")
    cache_path = os.path.join(cache_dir, "skills_zh.json")
    user_translations = load_user_translations()

    # 2. Check if a local Chinese translation file exists
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

    # 3. Dynamic translation if not found (or force translate) and preference is Chinese
    cached_to_file = False
    if (is_zh or force_translate) and not zh_meta and en_meta and (skill not in user_translations or force_translate):
        en_name = en_meta.get("name") or skill
        en_desc = en_meta.get("description") or ""
        
        zh_name_trans = translate_via_google(en_name)
        zh_desc_trans = translate_via_google(en_desc)
        
        if zh_name_trans or zh_desc_trans:
            if skill not in user_translations:
                user_translations[skill] = {}
            user_translations[skill]["name_zh"] = zh_name_trans or en_name
            user_translations[skill]["desc_zh"] = zh_desc_trans or en_desc
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
    
    if is_zh:
        if skill in user_translations:
            name_zh = user_translations[skill].get("name_zh")
            desc_zh = user_translations[skill].get("desc_zh")
            usage_zh = user_translations[skill].get("usage_zh", "")
        elif zh_meta:
            name_zh = zh_meta.get("name")
            desc_zh = zh_meta.get("description")

    # Clean description lists
    desc_en_lines = [l.strip() for l in desc_en.split("\n") if l.strip()]
    desc_zh_lines = [l.strip() for l in desc_zh.split("\n") if l.strip()] if desc_zh else []

    # Print layout
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    if is_zh:
        if name_zh:
            print(f"\033[1;32m 技能: \033[1;37m{name_zh} ({name_en})\033[0m")
        else:
            print(f"\033[1;32m 技能: \033[1;37m{name_en}\033[0m")
    else:
        print(f"\033[1;32m Skill: \033[1;37m{name_en}\033[0m")
    print("\033[1;36m" + "=" * 55 + "\033[0m")
    
    # Chinese Description
    if is_zh and desc_zh_lines:
        print("\033[1;33m功能描述 (中文):\033[0m")
        for line in desc_zh_lines:
            print(f"  {line}")
        print("\033[1;36m" + "-" * 55 + "\033[0m")

    # English Description
    if desc_en_lines:
        if is_zh:
            print("\033[1;33m功能描述 (英文):\033[0m")
        else:
            print("\033[1;33mFunctional Description:\033[0m")
        for line in desc_en_lines:
            print(f"  {line}")
        print("\033[1;36m" + "-" * 55 + "\033[0m")

    # Usage Tips
    if is_zh and usage_zh:
        print("\033[1;35m💡 使用场景与指南 (中文):\033[0m")
        print(f"  {usage_zh}")
        print("\033[1;36m" + "-" * 55 + "\033[0m")

    # Content Preview
    if is_zh:
        print("\033[1;34m内容预览:\033[0m")
    else:
        print("\033[1;34mContent Preview:\033[0m")
        
    body_to_print = zh_body if (is_zh and zh_body) else en_body
    if body_to_print:
        body_lines = body_to_print.strip().split("\n")
        printed_lines = 0
        for line in body_lines:
            if not show_full and printed_lines >= 25:
                break
            print(f"  {line}")
            printed_lines += 1
        if not show_full and len(body_lines) > 25:
            print("\033[1;30m  ... (more content below) ...\033[0m")
            
    if is_zh and cached_to_file:
        print("\033[1;30m  *已自动翻译元数据并缓存至 ~/.cache/zsh/skills_zh.json*\033[0m")


if __name__ == "__main__":
    main()
