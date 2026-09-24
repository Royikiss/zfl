# mskill

`mskill` (Manage Skill) is a full-lifecycle management and engineering collaboration hub for AI Agent skills, featuring automatic discovery, local directory import, self-contained packaging, version tracking, atomic persistence, declarative project dependency sync, health diagnosis, scaffolding, and full-featured FZF interactive console with project mount status awareness.

---

## ✨ Key Features

1. **Auto-Discovery, Packaging & Local Directory Import**:
   - Automatically anchors on `SKILL.md` regardless of GitHub repository structure (Monorepo, single-skill repo, or nested paths).
   - Bundles all accompanying assets (e.g. `scripts/`, `references/`, `examples/`) into `~/.agents/skills/<skill_name>/`.
   - **Local Directory Import**: Run `mskill -i /path/to/local-dir` to import and manage locally developed skills.
   - **Branch / Tag Pinning**: Supports `owner/repo@v1.0.0` or `owner/repo#branch`.
   - **Multi-Skill Auto-Grouping**: Prompts to create a skill group automatically when multiple skills are installed.
2. **Version Tracking & Atomic Persistence**:
   - Tracks repository source, branch, subpath, and commit hash in `~/.local/share/zfl/skills_manifest.json`.
   - Uses temporary file replacement for **Atomic JSON Writes**, preventing file corruption upon sudden termination.
   - Group configurations (`skills_groups.json`) remain 100% untouched upon updating.
3. **Symlink, Eject to Physical Copy & Safe Unlink**:
   - **Symlink (Default)**: Symlinks global skills into `.agents/skills/` of current project.
   - **Eject (`mskill eject`)**: Converts project symlinks into standalone physical copies in place for custom tweaks.
   - **Safe Unlink (`mskill --unlink`)**: Safely removes skill from current project without touching the global library.
4. **Team Collaboration & Declarative Dependencies (`dump` & `sync`)**:
   - **`mskill dump`**: Exports current project's skills and mounting modes into `.skillsrc`.
   - **`mskill sync`**: Team members run `mskill sync` to automatically pull missing skills and align project mounts.
5. **Health Diagnosis & Self-Healing (`mskill doctor`)**:
   - Diagnoses and repairs broken symlinks, checks `SKILL.md` integrity, and verifies required system CLI tools.
6. **Standard Skill Scaffold Generator (`mskill new <name>`)**:
   - Generates compliant skill templates with standard frontmatter, bilingual templates, `scripts/`, and `references/`.
7. **Interactive FZF Console with Mount Status Awareness**:
   - **Hierarchical Drill-Down Search**: Searches directly through all skills within groups, prioritizing parent group display and rendering matched items in expanded mode with match statistics (e.g. `(2 matched)`).
   - **Mount Badges**: Visually shows `[🔗linked]`, `[📄copied]`, or `[🔗:xx%, 📦:xx%]` percentage badges.
   - **Decoupled Group Identifiers & Display Titles**: Supports distinct CLI keys (e.g. `group:dev`) and human-readable aliases (e.g. `[Group: Daily Development Collaboration]`), keeping rigorous column alignment.
   - **Smart Tokenized Translation & Instant Pre-fetch**: Automatically tokenizes hyphenated identifiers (kebab-case) for clean machine translation, and pre-fetches Chinese translations immediately upon skill installation.
   - **Rich Hotkeys (Fully Bound with Multi-Selection Support)**:
     - `Tab` / `→` / `←`: Toggle group
     - `Ctrl-O`: Toggle all
     - `Space`: Multi-select toggle (All action hotkeys automatically prioritize multiple selections; fallback to focused item under cursor if unselected)
     - `Ctrl-E`: Open `$EDITOR` to modify `SKILL.md` of selected skill(s) (supports editing multiple files)
     - `Ctrl-X`: Safely unlink selected skill(s) from current project (with detailed mount mode inspection)
     - `Ctrl-G` / `Ctrl-D`: Set group (with custom title support) / Batch remove from groups or delete group
     - `Ctrl-N` / `Ctrl-U`: Install new skill / Batch check and update selected skills
     - `Ctrl-B`: Batch unbind Git tracking for selected skills (convert to local)
     - `Ctrl-T`: Batch force re-fetch Chinese translations for selected skills
     - `Enter`: Batch symlink selected skills to project
     - `Alt-C`: Batch copy physical entities to project

---

## 🚀 Usage & Commands

```bash
mskill [options] [skill_name/group_name...]
```

### 1. Installation & Local Import (`-i, --install`)
```bash
# Install from shorthand
mskill -i anthropics/anthropic-quickstarts

# Install specific Tag or branch
mskill -i owner/repo@v2.1.0
mskill -i owner/repo#dev

# Import local directory
mskill -i /path/to/local-dir

# Interactive installation
mskill -i
```

### 2. Project Mount Operations (Link / Eject / Unlink)
```bash
# Symlink into current project (default)
mskill caveman diagnose
mskill startup                    # Symlink entire group

# Eject symlinks into physical standalone copies
mskill eject video-generator
mskill eject                      # Eject all symlinked skills in project

# Unlink from project safely (preserves global skills)
mskill --unlink video-generator
mskill --unlink startup           # Unlink entire group
mskill --unlink-all               # Clear all skills in current project
```

### 3. Declarative Team Sync (`dump` / `sync`)
```bash
# Export current project skills manifest to .skillsrc
mskill dump

# Align and install all project skills on a new machine
mskill sync
```

