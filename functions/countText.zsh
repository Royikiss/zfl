#? name: countText
#? description: Count words or Chinese characters in a text file based on the specified mode
#? author: Royi
#? version: 1.0.0
#? deps: grep, wc
#? usage: countText <mode> <file_path>
#? example: countText -zh document.txt

countText() {
    zfl_require grep wc || return 1
    local mode=$1
    local file=$2
    local lang=${ZFL_LANG:-${LANG%%.*}}

    if [[ "$mode" != "-h" ]] && { [[ -z "$file" ]] || [[ ! -f "$file" ]] || [[ ! -r "$file" ]]; }; then
        if [[ "$lang" == zh* ]]; then
            echo "ERROR: 文件不存在或者文件不可读" >&2
        else
            echo "ERROR: File does not exist or is not readable" >&2
        fi
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
            if [[ "$lang" == zh* ]]; then
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
            else
                echo " CountText - Count words or Chinese characters in a file "
                echo "                                                         "
                echo " Purpose:                                                "
                echo "   Count characters or words in a file depending on mode."
                echo "                                                         "
                echo " Arguments:                                              "
                echo "   $1 (string) - Mode parameter:                          "
                echo "       -zh or -ch : Count Chinese characters             "
                echo "       -cn        : Count words (whitespace delimited)   "
                echo "       -h         : Show help                            "
                echo "   $2 (string) - File path                               "
                echo "                                                         "
                echo " Returns:                                                "
                echo "   Prints count to stdout, returns 0 on success.         "
                echo "   Returns 1 if file does not exist or arguments invalid."
                echo "                                                         "
                echo " Examples:                                               "
                echo "   CountText -zh my.txt   # Output Chinese character count"
                echo "   CountText -cn my.txt   # Output word count            "
            fi
            return 0
            ;;
        *)
            if [[ "$lang" == zh* ]]; then
                echo "ERROR: 未知参数 $mode" >&2
            else
                echo "ERROR: Unknown option $mode" >&2
            fi
            return 1
            ;;
        esac
        return 0
}

