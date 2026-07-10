#? 名称: verge-ipc-link
#? 描述: 建立 Clash Verge 服务的 IPC Socket 软链接配置辅助
#? 作者: Royi
#? 版本: 1.0.0
#? 依赖: 
#? 用法: verge-ipc-link
#? 示例: verge-ipc-link

_verge_ipc_link_help() {
    cat <<'EOF'
verge-ipc-link - 建立 Clash Verge 服务 IPC Socket 软连接

用法:
  verge-ipc-link [选项]

选项:
  -h, --help     显示本帮助并退出

说明:
  - 创建 /tmp/verge/ 目录
  - 将 /tmp/clash-verge-service-ipc-test/service.sock
    软连接到 /tmp/verge/clash-verge-service.sock
  - 使得 GUI 能找到服务实际生成的 Socket 路径

等价手动操作:
  sudo mkdir -p /tmp/verge
  sudo ln -sf /tmp/clash-verge-service-ipc-test/service.sock /tmp/verge/clash-verge-service.sock
EOF
}

verge-ipc-link() {
    local arg
    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                _verge_ipc_link_help
                return 0
                ;;
            *)
                echo "verge-ipc-link: 未知参数: $arg" >&2
                echo "Try: verge-ipc-link --help" >&2
                return 2
                ;;
        esac
    done

    load_color GREEN YELLOW RED RESET

    local src="/tmp/clash-verge-service-ipc-test/service.sock"
    local target_dir="/tmp/verge"
    local target="${target_dir}/clash-verge-service.sock"

    # 检查源 socket 是否存在
    if [[ ! -S "$src" ]]; then
        echo -e "${YELLOW}[verge-ipc-link] 源服务端 socket 不存在: ${src}${RESET}"
        echo -e "${YELLOW}请确保 Clash Verge 服务已启动并生成该 socket${RESET}"
    fi

    echo -e "${GREEN}[verge-ipc-link] 创建目录: ${target_dir}${RESET}"
    sudo mkdir -p "$target_dir" || {
        echo -e "${RED}[verge-ipc-link] 目录创建失败${RESET}" >&2
        return 1
    }

    echo -e "${GREEN}[verge-ipc-link] 建立软连接:${RESET}"
    echo "  ${src}  →  ${target}"
    sudo ln -sf "$src" "$target" || {
        echo -e "${RED}[verge-ipc-link] 软连接创建失败${RESET}" >&2
        return 1
    }

    echo -e "${GREEN}[verge-ipc-link] 完成${RESET}"
}
