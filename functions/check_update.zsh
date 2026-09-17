#? name: check_update
#? description: Check last system update date and prompt update reminder
#? author: Royi
#? version: 2.1.0
#? quiet: true
#? deps:
#? usage: check_update [-f|--force] [-i|--interval <days>] [-s|--set-interval <days>] [-g|--get-interval] [days]
#? example: check_update --interval 3

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
  check_update [选项] [天数]

选项:
  -f, --force                  强制显示更新提示（忽略当天已更新及间隔限制）
  -i, --interval <天数>        临时指定本次检查的提醒间隔天数（>= 1）
  -s, --set-interval <天数>    设置并持久化保存默认提醒间隔天数
  -g, --get-interval           查看当前生效的提醒间隔天数及配置来源
  -h, --help                   显示本帮助并退出

参数:
  [天数]                       简写形式，等同于 -i <天数>

优先级说明:
  1. 命令行参数 (-i/--interval 或 [天数])
  2. 环境变量 (ZFL_CHECK_UPDATE_INTERVAL)
  3. 持久化配置文件 (~/.local/share/zfl/check_update_interval)
  4. 框架默认值 (1 天)

说明:
  - 极速无阻塞启动：仅读取本地记录的上次更新日期，不发起网络请求或后台包扫描。
  - 若距离上次系统更新已有指定天数及以上，终端启动时输出提示。
  - 用户可随时在终端运行 'update' 直接执行系统更新。
HELP_EOF
    else
        cat <<'HELP_EOF'
check_update - Check last system update date and prompt reminder

Usage:
  check_update [options] [days]

Options:
  -f, --force                  Force display update reminder (ignoring same-day & interval limits)
  -i, --interval <days>        Specify reminder interval for this run (>= 1)
  -s, --set-interval <days>    Set and persist default reminder interval
  -g, --get-interval           Show currently effective reminder interval and its source
  -h, --help                   Show this help and exit

Arguments:
  [days]                       Shorthand for -i <days>

Precedence:
  1. CLI argument (-i/--interval or [days])
  2. Environment variable (ZFL_CHECK_UPDATE_INTERVAL)
  3. Persistent config file (~/.local/share/zfl/check_update_interval)
  4. Framework default (1 day)

Notes:
  - Zero-delay startup: Only reads local last update date flag, no network or background package scanning.
  - Prompts a reminder when opening terminal if not updated for the specified number of days or more.
  - You can run 'update' at any time to perform system update directly.
HELP_EOF
    fi
}

