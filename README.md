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
- **🔍 静态代码质量防御与管理 (zfl)**
  - 内置 `zfl` 工具提供本地静态质量 Lint 分析（自动化扫描变量/描述符泄漏，命名规范，颜色硬编码，文档配套），并部署 GitHub Actions PR 流水线门禁拦截。
  - 规范函数注释头元数据标准，自动生成可用指令列表展示，并在运行前对各函数的外部系统依赖进行检测校验。

---

## 📂 项目结构

```bash
zsh/
├── base.zsh                      # 框架总入口（导出 ZFL_HOME 并加载核心模块）
├── core/                         # 核心调度与公共模块
│   ├── colors.zsh                # 预设的 ANSI 颜色与样式定义
│   ├── func.zsh                  # 懒加载核心引擎（含颜色加载器、依赖检测器与补全代理）
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
│   ├── weather.zsh               # 天气快速查询 (wttr.in)
│   └── zfl.zsh                   # ZFL 框架内置命令行管理与自发现工具
├── custom_functions/             # 用户本地私有函数目录 (已被 gitignore 忽略)
├── python/                       # 跨语言脚本辅助
│   ├── aicp_context.py           # aicp 核心的 Token 计数与上下文生成逻辑
│   └── preview_skill.py          # AI Skill 预览展示
└── docs/                         # 技术设计、机制说明及排障避坑文档
    ├── aicp.md                   # AICP 详细设计与使用说明
    ├── aicp-exec-bug.md          # Wayland 终端下 wl-copy 导致 stdin 非阻塞闪退排障记录
    ├── check_update.md           # 自动更新检测设计、缓存及状态机制文档
    └── zfl.md                    # 内置管理工具及社区/用户脚本规范文档
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

为了保持主框架文件的整洁及避免 Git 冲突，`core/usr.zsh` 已加入 `.gitignore` 且不被 Git 跟踪。

您可以将模板文件复制一份，然后在其中填写您个人的环境变量、代理、别名等：

```bash
cp core/usr.zsh.example core/usr.zsh
```

`core/usr.zsh` 配置示例如下：

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

## 📖 核心命令与文档

ZFL 包含的每个函数都在 [docs/](file:///home/royi/.config/zsh/docs/) 目录下有对应的详细说明文档。请点击以下链接阅读：

- ⚙️ [zfl](file:///home/royi/.config/zsh/docs/zfl.md) - ZFL 框架内置命令行管理与自发现工具
- 🤖 [aicp](file:///home/royi/.config/zsh/docs/aicp.md) - AI 协作工具（上下文打包、Token 计数与 `--exec` 交互协作模式）
- 🔄 [check_update](file:///home/royi/.config/zsh/docs/check_update.md) - 异步只读更新统计与交互式系统升级
- ⚙️ [add_task](file:///home/royi/.config/zsh/docs/add_task.md) - 后台非阻塞启动任务管理
- 🔗 [link_skills](file:///home/royi/.config/zsh/docs/link_skills.md) - 软链接全局 AI Agent 技能配置到本地项目
- 🌐 [verge-ipc-link](file:///home/royi/.config/zsh/docs/verge-ipc-link.md) - Clash Verge IPC Socket 软链接配置辅助
- 📊 [countText](file:///home/royi/.config/zsh/docs/countText.md) - 中英文混排文本字数统计工具
- 🌤️ [weather](file:///home/royi/.config/zsh/docs/weather.md) - 终端快速查询实时天气与天气预报

---

## 🎨 开发设计规范

如果您打算向 ZFL 提交新的工具函数，请务必阅读并遵守 [CONTRIBUTING.md](file:///home/royi/.config/zsh/CONTRIBUTING.md) 与 [AGENTS.md](file:///home/royi/.config/zsh/AGENTS.md) 中规定的以下规范：
1.  **文件与主函数 1:1 对应**：新功能需放在 `functions/<函数名>.zsh` 中，且内部仅包含一个同名的全局主入口函数。
2.  **标准化元数据注释头**：文件最顶部必须包含以 `#?` 开头的名称、描述、作者、版本、依赖和用法声明。
3.  **变量强局部化**：所有临时变量、循环变量和输入读取变量必须显式声明为 `local`，防止污染用户 Shell 命名空间。
4.  **全局辅助函数回收**：外部辅助函数命名必须以 `_主函数名_` 开头，并在主函数退出前执行 `unfunction` 清理；推荐直接采用内部嵌套函数定义。
5.  **FD 3 安全关闭**：任何后台任务（`&`）或 fork 子 shell 的命令中，必须在其指令流中重定向并关闭文件描述符 3（`3<&-`），避免父终端异常挂起或锁死。
6.  **色彩载入与依赖声明**：严禁硬编码颜色转义字符，请使用 `load_color`；若有第三方 CLI 依赖，请在函数首行使用 `zfl_require` 保护。
7.  **静态代码自检**：在提交任何更改前，请在本地运行并完美通过 `zfl lint <函数名>`，确认退出状态码为 0。

