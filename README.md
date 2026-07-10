# ZFL (Zsh Function Library)

ZFL 是一个面向高性能、模块化的 Zsh 配置与函数库。在保持 Shell 极速启动（零文件加载延迟）的同时，内置了非阻塞启动任务调度、AI 辅助开发上下文打包工具、更新检测以及各类便捷的系统工具。

---

## 🚀 核心特性

- **⚡ 零延迟启动 (Lazy Loading)**
  - 启动时仅为 `functions/` 下的脚本注册同名占位函数，只有在实际执行命令时才 `source` 导入。
  - 独特的**补全懒加载代理**：首次触发 Tab 补全时动态导入完整补全规则，兼顾极致启动速度与极致补全体验。
- **🛡️ 非阻塞启动任务 (FD 3 隔离)**
  - 利用系统描述符 3 (`exec 3< ...`) 进行启动任务的读取与执行，使启动流与 `stdin` 完全隔离。
  - 防止启动任务中的交互式命令（如 `read`）误吞标准输入，消除终端锁死或闪退隐患。
- **🤖 AI 协作友好 (AICP)**
  - 内置 `aicp` 协作工具，支持多级别（`fast`/`balanced`/`deep`/`full`）的 Token 预算控制与多维度路径/关键词过滤。
  - 提供 `--exec` 交互模式，AI 可以生成 `<aicp:read>` 及 `<aicp:write>` 标签让终端自动展示源码或在用户确认后自动应用 Unified Diff 补丁。
- **🔄 只读、非阻塞更新检测 (check_update)**
  - 启动时异步检测系统可更新项（Pacman/AUR、Flatpak），只读计数，绝不在后台请求 `sudo`。
  - 内置进程锁、互斥锁、自愈陈旧锁与多种提示策略（`pending_first`、`once_per_day`、`strict_daily`），提示频率可按需精细配置。

---

## 📂 项目结构

```bash
zsh/
├── base.zsh                      # 框架总入口（导出 ZFL_HOME 并加载核心模块）
├── core/                         # 核心调度与公共模块
│   ├── colors.zsh                # 预设的 ANSI 颜色与样式定义
│   ├── func.zsh                  # 懒加载核心引擎（含颜色加载器与补全代理）
│   ├── startup_tasks.zsh         # 非阻塞启动任务执行器（FD 3 隔离）
│   ├── startup_task_commands.zsh # 启动执行任务白名单
│   └── usr.zsh                   # 用户个性化配置层（可在此填写别名、代理等）
├── functions/                    # 模块化业务函数目录 (文件名与函数名 1:1 映射)
│   ├── add_task.zsh              # 启动任务管理 CLI
│   ├── aicp.zsh                  # AI 上下文打包与交互式协作执行
│   ├── check_update.zsh          # 异步只读更新统计与交互式升级
│   ├── countText.zsh             # 中英文数字字数统计工具
│   ├── link_skills.zsh           # 软链接 Agent 认知技能包工具 (fzf 交互式)
│   ├── verge-ipc-link.zsh        # Clash Verge 服务的 IPC Socket 软链接辅助
│   └── weather.zsh               # 天气快速查询 (wttr.in)
├── python/                       # 跨语言脚本辅助
│   ├── aicp_context.py           # aicp 核心的 Token 计数与上下文生成逻辑
│   └── preview_skill.py          # AI Skill 预览展示
└── docs/                         # 技术设计、机制说明及排障避坑文档
    ├── aicp.md                   # AICP 详细设计与使用说明
    ├── aicp-exec-bug.md          # Wayland 终端下 wl-copy 导致 stdin 非阻塞闪退排障记录
    └── check_update.md           # 自动更新检测设计、缓存及状态机制文档
```

---

## 🛠️ 安装与启用

1. 将本项目克隆或放置到 `~/.config/zsh` 目录下：
   ```bash
   git clone https://github.com/Royikiss/zfl.git ~/.config/zsh
   ```
2. 在您的主 `~/.zshrc` 配置文件尾部添加以下行引入 ZFL：
   ```zsh
   if [[ -f "$HOME/.config/zsh/base.zsh" ]]; then
       source "$HOME/.config/zsh/base.zsh"
   fi
   ```
3. 重新打开终端或执行 `source ~/.zshrc` 即可加载。

---

## ⚙️ 个性化配置 (`core/usr.zsh`)

