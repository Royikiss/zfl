#? name: aicp
#? description: Generate project context suitable for AI consumption (directory tree + file index + code snippet budget trimming)
#? author: Royi
#? version: 1.0.0
#? deps: python3, git
#? usage: aicp [options] [target files/directories...]
#? example: aicp --changed --exec

aicp() {
    zfl_require python3 git || return 1
    load_color GREEN YELLOW RED BLUE RESET
    local lang=${ZFL_LANG:-${LANG%%.*}}

    _aicp_help() {
        local topic="${1:-general}"
        case "$topic" in
            general)     _aicp_help_general | _aicp_maybe_page ;;
            all)         _aicp_help_all | _aicp_maybe_page ;;
            mode|init|filter|changed|output|examples|exec|read)
                         "_aicp_help_sub_$topic" ;;
            *)
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}未知帮助主题:${RESET} $topic"
                    echo -e "可用主题: general mode init filter changed output examples exec read all"
                    echo -e "运行 ${GREEN}aicp -h${RESET} 查看交互式主题选择器"
                else
                    echo -e "${RED}Unknown help topic:${RESET} $topic"
                    echo -e "Available topics: general mode init filter changed output examples exec read all"
                    echo -e "Run ${GREEN}aicp -h${RESET} to check interactive topic selector"
                fi
                ;;
        esac
    }

    _aicp_maybe_page() {
        if [[ -t 1 ]] && command -v less >/dev/null 2>&1; then
            less -R
        else
            cat
        fi
    }

    _aicp_help_row() {
        printf "  ${GREEN}%-30s${RESET} %-34s ${BLUE}[%s]${RESET}
" "$1" "$2" "$3"
    }

    _aicp_help_general() {
        if [[ "$lang" == zh* ]]; then
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
            echo -e "${GREEN}aicp${RESET} - AI 上下文复制工具"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
            echo
            echo -e "${YELLOW}用法:${RESET}  aicp [参数...] [-c <文件/目录>...]"
            echo
            echo -e "${YELLOW}模式控制:${RESET}"
            _aicp_help_row "-a, --all" "全量扫描当前目录" "off"
            _aicp_help_row "-c, --choose <path>..." "手动指定目标文件/目录" "—"
            _aicp_help_row "--mode <fast|balanced|deep|full>" "复制等级" "balanced"
            echo
            echo -e "${YELLOW}筛选聚焦:${RESET}"
            _aicp_help_row "--query <keyword>" "关键词纳入（可多次）" "—"
            _aicp_help_row "--query-regex <regex>" "正则纳入（可多次）" "—"
            _aicp_help_row "--exclude <keyword>" "关键词排除（可多次）" "—"
            _aicp_help_row "--exclude-regex <regex>" "正则排除（可多次）" "—"
            _aicp_help_row "--ignore-docs" "过滤文档类文件" "off"
            echo
            echo -e "${YELLOW}Git 改动:${RESET}"
            _aicp_help_row "--changed" "相对 HEAD 改动+未跟踪" "off"
            _aicp_help_row "--changed-from <ref>" "相对某分支/标签对比" "—"
            _aicp_help_row "--changed-commit-range <A..B>" "提交区间对比" "—"
            echo
            echo -e "${YELLOW}代码片段:${RESET}"
            _aicp_help_row "--snippet-around-query" "命中点邻域模式" "off"
            _aicp_help_row "--snippet-context-lines <n>" "邻域扩展行数" "auto"
            echo
            echo -e "${YELLOW}输出控制:${RESET}"
            _aicp_help_row "--output-format <fmt>" "格式 markdown/plain/json" "markdown"
            _aicp_help_row "--quality-report" "附质量报告" "off"
            _aicp_help_row "--print" "打印到终端" "off"
            _aicp_help_row "--out <file>" "写入文件" "—"
            _aicp_help_row "--no-copy" "跳过剪贴板复制" "off"
            _aicp_help_row "--read <path[:l1-l2]>..." "读取文件指定行到剪贴板" "—"
            echo
            echo -e "${YELLOW}预算控制:${RESET}"
            _aicp_help_row "--max-files <n>" "文件总数上限" "auto"
            _aicp_help_row "--max-total-chars <n>" "总字符数上限" "auto"
            _aicp_help_row "--max-file-chars <n>" "单文件字符上限" "auto"
            echo
            echo -e "${YELLOW}预设与提示:${RESET}"
            _aicp_help_row "--init" "项目认知预设" "off"
            _aicp_help_row "--exec" "交互式 AI 协作模式" "off"
            _aicp_help_row "--prompt <text>" "自定义提示词" "—"
            _aicp_help_row "--prompt-file <path>" "从文件读取提示词" "—"
            echo
            echo -e "${BLUE}────────────────────────────────────────────────────────────────────────${RESET}"
            echo -e "${YELLOW}示例速览:${RESET}"
            echo -e "  ${GREEN}aicp --init${RESET}                          快速认知项目"
            echo -e "  ${GREEN}aicp -a${RESET}                              全量打包"
            echo -e "  ${GREEN}aicp --changed --prompt "review"${RESET}             仅改动审查"
            echo -e "  ${GREEN}aicp -a --query auth --exclude-regex "dist"${RESET}    定向聚焦"
            echo -e "  ${GREEN}aicp --exec -a${RESET}                       交互式 AI 协作"
            echo -e "  ${GREEN}aicp --read src/main.py:10-30${RESET}         读取文件指定行到剪贴板"
            echo
            echo -e "深入主题:  ${GREEN}aicp --help${RESET} <mode|init|filter|changed|output|examples|exec|read|all>"
        else
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
            echo -e "${GREEN}aicp${RESET} - AI Context Packaging & Copy Tool"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
            echo
            echo -e "${YELLOW}Usage:${RESET}  aicp [options] [-c <file/dir>...]"
            echo
            echo -e "${YELLOW}Mode Control:${RESET}"
            _aicp_help_row "-a, --all" "Scan the entire current directory" "off"
            _aicp_help_row "-c, --choose <path>..." "Manually specify target files/dirs" "—"
            _aicp_help_row "--mode <fast|balanced|deep|full>" "Context mode level" "balanced"
            echo
            echo -e "${YELLOW}Filters:${RESET}"
            _aicp_help_row "--query <keyword>" "Include file if keyword matches (repeatable)" "—"
            _aicp_help_row "--query-regex <regex>" "Include file if regex matches (repeatable)" "—"
            _aicp_help_row "--exclude <keyword>" "Exclude file if keyword matches (repeatable)" "—"
            _aicp_help_row "--exclude-regex <regex>" "Exclude file if regex matches (repeatable)" "—"
            _aicp_help_row "--ignore-docs" "Ignore documentation files" "off"
            echo
            echo -e "${YELLOW}Git Changes:${RESET}"
            _aicp_help_row "--changed" "Modified & untracked files relative to HEAD" "off"
            _aicp_help_row "--changed-from <ref>" "Compare changes against a branch/tag" "—"
            _aicp_help_row "--changed-commit-range <A..B>" "Compare changes in commit range" "—"
            echo
            echo -e "${YELLOW}Code Snippets:${RESET}"
            _aicp_help_row "--snippet-around-query" "Query match window snippet mode" "off"
            _aicp_help_row "--snippet-context-lines <n>" "Context lines around query match" "auto"
            echo
            echo -e "${YELLOW}Output Control:${RESET}"
            _aicp_help_row "--output-format <fmt>" "Format: markdown/plain/json" "markdown"
            _aicp_help_row "--quality-report" "Append code quality report" "off"
            _aicp_help_row "--print" "Print output directly to stdout" "off"
            _aicp_help_row "--out <file>" "Write output to file" "—"
            _aicp_help_row "--no-copy" "Do not copy output to clipboard" "off"
            _aicp_help_row "--read <path[:l1-l2]>..." "Read lines from files to clipboard" "—"
            echo
            echo -e "${YELLOW}Budget Limits:${RESET}"
            _aicp_help_row "--max-files <n>" "Maximum files limit" "auto"
            _aicp_help_row "--max-total-chars <n>" "Maximum total character limit" "auto"
            _aicp_help_row "--max-file-chars <n>" "Maximum per-file character limit" "auto"
            echo
            echo -e "${YELLOW}Presets & Interactive:${RESET}"
            _aicp_help_row "--init" "Initialize project context preset" "off"
            _aicp_help_row "--exec" "Interactive AI collaboration mode" "off"
            _aicp_help_row "--prompt <text>" "Custom instruction prompt" "—"
            _aicp_help_row "--prompt-file <path>" "Load prompt from file" "—"
            echo
            echo -e "${BLUE}────────────────────────────────────────────────────────────────────────${RESET}"
            echo -e "${YELLOW}Quick Examples:${RESET}"
            echo -e "  ${GREEN}aicp --init${RESET}                          Quick project map onboarding"
            echo -e "  ${GREEN}aicp -a${RESET}                              Package entire workspace"
            echo -e "  ${GREEN}aicp --changed --prompt "review"${RESET}             Review modified files"
            echo -e "  ${GREEN}aicp -a --query auth --exclude-regex "dist"${RESET}    Filter targeting"
            echo -e "  ${GREEN}aicp --exec -a${RESET}                       Interactive AI collaboration"
            echo -e "  ${GREEN}aicp --read src/main.py:10-30${RESET}         Read specific lines to clipboard"
            echo
            echo -e "Sub-topics:  ${GREEN}aicp --help${RESET} <mode|init|filter|changed|output|examples|exec|read|all>"
        fi
    }

    _aicp_help_all() {
        _aicp_help_general
        echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════${RESET}\n"
        _aicp_help_sub_mode
        echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════${RESET}\n"
        _aicp_help_sub_init
        echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════${RESET}\n"
        _aicp_help_sub_filter
        echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════${RESET}\n"
        _aicp_help_sub_changed
        echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════${RESET}\n"
        _aicp_help_sub_output
        echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════${RESET}\n"
        _aicp_help_sub_examples
        echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════${RESET}\n"
        _aicp_help_sub_exec
        echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════════${RESET}\n"
        _aicp_help_sub_read
    }

    _aicp_help_sub_mode() {
        if [[ "$lang" == zh* ]]; then
            cat <<'EOF'
[复制等级说明]

fast:
  - 内容：PROJECT TREE + FILE INDEX
  - 不包含 CODE SNIPPETS
  - 适用：先让 AI 建立"目录与模块地图"

balanced (默认):
  - 内容：TREE + INDEX + 预算内代码片段
  - 适用：日常分析、review、重构建议

deep:
  - 内容：与 balanced 相同，但预算更大、片段更多
  - 适用：复杂排障/深度重构/跨模块分析

full:
  - 内容：TREE + INDEX + 完整源码（不截断）
  - 涵盖所有文本文件（不限制后缀）
  - 若项目根目录存在 .ignore 文件，按其中规则排除文件/目录
  - 适用：需要完整项目源码投喂的场景

建议:
  - 第一步：fast 建图
  - 第二步：balanced 或 deep 深挖
EOF
        else
            cat <<'EOF'
[Context Modes Level Description]

fast:
  - Content: PROJECT TREE + FILE INDEX
  - Code snippets are excluded
  - Usage: Let the AI build a quick "directory & module map" first.

balanced (default):
  - Content: TREE + INDEX + code snippets under budget limits
  - Usage: Daily code analysis, review, refactoring advice.

  - Content: Same as balanced, but with higher budgets and longer snippets
  - Usage: Complex troubleshooting, deep refactoring, cross-module analysis.

full:
  - Content: TREE + INDEX + full source files (no truncation)
  - Covers all text files without extension filtering
  - Respects .ignore file in root if present
  - Usage: For feeding complete source codes to the AI.

Recommendation:
  - Step 1: Use `fast` to onboard.
  - Step 2: Use `balanced` or `deep` to dig deeper.
EOF
        fi
    }

    _aicp_help_sub_init() {
        if [[ "$lang" == zh* ]]; then
            cat <<'EOF'
[--init 说明]

用途:
  一键生成"项目认知包"，用于 AI 快速建立对项目的整体理解。

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
        else
            cat <<'EOF'
[--init Preset Description]

Purpose:
  Generate a "Project Onboarding Package" for the AI to quickly build a holistic map of your codebase.

Default Behaviors (unless overridden):
  - Automatically enables full scan (-a)
  - Includes PROJECT TREE (source tree) and FILE INDEX
  - Mode is set to 'balanced'
  - Enables quality report (--quality-report)
  - Default Budgets:
      --max-files 120
      --max-total-chars 85000
      --max-file-chars 2200
  - Injects onboarding prompt instructions (unless custom --prompt is passed)

Combinations:
  aicp --init --ignore-docs
  aicp --init --changed
  aicp --init --output-format json
EOF
        fi
    }

    _aicp_help_sub_filter() {
        if [[ "$lang" == zh* ]]; then
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
        else
            cat <<'EOF'
[Filters Description]

Include Filters:
  --query <keyword>
  --query-regex <regex>
  Files matching any of these will be included.

Exclude Filters:
  --exclude <keyword>
  --exclude-regex <regex>
  Files matching any of these will be excluded.

Documentation Filter:
  --ignore-docs
  Filters out documentation files like doxygen/markdown/sphinx/wiki/manual/etc.

Example:
  aicp -a --query auth --query token --exclude-regex "dist|vendor"
EOF
        fi
    }

    _aicp_help_sub_changed() {
        if [[ "$lang" == zh* ]]; then
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
        else
            cat <<'EOF'
[Git Changes Description]

--changed
  Modified & untracked files relative to HEAD.

--changed-from <ref>
  Modified & untracked files relative to a branch/tag.
  Example: --changed-from main

--changed-commit-range <A..B>
  Changes between a commit range.
  Example: --changed-commit-range HEAD~5..HEAD
EOF
        fi
    }

    _aicp_help_sub_output() {
        if [[ "$lang" == zh* ]]; then
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
        else
            cat <<'EOF'
[Output & Budget Description]

Output Format:
  --output-format markdown|plain|json

Quality Report:
  --quality-report

Budget Overrides:
  --max-files <n>
  --max-total-chars <n>
  --max-file-chars <n>

Destination:
  Copies to clipboard by default. Control destination with --no-copy, --print, or --out <file>.
EOF
        fi
    }

    _aicp_help_sub_examples() {
        if [[ "$lang" == zh* ]]; then
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

10) 交互式 AI 协作
    aicp --exec -a
    aicp --exec --init
    aicp --exec --changed

