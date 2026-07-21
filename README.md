# ZFL (Zsh Function Library)

ZFL is a high-performance, modular configuration and function library for Zsh. While maintaining instant shell startup speeds (zero file-loading delay), it features non-blocking startup task scheduling, an AI-assisted development context packager, update detection, and various system utilities.

---

## 🚀 Core Features

- **⚡ Zero-Delay Startup (Lazy Loading)**
  - Registers lightweight stubs for scripts under `functions/` on startup. Code files are sourced only when the commands are actually executed.
  - Proxy completion loaders dynamically import complete autocomplete mappings on the first Tab trigger, maintaining both instant shell startups and complete autocomplete experiences.
- **🛡️ Non-Blocking Startup Tasks (FD 3 Isolation)**
  - Reads and executes startup tasks through system file descriptor 3 (`exec 3< ...`), completely isolating them from standard stdin.
  - Prevents background interactive prompts from hijacking foreground stdin, resolving shell locking or crashing issues.
- **🤖 AI-Collaboration Friendly (AICP)**
  - Built-in `aicp` tool packages codebase context under token budgets (`fast`/`balanced`/`deep`/`full` levels) and multi-dimensional filters.
  - Interactive `--exec` mode handles tool execution via XML tags, displaying source ranges and interactively applying unified diff patches upon user confirmation.
- **🔄 Read-only, Non-Blocking Update Checks (check_update)**
  - Query updates asynchronously (Pacman/AUR, Flatpak) on shell startup. Processes only count packages and never invoke `sudo` in the background.
  - Lock directories prevent duplicate checks, and customizable policies (`pending_first`, `once_per_day`, `strict_daily`) control prompt frequency.
- 🔍 **Static Quality Gates & Management (zfl)**
  - Built-in `zfl` static code checker lints variable/file-descriptor leaks, naming styles, hardcoded colors, and missing documentation. Integrates with GitHub Actions gate checks.
  - Parses standardized metadata comment headers to auto-generate lists of available tools and verify system CLI dependencies.
  - Implements immutable core function protection and metadata `#? protected: true` safeguards, preventing built-in tools from accidental deletion.
- 📦 **Universal Decompression & One-Key Compression (extract)**
  - Seamlessly handles multi-format archives (tar, gz, bz2, xz, zst, zip, 7z, rar) with built-in archive-bomb protection.
  - Supports `--compress` (`-c`) mode with parameter-driven format selection (`--zip`, `--tar.gz`, etc.) and rich Tab-completion descriptions.

---

## 📂 Project Structure

```bash
zsh/
├── base.zsh                       # Framework entry point (exports ZFL_HOME and loads core modules)
├── core/                          # Core dispatch and public modules
│   ├── colors.zsh
│   ├── func.zsh
│   ├── startup_task_commands.zsh
│   ├── startup_tasks.zsh
│   ├── usr.zsh
│   └── usr.zsh.example
├── functions/                     # Modular function directory (1:1 mapping between file name and function name)
│   ├── add_task.zsh               # Manage startup tasks list (whitelist management)
│   ├── aicp.zsh                   # Generate project context suitable for AI consumption (directory tree + file index + code snippet budget trimming)
│   ├── check_update.zsh           # Asynchronously check system updates in read-only mode and prompt in terminal, supporting pacman/yay and flatpak
│   ├── countText.zsh              # Count words or Chinese characters in a text file based on the specified mode
│   ├── extract.zsh                # Universal auto-decompressor and compressor with format options, tool fallbacks, and Tab completion
│   ├── link_skills.zsh            # Selectively symlink skills from ~/.agents/skills/ into .agents/skills/ of the current project
│   ├── weather.zsh                # Query real-time weather and weather forecast in terminal
│   └── zfl.zsh                    # ZFL framework built-in command line management and self-discovery tool
├── custom_functions/              # User private local functions directory (ignored by git)
├── python/                        # Cross-language helper scripts
│   ├── aicp_context.py
│   ├── list_skills_fzf.py
│   ├── preview_skill.py
│   ├── resolve_skills.py          # Parse and expand skill groups and skill names, and provide interfaces to manage groups
│   └── zfl_lint.py
├── docs/                          # Technical design, core mechanics, and troubleshooting documentation
│   ├── add_task.md                # Non-blocking startup command and schedule scheduler.
│   ├── aicp.md                    # AI context packaging, token estimation, and interactive `--exec` loop helper.
│   ├── check_update.md            # Non-blocking package queries and interactive system upgrade coordinator.
│   ├── countText.md               # Characters and words counting tool for mixed English-Chinese texts.
│   ├── extract.md                 # Universal auto-decompressor with archive-bomb protection.
│   ├── link_skills.md             # Symbolic link management for globally-defined AI Agent skills.
│   ├── weather.md                 # Quick weather forecast query.
│   └── zfl.md                     # Built-in ZFL CLI manager and auto-discovery engine.
└── automation/                    # AI programming automation verification and sync scripts
    └── sync_readme.py             # Automatically synchronize and verify the README.md project structure tree
```

