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
   - Real-time previews, bilingual descriptions, and hotkeys for group management (`Ctrl-G`), updating (`Ctrl-U`), installing (`Ctrl-I`), and deleting (`Ctrl-D`).

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

### 3. Skill Groups Management (`-s`, `-r`, `-l`)
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

### 4. Link to Project
```bash
# Link specific skills
mskill caveman diagnose

# Link entire group
mskill startup

# Interactive selection via FZF
mskill
```

### 5. Backward Compatibility
The command `link_skills` is preserved as an alias for `mskill` with full parameter compatibility.
