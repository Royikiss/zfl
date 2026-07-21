#? name: extract
#? description: Universal auto-decompressor and compressor with format options and Tab completion
#? author: Royi
#? version: 1.2.0
#? protected: true
#? deps: tar, zip, unzip, 7z, unrar, gzip, bzip2, xz, zstd
#? usage: extract [-d|--decompress] archive... | extract -c|--compress [--zip|--tar.gz|...] [-o output] target...
#? example: extract archive.zip; extract -c --zip folder/; extract -c --tar.gz -o backup file1 dir2/

extract() {
    zfl_require tar || return 1
    load_color RED GREEN YELLOW CYAN BLUE BOLD RESET

    if [[ $# -eq 0 ]]; then
        echo -e "${GREEN}[extract]${RESET} ${BOLD}万能解压与压缩工具 (ZFL Universal Decompressor & Compressor)${RESET}"
        echo -e "用法:"
        echo -e "  解压 (默认): ${CYAN}extract${RESET} [-d|--decompress] <压缩包1> [压缩包2 ...]"
        echo -e "  压缩:        ${CYAN}extract${RESET} -c|--compress [--格式] [-o 输出名] <目标1> [目标2 ...]"
        echo -e "常用格式参数: ${YELLOW}--zip, --tar.gz, --tar.bz2, --tar.xz, --tar.zst, --7z, --tar${RESET}"
        echo -e "提示: 输入 ${CYAN}extract -${RESET} 并按 ${BOLD}Tab${RESET} 键可列出所有格式及中文说明。"
        return 0
    fi

    local mode="decompress"
    local target_format=""
    local output_name=""
    local -a targets=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -c|--compress)
                mode="compress"
                shift
                ;;
            -d|--decompress)
                mode="decompress"
                shift
                ;;
            -o|--output)
                if [[ -n "$2" && "$2" != -* ]]; then
                    output_name="$2"
                    shift 2
                else
                    echo -e "${RED}[Error]${RESET} -o/--output 需要指定输出文件名" >&2
                    return 1
                fi
                ;;
            --tar)
                target_format="tar"
                shift
                ;;
            --tar.gz|--tgz|-gz|--gz)
                target_format="tar.gz"
                shift
                ;;
            --tar.bz2|--tbz2|-bz2|--bz2)
                target_format="tar.bz2"
                shift
                ;;
            --tar.xz|--txz|-xz|--xz)
                target_format="tar.xz"
                shift
                ;;
            --tar.zst|--tzst|-zst|--zst)
                target_format="tar.zst"
                shift
                ;;
            --zip|-zip)
                target_format="zip"
                shift
                ;;
            --7z|-7z)
                target_format="7z"
                shift
                ;;
            --rar|-rar)
                target_format="rar"
                shift
                ;;
            -h|--help)
                extract
                return 0
                ;;
            -*)
                echo -e "${RED}[Error]${RESET} 未知选项: ${YELLOW}$1${RESET}" >&2
                return 1
                ;;
            *)
                targets+=("$1")
                shift
                ;;
        esac
    done

    if [[ ${#targets[@]} -eq 0 ]]; then
        echo -e "${RED}[Error]${RESET} 请指定需要处理的目标文件或目录" >&2
        return 1
    fi

    # ================= 1. 压缩模式逻辑 =================
    if [[ "$mode" == "compress" ]]; then
        if [[ -z "$target_format" ]]; then
            target_format="zip"
            echo -e "${YELLOW}[Notice]${RESET} 未指定压缩格式，默认使用 ${CYAN}--zip${RESET}"
        fi

        local first_target="${targets[1]}"
        first_target="${first_target%/}"
        local base_name="${first_target:t}"

        local out_archive=""
        if [[ -n "$output_name" ]]; then
            out_archive="$output_name"
        else
            out_archive="$base_name"
        fi

        # 补全文件后缀
        case "$target_format" in
            tar)      [[ "$out_archive" != *.tar ]] && out_archive="${out_archive}.tar" ;;
            tar.gz)   [[ "$out_archive" != *.tar.gz && "$out_archive" != *.tgz ]] && out_archive="${out_archive}.tar.gz" ;;
            tar.bz2)  [[ "$out_archive" != *.tar.bz2 && "$out_archive" != *.tbz2 ]] && out_archive="${out_archive}.tar.bz2" ;;
            tar.xz)   [[ "$out_archive" != *.tar.xz && "$out_archive" != *.txz ]] && out_archive="${out_archive}.tar.xz" ;;
            tar.zst)  [[ "$out_archive" != *.tar.zst && "$out_archive" != *.tzst ]] && out_archive="${out_archive}.tar.zst" ;;
            zip)      [[ "$out_archive" != *.zip ]] && out_archive="${out_archive}.zip" ;;
            7z)       [[ "$out_archive" != *.7z ]] && out_archive="${out_archive}.7z" ;;
            rar)      [[ "$out_archive" != *.rar ]] && out_archive="${out_archive}.rar" ;;
            gz)       [[ "$out_archive" != *.gz ]] && out_archive="${out_archive}.gz" ;;
            bz2)      [[ "$out_archive" != *.bz2 ]] && out_archive="${out_archive}.bz2" ;;
            xz)       [[ "$out_archive" != *.xz ]] && out_archive="${out_archive}.xz" ;;
            zst)      [[ "$out_archive" != *.zst ]] && out_archive="${out_archive}.zst" ;;
        esac

        echo -e "${GREEN}[compress]${RESET} 正在打包压缩至: ${CYAN}$out_archive${RESET} (${YELLOW}$target_format${RESET}) ..."

        local c_status=0
        case "$target_format" in
            tar)
                tar -cf "$out_archive" "${targets[@]}"
                c_status=$?
                ;;
            tar.gz)
                tar -czf "$out_archive" "${targets[@]}"
                c_status=$?
                ;;
            tar.bz2)
                tar -cjf "$out_archive" "${targets[@]}"
                c_status=$?
                ;;
            tar.xz)
                zfl_require xz || return 1
                tar -cJf "$out_archive" "${targets[@]}"
                c_status=$?
                ;;
            tar.zst)
                zfl_require zstd || return 1
                tar --zstd -cf "$out_archive" "${targets[@]}"
                c_status=$?
                ;;
            zip)
                zfl_require zip || return 1
                zip -r -q "$out_archive" "${targets[@]}"
                c_status=$?
                ;;
            7z)
                zfl_require 7z || return 1
                7z a "$out_archive" "${targets[@]}" >/dev/null
                c_status=$?
                ;;
            rar)
                if command -v rar &>/dev/null; then
                    rar a -idq "$out_archive" "${targets[@]}"
                    c_status=$?
                elif command -v 7z &>/dev/null; then
                    7z a "$out_archive" "${targets[@]}" >/dev/null
                    c_status=$?
                else
                    zfl_require rar || return 1
                fi
                ;;
            gz|bz2|xz|zst)
                echo -e "${RED}[Error]${RESET} 单文件压缩格式 ($target_format) 请直接使用工具或改用 --tar.$target_format" >&2
                return 1
                ;;
        esac

        if [[ $c_status -eq 0 ]]; then
            echo -e "${GREEN}[Success]${RESET} 压缩成功: ${CYAN}$out_archive${RESET}"
        else
            echo -e "${RED}[Failure]${RESET} 压缩失败: ${YELLOW}$out_archive${RESET}" >&2
        fi
        return $c_status
    fi

    # ================= 2. 解压模式逻辑 =================
    local target_file
    for target_file in "${targets[@]}"; do
        if [[ ! -f "$target_file" ]]; then
            echo -e "${RED}[Error]${RESET} 文件不存在或不是常规文件: ${YELLOW}$target_file${RESET}" >&2
            continue
        fi

        if [[ ! -r "$target_file" ]]; then
            echo -e "${RED}[Error]${RESET} 文件无可读权限: ${YELLOW}$target_file${RESET}" >&2
            continue
        fi

        local file_name="${target_file:t}"
        local stem="${file_name%.*}"

        if [[ "$file_name" == *.tar.gz || "$file_name" == *.tar.bz2 || "$file_name" == *.tar.xz || "$file_name" == *.tar.zst || "$file_name" == *.tgz || "$file_name" == *.tbz2 || "$file_name" == *.txz || "$file_name" == *.tzst ]]; then
            stem="${file_name%%.tar.*}"
            stem="${stem%%.tgz}"
            stem="${stem%%.tbz2}"
            stem="${stem%%.txz}"
            stem="${stem%%.tzst}"
        fi

        # 解压依赖预检
        case "${file_name:l}" in
            *.tar.xz|*.txz)      zfl_require xz || return 1 ;;
            *.tar.zst|*.tzst)     zfl_require zstd || return 1 ;;
            *.zip|*.jar|*.war)    zfl_require unzip || return 1 ;;
            *.7z)                 zfl_require 7z || return 1 ;;
            *.rar)
                if ! command -v unrar &>/dev/null && ! command -v 7z &>/dev/null; then
                    zfl_require unrar || return 1
                fi
                ;;
            *.gz)                 zfl_require gunzip || return 1 ;;
            *.bz2)                zfl_require bunzip2 || return 1 ;;
            *.xz)                 zfl_require unxz || return 1 ;;
            *.zst)                zfl_require zstd || return 1 ;;
        esac

        echo -e "${GREEN}[extract]${RESET} 正在解压: ${CYAN}$file_name${RESET} ..."

        # 防“解压炸弹”判断逻辑
        local root_item_count=0
        case "${file_name:l}" in
            *.tar.gz|*.tgz|*.tar.bz2|*.tbz2|*.tar.xz|*.txz|*.tar.zst|*.tzst|*.tar)
                root_item_count=$(tar -tf "$target_file" 2>/dev/null | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u | wc -l)
                ;;
            *.zip|*.jar|*.war)
                root_item_count=$(unzip -l "$target_file" 2>/dev/null | awk 'NR>3 && $4!="" {print $4}' | grep -v '^---' | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u | wc -l)
                ;;
            *.7z)
                root_item_count=$(7z l "$target_file" 2>/dev/null | awk '/^----/{p=!p;next} p {print $6}' | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u | wc -l)
                ;;
            *.rar)
                if command -v unrar &>/dev/null; then
                    root_item_count=$(unrar l "$target_file" 2>/dev/null | awk '/^----/{p=!p;next} p {print $6}' | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u | wc -l)
                elif command -v 7z &>/dev/null; then
                    root_item_count=$(7z l "$target_file" 2>/dev/null | awk '/^----/{p=!p;next} p {print $6}' | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u | wc -l)
                fi
                ;;
        esac

        local dest_dir=""
        local created_dest=0
        if [[ $root_item_count -gt 1 ]]; then
            dest_dir="$stem"
            if [[ -d "$dest_dir" ]]; then
                local index=1
                while [[ -d "${stem}_${index}" ]]; do
                    ((index++))
                done
                dest_dir="${stem}_${index}"
            fi
            mkdir -p "$dest_dir"
            created_dest=1
            echo -e "${YELLOW}[Archive Bomb Defense]${RESET} 检测到包内包含多项文件，已创建专属目录: ${CYAN}$dest_dir/${RESET}"
        fi

        local d_status=0
        case "${file_name:l}" in
            *.tar.bz2|*.tbz2|*.tbz)
                if [[ $created_dest -eq 1 ]]; then
                    tar -xj -C "$dest_dir" -f "$target_file"
                else
                    tar -xjf "$target_file"
                fi
                d_status=$?
                ;;
            *.tar.gz|*.tgz)
                if [[ $created_dest -eq 1 ]]; then
                    tar -xz -C "$dest_dir" -f "$target_file"
                else
                    tar -xzf "$target_file"
                fi
                d_status=$?
                ;;
            *.tar.xz|*.txz)
                if [[ $created_dest -eq 1 ]]; then
                    tar -xJ -C "$dest_dir" -f "$target_file"
                else
                    tar -xJf "$target_file"
                fi
                d_status=$?
                ;;
            *.tar.zst|*.tzst)
                if [[ $created_dest -eq 1 ]]; then
                    tar --zstd -x -C "$dest_dir" -f "$target_file"
                else
                    tar --zstd -xf "$target_file"
                fi
                d_status=$?
                ;;
            *.tar)
                if [[ $created_dest -eq 1 ]]; then
                    tar -x -C "$dest_dir" -f "$target_file"
                else
                    tar -xf "$target_file"
                fi
                d_status=$?
                ;;
            *.zip|*.jar|*.war)
                if [[ $created_dest -eq 1 ]]; then
                    unzip -q "$target_file" -d "$dest_dir"
                else
                    unzip -q "$target_file"
                fi
                d_status=$?
                ;;
            *.rar)
                if command -v unrar &>/dev/null; then
                    if [[ $created_dest -eq 1 ]]; then
                        unrar x -idq "$target_file" "$dest_dir/"
                    else
                        unrar x -idq "$target_file"
                    fi
                    d_status=$?
                else
                    if [[ $created_dest -eq 1 ]]; then
                        7z x -o"$dest_dir" "$target_file" >/dev/null
                    else
                        7z x "$target_file" >/dev/null
                    fi
                    d_status=$?
                fi
                ;;
            *.7z)
                if [[ $created_dest -eq 1 ]]; then
                    7z x -o"$dest_dir" "$target_file" >/dev/null
                else
                    7z x "$target_file" >/dev/null
                fi
                d_status=$?
                ;;
            *.gz)
                gunzip -k "$target_file"
                d_status=$?
                ;;
            *.bz2)
                bunzip2 -k "$target_file"
                d_status=$?
                ;;
            *.xz)
                unxz -k "$target_file"
                d_status=$?
                ;;
            *.zst)
                zstd -d -k "$target_file"
                d_status=$?
                ;;
            *.z)
                uncompress "$target_file"
                d_status=$?
                ;;
            *)
                echo -e "${RED}[Error]${RESET} 不支持的解压格式: ${YELLOW}$file_name${RESET}" >&2
                d_status=1
                ;;
        esac

        if [[ $d_status -eq 0 ]]; then
            echo -e "${GREEN}[Success]${RESET} 解压完成: ${CYAN}$file_name${RESET}"
        else
            echo -e "${RED}[Failure]${RESET} 解压失败: ${YELLOW}$file_name${RESET}" >&2
        fi
    done
}

