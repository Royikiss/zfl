# mskill

`mskill` (Manage Skill) is a full-lifecycle management tool for AI Agent skills (Skills), featuring automatic discovery, self-contained packaging, version tracking, updates, grouping, and selective symlinking into projects.

---

## ✨ Key Features

1. **Auto-Discovery & Self-Contained Packaging**:
   - Automatically anchors on `SKILL.md` regardless of GitHub repository structure (Monorepo, single-skill repo, or nested paths).
   - Bundles all accompanying assets (e.g. `scripts/`, `references/`, `examples/`) into a clean package under `~/.agents/skills/<skill_name>/`.
   - **Multi-Skill Auto-Grouping**: Prompts to create a skill group automatically whenever multiple skills are installed, allowing seamless batch linking later.
2. **Version Tracking & Safe Updates**:
   - Tracks source repository, branch, subpath, and commit hash in `~/.local/share/zfl/skills_manifest.json`.
   - Update commands (`mskill -u` / `mskill --update-all`) perform fast git pulls in local cache mirrors and sync changes to `~/.agents/skills/`.
   - **100% Group Isolation**: Updating skills modifies only code and version metadata, keeping skill groups (`~/.local/share/zfl/skills_groups.json`) completely untouched.
3. **Seamless Project Linking**:
   - Symlinks skills into `.agents/skills/` of the current working directory.
   - Any updates in global `~/.agents/skills/` automatically sync into projects without relinking.
4. **Interactive FZF Interface**:
   - Real-time previews, bilingual descriptions, and hotkeys for group management (`Ctrl-G`), updating (`Ctrl-U`), unbinding Git (`Ctrl-B`), installing (`Ctrl-I`), and deleting (`Ctrl-D`).
5. **Unbind Git Tracking (Convert to Local)**:
   - For deprecated, unmaintained, or locally customized skills, use `mskill -b <skill_name>` or `Ctrl-B` in FZF to detach from upstream Git tracking.
   - Preserves all skill files and group configurations while preventing unwanted remote updates or overwrites.

---

## 🚀 Usage & Commands

```bash
mskill [options] [skill_name/group_name...]
```

### 1. Installation & Download (`-i, --install`)
```bash
# Install from shorthand
mskill -i anthropics/anthropic-quickstarts

# Install from full URL
mskill -i https://github.com/owner/repo

# Install from specific subdirectory
mskill -i https://github.com/owner/repo/tree/main/skills/video-generator

# Interactive installation (prompted in terminal)
mskill -i
```

### 2. Check Version & Update (`-u, --update`, `--update-all`, `--status`)
```bash
# View versions, commits, and source repositories
mskill --status

# Update specific skill
mskill -u video-generator

# Update all tracked remote skills
mskill --update-all
```

### 3. Unbind Git Tracking (`-b, --unbind`)
```bash
# Unbind a skill from remote Git repo (converts to local, preserves files)
mskill -b video-generator

# Press Ctrl-B in FZF menu to unbind focused skill or group
```

### 4. Skill Groups Management (`-s`, `-r`, `-l`)
```bash
# Create/modify group
mskill --group-set dev prototype handoff grill-me

# Create ordered sequence group
mskill --group-set startup --ordered validate-idea first-customers marketing-plan

# List all groups
mskill --group-list

# Delete a group
mskill --group-rm dev
```

### 5. Import Skills into Current Project (Symlink vs Copy)

`mskill` supports two modes to import skills into the current project's `.agents/skills/` directory:

#### A. Symlink Mode (Default / Real-time Sync)
Symlinks global skills via `ln -s`. Updates in the global skills directory automatically propagate to your project in real-time:
```bash
# Symlink specific skills
mskill caveman diagnose

# Symlink entire group
mskill startup

# Interactive selection via FZF (Press Enter to symlink)
mskill
```

#### B. Copy Entity Mode (`-c, --copy` / Standalone Entity)
Copies the full skill directory (`cp -r`) into the current project, eliminating symlink dependency. Ideal for project-specific skill customizations or freezing skill versions:
```bash
# Copy specific skill entities to project
mskill -c caveman diagnose

# Copy all skills in a group as standalone entities
mskill -c startup

# Interactive selection to copy (Press Alt-C in FZF or run mskill -c and press Enter)
mskill -c
```

### 6. View Connected Skills (`-v, --view`)
```bash
mskill -v
```
Displays all imported skills in the current project, clearly distinguishing **[symlink]** vs **[copied entity]** status along with localized translations and descriptions.

