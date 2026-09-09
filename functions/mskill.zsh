#? name: mskill
#? description: Manage, install, discover, package, update, and selectively link or copy AI Agent skills
#? author: Royi
#? version: 1.4.0
#? deps: python3
#? usage: mskill [options] [skill_name/group_name...]
#? example: mskill -c startup

_mskill_help() {
    local lang=${ZFL_LANG:-${LANG%%.*}}
    if [[ "$lang" == zh* ]]; then
        cat <<'EOF'
mskill (Manage Skill) - AI Agent 技能全生命周期管理与工程化协作中枢

用法:
  mskill [选项] [技能名称/分组名称...]
  mskill -c / --copy [技能名称/分组名称...]
  mskill -i / --install <仓库地址/简写/本地目录> [技能名...]
  mskill -u / --update [技能名...]
  mskill --update-all
  mskill --status
  mskill -b / --unbind <技能名...>
  mskill -d / --uninstall <技能名>
  mskill --new / new / create [技能名]
  mskill --doctor / doctor / check
  mskill --eject / eject [技能名...]
  mskill --unlink / -X [技能名/组名...]
  mskill --unlink-all
  mskill dump / export
  mskill sync
  mskill --translate-all
  mskill -s / --group-set <分组名称> [--ordered] <技能列表...>
  mskill -r / --group-rm <分组名称>
  mskill -l / --group-list
  mskill -v / --view / view

常用示例:
  mskill                            # 交互式选择、管理与软链接技能 (使用 fzf)
  mskill -c                         # 交互式选择并拷贝技能实体副本到当前项目
  mskill caveman diagnose           # 软链接指定的技能到当前项目
  mskill -c startup                 # 拷贝 startup 分组下的所有技能实体副本到当前项目
  mskill new my-skill               # 生成标准 AI Agent 技能脚手架模板
  mskill doctor                     # 健康巡检：自动诊断并修复死链、损坏技能与环境依赖
  mskill eject video-generator      # 将当前项目中的软链接原地转换为独立物理实体副本
  mskill --unlink video-generator   # 安全从当前项目中解挂指定技能（不影响全局技能库）
  mskill --unlink-all               # 解挂当前项目引入的全部技能
  mskill dump                       # 将当前项目的技能依赖与挂载模式导出为 .skillsrc
  mskill sync                       # 团队/多机协作：根据 .skillsrc 自动安装并对齐所有项目技能
  mskill -i /path/to/local-dir      # 直接从本地文件夹打包导入自建技能并纳管
  mskill -i anthropics/quickstarts  # 从 GitHub 仓库自动识别并打包下载技能 (支持 @tag / #branch)
  mskill -u video-generator         # 检查并更新指定技能至最新版本
  mskill --update-all               # 一键更新所有已追踪的远程技能
  mskill --status                   # 查看已安装技能的版本 Commit 与来源
  mskill -b video-generator         # 解绑指定技能的远程 Git 关联 (转为本地自建技能)
  mskill --translate-all            # 一键批量拉取所有未翻译技能的中文译名与描述

选项:
  -h, --help                        显示帮助信息
  -c, --copy [技能/组...]           拷贝技能实体副本到当前项目 (独立存在，修改不影响全局)
  -i, --install <url/repo/path>     安装技能（支持 GitHub 简写、@tag/#branch、子路径及本地目录导入）
  -u, --update [技能名...]          更新指定的技能（分组关系自动 100% 保持不变）
  --update-all                      更新所有已安装的远程技能
  --status                          查看技能的版本、来源仓库与更新状态
  -b, --unbind <技能名...>          解绑技能的远程 Git 仓库（转为本地自建技能，保留本地代码）
  -d, --uninstall <技能名>          卸载指定的技能包并清理元数据
  --new, new, create [名]           生成标准技能脚手架 (SKILL.md, scripts/, references/)
  --doctor, doctor, check           健康检查：检测并修复悬空死链、缺失文件与系统依赖
  --eject, eject [技能名...]        将当前项目中的软链接就地脱壳为独立实体副本
  --unlink, -X [技能/组...]         从当前项目中移除指定技能（不影响全局技能库）
  --unlink-all                      从当前项目中移除所有技能
  dump, export                      导出当前项目技能依赖清单至 .skillsrc
  sync                              根据 .skillsrc 声明式一键安装并对齐当前项目技能
  --translate-all                   批量拉取全局未翻译技能的中文双语卡片
  -s, --group-set <组名> [--ordered] <技能...>
                                    创建或修改技能分组，加 --ordered 则将顺序标记为推荐调用顺序
  -r, --group-rm <组名>             删除指定的技能分组
  -l, --group-list                  列出当前定义的所有技能分组
  -v, --view / view                 直接查看当前项目底下的已连接技能及其中文翻译
EOF
    else
        cat <<'EOF'
mskill (Manage Skill) - AI Agent Skill Lifecycle Manager & Engineering Hub

Usage:
  mskill [options] [skill_name/group_name...]
  mskill -c / --copy [skill_name/group_name...]
  mskill -i / --install <repo_url_or_path> [skill_name...]
  mskill -u / --update [skill_name...]
  mskill --update-all
  mskill --status
  mskill -b / --unbind <skill_name...>
  mskill -d / --uninstall <skill_name>
  mskill --new / new / create [skill_name]
  mskill --doctor / doctor / check
  mskill --eject / eject [skill_name...]
  mskill --unlink / -X [skill_name/group...]
  mskill --unlink-all
  mskill dump / export
  mskill sync
  mskill --translate-all
  mskill -s / --group-set <group_name> [--ordered] <skills_list...>
  mskill -r / --group-rm <group_name>
  mskill -l / --group-list
  mskill -v / --view / view

Examples:
  mskill                            # Interactive selection and management (uses fzf)
  mskill -c                         # Interactive selection to copy skill entities to project
  mskill caveman diagnose           # Link specified skills into current project
  mskill -c startup                 # Copy all skill entities in 'startup' group into project
  mskill new my-skill               # Scaffold a new standard skill template
  mskill doctor                     # Check & repair broken symlinks, metadata, dependencies
  mskill eject video-generator      # Convert project symlink to independent physical copy
  mskill --unlink video-generator   # Unlink specified skill from project (preserves global)
  mskill --unlink-all               # Unlink all skills from current project
  mskill dump                       # Export project skills specification to .skillsrc
  mskill sync                       # Align and auto-install skills according to .skillsrc
  mskill -i /path/to/local-dir      # Import and manage local directory as a skill
  mskill -i anthropics/quickstarts  # Auto-discover from GitHub (supports @tag / #branch)
  mskill -u video-generator         # Check and update specified skill
  mskill --update-all               # Update all tracked remote skills
  mskill --status                   # View versions, commits, and source repositories
  mskill -b video-generator         # Unbind skill from remote Git tracking (convert to local)
  mskill --translate-all            # Batch pre-fetch Chinese translations for all skills

Options:
  -h, --help                        Show help information
  -c, --copy [skill/group...]       Copy standalone skill entities to project (independent)
  -i, --install <url/repo/path>     Install skill (supports GitHub shorthand, @tag, local dirs)
  -u, --update [skill_name...]      Update specified skills (group mappings preserved)
  --update-all                      Update all tracked remote skills
  --status                          View version commit and source repository status
  -b, --unbind <skill_name...>      Unbind skill from remote Git repo (convert to local)
  -d, --uninstall <skill_name>      Uninstall specified skill and clean manifest
  --new, new, create [name]         Scaffold new skill (SKILL.md, scripts/, references/)
  --doctor, doctor, check           Health check: inspect & fix broken symlinks, dependencies
  --eject, eject [name...]          Eject project symlink into local physical copy
  --unlink, -X [skill/group...]     Unlink skills from current project (preserves global)
  --unlink-all                      Unlink all skills from current project
  dump, export                      Export project skills configuration to .skillsrc
  sync                              Declaratively install and mount skills from .skillsrc
  --translate-all                   Batch fetch Chinese translations for all skills
  -s, --group-set <grp> [--ordered] <skills...>
                                    Create or modify a skill group; --ordered marks sequence
  -r, --group-rm <grp>              Delete a specified skill group
  -l, --group-list                  List all currently defined skill groups
  -v, --view / view                 View connected skills of the current project
EOF
    fi
}

