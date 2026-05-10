##
# AI Copy Project (aicp)
#
# 功能：
#   生成适合投喂 AI 的项目上下文（目录树 + 文件索引 + 代码片段预算裁剪），
#   支持复制到剪贴板（wl-copy/xclip/pbcopy）以及输出到终端/文件。
#
# 新增：
#   --init  一键生成“项目认知包”（适合 AI 快速建立项目理解）
#
# 参数（完整版见 aicp -h 或 aicp --help <topic>）：
#   -a, --all
#   -c, --choose <...>
#   --mode <fast|balanced|deep>
#   --init
#   --query / --query-regex
#   --exclude / --exclude-regex
#   --changed / --changed-from / --changed-commit-range
#   --snippet-around-query / --snippet-context-lines
#   --output-format / --quality-report
#   --max-files / --max-total-chars / --max-file-chars
#   --ignore-docs
#   --prompt / --prompt-file
#   --print / --out / --no-copy
#   -h, --help [topic]
#
aicp() {
    load_color GREEN YELLOW RED BLUE RESET

    _aicp_help() {
        local topic="${1:-general}"
        case "$topic" in
            general|"")
                cat <<'EOF'
aicp - AI 上下文复制工具

快速上手:
  aicp --init
  aicp -a
  aicp --help mode
  aicp --help init

常见场景:
  1) 让 AI 快速理解项目（推荐）
     aicp --init

  2) 全量打包
     aicp -a

  3) 只看改动
     aicp --changed --prompt "请按风险等级 review"

  4) 定向聚焦
     aicp -a --query auth --query token --exclude-regex "dist|vendor"

主题帮助:
  aicp --help mode      # 复制等级说明（fast/balanced/deep）
  aicp --help init      # init 预设做了什么
  aicp --help filter    # query/exclude 的差异
  aicp --help changed   # git 改动筛选
  aicp --help output    # 输出格式与预算控制
  aicp --help examples  # 更多组合示例
EOF
                ;;

            mode)
                cat <<'EOF'
[复制等级说明]

fast:
  - 内容：PROJECT TREE + FILE INDEX
  - 不包含 CODE SNIPPETS
  - 适用：先让 AI 建立“目录与模块地图”

balanced (默认):
  - 内容：TREE + INDEX + 预算内代码片段
  - 适用：日常分析、review、重构建议

deep:
  - 内容：与 balanced 相同，但预算更大、片段更多
  - 适用：复杂排障/深度重构/跨模块分析

建议:
  - 第一步：fast 建图
  - 第二步：balanced 或 deep 深挖
EOF
                ;;

            init)
                cat <<'EOF'
[--init 说明]

用途:
  一键生成“项目认知包”，用于 AI 快速建立对项目的整体理解。

默认行为（若你未手动覆盖）:
  - 自动启用全量扫描（-a）
  - 必含 PROJECT TREE（源代码目录树）与 FILE INDEX
  - mode 自动设为 balanced
  - 自动打开质量报告（--quality-report）
  - 默认预算：
      --max-files 120
      --max-total-chars 85000
      --max-file-chars 2200
  - 自动注入认知提示词（若你未显式传 --prompt）

你可以叠加:
  aicp --init --ignore-docs
  aicp --init --changed
  aicp --init --output-format json
EOF
                ;;

            filter)
                cat <<'EOF'
[筛选参数说明]

纳入过滤（include）:
  --query <keyword>
  --query-regex <regex>
  命中任一即纳入。

排除过滤（exclude）:
  --exclude <keyword>
  --exclude-regex <regex>
  命中即剔除。

文档过滤:
  --ignore-docs
  排除 doxygen/markdown/sphinx/wiki/manual 等文档类文件。

示例:
  aicp -a --query auth --query token --exclude-regex "dist|vendor"
EOF
                ;;

            changed)
                cat <<'EOF'
[改动筛选说明]

--changed
  相对 HEAD 的改动 + 未跟踪文件

--changed-from <ref>
  相对某分支/标签的改动 + 未跟踪文件
  例如: --changed-from main

--changed-commit-range <A..B>
  相对提交区间的改动 + 未跟踪文件
  例如: --changed-commit-range HEAD~5..HEAD