### 4. Skill Scaffolding & Health Check (`new` / `doctor`)
```bash
# Scaffold a new standard skill template
mskill new my-awesome-skill

# Run diagnostic health check
mskill doctor
```

### 5. Check Version & Update (`-u`, `--update-all`, `--status`, `-b`)
```bash
# View versions, commits, and source repositories
mskill --status

# Update specific skill
mskill -u video-generator

# Update all tracked remote skills
mskill --update-all

# Unbind Git tracking (convert to local standalone skill)
mskill -b video-generator
```

### 6. Skill Groups Management (`-s`, `-r`, `-l`)
```bash
# Create or modify group
mskill --group-set dev prototype handoff grill-me

# Create ordered sequence group
mskill --group-set startup --ordered validate-idea first-customers marketing-plan

# List all groups
mskill --group-list

# Delete a group
mskill --group-rm dev
```

### 7. View Connected Skills & Pre-fetch Translations (`-v`, `--translate-all`)
```bash
# View current project skills
mskill -v

# Batch pre-fetch Chinese translations
mskill --translate-all
```

---

## 🏗️ System Architecture Design & Guidelines (Architecture Foundation)

`mskill` adheres to a decoupled **Three-Tier Architecture**, designed around Domain-Driven Design and high-leverage Deep Modules:

```mermaid
flowchart TD
    subgraph "1. Shell Lightweight Layer (functions/mskill.zsh)"
        User[Command Invocation] --> ShellGuard{Fast-path Check}
        ShellGuard -->|"-h / --help"| ShellHelp[Native Fast Help]
        ShellGuard -->|"No args / pure -c"| FZFUI[Full-featured FZF Console]
        ShellGuard -->|"All CLI arguments"| Forward[Transparent Forwarding: python3 manage_skills.py "$@"]
        FZFUI -->|User Selection| Forward
    end

    subgraph "2. Unified Dispatch Facade (python/manage_skills.py)"
        Forward --> Facade[Unified Dispatch Facade]
        Facade --> HomeGuard[Home Directory Security Guard]
        Facade --> SmartDetect[Git / URL / Shorthand Auto-detect]
        Facade --> Lifecycle[Lifecycle Management: install / update / doctor / new]
    end

    subgraph "3. Core Domain Engines (python/skill_engine/)"
        Facade --> GroupsEngine[_groups.py: Group CRUD / Target Resolution / Completion]
        Facade --> MountEngine[_mount.py: Project Mount / Eject / Unlink / .skillsrc Sync]
        Facade --> DisplayEngine[_display.py: Modern Streamlined Layout / CJK Alignment]
        GroupsEngine --> StoreEngine[_store.py: Atomic JSON I/O & Cache]
        MountEngine --> StoreEngine
    end
```

### 1. Architectural Tiers & Responsibilities

1. **Shell Lightweight Layer (`functions/mskill.zsh`)**:
   - **Narrow Scope**: Hosts Zsh native completion proxies, zero-latency `-h/--help` fast path, and the zero-argument interactive FZF menu.
   - **Transparent Forwarding**: All CLI arguments with parameters are transparently forwarded to the Python unified facade.
2. **Unified Dispatch Facade (`python/manage_skills.py`)**:
   - **Single Source of Truth**: Serves as the sole external execution Seam, managing all CLI definitions, parameter validations, error exit codes, and workflows.
   - **Security & Smart Detection**: Enforces Home Directory Protection to prevent corrupting global skills, and smart auto-detects repository URLs/shorthands for instant installation.
3. **Core Domain Engines (`python/skill_engine/`)**:
   - **`_groups.py`**: Manages group CRUD, ordered sequence tracking, bidirectional target resolution (`resolve_group_targets`), and Zsh tab completion generation.
   - **`_mount.py`**: Handles root discovery, symlinks, physical copies, in-place ejection (`eject`), safe unlinking (`unlink`), and declarative `.skillsrc` alignment.
   - **`_store.py`**: Handles atomic JSON persistence.
   - **`_display.py`**: Encapsulates modern streamlined layout rendering and CJK visual width alignment.

---

## ⚠️ Architectural Invariants for Future Development (Strictly Preserved)

To prevent architectural erosion during future maintenance or feature additions, developers and AI agents **MUST** follow these rules:

> [!IMPORTANT]
> **Rule 1: Never Re-introduce Manual Shell Argument Parsing**  
> `functions/mskill.zsh` must remain lean. **Do not** add `while case` argument parsing loops or manage `opt_*` state flags in shell scripts. All CLI arguments must be handled in the unified facade (`manage_skills.py`) and underlying engines.

> [!IMPORTANT]
> **Rule 2: Single External Seam Principle**  
> `manage_skills.py` is the **only legitimate entry point** for shell invocations. Shell scripts (including FZF `bind` hotkeys) must never bypass this facade to call backend scripts or internal `skill_engine` modules directly.

> [!IMPORTANT]
> **Rule 3: Pure Data Domain Engines & Unit Test Coverage**  
> Functions in `skill_engine/` must remain decoupled from terminal UI formatting (`print`, ANSI codes), returning structured data dictionaries or booleans. Every engine module must have comprehensive, deterministic unit test coverage in `tests/` (`pytest` must 100% pass).

> [!IMPORTANT]
> **Rule 4: Strict Storage & Cache Isolation**  
> Persistent state must reside in `~/.local/share/zfl/`, while transient locks reside in `~/.cache/zsh/`. Never write uncommitted or temporary files directly into skill repositories or code workspaces.