_mskill() {
    local -a available_skills available_groups project_skills options
    available_skills=( $HOME/.agents/skills/*(/N:t) )
    project_skills=( .agents/skills/*(/N:t) )
    local lang=${ZFL_LANG:-${LANG%%.*}}

    if (( $+commands[python3] )); then
        available_groups=( ${(f)"$(python3 "$ZFL_HOME/python/resolve_skills.py" --list-groups 2>/dev/null)"} )
    fi

    if [[ "$lang" == zh* ]]; then
        options=(
            '-h:显示帮助信息'
            '--help:显示帮助信息'
            '-c:拷贝技能实体到当前项目 (解除对全局软链接依赖)'
            '--copy:拷贝技能实体到当前项目 (解除对全局软链接依赖)'
            '-i:安装/下载技能包 (支持 GitHub 简写/@tag/子路径/本地目录)'
            '--install:安装/下载技能包 (支持 GitHub 简写/@tag/子路径/本地目录)'
            '-u:检查并更新指定技能'
            '--update:检查并更新指定技能'
            '--update-all:一键更新所有已追踪的远程技能'
            '--status:查看技能版本 Commit 与来源状态'
            '-b:解绑技能的远程 Git 仓库关联 (转为本地自建技能)'
            '--unbind:解绑技能的远程 Git 仓库关联 (转为本地自建技能)'
            '--unbind-git:解绑技能的远程 Git 仓库关联 (转为本地自建技能)'
            '-d:卸载指定的技能包并清理元数据'
            '--uninstall:卸载指定的技能包并清理元数据'
            '--remove:卸载指定的技能包并清理元数据'
            '--new:创建标准技能脚手架骨架'
            'new:创建标准技能脚手架骨架'
            'create:创建标准技能脚手架骨架'
            '--doctor:技能健康诊断与死链修复'
            'doctor:技能健康诊断与死链修复'
            'check:技能健康诊断与死链修复'
            '--eject:将当前项目的软链接转为独立实体副本'
            'eject:将当前项目的软链接转为独立实体副本'
            '--unlink:从当前项目中移除指定技能 (不影响全局)'
            '-X:从当前项目中移除指定技能 (不影响全局)'
            'unlink:从当前项目中移除指定技能 (不影响全局)'
            '--unlink-all:从当前项目中移除所有技能'
            'dump:导出当前项目技能依赖清单至 .skillsrc'
            'export:导出当前项目技能依赖清单至 .skillsrc'
            'sync:根据 .skillsrc 一键拉取并对齐项目技能'
            '--translate-all:批量拉取所有未翻译技能的中文译名'
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
            '-c:Copy skill entities to current project (independent entity)'
            '--copy:Copy skill entities to current project (independent entity)'
            '-i:Install skill package (supports GitHub shorthand/tag/path/local)'
            '--install:Install skill package (supports GitHub shorthand/tag/path/local)'
            '-u:Check and update specified skill'
            '--update:Check and update specified skill'
            '--update-all:Update all tracked remote skills'
            '--status:View skill version commit and source status'
            '-b:Unbind skill from remote Git repo (convert to local)'
            '--unbind:Unbind skill from remote Git repo (convert to local)'
            '--unbind-git:Unbind skill from remote Git repo (convert to local)'
            '-d:Uninstall specified skill package'
            '--uninstall:Uninstall specified skill package'
            '--remove:Uninstall specified skill package'
            '--new:Scaffold new skill template'
            'new:Scaffold new skill template'
            'create:Scaffold new skill template'
            '--doctor:Diagnose skills health & fix broken links'
            'doctor:Diagnose skills health & fix broken links'
            'check:Diagnose skills health & fix broken links'
            '--eject:Eject project symlinks into physical copies'
            'eject:Eject project symlinks into physical copies'
            '--unlink:Unlink skills from current project'
            '-X:Unlink skills from current project'
            'unlink:Unlink skills from current project'
            '--unlink-all:Unlink all skills from current project'
            'dump:Export project skills specification to .skillsrc'
            'export:Export project skills specification to .skillsrc'
            'sync:Sync and install skills from .skillsrc'
            '--translate-all:Batch pre-fetch Chinese translations'
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
        -c|--copy)
            local desc_grp="skill groups" desc_skl="available skills"
            if [[ "$lang" == zh* ]]; then
                desc_grp="技能分组"
                desc_skl="可用技能"
            fi
            _describe -t available_groups "$desc_grp" available_groups
            _describe -t available_skills "$desc_skl" available_skills
            return
            ;;
        -u|--update|-b|--unbind|--unbind-git|-d|--uninstall|--remove)
            local desc_skills="available skills"
            [[ "$lang" == zh* ]] && desc_skills="已安装技能"
            _describe -t available_skills "$desc_skills" available_skills
            return
            ;;
        --unlink|-X|unlink|eject|--eject)
            local desc_proj_skills="project skills"
            [[ "$lang" == zh* ]] && desc_proj_skills="当前项目技能"
            _describe -t project_skills "$desc_proj_skills" project_skills
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
    load_color GREEN YELLOW RED BLUE CYAN RESET BRIGHT_BLACK
    local lang=${ZFL_LANG:-${LANG%%.*}}

    local -a available_skills skills_to_link group_skills
    local opt_set=0 opt_rm=0 opt_list=0 opt_view=0 opt_install=0 opt_update=0 opt_update_all=0 opt_status=0 opt_uninstall=0 opt_copy=0 opt_unbind=0
    local opt_new=0 opt_doctor=0 opt_eject=0 opt_unlink=0 opt_unlink_all=0 opt_dump=0 opt_sync=0 opt_translate_all=0
    local group_name target_repo uninstall_target line dest_dir skill src dest new_skill_name
    local -a update_targets=() install_args=() unbind_targets=() unlink_targets=() eject_targets=()

    available_skills=( $HOME/.agents/skills/*(/N:t) )

    while (( $# > 0 )); do
        case "$1" in
            -h|--help)
                _mskill_help
                return 0
                ;;
            -c|--copy|copy)
                opt_copy=1
                shift
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
            -b|--unbind|--unbind-git|unbind|detach)
                opt_unbind=1
                shift
                while (( $# > 0 )) && [[ "$1" != -* ]]; do
                    unbind_targets+=("$1")
                    shift
                done
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
            --new|new|create|--create)
                opt_new=1
                shift
                if (( $# > 0 )) && [[ "$1" != -* ]]; then
                    new_skill_name="$1"
                    shift
                fi
                break
                ;;
            --doctor|doctor|check|--check)
                opt_doctor=1
                shift
                break
                ;;
            --eject|eject)
                opt_eject=1
                shift
                while (( $# > 0 )) && [[ "$1" != -* ]]; do
                    eject_targets+=("$1")
                    shift
                done
                break
                ;;
            --unlink|-X|unlink)
                opt_unlink=1
                shift
                while (( $# > 0 )) && [[ "$1" != -* ]]; do
                    unlink_targets+=("$1")
                    shift
                done
                break
                ;;
            --unlink-all|unlink-all)
                opt_unlink_all=1
                shift
                break
                ;;
            dump|export|--dump|--export)
                opt_dump=1
                shift
                break
                ;;
            sync|--sync)
                opt_sync=1
                shift
                break
                ;;
            --translate-all|translate-all)
                opt_translate_all=1
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

    if (( opt_unbind )); then
        if (( ${#unbind_targets[@]} == 0 )); then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[mskill] 错误: 需要指定要解绑 Git 关联的技能名称。${RESET}" >&2
            else
                echo -e "${RED}[mskill] Error: Skill name(s) required for unbinding.${RESET}" >&2
            fi
            return 1
        fi
        python3 "$ZFL_HOME/python/manage_skills.py" --unbind "${unbind_targets[@]}"
        return $?
    fi

    if (( opt_uninstall )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --uninstall "$uninstall_target"
        return $?
    fi

    if (( opt_new )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --new "$new_skill_name"
        return $?
    fi

    if (( opt_doctor )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --doctor
        return $?
    fi

    if (( opt_eject )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --eject "${eject_targets[@]}"
        return $?
    fi

    if (( opt_unlink_all )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --unlink-all
        return $?
    fi

    if (( opt_unlink )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --unlink "${unlink_targets[@]}"
        return $?
    fi

    if (( opt_dump )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --dump
        return $?
    fi

    if (( opt_sync )); then
        python3 "$ZFL_HOME/python/manage_skills.py" --sync
        return $?
    fi

    if (( opt_translate_all )); then
        python3 "$ZFL_HOME/python/preview_skill.py" --translate-all
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
                if (( opt_copy )); then
                    header_msg=$'🌿 浏览: Tab/方向键 折叠展开  │  Ctrl-O 全展/全折  │  空格 多选\n⚡ 管理: Ctrl-G 分组  │  Ctrl-N 安装  │  Ctrl-U 更新  │  Ctrl-E 编辑\n🚀 执行: Enter 拷贝实体  │  Ctrl-X 解挂  │  Ctrl-B 解绑Git'
                    prompt_msg="Skill Copy > "
                else
                    header_msg=$'🌿 浏览: Tab/方向键 折叠展开  │  Ctrl-O 全展/全折  │  空格 多选\n⚡ 管理: Ctrl-G 分组  │  Ctrl-N 安装  │  Ctrl-U 更新  │  Ctrl-E 编辑\n🚀 执行: Enter 软链接  │  Alt-C 拷贝  │  Ctrl-X 解挂  │  Ctrl-B 解绑'
                    prompt_msg="Skill Search > "
                fi
            else
                if (( opt_copy )); then
                    header_msg=$'🌿 Browse: Tab/Arrows Toggle  │  Ctrl-O Toggle All  │  Space Multi\n⚡ Manage: Ctrl-G Groups  │  Ctrl-N Install  │  Ctrl-U Update  │  Ctrl-E Edit\n🚀 Action: Enter Copy Entity  │  Ctrl-X Unlink  │  Ctrl-B Unbind Git'
                    prompt_msg="Skill Copy > "
                else
                    header_msg=$'🌿 Browse: Tab/Arrows Toggle  │  Ctrl-O Toggle All  │  Space Multi\n⚡ Manage: Ctrl-G Groups  │  Ctrl-N Install  │  Ctrl-U Update  │  Ctrl-E Edit\n🚀 Action: Enter Symlink  │  Alt-C Copy Entity  │  Ctrl-X Unlink  │  Ctrl-B Unbind'
                    prompt_msg="Skill Search > "
                fi
            fi

            local fzf_opts=(
                --ansi
                --height 90%
                --reverse
                --multi
                --expect=alt-c
                --bind "start:execute(python3 $ZFL_HOME/python/list_skills_fzf.py --init)+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "tab:execute(python3 $ZFL_HOME/python/list_skills_fzf.py --toggle {})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "btab:execute(python3 $ZFL_HOME/python/list_skills_fzf.py --toggle-all)+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-o:execute(python3 $ZFL_HOME/python/list_skills_fzf.py --toggle-all)+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-e:execute(python3 $ZFL_HOME/python/manage_skills.py --interactive-edit {})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "right:execute(python3 $ZFL_HOME/python/list_skills_fzf.py --expand {})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "left:execute(python3 $ZFL_HOME/python/list_skills_fzf.py --collapse {})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "space:toggle+down"
                --bind "ctrl-t:reload(python3 $ZFL_HOME/python/preview_skill.py --force-translate {} >/dev/null 2>&1; python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-g:execute(python3 $ZFL_HOME/python/resolve_skills.py --interactive-set {+})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-d:execute(python3 $ZFL_HOME/python/resolve_skills.py --interactive-rm {})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-u:execute(python3 $ZFL_HOME/python/manage_skills.py --interactive-update {})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-b:execute(python3 $ZFL_HOME/python/manage_skills.py --interactive-unbind {})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-x:execute(python3 $ZFL_HOME/python/manage_skills.py --interactive-unlink {})+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-n:execute(python3 $ZFL_HOME/python/manage_skills.py --interactive-install)+reload(python3 $ZFL_HOME/python/list_skills_fzf.py)"
                --bind "ctrl-v:toggle-preview-wrap"
                --preview "python3 $ZFL_HOME/python/preview_skill.py {}"
                --preview-window "right:50%:wrap"
                --header "$header_msg"
                --prompt "$prompt_msg"
            )

            local selected_raw
            selected_raw=$(python3 "$ZFL_HOME/python/list_skills_fzf.py" | fzf "${fzf_opts[@]}")

            if [[ -z "$selected_raw" ]]; then
                if [[ "$lang" == zh* ]]; then
                    echo "未选择任何技能。"
                else
                    echo "No skill selected."
                fi
                return 0
            fi

            local first_line=1
            while IFS= read -r line; do
                if (( first_line )); then
                    first_line=0
                    if [[ "$line" == "alt-c" || "$line" == "alt-C" ]]; then
                        opt_copy=1
                    fi
                    continue
                fi
                [[ -n "$line" ]] && skills_to_link+=("$line")
            done <<< "$selected_raw"
        else
            if [[ "$lang" == zh* ]]; then
                echo -e "${YELLOW}[mskill] 提示: 未安装 fzf，无法使用交互式选择。${RESET}"
                echo "请直接指定要引入的 skill 名称，或安装 fzf 以获得交互式体验。"
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
        local no_action_msg
        if (( opt_copy )); then
            no_action_msg=$([[ "$lang" == zh* ]] && echo "没有需要拷贝的有效技能。" || echo "No valid skills to copy.")
        else
            no_action_msg=$([[ "$lang" == zh* ]] && echo "没有需要链接的有效技能。" || echo "No valid skills to link.")
        fi
        echo -e "${YELLOW}[mskill] ${no_action_msg}${RESET}"
        return 0
    fi

    # 5. Create Symlinks or Copy Entities into Current Project Directory
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

        if (( opt_copy )); then
            if cp -r "$src" "$dest"; then
                success_skills+=("$skill")
            else
                failed_skills+=("$skill")
            fi
        else
            if ln -s "$src" "$dest"; then
                success_skills+=("$skill")
            else
                failed_skills+=("$skill")
            fi
        fi
    done

    # 6. Report Execution Summary
    if (( ${#success_skills[@]} > 0 )); then
        if (( opt_copy )); then
            if [[ "$lang" == zh* ]]; then
                echo -e "\n  ${GREEN}✓ 技能实体拷贝成功${RESET} (共 ${#success_skills[@]} 个实体已拷贝至 ${CYAN}$dest_dir/${RESET})"
                echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}"
                for skill in "${success_skills[@]}"; do
                    echo -e "    ${GREEN}•${RESET} $skill -> $dest_dir/$skill (实体副本)"
                done
                echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}\n"
            else
                echo -e "\n  ${GREEN}✓ Skill Entities Copied${RESET} (${#success_skills[@]} entities copied to ${CYAN}$dest_dir/${RESET})"
                echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}"
                for skill in "${success_skills[@]}"; do
                    echo -e "    ${GREEN}•${RESET} $skill -> $dest_dir/$skill (copied entity)"
                done
                echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}\n"
            fi
        else
            if [[ "$lang" == zh* ]]; then
                echo -e "\n  ${GREEN}✓ 技能软链接挂载成功${RESET} (共 ${#success_skills[@]} 个技能已挂载至 ${CYAN}$dest_dir/${RESET})"
                echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}"
                for skill in "${success_skills[@]}"; do
                    echo -e "    ${GREEN}•${RESET} $skill -> $dest_dir/$skill (软链接)"
                done
                echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}\n"
            else
                echo -e "\n  ${GREEN}✓ Skills Symlinked${RESET} (${#success_skills[@]} skills mounted to ${CYAN}$dest_dir/${RESET})"
                echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}"
                for skill in "${success_skills[@]}"; do
                    echo -e "    ${GREEN}•${RESET} $skill -> $dest_dir/$skill (symlink)"
                done
                echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}\n"
            fi
        fi
    fi

    if (( ${#failed_skills[@]} > 0 )); then
        local action_str
        if (( opt_copy )); then
            action_str=$([[ "$lang" == zh* ]] && echo "拷贝" || echo "copy")
        else
            action_str=$([[ "$lang" == zh* ]] && echo "软链接" || echo "link")
        fi
        if [[ "$lang" == zh* ]]; then
            echo -e "\n  ${RED}✗ 操作部分失败${RESET} (以下技能${action_str}失败):" >&2
            echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}" >&2
            for skill in "${failed_skills[@]}"; do
                echo -e "    ${RED}✗${RESET} $skill" >&2
            done
            echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}\n" >&2
        else
            echo -e "\n  ${RED}✗ Operation Failed${RESET} (Failed to ${action_str} following skills):" >&2
            echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}" >&2
            for skill in "${failed_skills[@]}"; do
                echo -e "    ${RED}✗${RESET} $skill" >&2
            done
            echo -e "  ${BRIGHT_BLACK}────────────────────────────────────────────────────────────${RESET}\n" >&2
        fi
        return 1
    fi

    return 0
}

