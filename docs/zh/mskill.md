# mskill

`mskill` (Manage Skill) 是针对 AI Agent 技能（Skills）的全生命周期管理与工程化协作中枢，集成了**自动识别与打包下载、本地目录导入、版本追溯与平滑更新、软链接引入与原地脱壳、声明式依赖同步、健康巡检诊断、脚手架生成、项目挂载状态感知与全功能 FZF 交互控制台**。

---

## ✨ 核心特性

1. **精准识别、自包含打包与本地导入**：
   - 无论远程 GitHub 仓库是单 Skill 仓库、Monorepo 还是深层嵌套目录，均以 `SKILL.md` 为锚点完整打包其附属脚本（`scripts/`）、领域文档（`references/`）等。
   - **支持本地目录直导**：运行 `mskill -i /path/to/local-dir` 直接自包含打包导入本地自建技能。
   - **支持分支与版本定位**：支持 `owner/repo@v1.0.0` 或 `owner/repo#branch` 精确拉取。
   - **多技能自动分组引导**：多技能包安装完成后，自动提示快速创建技能分组。
2. **版本追踪与原子持久化**：
   - 在 `~/.local/share/zfl/skills_manifest.json` 中跟踪远程仓库源、分支、Commit Hash 及子路径。
   - 采用临时文件 + `os.replace` 的 **JSON 原子写入（Atomic Write）**，杜绝进程意外中断导致元数据损坏。
   - 分组关系（`skills_groups.json`）在更新或升级时 100% 保持不变。
3. **极速软链接、原地脱壳与安全解挂**：
   - **软链接（默认）**：以符号链接（`ln -s`）接入当前项目 `.agents/skills/`，全局更新项目即时生效。
   - **实体脱壳 (`mskill eject`)**：一键将当前项目中的软链接原地替换为物理独立实体副本，自由定制。
   - **安全解挂 (`mskill --unlink`)**：安全解除项目中的技能挂载，绝不误删全局技能库。
4. **团队协作与声明式依赖 (`dump` & `sync`)**：
   - **`mskill dump`**：将当前项目的技能依赖与挂载模式（软链或实体）导出至 `.skillsrc` 配置文件。
   - **`mskill sync`**：团队成员克隆项目后一键执行，自动拉取缺失项并完美对齐挂载，体验如 `pnpm install`。
5. **健康自愈诊断 (`mskill doctor`)**：
   - 深度扫描当前项目与全局：检测并修复悬空死链（Broken Symlink）、损坏的技能目录、元数据完整度及系统 CLI 依赖可用性。
6. **标准脚手架生成器 (`mskill new <name>`)**：
   - 一秒生成符合标准规范的技能骨架，包含标准 `SKILL.md`、双语模板、`scripts/` 与 `references/` 目录。
7. **全功能 FZF 交互控制台与挂载状态感知**：
   - **穿透式分组智能搜索**：搜索时自动穿透并直接检索各组内部的所有技能，搜索结果优先以展开模式展示该技能所属的分组内容及匹配统计（如 `(2 个匹配)`），一目了然。
   - **项目挂载状态胶囊**：技能行直观显示 `[🔗软链]` 或 `[📄拷贝]`；分组行显示 `[🔗:xx%, 📦:xx%]` 占比徽标（全是连接显示蓝色，全是下载拷贝显示绿色，两者兼有显示黄色），告别盲选。
   - **标识名与中文别名解耦**：分组具备 CLI 标识名与 UI 展示别名（如 `[分组: Anthropic 官方技能库]`），在多列流线型排版中与技能中文译名保持严密列对齐。
   - **智能分词翻译与下载即时预热**：自动对复合标识（kebab-case）进行自然分词翻译，并在下载安装技能瞬间在后台自动预热拉取中文译名与简介入库。
   - **丰富快捷键操作（全功能绑定多选联动）**：
     - `Tab` / `→` / `←`：折叠/展开分组
     - `Ctrl-O`：全展 / 全折
     - `空格`：多选切换（所有操作快捷键自动优先针对多选生效；未多选时以待选框当前光标所在项为准）
     - `Ctrl-E`：调用 `$EDITOR` 实时修改所选技能的 `SKILL.md`（支持多文件同开）
     - `Ctrl-X`：从当前项目中批量安全解挂所选技能（展示清晰的软链接/实体状态卡片）
     - `Ctrl-G` / `Ctrl-D`：分组批量设置（支持自定义展示名）/ 批量解散分组或从分组移出技能
     - `Ctrl-N` / `Ctrl-U`：安装新技能 / 批量检查更新所选技能
     - `Ctrl-B`：批量解绑所选技能的 Git 关联并转为本地自建
     - `Ctrl-T`：批量强制重新拉取所选技能的中文翻译
     - `Enter`：批量软链接所选技能到当前项目
     - `Alt-C`：批量拷贝所选技能的实体副本到当前项目

