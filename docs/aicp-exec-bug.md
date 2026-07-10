# AICP `--exec` 模式第二轮输入循环 EOF Bug

## 现象

1. 第 1 轮正常：粘贴 `<aicp:read>base.zsh</aicp:read>` → `---EOF---`，读取文件成功
2. 输出文件内容 → `[aicp/exec] 读取内容已累计`
3. `继续下一轮？[Y/n]` → 按 Enter
4. `[aicp/exec] 读取记录已复制到剪贴板`
5. 第 2 轮立即退出：`[aicp/exec] 空输入，退出`
6. 用户**未粘贴任何内容**，**未触发 Ctrl+D**

## 环境

| 属性 | 值 |
|------|------|
| 系统 | Linux |
| 桌面 | KDE Plasma |
| Shell | zsh |
| 剪贴板 | `wl-copy` (Wayland) |
| 粘贴方式 | Ctrl+Shift+V |
| 项目根 | `/home/royi/.config/zsh` |
| 文件 | `functions/aicp.zsh` |

## 关键代码

以下为 `_aicp_exec_loop` 经过所有修复后的当前版本（含调试插桩）：

### 准备阶段

```zsh
_aicp_debug() {
    [[ -z "$AICP_DEBUG" ]] && return
    local msg="$*" ts fd_state
    ts=$(date '+%H:%M:%S')
    if [[ -e /proc/$$/fd/3 ]]; then fd_state="fd3=OPEN"
    else fd_state="fd3=CLOSED"; fi
    echo -e "[DBG ${ts} ${fd_state}] ${msg}" >&2
}

_aicp_exec_loop() {
    local context_file="$1"
    local has_context=0
    [[ -n "$context_file" && -f "$context_file" ]] && has_context=1
    local round=1
    local accum_dir
    accum_dir=$(mktemp -d /tmp/aicp_exec.XXXXXX) || return 1
    local accum_file="$accum_dir/accumulated.txt"
    : > "$accum_file"

    exec 3</dev/tty
```

### 主循环（问题所在）

```zsh
    while true; do
        echo -e "${BLUE}[aicp/exec]${RESET} 第 ${round} 轮 — 上下文已就绪"
        echo -e "${YELLOW}粘贴 AI 回复（粘贴完成后输入 ---EOF---）：${RESET}"

        # ── 输入循环（第 2 轮在这里出问题） ──
        local ai_response="" read_rc=0
        while true; do
            IFS= read -r line <&3 || { read_rc=$?; break; }
            [[ "$line" == "---EOF---" ]] && break
            ai_response+="$line"$'\n'
        done
        [[ -z "$ai_response" ]] && { echo -e "${YELLOW}[aicp/exec]${RESET} 空输入，退出"; break; }

        # ── 解析器（走 here-string，不影响 fd 3） ──
        local in_read=0 in_write=0
        local -a read_targets=()
        local write_buf=""
        local -a write_diffs=()
        while IFS= read -r line; do
            ...  # 解析 <aicp:read>/<aicp:write> 标签
        done <<< "$ai_response"

        # ── 读取执行 ──
        for target in "${read_targets[@]}"; do
            content=$(cat -n "$file_path" 2>/dev/null)
            read_output+='<aicp:fetch ...>'$'\n'
        done

        echo "$read_output" >> "$accum_file"

        # ── 继续下一轮？ ──
        read next <&3
        [[ "$next" == "n" || "$next" == "N" ]] && break

        round=$((round + 1))

        # ── 剪贴板复制（嫌疑操作） ──
        if [[ -s "$accum_file" ]]; then
            cat "$accum_file" | wl-copy
            echo -e "${GREEN}[aicp/exec]${RESET} 读取记录已复制到剪贴板"
        fi

        # ── 回到循环顶部，进入第 2 轮 ──
    done

    exec 3<&-
```

## 调试日志（`AICP_DEBUG=1`）

完整日志：

