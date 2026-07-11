# AICP (AI Copy Project) Technical Documentation

This document explains the design goals, execution flow, core mechanisms, autocomplete system, and troubleshooting tips for `functions/aicp.zsh`.

---

## 1. Goals & Design Principles

`aicp` is a Zsh utility designed to **efficiently package and feed project context (codebase, directory tree, and change history) to AI agents**.

Its core design principles are:

1. **Context Structuring**: Automatically generates structured Markdown output tailored for LLM consumption, including directory trees, file indexes, and code blocks containing source snippets.
2. **Clipboard First**: By default, copies packaged context directly to the system clipboard (compatible with `wl-copy`, `xclip`, and `pbcopy`), allowing users to immediately run the command and paste (`Ctrl+V`) into AI chat dialogs.
3. **Token Budget Control**: Limits the total character count, maximum files, and per-file prefixes based on selected replication modes (`fast`/`balanced`/`deep`/`full`), preventing LLM context window overflows and reducing token costs.
4. **Targeted Focusing**: Supports Git differential checks, directory target filters, and regex/keyword filters (both includes and excludes), ensuring only relevant code is packed.
5. **Interactive Collaboration (`--exec`)**: Supports special XML tags inside AI responses to automatically read source snippets and interactively apply unified patch diffs.

---

## 2. Invocation & Parameters

### Command Line Usage
```bash
aicp [options] [-c <file/directory>...]
```

### Parameter Reference Cheat Sheet

| Parameter | Short | Description | Defaults / Options |
|:---|:---|:---|:---|
| `--all` | `-a` | Scan the entire current directory. | - |
| `--choose` | `-c` | Manually specify target files/directories. | Multiple targets allowed |
| `--mode` | - | Context mode and budget level. | `balanced` (options: `fast`/`balanced`/`deep`/`full`) |
| `--query` | - | Keyword filter: include matching files/filenames. | Can be specified multiple times |
| `--query-regex` | - | Regex filter: include matching paths/content. | Can be specified multiple times |
| `--exclude` | - | Keyword exclude: remove matching files/filenames. | Can be specified multiple times |
| `--exclude-regex` | - | Regex exclude: remove matching paths/content. | Can be specified multiple times |
| `--ignore-docs` | - | Ignore documentation files (e.g. Markdown, Sphinx). | Default: off |
| `--changed` | - | Scan only modified and untracked files relative to `HEAD`. | Default: off |
| `--changed-from` | - | Scan only modified/untracked files relative to a branch/tag. | - |
| `--changed-commit-range`| -| Scan changes within a commit range (`A..B`). | - |
| `--snippet-around-query`| -| Extract snippets surrounding matching query matches. | Default: off |
| `--snippet-context-lines`| -| Context lines to preserve around query matches. | Default: `24` lines |
| `--output-format` | - | Format of packaged context. | `markdown` (options: `plain`/`json`) |
| `--quality-report` | - | Append a static quality report to the output. | Default: off |
| `--print` | - | Print output to stdout instead of copying to clipboard. | Default: off |
| `--out` | - | Write packaged context to a specified file. | - |
| `--no-copy` | - | Disable clipboard copying. | Default: off |
| `--read` | - | Copy specific file ranges (e.g. `path:10-30`) to clipboard. | Standalone mode |
| `--init` | - | Initialize onboarding preset and inject onboarding prompt. | Default: off |
| `--exec` | - | Enable interactive AI collaboration loop. | Default: off |
| `--help` | `-h` | Display detailed help on topics. | Topic name is optional |

---

## 3. Core Mechanics Design

### 3.1 Mode Budgets (`MODE_MAP`)
In the underlying Python backend `python/aicp_context.py`, the budget parameters are configured as:

```python
MODE_MAP = {
    "fast": ModeConfig(max_total_chars=45000, max_file_chars=1200, max_files=180, include_snippets=False),
    "balanced": ModeConfig(max_total_chars=120000, max_file_chars=3500, max_files=260, include_snippets=True),
    "deep": ModeConfig(max_total_chars=220000, max_file_chars=7000, max_files=360, include_snippets=True),
    "full": ModeConfig(max_total_chars=999999999, max_file_chars=999999999, max_files=999999, include_snippets=True),
}
```
* `fast` mode packages only the directory tree and file index. It onboarding LLM agents to the codebase structure very quickly.
* `balanced` and `deep` modes truncate single file characters and selectively omit files once the total budget is exceeded, maintaining a highly density context without bloating token usage.
* `full` mode copies whole source files without truncation, respecting gitignore-style patterns defined in a root `.ignore` file.

