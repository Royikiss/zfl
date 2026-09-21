"""ZFL Skill Engine — unified skill lifecycle management."""

from ._display import (
    strip_ansi, clean_item_id, get_display_width, pad_display,
    truncate_display, c_print, circled_num, IS_ZH, LANG
)
from ._store import (
    SKILLS_DIR, DATA_DIR, SOURCES_DIR, MANIFEST_FILE, GROUPS_FILE, TRANSLATIONS_FILE,
    get_zfl_data_dir, atomic_save_json, load_manifest, save_manifest,
    load_groups, save_groups, safe_input
)
from ._frontmatter import parse_yaml_frontmatter
from ._translations import DEFAULT_TRANSLATIONS, DEFAULT_GROUPS, load_user_translations
from ._repo import (
    parse_repo_target, clone_or_fetch_repo,
    get_repo_head_commit, get_repo_remote_commit
)
from ._groups import (
    get_all_groups, get_group, save_group_definition, delete_group,
    resolve_group_targets, get_groups_completion_data,
    find_groups_for_skill, find_groups_for_skills,
    add_skills_to_group, remove_skill_from_group, remove_skill_from_all_groups
)
from ._mount import (
    get_project_skills_dir, get_connected_skills,
    mount_skills_to_project, unlink_skills_from_project,
    eject_skills_in_project, export_project_manifest, read_project_manifest
)

__all__ = [
    "strip_ansi", "clean_item_id", "get_display_width", "pad_display",
    "truncate_display", "c_print", "circled_num", "IS_ZH", "LANG",
    "SKILLS_DIR", "DATA_DIR", "SOURCES_DIR", "MANIFEST_FILE", "GROUPS_FILE", "TRANSLATIONS_FILE",
    "get_zfl_data_dir", "atomic_save_json", "load_manifest", "save_manifest",
    "load_groups", "save_groups", "safe_input",
    "parse_yaml_frontmatter",
    "DEFAULT_TRANSLATIONS", "DEFAULT_GROUPS", "load_user_translations",
    "parse_repo_target", "clone_or_fetch_repo",
    "get_repo_head_commit", "get_repo_remote_commit",
    "get_all_groups", "get_group", "save_group_definition", "delete_group",
    "resolve_group_targets", "get_groups_completion_data",
    "find_groups_for_skill", "find_groups_for_skills",
    "add_skills_to_group", "remove_skill_from_group", "remove_skill_from_all_groups",
    "get_project_skills_dir", "get_connected_skills",
    "mount_skills_to_project", "unlink_skills_from_project",
    "eject_skills_in_project", "export_project_manifest", "read_project_manifest"
]
