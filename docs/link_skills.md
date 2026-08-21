# link_skills

`link_skills` is a utility tool to link globally-defined AI Agent skills (Skills) selectively into the current project directory using symbolic links.

---

## 📖 Usage & Options

```bash
link_skills [options] [skill_name/group_name...]
```

### Option Descriptions

- **`-h, --help`**
  Show the help menu.
- **`-s, --group-set <group_name> <skill...>`**
  Create or update a skill group.
- **`-r, --group-rm <group_name>`**
  Delete a specified skill group.
- **`-l, --group-list`**
  List all currently defined skill groups.
- **`-v, --view` (or subcommand `view`)**
  View connected skills of the current project with Chinese translation loaded from the translation cache.

---

## 👥 Skill Groups (Grouping)

To simplify management and enable batch-linking, `link_skills` supports **skill groups**. You can combine multiple commonly used or related skills into a group and soft-link all of them with a single command.

Skill groups are stored in JSON format at `~/.local/share/zfl/skills_groups.json`. The framework automatically generates two default groups when run for the first time:
- **`startup` (Minimalist Entrepreneur)**: Contains `validate-idea`, `find-community`, `first-customers`, `marketing-plan`, `pricing`, `processize`, `grow-sustainably`, `minimalist-review`.
- **`dev` (Daily Development Collaboration)**: Contains `prototype`, `improve-codebase-architecture`, `gemini-prompt-optimizer`, `grill-me`, `grill-with-docs`, `handoff`, `nuwa-skill`.

### Group Management Examples

```bash
# Create/Modify group
link_skills --group-set my-triage triage caveman

# Delete group
link_skills --group-rm my-triage

# View current groups
link_skills --group-list
```

---

## 💡 Examples

### 1. Direct Command Mode
```bash
# Link specific skills
link_skills caveman diagnose

# Link an entire group (e.g. all skills in startup group)
link_skills startup
```
This symlinks the corresponding skills to `.agents/skills/` under the current directory.

### 2. Interactive Selection & Group Management Mode (Requires `fzf`)
```bash
link_skills
```
If run without parameters, the tool opens an `fzf` interactive menu where you can link skills and manage groups:
- **View and Select Groups**: Group entries (e.g. `group:startup`) are shown at the top of the menu. You can **press Space in the fzf list to select/deselect them**.
- **Real-time Preview**: When focusing on an entry, the right pane displays the details and description of the skill or group in both English and Chinese.
- **Scroll Preview**: Hover the mouse over the preview pane and scroll the wheel, or press `ctrl-j` (scroll down) / `ctrl-k` (scroll up) to scroll the preview window.
- **Expand Preview Window (`ctrl-v`)**: Press `ctrl-v` to toggle the preview window size between `50%` and `90%` (expand to full text) for easier reading of detailed descriptions.
- **Create/Update Group (`ctrl-g`)**: Press `Space` in the list to select multiple skills (or existing groups), then press `ctrl-g` and input the group name. After saving, the FZF menu refreshes and the new group is immediately displayed.
- **Delete Group (`ctrl-d`)**: Focus on a group entry (e.g. `group:startup`), press `ctrl-d`, and enter `y` to confirm deletion. The menu will automatically refresh.
- **Batch Linking**: Press `Enter` to confirm, and the tool will resolve all selected items, deduplicate, and automatically create symlinks.

---

## ⚙️ How it Works

1. **Destination Directory**: Symlinks are created at `.agents/skills/<skill_name>` under the current working directory. The parent directory is created automatically if it does not exist.
2. **Symlink Synchronization**: The utility maps files using `ln -s`. Any modifications made to a Skill under global `~/.agents/skills/` will automatically sync in real-time within your project, without manual copying.

---

## 🌐 Bilingual Support & Translation Cache

To facilitate local translation and off-line usages, ZFL implements bilingual previews and automatic API translations:

### 1. Dynamic Auto-cleaning
When you delete a Skill folder manually from the workspace, `link_skills` automatically removes it from the index list on next run.

### 2. Bilingual Previews
- **Selection List**: In `fzf`, Skills and Groups are cleanly formatted in perfectly aligned columns (ID, Name, Brief Description) without noisy separator bars.
- **Preview Pane**: The preview panel lists Chinese and English names, descriptions, and **"💡 Usage Scenarios & Guide"** tips.

### 3. Automatic Translation & Cache
When a new English Skill is added:
1. When previewed for the first time in the interactive menu, ZFL **calls a lightweight translation engine** to translate metadata.
2. Once translated, Chinese names and descriptions are cached to **`~/.cache/zsh/skills_zh.json`**.
3. Subsequent requests load directly from the local cache in **offline mode**, preventing network overhead.
4. If translation fails (e.g., due to network drops), it falls back to English description gracefully.
