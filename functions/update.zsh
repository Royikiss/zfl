#? name: update
#? description: Update system packages (yay/pacman and flatpak)
#? author: Royi
#? version: 1.0.0
#? deps: pacman
#? usage: update
#? example: update

_update_help() {
    local lang=${ZFL_LANG:-${LANG%%.*}}
    if [[ "$lang" == zh* ]]; then
        cat <<'HELP_EOF'
update - 系统一键更新

用法:
  update [选项]

选项:
  -h, --help     显示本帮助并退出

说明:
  - 自动检测并优先调用 yay 进行系统与 AUR 软件包更新；若 yay 不可用则回退至 sudo pacman。
  - 若系统配置有 flatpak (flathub)，将一并执行 flatpak 软件更新。
  - 更新成功后，会自动刷新更新时间标记，重置终端启动更新提示。
HELP_EOF
    else
        cat <<'HELP_EOF'
update - One-click system package updater

Usage:
  update [options]

Options:
  -h, --help     Show this help and exit

Notes:
  - Automatically detects and uses yay to update system and AUR packages; falls back to sudo pacman if yay is unavailable.
  - If flatpak (flathub) is configured, updates flatpak applications as well.
  - Upon successful update, automatically updates the timestamp flag and resets terminal startup reminders.
HELP_EOF
    fi
}

update() {
    local arg
    local lang=${ZFL_LANG:-${LANG%%.*}}

    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                _update_help
                return 0
                ;;
        esac
    done

    zfl_require pacman || return 1

    load_color GREEN RED RESET BOLD BRIGHT_BLUE BRIGHT_CYAN

    local update_success=0

    # 1. 更新系统包 (yay / pacman)
    if command -v yay >/dev/null 2>&1; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${BOLD}${BRIGHT_BLUE}>>> 开始更新系统及 AUR 软件包 (yay)...${RESET}"
        else
            echo -e "${BOLD}${BRIGHT_BLUE}>>> Updating system and AUR packages (yay)...${RESET}"
        fi
        if ! yay -Syu; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[update] yay 更新失败。${RESET}" >&2
            else
                echo -e "${RED}[update] yay update failed.${RESET}" >&2
            fi
            return 1
        fi
        update_success=1
    elif command -v pacman >/dev/null 2>&1; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${BOLD}${BRIGHT_BLUE}>>> 开始更新系统软件包 (sudo pacman)...${RESET}"
        else
            echo -e "${BOLD}${BRIGHT_BLUE}>>> Updating system packages (sudo pacman)...${RESET}"
        fi
        if ! sudo pacman -Syu; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[update] pacman 更新失败。${RESET}" >&2
            else
                echo -e "${RED}[update] pacman update failed.${RESET}" >&2
            fi
            return 1
        fi
        update_success=1
    fi

    # 2. 更新 Flatpak 应用（若已安装且配置了源）
    if command -v flatpak >/dev/null 2>&1; then
        if flatpak remotes --columns=name 2>/dev/null | grep -Fxq "flathub"; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${BOLD}${BRIGHT_CYAN}>>> 开始更新 Flatpak 应用与运行时...${RESET}"
            else
                echo -e "${BOLD}${BRIGHT_CYAN}>>> Updating Flatpak applications and runtimes...${RESET}"
            fi
            if ! flatpak update; then
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[update] flatpak 更新过程中出现错误。${RESET}" >&2
                else
                    echo -e "${RED}[update] Flatpak update encountered errors.${RESET}" >&2
                fi
                return 1
            fi
            update_success=1
        fi
    fi

    # 3. 记录更新成功日期，重置提示
    if (( update_success == 1 )); then
        local cache_dir="$HOME/.cache/zsh"
        local UpdateFlag="$cache_dir/UpdateFlag.lock"
        local today
        today=$(date "+%Y-%m-%d")

        mkdir -p "$cache_dir"
        [[ -f "$UpdateFlag" ]] && chmod 600 "$UpdateFlag"
        echo "$today" > "$UpdateFlag"
        chmod 400 "$UpdateFlag"

        # 清理旧版本遗留的状态文件
        rm -f "$cache_dir/UpdatePromptFlag.lock" "$cache_dir/UpdateCountCache.lock" 2>/dev/null
        rm -rf "$cache_dir/UpdateRefresh.lock" "$cache_dir/CheckUpdateProcess.lock" 2>/dev/null

        if [[ "$lang" == zh* ]]; then
            echo -e "${GREEN}${BOLD}[update] 全部更新完成！已更新日期标记为 ${today}。${RESET}"
        else
            echo -e "${GREEN}${BOLD}[update] All updates finished successfully! Updated flag to ${today}.${RESET}"
        fi
    fi

    return 0
}

_update() {
    local -a options
    options=(
        '-h[显示帮助信息]'
        '--help[显示帮助信息]'
    )
    _arguments -s -S $options
}
