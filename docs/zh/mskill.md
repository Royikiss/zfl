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
   - **项目挂载状态胶囊**：列表直观高亮 `[🔗软链]`、`[📄拷贝]` 或 `[全组已连]`，告别盲选。
   - **丰富快捷键操作**：
     - `Tab` / `→` / `←`：折叠/展开分组
     - `Ctrl-O`：全展 / 全折
     - `空格`：多选
     - `Ctrl-E`：调用 `$EDITOR` 实时修改高亮技能的 `SKILL.md`
     - `Ctrl-X`：对当前项目进行一键解挂
     - `Ctrl-G` / `Ctrl-D`：分组设置 / 解散分组
     - `Ctrl-N` / `Ctrl-U`：安装新技能 / 检查更新
     - `Ctrl-B`：解绑 Git 关联转为本地自建
     - `Enter`：软链接到当前项目
     - `Alt-C`：拷贝实体副本到当前项目

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
```

# 解绑 Git 追踪（转为纯本地技能，保留文件）
mskill -b video-generator

# 一键更新全部已追踪的远程技能
mskill --update-all
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

