# 辅助函数: 写入标记文件
_check_update_write_to() {
    local file=$1
    local text=$2
    [[ -f "$file" ]] && chmod 600 "$file"
    echo "$text" > "$file"
    chmod 400 "$file"
}

# 更新后端注册：新增更新源时，只需补充对应的 *_available/*_count/*_update 函数
typeset -ga _CHECK_UPDATE_BACKENDS
_CHECK_UPDATE_BACKENDS=(
    "aur_pacman"
    "flathub"
)

_check_update_backend_label() {
    local backend=$1
    case "$backend" in
        aur_pacman) echo "AUR/pacman" ;;
        flathub)    echo "flathub" ;;
        *)          echo "$backend" ;;
    esac
}

_check_update_backend_available_aur_pacman() {
    command -v yay >/dev/null 2>&1
}

_check_update_backend_count_aur_pacman() {
    yay -Sy >/dev/null
    yay -Qu | wc -l | tr -d ' '
}

_check_update_backend_update_aur_pacman() {
    yay -Syu
}

_check_update_backend_available_flathub() {
    command -v flatpak >/dev/null 2>&1 || return 1
    flatpak remotes --columns=name 2>/dev/null | grep -Fxq "flathub"
}

_check_update_backend_count_flathub() {
    flatpak remote-ls --updates --columns=application,origin 2>/dev/null | awk '$2=="flathub"{c++} END{print c+0}'
}

