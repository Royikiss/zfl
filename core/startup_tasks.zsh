# 自动执行
#

## QAUpdate - 询问更新并执行
#
# 功能：
#   调用后根据传入时间计算是否更新，如果满足条件则执行
#   ‘yay -Syu’ 命令更新
#
# 条件：
#   参数时间相差一天
#
# 参数：
#   $1(string) - 昨天的更新时间
#   $2(string) - 今天的时间
#
# 返回值：
#   0: 更新成功
#   1: 更新失败
#   2: 用户选择不更新
#
QAUpdate () {
    load_color RED GREEN YELLOW RESET
    local last=$1
    local now=$2
    local days=$(( ( $(date -d "$now" +%s ) - $(date -d "$last" +%s) ) / 86400 ))

    echo -e "现在是${YELLOW} $now ${RESET}，距离上次更新已经${YELLOW} $days ${RESET}天了"
    echo -n -e "请问需要${GREEN}更新${RESET}吗？[${GREEN}Y${RESET}/${RED}n${RESET}]"
    
    read ans

    if [[ "$ans" == "Y" || "$ans" == "y" || -z "$ans" ]]; then
        if yay -Syu; then
            echo -e "${GREEN}更新成功${RESET} ✅"
            return 0
        else
            echo -e "${RED}更新失败${RESET} ❌"
            return 1
        fi
    else 
        echo -e "你没有更新，记得更新哟，输入 '${GREEN}update${RESET}' 即可更新~"
        echo -e "${YELLOW}Ps: [此提示将延迟到第二天进行]${RESET}"
        return 2
    fi
}

##
# WriteTo - 写入文本到指定文件并设置权限
#
# 功能：
#   将指定文本写入到目标文件。如果文件已存在，会先放宽权限再写入，
#   最后统一收紧权限为只读（400）。
#
# 参数：
#   $1 (string) - 文件路径
#   $2 (string) - 要写入的文本内容
#
# 返回值：
#   无显式返回值。写入成功时返回 0，失败时返回非 0。
#
# 示例：
#   WriteTo "/tmp/test.lock" "2025-12-05"
#
WriteTo() {
    local file=$1
    local text=$2

    [[ -f "$file" ]] && chmod 600 "$file"
    echo "$text" > "$file"
    chmod 400 "$file"
}

####################################### RUN #######################################

# 每天打开终端自动更新
# 检查 $HOME/.cache/zsh下的UpdateFlag.lock 文件
# 如果有：读取文件中的内容，获取更新日期
# 如果没有：创建这个文件
# 
# 根据日期检查今天是不是第二天
# 如果是：执行 QAUpdate 函数

UpdateFlag="$HOME/.cache/zsh/UpdateFlag.lock"

mkdir -p "$HOME/.cache/zsh"

if [[ -f "$UpdateFlag" ]]; then
    # 文件存在，读取上次更新日期
    last_update=$(cat "$UpdateFlag")
    today=$(date "+%Y-%m-%d")
    if [[ "$last_update" != "$today" ]]; then
        QAUpdate "$last_update" "$today"
        result=$?
        # 0：更新成功
        # 2：选择不更新
        if [[ $result -eq 0 ]]; then
            WriteTo "$UpdateFlag" "$today"
        elif [[ $result -eq 2 ]]; then
            WriteTo "$UpdateFlag" "$today"
        fi
    fi
else
    # 文件不存在，创建并写入今天日期
    today=$(date "+%Y-%m-%d")
    echo "首次创建更新标记文件，日期: $today"
    WriteTo "$UpdateFlag" "$today"
    QAUpdate "$today" "$today"
fi
