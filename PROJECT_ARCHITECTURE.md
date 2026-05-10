# 项目组织架构（ZFL / Zsh Function Library）

本文档用于梳理当前项目的技术架构，便于后续持续迭代、故障定位与功能扩展。

---

## 1. 项目定位

这是一个以 Zsh 为核心的本地函数库项目，采用：
- `base.zsh` 作为统一入口
- `core/` 存放基础框架与启动流程
- `functions/` 存放可懒加载的用户功能函数
- `python/` 存放复杂功能的辅助脚本（当前主要服务于 `aicp`）

核心设计目标：
1) 启动轻量（懒加载）
2) 功能可扩展（新增 `.zsh` 即可注入）
3) 复杂逻辑下沉（Python 负责复杂检索/切片/预算控制）

---

## 2. 目录结构与职责

```text
.
├── base.zsh
├── core/
│   ├── colors.zsh
│   ├── func.zsh
│   ├── startup_tasks.zsh
│   └── usr.zsh
├── functions/
│   ├── aicp.zsh
│   ├── check_update.zsh
│   ├── countText.zsh
│   └── weather.zsh
├── python/
│   └── aicp_context.py
└── aicp.zsh.bak
```

### 2.1 入口层
- `base.zsh`
  - 设置 `ZFL_HOME`
  - 依次 `source`：
    - `core/func.zsh`
    - `core/startup_tasks.zsh`
    - `core/usr.zsh`

### 2.2 框架层（core）
- `core/func.zsh`
  - 懒加载核心：扫描 `functions/*.zsh`，为每个函数名生成占位函数
  - 首次调用时动态 `source` 对应脚本，再执行真实函数
  - 同时提供 `load_color()` 工具函数（颜色变量注入调用者作用域）

- `core/colors.zsh`
  - 全局颜色字典 `COLORS`（前景、背景、亮色、样式）
  - 供各 function 输出统一风格日志

- `core/startup_tasks.zsh`
  - 交互式 shell 启动任务调度器
  - 当前默认任务：`check_update`

- `core/usr.zsh`
  - 用户覆盖层（alias / 环境变量 / 本地习惯）
  - 是“用户个性配置入口”

### 2.3 功能层（functions）
- `functions/aicp.zsh`
  - AI 上下文打包入口函数
  - 参数解析、剪贴板写入、输出文件/终端、调用 Python 脚本
  - 支持筛选、预算覆盖、输出格式控制、质量报告

- `functions/check_update.zsh`
  - 多后端更新检查与交互更新（AUR/pacman + flathub）
  - 包含更新源探测、计数、执行、标记文件（成功日期/提示日期）

- `functions/countText.zsh`
  - 文本统计（中文字符数/英文词数）

- `functions/weather.zsh`
  - 简单天气查询封装（wttr.in）

### 2.4 复杂逻辑层（python）
- `python/aicp_context.py`
  - `aicp` 的核心引擎
  - 负责文件扫描、过滤、git 改动筛选、片段生成、预算控制、格式输出

---

## 3. 关键运行链路

### 3.1 Shell 启动链路
1) 用户 `source base.zsh`
2) 加载 `core/func.zsh` 并注册懒加载函数占位
3) 执行 `core/startup_tasks.zsh`（如 `check_update`）
4) 加载 `core/usr.zsh`（用户覆盖）

### 3.2 函数懒加载链路
1) 用户调用 `aicp`（或任意 functions 内函数）
2) 占位函数触发 `lazy_load_functions`
3) `source $ZFL_HOME/functions/aicp.zsh`
4) 再次以原参数执行真实 `aicp` 函数

### 3.3 aicp 双层架构链路
1) `functions/aicp.zsh` 完成参数解析
2) 组装 Python 命令并执行 `python/aicp_context.py`
3) Python 输出上下文文本（markdown/plain/json）
4) shell 层负责：
   - 复制到剪贴板（wl-copy/xclip/pbcopy）
   - 可选打印到终端
   - 可选写入文件

---

## 4. aicp 能力模型（当前）

### 4.1 输入范围
- `-a/--all`：全目录扫描
- `-c/--choose`：指定文件/目录

### 4.2 过滤与聚焦
- 纳入：`--query` / `--query-regex`
- 排除：`--exclude` / `--exclude-regex`

### 4.3 Git 改动视角
- `--changed`（相对 HEAD）
- `--changed-from <ref>`
- `--changed-commit-range <A..B>`

### 4.4 片段策略
- 默认：文件头部切片
- `--snippet-around-query`：命中点邻域切片
- `--snippet-context-lines <n>`：邻域行数

### 4.5 输出与预算
- `--output-format <markdown|plain|json>`
- `--quality-report`
- `--max-files`
- `--max-total-chars`
- `--max-file-chars`

---

## 5. 架构分层原则（后续修改遵循）

1) `functions/*.zsh` 负责：
   - 参数交互
   - 用户体验
   - 平台适配（剪贴板/终端）

2) `python/*.py` 负责：
   - 大规模文件处理
   - 复杂筛选规则
   - 预算/切片算法
   - 结构化输出

3) `core/*` 只做基础设施：
   - 懒加载
   - 颜色
   - 启动任务调度
   - 用户配置接入

4) 任何新功能优先“增量兼容”，避免破坏已存在命令习惯。

---

## 6. 建议的后续扩展点

1) `aicp`
- 增加 `--profile`（review/debug/doc/refactor 预设）
- 增加 `--save-preset`（本地场景模板）
- 增加 `--dry-run`（只输出命中文件清单）

2) `check_update`
- 增加后端插件注册规范（减少硬编码）
- 增加失败重试策略与日志摘要

3) 工程化
- 增加最小 smoke test 脚本：
  - `zsh -n functions/*.zsh`
  - `python3 python/aicp_context.py --mode fast --all`

---

## 7. 修改者快速指南

当你需要改项目时，优先判断改动落点：
- 改参数交互/帮助文档/输出行为：改 `functions/aicp.zsh`
- 改筛选逻辑/切片算法/输出结构：改 `python/aicp_context.py`
- 改懒加载机制：改 `core/func.zsh`
- 改启动任务策略：改 `core/startup_tasks.zsh`
- 改用户默认行为：改 `core/usr.zsh`

避免跨层耦合：不要把复杂文本处理重新塞回 zsh 层。

---

## 8. 当前状态结论

项目已经形成清晰的“Shell 外壳 + Python 引擎”双层架构，
具备日常 AI 上下文打包、改动审查、关键词定位、预算控制等核心能力。

此文档可作为后续重构与功能迭代的基线架构说明。