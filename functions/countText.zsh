##
# CountText - 统计文件中的字数/汉字数
#
# 功能：
#   根据传入的参数，统计文件中的汉字数或单词数。
#
# 参数：
#   $1 (string) - 模式参数：
#       -zh 或 -ch : 统计汉字数（匹配中文字符）
#       -cn        : 统计单词数（按空格分隔）
#   $2 (string) - 文件路径
#
# 返回值：
#   输出统计结果到标准输出，并返回 0 表示成功。
#   如果文件不存在或参数错误，返回 1。
#
# 示例：
#   CountText -zh my.txt   # 输出汉字数
#   CountText -cn my.txt   # 输出单词数
#
countText() {
    local mode=$1
    local file=$2

    if [[ "$mode" != "-h" ]] && { [[ -z "$file" ]] || [[ ! -f "$file" ]] || [[ ! -r "$file" ]]; }; then
        echo "ERROR: 文件不存在或者文件不可读" >&2
        return 1
    fi

    case "$mode" in
        -zh|-ch)
            local count
            count=$(grep -oP '[\p{Han}]' "$file" | wc -l)
            echo "$count"
            return 0
            ;;
        -cn)
            local count
            count=$(wc -w < "$file")
            echo "$count"
            return 0
            ;;
        -h)
            echo " CountText - 统计文件中的字数/汉字数                  "
            echo "                                                      "
            echo " 功能：                                               "
            echo "   根据传入的参数，统计文件中的汉字数或单词数。       "
            echo "                                                      "
            echo " 参数：                                               "
            echo "   $1 (string) - 模式参数：                           "
            echo "       -zh 或 -ch : 统计汉字数（匹配中文字符）        "
            echo "       -cn        : 统计单词数（按空格分隔）          "
            echo "       -h         : 显示帮助                          "
            echo "   $2 (string) - 文件路径                             "
            echo "                                                      "
            echo " 返回值：                                             "
            echo "   输出统计结果到标准输出，并返回 0 表示成功。        "
            echo "   如果文件不存在或参数错误，返回 1。                 "
            echo "                                                      "
            echo " 示例：                                               "
            echo "   CountText -zh my.txt   # 输出汉字数                "
            echo "   CountText -cn my.txt   # 输出单词数                "
            return 0
            ;;
        *)
            echo "ERROR:未知参数 $mode" >&2
            return 1
            ;;
        esac
        return 0
}
