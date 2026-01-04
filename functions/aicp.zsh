##
# AI Copy Project (aicp)
# 
# 功能：
#   将指定文件或目录下的所有代码文件读取，格式化为 Markdown 代码块，
#   并添加路径头注，最终复制到系统剪贴板 (wl-copy)。
#   专为向 AI 投喂项目上下文设计。
#
# 参数：
#   -a          : (All) 递归复制当前目录下所有文件（忽略 .git, node_modules 等）
#   -c [路径..] : (Choose) 选择指定的文件或文件夹（文件夹会自动递归）
#
# 示例：
#   aicp -a
#   aicp -c ./src ./base.zsh
#
aicp() {
    load_color GREEN YELLOW RED BLUE RESET

    # 检查依赖
    if ! command -v wl-copy &> /dev/null; then
        echo -e "${RED}[ERROR]${RESET} 需要安装 'wl-copy' 才能使用此功能 (Wayland)。"
        return 1
    fi

    # 内部函数：格式化单个文件并输出到 stdout
    _aicp_format_file() {
        local f="$1"

        # 1. 基础检查：必须是文件
        [[ ! -f "$f" ]] && return

        # 2. 二进制检查：简单的忽略二进制文件（防止乱码）
        # 使用 grep -I (Ignore binary) 检查文件是否为文本
        if ! grep -Iq . "$f" 2>/dev/null && [[ -s "$f" ]]; then
            # 文件非空且被 grep 判定为二进制，跳过
            return
        fi

        # 3. 获取扩展名用于 Markdown 标记
        local ext="${f##*.}"
        local lang="$ext"
        
        # 简单的映射优化 (可根据需要扩展)
        case "$ext" in
            zsh|bash|sh) lang="bash" ;;
            py)          lang="python" ;;
            js)          lang="javascript" ;;
            ts)          lang="typescript" ;;
            rs)          lang="rust" ;;
            h|c)         lang="c" ;;
            cpp|hpp)     lang="cpp" ;;
            java)        lang="java";;
            txt|md|json|yaml|toml) lang="$ext" ;;
            *)           lang="" ;; # 未知后缀不加语言标记，避免高亮错误
        esac

        # 4. 输出格式化内容
        echo -e "\nFILE PATH: ${f}"
        echo "\`\`\`${lang}"
        cat "$f"
        echo -e "\n\`\`\`"
    }

    local files=()
    local mode="$1"
    shift # 移除第一个参数

    if [[ "$mode" == "-a" ]]; then
        echo -e "${YELLOW}[aicp]${RESET} 正在扫描当前目录所有文件 (排除 .git/node_modules)..."
        # 使用 find 递归查找，排除常见垃圾目录
        while IFS= read -r line; do files+=("$line"); done < <(find . -type f \
            -not -path '*/.git/*' \
            -not -path '*/node_modules/*' \
            -not -path '*/__pycache__/*' \
            -not -path '*/.DS_Store' \
            -not -path '*/build/*' \
            -not -path '*/dist/*')
            
    elif [[ "$mode" == "-c" ]]; then
        # 遍历用户传入的每个路径
        for target in "$@"; do
            if [[ -f "$target" ]]; then
                files+=("$target")
            elif [[ -d "$target" ]]; then
                echo -e "${YELLOW}[aicp]${RESET} 正在递归扫描目录: $target ..."
                while IFS= read -r line; do files+=("$line"); done < <(find "$target" -type f \
                    -not -path '*/.git/*' \
                    -not -path '*/node_modules/*')
            else
                echo -e "${RED}[WARN]${RESET} 路径不存在: $target"
            fi
        done
    else
        echo -e "用法:"
        echo -e "  aicp -a             # 复制当前目录所有代码"
        echo -e "  aicp -c [file/dir]  # 复制指定文件或文件夹"
        return 1
    fi

    # 检查是否有文件
    if [[ ${#files[@]} -eq 0 ]]; then
        echo -e "${RED}[ERROR]${RESET} 未找到任何文件。"
        return 1
    fi

    # 核心处理：批量处理 -> 写入剪贴板
    echo -e "${BLUE}[aicp]${RESET} 正在处理 ${#files[@]} 个文件..."
    
    (
        for f in "${files[@]}"; do
            _aicp_format_file "$f"
        done
    ) | wl-copy

    echo -e "${GREEN}[SUCCESS]${RESET} 内容已复制到剪贴板！(共 ${#files[@]} 个文件)"
}