```
[DBG 19:00:38 fd3=CLOSED] ENTER _aicp_exec_loop, context_file=[], has_context=0, ZFL_HOME=/home/royi/.config/zsh
[DBG 19:00:38 fd3=OPEN] exec 3</dev/tty done, PID=50587

═══════════════════════════════════════════════
[aicp/exec] 第 1 轮 — 上下文已就绪
粘贴 AI 回复（粘贴完成后输入 ---EOF---）：
[DBG 19:00:38 fd3=OPEN] 第 1 轮: 开始阻塞等待 fd3 输入...
<aicp:read>base.zsh</aicp:read>
---EOF---
[DBG 19:02:17 fd3=OPEN] 读到行: [\<aicp:read\>base.zsh\</aicp:read\>]
[DBG 19:02:17 fd3=OPEN] 读到 ---EOF---, 退出输入循环
[DBG 19:02:17 fd3=OPEN] 第 1 轮: 读完, rc=0, 共 2 行, len=32
[DBG 19:02:17 fd3=OPEN] ai_response 非空, 首行=[<aicp:read>base.zsh</aicp:read>]
[DBG 19:02:17 fd3=OPEN] 开始解析 ai_response (32 字符)
[DBG 19:02:17 fd3=OPEN] 解析完毕: read_targets=1, write_diffs=0

→ 读取请求:
  base.zsh:
     1  # 基础配置:不许动
     2
     3  export ZFL_HOME="${0:A:h}"
     4  ...

[aicp/exec] 读取内容已累计

继续下一轮？[Y/n] 
[DBG 19:02:23 fd3=OPEN] 继续下一轮? 输入=[]
[aicp/exec] 读取记录已复制到剪贴板
[DBG 19:02:23 fd3=OPEN] 第 2 轮结束, 即将回到循环顶部

═══════════════════════════════════════════════
[aicp/exec] 第 2 轮 — 上下文已就绪
粘贴 AI 回复（粘贴完成后输入 ---EOF---）：
[DBG 19:02:23 fd3=OPEN] 第 2 轮: 开始阻塞等待 fd3 输入...
[DBG 19:02:23 fd3=OPEN] read 返回非零: rc=1, line=['']
[DBG 19:02:23 fd3=OPEN] 第 2 轮: 读完, rc=1, 共 1 行, len=0
[DBG 19:02:23 fd3=OPEN] ai_response 为空, 退出!
[aicp/exec] 空输入，退出
[DBG 19:02:23 fd3=OPEN] while true 退出, 准备 exec 3<&-
```

## Bug 定位

### 核心证据

| 证据 | 含义 |
|------|------|
| `fd3=OPEN` 贯穿全程 | fd 3 未被关闭 |
| `rc=1` | zsh `read` 返回码 1 = **EOF 或错误**（非正常读取） |
| `line=['']` | 读取没有内容 |
| `共 1 行, len=0` | `wc -l <<< ""` 恒为 1（here-string 自动补换行），实际 `ai_response` 长度为 0 |
| 19:02:23 同一秒内完成所有操作 | 第 2 轮 `read` 完全没有阻塞 |

**结论**：第 2 轮第一次调用 `IFS= read -r line <&3` 就立即返回 EOF（rc=1），没有等待用户输入。

### 已排除的假设

| 假设 | 排除理由 |
|------|----------|
| fd 3 被关闭 | `fd3=OPEN` 日志确认 |
| paste 残留输入 | `read -t 0` 清空后仍复现 |
| `read < /dev/tty` vs `read <&3` 差异 | 两种方式都试过，一样 |
| 子 shell `$()` 中操作 tty | 已改用内联 `while true; do read <&3`，无命令替换 |

### 嫌疑区间

第 1 轮 `read next <&3`（接收 Enter，返回空行）→ 剪贴板复制 `cat "$accum_file" \| wl-copy` → 第 2 轮 `while read <&3`。

**具体来说**：在已读 `read next <&3` 之后、回绕到循环顶部进入下一轮 `read <&3` 之间，剪贴板复制操作可能造成了某种副作用。

## 尝试过的修复（均无效）

| 修复 | 改动 | 结果 |
|------|------|------|
| 1. patch 路径修正 | `cd /` → `cd "$ZFL_HOME"` | 无关 |
| 2. 行号修正 | `cat -n` → `nl -ba -v` | 无关 |
| 3. 统一 fd 交互 | `read confirm` → `read confirm < /dev/tty`; `read next` → `read next < /dev/tty` | 无效 |
| 4. 独立读取函数 + 缓冲区清空 | `_aicp_exec_read_tty()` 函数，内用 `read -t 0` 清残存 | 无效 |
| 5. 持久 fd 替代反复开闭 | `exec 3</dev/tty` + `done <&3` 代替 `done < /dev/tty` | 无效 |
| 6. 逐行逐次显式读（当前调试版） | `while true; do IFS= read -r line <&3 || break; ... done` | 无效，暴露了 rc=1 |

## 最终确认的根因

### 主因：wl-copy 后台 Daemon 通过 O_NONBLOCK 污染终端 fd

