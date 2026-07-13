#? name: link_skills
#? description: Selectively symlink skills from ~/.agents/skills/ into .agents/skills/ of the current project
#? author: Royi
#? version: 1.0.0
#? deps: fzf, python3
#? usage: link_skills [options] [skill_name/group_name...]
#? example: link_skills startup

_link_skills_help() {
    local lang=${ZFL_LANG:-${LANG%%.*}}
    if [[ "$lang" == zh* ]]; then
        cat <<'EOF'
link_skills - 选择性地将 ~/.agents/skills 中的 skills 软链接到当前目录的 .agents/skills/ 中

用法:
  link_skills [选项] [技能名称...]
  link_skills -s / --group-set <分组名称> [--ordered] <技能列表...>
  link_skills -r / --group-rm <分组名称>
  link_skills -l / --group-list
  link_skills -v / --view / view

示例:
  link_skills caveman diagnose       # 链接指定的 skills
  link_skills startup               # 链接 startup 分组下的所有 skills
  link_skills                       # 交互式选择要链接的 skills (使用 fzf)

选项:
  -h, --help                        显示帮助信息
  -s, --group-set <分组名> [--ordered] <技能...>
                                    创建或修改技能分组，加 --ordered 则将技能列表顺序标记为推荐调用顺序
  -r, --group-rm <分组名>           删除指定的技能分组
  -l, --group-list                  列出当前定义的所有技能分组
  -v, --view / view                 直接查看当前项目底下的已连接技能及其中文翻译

说明:
  - 以符号链接（ln -s）的方式将 ~/.agents/skills/ 中的 skill 链接到当前目录的 .agents/skills/ 下。
  - 这样，您只需在 ~/.agents/skills 中修改内容，所有项目的 skill 都会自动同步。
  - 有序分组（ordered）会在 fzf 预览和 --group-list 中显示推荐调用序号（①②③...）。
EOF
    else
        cat <<'EOF'
link_skills - Selectively symlink skills from ~/.agents/skills into .agents/skills/ of the current directory

Usage:
  link_skills [options] [skill_name...]
  link_skills -s / --group-set <group_name> [--ordered] <skills_list...>
  link_skills -r / --group-rm <group_name>
  link_skills -l / --group-list
  link_skills -v / --view / view

Examples:
  link_skills caveman diagnose       # Link specified skills
  link_skills startup               # Link all skills in 'startup' group
  link_skills                       # Interactive selection of skills (uses fzf)

Options:
  -h, --help                        Show help information
  -s, --group-set <grp> [--ordered] <skills...>
                                    Create or modify a skill group; --ordered marks the list order
                                    as the recommended call sequence
  -r, --group-rm <grp>              Delete a specified skill group
  -l, --group-list                  List all currently defined skill groups
  -v, --view / view                 View connected skills of the current project with Chinese translation

Description:
  - Links skills from ~/.agents/skills/ to the current directory under .agents/skills/ using symlinks (ln -s).
  - This way, you only need to modify skills in ~/.agents/skills/, and all project skills will sync automatically.
  - Ordered groups show recommended call sequence numbers (①②③...) in fzf preview and --group-list output.
EOF
    fi
}

