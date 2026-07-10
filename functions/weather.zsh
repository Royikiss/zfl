#? 名称: weather
#? 描述: 终端快速查询实时天气与天气预报
#? 作者: Royi
#? 版本: 1.0.0
#? 依赖: curl
#? 用法: weather [城市名称]
#? 示例: weather beijing

weather() {
    zfl_require curl || return 1
    load_color GREEN YELLOW RESET
    echo -e "${GREEN}[weather]${RESET} ${YELLOW}[$1]${RESET} weather searching ..."
    curl wttr.in/$1
}
