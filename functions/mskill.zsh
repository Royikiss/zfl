#? name: mskill
#? description: Manage, install, discover, package, update, and selectively link AI Agent skills
#? author: Royi
#? version: 1.2.0
#? deps: python3
#? usage: mskill [options] [skill_name/group_name...]
#? example: mskill -i anthropics/anthropic-quickstarts

_mskill_help() {
    local lang=${ZFL_LANG:-${LANG%%.*}}
    if [[ "$lang" == zh* ]]; then
        cat <<'EOF'
mskill (Manage Skill) - AI Agent 技能全生命周期管理工具

用法:
  mskill [选项] [技能名称/分组名称...]
  mskill -i / --install <仓库地址/简写> [技能名...]
  mskill -u / --update [技能名...]
  mskill --update-all
  mskill --status
  mskill -d / --uninstall <技能名>
  mskill -s / --group-set <分组名称> [--ordered] <技能列表...>
  mskill -r / --group-rm <分组名称>
  mskill -l / --group-list
  mskill -v / --view / view

常用示例:
  mskill                            # 交互式选择、管理与软链接技能 (使用 fzf)
  mskill -i anthropics/quickstarts  # 从 GitHub 仓库自动识别并打包下载技能 (多技能支持自动分组引导)
  mskill -u video-generator         # 检查并更新指定技能至最新版本
  mskill --update-all               # 一键更新所有已追踪的远程技能
  mskill --status                   # 查看已安装技能的版本 Commit 与来源
  mskill startup                    # 批量链接 startup 分组下的所有技能到当前项目
  mskill caveman diagnose           # 链接指定的技能到当前项目

选项:
  -h, --help                        显示帮助信息
  -i, --install <url/repo> [名...]  安装技能（以 SKILL.md 为锚点自包含打包，多技能自动引导分组）
  -u, --update [技能名...]          更新指定的技能（分组关系自动 100% 保持不变）
  --update-all                      更新所有已安装的远程技能
  --status                          查看技能的版本、来源仓库与更新状态
  -d, --uninstall <技能名>          卸载指定的技能包并清理元数据
  -s, --group-set <组名> [--ordered] <技能...>
                                    创建或修改技能分组，加 --ordered 则将顺序标记为推荐调用顺序
  -r, --group-rm <组名>             删除指定的技能分组
  -l, --group-list                  列出当前定义的所有技能分组
  -v, --view / view                 直接查看当前项目底下的已连接技能及其中文翻译

说明:
  - 下载多技能数据包时会自动提示是否快速创建分组，方便下次一键批量引用。
  - 技能更新仅同步技能文件与版本，绝对不会影响分组配置（skills_groups.json）。
  - 项目端使用符号链接（ln -s），全局技能一旦更新，项目内即时同步生效。
EOF
    else
        cat <<'EOF'
mskill (Manage Skill) - Full Lifecycle Manager for AI Agent Skills

Usage:
  mskill [options] [skill_name/group_name...]
  mskill -i / --install <repo_url_or_shorthand> [skill_name...]
  mskill -u / --update [skill_name...]
  mskill --update-all
  mskill --status
  mskill -d / --uninstall <skill_name>
  mskill -s / --group-set <group_name> [--ordered] <skills_list...>
  mskill -r / --group-rm <group_name>
  mskill -l / --group-list
  mskill -v / --view / view

Examples:
  mskill                            # Interactive selection and management (uses fzf)
  mskill -i anthropics/quickstarts  # Auto-discover, package and download from GitHub
  mskill -u video-generator         # Check and update specified skill
  mskill --update-all               # Update all tracked remote skills
  mskill --status                   # View versions, commits, and source repositories
  mskill startup                    # Link all skills in 'startup' group into current project
  mskill caveman diagnose           # Link specified skills into current project

Options:
  -h, --help                        Show help information
  -i, --install <url/repo> [name]   Install skill (self-contained packaging, auto-groups multi-skill packages)
  -u, --update [skill_name...]      Update specified skills (group mappings preserved 100%)
  --update-all                      Update all tracked remote skills
  --status                          View version commit and source repository status
  -d, --uninstall <skill_name>      Uninstall specified skill and clean manifest
  -s, --group-set <grp> [--ordered] <skills...>
                                    Create or modify a skill group; --ordered marks sequence
  -r, --group-rm <grp>              Delete a specified skill group
  -l, --group-list                  List all currently defined skill groups
  -v, --view / view                 View connected skills of the current project

Description:
  - When downloading multi-skill packages, automatically prompts to create a skill group for easy batch linking.
  - Skill updates only sync files and commits; skill groups remain 100% untouched.
  - Project symlinks (ln -s) ensure updates reflect in projects instantly in real-time.
EOF
    fi
}