_check_update_backend_update_flathub() {
    load_color BOLD BRIGHT_CYAN BRIGHT_YELLOW GREEN RESET RED
    local -a rows
    local line app ref origin
    local idx=0 total=0

    # 逐行解析，避免空输出被错误识别为 1 条空记录
    while IFS=$'\t' read -r app ref origin; do
        [[ "$origin" == "flathub" ]] || continue
        [[ -n "$ref" ]] || continue
        [[ -z "$app" ]] && app="$ref"
        rows+=("$app|$ref")
    done < <(flatpak remote-ls --updates --columns=application,ref,origin 2>/dev/null)

    # 没有 flathub 更新时视为成功，不阻塞整体流程
    if (( ${#rows[@]} == 0 )); then
        echo -e "${BRIGHT_YELLOW}[flathub] 当前没有可更新包${RESET}"
        return 0
    fi

    total=${#rows[@]}
    echo -e "${BOLD}${BRIGHT_CYAN}========== 开始更新 flathub（共 ${total} 个） ==========${RESET}"

    for line in "${rows[@]}"; do
        app=${line%%|*}
        ref=${line#*|}
        ((idx++))

        # 即使终端不支持 flatpak 原生进度条，也能看到明确的整体进度
        echo -e "${BOLD}${BRIGHT_CYAN}[flathub ${idx}/${total}]${RESET} ${BRIGHT_YELLOW}${app}${RESET}"

        if ! flatpak update -y "$ref"; then
            echo -e "${RED}[flathub] 更新失败：${app} (${ref})${RESET}"
            return 1
        fi
    done

    echo -e "${GREEN}[flathub] 全部更新完成（${total}/${total}）${RESET}"
    return 0
}

_check_update_collect_available_backends() {
    local backend
    local -a available_backends=()
    for backend in "${_CHECK_UPDATE_BACKENDS[@]}"; do
        if "_check_update_backend_available_${backend}"; then
            available_backends+=("$backend")
        fi
    done
    echo "${available_backends[@]}"
}

_check_update_show_update_counts() {
    load_color GREEN YELLOW RESET
    local -a backends=("$@")
    local backend label count total=0

    if (( ${#backends[@]} == 0 )); then
        echo -e "${YELLOW}当前无可用更新源（yay/flatpak 不可用或未配置 flathub）${RESET}"
        return 0
    fi

    for backend in "${backends[@]}"; do
        label=$(_check_update_backend_label "$backend")
        count=$("_check_update_backend_count_${backend}")
        count=${count:-0}
        total=$(( total + count ))
        echo -e "${label} 可更新包数量：${GREEN}${count}${RESET}"
    done

    echo -e "总可更新包数量：${GREEN}${total}${RESET}"
}

_check_update_run_updates() {
    load_color RED GREEN RESET BOLD BRIGHT_BLUE BRIGHT_GREEN BRIGHT_YELLOW
    local -a backends=("$@")
    local backend label
    local i=0 total=${#backends[@]}

    for backend in "${backends[@]}"; do
        label=$(_check_update_backend_label "$backend")
        ((i++))
        echo -e "${BOLD}${BRIGHT_BLUE}>>> [${i}/${total}] 开始更新 ${label}${RESET}"
        if ! "_check_update_backend_update_${backend}"; then
            echo -e "${RED}${label} 更新失败${RESET} ❌"
            return 1
        fi
        echo -e "${BRIGHT_GREEN}<<< [${i}/${total}] ${label} 更新完成${RESET}"
    done

    echo -e "${GREEN}${BOLD}全部更新成功${RESET} ✅"
    return 0
}

# 辅助函数：交互式更新逻辑
_check_update_qa() {
    load_color RED GREEN YELLOW RESET
    local last=$1
    local now=$2
    local days=$(( ( $(date -d "$now" +%s ) - $(date -d "$last" +%s) ) / 86400 ))
    local -a available_backends
    local ans

    available_backends=("${(z)$(_check_update_collect_available_backends)}")

    echo -e "现在是${YELLOW} $now ${RESET}，距离上次更新已经${YELLOW} $days ${RESET}天了"
    if (( ${#available_backends[@]} > 0 )); then
        echo "已启用更新源：$(for b in "${available_backends[@]}"; do _check_update_backend_label "$b"; done | paste -sd ', ' -)"
    fi
    echo -n -e "请问需要${GREEN}更新${RESET}吗？\n"
    echo -n -e "${GREEN}[Enter/Y/y:更新]${RESET}\n${YELLOW}[C/c：查看更新包数目]${RESET}\n${RED}[N/n/Other:拒绝更新]${RESET}\n"

    read ans

    while [[ "$ans" == "C" || "$ans" == "c" ]]; do
        _check_update_show_update_counts "${available_backends[@]}"
        echo -n -e "请问需要${GREEN}更新${RESET}吗？\n"
        echo -n -e "${GREEN}[Enter/Y/y:更新]${RESET}\n${YELLOW}[C/c：查看更新包数目]${RESET}\n${RED}[N/n/Other:拒绝更新]${RESET}\n"
        read ans
    done

    case "$ans" in
        [Yy])
            _check_update_run_updates "${available_backends[@]}" || return 1
            return 0
            ;;
        "")
            _check_update_run_updates "${available_backends[@]}" || return 1
            return 0
            ;;
        *)
            echo -e "你没有更新，记得更新哟，输入 '${GREEN}update${RESET}' 即可更新~"
            return 2
            ;;
    esac
}

# 主函数：这是会被懒加载触发的入口
check_update() {
    local UpdateFlag="$HOME/.cache/zsh/UpdateFlag.lock"                 # 记录“上次成功更新日期”
    local PromptFlag="$HOME/.cache/zsh/UpdatePromptFlag.lock"           # 记录“上次提示日期（避免当天重复打扰）"
    mkdir -p "$HOME/.cache/zsh"

    local today=$(date "+%Y-%m-%d")
    local last_update last_prompt

    # 首次安装：初始化成功更新日期（保持你原来的“首次不强制更新”行为）
    if [[ ! -f "$UpdateFlag" ]]; then
        echo "首次创建更新标记文件..."
        _check_update_write_to "$UpdateFlag" "$today"
        return 0
    fi

    last_update=$(cat "$UpdateFlag")
    [[ -f "$PromptFlag" ]] && last_prompt=$(cat "$PromptFlag") || last_prompt=""

    # 当天已经提示过且用户未更新时，不再重复提示
    if [[ "$last_prompt" == "$today" && "$last_update" != "$today" ]]; then
        return 0
    fi

    if [[ "$last_update" != "$today" ]]; then
        _check_update_qa "$last_update" "$today"
        local result=$?

        case "$result" in
            0)
                # 只有真正更新成功，才刷新“上次成功更新日期”
                _check_update_write_to "$UpdateFlag" "$today"
                _check_update_write_to "$PromptFlag" "$today"
                ;;
            2)
                # 用户今天拒绝更新：只记录提示日期，不改成功更新日期
                _check_update_write_to "$PromptFlag" "$today"
                ;;
            *)
                # 更新失败：不写任何标记，方便用户修复后重试
                ;;
        esac
    fi
}
