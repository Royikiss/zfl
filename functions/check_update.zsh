# 辅助函数: 写入标记文件
_check_update_write_to() {
    local file=$1
    local text=$2
    [[ -f "$file" ]] && chmod 600 "$file"
    echo "$text" > "$file"
    chmod 400 "$file"
}

# 辅助函数: 兼容性超时执行（无 timeout 命令时直接执行）
_check_update_run_with_timeout() {
    local sec=$1
    shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "$sec" "$@"
    else
        "$@"
    fi
}

# 进程锁：确保同一台机器只有一个 check_update 实例运行
_check_update_acquire_process_lock() {
    local lock_dir=$1
    local pid_file="$lock_dir/pid"
    local ts_file="$lock_dir/.timestamp"
    local existing_pid=""

    if mkdir "$lock_dir" 2>/dev/null; then
        echo "$$" > "$pid_file" 2>/dev/null || true
        echo "$(date +%s)" > "$ts_file" 2>/dev/null || true
        return 0
    fi

    if [[ -f "$pid_file" ]]; then
        existing_pid=$(cat "$pid_file" 2>/dev/null)
        # 若锁的 pid 就是当前 shell（$$ 在函数里始终是交互式 shell pid），
        # 说明是本 shell 上次运行留下的陈旧锁，直接回收而非阻塞。
        if [[ "$existing_pid" == <-> ]] && [[ "$existing_pid" != "$$" ]] && kill -0 "$existing_pid" 2>/dev/null; then
            return 1
        fi
    fi

    # 锁存在但进程不在：回收后重试一次
    rm -rf "$lock_dir" 2>/dev/null || true
    if mkdir "$lock_dir" 2>/dev/null; then
        echo "$$" > "$pid_file" 2>/dev/null || true
        echo "$(date +%s)" > "$ts_file" 2>/dev/null || true
        return 0
    fi

    return 1
}

# 将“秒差”格式化为更友好的中文年龄文案
_check_update_format_age() {
    local age_seconds=$1

    if [[ -z "$age_seconds" || "$age_seconds" != <-> ]]; then
        echo "未知"
        return 0
    fi

    (( age_seconds < 0 )) && age_seconds=0

    if (( age_seconds < 10 )); then
        echo "刚刚"
    elif (( age_seconds < 60 )); then
        echo "${age_seconds}秒前"
    elif (( age_seconds < 3600 )); then
        echo "$(( age_seconds / 60 ))分钟前"
    elif (( age_seconds < 86400 )); then
        echo "$(( age_seconds / 3600 ))小时前"
    else
        echo "$(( age_seconds / 86400 ))天前"
    fi
}

# 规范化整数环境变量：非法值回退为默认
_check_update_int_or_default() {
    local raw=$1
    local fallback=$2
    if [[ "$raw" == <-> ]]; then
        echo "$raw"
    else
        echo "$fallback"
    fi
}

# 规范化提示策略：pending_first | once_per_day | strict_daily
_check_update_normalize_prompt_policy() {
    local raw=$1
    case "$raw" in
        pending_first|once_per_day|strict_daily)
            echo "$raw"
            ;;
        *)
            echo "pending_first"
            ;;
    esac
}

_check_update_help() {
    cat <<'EOF'
check_update - 启动时包更新检查与交互更新

用法:
  check_update [选项]

选项:
  -f, --force    强制触发一次检查/交互（忽略今天已提示/已更新限制）
  -h, --help     显示本帮助并退出

环境变量:
  CHECK_UPDATE_CACHE_TTL_SECONDS
                 更新数量缓存有效期（秒），默认 1800
  CHECK_UPDATE_LOCK_STALE_SECONDS
                 后台刷新锁超时阈值（秒），默认 600；超过则自动回收陈旧锁
  CHECK_UPDATE_PROCESS_LOCK
                 进程锁目录（默认 ~/.cache/zsh/CheckUpdateProcess.lock）
  CHECK_UPDATE_PROMPT_POLICY
                 提示策略：pending_first | once_per_day | strict_daily（默认 pending_first）

说明:
  - 正常模式下，check_update 会优先读取本地缓存并在后台异步刷新，避免阻塞 shell 启动。
  - 强制模式仅强制进入一次交互流程，不会关闭异步缓存机制。
  - pending_first：同天若仍有可更新包，继续提示（不易漏更新）。
  - once_per_day：同天最多提示一次，拒绝后当天静默。
  - strict_daily：仅在“非今天成功更新”时提示（除 --force）。
EOF
}

