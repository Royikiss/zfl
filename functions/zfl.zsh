#? name: zfl
#? description: ZFL framework built-in command line management and self-discovery tool
#? author: Antigravity
#? version: 1.0.0
#? deps: 
#? usage: zfl <subcommand> [args]
#? example: zfl list

_zfl_parse_metadata() {
    local file=$1
    # Initialize output variables (caller must declare them local)
    func_meta_name=""
    func_meta_desc=""
    func_meta_author=""
    func_meta_version=""
    func_meta_deps=""
    func_meta_usage=""
    func_meta_example=""
    func_meta_protected=""

    [[ -f "$file" ]] || return 1

    local line content key val trimmed
    while IFS= read -r line; do
        trimmed="${line##[[:space:]]}"
        
        # Stop parsing if we leave the header comment area
        if [[ -n "$trimmed" && "$trimmed" != "#"* ]]; then
            break
        fi

        # Parse metadata lines starting with #?
        if [[ "$trimmed" == "#?"* ]]; then
            content="${trimmed#\#?}"
            content="${content##[[:space:]]}"
            if [[ "$content" == *":"* ]]; then
                key="${content%%:*}"
                val="${content#*:}"
                
                # Trim spaces
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
                    "受保护"|"protected") func_meta_protected="$val" ;;
                esac
            fi
        fi
    done < "$file"

    # Fallback to file basename
    if [[ -z "$func_meta_name" ]]; then
        func_meta_name=$(basename "$file" .zsh)
    fi
}

_zfl_help() {
    local lang=${ZFL_LANG:-${LANG%%.*}}
    if [[ "$lang" == zh* ]]; then
        cat <<'EOF'
zfl - Zsh Function Library (ZFL) 管理工具

用法:
  zfl <子命令> [参数]

可用子命令:
  list, ls         列出所有已加载的函数及其简短描述
  info <函数名>    查看特定函数的详细元数据与用法
  check            检查所有函数的外部依赖项是否已安装
  lint [函数名...] 对指定的函数或全部函数进行静态质量校验
  addfunc [名称]   交互式在 custom_functions 中创建标准的函数模板
  remove, rm <名>  安全删除指定的函数文件并清理占位符与补全
  help, -h         显示此帮助信息

示例:
  zfl list
  zfl info extract
  zfl check
  zfl lint extract
  zfl addfunc my_tool
  zfl remove weather
EOF
    else
        cat <<'EOF'
zfl - Zsh Function Library (ZFL) management tool

Usage:
  zfl <subcommand> [arguments]

Available subcommands:
  list, ls         List all loaded functions and their short descriptions
  info <name>      View detailed metadata and usage for a specific function
  check            Check if external dependencies for all functions are installed
  lint [name...]   Run static quality verification on specific or all functions
  addfunc [name]   Interactively create a standard function template in custom_functions
  remove, rm <name> Safely delete function file and clean up placeholders/completions
  help, -h         Show this help message

Examples:
  zfl list
  zfl info extract
  zfl check
  zfl lint extract
  zfl addfunc my_tool
  zfl remove weather
EOF
    fi
}

