#!/usr/bin/env python3
import os
import sys
import json
import re
import unicodedata

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
    "desc_zh": "系统级技能，接收原始的人类意图，并将其编译成针对 Gemini (3.5 Flash / 3.1 Pro) 架构原生定制的、高度结构化、缓存优化且开箱即用的提示词。",
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

def get_display_width(s):
    w = 0
    for ch in s:
        status = unicodedata.east_asian_width(ch)
        if status in ('F', 'W'):
            w += 2
        else:
            w += 1
    return w

def pad_display(s, target_width):
    curr_w = get_display_width(s)
    if curr_w >= target_width:
        return s
    return s + " " * (target_width - curr_w)

def main():
    skills_dir = os.path.expanduser("~/.agents/skills")
    if not os.path.exists(skills_dir):
        print(f"Error: {skills_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    lang = os.environ.get("ZFL_LANG") or os.environ.get("LANG", "en")
    is_zh = lang.startswith("zh")

    # Load translations from ~/.cache/zsh/skills_zh.json (initialize if needed)
    user_translations = load_user_translations()

    items = []

    # Load groups and add them to items
    groups = {}
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import resolve_skills
        groups = resolve_skills.load_groups()
    except Exception:
        pass

    for gid, info in sorted(groups.items()):
        if isinstance(info, dict):
            name = info.get("name", gid)
            gskills = info.get("skills", [])
            is_ordered = info.get("ordered", False)
        else:
            name = gid
            gskills = info
            is_ordered = False

        item_id = f"group:{gid}"
        name_bracket = f"[分组: {name}]" if is_zh else f"[Group: {name}]"

        if is_ordered:
            def _cn(n):
                return chr(0x245F + n) if 1 <= n <= 20 else f"({n})"
            numbered = " ".join(f"{_cn(i+1)}{s}" for i, s in enumerate(gskills))
            desc_single = f"⚑ 有序 · {numbered}" if is_zh else f"⚑ Ordered · {numbered}"
        else:
            gskills_str = ", ".join(gskills)
            desc_single = f"包含: {gskills_str}" if is_zh else f"Contains: {gskills_str}"

        items.append({
            "id": item_id,
            "name_bracket": name_bracket,
            "desc": desc_single
        })

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
        
        if is_zh:
            # 1. Check database cache for Chinese translations
            if skill in user_translations:
                name_display = user_translations[skill].get("name_zh") or user_translations[skill].get("name", skill)
                desc_display = user_translations[skill].get("desc_zh") or user_translations[skill].get("description", "")
            else:
                # 2. Check local SKILL.zh.md or SKILL.zh-CN.md (fallback)
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
                    # 3. Fallback to English SKILL.md
                    en_path = os.path.join(skills_dir, skill, "SKILL.md")
                    en_data = parse_md_frontmatter(en_path)
                    if en_data:
                        name_display = en_data.get("name") or skill
                        desc_display = en_data.get("description") or ""
        else:
            # English preference: load from English SKILL.md directly
            en_path = os.path.join(skills_dir, skill, "SKILL.md")
            en_data = parse_md_frontmatter(en_path)
            if en_data:
                name_display = en_data.get("name") or skill
                desc_display = en_data.get("description") or ""

        # Make description single line and trim leading/trailing quotes
        desc_single = " ".join([l.strip() for l in desc_display.split("\n") if l.strip()]).strip('“"”')
        if len(desc_single) > 60:
            desc_single = desc_single[:57] + "..."

        items.append({
            "id": skill,
            "name_bracket": f"[{name_display}]",
            "desc": desc_single
        })

    if not items:
        return

    # Calculate padding widths
    max_id_len = max([len(x["id"]) for x in items] + [30])
    id_col_width = max_id_len + 3

    max_name_len = max([get_display_width(x["name_bracket"]) for x in items] + [20])
    name_col_width = max_name_len + 3

    for item in items:
        col1 = pad_display(item["id"], id_col_width)
        col2 = pad_display(item["name_bracket"], name_col_width)
        col3 = item["desc"]
        print(f"{col1}{col2}{col3}")

if __name__ == "__main__":
    main()

