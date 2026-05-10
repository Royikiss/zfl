# 1. 定义任务表 (支持任意数量参数)
typeset -a ZFL_STARTUP_TASKS
ZFL_STARTUP_TASKS=(
    "check_update"
    # "weather Tokyo"
)

# 2. 执行逻辑
if [[ -o interactive ]]; then
    for task_str in "${ZFL_STARTUP_TASKS[@]}"; do
        # (z) 像 shell 解析命令行一样切分字符串
        # (Q) 去掉解析后的引号（例如把 'a b' 变成 a b）
        local args=("${(zQ)task_str}")
        local cmd=$args[1]

        # 检查函数、别名或命令是否存在
        if whence "$cmd" > /dev/null; then
            # "${(@)args}" 的含义：
            # @ 表示保留数组中的每个元素作为独立参数
            # 双引号包裹确保参数中的空格不被二次切分
            "${(@)args}"
        else
            echo -e "${RED}[Error]${RESET} Startup task not found: $cmd"
        fi
    done
fi
