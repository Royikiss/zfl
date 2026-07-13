# Core loading engine

lazy_load_functions() {
    # Lazy loading method
    load_color RED GREEN RESET    # Load colors
    local func_name=$1
    local func_file=$2
    echo "${GREEN}[lazy_load]${RESET} for ${GREEN}${func_name}${RESET} ..."
    source "$func_file" || {
        echo -e "${RED}[ERROR]${RESET}: load ${func_name} failed from ${func_file}." >&2
        return 1
    }
    shift 2
    "${func_name}" "$@"
}


# Lazy loading preprocessing: traverse functions and custom_functions, and create dynamic placeholder and completion stubs
() {
    local dir file func_name
    for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
        [[ -d "$dir" ]] || continue
        for file in "$dir"/*.zsh(N); do
            func_name=$(basename "$file" .zsh)
            eval "${func_name}() { lazy_load_functions ${func_name} \"${file}\" \"\$@\"; }"
            eval "_${func_name}() { unfunction _${func_name} 2>/dev/null; source \"${file}\"; if whence -f _${func_name} >/dev/null; then _${func_name} \"\$@\"; else _default \"\$@\"; fi }"
            if whence compdef >/dev/null; then
                compdef "_${func_name}" "${func_name}"
            fi
        done
    done
}

# =========================
# base.zsh - Register color loader
# =========================

load_color() {
    local name
    # If called directly from an interactive terminal (toplevel), reject execution
    if [[ $ZSH_EVAL_CONTEXT == "toplevel" ]]; then
        local lang=${ZFL_LANG:-${LANG%%.*}}
        if [[ "$lang" == zh* ]]; then
            echo "load_color: 此函数仅供脚本内部使用" >&2
        else
            echo "load_color: This function is for internal script use only" >&2
        fi
        return 1
    fi

    # If COLORS array is not loaded yet, load it once
    if [[ -z "${COLORS[RESET]}" ]]; then
        source "$ZFL_HOME/core/colors.zsh" || {
            local lang=${ZFL_LANG:-${LANG%%.*}}
            if [[ "$lang" == zh* ]]; then
                echo "无法加载颜色定义文件" >&2
            else
                echo "Failed to load color definition file" >&2
            fi
            return 1
        }
    fi

    # Traverse user requested color names
    for name in "$@"; do
        if [[ -n "${COLORS[$name]}" ]]; then
            # Define variable in caller's scope
            eval "$name='${COLORS[$name]}'"
        else
            local lang=${ZFL_LANG:-${LANG%%.*}}
            if [[ "$lang" == zh* ]]; then
                echo "颜色变量 $name 未定义" >&2
            else
                echo "Color variable $name is not defined" >&2
            fi
        fi
    done
}
# =========================

# Dependency assertion function: check if external CLI dependencies are satisfied
zfl_require() {
    load_color RED RESET
    local dep missing=()
    for dep in "$@"; do
        if ! (( $+commands[$dep] )); then
            missing+=("$dep")
        fi
    done
    if (( ${#missing[@]} > 0 )); then
        local lang=${ZFL_LANG:-${LANG%%.*}}
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 缺少必要依赖: ${missing[*]}，请先安装它们。" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Missing required dependency: ${missing[*]}, please install them first." >&2
        fi
        return 1
    fi
}


