# core/metadata.zsh - ZFL Metadata Engine runtime consumer
#
# Provides high-performance, 0-fork in-memory metadata queries and cache
# synchronization for the ZFL framework.

() {
    local cache_file="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/metadata.zsh"
    if [[ -f "$cache_file" ]]; then
        source "$cache_file" 2>/dev/null
    fi
}

zfl_meta_sync() {
    local cache_file="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/metadata.zsh"
    local force=0
    [[ "$1" == "--force" || "$1" == "-f" ]] && force=1

    if (( force )) || [[ ! -f "$cache_file" ]]; then
        if whence python3 >/dev/null 2>&1; then
            python3 "$ZFL_HOME/python/metadata_engine.py" compile --output "$cache_file" 3<&- >/dev/null 2>&1
            [[ -f "$cache_file" ]] && source "$cache_file" 2>/dev/null
        fi
        return 0
    fi

    # Check mtime of functions directories vs cache file
    local dir_func="$ZFL_HOME/functions"
    local dir_custom="$ZFL_HOME/custom_functions"
    local is_stale=0

    if [[ -d "$dir_func" && "$dir_func" -nt "$cache_file" ]]; then
        is_stale=1
    elif [[ -d "$dir_custom" && "$dir_custom" -nt "$cache_file" ]]; then
        is_stale=1
    fi

    if (( is_stale )); then
        if whence python3 >/dev/null 2>&1; then
            python3 "$ZFL_HOME/python/metadata_engine.py" compile --output "$cache_file" 3<&- >/dev/null 2>&1
            [[ -f "$cache_file" ]] && source "$cache_file" 2>/dev/null
        fi
    fi
    return 0
}

zfl_meta_is_quiet() {
    local func_name=$1
    local func_file=$2

    # 1. Fast path: check in-memory associative array (0 fork, 0 file I/O)
    if [[ -n "${ZFL_META_NAMES[$func_name]}" ]]; then
        [[ "${ZFL_META_QUIET[$func_name]}" == "1" ]] && return 0
        return 1
    fi

    # 2. If cache wasn't loaded in current session, try loading it
    local cache_file="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/metadata.zsh"
    if [[ -f "$cache_file" ]]; then
        source "$cache_file" 2>/dev/null
        if [[ -n "${ZFL_META_NAMES[$func_name]}" ]]; then
            [[ "${ZFL_META_QUIET[$func_name]}" == "1" ]] && return 0
            return 1
        fi
    fi

    # 3. Cold-boot fallback: pure shell header scan for quiet flag
    if [[ -z "$func_file" ]]; then
        if [[ -f "$ZFL_HOME/functions/${func_name}.zsh" ]]; then
            func_file="$ZFL_HOME/functions/${func_name}.zsh"
        elif [[ -f "$ZFL_HOME/custom_functions/${func_name}.zsh" ]]; then
            func_file="$ZFL_HOME/custom_functions/${func_name}.zsh"
        fi
    fi

    if [[ -n "$func_file" && -f "$func_file" ]]; then
        local line trimmed content key val
        while IFS= read -r line; do
            trimmed="${line##[[:space:]]}"
            [[ -z "$trimmed" ]] && continue
            [[ "$trimmed" != "#"* ]] && break
            if [[ "$trimmed" == "#?"* ]]; then
                content="${trimmed#\#?}"
                content="${content##[[:space:]]}"
                if [[ "$content" == *":"* ]]; then
                    key="${content%%:*}"
                    val="${content#*:}"
                    key="${key##[[:space:]]}"; key="${key%%[[:space:]]}"
                    val="${val##[[:space:]]}"; val="${val%%[[:space:]]}"
                    case "${(L)key}" in
                        "quiet"|"lazy_quiet"|"lazy_silent"|"静默"|"免提示")
                            if [[ "$val" == "true" || "$val" == "1" || "$val" == "yes" ]]; then
                                return 0
                            fi
                            return 1
                            ;;
                    esac
                fi
            fi
        done < "$func_file"
    fi

    return 1
}

zfl_meta_is_protected() {
    local func_name=$1
    [[ -z "${ZFL_META_NAMES[$func_name]}" ]] && zfl_meta_sync
    [[ "${ZFL_META_PROTECTED[$func_name]}" == "1" ]] && return 0
    return 1
}

zfl_meta_load() {
    local func_name=$1
    local target_var=$2
    [[ -n "$func_name" && -n "$target_var" ]] || return 1

    [[ -z "${ZFL_META_NAMES[$func_name]}" ]] && zfl_meta_sync
    [[ -n "${ZFL_META_NAMES[$func_name]}" ]] || return 1

    eval "${target_var}[name]=${(q)ZFL_META_NAMES[$func_name]}
          ${target_var}[desc]=${(q)ZFL_META_DESC[$func_name]}
          ${target_var}[description]=${(q)ZFL_META_DESC[$func_name]}
          ${target_var}[author]=${(q)ZFL_META_AUTHOR[$func_name]}
          ${target_var}[version]=${(q)ZFL_META_VERSION[$func_name]}
          ${target_var}[deps]=${(q)ZFL_META_DEPS[$func_name]}
          ${target_var}[usage]=${(q)ZFL_META_USAGE[$func_name]}
          ${target_var}[example]=${(q)ZFL_META_EXAMPLE[$func_name]}
          ${target_var}[is_protected]=${(q)ZFL_META_PROTECTED[$func_name]}
          ${target_var}[is_quiet]=${(q)ZFL_META_QUIET[$func_name]}
          ${target_var}[file]=${(q)ZFL_META_FILE[$func_name]}
          ${target_var}[source]=${(q)ZFL_META_SOURCE[$func_name]}
          ${target_var}[valid]=${(q)ZFL_META_VALID[$func_name]}
          ${target_var}[warnings]=${(q)ZFL_META_WARNINGS[$func_name]}
          ${target_var}[errors]=${(q)ZFL_META_ERRORS[$func_name]}"
    return 0
}

zfl_meta_get() {
    local func_name=$1
    local field_name=$2
    REPLY=""
    [[ -n "$func_name" && -n "$field_name" ]] || return 1

    [[ -z "${ZFL_META_NAMES[$func_name]}" ]] && zfl_meta_sync
    [[ -n "${ZFL_META_NAMES[$func_name]}" ]] || return 1

    case "$field_name" in
        "name") REPLY="${ZFL_META_NAMES[$func_name]}" ;;
        "desc"|"description") REPLY="${ZFL_META_DESC[$func_name]}" ;;
        "author") REPLY="${ZFL_META_AUTHOR[$func_name]}" ;;
        "version") REPLY="${ZFL_META_VERSION[$func_name]}" ;;
        "deps") REPLY="${ZFL_META_DEPS[$func_name]}" ;;
        "usage") REPLY="${ZFL_META_USAGE[$func_name]}" ;;
        "example") REPLY="${ZFL_META_EXAMPLE[$func_name]}" ;;
        "protected") REPLY="${ZFL_META_PROTECTED[$func_name]}" ;;
        "quiet") REPLY="${ZFL_META_QUIET[$func_name]}" ;;
        "file") REPLY="${ZFL_META_FILE[$func_name]}" ;;
        "source") REPLY="${ZFL_META_SOURCE[$func_name]}" ;;
        "valid") REPLY="${ZFL_META_VALID[$func_name]}" ;;
        "warnings") REPLY="${ZFL_META_WARNINGS[$func_name]}" ;;
        "errors") REPLY="${ZFL_META_ERRORS[$func_name]}" ;;
        *) return 1 ;;
    esac
    return 0
}