_link_skills() {
    local -a available_skills available_groups options
    available_skills=( $HOME/.agents/skills/*(/N:t) )
    local lang=${ZFL_LANG:-${LANG%%.*}}
    
    if (( $+commands[python3] )); then
        available_groups=( ${(f)"$(python3 "$ZFL_HOME/python/resolve_skills.py" --list-groups 2>/dev/null)"} )
    fi

    local -a subcommands
    if [[ "$lang" == zh* ]]; then
        options=(
            '-h[显示帮助信息]'
            '--help[显示帮助信息]'
            '-s[创建或修改技能分组]'
            '--group-set[创建或修改技能分组]'
            '--ordered[将技能列表顺序标记为推荐调用顺序（与 -s 搭配使用）]'
            '-r[删除指定的技能分组]'
            '--group-rm[删除指定的技能分组]'
            '-l[列出当前定义的所有技能分组]'
            '--group-list[列出当前定义的所有技能分组]'
            '-v[查看当前项目已连接的技能及其中文翻译]'
            '--view[查看当前项目已连接的技能及其中文翻译]'
        )
        subcommands=('view:查看当前项目已连接的技能及其中文翻译')
    else
        options=(
            '-h[Show help information]'
            '--help[Show help information]'
            '-s[Create or modify a skill group]'
            '--group-set[Create or modify a skill group]'
            '--ordered[Mark skills list order as recommended call sequence (use with -s)]'
            '-r[Delete a specified skill group]'
            '--group-rm[Delete a specified skill group]'
            '-l[List all currently defined skill groups]'
            '--group-list[List all currently defined skill groups]'
            '-v[View connected skills of the current project with Chinese translation]'
            '--view[View connected skills of the current project with Chinese translation]'
        )
        subcommands=('view:View connected skills of the current project')
    fi

    if [[ "$words[CURRENT]" == -* ]]; then
        _describe -t options 'options' options
    else
        if (( CURRENT == 2 )); then
            _describe -t options 'options' options
            _describe -t subcommands 'subcommands' subcommands
        fi
        _describe -t available_groups 'available groups' available_groups
        _describe -t available_skills 'available skills' available_skills
    fi
}

link_skills() {
    zfl_require python3 || return 1
    load_color GREEN YELLOW RED RESET
    local lang=${ZFL_LANG:-${LANG%%.*}}

    local -a available_skills skills_to_link group_skills
    local opt_set=0 opt_rm=0 opt_list=0 opt_view=0 group_name selected line dest_dir skill src dest

    available_skills=( $HOME/.agents/skills/*(/N:t) )

    if (( ${#available_skills[@]} == 0 )); then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[link_skills] 错误: ~/.agents/skills/ 目录下没有找到任何 skill。${RESET}" >&2
        else
            echo -e "${RED}[link_skills] Error: No skills found under ~/.agents/skills/.${RESET}" >&2
        fi
        return 1
    fi

    while (( $# > 0 )); do
        case "$1" in
            -h|--help)
                _link_skills_help
                return 0
                ;;
            -v|--view|view)
                opt_view=1
                shift
                break
                ;;
            -s|--group-set)
                opt_set=1
                shift
                if (( $# < 2 )); then
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${RED}[link_skills] 错误: --group-set 需要指定分组名称和至少一个技能名。${RESET}" >&2
                    else
                        echo -e "${RED}[link_skills] Error: --group-set requires a group name and at least one skill name.${RESET}" >&2
                    fi
                    return 1
                fi
                group_name="$1"
                shift
                # Collect optional --ordered flag and skills
                local opt_ordered_flag=()
                local group_skills_raw=()
                while (( $# > 0 )); do
                    if [[ "$1" == "--ordered" ]]; then
                        opt_ordered_flag=("--ordered")
                    else
                        group_skills_raw+=("$1")
                    fi
                    shift
                done
                group_skills=( "${opt_ordered_flag[@]}" "${group_skills_raw[@]}" )
                break
                ;;
            -r|--group-rm)
                opt_rm=1
                shift
                if (( $# == 0 )); then
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${RED}[link_skills] 错误: --group-rm 需要指定分组名称。${RESET}" >&2
                    else
                        echo -e "${RED}[link_skills] Error: --group-rm requires a group name.${RESET}" >&2
                    fi
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
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[link_skills] 未知参数: $1${RESET}" >&2
                    echo "请使用 --help 查看用法。" >&2
                else
                    echo -e "${RED}[link_skills] Unknown option: $1${RESET}" >&2
                    echo "Please use --help to view usage." >&2
                fi
                return 2
                ;;
            *)
                skills_to_link+=("$1")
                shift
                ;;
        esac
    done

    # Handle group management instructions
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

    if (( opt_view )); then
        python3 "$ZFL_HOME/python/resolve_skills.py" --view-connected
        return $?
    fi

    # Interactive selection (using fzf) if no arguments provided
    if (( ${#skills_to_link[@]} == 0 )); then
        if (( $+commands[fzf] )); then
            local prompt_msg
            if [[ "$lang" == zh* ]]; then
                prompt_msg="选择要链接的 Skill/分组 (空格多选，ctrl-g:创建/更新组，ctrl-d:删除组，ctrl-t:重新翻译，ctrl-v:展开/收起预览，Enter确认): "
            else
                prompt_msg="Select skills/groups to link (Space to multi-select, ctrl-g:create/update group, ctrl-d:delete group, ctrl-t:re-translate, ctrl-v:toggle-expand, Enter to confirm): "
            fi
            selected=$(python3 "$ZFL_HOME/python/list_skills_fzf.py" | fzf -m \
                --bind "space:toggle" \
                --bind 'ctrl-g:execute(python3 "'"$ZFL_HOME"'/python/resolve_skills.py" --interactive-set {+1})+reload(python3 "'"$ZFL_HOME"'/python/list_skills_fzf.py")' \
                --bind 'ctrl-d:execute(python3 "'"$ZFL_HOME"'/python/resolve_skills.py" --interactive-rm {1})+reload(python3 "'"$ZFL_HOME"'/python/list_skills_fzf.py")' \
                --bind 'ctrl-t:execute-silent(python3 "'"$ZFL_HOME"'/python/preview_skill.py" --force-translate {1})+reload(python3 "'"$ZFL_HOME"'/python/list_skills_fzf.py")' \
                --bind 'ctrl-v:change-preview-window(right:90%:wrap|right:50%:wrap)+refresh-preview' \
                --bind 'preview-scroll-up:preview-up,preview-scroll-down:preview-down' \
                --bind 'ctrl-j:preview-down,ctrl-k:preview-up' \
                --preview 'python3 "'"$ZFL_HOME"'/python/preview_skill.py" {1}' \
                --preview-window='right:50%:wrap' \
                --prompt="$prompt_msg")
            [[ -z "$selected" ]] && return 0
            
            for line in ${(f)selected}; do
                skills_to_link+=("${line%% *}")
            done
        else
            if [[ "$lang" == zh* ]]; then
                echo -e "${YELLOW}[link_skills] fzf 未安装，无法进行交互式选择。${RESET}"
                echo -e "可用 skills 为: ${GREEN}${available_skills[*]}${RESET}"
                echo "请直接指定参数运行，例如: link_skills ${available_skills[1]}"
            else
                echo -e "${YELLOW}[link_skills] fzf is not installed, cannot perform interactive selection.${RESET}"
                echo -e "Available skills: ${GREEN}${available_skills[*]}${RESET}"
                echo "Please run with arguments, e.g.: link_skills ${available_skills[1]}"
            fi
            return 1
        fi
    fi

    # Expand group names and skill names via python script
    skills_to_link=( ${(f)"$(python3 "$ZFL_HOME/python/resolve_skills.py" "${skills_to_link[@]}")"} )
    skills_to_link=( "${(@)skills_to_link:#}" ) # Filter empty entries

    if (( ${#skills_to_link[@]} == 0 )); then
        if [[ "$lang" == zh* ]]; then
            echo -e "${YELLOW}[link_skills] 没有需要链接的技能。${RESET}"
        else
            echo -e "${YELLOW}[link_skills] No skills to link.${RESET}"
        fi
        return 0
    fi

    # Determine target directory
    dest_dir="./.agents/skills"
    mkdir -p "$dest_dir" || {
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[link_skills] 错误: 无法创建目标目录 $dest_dir${RESET}" >&2
        else
            echo -e "${RED}[link_skills] Error: Cannot create target directory $dest_dir${RESET}" >&2
        fi
        return 1
    }

    # Perform symlinks
    for skill in "${skills_to_link[@]}"; do
        src="$HOME/.agents/skills/$skill"
        dest="$dest_dir/$skill"

        # Check if source directory exists
        if [[ ! -d "$src" ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[link_skills] 错误: 源 skill '$skill' 不存在 ($src)${RESET}" >&2
            else
                echo -e "${RED}[link_skills] Error: Source skill '$skill' does not exist ($src)${RESET}" >&2
            fi
            continue
        fi

        # Check target position
        if [[ -e "$dest" || -L "$dest" ]]; then
            if [[ -L "$dest" ]]; then
                if [[ "$lang" == zh* ]]; then
                    echo -e "${YELLOW}[link_skills] 正在覆盖已有的软链接: $skill -> $dest${RESET}"
                else
                    echo -e "${YELLOW}[link_skills] Overwriting existing symlink: $skill -> $dest${RESET}"
                fi
                ln -sfn "$src" "$dest"
            else
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[link_skills] 警告: 目标 '$dest' 已存在且不是软链接，跳过。${RESET}" >&2
                else
                    echo -e "${RED}[link_skills] Warning: Target '$dest' already exists and is not a symlink, skipping.${RESET}" >&2
                fi
            fi
        else
            if [[ "$lang" == zh* ]]; then
                echo -e "${GREEN}[link_skills] 建立软链接: $skill -> $dest${RESET}"
            else
                echo -e "${GREEN}[link_skills] Creating symlink: $skill -> $dest${RESET}"
            fi
            ln -sfn "$src" "$dest"
        fi
    done

    if [[ "$lang" == zh* ]]; then
        echo -e "${GREEN}[link_skills] 完成!${RESET}"
    else
        echo -e "${GREEN}[link_skills] Done!${RESET}"
    fi
}


