# check_update Detailed Documentation

This document explains the design goals, execution flow, configurations, status files, troubleshooting, and maintenance guidelines for `functions/check_update.zsh`.

Scope: The startup workflow defined in `base.zsh -> core/startup_tasks.zsh -> check_update`.

---

## 1. Goals & Design Principles

`check_update` triggers prompts at shell startup and runs package updates on demand. Its goals are:

1. **Non-blocking Startup**
   - The foreground reads from local cache first.
   - If the cache is missing or expired, it spawns an asynchronous background job to refresh the cache.

2. **No sudo in Background**
   - Background tasks only run read-only update queries (`checkupdates`, `pacman -Qu`, `yay -Qua`, `flatpak remote-ls`).
   - Privilege-escalation commands (`yay -Syu`, `flatpak update`) are executed only after user confirmation.

3. **Configurable Prompt Frequency**
   - Supports strategy-based prompt policies to prevent update prompts from being too noisy.

4. **Self-Healing Locks**
   - Detects and clears stale lock directories to prevent background refresh processes from hanging indefinitely.

---

## 2. Entrance & Invocation

- **Automatic Trigger**: Sourced from `check_update` listed in `core/startup_task_commands.zsh`.
- **Manual Invocation**:
  - `check_update`
  - `check_update --force`
  - `check_update --help`

### Parameter Options:

- `-f, --force`
  - Ignore standard frequency constraints and enter the interactive prompt immediately.
- `-h, --help`
  - Show the help menu.

---

## 3. Backends & Responsibility Division

Currently supported package backends:

1. **`aur_pacman`**
   - Availability: `yay` exists.
   - Counting (Read-only):
     - Official repository: `checkupdates` (falls back to `pacman -Qu` if missing)
     - AUR: `yay -Qua`
     - Total = Official + AUR
   - Perform Update: `yay -Syu`

2. **`flathub`**
   - Availability: `flatpak` exists and remotes contain `flathub`.
   - Counting (Read-only): `flatpak remote-ls --updates --columns=application,origin`
   - Perform Update: Runs `flatpak update -y <ref>` for each update, displaying `[idx/total]` progress.

---

## 4. Key Status Files

Directory: `~/.cache/zsh`

1. **`UpdateFlag.lock`**
   - Meaning: The date of the last successful update (YYYY-MM-DD).
   - Written only after a successful package update.

2. **`UpdatePromptFlag.lock`**
   - Meaning: The date of the last skipped/rejected update prompt.
   - Written only when the user chooses to skip updates.

3. **`UpdateCountCache.lock`**
   - Meaning: Cache of available update counts (in Shell assignment format).
   - Fields:
     - `generated_at=<epoch>`
     - `aur_pacman=<count>`
     - `flathub=<count>`

4. **`UpdateRefresh.lock/`**
   - Meaning: Mutex lock directory for background cache refreshes.
   - Contains: `.timestamp` (epoch value).
   - Automatically recycled after timing out.

5. **`CheckUpdateProcess.lock/`**
   - Meaning: Mutex process lock directory (ensuring a single instance run across the machine).
   - Contains:
     - `pid` (process ID)
     - `.timestamp` (epoch value)
   - If the process exited, the next run will recycle the stale lock and re-acquire it.

*Note: Lock files are written with read-only permissions (0400), temporarily modifying permission during writes and restoring it afterwards to prevent accidental modifications.*

---

## 5. Execution Flow

1. **Parameter Parsing**
   - Parses `--force` and `--help`.
   - Rejects other parameters, returning a non-zero exit code.

2. **Status Initialization**
   - If `UpdateFlag.lock` is missing on first run, it initializes it with today's date (so that it does not prompt on first install).

3. **Cache & Backend Query**
   - Detects available backends.
   - Reads `UpdateCountCache.lock`.
   - If cache is missing or stale, it schedules a background task to refresh the count (without blocking startup).

4. **Policy Evaluation**
   - Checks `CHECK_UPDATE_PROMPT_POLICY` to decide if it should prompt the user (see Section 6).
   - `--force` overrides any policy checks.

5. **Interactive QA Loop**
   - Inputs:
     - `Enter / Y / y` => Run package updates
     - `C / c` => List available update counts from each backend and query again
     - `N / n / other` => Skip updates

6. **Status Persistence**
   - Update succeeded: Writes `UpdateFlag.lock`, removes the daily skip flag, and triggers a background refresh.
   - User skipped: Writes `UpdatePromptFlag.lock`.
   - Update failed: Does not write any flags, making it easy for the user to retry after fixing issues.

