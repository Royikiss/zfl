# zfl

`zfl` is the built-in CLI management tool for the ZFL (Zsh Function Library) framework. It provides automatic function discovery, metadata querying, and dependencies checking, helping developers standardize and explore available scripts.

ZFL supports isolating personal local functions from shared community functions, managing their automatic lazy loading and tab completion proxy registration.

---

## 📂 Directory Structure Isolation

ZFL scans and loads scripts from two directories:
1.  `functions/`: Community-contributed official/public functions.
2.  `custom_functions/`: Private local scripts for individual users (ignored by `.gitignore` to avoid version control conflicts when updating the framework).

Upon shell startup, ZFL automatically scans these directories to register lazy-loading stubs and tab completion proxies.

---

## 📖 Usage & Subcommands

```bash
zfl <subcommand> [arguments]
```

### Available Subcommands

*   **`list` or `ls`**
    Scan `functions/` and `custom_functions/` directories, listing all functions with their sources (community/user) and short descriptions extracted from metadata headers.
*   **`info <function_name>`**
    View detailed metadata (author, version, external dependencies, usage, examples, etc.) of a specific function.
*   **`check`**
    Check all external CLI dependencies declared in functions metadata, reporting whether they are installed in the current system.
*   **`lint [function_name...]`**
    Perform static code analysis on specified functions (or all functions if omitted) to check style compliance and variable leaks.
*   **`remove <function_name>` or `rm <function_name>`**
    Safely delete a function file (prompts with `[y/N]`), uninstall it and its completion proxies from the current session (`unfunction`), and automatically synchronize the project structure tree.
*   **`help` or `-h`**
    Show the help menu.

---

## 💡 Examples

```bash
zfl list            # List all available functions
zfl info weather    # View metadata of the weather tool
zfl check           # Check external dependency status of all functions
zfl lint weather    # Check weather function code quality and leak risks
zfl lint            # Lint all scripts under functions/ and custom_functions/
zfl remove weather  # Safely delete weather and unload its hooks from current session
```

---

## 🔍 Code Static Quality Gate (zfl lint)

`zfl lint` integrates a Python static analysis tool to inspect script quality in local environments or CI workflows. Key check items include:

1.  **File-to-Function 1:1 Mapping**: File `foo.zsh` must contain and only define a main entry function `foo()`.
2.  **Global Variable Leaks**: Scans variables assigned in functions. Any variable that is not explicitly declared using `local` or `typeset`, and is not in the system whitelist, will trigger a leak warning.
3.  **FD 3 Leak Risks**: Checks if background tasks (like `&`, `coproc`) have file descriptor 3 safely closed (`3<&-`), preventing sub-processes from locking the parent terminal.
4.  **Hardcoded Colors**: Flags any hardcoded ANSI escape color codes, encouraging developers to use the library's `load_color` instead.
5.  **Companion Documentation**: Warns if a matching `.md` documentation file is missing from the `docs/` folder.

---

## 📝 Metadata Header Standard

To enable `zfl` to parse and display function information, it is recommended to include metadata headers (lines starting with `#?`) at the top of scripts in `functions/` or `custom_functions/`:

```zsh
#? name: weather
#? description: Query real-time weather and forecast in terminal
#? author: Royi
#? version: 1.0.0
#? protected: true
#? deps: curl
#? usage: weather [city_name]
#? example: weather beijing
```

> **🛡️ Core Function Protection Mechanism**:
> 1. **Hardcoded Protection Whitelist**: Built-in core functions (`zfl`, `aicp`, `check_update`, `add_task`, `link_skills`, `countText`, `weather`, `extract`) are hardcoded and cannot be deleted via `zfl remove`.
> 2. **Metadata Protection Tag**: Adding `#? protected: true` in any script header prevents `zfl remove` from deleting it.
> 3. **Tab Completion Filtering**: `zfl remove <Tab>` automatically excludes protected core functions, allowing completion only for removable custom scripts.

*The metadata parser will automatically stop reading after it encounters a non-comment or empty line, ensuring lightweight and fast execution.*

---

## 🛡️ Dependency Check Assertions (`zfl_require`)

When writing functions that depend on third-party commands (e.g. `fzf`, `jq`), it is recommended to invoke `zfl_require` at the beginning of the main function entry.

### Example

```zsh
my_tool() {
    # Check dependencies. Missing tools will output a friendly warning and return 1.
    zfl_require fzf jq || return 1

    # Main logic
    ...
}
```