---

## 🚀 命令与用法

```bash
mskill [选项] [技能名称/分组名称...]
```

### 1. 下载、导入与安装技能 (`-i, --install`)
```bash
# 通过 GitHub 简写安装
mskill -i anthropics/anthropic-quickstarts

# 安装指定版本 Tag 或分支
mskill -i owner/repo@v2.1.0
mskill -i owner/repo#dev

# 从本地目录直接打包导入
mskill -i /path/to/my-local-skill

# 终端交互式安装引导
mskill -i
```

### 2. 项目挂载与逆向操作 (软链接 / 脱壳 / 解挂)
```bash
# 软链接引入项目 (默认)
mskill caveman diagnose
mskill startup                    # 引入整个分组

# 原地脱壳：将软链接转为独立实体副本
mskill eject video-generator
mskill eject                      # 脱壳当前项目全部软链接技能

# 从当前项目中安全解挂 (不影响全局)
mskill --unlink video-generator
mskill --unlink startup           # 解挂整组
mskill --unlink-all               # 清空当前项目所有已挂载技能
```

### 3. 团队协同与声明式依赖 (`dump` / `sync`)
```bash
# 导出当前项目技能依赖清单至 .skillsrc (提交至 Git)
mskill dump

# 团队新成员克隆项目后一键对齐与拉取所有技能依赖
mskill sync
```

### 4. 技能脚手架与健康巡检 (`new` / `doctor`)
```bash
# 快速创建新技能标准规范骨架
mskill new my-awesome-skill

# 运行健康巡检：诊断并修复悬空死链、损坏文件与系统依赖
mskill doctor
```

### 5. 版本检查与更新 (`-u`, `--update-all`, `--status`, `-b`)
```bash
# 查看所有已安装技能的版本 Commit、来源与本地自建状态
mskill --status

# 检查并更新指定技能
mskill -u video-generator

# 一键更新全部已追踪的远程技能
mskill --update-all

# 解绑 Git 追踪（转为纯本地技能，保留文件）
mskill -b video-generator
```

### 6. 技能分组管理 (`-s`, `-r`, `-l`)
```bash
# 创建或修改技能分组
mskill --group-set dev prototype handoff grill-me

# 创建有序分组（标记推荐调用顺序）
mskill --group-set startup --ordered validate-idea first-customers marketing-plan

# 列出所有已定义的分组
mskill --group-list

# 删除指定分组
mskill --group-rm dev
```

### 7. 中文翻译预热与项目查看 (`-v`, `--translate-all`)
```bash
# 查看当前项目已引入的技能状态与中文功能说明
mskill -v

# 一键批量拉取所有未翻译技能的中文译名与描述 (离线极速浏览)
mskill --translate-all
```

---

## 🏗️ 系统三层架构设计规范 (Architecture Foundation)

`mskill` 采用严密的**三层解耦架构**设计，遵循领域驱动设计与高内聚深模块（Deep Module）原则：