check_update() {
    local arg
    local force_prompt=0
    local cli_interval=""
    local set_interval_val=""
    local get_interval_mode=0
    local lang=${ZFL_LANG:-${LANG%%.*}}
    local config_dir="${XDG_DATA_HOME:-$HOME/.local/share}/zfl"
    local config_file="$config_dir/check_update_interval"

    while (( $# > 0 )); do
        arg="$1"
        shift
        case "$arg" in
            -f|--force)
                force_prompt=1
                ;;
            -h|--help)
                _check_update_help
                return 0
                ;;
            -g|--get-interval)
                get_interval_mode=1
                ;;
            -s|--set-interval)
                if (( $# == 0 )); then
                    if [[ "$lang" == zh* ]]; then
                        echo "check_update: 选项 '$arg' 需要参数 <天数>" >&2
                    else
                        echo "check_update: option '$arg' requires an argument <days>" >&2
                    fi
                    return 2
                fi
                set_interval_val="$1"
                shift
                ;;
            --set-interval=*)
                set_interval_val="${arg#*=}"
                ;;
            -i|--interval)
                if (( $# == 0 )); then
                    if [[ "$lang" == zh* ]]; then
                        echo "check_update: 选项 '$arg' 需要参数 <天数>" >&2
                    else
                        echo "check_update: option '$arg' requires an argument <days>" >&2
                    fi
                    return 2
                fi
                cli_interval="$1"
                shift
                ;;
            --interval=*)
                cli_interval="${arg#*=}"
                ;;
            <1->)
                cli_interval="$arg"
                ;;
            *)
                if [[ "$lang" == zh* ]]; then
                    echo "check_update: 未知选项或参数: $arg" >&2
                    echo "可使用 'check_update --help' 查看用法说明。" >&2
                else
                    echo "check_update: unknown option or argument: $arg" >&2
                    echo "Try: check_update --help" >&2
                fi
                return 2
                ;;
        esac
    done

    # 1. 查询当前提醒间隔模式
    if (( get_interval_mode == 1 )); then
        load_color YELLOW GREEN RESET BOLD RED
        local current_interval="" source_desc=""
        if [[ -n "$cli_interval" ]]; then
            if [[ "$cli_interval" != <1-> ]]; then
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[check_update] 错误: 提醒间隔必须是大于或等于 1 的正整数，当前输入: '${cli_interval}'${RESET}" >&2
                else
                    echo -e "${RED}[check_update] Error: Reminder interval must be a positive integer (>= 1), got: '${cli_interval}'${RESET}" >&2
                fi
                return 2
            fi
            current_interval="$cli_interval"
            if [[ "$lang" == zh* ]]; then
                source_desc="命令行参数"
            else
                source_desc="CLI argument"
            fi
        elif [[ -n "$ZFL_CHECK_UPDATE_INTERVAL" && "$ZFL_CHECK_UPDATE_INTERVAL" == <1-> ]]; then
            current_interval="$ZFL_CHECK_UPDATE_INTERVAL"
            if [[ "$lang" == zh* ]]; then
                source_desc="环境变量 ZFL_CHECK_UPDATE_INTERVAL"
            else
                source_desc="Environment variable ZFL_CHECK_UPDATE_INTERVAL"
            fi
        elif [[ -r "$config_file" ]]; then
            local saved_val=""
            saved_val=$(<"$config_file")
            saved_val="${saved_val//[[:space:]]/}"
            if [[ "$saved_val" == <1-> ]]; then
                current_interval="$saved_val"
                if [[ "$lang" == zh* ]]; then
                    source_desc="配置文件 $config_file"
                else
                    source_desc="Config file $config_file"
                fi
            fi
        fi

        if [[ -z "$current_interval" ]]; then
            current_interval="1"
            if [[ "$lang" == zh* ]]; then
                source_desc="默认值 (1天)"
            else
                source_desc="Default (1 day)"
            fi
        fi

        if [[ "$lang" == zh* ]]; then
            echo -e "${YELLOW}[check_update] 当前更新提醒间隔为: ${BOLD}${GREEN}${current_interval}${RESET}${YELLOW} 天（来源: ${source_desc}）${RESET}"
        else
            echo -e "${YELLOW}[check_update] Current update reminder interval: ${BOLD}${GREEN}${current_interval}${RESET}${YELLOW} day(s) (source: ${source_desc})${RESET}"
        fi
        return 0
    fi

    # 2. 设置并持久化提醒间隔模式
    if [[ -n "$set_interval_val" ]]; then
        load_color YELLOW GREEN RESET BOLD RED
        if [[ "$set_interval_val" != <1-> ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[check_update] 错误: 提醒间隔必须是大于或等于 1 的正整数，当前输入: '${set_interval_val}'${RESET}" >&2
            else
                echo -e "${RED}[check_update] Error: Reminder interval must be a positive integer (>= 1), got: '${set_interval_val}'${RESET}" >&2
            fi
            return 2
        fi

        mkdir -p "$config_dir" 2>/dev/null
        if ! echo "$set_interval_val" > "$config_file" 2>/dev/null; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[check_update] 错误: 无法写入配置文件: ${config_file}${RESET}" >&2
            else
                echo -e "${RED}[check_update] Error: Cannot write to config file: ${config_file}${RESET}" >&2
            fi
            return 1
        fi

        if [[ "$lang" == zh* ]]; then
            echo -e "${GREEN}[check_update] 已成功将默认更新提醒间隔设置为 ${BOLD}${set_interval_val}${RESET}${GREEN} 天。${RESET}"
            if [[ -n "$ZFL_CHECK_UPDATE_INTERVAL" ]]; then
                echo -e "${YELLOW}[check_update] 提示: 当前环境变量 ZFL_CHECK_UPDATE_INTERVAL=${ZFL_CHECK_UPDATE_INTERVAL} 处于生效状态，其优先级高于配置文件。${RESET}"
            fi
        else
            echo -e "${GREEN}[check_update] Successfully set default reminder interval to ${BOLD}${set_interval_val}${RESET}${GREEN} day(s).${RESET}"
            if [[ -n "$ZFL_CHECK_UPDATE_INTERVAL" ]]; then
                echo -e "${YELLOW}[check_update] Notice: Environment variable ZFL_CHECK_UPDATE_INTERVAL=${ZFL_CHECK_UPDATE_INTERVAL} is set and takes precedence over the config file.${RESET}"
            fi
        fi
        return 0
    fi

    # 3. 解析当前检查生效的间隔阈值
    local interval=""
    if [[ -n "$cli_interval" ]]; then
        if [[ "$cli_interval" != <1-> ]]; then
            load_color RED RESET
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[check_update] 错误: 提醒间隔必须是大于或等于 1 的正整数，当前输入: '${cli_interval}'${RESET}" >&2
            else
                echo -e "${RED}[check_update] Error: Reminder interval must be a positive integer (>= 1), got: '${cli_interval}'${RESET}" >&2
            fi
            return 2
        fi
        interval="$cli_interval"
    elif [[ -n "$ZFL_CHECK_UPDATE_INTERVAL" && "$ZFL_CHECK_UPDATE_INTERVAL" == <1-> ]]; then
        interval="$ZFL_CHECK_UPDATE_INTERVAL"
    elif [[ -r "$config_file" ]]; then
        local saved_val=""
        saved_val=$(<"$config_file")
        saved_val="${saved_val//[[:space:]]/}"
        if [[ "$saved_val" == <1-> ]]; then
            interval="$saved_val"
        fi
    fi

    [[ -z "$interval" ]] && interval=1

    local cache_dir="$HOME/.cache/zsh"
    local UpdateFlag="$cache_dir/UpdateFlag.lock"
    local today="" last_update=""
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

    # 若非强制模式且相隔天数少于指定间隔阈值，静默退出
    if (( force_prompt == 0 && days < interval )); then
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
        '(-f --force)'{-f,--force}'[强制显示更新提示]'
        '(-h --help)'{-h,--help}'[显示帮助信息]'
        '(-i --interval)'{-i,--interval}'[临时指定提醒间隔天数]:天数:'
        '(-s --set-interval)'{-s,--set-interval}'[设置默认提醒间隔天数]:天数:'
        '(-g --get-interval)'{-g,--get-interval}'[查看当前提醒间隔天数]'
        '::天数:_message "提醒间隔天数"'
    )
    _arguments -s -S $options
}
