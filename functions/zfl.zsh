#? 名称: zfl
#? 描述: ZFL 框架内置命令行管理与自发现工具
#? 作者: Antigravity
#? 版本: 1.0.0
#? 依赖: 
#? 用法: zfl <子命令> [参数]
#? 示例: zfl list

_zfl_parse_metadata() {
    local file=$1
    # 初始化输出变量（调用者需声明为 local 以接收结果）
    func_meta_name=""
    func_meta_desc=""
    func_meta_author=""
    func_meta_version=""
    func_meta_deps=""
    func_meta_usage=""
    func_meta_example=""

    [[ -f "$file" ]] || return 1

    local line content key val trimmed
    while IFS= read -r line; do
        # 去除前导空格
        trimmed="${line##[[:space:]]}"
        
        # 如果是空行或非注释行，说明已经离开了头部注释区域，停止解析
        if [[ -n "$trimmed" && "$trimmed" != "#"* ]]; then
            break
        fi

        # 解析 #? 开头的元数据行
        if [[ "$trimmed" == "#?"* ]]; then
            content="${trimmed#\#?}"
            content="${content##[[:space:]]}"
            if [[ "$content" == *":"* ]]; then
                key="${content%%:*}"
                val="${content#*:}"
                
                # 去除键值两端空格
                key="${key##[[:space:]]}"
                key="${key%%[[:space:]]}"
                val="${val##[[:space:]]}"
                val="${val%%[[:space:]]}"
                
                case "$key" in
                    "名称"|"name") func_meta_name="$val" ;;
                    "描述"|"desc"|"description") func_meta_desc="$val" ;;
                    "作者"|"author") func_meta_author="$val" ;;
                    "版本"|"version") func_meta_version="$val" ;;
                    "依赖"|"deps"|"dependencies") func_meta_deps="$val" ;;
                    "用法"|"usage") func_meta_usage="$val" ;;
                    "示例"|"example") func_meta_example="$val" ;;
                esac
            fi
        fi
    done < "$file"

    # 兜底名称
    if [[ -z "$func_meta_name" ]]; then
        func_meta_name=$(basename "$file" .zsh)
    fi
}

_zfl_help() {
    cat <<'EOF'
zfl - Zsh Function Library (ZFL) 管理工具

用法:
  zfl <子命令> [参数]

可用子命令:
  list, ls         列出所有已加载的函数及其简短描述
  info <函数名>    查看特定函数的详细元数据与用法
  check            检查所有函数的外部依赖项是否已安装
  lint [函数名...] 对指定的函数或全部函数进行静态质量校验
  remove, rm <名>  安全删除指定的函数文件并清理占位符与补全
  help, -h         显示此帮助信息

示例:
  zfl list
  zfl info weather
  zfl check
  zfl lint weather
  zfl remove weather
EOF
}