为了保持主框架文件的整洁及避免 Git 冲突，您可以将个人的环境变量、代理、别名等写在 [core/usr.zsh](file:///home/royi/.config/zsh/core/usr.zsh) 中。示例如下：

```zsh
# 用户自定义别名
alias ls='eza --icons'
alias l='eza -lgh --header --git --icons'

# 网络代理配置
export HTTPS_PROXY=http://127.0.0.1:7897
export HTTP_PROXY=http://127.0.0.1:7897

# 调节 check_update 更新检测选项
export CHECK_UPDATE_CACHE_TTL_SECONDS=1800   # 缓存30分钟
export CHECK_UPDATE_PROMPT_POLICY=once_per_day # 拒绝后当日不再打扰
```

---

## 📖 核心命令指南

### 1. `aicp` - AI 协作工具
将当前项目结构及代码段精准打包到剪贴板，极大方便向 LLM 提问。
*   **基础用法**：
    ```bash
    aicp                  # 使用默认的 balanced 模式打包整个项目
    aicp -c core/func.zsh # 仅打包特定文件
    aicp --changed        # 仅打包 Git 相比 HEAD 有改动及未跟踪的文件
    ```
*   **模式控制 (`--mode`)**：
    - `fast`: 仅生成项目目录树及文件列表，生成速度极快。
    - `balanced` (默认): 带有代码段上下文，控制最大单文件字符，适合日常提问。
    - `deep`: 放宽单文件字符数上限，保留更多代码细节。
    - `full`: 复制完整内容，无截断（完全依照 `.ignore` 规则过滤）。
*   **交互运行模式 (`--exec`)**：
    ```bash
    aicp --exec
    ```
    执行后，除生成代码上下文外，还会接管终端。当 AI 的回复中带有特定 XML 标签时，支持在本地交互式读取文件片段（`<aicp:read>`）或在终端用户确认后自动应用 Unified Diff 补丁（`<aicp:write>`）。

### 2. `check_update` - 更新统计与升级
异步静默刷新系统更新缓存，以友好无干扰的方式管理 Arch Linux 包及 Flatpak 更新。
*   **运行**：
    ```bash
    check_update         # 按配置策略展示更新提示
    check_update --force # 忽略今日已提示/已更新等抑制状态，强行发起检测交互
    ```
*   提示后输入 `Y` 或回车启动系统升级（pacman/yay/flatpak）；输入 `C` 预览具体可升级的软件包清单；输入 `N` 忽略。

### 3. `add_task` - 启动任务管理
管理在每次打开 Shell 终端时后台自动非阻塞执行的任务列表。
*   **用法**：
    ```bash
    add_task -l                       # 列出当前所有的启动任务
    add_task check_update             # 添加 check_update 到启动任务
    add_task --remove check_update    # 从启动任务中删除
    ```

### 4. `link_skills` - 技能包软链工具
将全局的 AI Agent 技能库（Skills）有选择性地同步链接到当前工作目录的 `.agents/skills/` 下，便于当前项目的 AI 助手感知专属指令。
*   **用法**：
    ```bash
    link_skills                 # 启动 fzf 交互式菜单多选链接
    link_skills my_skill_name   # 直接链接指定的技能
    ```

### 5. `countText` - 字数统计工具
快速统计中英文混合文件中的字符数。
*   **用法**：
    ```bash
    countText -zh document.txt  # 统计中文字数 (汉字数)
    countText -cn document.txt  # 统计英文单词数
    ```

---

## 🎨 开发设计规范

如果您打算向 ZFL 提交新的工具函数，请务必遵守 [AGENTS.md](file:///home/royi/.config/zsh/AGENTS.md) 中规定的以下规范：
1.  **文件与主函数 1:1 对应**：新功能需放在 `functions/<函数名>.zsh` 中，且内部仅包含一个同名的全局主入口函数。
2.  **变量局部化**：所有临时变量必须声明为 `local`，防止污染用户 Shell 空间。
3.  **FD 3 安全关闭**：在涉及后台 Daemon 启动或包含 fork 行为的命令中，**必须手动重定向并关闭文件描述符 3**（例如 `my_cmd >/dev/null 2>&1 3<&-`），以避免父终端由于 fd 状态泄露产生阻塞/异常。
4.  **动态颜色引入**：严禁硬编码 ANSI Escape 序列，函数内可使用 `load_color RED GREEN RESET` 动态引入颜色样式。