_mskill() {
    local -a available_skills available_groups options
    available_skills=( $HOME/.agents/skills/*(/N:t) )
    local lang=${ZFL_LANG:-${LANG%%.*}}

    if (( $+commands[python3] )); then
        available_groups=( ${(f)"$(python3 "$ZFL_HOME/python/resolve_skills.py" --list-groups 2>/dev/null)"} )
    fi

    if [[ "$lang" == zh* ]]; then
        options=(
            '-h:显示帮助信息'
            '--help:显示帮助信息'
            '-i:安装/下载技能包 (支持 GitHub 简写/完整 URL/目录直链)'
            '--install:安装/下载技能包 (支持 GitHub 简写/完整 URL/目录直链)'
            '-u:检查并更新指定技能'
            '--update:检查并更新指定技能'
            '--update-all:一键更新所有已追踪的远程技能'
            '--status:查看技能版本 Commit 与来源状态'
            '-d:卸载指定的技能包并清理元数据'
            '--uninstall:卸载指定的技能包并清理元数据'
            '--remove:卸载指定的技能包并清理元数据'
            '-s:创建或修改技能分组'
            '--group-set:创建或修改技能分组'
            '--ordered:标记技能列表顺序为推荐调用顺序 (与 -s 搭配使用)'
            '-r:删除指定的技能分组'
            '--group-rm:删除指定的技能分组'
            '-l:列出当前定义的所有技能分组'
            '--group-list:列出当前定义的所有技能分组'
            '-v:查看当前项目已连接的技能及其中文翻译'
            '--view:查看当前项目已连接的技能及其中文翻译'
        )
    else
        options=(
            '-h:Show help information'
            '--help:Show help information'
            '-i:Install skill package (supports GitHub shorthand/URL/path)'
            '--install:Install skill package (supports GitHub shorthand/URL/path)'
            '-u:Check and update specified skill'
            '--update:Check and update specified skill'
            '--update-all:Update all tracked remote skills'
            '--status:View skill version commit and source status'
            '-d:Uninstall specified skill package'
            '--uninstall:Uninstall specified skill package'
            '--remove:Uninstall specified skill package'
            '-s:Create or modify a skill group'
            '--group-set:Create or modify a skill group'
            '--ordered:Mark skills sequence as recommended call order'
            '-r:Delete a specified skill group'
            '--group-rm:Delete a specified skill group'
            '-l:List all currently defined skill groups'
            '--group-list:List all currently defined skill groups'
            '-v:View connected skills of current project'
            '--view:View connected skills of current project'
        )
    fi

    # 1. If currently completing an option (starts with -)
    if [[ "$words[CURRENT]" == -* ]]; then
        local desc_opts="options"
        [[ "$lang" == zh* ]] && desc_opts="可选参数"
        _describe -t options "$desc_opts" options
        return
    fi

    # 2. Context-aware completions based on previous word
    local prev_word="$words[CURRENT-1]"
    case "$prev_word" in
        -u|--update|-d|--uninstall|--remove)
            local desc_skills="available skills"
            [[ "$lang" == zh* ]] && desc_skills="已安装技能"
            _describe -t available_skills "$desc_skills" available_skills
            return
            ;;
        -r|--group-rm)
            local desc_groups="available groups"
            [[ "$lang" == zh* ]] && desc_groups="已有分组"
            _describe -t available_groups "$desc_groups" available_groups
            return
            ;;
        -s|--group-set)
            local desc_groups="existing groups"
            [[ "$lang" == zh* ]] && desc_groups="已有分组(可选)"
            _describe -t available_groups "$desc_groups" available_groups
            return
            ;;
    esac

    # 3. Default positional arguments: complete available groups and skills cleanly
    local desc_grp="skill groups" desc_skl="available skills"
    if [[ "$lang" == zh* ]]; then
        desc_grp="技能分组"
        desc_skl="可用技能"
    fi
    _describe -t available_groups "$desc_grp" available_groups
    _describe -t available_skills "$desc_skl" available_skills
}

mskill() {
    zfl_require python3 || return 1
    load_color GREEN YELLOW RED BLUE CYAN RESET
    local lang=${ZFL_LANG:-${LANG%%.*}}

    local -a available_skills skills_to_link group_skills
    local opt_set=0 opt_rm=0 opt_list=0 opt_view=0 opt_install=0 opt_update=0 opt_update_all=0 opt_status=0 opt_uninstall=0
    local group_name target_repo uninstall_target selected line dest_dir skill src dest
    local -a update_targets=() install_args=()

    available_skills=( $HOME/.agents/skills/*(/N:t) )

    while (( $# > 0 )); do
        case "$1" in
            -h|--help)
                _mskill_help
                return 0
                ;;
            -i|--install|install)
                opt_install=1
                shift
                if (( $# == 0 )); then
                    # Interactive install
                    python3 "$ZFL_HOME/python/manage_skills.py" --interactive-install
                    return $?
                fi
                target_repo="$1"
                shift
                while (( $# > 0 )) && [[ "$1" != -* ]]; do
                    install_args+=("$1")
                    shift
                done
                break
                ;;
            -u|--update|update)
                opt_update=1
                shift
                while (( $# > 0 )) && [[ "$1" != -* ]]; do
                    update_targets+=("$1")
                    shift
                done
                break
                ;;
            --update-all|update-all)
                opt_update_all=1
                shift
                break
                ;;
            --status|status)
                opt_status=1
                shift
                break
                ;;
            -d|--uninstall|--remove|uninstall|remove)
                opt_uninstall=1
                shift
                if (( $# == 0 )); then
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${RED}[mskill] 错误: 需要指定要卸载的技能名称。${RESET}" >&2
                    else
                        echo -e "${RED}[mskill] Error: Skill name required for uninstallation.${RESET}" >&2
                    fi
                    return 1
                fi
                uninstall_target="$1"
                shift
                break
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
                        echo -e "${RED}[mskill] 错误: --group-set 需要指定分组名称和至少一个技能名。${RESET}" >&2
                    else
                        echo -e "${RED}[mskill] Error: --group-set requires a group name and at least one skill name.${RESET}" >&2
                    fi
                    return 1
                fi
                group_name="$1"
                shift
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
                        echo -e "${RED}[mskill] 错误: --group-rm 需要指定分组名称。${RESET}" >&2
                    else
                        echo -e "${RED}[mskill] Error: --group-rm requires a group name.${RESET}" >&2
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
                    echo -e "${RED}[mskill] 未知参数: $1${RESET}" >&2
                    echo "请使用 --help 查看用法。" >&2
                else
                    echo -e "${RED}[mskill] Unknown option: $1${RESET}" >&2
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

    # 1. Manage Skills Operations
    if (( opt_install )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --install "$target_repo" "${install_args[@]}"
        return $?
    fi

    if (( opt_update_all )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --update-all
        return $?
    fi

    if (( opt_update )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --update "${update_targets[@]}"
        return $?
    fi

    if (( opt_status )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --status
        return $?
    fi

    if (( opt_uninstall )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --uninstall "$uninstall_target"
        return $?
    fi

    # 2. Group Management Operations
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

    # 3. Interactive Selection (using fzf) if no arguments provided
    if (( ${#skills_to_link[@]} == 0 )); then
        if (( $+commands[fzf] )); then
            local prompt_msg header_msg
            if [[ "$lang" == zh* ]]; then
                header_msg="💡 快捷键: 空格:多选 | Ctrl-G:组管理 | Ctrl-U:更新 | Ctrl-I:安装 | Ctrl-D:删除组 | Ctrl-T:重译 | Ctrl-V:缩放 | Enter:确认链接"
                prompt_msg="Skill Search > "
            else
                header_msg="💡 Shortcuts: Space:Multi | Ctrl-G:Groups | Ctrl-U:Update | Ctrl-I:Install | Ctrl-D:Delete | Ctrl-T:Translate | Ctrl-V:Preview | Enter:Link"
            fi

            local fzf_opts=(
                --ansi
                --height 90%
                --reverse
                --multi
                --bind "start:reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-t:reload(python3 $ZFL_HOME/python/preview_skill.py --force-translate {1} >/dev/null 2>&1; python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-g:execute(python3 $ZFL_HOME/python/resolve_skills.py --interactive-set {+1})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-d:execute(python3 $ZFL_HOME/python/resolve_skills.py --interactive-rm {1})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-u:execute(python3 $ZFL_HOME/python/manage_skills.py --interactive-update {1})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-i:execute(python3 $ZFL_HOME/python/manage_skills.py --interactive-install)+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-v:toggle-preview-wrap"
                --preview "python3 $ZFL_HOME/python/preview_skill.py {1}"
                --preview-window "right:50%:wrap"
                --header "$header_msg"
                --prompt "$prompt_msg"
            )

            local selected_raw
            selected_raw=$(python3 "$ZFL_HOME/python/list_skills_fzf.py" | fzf "${fzf_opts[@]}")

            if [[ -z "$selected_raw" ]]; then
                if [[ "$lang" == zh* ]]; then
                    echo "未选择任何 skill。"
                else
                    echo "No skill selected."
                fi
                return 0
            fi

            while IFS= read -r line; do
                local s_id="${line%% *}"
                [[ -n "$s_id" ]] && skills_to_link+=("$s_id")
            done <<< "$selected_raw"
        else
            if [[ "$lang" == zh* ]]; then
                echo -e "${YELLOW}[mskill] 提示: 未安装 fzf，无法使用交互式选择。${RESET}"
                echo "请直接指定要链接的 skill 名称，或安装 fzf 以获得交互式体验。"
            else
                echo -e "${YELLOW}[mskill] Notice: fzf is not installed, cannot open interactive menu.${RESET}"
                echo "Please specify skill names directly, or install fzf for interactive selection."
            fi
            return 1
        fi
    fi

    # 4. Resolve Groups and Skill Names
    local -a resolved_skills
    resolved_skills=( ${(f)"$(python3 "$ZFL_HOME/python/resolve_skills.py" "${skills_to_link[@]}")"} )

    if (( ${#resolved_skills[@]} == 0 )); then
        if [[ "$lang" == zh* ]]; then
            echo -e "${YELLOW}[mskill] 没有需要链接的有效技能。${RESET}"
        else
            echo -e "${YELLOW}[mskill] No valid skills to link.${RESET}"
        fi
        return 0
    fi

    # 5. Create Symlinks in Current Project Directory
    dest_dir=".agents/skills"
    mkdir -p "$dest_dir"

    local -a success_skills failed_skills
    for skill in "${resolved_skills[@]}"; do
        [[ -z "$skill" ]] && continue
        src="$HOME/.agents/skills/$skill"
        dest="$dest_dir/$skill"

        if [[ ! -d "$src" ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[mskill] 错误: 全局技能 '$skill' 不存在于 ~/.agents/skills/ 中。${RESET}" >&2
            else
                echo -e "${RED}[mskill] Error: Global skill '$skill' does not exist in ~/.agents/skills/.${RESET}" >&2
            fi
            failed_skills+=("$skill")
            continue
        fi

        if [[ -e "$dest" || -L "$dest" ]]; then
            rm -rf "$dest"
        fi

        if ln -s "$src" "$dest"; then
            success_skills+=("$skill")
        else
            failed_skills+=("$skill")
        fi
    done

    # 6. Report Execution Summary
    if (( ${#success_skills[@]} > 0 )); then
        if [[ "$lang" == zh* ]]; then
            echo -e "${GREEN}[mskill] 成功将以下技能软链接到当前项目的 $dest_dir/ :${RESET}"
            for skill in "${success_skills[@]}"; do
                echo -e "  ${GREEN}✓${RESET} $skill -> $dest_dir/$skill"
            done
        else
            echo -e "${GREEN}[mskill] Successfully symlinked the following skills to $dest_dir/ :${RESET}"
            for skill in "${success_skills[@]}"; do
                echo -e "  ${GREEN}✓${RESET} $skill -> $dest_dir/$skill"
            done
        fi
    fi

    if (( ${#failed_skills[@]} > 0 )); then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[mskill] 以下技能软链接失败:${RESET}" >&2
            for skill in "${failed_skills[@]}"; do
                echo -e "  ${RED}✗${RESET} $skill" >&2
            done
        else
            echo -e "${RED}[mskill] Failed to link the following skills:${RESET}" >&2
            for skill in "${failed_skills[@]}"; do
                echo -e "  ${RED}✗${RESET} $skill" >&2
            done
        fi
        return 1
    fi

    return 0
}
