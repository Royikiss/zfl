# AICP (AI Copy Project) 技术文档

本文档说明 `functions/aicp.zsh` 的设计目标、执行流程、核心机制、自动补全框架以及相关排障建议。

---

## 1. 目标与设计原则

`aicp` 是一个专为**将项目上下文（代码库、目录树、修改历史）高效打包并投喂给 AI** 而设计的 Zsh 工具。

其核心设计原则包括：

1. **上下文格式化**：自动生成符合 LLM（大语言模型）阅读习惯的结构化 Markdown 输出，包含项目目录树、文件索引及带代码块标记的源码片段。
2. **剪贴板优先**：默认直接复制到系统剪贴板（兼容 `wl-copy`、`xclip`、`pbcopy`），使用户在终端运行后即可在 AI 对话框中 `Ctrl+V`。
3. **Token 预算控制**：根据不同复制级别（`fast`/`balanced`/`deep`/`full`）严格限制总字符数、最大文件数和单文件前缀字符数，避免超出 LLM 上下文窗口或浪费 Token。
4. **定向聚焦**：支持 Git 增量对比、指定文件、关键词和正则筛选（包括包含和排除），确保只发送最相关的代码。
5. **交互式协作（`--exec`）**：在 AI 回复中支持特定 XML 标签，实现自动读取代码片段、交互式应用 Patch（改动 diff）的反向修改。

---

## 2. 调用方式与参数

### 命令行用法
```bash
aicp [参数...] [-c <文件/目录>...]
```

### 参数速查表

| 参数 | 缩写 | 说明 | 默认值 / 选项 |
|:---|:---|:---|:---|
| `--all` | `-a` | 全量扫描当前目录。 | - |
| `--choose` | `-c` | 手动指定目标文件或目录（可输入多个）。 | - |
| `--mode` | - | 复制等级与预算控制模式。 | `balanced`（可选 `fast`/`balanced`/`deep`/`full`） |
| `--query` | - | 关键词过滤：命中文件名或文件内容时纳入。 | 支持多次指定 |
| `--query-regex` | - | 正则过滤：命中文件名或文件内容时纳入。 | 支持多次指定 |
| `--exclude` | - | 关键词排除：命中文件名或文件内容时剔除。 | 支持多次指定 |
| `--exclude-regex` | - | 正则排除：命中相对路径或文件内容时剔除。 | 支持多次指定 |
| `--ignore-docs` | - | 自动过滤文档类文件（如 markdown, sphinx 等）。| 默认 off |
| `--changed` | - | 仅扫描相对 `HEAD` 的改动及未跟踪文件。 | 默认 off |
| `--changed-from` | - | 仅扫描相对指定分支/标签的改动及未跟踪文件。| - |
| `--changed-commit-range`| -| 仅扫描指定提交区间（`A..B`）的改动。 | - |
| `--snippet-around-query`| -| 启用命中点邻域模式（只复制包含关键词前后的代码）。| 默认 off |
| `--snippet-context-lines`| -| 邻域扩展行数。 | 默认 `24` 行 |
| `--output-format` | - | 输出格式。 | `markdown`（可选 `plain`/`json`） |
| `--quality-report` | - | 在输出中附加项目质量报告。 | 默认 off |
| `--print` | - | 将生成的上下文打印到终端（不写入剪贴板）。| 默认 off |
| `--out` | - | 将生成的上下文写入到指定文件。 | - |
| `--no-copy` | - | 强制跳过复制到系统剪贴板。 | 默认 off |
| `--read` | - | 读取指定文件及可选行号范围（如 `path:10-30`）到剪贴板。| 独立运行模式 |
| `--init` | - | 一键生成项目认知预设包，注入认知提示词。 | 默认 off |
| `--exec` | - | 开启交互式 AI 协作模式。 | 默认 off |
| `--help` | `-h` | 查看详细帮助。 | 可选指定主题 |

---

## 3. 核心机制设计

### 3.1 复制等级与预算定义 (`MODE_MAP`)
在底层的 Python 脚本 `python/aicp_context.py` 中，定义了四种模式的预算上限：

```python
MODE_MAP = {
    "fast": ModeConfig(max_total_chars=45000, max_file_chars=1200, max_files=180, include_snippets=False),
    "balanced": ModeConfig(max_total_chars=120000, max_file_chars=3500, max_files=260, include_snippets=True),
    "deep": ModeConfig(max_total_chars=220000, max_file_chars=7000, max_files=360, include_snippets=True),
    "full": ModeConfig(max_total_chars=999999999, max_file_chars=999999999, max_files=999999, include_snippets=True),
}
```
*   `fast` 模式只复制项目树与文件索引，非常适合让 AI 快速建立系统架构地图。
*   `balanced` 和 `deep` 模式会限制单个文件的字符数（首部截断），并根据字符总预算进行阶段性舍弃，确保不会撑爆 context。
*   `full` 模式会复制完整的文件内容，且如果在项目根目录下存在 `.ignore` 文件，将依据其中的 gitignore 风格规则对文件进行过滤。

