# 无需变动

lazy_load_functions() {
    # 懒加载方法
    load_color RED GREEN RESET    # 加载颜色
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


# 懒加载预处理:遍历社区函数与用户私有函数目录，为每个函数创建占位符与补全占位符
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
# base.zsh - 注册颜色加载器
# =========================

load_color() {
    # 如果是交互式终端直接调用（顶层调用），拒绝执行
    if [[ $ZSH_EVAL_CONTEXT == "toplevel" ]]; then
        echo "load_color: 此函数仅供脚本内部使用" >&2
        return 1
    fi

    # 如果 COLORS 数组还没加载，就加载一次
    if [[ -z "${COLORS[RESET]}" ]]; then
        source "$ZFL_HOME/core/colors.zsh" || {
            echo "无法加载颜色定义文件" >&2
            return 1
        }
    fi

    # 遍历用户请求的颜色名
    for name in "$@"; do
        if [[ -n "${COLORS[$name]}" ]]; then
            # 在调用者作用域定义变量
            eval "$name='${COLORS[$name]}'"
        else
            echo "颜色变量 $name 未定义" >&2
        fi
    done
}
# =========================

# 依赖断言函数：检查外部命令依赖是否满足
zfl_require() {
    load_color RED RESET
    local dep missing=()
    for dep in "$@"; do
        if ! (( $+commands[$dep] )); then
            missing+=("$dep")
        fi
    done
    if (( ${#missing[@]} > 0 )); then
        echo -e "${RED}[ERROR]${RESET} 缺少必要依赖: ${missing[*]}，请先安装它们。" >&2
        return 1
    fi
}

