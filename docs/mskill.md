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
   - **Mount Badges**: Visually shows `[🔗linked]`, `[📄copied]`, or `[all mounted]`.
   - **Rich Hotkeys**:
     - `Tab` / `→` / `←`: Toggle group
     - `Ctrl-O`: Toggle all
     - `Space`: Multi-select
     - `Ctrl-E`: Open `$EDITOR` to modify highlighted `SKILL.md`
     - `Ctrl-X`: Unlink highlighted skill from current project
     - `Ctrl-G` / `Ctrl-D`: Set / Delete groups
     - `Ctrl-N` / `Ctrl-U`: Install / Update
     - `Ctrl-B`: Unbind Git tracking
     - `Enter`: Symlink to project
     - `Alt-C`: Copy physical entity to project

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

