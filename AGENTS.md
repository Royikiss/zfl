# Antigravity Developer Guide (AGENTS.md)

本文件是针对本 Zsh 扩展配置与函数库（Zsh Function Library，简称 **ZFL**）的开发与维护指南。后续 AI 助手在理解、新增或重构代码时，应严格遵循本指南中定义的架构设计与编码约束。

---

## 项目概述

**ZFL (Zsh Function Library)** 是一个高性能、模块化的 Zsh 配置与函数库。在保留极速 shell 启动的同时，支持以下关键特性：
- **零延迟启动**：利用函数桩懒加载与补全懒加载代理机制，确保初始化只做桩注册，零文件加载开销。
- **非阻塞启动**：利用独立文件描述符（FD 3）隔离读取并执行后台启动任务，保证终端启动期间交互无卡顿。
- **AI 协作友好**：内置 `aicp` 协作工具，方便打包项目上下文并交互式应用 unified diff 补丁。

---

## 简要目录结构要求与功能

- **[core/](file:///home/royi/.config/zsh/core/)**：框架核心调度与公共模块。
  - [colors.zsh](file:///home/royi/.config/zsh/core/colors.zsh)：声明 ANSI 颜色与文本样式变量。
  - [func.zsh](file:///home/royi/.config/zsh/core/func.zsh)：核心加载引擎，负责懒加载函数与补全桩的动态注册。
  - [startup_tasks.zsh](file:///home/royi/.config/zsh/core/startup_tasks.zsh) / [startup_task_commands.zsh](file:///home/royi/.config/zsh/core/startup_task_commands.zsh)：非阻塞启动任务调度与白名单列表。
  - [usr.zsh](file:///home/royi/.config/zsh/core/usr.zsh)：用户个性化配置覆盖层（环境变量、别名等）。
- **[functions/](file:///home/royi/.config/zsh/functions/)**：模块化业务函数目录。
  - 文件名与函数名必须严格 **1:1 映射**。
  - 承载具体命令逻辑（如 [add_task.zsh](file:///home/royi/.config/zsh/functions/add_task.zsh)、[aicp.zsh](file:///home/royi/.config/zsh/functions/aicp.zsh)、[check_update.zsh](file:///home/royi/.config/zsh/functions/check_update.zsh) 等）。支持补全的函数其补全代理应定义在脚本底部。
- **[python/](file:///home/royi/.config/zsh/python/)**：跨语言辅助脚本，如 [aicp_context.py](file:///home/royi/.config/zsh/python/aicp_context.py)（上下文计算）与 [preview_skill.py](file:///home/royi/.config/zsh/python/preview_skill.py)（技能预览）。
- **[docs/](file:///home/royi/.config/zsh/docs/)**：框架核心机制的技术设计与避坑文档。

---

## 项目运作机制

### 1. 懒加载与补全桩 (Lazy Loading)
- **懒加载函数**：初始化时仅为 `functions/` 下的函数注册同名桩函数。只有当用户执行命令时，桩函数才会 `source` 对应脚本并接管运行。
- **补全桩代理**：动态注册以 `_` 开头的补全桩函数。当触发 Tab 补全时，桩函数加载真实脚本、移交控制权，若无特定补全则降级为默认补全。

### 2. 启动任务调度与 FD 3 隔离
- 框架启动任务流通过系统描述符 3 (`exec 3< ...`) 进行读取，使之与 stdin（描述符 0）完全隔离。这避免了启动流中的交互式命令（如 `read` 确认）误吞标准输入，防止后续启动任务丢失。

### 3. 状态管理与缓存锁设计
- 异步任务（如 `check_update`）的状态锁保存在 `~/.cache/zsh/` 下：`UpdateCountCache.lock`（缓存更新计数）、`UpdateRefresh.lock/`（并发刷新互斥锁）、`CheckUpdateProcess.lock/`（避免多终端重复提示的单例锁）。

---

## 开发准则

1. **命名与结构规范**：新增函数必须在 `functions/` 下新建 `<函数名>.zsh`，内有且仅有一个同名主函数。如有补全，编写在同文件底部。
2. **变量局部化**：函数内临时变量必须显式声明为 `local`，防止污染用户 Shell 的全局命名空间。
3. **FD 3 重定向与清理**：在启动流中执行或会 Fork 守护进程的命令，**必须关闭或重定向描述符 3**（例如 `wl-copy < "$tmp" >/dev/null 2>&1 3<&-`），否则会导致父进程交互式 Shell 读到 EOF 闪退。
4. **颜色加载**：严禁硬编码 ANSI 转义。必须使用 `load_color` 动态引入颜色变量（仅限函数内部使用，不要在顶层调用）。
5. **添加启动任务**：必须使用 `add_task` CLI 写入，严禁直接手动修改 `startup_task_commands.zsh`。
6. **AI 协作**：使用 `aicp` 命令可自动打包项目上下文至剪贴板，方便与 AI 对话。
