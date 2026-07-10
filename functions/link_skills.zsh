#? 名称: link_skills
#? 描述: 选择性地将 ~/.agents/skills 中的技能软链接到当前项目的 .agents/skills/ 中
#? 作者: Royi
#? 版本: 1.0.0
#? 依赖: fzf, python3
#? 用法: link_skills [选项] [技能名称/分组名称...]
#? 示例: link_skills startup

_link_skills_help() {
    cat <<'EOF'
link_skills - 选择性地将 ~/.agents/skills 中的 skills 软链接到当前目录的 .agents/skills/ 中

用法:
  link_skills [选项] [技能名称...]
  link_skills -s / --group-set <分组名称> <技能列表...>
  link_skills -r / --group-rm <分组名称>
  link_skills -l / --group-list

示例:
  link_skills caveman diagnose       # 链接指定的 skills
  link_skills startup               # 链接 startup 分组下的所有 skills
  link_skills                       # 交互式选择要链接的 skills (使用 fzf)

选项:
  -h, --help                        显示帮助信息
  -s, --group-set <分组名> <技能...> 创建或修改技能分组
  -r, --group-rm <分组名>           删除指定的技能分组
  -l, --group-list                  列出当前定义的所有技能分组

说明:
  - 以符号链接（ln -s）的方式将 ~/.agents/skills/ 中的 skill 链接到当前目录的 .agents/skills/ 下。
  - 这样，您只需在 ~/.agents/skills 中修改内容，所有项目的 skill 都会自动同步。
EOF
}