---

## 🛠️ Installation & Activation

1. Clone ZFL to your `~/.config/zsh` directory:
   ```bash
   git clone https://github.com/Royikiss/zfl.git ~/.config/zsh
   ```
2. Append the following lines to your `~/.zshrc` file to source ZFL:
   ```zsh
   if [[ -f "$HOME/.config/zsh/base.zsh" ]]; then
       source "$HOME/.config/zsh/base.zsh"
   fi
   ```
3. Restart your terminal or run `source ~/.zshrc` to reload.

---

## ⚙️ Custom Configurations (`core/usr.zsh`)

To keep core framework files clean and avoid version control conflicts, `core/usr.zsh` is ignored by `.gitignore` and untracked.

Copy the template file to create your own configuration:

```bash
cp core/usr.zsh.example core/usr.zsh
```

Example configurations inside `core/usr.zsh`:

```zsh
# User custom aliases
alias ls='eza --icons'
alias l='eza -lgh --header --git --icons'

# Network proxies
export HTTPS_PROXY=http://127.0.0.1:7897
export HTTP_PROXY=http://127.0.0.1:7897

# check_update configs
export CHECK_UPDATE_CACHE_TTL_SECONDS=3600   # Cache duration: 1 hour
export CHECK_UPDATE_PROMPT_POLICY=once_per_day # Silent on subsequent prompts today if skipped
```

---

## 📖 Core Commands & Documentation

Each tool in ZFL has a companion markdown documentation under [docs/](file:///home/royi/.config/zsh/docs/). Click the links below to view details:

- ⚙️ [zfl](file:///home/royi/.config/zsh/docs/zfl.md) - Built-in ZFL CLI manager and auto-discovery engine.
- 🤖 [aicp](file:///home/royi/.config/zsh/docs/aicp.md) - AI context packaging, token estimation, and interactive `--exec` loop helper.
- 🔄 [check_update](file:///home/royi/.config/zsh/docs/check_update.md) - Non-blocking package queries and interactive system upgrade coordinator.
- ⚙️ [add_task](file:///home/royi/.config/zsh/docs/add_task.md) - Non-blocking startup command and schedule scheduler.
- 🔗 [link_skills](file:///home/royi/.config/zsh/docs/link_skills.md) - Symbolic link management for globally-defined AI Agent skills.
- 📊 [countText](file:///home/royi/.config/zsh/docs/countText.md) - Characters and words counting tool for mixed English-Chinese texts.
- 📦 [extract](file:///home/royi/.config/zsh/docs/extract.md) - Universal auto-decompressor with archive-bomb protection.
- 🌤️ [weather](file:///home/royi/.config/zsh/docs/weather.md) - Quick weather forecast query.

---

## 🎨 Development Guidelines & Coding Standards

If you plan to contribute new tools or modify functions in ZFL, please adhere to the conventions defined in [CONTRIBUTING.md](file:///home/royi/.config/zsh/CONTRIBUTING.md) and [AGENTS.md](file:///home/royi/.config/zsh/AGENTS.md):

1. **File-to-Function 1:1 Mapping**: New features must reside under `functions/<name>.zsh` containing exactly one entry function named `<name>()`.
2. **Metadata Header Standards**: Include standardized metadata descriptions (lines starting with `#?`) declaring name, description, author, version, deps, and usage at the very top of files.
3. **Strong Variable Declarations**: All loop iterators, read buffers, and temporary variables must be explicitly declared as `local` to prevent namespace pollution.
4. **Helper Function Cleanup**: Out-of-scope helper functions must start with `_parentname_` and be unloaded using `unfunction` before the parent exits. Embedded inner function structures are highly recommended.
5. **FD 3 Safe Closing**: Background tasks (`&`, `coproc`) or subshell forks must explicitly close file descriptor 3 (`3<&-`), preventing parent shells from hanging or locking.
6. **No Hardcoded Colors**: Use `load_color` instead of hardcoding ANSI escape codes. Declare CLI requirements at the top of functions using `zfl_require`.
7. **Local Static Verification**: Run `zfl lint <name>` and verify that it returns exit code `0` before committing changes.
