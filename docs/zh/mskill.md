# mskill

`mskill` (Manage Skill) 是针对 AI Agent 技能（Skills）的全生命周期管理工具，集成了**自动识别与打包下载、版本追溯与一键更新、软链接引入项目、技能分组管理与中英文双语 FZF 交互预览**。

---

## ✨ 核心特性

1. **精准识别与自包含完整打包**：
   - 无论远程 GitHub 仓库是单 Skill 仓库、Monorepo 大仓库还是深层嵌套目录，均以 `SKILL.md` 所在目录为边界。
   - 将其伴生依赖（如 `scripts/` 脚本、`references/` 知识库文档、`examples/` 示例配置等）完整自包含打包下载至 `~/.agents/skills/<skill_name>/`。
   - **多技能自动分组引导**：若数据包包含多个技能，安装完成后自动提示快速创建技能分组（支持默认命名与有序标记），便于日后一键批量引用。
2. **版本追踪与平滑更新**：
   - 在 `~/.local/share/zfl/skills_manifest.json` 中跟踪远程仓库源、分支、Commit Hash 及子路径。
   - 执行更新（`mskill -u` / `mskill --update-all`）时，自动拉取远程最新变更并增量同步。
   - **分组结构 100% 保持不变**：更新技能只变更代码和版本元数据，绝不破坏任何已有的分组配置（`~/.local/share/zfl/skills_groups.json`）。
3. **极速软链接与实时生效**：
   - 将全局技能以符号链接（`ln -s`）形式引入当前项目的 `.agents/skills/` 中。
   - 全局更新后，所有关联项目瞬间自动获得最新版本，无需重新链接。
4. **全功能 FZF 交互控制台**：
   - 终端直接运行 `mskill` 即可唤起交互式菜单，支持实时中英文预览。
   - 快捷键支持：组管理 (`Ctrl-G`)、更新当前项 (`Ctrl-U`)、解绑 Git (`Ctrl-B`)、安装新技能 (`Ctrl-I`)、删除组 (`Ctrl-D`)、重译 (`Ctrl-T`)。
5. **解绑 Git 仓库（转为本地自建）**：
   - 针对下游已停止维护或已被本地定制修改的技能，可通过 `mskill -b <技能名>` 或 FZF 快捷键 `Ctrl-B` 解绑远程 Git 追踪。
   - 本地技能文件与分组配置 100% 完整保留，不再受到远程更新检查或覆盖影响。

---

## 🚀 命令与用法

```bash
mskill [选项] [技能名称/分组名称...]
```

### 1. 下载与安装技能 (`-i, --install`)
```bash
# 通过 GitHub 简写安装
mskill -i anthropics/anthropic-quickstarts

# 通过完整 URL 安装
mskill -i https://github.com/owner/repo

# 通过具体子目录直链精准安装
mskill -i https://github.com/owner/repo/tree/main/skills/video-generator

# 终端交互式安装引导
mskill -i
```

### 2. 检查版本与更新 (`-u, --update`, `--update-all`, `--status`)
```bash
# 查看所有已安装技能的版本 Commit 与远程来源
mskill --status

# 检查并更新指定技能
mskill -u video-generator

# 一键更新全部已追踪的远程技能
mskill --update-all
```

### 3. 解绑 Git 追踪 (`-b, --unbind`)
```bash
# 解绑指定技能的远程 Git 关联（转为本地自建技能，保留全部文件）
mskill -b video-generator

# 在 FZF 菜单中直接按 Ctrl-B 解绑当前高亮技能或分组
```

### 4. 技能分组管理 (`-s`, `-r`, `-l`)
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

### 5. 引入技能到当前项目 (软链接 vs 实体拷贝)

`mskill` 支持两种方式将技能引入当前项目的 `.agents/skills/` 目录：

#### A. 软链接模式 (默认 / 实时同步)
将全局技能以符号链接（`ln -s`）方式接入当前项目。当全局技能更新时，项目内立即同步生效：
```bash
# 软链接指定技能到当前项目
mskill caveman diagnose

# 软链接整个分组下的所有技能
mskill startup

# 交互式选择并软链接 (FZF 菜单按 Enter)
mskill
```

#### B. 实体拷贝模式 (`-c, --copy` / 独立副本)
将技能实体目录完整拷贝（`cp -r`）到当前项目中，摆脱软链接依赖。适合需要为特定项目定制修改 Skill 内容或冻结特定版本的场景：
```bash
# 拷贝指定技能实体到当前项目
mskill -c caveman diagnose

# 拷贝整个分组下的所有技能实体到当前项目
mskill -c startup

# 交互式选择并拷贝技能实体 (FZF 菜单按 Alt-C 或直接运行 mskill -c 按 Enter)
mskill -c
```

### 6. 查看当前项目已引入的技能 (`-v, --view`)
```bash
mskill -v
```
清晰展示当前项目中已引入的所有技能、区分 **[软链接]** 与 **[实体副本]** 状态，并列出其中文译名与功能描述。