### 3.2 Interactive Loop (`--exec`)
When `--exec` is enabled, `aicp` injects agent tool capabilities into the packaged context instructions. The AI can trigger system actions via:
* **Reading File Ranges**: `<aicp:read>src/foo.py:10-30</aicp:read>`. The `aicp` daemon parses the tag, queries the terminal to fetch the line ranges, and displays it with line numbers, accumulating this data for the next round.
* **Applying Patches**: `<aicp:write>--- a/src/foo.py ...</aicp:write>`. `aicp` captures the unified diff and prompts the user in the terminal for confirmation before invoking the system's `patch` tool to modify the file.

---

## 4. Lazy Loading & Tab Autocomplete

To keep shell startup times instantaneous, ZFL combines **lazy loading functions** with **completion proxy registers**.

### 4.1 Lazy Loading Mechanism
During Zsh initialization, [core/func.zsh](file:///home/royi/.config/zsh/core/func.zsh) registers stub functions for scripts inside `functions/` instead of sourcing them:
```zsh
for file in $ZFL_HOME/functions/*.zsh; do
  func_name=$(basename $file .zsh)
  eval "${func_name}() { lazy_load_functions ${func_name} \"\$@\"; }"
done
```
The script files are only `source`d and executed when the user runs the command (e.g. `aicp`) for the first time in a session.

### 4.2 Tab Completion Proxy (Lazy Completions)
To enable tab autocompletions **prior to sourcing the functions**, [core/func.zsh](file:///home/royi/.config/zsh/core/func.zsh) creates proxy completion hooks:

```zsh
# Dynamically register completion proxies for each lazy function
eval "_${func_name}() { 
    unfunction _${func_name} 2>/dev/null;                 # 1. Destroy proxy hook to prevent recursion
    source \"\$ZFL_HOME/functions/${func_name}.zsh\";       # 2. Source the actual function code and its real completion definition
    if whence -f _${func_name} >/dev/null; then
        _${func_name} \"\$@\";                             # 3. If real completion handler exists, forward arguments
    else
        _default \"\$@\";                                   # 4. Fallback to default completion if missing
    fi 
}"
if whence compdef >/dev/null; then
    compdef "_${func_name}" "${func_name}"                  # 5. Map the proxy handler in Zsh compdef
fi
```

**How it works**:
1. When a shell opens, both the command `aicp` and its autocomplete handler `_aicp` are lightweight stub functions.
2. The user types `aicp --[Tab]`, triggering the stub `_aicp`.
3. The stub `_aicp` executes:
   - Removes the shell stub `_aicp`.
   - Sources [functions/aicp.zsh](file:///home/royi/.config/zsh/functions/aicp.zsh), which defines the real `_aicp` completion function at the end of the file.
   - Forwards the autocomplete arguments `"$@"` to the newly imported `_aicp` function.
4. Subsequent Tab triggers call the real loaded autocomplete function in memory directly, incurring no additional sourcing overhead.

### 4.3 Autocomplete Definitions
Zsh autocomplete options are defined at the end of [functions/aicp.zsh](file:///home/royi/.config/zsh/functions/aicp.zsh) using the Zsh `_arguments` module.

---

## 5. Troubleshooting

### 5.1 Wayland Stdin Non-blocking Bug (`--exec` mode exiting early)
**Symptoms**: In `--exec` mode, the first round executes normally. However, after choosing `Continue to next round? [Y/n]`, the next read iteration immediately returns EOF and prints `Empty input, exiting`.
**Root Cause**:
* Under Wayland, the clipboard tool `wl-copy` forks a background daemon process.
* This daemon inherits file descriptor 3 (FD 3) pointing to `/dev/tty` from the parent Zsh process.
* The wayland client library sets inherited descriptors to `O_NONBLOCK` in the background daemon.
* Because file descriptor flags are bound to the kernel-level file table description, this sets the parent Zsh process's `/dev/tty` FD 3 to **non-blocking** as well. The next read call fails to block for user input, returning EOF immediately.

**Fix**:
ZFL safely isolates clipboard command executions by redirecting inputs/outputs and **explicitly closing FD 3** when calling clipboard utilities:
```zsh
wl-copy < "$tmp_file" >/dev/null 2>&1 3<&-
```

---

## 6. Related Files

- **Zsh Entry & Shell Logic**: [functions/aicp.zsh](file:///home/royi/.config/zsh/functions/aicp.zsh) (Shell functions, interactive loops, autocomplete)
- **Python Context Engine**: [python/aicp_context.py](file:///home/royi/.config/zsh/python/aicp_context.py) (Parser logic, file indexing, token budgets)
- **Core Loader**: [core/func.zsh](file:///home/royi/.config/zsh/core/func.zsh) (Lazy loading registers, completion proxy anchors)