_link_skills() {
    local -a available_skills available_groups options
    available_skills=( $HOME/.agents/skills/*(/N:t) )
    
    if (( $+commands[python3] )); then
        available_groups=( ${(f)"$(python3 "$ZFL_HOME/python/resolve_skills.py" --list-groups 2>/dev/null)"} )
    fi

    options=(
        '-h[显示帮助信息]'
        '--help[显示帮助信息]'
        '-s[创建或修改技能分组]'
        '--group-set[创建或修改技能分组]'
        '-r[删除指定的技能分组]'
        '--group-rm[删除指定的技能分组]'
        '-l[列出当前定义的所有技能分组]'
        '--group-list[列出当前定义的所有技能分组]'
    )

    if [[ "$words[CURRENT]" == -* ]]; then
        _describe -t options 'options' options
    else
        if (( CURRENT == 2 )); then
            _describe -t options 'options' options
        fi
        _describe -t available_groups 'available groups' available_groups
        _describe -t available_skills 'available skills' available_skills
    fi
}

link_skills() {
    zfl_require python3 || return 1
    load_color GREEN YELLOW RED RESET

    local -a available_skills skills_to_link group_skills
    local opt_set=0 opt_rm=0 opt_list=0 group_name selected line dest_dir skill src dest

    available_skills=( $HOME/.agents/skills/*(/N:t) )

    if (( ${#available_skills[@]} == 0 )); then
        echo -e "${RED}[link_skills] 错误: ~/.agents/skills/ 目录下没有找到任何 skill。${RESET}" >&2
        return 1
    fi

    while (( $# > 0 )); do
        case "$1" in
            -h|--help)
                _link_skills_help
                return 0
                ;;
            -s|--group-set)
                opt_set=1
                shift
                if (( $# < 2 )); then
                    echo -e "${RED}[link_skills] 错误: --group-set 需要指定分组名称和至少一个技能名。${RESET}" >&2
                    return 1
                fi
                group_name="$1"
                shift
                group_skills=( "$@" )
                break
                ;;
            -r|--group-rm)
                opt_rm=1
                shift
                if (( $# == 0 )); then
                    echo -e "${RED}[link_skills] 错误: --group-rm 需要指定分组名称。${RESET}" >&2
                    return 1
                fi
                group_name="$1"
                shift
                break
                ;;
            -l|--group-list)
                opt_list=1
                shift
                break
                ;;
            -*)
                echo -e "${RED}[link_skills] 未知参数: $1${RESET}" >&2
                echo "请使用 --help 查看用法。" >&2
                return 2
                ;;
            *)
                skills_to_link+=("$1")
                shift
                ;;
        esac
    done

    # 处理分组管理指令
    if (( opt_list )); then
        python3 "$ZFL_HOME/python/resolve_skills.py" --list-groups-detailed
        return $?
    fi

    if (( opt_rm )); then
        python3 "$ZFL_HOME/python/resolve_skills.py" --rm-group "$group_name"
        return $?
    fi

    if (( opt_set )); then
        python3 "$ZFL_HOME/python/resolve_skills.py" --set-group "$group_name" "${group_skills[@]}"
        return $?
    fi

    # 如果没有指定任何参数，进入交互式选择 (使用 fzf)
    if (( ${#skills_to_link[@]} == 0 )); then
        if (( $+commands[fzf] )); then
            selected=$(python3 "$ZFL_HOME/python/list_skills_fzf.py" | fzf -m \
                --bind "space:toggle" \
                --bind 'ctrl-g:execute(python3 "'"$ZFL_HOME"'/python/resolve_skills.py" --interactive-set {+1})+reload(python3 "'"$ZFL_HOME"'/python/list_skills_fzf.py")' \
                --bind 'ctrl-d:execute(python3 "'"$ZFL_HOME"'/python/resolve_skills.py" --interactive-rm {1})+reload(python3 "'"$ZFL_HOME"'/python/list_skills_fzf.py")' \
                --preview 'python3 "'"$ZFL_HOME"'/python/preview_skill.py" {1}' \
                --preview-window='right:50%:wrap' \
                --prompt="选择要链接的 Skill/分组 (空格多选，ctrl-g:创建/更新组，ctrl-d:删除组，Enter确认): ")
            [[ -z "$selected" ]] && return 0
            
            for line in ${(f)selected}; do
                skills_to_link+=("${line%% *}")
            done
        else
            echo -e "${YELLOW}[link_skills] fzf 未安装，无法进行交互式选择。${RESET}"
            echo -e "可用 skills 为: ${GREEN}${available_skills[*]}${RESET}"
            echo "请直接指定参数运行，例如: link_skills ${available_skills[1]}"
            return 1
        fi
    fi

    # 通过 python 脚本解析并展开分组和技能名，并去重
    skills_to_link=( ${(f)"$(python3 "$ZFL_HOME/python/resolve_skills.py" "${skills_to_link[@]}")"} )
    skills_to_link=( "${(@)skills_to_link:#}" ) # 过滤空项

    if (( ${#skills_to_link[@]} == 0 )); then
        echo -e "${YELLOW}[link_skills] 没有需要链接的技能。${RESET}"
        return 0
    fi

    # 确定目标目录
    dest_dir="./.agents/skills"
    mkdir -p "$dest_dir" || {
        echo -e "${RED}[link_skills] 错误: 无法创建目标目录 $dest_dir${RESET}" >&2
        return 1
    }

    # 执行软链接
    for skill in "${skills_to_link[@]}"; do
        src="$HOME/.agents/skills/$skill"
        dest="$dest_dir/$skill"

        # 检查源目录是否存在
        if [[ ! -d "$src" ]]; then
            echo -e "${RED}[link_skills] 错误: 源 skill '$skill' 不存在 ($src)${RESET}" >&2
            continue
        fi

        # 检查目标位置
        if [[ -e "$dest" || -L "$dest" ]]; then
            if [[ -L "$dest" ]]; then
                echo -e "${YELLOW}[link_skills] 正在覆盖已有的软链接: $skill -> $dest${RESET}"
                ln -sfn "$src" "$dest"
            else
                echo -e "${RED}[link_skills] 警告: 目标 '$dest' 已存在且不是软链接，跳过。${RESET}" >&2
            fi
        else
            echo -e "${GREEN}[link_skills] 建立软链接: $skill -> $dest${RESET}"
            ln -sfn "$src" "$dest"
        fi
    done

    echo -e "${GREEN}[link_skills] 完成!${RESET}"
}