---

## 6. Environment Variables (Customizable Policies)

1. **`CHECK_UPDATE_CACHE_TTL_SECONDS`**
   - Meaning: Validity duration of the cached update count (seconds).
   - Default: `1800`.
   - Falls back to default if invalid.

2. **`CHECK_UPDATE_LOCK_STALE_SECONDS`**
   - Meaning: Stale threshold of the background refresh lock directory (seconds).
   - Default: `600`.
   - If the lock timestamp exceeds this threshold, the lock is cleared and rebuilt.
   - Falls back to default if invalid.

3. **`CHECK_UPDATE_PROCESS_LOCK`**
   - Meaning: Path of the process lock directory (defaults to `~/.cache/zsh/CheckUpdateProcess.lock`).
   - Purpose: Prevents multiple foreground check instances from running concurrently.

4. **`CHECK_UPDATE_PROMPT_POLICY`**
   - Supported values:
     - `pending_first` (default)
       - Prompts the user if there are still pending updates on the same day (reduces missed updates).
     - `once_per_day`
       - Prompts at most once a day; silences further prompts once the user skips.
     - `strict_daily`
       - Prompts only if the last successful update date was not today.
   - Falls back to `pending_first` if invalid.

### Recommended Configuration Example (can be placed in `core/usr.zsh`):

```zsh
# Cache validity: 30 minutes
export CHECK_UPDATE_CACHE_TTL_SECONDS=1800

# Background lock expiry: 10 minutes
export CHECK_UPDATE_LOCK_STALE_SECONDS=600

# Prompt policy: prompt once per day
export CHECK_UPDATE_PROMPT_POLICY=once_per_day
```

---

## 7. Startup Tasks Executor Cooperation

`core/startup_tasks.zsh` isolates startup commands by reading task files from file descriptor 3 (FD 3), preventing stdin conflicts.

Significance:
- `check_update` interactive `read` queries read from the real terminal stdin.
- The executor will not misread lines or comments in the task file, avoiding false skips.

---

## 8. Exit Code Meanings

From the startup executor perspective:
- `0`: Task succeeded (including controlled paths like user skips).
- Non-zero: Task failed (e.g. invalid arguments or package update error).

Within the `check_update` QA handler:
- `0`: Update succeeded.
- `2`: User skipped.
- Other: Update failed.

The main function maps the skip branch (`2`) to a successful execution return (`0`), ensuring startup logs show `exit=0`.

---

## 9. Troubleshooting

1. **Issue: Startup count cache does not refresh**
   - Diagnosis: Check if `~/.cache/zsh/UpdateRefresh.lock` remains.
   - Solution:
     - It should be auto-recycled by lock stale checks.
     - Manual override: run `rm -rf ~/.cache/zsh/UpdateRefresh.lock`

2. **Issue: Prompting for updates on every shell startup**
   - Diagnosis:
     - Check if the prompt policy is `pending_first`.
     - Check if the counts in `UpdateCountCache.lock` are continuously > 0.
   - Solution: Switch policy to `once_per_day` or `strict_daily`.

3. **Issue: Prompting for sudo passwords in the background**
   - This should not occur under the current design.
   - If it happens, it is usually triggered by external tasks, not the `check_update` cache count queries.

4. **Issue: Policies or help edits not taking effect**
   - Solution: Reload the shell environment or run `source core/func.zsh` again.

---

## 10. Development Guidelines

1. **Make a checkpoint commit before editing**
   - Startup hooks can affect shell load. Always make a git commit anchor first.

2. **Keep "Query" and "Update" logic strictly separate**
   - Never run `sudo` during the query stage.
   - Request privileges only when the user confirms the update.

3. **Maintain Observability**
   - Keep details such as cache age, lock status, and backend availability visible to help troubleshoot issues.

4. **Adhere to conventions when adding new backends**
   - Each backend must implement 3 functions:
     - `_check_update_backend_available_<name>`
     - `_check_update_backend_count_<name>`
     - `_check_update_backend_update_<name>`

---

## 11. Future Enhancements

1. Add `quiet/info/debug` logging levels.
2. Modularize backend registrations (decoupling from static arrays).
3. Implement smoke tests (such as syntax validations and dry-run parameters).
4. Introduce per-backend cache timestamps for finer refresh granularity.

---

## 12. Related Files

- `functions/check_update.zsh`
- `core/startup_tasks.zsh`
- `core/startup_task_commands.zsh`
- `README.md`