```mermaid
flowchart TD
    subgraph "1. Shell 交互层 (functions/mskill.zsh)"
        User[用户执行命令] --> ShellGuard{快速路径判定}
        ShellGuard -->|"-h / --help"| ShellHelp[原生极速直出帮助]
        ShellGuard -->|"无参数 / 单独 -c"| FZFUI[FZF 全功能交互式控制台]
        ShellGuard -->|"所有带参命令行"| Forward[透明转发: python3 manage_skills.py "$@"]
        FZFUI -->|用户选定操作| Forward
    end

    subgraph "2. 统一调度门面层 (python/manage_skills.py)"
        Forward --> Facade[Unified Dispatch Facade]
        Facade --> HomeGuard[家目录安全防护拦截]
        Facade --> SmartDetect[Git / URL / 简写智能识别]
        Facade --> Lifecycle[生命周期管理: install / update / doctor / new]
    end

    subgraph "3. 核心领域引擎层 (python/skill_engine/)"
        Facade --> GroupsEngine[_groups.py: 分组 CRUD / 双向目标解析 / 补全生成]
        Facade --> MountEngine[_mount.py: 项目挂载 / 脱壳 / 解绑 / .skillsrc 对齐]
        Facade --> DisplayEngine[_display.py: 现代流线型无框排版 / 宽字符对齐]
        GroupsEngine --> StoreEngine[_store.py: 原子 JSON 读写与缓存]
        MountEngine --> StoreEngine
    end
```

### 1. 各层职责边界

1. **Shell 交互轻量层 (`functions/mskill.zsh`)**：
   - **职责极窄化**：仅承载 Zsh 原生 Tab 补全代理、零延迟 `-h/--help` 快速通道，以及无参数触发的全功能 FZF 交互工作流。
   - **透明转发机制（Transparent Forwarding）**：所有非帮助的带参命令行调用，直接透明转发给 Python 统一门面处理。
2. **统一调度中枢门面 (`python/manage_skills.py`)**：
   - **单一真实源（Single Source of Truth）**：作为整个体系唯一的外部调用接缝（Unified Seam），集中管理所有命令定义、参数校验、异常退出码与交互工作流。
   - **智能识别与安全防护**：内置家目录防御机制（Home Directory Protection）防止破坏全局技能库，内置仓库模式智能感知（Smart Auto-detection）实现免 `-i` 直接安装。
3. **下沉核心领域引擎 (`python/skill_engine/`)**：
   - **`_groups.py`（分组管理引擎）**：负责分组 CRUD、有序/无序属性维护、混合技能/分组目标展开解析（`resolve_group_targets`）及 Tab 补全数据格式化。
   - **`_mount.py`（项目挂载引擎）**：负责向上回溯定位 Git 根目录、软链接与实体副本挂载、原地脱壳（`eject`）、安全解绑（`unlink`）与 `.skillsrc` 声明式清单导出与对齐。
   - **`_store.py`（数据存储引擎）**：负责所有全局配置与清单的原子安全持久化（Atomic Write）。
   - **`_display.py`（终端渲染引擎）**：封装现代流线型无框排版规范与宽字符（CJK）真实视觉宽度精确对齐算法。

---

## ⚠️ 将来开发规范与基石规约（严格禁止随意更改架构）

为防止后续 AI 助手或开发者在维护和迭代过程中发生**架构退化**，必须无条件遵循以下基石规约：

> [!IMPORTANT]
> **基石规约一：严禁在 Shell 端重新引入手工参数解析**  
> `functions/mskill.zsh` 必须始终保持纯粹轻量。**严禁**在 Shell 脚本中重新添加 `while case` 循环解析、维护 `opt_*` 状态标志或自行分发指令。凡增改 CLI 参数或命令，必须在 `manage_skills.py` 门面及 `skill_engine` 中处理。

> [!IMPORTANT]
> **基石规约二：单一对外接缝（Seam）原则**  
> `manage_skills.py` 是外部面对 Python 侧的**唯一合法入口**。Shell 端（包括 FZF 的 `bind` 按键）**严禁绕过此门面**直接穿透调用 `resolve_skills.py`、`preview_skill.py` 或 `skill_engine` 下属私有模块。

> [!IMPORTANT]
> **基石规约三：领域引擎无 UI 纯数据化与自动化测试保障**  
> `skill_engine/` 中的任何函数（如 `_groups.py`、`_mount.py`）**必须严格与终端渲染（`print`、ANSI 颜色）解耦**，全部返回结构化纯数据字典或布尔值。每个引擎模块必须在 `tests/` 下配备确定性的独立单元测试（`pytest` 必须 100% 通过）。

> [!IMPORTANT]
> **基石规约四：严格遵守持久化与缓存边界**  
> 运行期间产生的所有持久化配置必须存放在 `~/.local/share/zfl/`，临时状态锁必须存放在 `~/.cache/zsh/`。严禁向代码仓库目录或全局技能包本体目录直接写入临时私有数据。