# 缓存写入：shell 赋值格式，便于 zsh 直接 source
_check_update_write_count_cache() {
    local file=$1
    local generated_at=$2
    local aur_count=$3
    local flathub_count=$4
    local tmp_file="${file}.tmp.$$"

    [[ -f "$file" ]] && chmod 600 "$file"

    {
        echo "generated_at=${generated_at}"
        echo "aur_pacman=${aur_count}"
        echo "flathub=${flathub_count}"
    } > "$tmp_file"

    mv "$tmp_file" "$file"
    chmod 400 "$file"
}

# 读取缓存: 输出 generated_at aur_pacman flathub
_check_update_read_count_cache() {
    local file=$1
    local generated_at=""
    local aur_pacman=""
    local flathub=""

    [[ -f "$file" ]] || return 1
    source "$file" 2>/dev/null || return 1

    [[ "$generated_at" == <-> ]] || return 1
    [[ "$aur_pacman" == <-> ]] || aur_pacman=0
    [[ "$flathub" == <-> ]] || flathub=0

    echo "$generated_at $aur_pacman $flathub"
}

_check_update_cached_count() {
    local backend=$1
    local cache_file=$2
    local cache_data generated_at aur_count flathub_count

    cache_data=$(_check_update_read_count_cache "$cache_file") || return 1
    generated_at=${cache_data%% *}
    cache_data=${cache_data#* }
    aur_count=${cache_data%% *}
    flathub_count=${cache_data#* }

    case "$backend" in
        aur_pacman) echo "${aur_count:-0}" ;;
        flathub) echo "${flathub_count:-0}" ;;
        *) return 1 ;;
    esac
}

# 只读计数：统计非空行数量
_check_update_count_lines() {
    awk 'NF{c++} END{print c+0}'
}

# 只读计数：官方仓库（不触发 sudo，不做 -Sy）
_check_update_count_repo_readonly() {
    local rows=""

    if command -v checkupdates >/dev/null 2>&1; then
        rows=$(checkupdates 2>/dev/null) || rows=""
    elif command -v pacman >/dev/null 2>&1; then
        rows=$(pacman -Qu 2>/dev/null) || rows=""
    fi

    if [[ -n "$rows" ]]; then
        printf "%s\n" "$rows" | _check_update_count_lines
    else
        echo 0
    fi
}

# 只读计数：AUR（不触发 sudo，不做 -Sy）
_check_update_count_aur_readonly() {
    local rows=""

    if command -v yay >/dev/null 2>&1; then
        rows=$(yay -Qua 2>/dev/null) || rows=""
    fi

    if [[ -n "$rows" ]]; then
        printf "%s\n" "$rows" | _check_update_count_lines
    else
        echo 0
    fi
}

# 后台刷新缓存（只读计数，不触发 sudo）
_check_update_refresh_count_cache() {
    local cache_file=$1
    local aur_count=0
    local flathub_count=0
    local now_epoch
    local repo_count=0
    local aur_only_count=0

    now_epoch=$(date +%s)

    if _check_update_backend_available_aur_pacman; then
        repo_count=$(_check_update_count_repo_readonly)
        aur_only_count=$(_check_update_count_aur_readonly)
        aur_count=$(( ${repo_count:-0} + ${aur_only_count:-0} ))
    fi

    if _check_update_backend_available_flathub; then
        flathub_count=$(_check_update_run_with_timeout 25 flatpak remote-ls --updates --columns=application,origin 2>/dev/null | awk '$2=="flathub"{c++} END{print c+0}')
        flathub_count=${flathub_count:-0}
    fi

    _check_update_write_count_cache "$cache_file" "$now_epoch" "$aur_count" "$flathub_count"
}

