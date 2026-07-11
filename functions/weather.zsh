#? name: weather
#? description: Query real-time weather and weather forecast in terminal
#? author: Royi
#? version: 1.0.0
#? deps: curl
#? usage: weather [city_name]
#? example: weather beijing

weather() {
    zfl_require curl || return 1
    load_color GREEN YELLOW RESET
    local lang=${ZFL_LANG:-${LANG%%.*}}
    if [[ "$lang" == zh* ]]; then
        echo -e "${GREEN}[weather]${RESET} ${YELLOW}[$1]${RESET} 正在查询天气..."
    else
        echo -e "${GREEN}[weather]${RESET} ${YELLOW}[$1]${RESET} weather searching ..."
    fi
    curl wttr.in/$1
}

