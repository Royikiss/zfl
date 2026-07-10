# Antigravity Developer Guide (AGENTS.md)

本文件是针对本 Zsh 扩展配置与函数库（Zsh Function Library，简称 **ZFL**）的开发与维护指南。后续 AI 助手在理解、新增或重构代码时，应严格遵循本指南中定义的架构设计与编码约束。

---

## 项目概述

**ZFL (Zsh Function Library)** 是一个高性能、模块化的 Zsh 配置与函数库。在保留极速 shell 启动的同时，支持以下关键特性：
- **零延迟启动**：利用函数桩懒加载与补全懒加载代理机制，确保初始化只做桩注册，零文件加载开销。
- **非阻塞启动**：利用独立文件描述符（FD 3）隔离读取并执行后台启动任务，保证终端启动期间交互无卡顿。
- **AI 协作友好**：内置 `aicp` 协作工具，方便打包项目上下文并交互式应用 unified diff 补丁。
- **静态质量防御**：内置 `zfl lint` 静态分析机制与 GitHub Actions 自动化门禁，杜绝全局泄漏与描述符污染。

---

## 简要目录结构要求与功能

- **[core/](file:///home/royi/.config/zsh/core/)**：框架核心调度与公共模块。
  - [colors.zsh](file:///home/royi/.config/zsh/core/colors.zsh)：声明 ANSI 颜色与文本样式变量。
  - [func.zsh](file:///home/royi/.config/zsh/core/func.zsh)：核心加载引擎，负责懒加载函数与补全桩的动态注册。使用匿名函数保证初始化环境洁净。
  - [startup_tasks.zsh](file:///home/royi/.config/zsh/core/startup_tasks.zsh) / [startup_task_commands.zsh](file:///home/royi/.config/zsh/core/startup_task_commands.zsh)：非阻塞启动任务调度与白名单列表。
  - [usr.zsh.example](file:///home/royi/.config/zsh/core/usr.zsh.example)：用户配置模板文件。用户需拷贝并创建 `usr.zsh` 来存放个性化配置覆盖层（如环境变量、别名等），该文件已被 `.gitignore` 忽略。
- **[functions/](file:///home/royi/.config/zsh/functions/)**：模块化业务函数目录。
  - 文件名与函数名必须严格 **1:1 映射**。
  - 承载具体命令逻辑。支持补全的函数其补全代理应定义在脚本底部。
  - 新增管理工具 [zfl.zsh](file:///home/royi/.config/zsh/functions/zfl.zsh)（支持 list、info、check、lint 子命令及补全）。
- **[custom_functions/](file:///home/royi/.config/zsh/custom_functions/)**：用户本地私有函数目录。
  - 此目录在 `.gitignore` 中被忽略，用于用户存放个人的自定义非公开脚本，防止 Git 合并冲突。
- **[python/](file:///home/royi/.config/zsh/python/)**：跨语言辅助脚本，如 [zfl_lint.py](file:///home/royi/.config/zsh/python/zfl_lint.py)（静态代码质检分析）、[aicp_context.py](file:///home/royi/.config/zsh/python/aicp_context.py) 与 [preview_skill.py](file:///home/royi/.config/zsh/python/preview_skill.py)。
- **[docs/](file:///home/royi/.config/zsh/docs/)**：框架核心机制的技术设计与避坑文档。
- **[.github/workflows/](file:///home/royi/.config/zsh/.github/workflows/)**：包含 [lint.yml](file:///home/royi/.config/zsh/.github/workflows/lint.yml) 自动化门禁配置文件。

---

## 项目运作机制

### 1. 懒加载与补全桩 (Lazy Loading)
- **双目录自发现**：初始化时遍历 `functions/` 与 `custom_functions/` 下的所有脚本。
- **懒加载函数**：为每个函数注册同名桩函数。只有当用户执行命令时，桩函数才会 `source` 对应路径的脚本并接管运行。
- **补全桩代理**：动态注册以 `_` 开头的补全桩函数。当触发 Tab 补全时，桩函数加载真实脚本、移交控制权，若无特定补全则降级为默认补全。

### 2. 启动任务调度与 FD 3 隔离
- 框架启动任务流通过系统描述符 3 (`exec 3< ...`) 进行读取并隔离执行。在启动流中执行或会 Fork 守护进程的命令，**必须关闭或重定向描述符 3**（例如加上 `3<&-`），否则会导致父进程终端交互读到 EOF 闪退或锁死。

### 3. 状态管理与缓存锁设计
- 异步任务（如 `check_update`）的状态锁保存在 `~/.cache/zsh/` 下。

---

## 开发准则

AI 助手在新增、修复或重构函数时，**必须满足以下开发准则，并通过本地 `zfl lint` 检测**：

1.  **文件与主函数映射**：新增业务函数必须在 `functions/` 下新建 `<函数名>.zsh`，文件内必须定义有同名全局入口函数。
2.  **元数据头部标准**：文件顶部**必须**包含 `#?` 格式的描述注释块（包括：名称、描述、作者、版本、依赖、用法、示例）。
3.  **局部变量强声明**：函数内定义的临时变量、循环迭代变量（如 `for x in ...`）、命令行读取变量（如 `read var`）**必须显式声明为 `local`**，防范作用域向外渗透污染。
4.  **全局辅助函数清理**：
    *   内部辅助逻辑**优先使用嵌套定义**在主函数内。
    *   若定义在文件最外层，其名字必须以 `_主函数名_` 或 `_主函数名` 前缀命名，并在主函数执行退出前使用 `unfunction` 对其主动清理。
5.  **统一依赖声明**：若脚本依赖外部 CLI 工具，应在入口处首行执行 `zfl_require <dep1> <dep2> || return 1` 守卫检测。
6.  **严禁硬编码颜色**：严禁写死 ANSI 颜色转义字串（如 `\e[31m`），须通过 `load_color RED GREEN RESET` 载入公共颜色变量。
7.  **FD 3 安全关闭**：任何后台任务（`&`）或 fork 子 shell 的命令中，必须在其指令流中添加 `3<&-` 进行安全关闭重定向。
8.  **本地自检与测试**：在提交任何修改前，必须运行本地 `zfl lint <函数名>`，确认状态为 **完美通过**（返回状态码 `0`）。
9.  **Python 脚本与副产物规范**：在 `python/` 目录下只编写用于辅助 `functions/` 的跨语言辅助 Python 脚本。运行期间由脚本产生的任何用户个性化副产物（如缓存、自动翻译结果、配置副本等）必须统一存放于 `~/.cache/zsh/` 下，严禁污染或修改全局共享技能目录（`~/.agents/skills/`）或其他非暂存的代码路径。

