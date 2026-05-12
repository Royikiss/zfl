# 启动任务执行器
# 行为：
# 1) 从 core/startup_task_commands.zsh 读取命令（每行一条）
# 2) 忽略空行与注释行
# 3) 按 shell 规则解析参数并执行
# 4) 记录每个任务的开始时间、耗时、退出码

if [[ -o interactive ]]; then
    local task_file="$ZFL_HOME/core/startup_task_commands.zsh"

    if [[ -f "$task_file" ]]; then
        local line line_trimmed task_str
        local -a args
        local cmd
        local start_ts end_ts elapsed_sec exit_code

        # 用独立 fd 读取任务文件，避免占用 stdin（否则任务里的 read 会误读任务文件内容）
        exec 3< "$task_file"
        while IFS= read -r line <&3 || [[ -n "$line" ]]; do
            # 去掉首尾空白，便于判定空行/注释
            line_trimmed="${line#${line%%[![:space:]]*}}"
            line_trimmed="${line_trimmed%${line_trimmed##*[![:space:]]}}"

            # 忽略空行与注释
            [[ -z "$line_trimmed" ]] && continue
            [[ "$line_trimmed" == \#* ]] && continue

            task_str="$line_trimmed"
            # 使用 (Q)+(z) 做 shell 级拆词与去引号：
            # - 支持 add_task 写入的转义格式（echo hello\ world）
            # - 支持手写引号格式（echo "hello world"）
            args=(${(Q)${(z)task_str}})

            cmd=$args[1]

            # 兼容历史任务行（如旧版写入的 echo\ hello\ world）
            if [[ -n "$cmd" ]] && ! whence "$cmd" > /dev/null && (( ${#args[@]} == 1 )); then
                local -a legacy_args
                legacy_args=("${(zQ)task_str}")
                if (( ${#legacy_args[@]} > 1 )); then
                    args=("${legacy_args[@]}")
                    cmd=$args[1]
                fi
            fi

            if [[ -z "$cmd" ]]; then
                continue
            fi

            if whence "$cmd" > /dev/null; then
                start_ts=$(date +%s)
                echo -e "${BRIGHT_BLUE}[Startup]${RESET} 开始: ${task_str}"

                "${(@)args}"
                exit_code=$?

                end_ts=$(date +%s)
                elapsed_sec=$(( end_ts - start_ts ))

                if (( exit_code == 0 )); then
                    echo -e "${GREEN}[Startup]${RESET} 完成: ${task_str} | exit=${exit_code} | 耗时=${elapsed_sec}s"
                else
                    echo -e "${RED}[Startup]${RESET} 失败: ${task_str} | exit=${exit_code} | 耗时=${elapsed_sec}s"
                fi
            else
                echo -e "${RED}[Startup] 命令不存在:${RESET} $cmd | 原始: $task_str"
            fi
        done
        exec 3<&-
    else
        echo -e "${YELLOW}[Startup] 任务文件不存在:${RESET} $task_file"
    fi
fi