11) 读取文件指定行范围
    aicp --read src/main.py:10-30 src/utils.py:1-50
    aicp --read config.yaml --print
EOF
        else
            cat <<'EOF'
[Examples Collection]

1) Quick project mapping
   aicp --init

2) Mapping & ignore documentation
   aicp --init --ignore-docs

3) Code change review only
   aicp --changed --prompt "Review changes, highlight risk matrix and fix plan"

4) Compare changes against main branch
   aicp --changed-from main --mode balanced

5) Commit range analysis
   aicp --changed-commit-range HEAD~8..HEAD --output-format plain --print

6) Focus on security keywords
   aicp -a --query-regex "token|secret|password|apikey" --exclude-regex "dist|vendor|node_modules"

7) Query match snippet context window
   aicp -a --query auth --snippet-around-query --snippet-context-lines 20

8) JSON format for tool consumption
   aicp -a --output-format json --quality-report --no-copy --print

9) Control context character size
   aicp -a --max-files 60 --max-total-chars 70000 --max-file-chars 1800

10) Interactive AI collaboration mode
    aicp --exec -a
    aicp --exec --init
    aicp --exec --changed

11) Read specific lines to clipboard
    aicp --read src/main.py:10-30 src/utils.py:1-50
    aicp --read config.yaml --print
