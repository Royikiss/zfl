#? name: check_update
#? description: Check last system update date and prompt update reminder
#? author: Royi
#? version: 2.0.0
#? deps:
#? usage: check_update [-f|--force]
#? example: check_update

_check_update_write_flag() {
    local file=$1
    local text=$2
    [[ -f "$file" ]] && chmod 600 "$file"
    echo "$text" > "$file"
    chmod 400 "$file"
}

_check_update_help() {
    local lang=${ZFL_LANG:-${LANG%%.*}}
    if [[ "$lang" == zh* ]]; then
        cat <<'HELP_EOF'
check_update - 系统更新状态检测与提示

用法:
  check_update [选项]

选项:
  -f, --force    强制显示更新提示（忽略当天已更新限制）
  -h, --help     显示本帮助并退出

说明:
  - 极速无阻塞启动：仅读取本地记录的上次更新日期，不发起网络请求或后台包扫描。
  - 若距离上次系统更新已有 1 天及以上，终端启动时输出提示。
  - 用户可随时在终端运行 'update' 直接执行系统更新。
HELP_EOF
    else
        cat <<'HELP_EOF'
check_update - Check last system update date and prompt reminder

Usage:
  check_update [options]

Options:
  -f, --force    Force display update reminder (ignoring same-day limit)
  -h, --help     Show this help and exit

Notes:
  - Zero-delay startup: Only reads local last update date flag, no network or background package scanning.
  - Prompts a reminder when opening terminal if it has been 1 or more days since last update.
  - You can run 'update' at any time to perform system update directly.
HELP_EOF
    fi
}

check_update() {
    local arg
    local force_prompt=0
    local lang=${ZFL_LANG:-${LANG%%.*}}

    for arg in "$@"; do
        case "$arg" in
            -f|--force)
                force_prompt=1
                ;;
            -h|--help)
                _check_update_help
                return 0
                ;;
            *)
                echo "check_update: unknown option: $arg" >&2
                echo "Try: check_update --help" >&2
                return 2
                ;;
        esac
    done

    local cache_dir="$HOME/.cache/zsh"
    local UpdateFlag="$cache_dir/UpdateFlag.lock"
    local today last_update
    today=$(date "+%Y-%m-%d")

    mkdir -p "$cache_dir"

    # 首次使用初始化标记文件
    if [[ ! -f "$UpdateFlag" ]]; then
        _check_update_write_flag "$UpdateFlag" "$today"
        return 0
    fi

    last_update=$(cat "$UpdateFlag" 2>/dev/null)
    [[ -z "$last_update" ]] && last_update="$today"

    # 若今天已更新且未指定强制模式，直接静默退出
    if (( force_prompt == 0 )) && [[ "$last_update" == "$today" ]]; then
        return 0
    fi

    # 计算与上次更新相隔天数
    local last_epoch="" now_epoch_val=""
    if zmodload zsh/datetime 2>/dev/null; then
        last_epoch=$(strftime -r "%Y-%m-%d" "$last_update" 2>/dev/null)
        now_epoch_val=$(strftime -r "%Y-%m-%d" "$today" 2>/dev/null)
    fi

    if [[ -z "$last_epoch" || -z "$now_epoch_val" ]]; then
        if command -v date >/dev/null 2>&1; then
            last_epoch=$(date -d "$last_update" +%s 2>/dev/null)
            now_epoch_val=$(date -d "$today" +%s 2>/dev/null)
            if [[ -z "$last_epoch" || -z "$now_epoch_val" ]]; then
                last_epoch=$(date -j -f "%Y-%m-%d" "$last_update" "+%s" 2>/dev/null)
                now_epoch_val=$(date -j -f "%Y-%m-%d" "$today" "+%s" 2>/dev/null)
            fi
        fi
    fi

    local days=0
    if [[ -n "$last_epoch" && -n "$now_epoch_val" ]]; then
        days=$(( (now_epoch_val - last_epoch) / 86400 ))
        (( days < 0 )) && days=0
    fi

    # 若非强制模式且相隔天数少于 1 天，静默退出
    if (( force_prompt == 0 && days < 1 )); then
        return 0
    fi

    load_color YELLOW GREEN RESET BOLD BRIGHT_CYAN

    if [[ "$lang" == zh* ]]; then
        if (( days > 0 )); then
            echo -e "${YELLOW}[check_update] 系统已有 ${BOLD}${GREEN}${days}${RESET}${YELLOW} 天未更新，可输入 '${BOLD}${GREEN}update${RESET}${YELLOW}' 执行更新。${RESET}"
        else
            echo -e "${YELLOW}[check_update] 今天已更新，可输入 '${BOLD}${GREEN}update${RESET}${YELLOW}' 重新检查更新。${RESET}"
        fi
    else
        if (( days > 0 )); then
            echo -e "${YELLOW}[check_update] System has not been updated for ${BOLD}${GREEN}${days}${RESET}${YELLOW} day(s). Run '${BOLD}${GREEN}update${RESET}${YELLOW}' to update.${RESET}"
        else
            echo -e "${YELLOW}[check_update] System was updated today. Run '${BOLD}${GREEN}update${RESET}${YELLOW}' to re-update.${RESET}"
        fi
    fi

    return 0
}

_check_update() {
    local -a options
    options=(
        '-f[强制显示更新提示]'
        '--force[强制显示更新提示]'
        '-h[显示帮助信息]'
        '--help[显示帮助信息]'
    )
    _arguments -s -S $options
}
