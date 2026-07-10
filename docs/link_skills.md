# link_skills

`link_skills` 用于将全局定义好的 AI Agent 技能配置（Skills）选择性地以符号链接的形式引入当前项目目录。

---

## 📖 用法与选项

```bash
link_skills [选项] [技能名称...]
```

### 选项说明

- **`-h, --help`**
  显示帮助信息。

---

## 💡 示例

### 1. 命令行直接指定技能名
```bash
link_skills caveman diagnose
```
会将 `~/.agents/skills/caveman` 和 `~/.agents/skills/diagnose` 符号链接到当前工作目录下的 `.agents/skills/` 对应位置。

### 2. 交互式多选模式 (需要安装 `fzf`)
```bash
link_skills
```
若不带参数运行，工具将扫描 `~/.agents/skills/` 目录，并启动 `fzf` 交互式筛选菜单，让您可以多选技能进行快捷链接。

---

## ⚙️ 运行机制

1. **自动归宿**：链接将被创建在当前工作目录的 `.agents/skills/<技能名>` 下。如果父目录不存在，将自动创建。
2. **软链接同步**：采用 `ln -s` 进行软链接映射。这样您在全局 `~/.agents/skills/` 下进行的任何 Skill 修改，当前项目都能自动实时同步，无需重复手动复制更新。