Wayland 剪贴板工具 `wl-copy` 的默认行为是：读取完输入后 **Fork 出一个后台守护进程**（Daemon）在后台持续提供剪贴板数据，前台父进程退出。

#### 核心机制（Linux 文件描述符污染）

1. **fd 继承**：`cat file | wl-copy` 通过管道执行，wl-copy 的子进程（Daemon）继承了 Zsh 的全部文件描述符，包括 fd 3（指向 `/dev/tty`）。

2. **O_NONBLOCK 污染**：Wayland 客户端库（libwayland-client）使用 epoll 处理异步事件。wl-copy 的 Daemon 进程会遍历或操作继承的 fd，将它们设为 `O_NONBLOCK`（非阻塞模式）。

3. **文件状态标志共享**：在 Linux 中，`O_NONBLOCK` 是绑定在 **Open File Description**（内核级打开文件表项）上的，**而不是单独的 fd 编号上**。当 Daemon 将它继承的 fd 3 设为 O_NONBLOCK 时，由于它和 Zsh 父进程的 fd 3 指向同一个 Open File Description，**Zsh 的 fd 3 也会变成非阻塞模式**。

4. **结果**：`read <&3` 发现终端缓冲区无用户输入，因为 O_NONBLOCK 标志，系统调用 `read(2)` 不阻塞等待，立即返回 `-1` 和 `EAGAIN`。Zsh 内建 `read` 将此视为 EOF，返回 rc=1。

#### 为什么之前 "每次重新 open /dev/tty" 也无效

重新 `open("/dev/tty")` 确实会创建新的 Open File Description（默认阻塞模式）。但如果 wl-copy 的 Daemon 还通过 `tcsetattr` 禁用了终端的 `ICANON`（规范模式）等属性，则 termios 是终端级别的属性，即使重新 open 也会继承非规范模式，导致 `read` 行为异常。

### 次因：外部剪贴板调用（连环杀手）

`_aicp_exec_loop` 之外还有 3 处 `cat "$tmp_file" | wl-copy`（`functions/aicp.zsh` 第 887/890/893 行），在进入循环之前就执行了。wl-copy 的 Daemon 在这时就已污染了终端状态，导致随后 `exec 3</dev/tty` 和 `read <&3` 成为受害者。

## 最终修复

### 原理：物理级隔离 wl-copy/xclip/pbcopy 进程

对 `aicp.zsh` 中全部 **7 处**剪贴板调用实施统一的隔离策略：

1. **`< file` 替代 `cat file |`** — 消除管道，避免 Zsh 创建独立 Process Group 造成作业控制问题
2. **`>/dev/null 2>&1`** — 掐断与伪终端的 stdout/stderr 连接
3. **`3<&-`**（仅 exec 循环内需要） — 在 fork 之前显式关闭 fd 3，从根本上杜绝子进程继承和篡改

### 修改清单

**`_aicp_exec_loop` 内部（第 557/559/565/567 行）**：

```zsh
# 之前
cat "$new_tmp" | wl-copy; copied=1
cat "$new_tmp" | xclip -selection clipboard; copied=1
cat "$accum_file" | wl-copy
cat "$accum_file" | xclip -selection clipboard

# 之后
wl-copy < "$new_tmp" >/dev/null 2>&1 3<&-; copied=1
xclip -selection clipboard < "$new_tmp" >/dev/null 2>&1 3<&-; copied=1
wl-copy < "$accum_file" >/dev/null 2>&1 3<&-
xclip -selection clipboard < "$accum_file" >/dev/null 2>&1 3<&-
```

**`_aicp_exec_loop` 外部（第 887/890/893 行）**：

```zsh
# 之前
cat "$tmp_file" | wl-copy
cat "$tmp_file" | xclip -selection clipboard
cat "$tmp_file" | pbcopy

# 之后
wl-copy < "$tmp_file" >/dev/null 2>&1
xclip -selection clipboard < "$tmp_file" >/dev/null 2>&1
pbcopy < "$tmp_file" >/dev/null 2>&1
```

### 验证结果

```
[DBG 19:21:51 fd3=OPEN] 第 2 轮: 读完, rc=0, 共 2 行, len=32     ← 之前 rc=1
[DBG 19:21:54 fd3=OPEN] 第 3 轮: 开始阻塞等待 fd3 输入...          ← 之前不会出现
```

第 2 轮 `read` 正常阻塞等待用户粘贴，rc=0，不再触发空输入退出。