EOF
        fi
    }

    _aicp_help_sub_exec() {
        if [[ "$lang" == zh* ]]; then
            cat <<'EOF'
[--exec 说明]

用途:
  交互式 AI 协作模式。生成上下文 + 注入能力声明，
  让 AI 可以通过 XML 标签请求读/写文件。

工作流程:
  1) 上下文生成 → 复制到剪贴板
  2) 用户粘贴到 AI 对话框
  3) AI 回复中包含 <aicp:read> / <aicp:write> 标签
  4) 用户将回复粘贴回终端，输入 ---EOF--- 结束
  5) aicp 自动解析执行：
      - <aicp:read>...</aicp:read> / <aicp:read ... />
        → cat -n 显示文件内容（带行号）
      - <aicp:write>...</aicp:write>
        → patch -p0/-p1 自动检测并应用 diff
  6) 读取结果自动累计到下一轮上下文
  7) 可反复迭代

AI 回复格式:

  读取文件:
  <aicp:read>src/foo.py:10-30</aicp:read>
  # 或单行: <aicp:read src/foo.py:10-30 />

  写入文件:
  <aicp:write>
  --- a/src/foo.py
  +++ b/src/foo.py
  @@ -10,6 +10,8 @@
   ...
  </aicp:write>

示例:
  aicp --exec -a                      # 全量 + 协作模式
  aicp --exec --init                  # 认知预设 + 协作模式
  aicp --exec --changed               # 改动审查 + 协作模式
EOF
        else
            cat <<'EOF'
[--exec Interactive Mode Description]

Purpose:
  Interactive AI collaboration. Packages context & appends tool capabilities,
  allowing the AI to read/write files via XML tags.

Workflow:
  1) Packages context -> copies to clipboard.
  2) Paste context to AI chat box.
  3) AI replies with <aicp:read> / <aicp:write> tags.
  4) Copy AI response and paste it back in terminal (type ---EOF--- to end).
  5) aicp automatically parses and executes instructions:
       - <aicp:read>...</aicp:read> / <aicp:read ... />
         -> Displays file content with line numbers (using cat -n).
       - <aicp:write>...</aicp:write>
         -> Detects and applies unified diffs automatically.
  6) Fetched read contents are automatically accumulated for the next round.
  7) Iterate as needed.

AI Response Tag Format:

  Read file:
  <aicp:read>src/foo.py:10-30</aicp:read>
  # Or inline: <aicp:read src/foo.py:10-30 />

  Modify file (patch diff):
  <aicp:write>
  --- a/src/foo.py
  +++ b/src/foo.py
  @@ -10,6 +10,8 @@
   ...
  </aicp:write>

Example:
  aicp --exec -a                      # Pack workspace + Interactive mode
  aicp --exec --init                  # Map onboarding + Interactive mode
  aicp --exec --changed               # Change review + Interactive mode