# 快捷别名
alias x=extract

# ================= 3. Tab 自动补全代理函数 =================
_extract() {
    local lang=${ZFL_LANG:-${LANG%%.*}}
    local -a options

    if [[ "$lang" == zh* ]]; then
        options=(
            '-c:切换为一键压缩模式'
            '--compress:切换为一键压缩模式'
            '-d:切换为解压模式 (默认行为)'
            '--decompress:切换为解压模式 (默认行为)'
            '-o:指定输出压缩包名称 (如 -o backup)'
            '--output:指定输出压缩包名称 (如 --output backup)'
            '--tar:打包为未压缩的 .tar 归档'
            '--tar.gz:使用 gzip 压缩打包 (.tar.gz / .tgz)'
            '--tgz:使用 gzip 压缩打包 (.tar.gz / .tgz)'
            '--tar.bz2:使用 bzip2 压缩打包 (.tar.bz2 / .tbz2)'
            '--tbz2:使用 bzip2 压缩打包 (.tar.bz2 / .tbz2)'
            '--tar.xz:使用 xz 极高压缩率打包 (.tar.xz / .txz)'
            '--txz:使用 xz 极高压缩率打包 (.tar.xz / .txz)'
            '--tar.zst:使用 zstd 极速高压缩率打包 (.tar.zst)'
            '--tzst:使用 zstd 极速高压缩率打包 (.tar.zst)'
            '--zip:压缩为通用 .zip 格式文件'
            '--7z:使用 7-Zip 高压缩率格式打包 (.7z)'
            '--rar:压缩为 RAR 归档文件 (.rar)'
            '-h:显示帮助信息'
            '--help:显示帮助信息'
        )
    else
        options=(
            '-c:Switch to compression mode'
            '--compress:Switch to compression mode'
            '-d:Switch to decompression mode (default)'
            '--decompress:Switch to decompression mode (default)'
            '-o:Specify output archive filename'
            '--output:Specify output archive filename'
            '--tar:Pack into uncompressed .tar archive'
            '--tar.gz:Compress with gzip (.tar.gz / .tgz)'
            '--tgz:Compress with gzip (.tar.gz / .tgz)'
            '--tar.bz2:Compress with bzip2 (.tar.bz2 / .tbz2)'
            '--tbz2:Compress with bzip2 (.tar.bz2 / .tbz2)'
            '--tar.xz:Compress with xz (.tar.xz / .txz)'
            '--txz:Compress with xz (.tar.xz / .txz)'
            '--tar.zst:Compress with zstd (.tar.zst)'
            '--tzst:Compress with zstd (.tar.zst)'
            '--zip:Compress into universal .zip archive'
            '--7z:Compress with 7-Zip (.7z)'
            '--rar:Compress into RAR archive (.rar)'
            '-h:Show help menu'
            '--help:Show help menu'
        )
    fi

    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -s -S \
        '(-c --compress -d --decompress)'{-c,--compress}'[切换为一键压缩模式]' \
        '(-c --compress -d --decompress)'{-d,--decompress}'[切换为解压模式 (默认)]' \
        '(-o --output)'{-o,--output}'[指定输出文件名]:filename:_files' \
        '--tar[打包为 .tar 归档]' \
        '--tar.gz[压缩为 .tar.gz]' \
        '--tgz[压缩为 .tgz]' \
        '--tar.bz2[压缩为 .tar.bz2]' \
        '--tbz2[压缩为 .tbz2]' \
        '--tar.xz[压缩为 .tar.xz]' \
        '--txz[压缩为 .txz]' \
        '--tar.zst[压缩为 .tar.zst]' \
        '--tzst[压缩为 .tzst]' \
        '--zip[压缩为 .zip]' \
        '--7z[压缩为 .7z]' \
        '--rar[压缩为 .rar]' \
        '(-h --help)'{-h,--help}'[显示帮助信息]' \
        '*:files:_files'
}
