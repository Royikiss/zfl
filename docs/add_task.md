# add_task

`add_task` is a CLI tool in the ZFL framework used to manage startup tasks that execute automatically when a shell starts.

---

## 📖 Usage & Options

```bash
add_task [options] <command> [arguments...]
```

### Option Descriptions

- **`-l, --list`**
  List all currently configured startup tasks.
- **`-r, --remove <command...>`**
  Remove a configured startup task (matches against the normalized command string).
- **`-h, --help`**
  Show the help menu.

---

## 💡 Examples

### 1. Add a startup task
```bash
add_task check_update --force
add_task echo "hello world"
```

### 2. View configured tasks
```bash
add_task -l
```

### 3. Remove a startup task
```bash
add_task --remove echo "hello world"
```

---

## ⚙️ How it Works

1. **Task Storage**: Startup tasks are stored in `$ZFL_HOME/core/startup_task_commands.zsh`. Each non-empty line represents a command.
2. **Normalized Writing**: `add_task` automatically normalizes the input command (handling escapes and quotes) and deduplicates to prevent duplicate task entries.
3. **Isolated Startup Execution**: Every time an interactive shell starts, the ZFL startup executor reads instructions line-by-line from the task file and isolates their execution using file descriptor 3 (FD 3), preventing child processes from hijacking the foreground interactive stdin.
4. **Comments & Empty Lines**: Empty lines and lines starting with `#` in the task file are automatically ignored by the executor.
