# 无需变动

lazy_load_functions() {
    # 懒加载方法
    load_color RED GREEN RESET    # 加载颜色
	local func_name=$1
    echo "${GREEN}[lazy_load]${RESET} for ${GREEN}${func_name}${RESET} ..."
	source "$HOME/.config/zsh/functions/${func_name}.zsh" || {
        echo -e "${RED}[ERROR]${RESET}: load ${func_name} failed." >&2
        return 1
    }
	"$@"
}

# 懒加载预处理:遍历函数目录，为每个函数创建占位符与补全占位符
for file in $ZFL_HOME/functions/*.zsh; do
  func_name=$(basename $file .zsh)
  eval "${func_name}() { lazy_load_functions ${func_name} \"\$@\"; }"
  eval "_${func_name}() { unfunction _${func_name} 2>/dev/null; source \"\$ZFL_HOME/functions/${func_name}.zsh\"; if whence -f _${func_name} >/dev/null; then _${func_name} \"\$@\"; else _default \"\$@\"; fi }"
  if whence compdef >/dev/null; then
    compdef "_${func_name}" "${func_name}"
  fi
done

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
