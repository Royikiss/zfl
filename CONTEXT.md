# Domain Context (CONTEXT.md)

Shared domain glossary for the ZFL (Zsh Function Library) codebase.

---

## Domain Concepts

### Function Metadata
The standardized `#?` comment block placed at the very top of every function script in `functions/` and `custom_functions/`.
- **Mandatory Fields (7)**: `name` (名称), `description` (描述), `author` (作者), `version` (版本), `deps` (依赖), `usage` (用法), `example` (示例).
- **Optional Control Tags**: `protected` (受保护, blocks accidental deletion via `zfl remove`), `quiet` (静默/免提示, suppresses `[lazy_load]` notice during first invocation).

### Metadata Engine
The deepened module (`python/metadata_engine.py`) serving as the Single Source of Truth for parsing, alias canonicalization, type coercion, and validation across all developer tooling (`zfl_lint.py`, `sync_readme.py`) and CI workflows.

### Compiled Metadata Cache
An atomically compiled Zsh script (`~/.cache/zsh/metadata.zsh`) containing pre-indexed native associative arrays (`ZFL_META_*`).
- Consumed by `core/metadata.zsh` to provide **0-fork, sub-millisecond** access during interactive shell startup and CLI inspection (`zfl list`, `zfl info`, `zfl check`).
- Automatically recompiled whenever function directory modification timestamps (`mtime`) change.

### Lazy Loading & Function Stubs
Framework mechanism in `core/func.zsh` where shell initialization only registers lightweight proxy placeholder stubs and completion proxies, ensuring zero file loading overhead at terminal launch. The real function body is sourced only upon first invocation.

### Startup Tasks
Non-blocking asynchronous initialization tasks configured in `core/startup_task_commands.zsh` and executed by `core/startup_tasks.zsh` using an isolated file descriptor (FD 3).

### Skill Dispatch Facade
The deepened module (`python/manage_skills.py`) serving as the unified command and lifecycle facade for all AI Agent skill operations, consolidating group management, translation prefetching, project mounting, and interactive workflows behind a single execution seam.

### Skill Groups & Mount Subsystem
The deepened domain modules located in `python/skill_engine/` (`_groups.py` and `_mount.py`):
- `_groups.py`: Encapsulates atomic persistence, lookup, CRUD mutations, bidirectional target expansion (resolving mixed group and skill references), and Zsh tab completion generation for skill groups.
- `_mount.py`: Encapsulates project-level skill attachment (`.agents/skills`), managing symlink linking, physical copy conversion (ejection), unlinking, and declarative `.skillsrc` manifest export/sync.

### Transparent Shell Forwarding
The architectural pattern utilized by `functions/mskill.zsh` where the shell layer only retains native completion proxies, zero-latency help, and zero-argument interactive FZF menus. All parameterized command-line invocations are transparently forwarded (`python3 manage_skills.py "$@"`) to the Python facade, eliminating dual argument parsing loops and establishing Python as the Single Source of Truth.

### mskill Architecture Invariants
Strict development rules governing `mskill`:
1. Never re-introduce manual shell argument parsing (`while case`) in `mskill.zsh`.
2. All invocations and FZF actions must target the single `manage_skills.py` facade seam.
3. Domain engines in `skill_engine/` must remain pure data (no terminal UI printing) with 100% deterministic unit tests.



