#? 名称: link_skills
#? 描述: 选择性地将 ~/.agents/skills 中的技能软链接到当前项目的 .agents/skills/ 中
#? 作者: Royi
#? 版本: 1.0.0
#? 依赖: fzf, python3
#? 用法: link_skills [技能名称...]
#? 示例: link_skills aicp

_link_skills_help() {
    cat <<'EOF'
link_skills - 选择性地将 ~/.agents/skills 中的 skills 软链接到当前目录的 .agents/skills/ 中

用法:
  link_skills [选项] [技能名称...]

示例:
  link_skills caveman diagnose       # 链接指定的 skills
  link_skills                       # 交互式选择要链接的 skills (使用 fzf)

选项:
  -h, --help                        显示帮助信息

说明:
  - 以符号链接（ln -s）的方式将 ~/.agents/skills/ 中的 skill 链接到当前目录的 .agents/skills/ 下。
  - 这样，您只需在 ~/.agents/skills 中修改内容，所有项目的 skill 都会自动同步。
EOF
}

_link_skills() {
    local -a available_skills
    # 获取 ~/.agents/skills/ 下的所有目录名
    available_skills=( $HOME/.agents/skills/*(/N:t) )
    _describe -t available_skills 'available skills' available_skills
}

link_skills() {
    zfl_require python3 || return 1
    # 加载颜色
    load_color GREEN YELLOW RED RESET

    local -a available_skills
    available_skills=( $HOME/.agents/skills/*(/N:t) )

    if (( ${#available_skills[@]} == 0 )); then
        echo -e "${RED}[link_skills] 错误: ~/.agents/skills/ 目录下没有找到任何 skill。${RESET}" >&2
        return 1
    fi

    local -a skills_to_link
    local arg
    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                _link_skills_help
                return 0
                ;;
            -*)
                echo -e "${RED}[link_skills] 未知参数: $arg${RESET}" >&2
                echo "请使用 --help 查看用法。" >&2
                return 2
                ;;
            *)
                skills_to_link+=("$arg")
                ;;
        esac
    done

    # 如果没有指定任何参数，进入交互式选择 (使用 fzf)
    if (( ${#skills_to_link[@]} == 0 )); then
        if (( $+commands[fzf] )); then
            local selected
            selected=$(printf '%s\n' "${available_skills[@]}" | fzf -m --bind "space:toggle" --preview 'python3 "'"$ZFL_HOME"'/python/preview_skill.py" {}' --preview-window='right:50%:wrap' --prompt="选择要链接的 Skill (空格键多选，Enter键确认): ")
            [[ -z "$selected" ]] && return 0
            skills_to_link=(${(f)selected})
        else
            echo -e "${YELLOW}[link_skills] fzf 未安装，无法进行交互式选择。${RESET}"
            echo -e "可用 skills 为: ${GREEN}${available_skills[*]}${RESET}"
            echo "请直接指定参数运行，例如: link_skills ${available_skills[1]}"
            return 1
        fi
    fi

    # 确定目标目录
    local dest_dir="./.agents/skills"
    mkdir -p "$dest_dir" || {
        echo -e "${RED}[link_skills] 错误: 无法创建目标目录 $dest_dir${RESET}" >&2
        return 1
    }

    # 执行软链接
    local skill
    for skill in "${skills_to_link[@]}"; do
        local src="$HOME/.agents/skills/$skill"
        local dest="$dest_dir/$skill"

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