# 后台刷新调度（防并发 + 陈旧锁回收）
_check_update_schedule_cache_refresh() {
    local cache_file=$1
    local lock_dir=$2
    local lock_stale_seconds=${3:-600}
    local lock_ts_file="$lock_dir/.timestamp"
    local lock_ts=""
    local now_epoch

    now_epoch=$(date +%s)

    mkdir -p "${lock_dir:h}"

    # 若检测到陈旧锁，先回收再尝试重新加锁
    if [[ -d "$lock_dir" ]]; then
        if [[ -f "$lock_ts_file" ]]; then
            lock_ts=$(cat "$lock_ts_file" 2>/dev/null)
            if [[ "$lock_ts" == <-> ]] && (( now_epoch - lock_ts > lock_stale_seconds )); then
                rm -rf "$lock_dir" 2>/dev/null || true
            fi
        else
            # 历史无时间戳锁：保守回收，避免永久卡住
            rm -rf "$lock_dir" 2>/dev/null || true
        fi
    fi

    if ! mkdir "$lock_dir" 2>/dev/null; then
        return 1
    fi

    echo "$now_epoch" > "$lock_ts_file" 2>/dev/null || true

    (
        trap 'rm -rf "$lock_dir" 2>/dev/null' EXIT INT TERM
        _check_update_refresh_count_cache "$cache_file"
    ) >/dev/null 2>&1 &!

    return 0
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

# 前台计数：只读统计（官方仓库 + AUR），不做 -Sy，不触发 sudo
_check_update_backend_count_aur_pacman() {
    local repo_count=0
    local aur_only_count=0

    repo_count=$(_check_update_count_repo_readonly)
    aur_only_count=$(_check_update_count_aur_readonly)

    echo $(( ${repo_count:-0} + ${aur_only_count:-0} ))
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

_check_update_sum_cached_counts() {
    local cache_file=$1
    shift
    local -a backends=("$@")
    local backend count total=0

    for backend in "${backends[@]}"; do
        count=$(_check_update_cached_count "$backend" "$cache_file") || count=0
        count=${count:-0}
        total=$(( total + count ))
    done

    echo "$total"
}

_check_update_show_update_counts() {
    load_color GREEN YELLOW RESET
    local cache_file=$1
    shift
    local -a backends=("$@")
    local backend label count total=0

    if (( ${#backends[@]} == 0 )); then
        echo -e "${YELLOW}当前无可用更新源（yay/flatpak 不可用或未配置 flathub）${RESET}"
        return 0
    fi

    for backend in "${backends[@]}"; do
        label=$(_check_update_backend_label "$backend")

        count=$(_check_update_cached_count "$backend" "$cache_file") || count=""
        if [[ -z "$count" ]]; then
            count=$("_check_update_backend_count_${backend}")
        fi

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
    local cache_file=$3
    local cache_generated_at=$4
    local now_epoch=$5
    local cache_ttl_seconds=$6
    local refresh_in_progress=$7

    local days=$(( ( $(date -d "$now" +%s ) - $(date -d "$last" +%s) ) / 86400 ))
    local -a available_backends
    local ans cache_age cache_age_human

    available_backends=("${(z)$(_check_update_collect_available_backends)}")

    echo -e "现在是${YELLOW} $now ${RESET}，距离上次成功更新已经${YELLOW} $days ${RESET}天了"
    if [[ "$cache_generated_at" == <-> ]]; then
        cache_age=$(( now_epoch - cache_generated_at ))
        cache_age_human=$(_check_update_format_age "$cache_age")

        if (( cache_age > cache_ttl_seconds )); then
            echo -e "更新数量缓存：${YELLOW}${cache_age_human}${RESET}（已过期）"
        else
            echo -e "更新数量缓存：${YELLOW}${cache_age_human}${RESET}（有效）"
        fi
    else
        echo -e "${YELLOW}更新数量缓存不可用${RESET}"
    fi

    if (( refresh_in_progress == 1 )); then
        echo -e "${YELLOW}后台刷新状态：进行中（本次提示可能使用旧缓存）${RESET}"
    fi

    if (( ${#available_backends[@]} > 0 )); then
        echo "已启用更新源：$(for b in "${available_backends[@]}"; do _check_update_backend_label "$b"; done | paste -sd ', ' -)"
    fi

    echo -n -e "请问需要${GREEN}更新${RESET}吗？\n"
    echo -n -e "${GREEN}[Enter/Y/y:更新]${RESET}\n${YELLOW}[C/c：查看更新包数目]${RESET}\n${RED}[N/n/Other:拒绝更新]${RESET}\n"

    read ans

    while [[ "$ans" == "C" || "$ans" == "c" ]]; do
        _check_update_show_update_counts "$cache_file" "${available_backends[@]}"
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
    local arg
    local force_update=0

    for arg in "$@"; do
        case "$arg" in
            -f|--force)
                force_update=1
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
    local UpdateFlag="$cache_dir/UpdateFlag.lock"                 # 记录“上次成功更新日期”
    local PromptFlag="$cache_dir/UpdatePromptFlag.lock"           # 记录“上次拒绝提示日期（避免当天重复打扰）"
    local CountCache="$cache_dir/UpdateCountCache.lock"           # 记录“上次更新数量缓存”
    local RefreshLockDir="$cache_dir/UpdateRefresh.lock"          # 后台刷新互斥锁
    local ProcessLockDir="${CHECK_UPDATE_PROCESS_LOCK:-$cache_dir/CheckUpdateProcess.lock}"     # 进程锁：整机唯一实例
    local cache_ttl_seconds
    cache_ttl_seconds=$(_check_update_int_or_default "${CHECK_UPDATE_CACHE_TTL_SECONDS:-1800}" 1800)
    local lock_stale_seconds
    lock_stale_seconds=$(_check_update_int_or_default "${CHECK_UPDATE_LOCK_STALE_SECONDS:-600}" 600)
    local prompt_policy
    prompt_policy=$(_check_update_normalize_prompt_policy "${CHECK_UPDATE_PROMPT_POLICY:-once_per_day}")

    mkdir -p "$cache_dir"

    if ! _check_update_acquire_process_lock "$ProcessLockDir"; then
        return 0
    fi

    trap "rm -rf '$ProcessLockDir' 2>/dev/null" EXIT INT TERM

    local today=$(date "+%Y-%m-%d")
    local now_epoch
    now_epoch=$(date +%s)

    local last_update last_prompt
    local cache_data cache_generated_at="" cache_total=0
    local refresh_in_progress=0
    local -a available_backends
    local should_prompt=0

    if (( force_update == 1 )); then
        echo "[check_update] 强制模式已启用（-f/--force）"
    fi

    # 首次安装：初始化成功更新日期（保持你原来的“首次不强制更新”行为）
    if [[ ! -f "$UpdateFlag" ]]; then
        echo "首次创建更新标记文件..."
        _check_update_write_to "$UpdateFlag" "$today"
    fi

    last_update=$(cat "$UpdateFlag")
    [[ -f "$PromptFlag" ]] && last_prompt=$(cat "$PromptFlag") || last_prompt=""

    available_backends=("${(z)$(_check_update_collect_available_backends)}")

    cache_data=$(_check_update_read_count_cache "$CountCache") || cache_data=""
    if [[ -n "$cache_data" ]]; then
        cache_generated_at=${cache_data%% *}
    fi

    # 缓存缺失或过期时，后台异步刷新（不阻塞前台）
    if [[ -z "$cache_generated_at" || $(( now_epoch - cache_generated_at )) -gt $cache_ttl_seconds ]]; then
        _check_update_schedule_cache_refresh "$CountCache" "$RefreshLockDir" "$lock_stale_seconds" >/dev/null 2>&1
    fi

    [[ -d "$RefreshLockDir" ]] && refresh_in_progress=1

    if [[ -n "$cache_data" ]]; then
        cache_total=$(_check_update_sum_cached_counts "$CountCache" "${available_backends[@]}")
    fi

    # 触发提示条件：
    # 1) 强制模式：无条件提示（忽略日期与拒绝标记）
    # 2) 提示策略可配置（CHECK_UPDATE_PROMPT_POLICY）：
    #    - pending_first（默认）：同天若仍有可更新包则提示
    #    - once_per_day：同天不再提示（除 --force）
    #    - strict_daily：仅按“上次成功更新日期”判断（除 --force）
    if (( force_update == 1 )); then
        should_prompt=1
    else
        case "$prompt_policy" in
            pending_first)
                if [[ "$last_update" != "$today" ]]; then
                    should_prompt=1
                elif (( cache_total > 0 )); then
                    should_prompt=1
                fi
                ;;
            once_per_day|strict_daily)
                if [[ "$last_update" != "$today" ]]; then
                    should_prompt=1
                fi
                ;;
        esac
    fi

    # once_per_day：今天拒绝过后当天静默（强制模式除外）
    if (( force_update == 0 )) && [[ "$prompt_policy" == "once_per_day" ]] && [[ "$last_prompt" == "$today" ]]; then
        should_prompt=0
    fi

    if (( should_prompt == 1 )); then
        _check_update_qa "$last_update" "$today" "$CountCache" "$cache_generated_at" "$now_epoch" "$cache_ttl_seconds" "$refresh_in_progress"
        local result=$?

        case "$result" in
            0)
                # 只有真正更新成功，才刷新“上次成功更新日期”
                _check_update_write_to "$UpdateFlag" "$today"
                # 更新成功后清理“拒绝提示”标记，允许当天后续新包再次触发
                [[ -f "$PromptFlag" ]] && rm -f "$PromptFlag"
                # 更新完成后异步刷新一次缓存
                _check_update_schedule_cache_refresh "$CountCache" "$RefreshLockDir" "$lock_stale_seconds" >/dev/null 2>&1
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
