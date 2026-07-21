#? name: extract
#? description: Universal auto-decompressor and compressor with format options, password encryption, fallbacks, and Tab completion
#? author: Royi
#? version: 1.7.0
#? protected: true
#? deps: tar, zip, unzip, 7z, unrar, gzip, bzip2, xz, zstd
#? usage: extract archive... | extract --<format> [-p password] [-o output] target...
#? example: extract archive.zip; extract --zip -p 123456 folder/; extract --7z -p mypass -o secret files/

extract() {
    zfl_require tar || return 1
    load_color RED GREEN YELLOW CYAN BLUE BOLD RESET
    local lang=${ZFL_LANG:-${LANG%%.*}}

    if [[ $# -eq 0 ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${GREEN}[extract]${RESET} ${BOLD}万能解压与一键压缩工具 (ZFL Universal Decompressor & Compressor)${RESET}"
            echo -e "用法:"
            echo -e "  解压 (默认模式): ${CYAN}extract${RESET} [-p 密码] <压缩包1> [压缩包2 ...]"
            echo -e "  压缩 (指定格式): ${CYAN}extract${RESET} --<格式> [-p 密码] [-o 输出名] <目标1> [目标2 ...]"
            echo -e "格式选项: ${YELLOW}--zip, --tar.gz, --tar.bz2, --tar.xz, --tar.zst, --7z, --tar, --rar${RESET}"
            echo -e "提示: 支持使用 ${CYAN}-p <密码>${RESET} 加密压缩或解压带密码的压缩包。"
        else
            echo -e "${GREEN}[extract]${RESET} ${BOLD}Universal Decompressor & Compressor (ZFL)${RESET}"
            echo -e "Usage:"
            echo -e "  Decompress (default): ${CYAN}extract${RESET} [-p password] <archive1> [archive2 ...]"
            echo -e "  Compress (option):   ${CYAN}extract${RESET} --<format> [-p password] [-o output_name] <target1> [target2 ...]"
            echo -e "Format Options: ${YELLOW}--zip, --tar.gz, --tar.bz2, --tar.xz, --tar.zst, --7z, --tar, --rar${RESET}"
            echo -e "Tip: Use ${CYAN}-p <password>${RESET} to encrypt archives or extract password-protected files."
        fi
        return 0
    fi

    local mode="decompress"
    local target_format=""
    local output_name=""
    local password=""
    local -a targets=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -o|--output)
                if [[ -n "$2" && "$2" != -* ]]; then
                    output_name="$2"
                    shift 2
                else
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${RED}[Error]${RESET} -o/--output 需要指定输出文件名" >&2
                    else
                        echo -e "${RED}[Error]${RESET} -o/--output requires an output filename" >&2
                    fi
                    return 1
                fi
                ;;
            -p|--password|--pass)
                if [[ -n "$2" && "$2" != -* ]]; then
                    password="$2"
                    shift 2
                else
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${RED}[Error]${RESET} -p/--password 需要指定密码内容" >&2
                    else
                        echo -e "${RED}[Error]${RESET} -p/--password requires a password value" >&2
                    fi
                    return 1
                fi
                ;;
            --tar)
                mode="compress"
                target_format="tar"
                shift
                ;;
            --tar.gz|--tgz|-gz|--gz)
                mode="compress"
                target_format="tar.gz"
                shift
                ;;
            --tar.bz2|--tbz2|-bz2|--bz2)
                mode="compress"
                target_format="tar.bz2"
                shift
                ;;
            --tar.xz|--txz|-xz|--xz)
                mode="compress"
                target_format="tar.xz"
                shift
                ;;
            --tar.zst|--tzst|-zst|--zst)
                mode="compress"
                target_format="tar.zst"
                shift
                ;;
            --zip|-zip)
                mode="compress"
                target_format="zip"
                shift
                ;;
            --7z|-7z)
                mode="compress"
                target_format="7z"
                shift
                ;;
            --rar|-rar)
                mode="compress"
                target_format="rar"
                shift
                ;;
            -h|--help)
                extract
                return 0
                ;;
            -*)
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[Error]${RESET} 未知选项: ${YELLOW}$1${RESET}" >&2
                else
                    echo -e "${RED}[Error]${RESET} Unknown option: ${YELLOW}$1${RESET}" >&2
                fi
                return 1
                ;;
            *)
                targets+=("$1")
                shift
                ;;
        esac
    done

    if [[ ${#targets[@]} -eq 0 ]]; then
        if [[ "$lang" == zh* ]]; then
            echo -e "${RED}[Error]${RESET} 请指定需要处理的目标文件或目录" >&2
        else
            echo -e "${RED}[Error]${RESET} Please specify target files or directories to process" >&2
        fi
        return 1
    fi

    # ================= 1. 压缩模式逻辑 (支持密码加密) =================
    if [[ "$mode" == "compress" ]]; then
        local first_target="${targets[1]}"
        first_target="${first_target%/}"
        local base_name="${first_target:t}"

        local out_archive=""
        if [[ -n "$output_name" ]]; then
            out_archive="$output_name"
        else
            out_archive="$base_name"
        fi

        case "$target_format" in
            tar)      [[ "$out_archive" != *.tar ]] && out_archive="${out_archive}.tar" ;;
            tar.gz)   [[ "$out_archive" != *.tar.gz && "$out_archive" != *.tgz ]] && out_archive="${out_archive}.tar.gz" ;;
            tar.bz2)  [[ "$out_archive" != *.tar.bz2 && "$out_archive" != *.tbz2 ]] && out_archive="${out_archive}.tar.bz2" ;;
            tar.xz)   [[ "$out_archive" != *.tar.xz && "$out_archive" != *.txz ]] && out_archive="${out_archive}.tar.xz" ;;
            tar.zst)  [[ "$out_archive" != *.tar.zst && "$out_archive" != *.tzst ]] && out_archive="${out_archive}.tar.zst" ;;
            zip)      [[ "$out_archive" != *.zip ]] && out_archive="${out_archive}.zip" ;;
            7z)       [[ "$out_archive" != *.7z ]] && out_archive="${out_archive}.7z" ;;
            rar)      [[ "$out_archive" != *.rar ]] && out_archive="${out_archive}.rar" ;;
        esac

        # 重名防覆盖
        if [[ -e "$out_archive" ]]; then
            local stem_name="${out_archive%.*}"
            local ext_name="${out_archive#*.}"
            if [[ "$out_archive" == *.tar.gz || "$out_archive" == *.tar.bz2 || "$out_archive" == *.tar.xz || "$out_archive" == *.tar.zst ]]; then
                stem_name="${out_archive%%.tar.*}"
                ext_name="tar.${out_archive#*.tar.}"
            fi

            local idx=1
            local new_archive="${stem_name}_${idx}.${ext_name}"
            while [[ -e "$new_archive" ]]; do
                ((idx++))
                new_archive="${stem_name}_${idx}.${ext_name}"
            done
            if [[ "$lang" == zh* ]]; then
                echo -e "${YELLOW}[Collision Defense]${RESET} 检测到当前目录已存在 ${CYAN}$out_archive${RESET}，为防覆盖自动存为: ${CYAN}$new_archive${RESET}"
            else
                echo -e "${YELLOW}[Collision Defense]${RESET} Target ${CYAN}$out_archive${RESET} already exists, auto saving to: ${CYAN}$new_archive${RESET}"
            fi
            out_archive="$new_archive"
        fi

        local enc_msg=""
        [[ -n "$password" ]] && enc_msg=" [${YELLOW}🔒 Password Encrypted${RESET}]"

        if [[ "$lang" == zh* ]]; then
            echo -e "${GREEN}[compress]${RESET} 正在打包压缩至: ${CYAN}$out_archive${RESET} (${YELLOW}$target_format${RESET})${enc_msg} ..."
        else
            echo -e "${GREEN}[compress]${RESET} Packing and compressing to: ${CYAN}$out_archive${RESET} (${YELLOW}$target_format${RESET})${enc_msg} ..."
        fi

        local c_status=0
        case "$target_format" in
            tar|tar.gz|tar.bz2|tar.xz|tar.zst)
                if [[ -n "$password" ]]; then
                    # Tar 不原生支持文件加密，转用 7z 加密打包
                    if zfl_require 7z; then
                        7z a -p"$password" "$out_archive" "${targets[@]}" >/dev/null
                        c_status=$?
                    else
                        return 1
                    fi
                else
                    case "$target_format" in
                        tar)     tar -cf "$out_archive" "${targets[@]}" ;;
                        tar.gz)  tar -czf "$out_archive" "${targets[@]}" ;;
                        tar.bz2) tar -cjf "$out_archive" "${targets[@]}" ;;
                        tar.xz)  zfl_require xz || return 1; tar -cJf "$out_archive" "${targets[@]}" ;;
                        tar.zst) zfl_require zstd || return 1; tar --zstd -cf "$out_archive" "${targets[@]}" ;;
                    esac
                    c_status=$?
                fi
                ;;
            zip)
                if [[ -n "$password" ]]; then
                    if command -v zip &>/dev/null; then
                        zip -r -q -P "$password" "$out_archive" "${targets[@]}"
                        c_status=$?
                    elif zfl_require 7z; then
                        7z a -tzip -p"$password" "$out_archive" "${targets[@]}" >/dev/null
                        c_status=$?
                    fi
                else
                    if command -v zip &>/dev/null; then
                        zip -r -q "$out_archive" "${targets[@]}"
                        c_status=$?
                    elif command -v 7z &>/dev/null; then
                        7z a -tzip "$out_archive" "${targets[@]}" >/dev/null
                        c_status=$?
                    else
                        zfl_require zip || return 1
                    fi
                fi
                ;;
            7z)
                zfl_require 7z || return 1
                if [[ -n "$password" ]]; then
                    7z a -p"$password" "$out_archive" "${targets[@]}" >/dev/null
                else
                    7z a "$out_archive" "${targets[@]}" >/dev/null
                fi
                c_status=$?
                ;;
            rar)
                if command -v rar &>/dev/null; then
                    if [[ -n "$password" ]]; then
                        rar a -idq -p"$password" "$out_archive" "${targets[@]}"
                    else
                        rar a -idq "$out_archive" "${targets[@]}"
                    fi
                    c_status=$?
                elif zfl_require 7z; then
                    if [[ -n "$password" ]]; then
                        7z a -p"$password" "$out_archive" "${targets[@]}" >/dev/null
                    else
                        7z a "$out_archive" "${targets[@]}" >/dev/null
                    fi
                    c_status=$?
                fi
                ;;
        esac

        if [[ $c_status -eq 0 ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${GREEN}[Success]${RESET} 压缩成功: ${CYAN}$out_archive${RESET}"
            else
                echo -e "${GREEN}[Success]${RESET} Compression completed: ${CYAN}$out_archive${RESET}"
            fi
        else
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[Failure]${RESET} 压缩失败: ${YELLOW}$out_archive${RESET}" >&2
            else
                echo -e "${RED}[Failure]${RESET} Compression failed: ${YELLOW}$out_archive${RESET}" >&2
            fi
        fi
        return $c_status
    fi

    # ================= 2. 解压模式逻辑 (支持密码解段) =================
    local target_file
    for target_file in "${targets[@]}"; do
        if [[ ! -f "$target_file" ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[Error]${RESET} 文件不存在或不是常规文件: ${YELLOW}$target_file${RESET}" >&2
            else
                echo -e "${RED}[Error]${RESET} File does not exist or is not a regular file: ${YELLOW}$target_file${RESET}" >&2
            fi
            continue
        fi

        if [[ ! -r "$target_file" ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[Error]${RESET} 文件无可读权限: ${YELLOW}$target_file${RESET}" >&2
            else
                echo -e "${RED}[Error]${RESET} File is not readable: ${YELLOW}$target_file${RESET}" >&2
            fi
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

        case "${file_name:l}" in
            *.tar.xz|*.txz)      zfl_require xz || return 1 ;;
            *.tar.zst|*.tzst)     zfl_require zstd || return 1 ;;
            *.zip|*.jar|*.war)
                if ! command -v unzip &>/dev/null && ! command -v 7z &>/dev/null; then
                    zfl_require unzip || return 1
                fi
                ;;
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

        if [[ "$lang" == zh* ]]; then
            echo -e "${GREEN}[extract]${RESET} 正在解压: ${CYAN}$file_name${RESET} ..."
        else
            echo -e "${GREEN}[extract]${RESET} Decompressing: ${CYAN}$file_name${RESET} ..."
        fi

        local root_item_count=0
        local single_root_item=""
        case "${file_name:l}" in
            *.tar.gz|*.tgz|*.tar.bz2|*.tbz2|*.tar.xz|*.txz|*.tar.zst|*.tzst|*.tar)
                local -a root_items=($(tar -tf "$target_file" 2>/dev/null | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u))
                root_item_count=${#root_items[@]}
                [[ $root_item_count -eq 1 ]] && single_root_item="${root_items[1]}"
                ;;
            *.zip|*.jar|*.war)
                if command -v unzip &>/dev/null; then
                    local -a root_items=($(unzip -l "$target_file" 2>/dev/null | awk 'NR>3 && $4!="" {print $4}' | grep -v '^---' | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u))
                    root_item_count=${#root_items[@]}
                    [[ $root_item_count -eq 1 ]] && single_root_item="${root_items[1]}"
                elif command -v 7z &>/dev/null; then
                    local -a root_items=($(7z l "$target_file" 2>/dev/null | awk '/^----/{p=!p;next} p {print $6}' | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u))
                    root_item_count=${#root_items[@]}
                    [[ $root_item_count -eq 1 ]] && single_root_item="${root_items[1]}"
                fi
                ;;
            *.7z)
                local p_flag=""
                [[ -n "$password" ]] && p_flag="-p${password}"
                local -a root_items=($(7z l $p_flag "$target_file" 2>/dev/null | awk '/^----/{p=!p;next} p {print $6}' | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u))
                root_item_count=${#root_items[@]}
                [[ $root_item_count -eq 1 ]] && single_root_item="${root_items[1]}"
                ;;
            *.rar)
                local p_flag=""
                [[ -n "$password" ]] && p_flag="-p${password}"
                if command -v unrar &>/dev/null; then
                    local -a root_items=($(unrar l $p_flag "$target_file" 2>/dev/null | awk '/^----/{p=!p;next} p {print $6}' | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u))
                    root_item_count=${#root_items[@]}
                    [[ $root_item_count -eq 1 ]] && single_root_item="${root_items[1]}"
                elif command -v 7z &>/dev/null; then
                    local -a root_items=($(7z l $p_flag "$target_file" 2>/dev/null | awk '/^----/{p=!p;next} p {print $6}' | sed -e 's@/.*@@' | grep -v '^\s*$' | sort -u))
                    root_item_count=${#root_items[@]}
                    [[ $root_item_count -eq 1 ]] && single_root_item="${root_items[1]}"
                fi
                ;;
        esac

        local dest_dir=""
        local created_dest=0

        if [[ $root_item_count -gt 1 ]]; then
            dest_dir="$stem"
            if [[ -e "$dest_dir" ]]; then
                local index=1
                while [[ -e "${stem}_${index}" ]]; do
                    ((index++))
                done
                dest_dir="${stem}_${index}"
            fi
            mkdir -p "$dest_dir"
            created_dest=1
            if [[ "$lang" == zh* ]]; then
                echo -e "${YELLOW}[Archive Bomb Defense]${RESET} 包内包含多项文件，已创建专属隔离目录: ${CYAN}$dest_dir/${RESET}"
            else
                echo -e "${YELLOW}[Archive Bomb Defense]${RESET} Archive contains multiple items, created dedicated folder: ${CYAN}$dest_dir/${RESET}"
            fi
        elif [[ $root_item_count -eq 1 && -n "$single_root_item" && -e "$single_root_item" ]]; then
            dest_dir="${stem}"
            if [[ -e "$dest_dir" ]]; then
                local index=1
                while [[ -e "${stem}_${index}" ]]; do
                    ((index++))
                done
                dest_dir="${stem}_${index}"
            fi
            mkdir -p "$dest_dir"
            created_dest=1
            if [[ "$lang" == zh* ]]; then
                echo -e "${YELLOW}[Collision Defense]${RESET} 检测到当前目录已存在 ${CYAN}$single_root_item${RESET}，为防覆盖自动解压至专属目录: ${CYAN}$dest_dir/${RESET}"
            else
                echo -e "${YELLOW}[Collision Defense]${RESET} Target ${CYAN}$single_root_item${RESET} already exists, auto extracting to: ${CYAN}$dest_dir/${RESET}"
            fi
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
                if command -v unzip &>/dev/null; then
                    local p_arg=()
                    [[ -n "$password" ]] && p_arg=(-P "$password")
                    if [[ $created_dest -eq 1 ]]; then
                        unzip -q "${p_arg[@]}" "$target_file" -d "$dest_dir"
                    else
                        unzip -q "${p_arg[@]}" "$target_file"
                    fi
                    d_status=$?
                elif command -v 7z &>/dev/null; then
                    local p_flag=""
                    [[ -n "$password" ]] && p_flag="-p${password}"
                    if [[ $created_dest -eq 1 ]]; then
                        7z x $p_flag -o"$dest_dir" "$target_file" >/dev/null
                    else
                        7z x $p_flag "$target_file" >/dev/null
                    fi
                    d_status=$?
                else
                    zfl_require unzip || return 1
                fi
                ;;
            *.rar)
                local p_flag=""
                [[ -n "$password" ]] && p_flag="-p${password}"
                if command -v unrar &>/dev/null; then
                    if [[ $created_dest -eq 1 ]]; then
                        unrar x -idq $p_flag "$target_file" "$dest_dir/"
                    else
                        unrar x -idq $p_flag "$target_file"
                    fi
                    d_status=$?
                else
                    if [[ $created_dest -eq 1 ]]; then
                        7z x $p_flag -o"$dest_dir" "$target_file" >/dev/null
                    else
                        7z x $p_flag "$target_file" >/dev/null
                    fi
                    d_status=$?
                fi
                ;;
            *.7z)
                local p_flag=""
                [[ -n "$password" ]] && p_flag="-p${password}"
                if [[ $created_dest -eq 1 ]]; then
                    7z x $p_flag -o"$dest_dir" "$target_file" >/dev/null
                else
                    7z x $p_flag "$target_file" >/dev/null
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
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[Error]${RESET} 不支持的解压格式: ${YELLOW}$file_name${RESET}" >&2
                else
                    echo -e "${RED}[Error]${RESET} Unsupported decompression format: ${YELLOW}$file_name${RESET}" >&2
                fi
                d_status=1
                ;;
        esac

        if [[ $d_status -eq 0 ]]; then
            if [[ "$lang" == zh* ]]; then
                echo -e "${GREEN}[Success]${RESET} 解压完成: ${CYAN}$file_name${RESET}"
            else
                echo -e "${GREEN}[Success]${RESET} Decompression completed: ${CYAN}$file_name${RESET}"
            fi
        else
            if [[ "$lang" == zh* ]]; then
                echo -e "${RED}[Failure]${RESET} 解压失败: ${YELLOW}$file_name${RESET}" >&2
            else
                echo -e "${RED}[Failure]${RESET} Decompression failed: ${YELLOW}$file_name${RESET}" >&2
            fi
        fi
    done
}

# 快捷别名
alias x=extract

# ================= 3. Tab 自动补全代理函数 =================
_extract() {
    local lang=${ZFL_LANG:-${LANG%%.*}}
    local curcontext="$curcontext" state line
    typeset -A opt_args

    if [[ "$lang" == zh* ]]; then
        _arguments -s -S \
            '(-o --output)'{-o,--output}'[指定输出文件名]:filename:_files' \
            '(-p --password --pass)'{-p,--password,--pass}'[指定压缩/解压密码]:password:' \
            '--zip[一键压缩为 .zip 格式]' \
            '--tar.gz[一键打包压缩为 .tar.gz]' \
            '--tgz[一键打包压缩为 .tgz]' \
            '--tar.bz2[一键打包压缩为 .tar.bz2]' \
            '--tbz2[一键打包压缩为 .tbz2]' \
            '--tar.xz[一键打包压缩为 .tar.xz (高压缩率)]' \
            '--txz[一键打包压缩为 .txz]' \
            '--tar.zst[一键打包压缩为 .tar.zst (极速高压缩率)]' \
            '--tzst[一键打包压缩为 .tzst]' \
            '--7z[一键压缩为 7-Zip (.7z)]' \
            '--rar[一键打包压缩为 .rar]' \
            '--tar[一键打包为未压缩的 .tar 归档]' \
            '(-h --help)'{-h,--help}'[显示帮助信息]' \
            '*:files:_files'
    else
        _arguments -s -S \
            '(-o --output)'{-o,--output}'[Specify output filename]:filename:_files' \
            '(-p --password --pass)'{-p,--password,--pass}'[Specify encryption/decryption password]:password:' \
            '--zip[Compress into .zip format]' \
            '--tar.gz[Compress into .tar.gz archive]' \
            '--tgz[Compress into .tgz archive]' \
            '--tar.bz2[Compress into .tar.bz2 archive]' \
            '--tbz2[Compress into .tbz2 archive]' \
            '--tar.xz[Compress into .tar.xz (high compression)]' \
            '--txz[Compress into .txz archive]' \
            '--tar.zst[Compress into .tar.zst (fast high compression)]' \
            '--tzst[Compress into .tzst archive]' \
            '--7z[Compress into 7-Zip (.7z)]' \
            '--rar[Compress into .rar archive]' \
            '--tar[Pack into uncompressed .tar archive]' \
            '(-h --help)'{-h,--help}'[Show help menu]' \
            '*:files:_files'
    fi
}