_zfl_diagnose_file() {
    local file=$1
    diag_errors=()
    diag_warnings=()

    local filename=$(basename "$file")
    local expected_name="${filename%.zsh}"
    local lang=${ZFL_LANG:-${LANG%%.*}}

    # Check 1: File Extension
    if [[ "$filename" != *.zsh ]]; then
        if [[ "$lang" == zh* ]]; then
            diag_errors+=("【后缀错误】文件名 '$filename' 扩展名必须为 '.zsh'，否则框架无法自动发现与懒加载。")
        else
            diag_errors+=("[Extension Error] File '$filename' must end with '.zsh' to be discovered by ZFL.")
        fi
    fi

    # Check 2: Header Metadata (#?)
    _zfl_parse_metadata "$file"
    if [[ -z "$func_meta_desc" ]]; then
        if [[ "$lang" == zh* ]]; then
            diag_warnings+=("【元数据缺失】缺少描述信息 (#? description: ...)。")
        else
            diag_warnings+=("[Missing Metadata] Missing description (#? description: ...).")
        fi
    fi

    if [[ -z "$func_meta_usage" ]]; then
        if [[ "$lang" == zh* ]]; then
            diag_warnings+=("【元数据缺失】缺少用法说明 (#? usage: ...)。")
        else
            diag_warnings+=("[Missing Metadata] Missing usage instruction (#? usage: ...).")
        fi
    fi

    # Check 3: Main Entry Function Mapping
    if [[ "$filename" == *.zsh ]]; then
        if ! grep -qE "(function[[:space:]]+)?${expected_name}[[:space:]]*\([[:space:]]*\)" "$file"; then
            if [[ "$lang" == zh* ]]; then
                diag_errors+=("【映射失败】文件内未声明同名主入口函数 '${expected_name}()'。")
            else
                diag_errors+=("[Mapping Failed] Main entry function '${expected_name}()' not found in file.")
            fi
        fi
    fi
}

