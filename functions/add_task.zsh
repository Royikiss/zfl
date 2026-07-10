#? 名称: add_task
#? 描述: 管理后台非阻塞启动自动执行任务列表 (白名单管理)
#? 作者: Royi
#? 版本: 1.0.0
#? 依赖: 
#? 用法: add_task [选项] <命令> [参数...]
#? 示例: add_task check_update

_add_task_help() {
    cat <<'EOF'
add_task - 管理启动自动执行任务列表

用法:
  add_task [选项] <命令> [参数...]

示例:
  add_task check_update --force
  add_task echo "hello world"
  add_task --remove echo "hello world"

选项:
  -l, --list               列出当前已配置的启动任务
  -r, --remove <命令...>   删除一条已配置任务（按规范化命令匹配）
  -h, --help               显示帮助

说明:
  - 任务文件: $ZFL_HOME/core/startup_task_commands.zsh
  - add_task 会将命令规范化后写入（shell 转义格式），并避免重复添加。
  - 启动执行器会忽略空行与 # 注释行。
EOF
}

_add_task_task_file() {
    echo "${ZFL_HOME:-$HOME/.config/zsh}/core/startup_task_commands.zsh"
}

_add_task_normalize_line() {
    local line=$1
    local trimmed
    local -a parts

    trimmed="${line#${line%%[![:space:]]*}}"
    trimmed="${trimmed%${trimmed##*[![:space:]]}}"

    [[ -z "$trimmed" ]] && return 1
    [[ "$trimmed" == \#* ]] && return 1

    parts=(${(Q)${(z)trimmed}})

    # 兼容历史脏数据：若被解析成单 token 且含空格，尝试退回 (zQ) 再拆一次
    if (( ${#parts[@]} == 1 )) && [[ "$parts[1]" == *" "* ]]; then
        local -a fallback_parts
        fallback_parts=("${(zQ)trimmed}")
        if (( ${#fallback_parts[@]} > 1 )); then
            parts=("${fallback_parts[@]}")
        fi
    fi

    (( ${#parts[@]} > 0 )) || return 1

    # 统一规范为 shell-escaped 形式，便于 startup_tasks 直接解析执行
    print -r -- "${(j: :)${(@q)parts}}"
}

_add_task_ensure_file() {
    local task_file=$1
    mkdir -p "${task_file:h}"

    if [[ ! -f "$task_file" ]]; then
        cat > "$task_file" <<'EOF'
# 启动任务命令列表（每行一个命令）
# - 支持函数、别名、系统命令
# - 支持带参数与引号（按 shell 命令行规则解析）
# - 空行与 # 开头行会被忽略
EOF
    fi
}

_add_task_list() {
    load_color YELLOW RESET
    local task_file=$1

    if [[ ! -f "$task_file" ]]; then
        echo -e "${YELLOW}[add_task] 任务文件不存在:${RESET} $task_file"
        return 0
    fi

    local line normalized idx=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        normalized=$(_add_task_normalize_line "$line") || continue
        ((idx++))
        echo "[$idx] $normalized"
    done < "$task_file"

    if (( idx == 0 )); then
        echo -e "${YELLOW}[add_task] 当前没有有效启动任务${RESET}"
    fi
}

_add_task_remove() {
    load_color GREEN YELLOW RED RESET
    local task_file=$1
    shift

    if (( $# == 0 )); then
        echo -e "${RED}[add_task] --remove 需要后续命令参数${RESET}"
        return 2
    fi

    if [[ ! -f "$task_file" ]]; then
        echo -e "${YELLOW}[add_task] 任务文件不存在:${RESET} $task_file"
        return 1
    fi

    local -a cmd_parts
    cmd_parts=("$@")
    local target="${(j: :)${(@q)cmd_parts}}"

    local tmp_file="${task_file}.tmp.$$"
    local line normalized removed=0

    while IFS= read -r line || [[ -n "$line" ]]; do
        normalized=$(_add_task_normalize_line "$line") || {
            print -r -- "$line" >> "$tmp_file"
            continue
        }

        if (( removed == 0 )) && [[ "$normalized" == "$target" ]]; then
            removed=1
            continue
        fi

        print -r -- "$line" >> "$tmp_file"
    done < "$task_file"

    mv "$tmp_file" "$task_file"

    if (( removed == 1 )); then
        echo -e "${GREEN}[add_task] 已删除启动任务:${RESET} $target"
        return 0
    else
        echo -e "${YELLOW}[add_task] 未找到任务:${RESET} $target"
        return 1
    fi
}

add_task() {
    load_color GREEN YELLOW RED RESET

    local task_file
    task_file=$(_add_task_task_file)

    case "$1" in
        -h|--help)
            _add_task_help
            return 0
            ;;
        -l|--list)
            _add_task_list "$task_file"
            return $?
            ;;
        -r|--remove)
            shift
            _add_task_remove "$task_file" "$@"
            return $?
            ;;
    esac

    if (( $# == 0 )); then
        echo -e "${RED}[add_task] 请提供要添加的命令${RESET}"
        echo "Try: add_task --help"
        return 2
    fi

    _add_task_ensure_file "$task_file"

    local -a cmd_parts
    cmd_parts=("$@")
    local cmd_line="${(j: :)${(@q)cmd_parts}}"

    local line normalized
    while IFS= read -r line || [[ -n "$line" ]]; do
        normalized=$(_add_task_normalize_line "$line") || continue
        if [[ "$normalized" == "$cmd_line" ]]; then
            echo -e "${YELLOW}[add_task] 任务已存在，已跳过:${RESET} $cmd_line"
            return 0
        fi
    done < "$task_file"

    print -r -- "$cmd_line" >> "$task_file"
    echo -e "${GREEN}[add_task] 已添加启动任务:${RESET} $cmd_line"
    echo "任务文件: $task_file"
}