EOF
                ;;

            output)
                cat <<'EOF'
[输出与预算说明]

输出格式:
  --output-format markdown|plain|json

质量报告:
  --quality-report

预算覆盖:
  --max-files <n>
  --max-total-chars <n>
  --max-file-chars <n>

输出去向:
  默认复制剪贴板；可配合 --no-copy --print --out <file>
EOF
                ;;

            examples)
                cat <<'EOF'
[示例合集]

1) 快速认知
   aicp --init

2) 快速认知 + 忽略文档
   aicp --init --ignore-docs

3) 仅改动 review
   aicp --changed --prompt "请给出风险矩阵和最小修复方案"

4) 相对主分支改动
   aicp --changed-from main --mode balanced

5) 提交区间分析
   aicp --changed-commit-range HEAD~8..HEAD --output-format plain --print

6) 安全相关聚焦
   aicp -a --query-regex "token|secret|password|apikey" --exclude-regex "dist|vendor|node_modules"

7) 命中点邻域片段
   aicp -a --query auth --snippet-around-query --snippet-context-lines 20

8) 机器消费 JSON
   aicp -a --output-format json --quality-report --no-copy --print

9) 控制上下文体积
   aicp -a --max-files 60 --max-total-chars 70000 --max-file-chars 1800
EOF
                ;;

            *)
                echo "未知 help 主题: $topic"
                echo "可用主题: mode, init, filter, changed, output, examples"
                ;;
        esac
    }

    local mode="balanced"
    local mode_user_set=0
    local all_mode=0
    local copy_mode=1
    local print_mode=0
    local changed_mode=0
    local init_mode=0

    local changed_from=""
    local changed_commit_range=""
    local out_file=""
    local prompt_text=""
    local prompt_file=""

    local prompt_user_set=0
    local snippet_around_query=0
    local snippet_context_lines=""
    local output_format="markdown"
    local quality_report=0
    local ignore_docs=0

    local max_files=""
    local max_total_chars=""
    local max_file_chars=""

    local -a targets=()
    local -a queries=()
    local -a query_regexes=()
    local -a excludes=()
    local -a exclude_regexes=()

    local arg
    while [[ $# -gt 0 ]]; do
        arg="$1"
        case "$arg" in
            -a|--all)
                all_mode=1; shift ;;
            -c|--choose)
                shift
                while [[ $# -gt 0 && "$1" != -* ]]; do
                    targets+=("$1")
                    shift
                done
                ;;
            --mode)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --mode 缺少参数"; return 1; }
                mode="$2"; mode_user_set=1; shift 2 ;;
            --init)
                init_mode=1; shift ;;
            --query)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --query 缺少参数"; return 1; }
                queries+=("$2"); shift 2 ;;
            --query-regex)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --query-regex 缺少参数"; return 1; }
                query_regexes+=("$2"); shift 2 ;;
            --exclude)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --exclude 缺少参数"; return 1; }
                excludes+=("$2"); shift 2 ;;
            --exclude-regex)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --exclude-regex 缺少参数"; return 1; }
                exclude_regexes+=("$2"); shift 2 ;;
            --changed)
                changed_mode=1; shift ;;
            --changed-from)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --changed-from 缺少参数"; return 1; }
                changed_from="$2"; shift 2 ;;
            --changed-commit-range)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --changed-commit-range 缺少参数"; return 1; }
                changed_commit_range="$2"; shift 2 ;;
            --snippet-around-query)
                snippet_around_query=1; shift ;;
            --snippet-context-lines)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --snippet-context-lines 缺少参数"; return 1; }
                snippet_context_lines="$2"; shift 2 ;;
            --output-format)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --output-format 缺少参数"; return 1; }
                output_format="$2"; shift 2 ;;
            --quality-report)
                quality_report=1; shift ;;
            --ignore-docs)
                ignore_docs=1; shift ;;
            --max-files)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --max-files 缺少参数"; return 1; }
                max_files="$2"; shift 2 ;;
            --max-total-chars)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --max-total-chars 缺少参数"; return 1; }
                max_total_chars="$2"; shift 2 ;;
            --max-file-chars)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --max-file-chars 缺少参数"; return 1; }
                max_file_chars="$2"; shift 2 ;;
            --prompt)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --prompt 缺少参数"; return 1; }
                prompt_text="$2"; prompt_user_set=1; shift 2 ;;
            --prompt-file)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --prompt-file 缺少参数"; return 1; }
                prompt_file="$2"; shift 2 ;;
            --print)
                print_mode=1; shift ;;
            --out)
                [[ -z "$2" ]] && { echo -e "${RED}[ERROR]${RESET} --out 缺少参数"; return 1; }
                out_file="$2"; shift 2 ;;
            --no-copy)
                copy_mode=0; shift ;;
            -h|--help)
                if [[ -n "$2" && "$2" != -* ]]; then
                    _aicp_help "$2"
                else
                    _aicp_help "general"
                fi
                return 0 ;;
            *)
                echo -e "${RED}[ERROR]${RESET} 未知参数: $arg"
                echo "使用 aicp -h 查看帮助"
                return 1 ;;
        esac
    done

    # init 预设：用于 AI 快速建立项目认知
    if [[ $init_mode -eq 1 ]]; then
        [[ $mode_user_set -eq 0 ]] && mode="balanced"
        [[ $all_mode -eq 0 && ${#targets[@]} -eq 0 ]] && all_mode=1
        [[ $quality_report -eq 0 ]] && quality_report=1
        [[ -z "$max_files" ]] && max_files="120"
        [[ -z "$max_total_chars" ]] && max_total_chars="85000"
        [[ -z "$max_file_chars" ]] && max_file_chars="2200"
        if [[ $prompt_user_set -eq 0 && -z "$prompt_file" ]]; then
            prompt_text="请先建立该项目的认知地图：1) 分层与职责 2) 启动链路与调用路径 3) 关键模块关系 4) 高风险改动点与建议入口。"
        fi
    fi

    if [[ "$mode" != "fast" && "$mode" != "balanced" && "$mode" != "deep" ]]; then
        echo -e "${RED}[ERROR]${RESET} --mode 仅支持 fast / balanced / deep"; return 1
    fi
    if [[ "$output_format" != "markdown" && "$output_format" != "plain" && "$output_format" != "json" ]]; then
        echo -e "${RED}[ERROR]${RESET} --output-format 仅支持 markdown/plain/json"; return 1
    fi

    local n
    for n in "$snippet_context_lines" "$max_files" "$max_total_chars" "$max_file_chars"; do
        [[ -z "$n" ]] && continue
        if [[ ! "$n" =~ ^[0-9]+$ ]]; then
            echo -e "${RED}[ERROR]${RESET} 数值参数必须为正整数"; return 1
        fi
    done

    if [[ -n "$prompt_file" ]]; then
        if [[ ! -f "$prompt_file" || ! -r "$prompt_file" ]]; then
            echo -e "${RED}[ERROR]${RESET} prompt 文件不存在或不可读: $prompt_file"; return 1
        fi
        prompt_text="$(cat "$prompt_file")"
    fi

    if [[ $all_mode -eq 0 && ${#targets[@]} -eq 0 ]]; then
        echo -e "${YELLOW}[aicp]${RESET} 未指定目标，默认使用 -a 扫描当前目录"
        all_mode=1
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}[ERROR]${RESET} 未找到 python3，无法生成上下文。"; return 1
    fi

    local py_script="$ZFL_HOME/python/aicp_context.py"
    [[ ! -f "$py_script" ]] && { echo -e "${RED}[ERROR]${RESET} 缺少脚本: $py_script"; return 1; }

    local tmp_file
    tmp_file=$(mktemp /tmp/aicp.XXXXXX.txt) || return 1

    local -a cmd
    cmd=(python3 "$py_script" --root "$PWD" --mode "$mode" --output-format "$output_format")

    [[ $all_mode -eq 1 ]] && cmd+=(--all)
    [[ $changed_mode -eq 1 ]] && cmd+=(--changed)
    [[ -n "$changed_from" ]] && cmd+=(--changed-from "$changed_from")
    [[ -n "$changed_commit_range" ]] && cmd+=(--changed-commit-range "$changed_commit_range")
    [[ -n "$prompt_text" ]] && cmd+=(--prompt "$prompt_text")
    [[ $snippet_around_query -eq 1 ]] && cmd+=(--snippet-around-query)
    [[ -n "$snippet_context_lines" ]] && cmd+=(--snippet-context-lines "$snippet_context_lines")
    [[ $quality_report -eq 1 ]] && cmd+=(--quality-report)
    [[ $ignore_docs -eq 1 ]] && cmd+=(--ignore-docs)
    [[ -n "$max_files" ]] && cmd+=(--max-files "$max_files")
    [[ -n "$max_total_chars" ]] && cmd+=(--max-total-chars "$max_total_chars")
    [[ -n "$max_file_chars" ]] && cmd+=(--max-file-chars "$max_file_chars")

    local t q r ex exr
    for t in "${targets[@]}"; do cmd+=(--target "$t"); done
    for q in "${queries[@]}"; do cmd+=(--query "$q"); done
    for r in "${query_regexes[@]}"; do cmd+=(--query-regex "$r"); done
    for ex in "${excludes[@]}"; do cmd+=(--exclude "$ex"); done
    for exr in "${exclude_regexes[@]}"; do cmd+=(--exclude-regex "$exr"); done

    local changed_effective=0
    [[ $changed_mode -eq 1 || -n "$changed_from" || -n "$changed_commit_range" ]] && changed_effective=1

    echo -e "${BLUE}[aicp]${RESET} 生成上下文中... mode=${mode}, init=${init_mode}, format=${output_format}, changed=${changed_effective}, changed_from=${changed_from:-none}, commit_range=${changed_commit_range:-none}, query_count=${#queries[@]}, regex_count=${#query_regexes[@]}, exclude_count=${#excludes[@]}, exclude_regex_count=${#exclude_regexes[@]}, ignore_docs=${ignore_docs}, around_query=${snippet_around_query}, quality=${quality_report}"

    if ! "${cmd[@]}" > "$tmp_file"; then
        rm -f "$tmp_file"
        echo -e "${RED}[ERROR]${RESET} 上下文生成失败。"
        return 1
    fi

    local token_count
    token_count=$(python3 - "$tmp_file" <<'PY'
import sys
from pathlib import Path

p = Path(sys.argv[1])
text = p.read_text(encoding='utf-8', errors='ignore')

try:
    import tiktoken  # type: ignore
    enc = tiktoken.get_encoding("cl100k_base")
    n = len(enc.encode(text))
    print(n)
except Exception:
    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    non_ascii_chars = len(text) - ascii_chars
    n = int(round(ascii_chars / 4.0 + non_ascii_chars))
    print(max(n, 1))
PY
)

    if [[ $copy_mode -eq 1 ]]; then
        if command -v wl-copy >/dev/null 2>&1; then
            cat "$tmp_file" | wl-copy
            echo -e "${GREEN}[SUCCESS]${RESET} 已复制到剪贴板 (wl-copy)。"
        elif command -v xclip >/dev/null 2>&1; then
            cat "$tmp_file" | xclip -selection clipboard
            echo -e "${GREEN}[SUCCESS]${RESET} 已复制到剪贴板 (xclip)。"
        elif command -v pbcopy >/dev/null 2>&1; then
            cat "$tmp_file" | pbcopy
            echo -e "${GREEN}[SUCCESS]${RESET} 已复制到剪贴板 (pbcopy)。"
        else
            echo -e "${YELLOW}[WARN]${RESET} 未检测到剪贴板命令(wl-copy/xclip/pbcopy)，跳过复制。"
        fi
    fi

    [[ -n "$out_file" ]] && { cp "$tmp_file" "$out_file"; echo -e "${GREEN}[aicp]${RESET} 已写入文件: $out_file"; }
    [[ $print_mode -eq 1 ]] && cat "$tmp_file"

    echo -e "${BLUE}[aicp]${RESET} 完成，预估 token 数: ${token_count}"
    rm -f "$tmp_file"
}
