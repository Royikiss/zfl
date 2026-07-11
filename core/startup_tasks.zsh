# Startup task runner
# Behavior:
# 1) Reads commands from core/startup_task_commands.zsh (one per line)
# 2) Ignores empty lines and comments
# 3) Parses arguments according to shell rules and executes them
# 4) Logs starting time, elapsed time, and exit code for each task

if [[ -o interactive ]]; then
    local task_file="$ZFL_HOME/core/startup_task_commands.zsh"

    if [[ -f "$task_file" ]]; then
        local line line_trimmed task_str
        local -a args
        local cmd
        local start_ts end_ts elapsed_sec exit_code
        local lang=${ZFL_LANG:-${LANG%%.*}}
        load_color RED GREEN YELLOW BRIGHT_BLUE RESET

        # Use independent file descriptor (FD 3) to read the task file,
        # avoiding taking over stdin (otherwise interactive commands in tasks would read the file)
        exec 3< "$task_file"
        while IFS= read -r line <&3 || [[ -n "$line" ]]; do
            # Trim leading/trailing whitespace
            line_trimmed="${line#${line%%[![:space:]]*}}"
            line_trimmed="${line_trimmed%${line_trimmed##*[![:space:]]}}"

            # Ignore empty lines and comments
            [[ -z "$line_trimmed" ]] && continue
            [[ "$line_trimmed" == \#* ]] && continue

            task_str="$line_trimmed"
            # Use (Q)+(z) to split into shell tokens and remove quotes:
            # - Supports escaped format written by add_task (e.g. echo hello\ world)
            # - Supports handwritten quotes format (e.g. echo "hello world")
            args=(${(Q)${(z)task_str}})

            cmd=$args[1]

            # Compatibility with legacy task formats
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
                if [[ "$lang" == zh* ]]; then
                    echo -e "${BRIGHT_BLUE}[Startup]${RESET} 开始: ${task_str}"
                else
                    echo -e "${BRIGHT_BLUE}[Startup]${RESET} Start: ${task_str}"
                fi

                "${(@)args}"
                exit_code=$?

                end_ts=$(date +%s)
                elapsed_sec=$(( end_ts - start_ts ))

                if (( exit_code == 0 )); then
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${GREEN}[Startup]${RESET} 完成: ${task_str} | exit=${exit_code} | 耗时=${elapsed_sec}s"
                    else
                        echo -e "${GREEN}[Startup]${RESET} Completed: ${task_str} | exit=${exit_code} | elapsed=${elapsed_sec}s"
                    fi
                else
                    if [[ "$lang" == zh* ]]; then
                        echo -e "${RED}[Startup]${RESET} 失败: ${task_str} | exit=${exit_code} | 耗时=${elapsed_sec}s"
                    else
                        echo -e "${RED}[Startup]${RESET} Failed: ${task_str} | exit=${exit_code} | elapsed=${elapsed_sec}s"
                    fi
                fi
            else
                if [[ "$lang" == zh* ]]; then
                    echo -e "${RED}[Startup] 命令不存在:${RESET} $cmd | 原始: $task_str"
                else
                    echo -e "${RED}[Startup] Command does not exist:${RESET} $cmd | raw: $task_str"
                fi
            fi
        done
        exec 3<&-
    else
        local lang=${ZFL_LANG:-${LANG%%.*}}
        load_color YELLOW RESET
        if [[ "$lang" == zh* ]]; then
            echo -e "${YELLOW}[Startup] 任务文件不存在:${RESET} $task_file"
        else
            echo -e "${YELLOW}[Startup] Task file does not exist:${RESET} $task_file"
        fi
    fi
fi

