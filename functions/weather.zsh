weather() {
    load_color GREEN YELLOW RESET
    echo -e "${GREEN}[weather]${RESET} ${YELLOW}[$1]${RESET} weather searching ..."
    curl wttr.in/$1
}