_zfl_list() {
    load_color GREEN YELLOW CYAN RED RESET BOLD
    echo -e "${BOLD}${CYAN}ZFL (Zsh Function Library) 函数列表:${RESET}"
    echo -e "--------------------------------------------------------"
    # 表头对齐：函数名(18) | 来源(4) | 描述
    printf "%-18s | %-4s | %s\n" "函数名称" "来源" "简短描述"
    echo -e "--------------------------------------------------------"

    local dir file fname source_type color_source
    # 声明用于解析的局部变量，通过动态作用域由 _zfl_parse_metadata 写入
    local func_meta_name func_meta_desc func_meta_author func_meta_version func_meta_deps func_meta_usage func_meta_example

    for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
        [[ -d "$dir" ]] || continue
        if [[ "$dir" == *"/custom_functions" ]]; then
            source_type="用户"
            color_source="${YELLOW}"
        else
            source_type="社区"
            color_source="${GREEN}"
        fi

        for file in "$dir"/*.zsh(N); do
            fname=$(basename "$file" .zsh)
            _zfl_parse_metadata "$file"
            
            # 使用 Zsh 填充修饰符保证对齐，避免 ANSI 颜色字符干扰 printf 宽度计算
            local padded_name="${(r:18:)fname}"
            local colored_name="${BOLD}${CYAN}${padded_name}${RESET}"
            
            local padded_source="${(r:4:)source_type}"
            local colored_source="${color_source}${padded_source}${RESET}"

            printf "%b | %b | %s\n" "$colored_name" "$colored_source" "${func_meta_desc:-暂无描述}"
        done
    done
    echo -e "--------------------------------------------------------"
    echo -e "提示: 使用 ${GREEN}zfl info <函数名>${RESET} 查看详细用法与依赖。"
}

_zfl_info() {
    load_color GREEN YELLOW CYAN RED RESET BOLD
    local target=$1
    if [[ -z "$target" ]]; then
        echo -e "${RED}[ERROR]${RESET} 请指定函数名称。例如: zfl info weather" >&2
        return 1
    fi

    local file path_found="" dir
    for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
        if [[ -f "$dir/${target}.zsh" ]]; then
            path_found="$dir/${target}.zsh"
            break
        fi
    done

    if [[ -z "$path_found" ]]; then
        echo -e "${RED}[ERROR]${RESET} 函数 '${target}' 不存在。" >&2
        return 1
    fi

    # 声明解析的局部变量
    local func_meta_name func_meta_desc func_meta_author func_meta_version func_meta_deps func_meta_usage func_meta_example
    _zfl_parse_metadata "$path_found"

    echo -e "${BOLD}${CYAN}函数详情: ${target}${RESET}"
    echo -e "----------------------------------------"
    echo -e "${BOLD}文件路径:${RESET} ${path_found}"
    echo -e "${BOLD}简短描述:${RESET} ${func_meta_desc:-暂无}"
    echo -e "${BOLD}脚本作者:${RESET} ${func_meta_author:-未知}"
    echo -e "${BOLD}当前版本:${RESET} ${func_meta_version:-1.0.0}"
    echo -e "${BOLD}必要依赖:${RESET} ${func_meta_deps:-无}"
    echo -e "${BOLD}使用方法:${RESET} ${func_meta_usage:-暂无}"
    if [[ -n "$func_meta_example" ]]; then
        echo -e "${BOLD}使用示例:${RESET} ${GREEN}${func_meta_example}${RESET}"
    fi
    echo -e "----------------------------------------"
}

_zfl_check() {
    load_color GREEN YELLOW CYAN RED RESET BOLD
    echo -e "${BOLD}${CYAN}正在检测 ZFL 所有函数的系统依赖状态...${RESET}"
    echo -e "--------------------------------------------------------"
    printf "%-18s | %-8s | %s\n" "函数名称" "依赖状态" "缺失依赖"
    echo -e "--------------------------------------------------------"

    local dir file fname
    local func_meta_name func_meta_desc func_meta_author func_meta_version func_meta_deps func_meta_usage func_meta_example

    for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
        [[ -d "$dir" ]] || continue
        for file in "$dir"/*.zsh(N); do
            fname=$(basename "$file" .zsh)
            _zfl_parse_metadata "$file"
            
            local padded_name="${(r:18:)fname}"
            local colored_name="${BOLD}${CYAN}${padded_name}${RESET}"

            if [[ -z "$func_meta_deps" ]]; then
                local status_str="[ NONE ]"
                local colored_status="${status_str}"
                printf "%b | %b | %s\n" "$colored_name" "$colored_status" "-"
                continue
            fi

            local dep deps_list=(${(s:,:)func_meta_deps})
            local missing=()
            for dep in "${deps_list[@]}"; do
                dep="${dep##[[:space:]]}"
                dep="${dep%%[[:space:]]}"
                [[ -z "$dep" ]] && continue
                if ! (( $+commands[$dep] )); then
                    missing+=("$dep")
                fi
            done

            if (( ${#missing[@]} == 0 )); then
                local status_str="[  OK  ]"
                local colored_status="${GREEN}${status_str}${RESET}"
                printf "%b | %b | %s\n" "$colored_name" "$colored_status" "-"
            else
                local status_str="[ MISS ]"
                local colored_status="${RED}${status_str}${RESET}"
                printf "%b | %b | %b\n" "$colored_name" "$colored_status" "${YELLOW}${missing[*]}${RESET}"
            fi
        done
    done
    echo -e "--------------------------------------------------------"
}

_zfl_lint() {
    load_color RED GREEN RESET

    local -a files_to_lint
    local target file path_found dir
    if (( $# > 0 )); then
        for target in "$@"; do
            path_found=""
            # 如果传入的直接是个存在的文件路径
            if [[ -f "$target" ]]; then
                path_found="$target"
            else
                for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
                    if [[ -f "$dir/${target}.zsh" ]]; then
                        path_found="$dir/${target}.zsh"
                        break
                    fi
                done
            fi

            if [[ -n "$path_found" ]]; then
                files_to_lint+=("$path_found")
            else
                echo -e "${RED}[ERROR]${RESET} 找不到函数或文件: $target" >&2
                return 1
            fi
        done
    else
        # 默认扫描所有函数文件
        for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
            [[ -d "$dir" ]] || continue
            for file in "$dir"/*.zsh(N); do
                files_to_lint+=("$file")
            done
        done
    fi

    if (( ${#files_to_lint[@]} == 0 )); then
        echo "未发现任何待扫描的文件。"
        return 0
    fi

    # 调用 Python 静态校验脚本并继承退出码
    python3 "$ZFL_HOME/python/zfl_lint.py" "${files_to_lint[@]}"
}

_zfl_remove() {
    load_color RED GREEN YELLOW RESET BOLD
    local target=$1
    if [[ -z "$target" ]]; then
        echo -e "${RED}[ERROR]${RESET} 请指定要删除的函数名称。例如: zfl remove weather" >&2
        return 1
    fi

    # 保护 zfl 自己，不要把自己删了
    if [[ "$target" == "zfl" ]]; then
        echo -e "${RED}[ERROR]${RESET} 不能删除 zfl 核心管理工具本身！" >&2
        return 1
    fi

    local file path_found="" dir
    for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
        if [[ -f "$dir/${target}.zsh" ]]; then
            path_found="$dir/${target}.zsh"
            break
        fi
    done

    if [[ -z "$path_found" ]]; then
        echo -e "${RED}[ERROR]${RESET} 函数 '${target}' 不存在。" >&2
        return 1
    fi

    echo -e "${YELLOW}确定要删除函数文件 ${BOLD}${path_found}${RESET}${YELLOW} 吗？ [y/N]${RESET}"
    local confirm
    read -r confirm
    if [[ "$confirm" != [yY] && "$confirm" != [yY][eE][sS] ]]; then
        echo "已取消删除。"
        return 0
    fi

    # 删除文件
    rm "$path_found" || {
        echo -e "${RED}[ERROR]${RESET} 无法删除文件 ${path_found}。" >&2
        return 1
    }

    echo -e "${GREEN}[SUCCESS]${RESET} 已删除函数文件: ${path_found}"

    # 检测并同步删除技术文档
    local doc_file="$ZFL_HOME/docs/${target}.md"
    local confirm_doc
    if [[ -f "$doc_file" ]]; then
        echo -e "${YELLOW}检测到该函数关联的技术文档 ${BOLD}${doc_file}${RESET}${YELLOW}，是否一并删除？ [y/N]${RESET}"
        read -r confirm_doc
        if [[ "$confirm_doc" == [yY] || "$confirm_doc" == [yY][eE][sS] ]]; then
            rm "$doc_file" || {
                echo -e "${RED}[WARNING]${RESET} 无法删除文档文件 ${doc_file}。" >&2
            }
            echo -e "${GREEN}[SUCCESS]${RESET} 已删除文档文件: ${doc_file}"
        else
            echo "保留文档文件。"
        fi
    fi

    # 清理当前会话的函数和补全
    if whence -f "$target" >/dev/null; then
        unfunction "$target" 2>/dev/null
        echo -e "${GREEN}[CLEAN]${RESET} 已卸载当前会话中的函数 ${target}"
    fi
    if whence -f "_$target" >/dev/null; then
        unfunction "_$target" 2>/dev/null
        echo -e "${GREEN}[CLEAN]${RESET} 已卸载当前会话中的补全代理 _$target"
    fi

    # 同步项目结构树
    if [[ -f "$ZFL_HOME/automation/sync_readme.py" ]]; then
        echo -e "正在同步项目结构树..."
        python3 "$ZFL_HOME/automation/sync_readme.py"
    fi
}

zfl() {
    load_color RED GREEN RESET

    local cmd=$1
    if [[ -z "$cmd" ]]; then
        _zfl_help
        return 0
    fi
    shift

    case "$cmd" in
        list|ls)
            _zfl_list "$@"
            ;;
        info)
            _zfl_info "$@"
            ;;
        check)
            _zfl_check "$@"
            ;;
        lint)
            _zfl_lint "$@"
            ;;
        remove|rm)
            _zfl_remove "$@"
            ;;
        -h|--help|help)
            _zfl_help
            ;;
        *)
            echo -e "${RED}[ERROR]${RESET} 未知子命令: $cmd" >&2
            echo "使用 'zfl help' 查看帮助。" >&2
            return 1
            ;;
    esac
}

# 补全代理函数
_zfl() {
    local -a commands
    commands=(
        'list:列出所有函数及其简短描述'
        'ls:列出所有函数及其简短描述'
        'info:查看特定函数的详细元数据'
        'check:检查所有函数的外部依赖项'
        'lint:对指定的函数或全部函数进行静态质量校验'
        'remove:安全删除指定的函数文件并清理桩函数'
        'rm:安全删除指定的函数文件并清理桩函数'
        'help:显示帮助信息'
    )

    if (( CURRENT == 2 )); then
        _describe -t commands 'zfl 子命令' commands
    elif (( CURRENT == 3 )); then
        case "$words[2]" in
            info|lint|remove|rm)
                local -a funcs
                local dir file fname
                for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
                    [[ -d "$dir" ]] || continue
                    for file in "$dir"/*.zsh(N); do
                        fname=$(basename "$file" .zsh)
                        funcs+=("$fname")
                    done
                done
                _describe -t funcs '可用函数' funcs
                ;;
        esac
    fi
}