EOF
        fi
    }

    _aicp_help_fzf() {
        local choice
        if [[ "$lang" == zh* ]]; then
            choice=$(
                printf "%s\n"                     "general    速查表 · 全部参数一目了然"                     "mode       复制等级说明 (fast/balanced/deep/full)"                     "init       项目认知预设 (--init 详解)"                     "exec       交互式 AI 协作模式 (--exec 详解)"                     "filter     纳入/排除筛选参数差异"                     "changed    Git 改动筛选选项"                     "output     输出格式与预算控制"                     "read       文件行读取与剪贴板复制"                     "examples   完整组合示例"                     "all        展开全部帮助" |
                fzf --prompt="aicp help > "                     --height=14                     --border=sharp                     --header="选择主题 (ESC 退出)"                     | awk '{print $1}'
            )
        else
            choice=$(
                printf "%s\n"                     "general    Quick Reference Cheat Sheet"                     "mode       Context levels (fast/balanced/deep/full)"                     "init       Project onboarding preset (--init)"                     "exec       Interactive AI Collaboration (--exec)"                     "filter     Include/exclude filters"                     "changed    Git change targeting options"                     "output     Formats and budgets control"                     "read       File lines reader and clipboard"                     "examples   Usage examples collection"                     "all        Show all help contents" |
                fzf --prompt="aicp help > "                     --height=14                     --border=sharp                     --header="Select Topic (ESC to exit)"                     | awk '{print $1}'
            )
        fi
        [[ -n "$choice" ]] && _aicp_help "$choice"
    }

    _aicp_help_topic_menu() {
        local -a topics
        if [[ "$lang" == zh* ]]; then
            topics=(
                "general:速查表 · 全部参数一目了然"
                "mode:复制等级说明 (fast/balanced/deep/full)"
                "init:项目认知预设 (--init 详解)"
                "filter:纳入/排除筛选参数差异"
                "changed:Git 改动筛选选项"
                "output:输出格式与预算控制"
                "read:文件行读取与剪贴板复制"
                "exec:交互式 AI 协作模式 (--exec 详解)"
                "examples:完整组合示例"
                "all:展开全部帮助"
            )
        else
            topics=(
                "general:Quick Reference Cheat Sheet"
                "mode:Context levels (fast/balanced/deep/full)"
                "init:Project onboarding preset (--init)"
                "filter:Include/exclude filters"
                "changed:Git change targeting options"
                "output:Formats and budgets control"
                "read:File lines reader and clipboard"
                "exec:Interactive AI Collaboration (--exec)"
                "examples:Usage examples collection"
                "all:Show all help contents"
            )
        fi

        if [[ "$lang" == zh* ]]; then
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
            echo -e "${GREEN}aicp${RESET} 帮助主题"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        else
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
            echo -e "${GREEN}aicp${RESET} Help Topics"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        fi
        local i topic desc
        for i in {1..${#topics[@]}}; do
            topic="${topics[$i]%%:*}"
            desc="${topics[$i]#*:}"
            printf "  ${GREEN}%2d${RESET}) %-12s %s\n" "$i" "$topic" "$desc"
        done
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        if [[ "$lang" == zh* ]]; then
            echo -n -e "输入编号或主题名 (${YELLOW}q${RESET} 退出): "
        else
            echo -n -e "Enter number or topic name (${YELLOW}q${RESET} to quit): "
        fi
        local sel
        read sel
        [[ -z "$sel" || "$sel" == "q" ]] && return 0

        # 按编号匹配
        if [[ "$sel" =~ ^[0-9]+$ ]] && (( sel >= 1 && sel <= ${#topics[@]} )); then
            topic="${topics[$sel]%%:*}"
            _aicp_help "$topic"
        # 按主题名匹配
        elif [[ -n "$sel" ]]; then
            local matched=0 entry
            for entry in "${topics[@]}"; do
                local t="${entry%%:*}"
                if [[ "$t" == "$sel" ]]; then
                    _aicp_help "$t"
                    matched=1
                    break
                fi
            done
            if [[ $matched -eq 0 ]]; then
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}未知主题:${RESET} $sel"
                else
                    echo -e "${RED}Unknown topic:${RESET} $sel"
                fi
            fi
        fi
    }

    _aicp_help_sub_read() {
        if [[ "$lang" == zh* ]]; then
            cat <<'EOF'
[--read 说明]

用途:
  手动读取一个或多个文件的指定行范围，带行号复制到剪贴板。
  适合直接提取代码片段投喂给 AI，或快速查看文件特定部分。

语法:
  aicp --read <path>[:<start>-<end>] [...]

示例:
  aicp --read src/main.py:10-30
    复制 src/main.py 的第 10~30 行到剪贴板（带行号）

  aicp --read src/main.py:10-30 src/utils.py:1-50
    同时读取多个文件的行范围

  aicp --read src/main.py
    不指定行号时复制整个文件

  aicp --read src/main.py:10-30 --print
    读取并打印到终端

  aicp --read src/main.py:10-30 --out snippet.txt
    读取并写入文件

注意:
  - 行号范围必须是 "NN-NN" 格式，起始行 ≤ 结束行
  - --read 为独立模式，不与 -a/--changed/--exec 等其它模式混用
  - 可通过 --print、--out、--no-copy 控制输出行为
EOF
        else
            cat <<'EOF'
[--read Description]

Purpose:
  Read specific line ranges of one or more files, copy them with line numbers to the clipboard.
  Useful for feeding exact code snippets to AI or inspecting specific parts of files.

Syntax:
  aicp --read <path>[:<start>-<end>] [...]

Example:
  aicp --read src/main.py:10-30
    Copies lines 10-30 of src/main.py (with line numbers) to the clipboard.

  aicp --read src/main.py:10-30 src/utils.py:1-50
    Reads multiple file line ranges.

  aicp --read src/main.py
    Copies the entire file.

  aicp --read src/main.py:10-30 --print
    Reads and prints to stdout.

  aicp --read src/main.py:10-30 --out snippet.txt
    Reads and writes to a file.

Note:
  - Range format must be "NN-NN" where start_line <= end_line.
  - --read is a standalone mode and cannot be combined with -a/--changed/--exec etc.
  - Control output behaviors via --print, --out, and --no-copy.
EOF
        fi
    }

    _aicp_handle_read() {
        local output=""
        local target file_path line_range start_line end_line content
        local has_error=0

        for target in "${read_targets[@]}"; do
            # 解析 path:line1-line2 格式
            if [[ "$target" == *:* ]]; then
                file_path="${target%%:*}"
                line_range="${target#*:}"
                if [[ ! "$line_range" =~ ^[0-9]+-[0-9]+$ ]]; then
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${RED}[ERROR]${RESET} 无效的行范围格式: $line_range (期望: NN-NN，如 10-30)"
                    else
                        echo -e "${RED}[ERROR]${RESET} Invalid line range format: $line_range (expected: NN-NN, e.g., 10-30)"
                    fi
                    has_error=1
                    continue
                fi
                start_line="${line_range%-*}"
                end_line="${line_range#*-}"
                if (( start_line > end_line )); then
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${RED}[ERROR]${RESET} 起始行大于结束行: $start_line > $end_line"
                    else
                        echo -e "${RED}[ERROR]${RESET} Start line greater than end line: $start_line > $end_line"
                    fi
                    has_error=1
                    continue
                fi
            else
                file_path="$target"
                line_range=""
            fi

            # 文件存在性检查
            if [[ ! -f "$file_path" ]]; then
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[ERROR]${RESET} 文件不存在: $file_path"
                else
                    echo -e "${RED}[ERROR]${RESET} File does not exist: $file_path"
                fi
                has_error=1
                continue
            fi

            # 构建带行号的内容
            local header="### $target"
            output+="$header"$'
'

            if [[ -n "$line_range" ]]; then
                content=$(sed -n "${start_line},${end_line}p" "$file_path" 2>/dev/null)
                if [[ -z "$content" ]]; then
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${YELLOW}[WARN]${RESET} $target: 指定范围内无内容"
                    else
                        echo -e "${YELLOW}[WARN]${RESET} $target: No content in specified range"
                    fi
                    continue
                fi
                # awk 从 start_line 开始编号
                content=$(echo "$content" | awk -v s="$start_line" '{printf "%5d|%s\n", s+NR-1, $0}')
            else
                content=$(cat -n "$file_path" 2>/dev/null | awk '{printf "%5d|%s\n", $1, substr($0, index($0,$2))}')
            fi

            if [[ -z "$content" ]]; then
                if [[ "$lang" == zh* ]]; then
                    echo -e "${YELLOW}[WARN]${RESET} $target: 空文件或无内容"
                else
                    echo -e "${YELLOW}[WARN]${RESET} $target: Empty file or no content"
                fi
                continue
            fi

            output+="$content"$'

'
        done

        if [[ -z "$output" ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${YELLOW}[aicp]${RESET} 未读取到任何内容"
            else
                echo -e "${YELLOW}[aicp]${RESET} Read no content"
            fi
            return $has_error
        fi

        # 写入临时文件
        local tmp_file
        tmp_file=$(mktemp /tmp/aicp-read.XXXXXX.txt) || return 1
        echo -n "$output" > "$tmp_file"

        # 剪贴板复制
        if [[ $copy_mode -eq 1 ]]; then
            if command -v wl-copy >/dev/null 2>&1; then
                wl-copy < "$tmp_file" >/dev/null 2>&1
                if [[ "$lang" == zh* ]]; then
                    echo -e "${GREEN}[SUCCESS]${RESET} 已复制到剪贴板 (wl-copy)。"
                else
                    echo -e "${GREEN}[SUCCESS]${RESET} Copied to clipboard (wl-copy)."
                fi
            elif command -v xclip >/dev/null 2>&1; then
                xclip -selection clipboard < "$tmp_file" >/dev/null 2>&1
                if [[ "$lang" == zh* ]]; then
                    echo -e "${GREEN}[SUCCESS]${RESET} 已复制到剪贴板 (xclip)。"
                else
                    echo -e "${GREEN}[SUCCESS]${RESET} Copied to clipboard (xclip)."
                fi
            elif command -v pbcopy >/dev/null 2>&1; then
                pbcopy < "$tmp_file" >/dev/null 2>&1
                if [[ "$lang" == zh* ]]; then
                    echo -e "${GREEN}[SUCCESS]${RESET} 已复制到剪贴板 (pbcopy)。"
                else
                    echo -e "${GREEN}[SUCCESS]${RESET} Copied to clipboard (pbcopy)."
                fi
            else
                if [[ "$lang" == zh* ]]; then
                    echo -e "${YELLOW}[WARN]${RESET} 未检测到剪贴板命令(wl-copy/xclip/pbcopy)，跳过复制。"
                else
                    echo -e "${YELLOW}[WARN]${RESET} Clipboard command not found (wl-copy/xclip/pbcopy), skipped copying."
                fi
            fi
        fi

        # 输出到文件和打印
        if [[ -n "$out_file" ]]; then
            cp "$tmp_file" "$out_file"
            if [[ "$lang" == zh* ]]; then
                echo -e "${GREEN}[aicp]${RESET} 已写入文件: $out_file"
            else
                echo -e "${GREEN}[aicp]${RESET} Written to file: $out_file"
            fi
        fi
        [[ $print_mode -eq 1 ]] && cat "$tmp_file"

        rm -f "$tmp_file"
        return $has_error
    }
    _aicp_exec_loop() {
        local context_file="$1"
        local has_context=0
        [[ -n "$context_file" && -f "$context_file" ]] && has_context=1
        local round=1
        local accum_dir
        accum_dir=$(mktemp -d /tmp/aicp_exec.XXXXXX) || return 1
        local accum_file="$accum_dir/accumulated.txt"
        : > "$accum_file"

        local line

        exec 3</dev/tty

        while true; do
            echo
            echo -e "${BLUE}═══════════════════════════════════════════════${RESET}"
            if [[ "$lang" == zh* ]]; then
                echo -e "${BLUE}[aicp/exec]${RESET} 第 ${round} 轮 — 上下文已就绪"
                echo -e "${YELLOW}粘贴 AI 回复（粘贴完成后输入 ---EOF---）：${RESET}"
            else
                echo -e "${BLUE}[aicp/exec]${RESET} Round ${round} — Context ready"
                echo -e "${YELLOW}Paste AI response (type ---EOF--- when done):${RESET}"
            fi

            local ai_response=""
            while IFS= read -r line; do
                [[ "$line" == "---EOF---" ]] && break
                ai_response+="$line"$'
'
            done <&3
            if [[ -z "$ai_response" ]]; then
                if [[ "$lang" == zh* ]]; then
                    echo -e "${YELLOW}[aicp/exec]${RESET} 空输入，退出"
                else
                    echo -e "${YELLOW}[aicp/exec]${RESET} Empty input, exiting"
                fi
                break
            fi

            local in_read=0 in_write=0
            local -a read_targets=()
            local write_buf=""
            local -a write_diffs=()

            while IFS= read -r line; do
                # Self-closing format: <aicp:read path/to/file />
                if [[ "$line" =~ '<aicp:read ' ]]; then
                    local read_path="${line#*<aicp:read }"
                    read_path="${read_path%% />*}"
                    read_path="${read_path#"${read_path%%[![:space:]]*}"}"
                    read_path="${read_path%${read_path##*[![:space:]]}}"
                    [[ -n "$read_path" ]] && read_targets+=("$read_path")
                    continue
                # Tag pair (single line): <aicp:read>path/to/file</aicp:read>
                elif [[ "$line" =~ '<aicp:read>' && "$line" =~ '</aicp:read>' ]]; then
                    local read_path="${line#*<aicp:read>}"
                    read_path="${read_path%</aicp:read>*}"
                    read_path="${read_path#"${read_path%%[![:space:]]*}"}"
                    read_path="${read_path%${read_path##*[![:space:]]}}"
                    [[ -n "$read_path" ]] && read_targets+=("$read_path"); continue
                # Tag pair (multi-line): <aicp:read> / path / </aicp:read>
                elif [[ "$line" == '<aicp:read>' ]]; then
                    in_read=1; continue
                elif [[ "$line" == '</aicp:read>' && $in_read -eq 1 ]]; then
                    in_read=0; continue
                # Tolerant format: missing < prefix (e.g. "aicp:read>path")
                elif [[ "$line" =~ 'aicp:read ' && "$line" =~ '/>' ]]; then
                    local read_path="${line#*aicp:read }"
                    read_path="${read_path%% />*}"
                    read_path="${read_path#"${read_path%%[![:space:]]*}"}"
                    read_path="${read_path%${read_path##*[![:space:]]}}"
                    [[ -n "$read_path" ]] && read_targets+=("$read_path")
                    continue
                elif [[ "$line" =~ 'aicp:read>' && "$line" =~ '</aicp:read>' ]]; then
                    local read_path="${line#*aicp:read>}"
                    read_path="${read_path%</aicp:read>*}"
                    read_path="${read_path#"${read_path%%[![:space:]]*}"}"
                    read_path="${read_path%${read_path##*[![:space:]]}}"
                    [[ -n "$read_path" ]] && read_targets+=("$read_path"); continue
                # Tolerant format: aicp:read + path + </aicp:read> (no brackets at all)
                elif [[ "$line" =~ 'aicp:read' && "$line" =~ '</aicp:read>' ]]; then
                    local read_path="${line#*aicp:read}"
                    read_path="${read_path%</aicp:read>*}"
                    read_path="${read_path#"${read_path%%[![:space:]]*}"}"
                    read_path="${read_path%${read_path##*[![:space:]]}}"
                    [[ -n "$read_path" ]] && read_targets+=("$read_path"); continue
                elif [[ "$line" == 'aicp:read>' ]]; then
                    in_read=1; continue
                elif [[ "$line" == '<aicp:write>' ]]; then
                    in_write=1; in_read=0; write_buf=""; continue
                elif [[ "$line" == '</aicp:write>' && $in_write -eq 1 ]]; then
                    in_write=0
                    [[ -n "$write_buf" ]] && write_diffs+=("$write_buf")
                    continue
                fi

                if [[ $in_read -eq 1 ]]; then
                    local trimmed="${line#"${line%%[![:space:]]*}"}"
                    [[ -n "$trimmed" ]] && read_targets+=("$trimmed")
                elif [[ $in_write -eq 1 ]]; then
                    write_buf+="$line"$'
'
                fi
            done <<< "$ai_response"

            local has_read=0 has_write=0
            local read_output=""

            if [[ ${#read_targets[@]} -gt 0 ]]; then
                has_read=1
                echo
                if [[ "$lang" == zh* ]]; then
                    echo -e "${YELLOW}→ 读取请求:${RESET}"
                else
                    echo -e "${YELLOW}→ Read Request:${RESET}"
                fi
                local target
                for target in "${read_targets[@]}"; do
                    [[ -z "$target" ]] && continue
                    local file_path="${target%%:*}"
                    local line_range=""
                    [[ "$target" == *:* ]] && line_range="${target#*:}"
                    line_range="${line_range/-/,}"

                    if [[ ! -f "$file_path" ]]; then
                        if [[ "$lang" == zh* ]]; then
                            echo -e "  ${RED}文件不存在: $file_path${RESET}"
                        else
                            echo -e "  ${RED}File does not exist: $file_path${RESET}"
                        fi
                        continue
                    fi

                    echo -e "  ${GREEN}$target${RESET}:"
                    local content
                    if [[ -n "$line_range" ]]; then
                        local start_line="${line_range%,*}"
                        content=$(sed -n "${line_range}p" "$file_path" 2>/dev/null | nl -ba -v "$start_line")
                    else
                        content=$(cat -n "$file_path" 2>/dev/null)
                    fi
                    if [[ -n "$content" ]]; then
                        echo "$content"
                        read_output+='<aicp:fetch name="'"$target"'"'$'
'
                        read_output+="$content"$'
'
                        read_output+='</aicp:fetch>'$'

'
                    else
                        if [[ "$lang" == zh* ]]; then
                            echo -e "  ${YELLOW}(空文件)${RESET}"
                        else
                            echo -e "  ${YELLOW}(Empty file)${RESET}"
                        fi
                    fi
                done
            fi

            if [[ ${#write_diffs[@]} -gt 0 ]]; then
                has_write=1
                local wdiff
                for wdiff in "${write_diffs[@]}"; do
                    local diff_file="$accum_dir/diff.patch"
                    echo "$wdiff" > "$diff_file"
                    echo
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${YELLOW}→ 写入请求 (diff):${RESET}"
                    else
                        echo -e "${YELLOW}→ Write Request (diff):${RESET}"
                    fi
                    echo "$wdiff"

                    local strip_level=""
                    (cd "$ZFL_HOME" && patch -p0 -t -f --dry-run -i "$diff_file" 2>/dev/null) && strip_level=0
                    [[ -z "$strip_level" ]] && (cd "$ZFL_HOME" && patch -p1 -t -f --dry-run -i "$diff_file" 2>/dev/null) && strip_level=1
                    if [[ -z "$strip_level" ]]; then
                        if [[ "$lang" == zh* ]]; then
                            echo -e "${RED}  ✗ 无法干净应用${RESET}"
                        else
                            echo -e "${RED}  ✗ Cannot apply cleanly${RESET}"
                        fi
                        continue
                    fi

                    if [[ "$lang" == zh* ]]; then
                        echo -e "${GREEN}  ✓ 可以干净应用${RESET}"
                        echo -n -e "应用此 diff？${GREEN}[y/N]${RESET} "
                    else
                        echo -e "${GREEN}  ✓ Can apply cleanly${RESET}"
                        echo -n -e "Apply this diff? ${GREEN}[y/N]${RESET} "
                    fi
                    local confirm
                    read confirm <&3
                    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
                        if [[ "$lang" == zh* ]]; then
                            echo -e "  ${YELLOW}已跳过${RESET}"
                        else
                            echo -e "  ${YELLOW}Skipped${RESET}"
                        fi
                        continue
                    fi

                    if (cd "$ZFL_HOME" && patch -p"$strip_level" -t -f -i "$diff_file"); then
                        if [[ "$lang" == zh* ]]; then
                            echo -e "${GREEN}  ✓ 已应用${RESET}"
                        else
                            echo -e "${GREEN}  ✓ Applied${RESET}"
                        fi
                        if git rev-parse --git-dir >/dev/null 2>&1; then
                            if [[ "$lang" == zh* ]]; then
                                echo -e "${BLUE}  改动摘要:${RESET}"
                            else
                                echo -e "${BLUE}  Change summary:${RESET}"
                            fi
                            git diff --stat
                        fi
                    else
                        if [[ "$lang" == zh* ]]; then
                            echo -e "${RED}  ✗ 应用失败${RESET}"
                        else
                            echo -e "${RED}  ✗ Apply failed${RESET}"
                        fi
                    fi
                done
            fi

            if [[ -n "$read_output" ]]; then
                echo "$read_output" >> "$accum_file"
                if [[ "$lang" == zh* ]]; then
                    echo -e "${GREEN}[aicp/exec]${RESET} 读取内容已累计"
                else
                    echo -e "${GREEN}[aicp/exec]${RESET} Read content accumulated"
                fi
            fi

            if [[ $has_read -eq 0 && $has_write -eq 0 ]]; then
                if [[ "$lang" == zh* ]]; then
                    echo -e "${YELLOW}[aicp/exec]${RESET} 未检测到 <aicp:read> 或 <aicp:write> 标签"
                else
                    echo -e "${YELLOW}[aicp/exec]${RESET} No <aicp:read> or <aicp:write> tags detected"
                fi
                break
            fi

            echo
            if [[ "$lang" == zh* ]]; then
                echo -n -e "继续下一轮？${GREEN}[Y/n]${RESET} "
            else
                echo -n -e "Continue to next round? ${GREEN}[Y/n]${RESET} "
            fi
            local next
            read next <&3
            [[ "$next" == "n" || "$next" == "N" ]] && break

            round=$((round + 1))

            if [[ $has_context -eq 1 ]]; then
                if [[ "$lang" == zh* ]]; then
                    echo -e "${BLUE}[aicp/exec]${RESET} 重新生成上下文..."
                else
                    echo -e "${BLUE}[aicp/exec]${RESET} Regenerating context..."
                fi

                local new_tmp
                new_tmp=$(mktemp /tmp/aicp.XXXXXX.txt) || break
                if ! "${cmd[@]}" > "$new_tmp"; then
                    rm -f "$new_tmp"
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${RED}[ERROR]${RESET} 上下文生成失败"
                    else
                        echo -e "${RED}[ERROR]${RESET} Context generation failed"
                    fi
                    break
                fi

                if [[ -s "$accum_file" ]]; then
                    {
                        echo ""
                        echo "---"
                        if [[ "$lang" == zh* ]]; then
                            echo "## 上一轮 AI 读取请求的结果"
                        else
                            echo "## Results of the previous AI read requests"
                        fi
                        cat "$accum_file"
                    } >> "$new_tmp"
                fi

                local copied=0
                if command -v wl-copy >/dev/null 2>&1; then
                    wl-copy < "$new_tmp" >/dev/null 2>&1 3<&-; copied=1
                elif command -v xclip >/dev/null 2>&1; then
                    xclip -selection clipboard < "$new_tmp" >/dev/null 2>&1 3<&-; copied=1
                fi
                if [[ $copied -eq 1 ]]; then
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${GREEN}[aicp/exec]${RESET} 已复制到剪贴板 (第 ${round} 轮)"
                    else
                        echo -e "${GREEN}[aicp/exec]${RESET} Copied to clipboard (Round ${round})"
                    fi
                fi
                rm -f "$new_tmp"
            elif [[ -s "$accum_file" ]]; then
                if command -v wl-copy >/dev/null 2>&1; then
                    wl-copy < "$accum_file" >/dev/null 2>&1 3<&-
                elif command -v xclip >/dev/null 2>&1; then
                    xclip -selection clipboard < "$accum_file" >/dev/null 2>&1 3<&-
                fi
                if [[ "$lang" == zh* ]]; then
                    echo -e "${GREEN}[aicp/exec]${RESET} 读取记录已复制到剪贴板"
                else
                    echo -e "${GREEN}[aicp/exec]${RESET} Read logs copied to clipboard"
                fi
            fi
        done

        exec 3<&-
        rm -rf "$accum_dir"
    }

    _aicp_missing_arg() {
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} $1 缺少参数"
        else
            echo -e "${RED}[ERROR]${RESET} $1 missing argument"
        fi
    }

    local mode="balanced"
    local mode_user_set=0
    local all_mode=0
    local copy_mode=1
    local print_mode=0
    local changed_mode=0
    local init_mode=0
    local exec_mode=0

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

    local read_mode=0
    local -a read_targets=()

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
                [[ -z "$2" ]] && { _aicp_missing_arg "--mode"; return 1; }
                mode="$2"; mode_user_set=1; shift 2 ;;
            --init)
                init_mode=1; shift ;;
            --exec)
                exec_mode=1; shift ;;
            --query)
                [[ -z "$2" ]] && { _aicp_missing_arg "--query"; return 1; }
                queries+=("$2"); shift 2 ;;
            --query-regex)
                [[ -z "$2" ]] && { _aicp_missing_arg "--query-regex"; return 1; }
                query_regexes+=("$2"); shift 2 ;;
            --exclude)
                [[ -z "$2" ]] && { _aicp_missing_arg "--exclude"; return 1; }
                excludes+=("$2"); shift 2 ;;
            --exclude-regex)
                [[ -z "$2" ]] && { _aicp_missing_arg "--exclude-regex"; return 1; }
                exclude_regexes+=("$2"); shift 2 ;;
            --changed)
                changed_mode=1; shift ;;
            --changed-from)
                [[ -z "$2" ]] && { _aicp_missing_arg "--changed-from"; return 1; }
                changed_from="$2"; shift 2 ;;
            --changed-commit-range)
                [[ -z "$2" ]] && { _aicp_missing_arg "--changed-commit-range"; return 1; }
                changed_commit_range="$2"; shift 2 ;;
            --snippet-around-query)
                snippet_around_query=1; shift ;;
            --snippet-context-lines)
                [[ -z "$2" ]] && { _aicp_missing_arg "--snippet-context-lines"; return 1; }
                snippet_context_lines="$2"; shift 2 ;;
            --output-format)
                [[ -z "$2" ]] && { _aicp_missing_arg "--output-format"; return 1; }
                output_format="$2"; shift 2 ;;
            --quality-report)
                quality_report=1; shift ;;
            --ignore-docs)
                ignore_docs=1; shift ;;
            --max-files)
                [[ -z "$2" ]] && { _aicp_missing_arg "--max-files"; return 1; }
                max_files="$2"; shift 2 ;;
            --max-total-chars)
                [[ -z "$2" ]] && { _aicp_missing_arg "--max-total-chars"; return 1; }
                max_total_chars="$2"; shift 2 ;;
            --max-file-chars)
                [[ -z "$2" ]] && { _aicp_missing_arg "--max-file-chars"; return 1; }
                max_file_chars="$2"; shift 2 ;;
            --prompt)
                [[ -z "$2" ]] && { _aicp_missing_arg "--prompt"; return 1; }
                prompt_text="$2"; prompt_user_set=1; shift 2 ;;
            --prompt-file)
                [[ -z "$2" ]] && { _aicp_missing_arg "--prompt-file"; return 1; }
                prompt_file="$2"; shift 2 ;;
            --print)
                print_mode=1; shift ;;
            --out)
                [[ -z "$2" ]] && { _aicp_missing_arg "--out"; return 1; }
                out_file="$2"; shift 2 ;;
            --no-copy)
                copy_mode=0; shift ;;
            --read)
                read_mode=1
                shift
                while [[ $# -gt 0 && "$1" != -* ]]; do
                    read_targets+=("$1")
                    shift
                done
                ;;
            -h|--help)
                if [[ -n "$2" && "$2" != -* ]]; then
                    _aicp_help "$2"
                elif [[ -t 1 ]] && command -v fzf >/dev/null 2>&1; then
                    _aicp_help_fzf
                elif [[ -t 1 ]]; then
                    _aicp_help_topic_menu
                else
                    _aicp_help "general"
                fi
                return 0 ;;
            *)
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[ERROR]${RESET} 未知参数: $arg"
                    echo "使用 aicp -h 查看帮助"
                else
                    echo -e "${RED}[ERROR]${RESET} Unknown option: $arg"
                    echo "Try 'aicp -h' for help"
                fi
                return 1 ;;
        esac
    done

    # init preset for project onboarding
    if [[ $init_mode -eq 1 ]]; then
        [[ $mode_user_set -eq 0 ]] && mode="balanced"
        [[ $all_mode -eq 0 && ${#targets[@]} -eq 0 ]] && all_mode=1
        [[ $quality_report -eq 0 ]] && quality_report=1
        [[ -z "$max_files" ]] && max_files="120"
        [[ -z "$max_total_chars" ]] && max_total_chars="85000"
        [[ -z "$max_file_chars" ]] && max_file_chars="2200"
        if [[ $prompt_user_set -eq 0 && -z "$prompt_file" ]]; then
            if [[ "$lang" == zh* ]]; then
                prompt_text="请先建立该项目的认知地图：1) 分层与职责 2) 启动链路与调用路径 3) 关键模块关系 4) 高风险改动点与建议入口。"
            else
                prompt_text="Please establish the cognitive map of this project first: 1) Architecture layers & responsibilities 2) Startup path & calling sequence 3) Key module relationships 4) High-risk change points & recommendations."
            fi
        fi
    fi

    if [[ "$mode" != "fast" && "$mode" != "balanced" && "$mode" != "deep" && "$mode" != "full" ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} --mode 仅支持 fast / balanced / deep / full"
        else
            echo -e "${RED}[ERROR]${RESET} --mode only supports fast / balanced / deep / full"
        fi
        return 1
    fi
    if [[ "$output_format" != "markdown" && "$output_format" != "plain" && "$output_format" != "json" ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} --output-format 仅支持 markdown/plain/json"
        else
            echo -e "${RED}[ERROR]${RESET} --output-format only supports markdown/plain/json"
        fi
        return 1
    fi

    local n
    for n in "$snippet_context_lines" "$max_files" "$max_total_chars" "$max_file_chars"; do
        [[ -z "$n" ]] && continue
        if [[ ! "$n" =~ ^[0-9]+$ ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[ERROR]${RESET} 数值参数必须为正整数"
            else
                echo -e "${RED}[ERROR]${RESET} Numeric arguments must be positive integers"
            fi
            return 1
        fi
    done

    if [[ -n "$prompt_file" ]]; then
        if [[ ! -f "$prompt_file" || ! -r "$prompt_file" ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[ERROR]${RESET} prompt 文件不存在或不可读: $prompt_file"
            else
                echo -e "${RED}[ERROR]${RESET} prompt file does not exist or is not readable: $prompt_file"
            fi
            return 1
        fi
        prompt_text="$(cat "$prompt_file")"
    fi

    # exec mode capability injection
    if [[ $exec_mode -eq 1 ]]; then
        local exec_prompt
        if [[ "$lang" == zh* ]]; then
            exec_prompt=$(
                cat <<'EOP'

## 系统能力：文件读写

可以通过以下 XML 标签请求读写文件，助手将代为执行。

### 读取文件（优先使用）

```xml
<aicp:read>src/foo.py</aicp:read>
<aicp:read>src/foo.py:10-30</aicp:read>
```

或单行自闭合格式：

```xml
<aicp:read src/foo.py:10-30 />
```

读取策略：
1. 先利用 FILE INDEX 锁定目标文件
2. 用 `<aicp:read>` 精确请求关键函数或模块的行号范围
3. 读取返回的文件内容带行号，可直接用于写入请求的 `@@` 行号

### 修改文件

```xml
<aicp:write>
--- a/src/foo.py
+++ b/src/foo.py
@@ -10,6 +10,8 @@
 ...
 </aicp:write>
```

写入注意：
- 路径使用相对项目根目录的路径
- `@@` 行号必须来自上一轮读取结果
- 写入前会显示 diff 并等待用户确认

示例：

```xml
<aicp:read>src/main.py:20-50</aicp:read>
<aicp:read>src/utils.py</aicp:read>

<aicp:write>
--- a/src/main.py
+++ b/src/main.py
@@ -30,6 +30,8 @@
  ...
 </aicp:write>
```

回复格式规则：
1. 工具调用场景：若回复中包含任何 <aicp:read> 或 <aicp:write> 标签，则必须保持绝对静默——仅输出 XML 标签，不得附带任何解释、分析、过渡句或问候语。回复末尾单独一行添加 `---EOF---` 作为结束标记。读取返回的行号为文件实际行号，可直接用于写入补丁的 @@ 引用。
2. 纯对话场景：若回复不含任何工具标签，正常输出文本，绝对不要在末尾添加 `---EOF---` 标记。
EOP
            )
        else:
            exec_prompt=$(
                cat <<'EOP'

## System Capability: File Read/Write

You can read/write files through the following XML tags, which the helper will execute on your behalf.

### Read File (Preferred)

```xml
<aicp:read>src/foo.py</aicp:read>
<aicp:read>src/foo.py:10-30</aicp:read>
```

Or inline self-closing format:

```xml
<aicp:read src/foo.py:10-30 />
```

Reading Policy:
1. Locate target files using the FILE INDEX.
2. Use `<aicp:read>` to precisely fetch key function/module line ranges.
3. The returned lines contain line numbers which can be directly referenced in patch diffs.

### Modify File

```xml
<aicp:write>
--- a/src/foo.py
+++ b/src/foo.py
@@ -10,6 +10,8 @@
 ...
 </aicp:write>
```

Important Rules for Writing:
- Use relative paths from the project root.
- The `@@` line numbers must match those returned in previous read results.
- Diffs will be shown to the user for confirmation before applying.

Example:

```xml
<aicp:read>src/main.py:20-50</aicp:read>
<aicp:read>src/utils.py</aicp:read>

<aicp:write>
--- a/src/main.py
+++ b/src/main.py
@@ -30,6 +30,8 @@
  ...
 </aicp:write>
```

Response Format Rules:
1. Tool Call Scenario: If your response contains any `<aicp:read>` or `<aicp:write>` tags, you MUST remain absolutely silent—output ONLY the XML tags, without any explanation, transition, or greetings. Append `---EOF---` on a separate line at the end of your response.
2. Conversational Scenario: If your response does not contain any tool tags, output normal text and do NOT append `---EOF---`.
EOP
            )
        fi
        if [[ -n "$prompt_text" ]]; then
            prompt_text="$prompt_text$exec_prompt"
        else
            prompt_text="$exec_prompt"
        fi
    fi

    # --exec no context mode: interactive loop directly
    if [[ $exec_mode -eq 1 && $all_mode -eq 0 && $changed_mode -eq 0 &&
          -z "$changed_from" && -z "$changed_commit_range" &&
          ${#targets[@]} -eq 0 ]]; then
        echo
        _aicp_exec_loop ""
        return 0
    fi

    # --read mode: read files to clipboard directly
    if [[ $read_mode -eq 1 ]]; then
        if [[ ${#read_targets[@]} -eq 0 ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[ERROR]${RESET} --read 需要至少一个路径参数，格式: <path>[:<start>-<end>]"
            else
                echo -e "${RED}[ERROR]${RESET} --read requires at least one path argument, format: <path>[:<start>-<end>]"
            fi
            return 1
        fi
        _aicp_handle_read
        return $?
    fi

    if [[ $all_mode -eq 0 && ${#targets[@]} -eq 0 ]]; then
        if [[ $exec_mode -eq 0 ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${YELLOW}[aicp]${RESET} 未指定目标，默认使用 -a 扫描当前目录"
            else
                echo -e "${YELLOW}[aicp]${RESET} No target specified, default to scanning current directory with -a"
            fi
        fi
        all_mode=1
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 未找到 python3，无法生成上下文。"
        else
            echo -e "${RED}[ERROR]${RESET} python3 not found, cannot generate context."
        fi
        return 1
    fi

    local py_script="$ZFL_HOME/python/aicp_context.py"
    if [[ ! -f "$py_script" ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 缺少脚本: $py_script"
        else
            echo -e "${RED}[ERROR]${RESET} Missing script: $py_script"
        fi
        return 1
    fi

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

    if [[ "$lang" == zh* ]]; then
        echo -e "${BLUE}[aicp]${RESET} 生成上下文中... mode=${mode}, init=${init_mode}, format=${output_format}, changed=${changed_effective}, changed_from=${changed_from:-none}, commit_range=${changed_commit_range:-none}, query_count=${#queries[@]}, regex_count=${#query_regexes[@]}, exclude_count=${#excludes[@]}, exclude_regex_count=${#exclude_regexes[@]}, ignore_docs=${ignore_docs}, around_query=${snippet_around_query}, quality=${quality_report}"
    else
        echo -e "${BLUE}[aicp]${RESET} Generating context... mode=${mode}, init=${init_mode}, format=${output_format}, changed=${changed_effective}, changed_from=${changed_from:-none}, commit_range=${changed_commit_range:-none}, query_count=${#queries[@]}, regex_count=${#query_regexes[@]}, exclude_count=${#excludes[@]}, exclude_regex_count=${#exclude_regexes[@]}, ignore_docs=${ignore_docs}, around_query=${snippet_around_query}, quality=${quality_report}"
    fi

    if ! "${cmd[@]}" > "$tmp_file"; then
        rm -f "$tmp_file"
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 上下文生成失败。"
        else
            echo -e "${RED}[ERROR]${RESET} Context generation failed."
        fi
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
            wl-copy < "$tmp_file" >/dev/null 2>&1
            if [[ "$lang" == zh* ]]; then
                echo -e "${GREEN}[SUCCESS]${RESET} 已复制到剪贴板 (wl-copy)。"
            else
                echo -e "${GREEN}[SUCCESS]${RESET} Copied to clipboard (wl-copy)."
            fi
        elif command -v xclip >/dev/null 2>&1; then
            xclip -selection clipboard < "$tmp_file" >/dev/null 2>&1
            if [[ "$lang" == zh* ]]; then
                echo -e "${GREEN}[SUCCESS]${RESET} 已复制到剪贴板 (xclip)。"
            else
                echo -e "${GREEN}[SUCCESS]${RESET} Copied to clipboard (xclip)."
            fi
        elif command -v pbcopy >/dev/null 2>&1; then
            pbcopy < "$tmp_file" >/dev/null 2>&1
            if [[ "$lang" == zh* ]]; then
                echo -e "${GREEN}[SUCCESS]${RESET} 已复制到剪贴板 (pbcopy)。"
            else
                echo -e "${GREEN}[SUCCESS]${RESET} Copied to clipboard (pbcopy)."
            fi
        else
            if [[ "$lang" == zh* ]]; then
                echo -e "${YELLOW}[WARN]${RESET} 未检测到剪贴板命令(wl-copy/xclip/pbcopy)，跳过复制。"
            else
                echo -e "${YELLOW}[WARN]${RESET} Clipboard command not found (wl-copy/xclip/pbcopy), skipped copying."
            fi
        fi
    fi

    if [[ -n "$out_file" ]]; then
        cp "$tmp_file" "$out_file"
        if [[ "$lang" == zh* ]]; then
            echo -e "${GREEN}[aicp]${RESET} 已写入文件: $out_file"
        else
            echo -e "${GREEN}[aicp]${RESET} Written to file: $out_file"
        fi
    fi
    [[ $print_mode -eq 1 ]] && cat "$tmp_file"

    if [[ "$lang" == zh* ]]; then
        echo -e "${BLUE}[aicp]${RESET} 完成，预估 token 数: ${token_count}"
    else
        echo -e "${BLUE}[aicp]${RESET} Finished, estimated token count: ${token_count}"
    fi

    if [[ $exec_mode -eq 1 ]]; then
        echo
        _aicp_exec_loop "$tmp_file"
    fi

    rm -f "$tmp_file"
}

# aicp tab completions
_aicp() {
    local -a modes output_formats help_topics
    modes=(fast balanced deep full)
    output_formats=(markdown plain json)
    help_topics=(general mode init filter changed output examples exec read all)
    local lang=${ZFL_LANG:-${LANG%%.*}}

    if [[ "$lang" == zh* ]]; then
        _arguments -s -S             '(-a --all)'{-a,--all}'[全量扫描当前目录]'             '*-c[手动指定目标文件/目录]:file:_files'             '*--choose[手动指定目标文件/目录]:file:_files'             '--mode[复制等级]:mode:('"${modes[*]}"')'             '--init[项目认知预设]'             '--exec[交互式 AI 协作模式]'             '*--query[关键词纳入]:keyword:'             '*--query-regex[正则纳入]:regex:'             '*--exclude[关键词排除]:keyword:'             '*--exclude-regex[正则排除]:regex:'             '--changed[相对 HEAD 改动+未跟踪]'             '--changed-from[相对某分支/标签对比]:ref:'             '--changed-commit-range[提交区间对比]:range:'             '--snippet-around-query[命中点邻域模式]'             '--snippet-context-lines[邻域扩展行数]:lines:'             '--output-format[格式]:format:('"${output_formats[*]}"')'             '--quality-report[附质量报告]'             '--max-files[文件总数上限]:limit:'             '--max-total-chars[总字符数上限]:limit:'             '--max-file-chars[单文件字符上限]:limit:'             '--ignore-docs[过滤文档类文件]'             '--prompt[自定义提示词]:text:'             '--prompt-file[从文件读取提示词]:file:_files'             '--print[打印到终端]'             '--out[写入文件]:file:_files'             '--no-copy[跳过剪贴板复制]'             '*--read[读取文件指定行到剪贴板]:file:_files'             '(-h --help)'{-h,--help}'[查看帮助]:topic:('"${help_topics[*]}"')'
    else
        _arguments -s -S             '(-a --all)'{-a,--all}'[Scan all files in current directory]'             '*-c[Specify target files/directories manually]:file:_files'             '*--choose[Specify target files/directories manually]:file:_files'             '--mode[Context mode level]:mode:('"${modes[*]}"')'             '--init[Initialize project context preset]'             '--exec[Interactive AI collaboration mode]'             '*--query[Query match keyword]:keyword:'             '*--query-regex[Query match regex]:regex:'             '*--exclude[Query exclude keyword]:keyword:'             '*--exclude-regex[Query exclude regex]:regex:'             '--changed[Relative to HEAD changes and untracked]'             '--changed-from[Compare changes relative to branch/tag]:ref:'             '--changed-commit-range[Compare changes in commit range]:range:'             '--snippet-around-query[Query match window snippet mode]'             '--snippet-context-lines[Lines around query match]:lines:'             '--output-format[Format]:format:('"${output_formats[*]}"')'             '--quality-report[Append code quality report]'             '--max-files[Maximum files limit]:limit:'             '--max-total-chars[Maximum total character limit]:limit:'             '--max-file-chars[Maximum per-file character limit]:limit:'             '--ignore-docs[Filter out documentation files]'             '--prompt[Custom instruction prompt]:text:'             '--prompt-file[Load prompt from file]:file:_files'             '--print[Print output directly to stdout]'             '--out[Write output to file]:file:_files'             '--no-copy[Skip clipboard copying]'             '*--read[Read specific lines to clipboard]:file:_files'             '(-h --help)'{-h,--help}'[Check help topics]:topic:('"${help_topics[*]}"')'
    fi
}

if whence compdef >/dev/null; then
    compdef _aicp aicp
fi