_zfl_list() {
    load_color GREEN YELLOW CYAN RED RESET BOLD
    local lang=${ZFL_LANG:-${LANG%%.*}}

    if [[ "$lang" == zh* ]]; then
        echo -e "${BOLD}${CYAN}ZFL (Zsh Function Library) 函数与物理文件列表:${RESET}"
        echo -e "--------------------------------------------------------------------------------"
        printf "%-22s | %-4s | %s\n" "文件/函数名称" "来源" "状态与描述信息"
        echo -e "--------------------------------------------------------------------------------"
    else
        echo -e "${BOLD}${CYAN}ZFL (Zsh Function Library) Function & File List:${RESET}"
        echo -e "--------------------------------------------------------------------------------"
        printf "%-22s | %-6s | %s\n" "File/Function Name" "Source" "Status & Description"
        echo -e "--------------------------------------------------------------------------------"
    fi

    local dir file fname source_type color_source
    local func_meta_name func_meta_desc func_meta_author func_meta_version func_meta_deps func_meta_usage func_meta_example func_meta_protected
    local -a diag_errors diag_warnings
    local -a problem_details

    for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
        [[ -d "$dir" ]] || continue
        if [[ "$dir" == *"/custom_functions" ]]; then
            if [[ "$lang" == zh* ]]; then
                source_type="用户"
                local padded_source="${(r:4:)source_type}"
            else
                source_type="User"
                local padded_source="${(r:6:)source_type}"
            fi
            color_source="${YELLOW}"
        else
            if [[ "$lang" == zh* ]]; then
                source_type="社区"
                local padded_source="${(r:4:)source_type}"
            else
                source_type="System"
                local padded_source="${(r:6:)source_type}"
            fi
            color_source="${GREEN}"
        fi

        for file in "$dir"/*(N); do
            [[ -f "$file" ]] || continue
            fname=$(basename "$file")

            _zfl_diagnose_file "$file"

            local padded_name="${(r:22:)fname}"
            local colored_source="${color_source}${padded_source}${RESET}"
            local status_desc=""

            if (( ${#diag_errors[@]} > 0 )); then
                local colored_name="${BOLD}${RED}${padded_name}${RESET}"
                status_desc="${RED}[错误/无法加载] ${diag_errors[1]}${RESET}"
                local detail_msg="${BOLD}${RED}${fname}${RESET} (${file}):"
                local err warn
                for err in "${diag_errors[@]}"; do
                    detail_msg+=$'\n'"  └─ ${RED}✗ ${err}${RESET}"
                done
                for warn in "${diag_warnings[@]}"; do
                    detail_msg+=$'\n'"  └─ ${YELLOW}! ${warn}${RESET}"
                done
                problem_details+=("$detail_msg")
            elif (( ${#diag_warnings[@]} > 0 )); then
                local colored_name="${BOLD}${YELLOW}${padded_name}${RESET}"
                local desc_txt="${func_meta_desc:-暂无描述}"
                status_desc="${YELLOW}[警告: 格式欠佳] ${desc_txt}${RESET}"
                local detail_msg="${BOLD}${YELLOW}${fname}${RESET} (${file}):"
                local warn
                for warn in "${diag_warnings[@]}"; do
                    detail_msg+=$'\n'"  └─ ${YELLOW}! ${warn}${RESET}"
                done
                problem_details+=("$detail_msg")
            else
                local colored_name="${BOLD}${CYAN}${padded_name}${RESET}"
                local no_desc="No description"
                if [[ "$lang" == zh* ]]; then
                    no_desc="暂无描述"
                fi
                status_desc="${func_meta_desc:-$no_desc}"
            fi

            printf "%b | %b | %b\n" "$colored_name" "$colored_source" "$status_desc"
        done
    done
    echo -e "--------------------------------------------------------------------------------"

    if (( ${#problem_details[@]} > 0 )); then
        echo ""
        if [[ "$lang" == zh* ]]; then
            echo -e "${BOLD}${RED}⚠️  检测到不合规文件格式诊断报告 (${#problem_details[@]} 个文件需要处理):${RESET}"
            echo -e "--------------------------------------------------------------------------------"
        else
            echo -e "${BOLD}${RED}⚠️  Format Diagnostics Report (${#problem_details[@]} files need attention):${RESET}"
            echo -e "--------------------------------------------------------------------------------"
        fi
        local item
        for item in "${problem_details[@]}"; do
            echo -e "$item"
        done
        echo -e "--------------------------------------------------------------------------------"
    fi

    if [[ "$lang" == zh* ]]; then
        echo -e "提示: 使用 ${GREEN}zfl info <函数名>${RESET} 查看详细用法，使用 ${GREEN}zfl lint <函数名>${RESET} 进行深度静态检查。"
    else
        echo -e "Tip: Use ${GREEN}zfl info <func_name>${RESET} for usage, and ${GREEN}zfl lint <func_name>${RESET} for deep linting."
    fi
}

_zfl_info() {
    load_color GREEN YELLOW CYAN RED RESET BOLD
    local target=$1
    local lang=${ZFL_LANG:-${LANG%%.*}}

    if [[ -z "$target" ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 请指定函数名称。例如: zfl info weather" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Please specify function name. E.g.: zfl info weather" >&2
        fi
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
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 函数 '${target}' 不存在。" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Function '${target}' does not exist." >&2
        fi
        return 1
    fi

    local func_meta_name func_meta_desc func_meta_author func_meta_version func_meta_deps func_meta_usage func_meta_example
    _zfl_parse_metadata "$path_found"

    if [[ "$lang" == zh* ]]; then
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
    else
        echo -e "${BOLD}${CYAN}Function Details: ${target}${RESET}"
        echo -e "----------------------------------------"
        echo -e "${BOLD}File Path:      ${RESET} ${path_found}"
        echo -e "${BOLD}Description:    ${RESET} ${func_meta_desc:-None}"
        echo -e "${BOLD}Author:         ${RESET} ${func_meta_author:-Unknown}"
        echo -e "${BOLD}Version:        ${RESET} ${func_meta_version:-1.0.0}"
        echo -e "${BOLD}Dependencies:   ${RESET} ${func_meta_deps:-None}"
        echo -e "${BOLD}Usage:          ${RESET} ${func_meta_usage:-None}"
        if [[ -n "$func_meta_example" ]]; then
            echo -e "${BOLD}Example:        ${RESET} ${GREEN}${func_meta_example}${RESET}"
        fi
    fi
    echo -e "----------------------------------------"
}

_zfl_check() {
    load_color GREEN YELLOW CYAN RED RESET BOLD
    local lang=${ZFL_LANG:-${LANG%%.*}}

    if [[ "$lang" == zh* ]]; then
        echo -e "${BOLD}${CYAN}正在检测 ZFL 所有函数的系统依赖状态...${RESET}"
        echo -e "--------------------------------------------------------"
        printf "%-18s | %-8s | %s\n" "函数名称" "依赖状态" "缺失依赖"
        echo -e "--------------------------------------------------------"
    else
        echo -e "${BOLD}${CYAN}Checking ZFL dependency status for all functions...${RESET}"
        echo -e "--------------------------------------------------------"
        printf "%-18s | %-8s | %s\n" "Function Name" "Status" "Missing Deps"
        echo -e "--------------------------------------------------------"
    fi

    local dir file fname dep
    local -a deps_list
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

            deps_list=(${(s:,:)func_meta_deps})
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
    local lang=${ZFL_LANG:-${LANG%%.*}}

    local -a files_to_lint
    local target file path_found dir
    if (( $# > 0 )); then
        for target in "$@"; do
            path_found=""
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
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[ERROR]${RESET} 找不到函数或文件: $target" >&2
                else
                    echo -e "${RED}[ERROR]${RESET} Cannot find function or file: $target" >&2
                fi
                return 1
            fi
        done
    else
        for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
            [[ -d "$dir" ]] || continue
            for file in "$dir"/*.zsh(N); do
                files_to_lint+=("$file")
            done
        done
    fi

    if (( ${#files_to_lint[@]} == 0 )); then
        if [[ "$lang" == zh* ]]; then
            echo "未发现任何待扫描的文件。"
        else
            echo "No files found to scan."
        fi
        return 0
    fi

    python3 "$ZFL_HOME/python/zfl_lint.py" "${files_to_lint[@]}"
}

_zfl_read_input() {
    local prompt_msg=$1
    local var_name=$2

    [[ -n "$prompt_msg" ]] && echo -e "$prompt_msg"
    if [[ -t 0 && -t 1 ]]; then
        eval "${var_name}=''"
        vared -p "> " "$var_name"
    else
        local input_val
        read -r input_val
        eval "${var_name}=\$input_val"
    fi
}

_zfl_addfunc() {
    load_color RED GREEN YELLOW CYAN RESET BOLD
    local lang=${ZFL_LANG:-${LANG%%.*}}
    local target_name=$1

    if [[ -z "$target_name" ]]; then
        if [[ "$lang" == zh* ]]; then
            _zfl_read_input "${CYAN}► 请输入要新建的自定义函数名称${RESET}:" target_name
        else
            _zfl_read_input "${CYAN}► Please enter the name of the new custom function${RESET}:" target_name
        fi
    fi

    target_name="${target_name##[[:space:]]}"
    target_name="${target_name%%[[:space:]]}"
    target_name="${target_name%.zsh}"

    if [[ -z "$target_name" ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 函数名称不能为空！" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Function name cannot be empty!" >&2
        fi
        return 1
    fi

    if [[ ! "$target_name" =~ ^[a-zA-Z_][a-zA-Z0-9_-]*$ ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 函数名称包含非法字符 '$target_name'。必须以字母或下划线开头，仅包含字母、数字、下划线或短横线。" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Invalid function name '$target_name'. Must start with a letter/underscore and contain alphanumeric characters, underscores, or hyphens." >&2
        fi
        return 1
    fi

    local -a core_funcs=('zfl' 'aicp' 'check_update' 'add_task' 'link_skills' 'countText' 'weather' 'extract')
    if (( ${core_funcs[(Ie)$target_name]} )); then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 名称 '${target_name}' 与 ZFL 系统保留核心函数重名，禁止创建！" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Function name '${target_name}' conflicts with a ZFL core function and is prohibited!" >&2
        fi
        return 1
    fi

    local target_file="$ZFL_HOME/custom_functions/${target_name}.zsh"
    local sys_file="$ZFL_HOME/functions/${target_name}.zsh"
    if [[ -f "$target_file" || -f "$sys_file" ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 函数 '${target_name}' 已存在！" >&2
            [[ -f "$target_file" ]] && echo -e "  └─ 冲突文件: ${target_file}" >&2
            [[ -f "$sys_file" ]] && echo -e "  └─ 冲突文件: ${sys_file}" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Function '${target_name}' already exists!" >&2
            [[ -f "$target_file" ]] && echo -e "  └─ Conflicting file: ${target_file}" >&2
            [[ -f "$sys_file" ]] && echo -e "  └─ Conflicting file: ${sys_file}" >&2
        fi
        return 1
    fi

    mkdir -p "$ZFL_HOME/custom_functions" || return 1

    local func_desc func_author
    if [[ "$lang" == zh* ]]; then
        _zfl_read_input "${CYAN}► 请输入简短描述${RESET} (留空使用默认):" func_desc
        _zfl_read_input "${CYAN}► 请输入作者名称${RESET} (留空默认为当前用户):" func_author
    else
        _zfl_read_input "${CYAN}► Enter short description${RESET} (press Enter for default):" func_desc
        _zfl_read_input "${CYAN}► Enter author name${RESET} (press Enter for $USER):" func_author
    fi

    [[ -z "$func_desc" ]] && func_desc="用户自定义函数 ${target_name}"
    [[ -z "$func_author" ]] && func_author="${USER:-custom}"

    cat <<EOF > "$target_file"
#? name: ${target_name}
#? description: ${func_desc}
#? author: ${func_author}
#? version: 1.0.0
#? deps: 
#? usage: ${target_name} [args]
#? example: ${target_name}

${target_name}() {
    load_color GREEN RED YELLOW RESET BOLD
    local lang=\${ZFL_LANG:-\${LANG%%.*}}

    if [[ "\$lang" == zh* ]]; then
        echo -e "\${GREEN}[${target_name}]\${RESET} 自定义函数运行成功！"
    else
        echo -e "\${GREEN}[${target_name}]\${RESET} Custom function executed successfully!"
    fi
}

_${target_name}() {
    _default "\$@"
}
EOF

    if [[ "$lang" == zh* ]]; then
        echo -e "${GREEN}[SUCCESS]${RESET} 已成功创建标准函数模板: ${BOLD}${target_file}${RESET}"
        echo -e "提示: 已在当前会话中即时注册桩函数。可以使用 ${GREEN}zfl lint ${target_name}${RESET} 检测代码规范。"
    else
        echo -e "${GREEN}[SUCCESS]${RESET} Standard function template created: ${BOLD}${target_file}${RESET}"
        echo -e "Tip: Lazy loading stub registered for active session. Use ${GREEN}zfl lint ${target_name}${RESET} to check code quality."
    fi

    eval "${target_name}() { lazy_load_functions ${target_name} \"${target_file}\" \"\$@\"; }"
    eval "_${target_name}() { unfunction _${target_name} 2>/dev/null; source \"${target_file}\"; if whence -f _${target_name} >/dev/null; then _${target_name} \"\$@\"; else _default \"\$@\"; fi }"
    if whence compdef >/dev/null; then
        compdef "_${target_name}" "${target_name}"
    fi

    if [[ -f "$ZFL_HOME/automation/sync_readme.py" ]]; then
        python3 "$ZFL_HOME/automation/sync_readme.py" >/dev/null 2>&1
    fi
}

_zfl_remove() {
    load_color RED GREEN YELLOW RESET BOLD
    local target=$1
    local lang=${ZFL_LANG:-${LANG%%.*}}

    if [[ -z "$target" ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 请指定要删除的函数名称。例如: zfl remove weather" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Please specify function name. E.g.: zfl remove weather" >&2
        fi
        return 1
    fi

    # Protect system core functions (hardcoded whitelist)
    local -a core_funcs=('zfl' 'aicp' 'check_update' 'add_task' 'link_skills' 'countText' 'weather' 'extract')
    if (( ${core_funcs[(Ie)$target]} )); then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 函数 '${target}' 是 ZFL 的核心/内置系统函数，已被系统写死保护，禁止删除！" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Function '${target}' is a ZFL core/system function and is protected from deletion!" >&2
        fi
        return 1
    fi

    local file path_found="" dir
    for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
        if [[ -f "$dir/${target}.zsh" ]]; then
            path_found="$dir/${target}.zsh"
            break
        fi
    done

    # Check metadata protected flag
    if [[ -n "$path_found" ]]; then
        _zfl_parse_metadata "$path_found"
        if [[ "$func_meta_protected" == "true" ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[ERROR]${RESET} 函数 '${target}' 的元数据被标记为受保护 (#? protected: true)，禁止删除！" >&2
            else
                echo -e "${RED}[ERROR]${RESET} Function '${target}' is marked as protected in metadata (#? protected: true)!" >&2
            fi
            return 1
        fi
    fi

    if [[ -z "$path_found" ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 函数 '${target}' 不存在。" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Function '${target}' does not exist." >&2
        fi
        return 1
    fi

    if [[ "$lang" == zh* ]]; then
        echo -e "${YELLOW}确定要删除函数文件 ${BOLD}${path_found}${RESET}${YELLOW} 吗？ [y/N]${RESET}"
    else
        echo -e "${YELLOW}Are you sure you want to delete function file ${BOLD}${path_found}${RESET}${YELLOW}? [y/N]${RESET}"
    fi

    local confirm
    read -r confirm
    if [[ "$confirm" != [yY] && "$confirm" != [yY][eE][sS] ]]; then
        if [[ "$lang" == zh* ]]; then
            echo "已取消删除。"
        else
            echo "Deletion cancelled."
        fi
        return 0
    fi

    rm "$path_found" || {
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[ERROR]${RESET} 无法删除文件 ${path_found}。" >&2
        else
            echo -e "${RED}[ERROR]${RESET} Failed to delete file ${path_found}." >&2
        fi
        return 1
    }

    if [[ "$lang" == zh* ]]; then
        echo -e "${GREEN}[SUCCESS]${RESET} 已删除函数文件: ${path_found}"
    else
        echo -e "${GREEN}[SUCCESS]${RESET} Deleted function file: ${path_found}"
    fi

    # Detect and delete documentation
    local doc_file="$ZFL_HOME/docs/${target}.md"
    local confirm_doc
    if [[ -f "$doc_file" ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${YELLOW}检测到该函数关联的技术文档 ${BOLD}${doc_file}${RESET}${YELLOW}，是否一并删除？ [y/N]${RESET}"
        else
            echo -e "${YELLOW}Detected associated documentation ${BOLD}${doc_file}${RESET}${YELLOW}, delete it as well? [y/N]${RESET}"
        fi
        read -r confirm_doc
        if [[ "$confirm_doc" == [yY] || "$confirm_doc" == [yY][eE][sS] ]]; then
            rm "$doc_file" || {
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[WARNING]${RESET} 无法删除文档文件 ${doc_file}。" >&2
                else
                    echo -e "${RED}[WARNING]${RESET} Failed to delete documentation file ${doc_file}." >&2
                fi
            }
            if [[ "$lang" == zh* ]]; then
                echo -e "${GREEN}[SUCCESS]${RESET} 已删除文档文件: ${doc_file}"
            else
                echo -e "${GREEN}[SUCCESS]${RESET} Deleted documentation file: ${doc_file}"
            fi
        else
            if [[ "$lang" == zh* ]]; then
                echo "保留文档文件。"
            else
                echo "Documentation file kept."
            fi
        fi
    fi

    # Clean up function and completion from active session
    if whence -f "$target" >/dev/null; then
        unfunction "$target" 2>/dev/null
        if [[ "$lang" == zh* ]]; then
            echo -e "${GREEN}[CLEAN]${RESET} 已卸载当前会话中的函数 ${target}"
        else
            echo -e "${GREEN}[CLEAN]${RESET} Unloaded function ${target} from current session"
        fi
    fi
    if whence -f "_$target" >/dev/null; then
        unfunction "_$target" 2>/dev/null
        if [[ "$lang" == zh* ]]; then
            echo -e "${GREEN}[CLEAN]${RESET} 已卸载当前会话中的补全代理 _$target"
        else
            echo -e "${GREEN}[CLEAN]${RESET} Unloaded completion agent _$target from current session"
        fi
    fi

    # Sync project structure
    if [[ -f "$ZFL_HOME/automation/sync_readme.py" ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "正在同步项目结构树..."
        else
            echo -e "Syncing project structure tree..."
        fi
        python3 "$ZFL_HOME/automation/sync_readme.py"
    fi
}

zfl() {
    load_color RED GREEN RESET
    local lang=${ZFL_LANG:-${LANG%%.*}}

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
        addfunc)
            _zfl_addfunc "$@"
            ;;
        remove|rm)
            _zfl_remove "$@"
            ;;
        -h|--help|help)
            _zfl_help
            ;;
        *)
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[ERROR]${RESET} 未知子命令: $cmd" >&2
                echo "使用 'zfl help' 查看帮助。" >&2
            else
                echo -e "${RED}[ERROR]${RESET} Unknown subcommand: $cmd" >&2
                echo "Use 'zfl help' to view help." >&2
            fi
            return 1
            ;;
    esac
}

# Completion agent function
_zfl() {
    local -a commands
    local lang=${ZFL_LANG:-${LANG%%.*}}

    if [[ "$lang" == zh* ]]; then
        commands=(
            'list:列出所有函数及其简短描述'
            'ls:列出所有函数及其简短描述'
            'info:查看特定函数的详细元数据'
            'check:检查所有函数的外部依赖项'
            'lint:对指定的函数或全部函数进行静态质量校验'
            'addfunc:交互式在 custom_functions 中创建标准的函数模板'
            'remove:安全删除指定的函数文件并清理桩函数'
            'rm:安全删除指定的函数文件并清理桩函数'
            'help:显示帮助信息'
        )
    else
        commands=(
            'list:List all functions and their short descriptions'
            'ls:List all functions and their short descriptions'
            'info:View detailed metadata for a specific function'
            'check:Check external dependencies for all functions'
            'lint:Run static quality verification on specific or all functions'
            'addfunc:Interactively create a standard function template in custom_functions'
            'remove:Safely delete function file and clean up placeholders'
            'rm:Safely delete function file and clean up placeholders'
            'help:Show help information'
        )
    fi

    if (( CURRENT == 2 )); then
        local desc_msg="zfl subcommand"
        if [[ "$lang" == zh* ]]; then
            desc_msg="zfl 子命令"
        fi
        _describe -t commands "$desc_msg" commands
    elif (( CURRENT == 3 )); then
        case "$words[2]" in
            info|lint)
                local -a funcs
                local dir file fname
                for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
                    [[ -d "$dir" ]] || continue
                    for file in "$dir"/*.zsh(N); do
                        fname=$(basename "$file" .zsh)
                        funcs+=("$fname")
                    done
                done
                local desc_func="available functions"
                if [[ "$lang" == zh* ]]; then
                    desc_func="可用函数"
                fi
                _describe -t funcs "$desc_func" funcs
                ;;
            remove|rm)
                local -a removable_funcs
                local -a core_funcs=('zfl' 'aicp' 'check_update' 'add_task' 'link_skills' 'countText' 'weather' 'extract')
                local dir file fname
                for dir in "$ZFL_HOME/functions" "$ZFL_HOME/custom_functions"; do
                    [[ -d "$dir" ]] || continue
                    for file in "$dir"/*.zsh(N); do
                        fname=$(basename "$file" .zsh)
                        if (( ! ${core_funcs[(Ie)$fname]} )); then
                            _zfl_parse_metadata "$file"
                            if [[ "$func_meta_protected" != "true" ]]; then
                                removable_funcs+=("$fname")
                            fi
                        fi
                    done
                done
                local desc_removable="removable functions"
                if [[ "$lang" == zh* ]]; then
                    desc_removable="可安全删除的函数"
                fi
                _describe -t removable_funcs "$desc_removable" removable_funcs
                ;;
        esac
    fi
}