### 3.2 交互式 AI 协作机制 (`--exec`)
开启 `--exec` 后，`aicp` 会生成上下文并注入系统能力声明。AI 可以通过以下标签指示终端执行操作：
*   **读取文件**：`<aicp:read>src/foo.py:10-30</aicp:read>`。`aicp` 解析此标签后，会从伪终端直接读取代码内容并带行号显示，同时缓存至本轮迭代，准备在下一轮重新喂回 AI。
*   **修改文件**：`<aicp:write>--- a/src/foo.py ...</aicp:write>`。`aicp` 将截获标准 unified diff，并在终端提示用户确认后，自动通过系统的 `patch` 命令干净应用该补丁。

---

## 4. 懒加载与自动补全设计

为了保障终端的极速启动，本系统采用了**“懒加载函数 + 补全代理占位符”**的联合设计。

### 4.1 函数懒加载机制
在 Zsh 启动时，[core/func.zsh](file:///home/royi/.config/zsh/core/func.zsh) 会遍历 `functions` 文件夹下的所有 `.zsh` 文件，不直接加载它们，而是注册一个桩函数：
```zsh
for file in $ZFL_HOME/functions/*.zsh; do
  func_name=$(basename $file .zsh)
  eval "${func_name}() { lazy_load_functions ${func_name} \"\$@\"; }"
done
```
只有在用户实际键入并运行命令（如 `aicp`）时，`lazy_load_functions` 才会通过 `source` 导入真实的函数体并执行。

### 4.2 补全代理占位符 (补全懒加载)
为了在**首次运行前**就能享受 `Tab` 自动补全，系统在 [core/func.zsh](file:///home/royi/.config/zsh/core/func.zsh) 中引入了**补全代理占位符**逻辑：

```zsh
# 为每个懒加载函数动态注册补全代理
eval "_${func_name}() { 
    unfunction _${func_name} 2>/dev/null;                 # 1. 销毁占位符防止递归
    source \"\$ZFL_HOME/functions/${func_name}.zsh\";       # 2. 真正加载函数体及其实际补全函数
    if whence -f _${func_name} >/dev/null; then
        _${func_name} \"\$@\";                             # 3. 若有实际补全，移交执行
    else
        _default \"\$@\";                                   # 4. 若无实际补全，降级为默认补全
    fi 
}"
if whence compdef >/dev/null; then
    compdef "_${func_name}" "${func_name}"                  # 5. 向 Zsh 注册补全映射
fi
```

**运行原理**：
1.  终端启动：`aicp` 对应的命令函数和补全函数 `_aicp` 均是空壳占位符。
2.  用户首次输入 `aicp --[Tab]`：Zsh 触发占位符 `_aicp`。
3.  `_aicp` 执行：
    *   删除当前的 `_aicp` 壳函数。
    *   `source` 载入 [functions/aicp.zsh](file:///home/royi/.config/zsh/functions/aicp.zsh)。该文件在末尾定义了真实完整的 `_aicp`（见下节）。
    *   检查发现真实的 `_aicp` 已经存在，便将 Zsh 的补全请求参数 `"$@"` 转发给它。
4.  后续运行：由于内存中的 `_aicp` 已被真实补全代码覆写，随后的 `Tab` 会直接呼叫真实的补全逻辑，不再有任何 `source` 开销。

### 4.3 补全逻辑集中定义
根据高内聚的原则，真实的 `_aicp` 补全定义保存在 [functions/aicp.zsh](file:///home/royi/.config/zsh/functions/aicp.zsh) 的文件尾部。它通过 `_arguments` 系统精确补全了各个开关、参数提示和参数的可选值。

---

## 5. 故障排查

### 5.1 Wayland 终端非阻塞污染 Bug (`--exec` 模式循环闪退)
**现象**：在 `--exec` 模式下，第一轮正常运行，但在回答 `继续下一轮？[Y/n]` 确认进入第二轮后，终端输入循环立刻触发 EOF 闪退并提示 `空输入，退出`。
**原因**：
*   在 Wayland 环境下，剪贴板工具 `wl-copy` 在执行复制后，会 Fork 出一个后台 Daemon 守护进程。
*   该 Daemon 继承了父进程 Zsh 的文件描述符（fd 3，指向 `/dev/tty`）。
*   libwayland-client 在后台运行时，会把继承的 fd 3 设为 `O_NONBLOCK`。
*   由于文件描述符状态绑定在内核级表项上，这导致父进程 Zsh 的终端 fd 3 也被同步改写为**非阻塞状态**。第二轮 read 时由于输入未就绪且非阻塞，系统直接返回 EOF，导致闪退。

**修复手段**：
系统中对所有剪贴板进程进行了物理级别的安全隔离。在执行 `wl-copy` 或 `xclip` 时，采用重定向输入输出并**显式关闭 fd 3**：
```zsh
wl-copy < "$tmp_file" >/dev/null 2>&1 3<&-
```

---

## 6. 相关文件

*   **脚本入口与外部逻辑**：[functions/aicp.zsh](file:///home/royi/.config/zsh/functions/aicp.zsh) (Zsh 壳函数、AI 交互循环、自动补全实现)
*   **上下文构建核心**：[python/aicp_context.py](file:///home/royi/.config/zsh/python/aicp_context.py) (过滤逻辑、文件提取、分词与 Token 截断)
*   **函数懒加载机制**：[core/func.zsh](file:///home/royi/.config/zsh/core/func.zsh) (占位符生成、补全自动加载代理)
*   **Wayland Bug 追溯**：[docs/aicp-exec-bug.md](file:///home/royi/.config/zsh/docs/aicp-exec-bug.md) (Bug 排查记录)
