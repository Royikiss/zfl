"""Skill group management and resolution engine."""

import os
from ._store import load_groups, save_groups
from ._display import clean_item_id, IS_ZH


def get_all_groups():
    """Return all defined groups as a sorted dictionary."""
    return load_groups()


def get_group(gid):
    """Get metadata and skill list for a specific group id, or None if not found."""
    groups = load_groups()
    clean_id = clean_item_id(gid).removeprefix("group:")
    return groups.get(clean_id)


def save_group_definition(gname, skills, is_ordered=False, display_name=None):
    """
    Create or update a skill group definition.
    Returns True on success, False on failure.
    """
    clean_gname = clean_item_id(gname).removeprefix("group:")
    if not clean_gname:
        return False

    clean_skills = []
    for s in skills:
        cs = clean_item_id(s)
        if cs and cs not in clean_skills:
            clean_skills.append(cs)

    if not clean_skills:
        return False

    groups = load_groups()
    title = display_name
    if not title:
        if clean_gname in groups and isinstance(groups[clean_gname], dict):
            title = groups[clean_gname].get("name", clean_gname)
        else:
            title = clean_gname

    groups[clean_gname] = {
        "name": title,
        "ordered": bool(is_ordered),
        "skills": clean_skills
    }
    return save_groups(groups)


def delete_group(gname):
    """
    Delete a skill group by name.
    Returns True if deleted, False if group did not exist or save failed.
    """
    clean_gname = clean_item_id(gname).removeprefix("group:")
    groups = load_groups()
    if clean_gname in groups:
        del groups[clean_gname]
        return save_groups(groups)
    return False


def resolve_group_targets(target_names):
    """
    Expand a mixed list of group names and individual skill names into a flat,
    deduplicated, order-preserved list of concrete skill names.
    Supports 'group:xxx' prefix, plain group names, and raw skill names.
    """
    if not target_names:
        return []

    groups = load_groups()
    resolved = []

    for raw in target_names:
        if not raw or raw.startswith("-"):
            continue
        item = clean_item_id(raw)
        if not item or item.startswith("-"):
            continue

        gkey = item[6:] if item.startswith("group:") else item
        if gkey in groups:
            ginfo = groups[gkey]
            skills = ginfo.get("skills", []) if isinstance(ginfo, dict) else ginfo
            for s in skills:
                cs = clean_item_id(s)
                if cs and cs not in resolved:
                    resolved.append(cs)
        else:
            if item not in resolved:
                resolved.append(item)

    return resolved


def get_groups_completion_data(is_zh=None):
    """
    Return formatted completion lines for Zsh tab completion:
    e.g. ['group_id:Display Name (N skills)', ...]
    """
    if is_zh is None:
        is_zh = IS_ZH
    groups = load_groups()
    results = []
    for gid in sorted(groups.keys()):
        info = groups[gid]
        if isinstance(info, dict):
            name = info.get("name") or gid
            count = len(info.get("skills", []))
        else:
            name = gid
            count = len(info) if isinstance(info, list) else 0

        count_str = f"{count} 个技能" if is_zh else f"{count} skills"
        clean_name = name.replace(":", "\\:").strip()
        if clean_name and clean_name != gid:
            results.append(f"{gid}:{clean_name} ({count_str})")
        else:
            results.append(f"{gid}:({count_str})")
    return results


def _extract_group_skills(ginfo):
    if isinstance(ginfo, dict):
        return list(ginfo.get("skills", []))
    elif isinstance(ginfo, list):
        return list(ginfo)
    return []


def find_groups_for_skills(skill_names):
    """
    Find which groups contain any of the given skill names.
    Returns dict of {group_id: [matching_skill_names]}.
    """
    if not skill_names:
        return {}
    clean_targets = {clean_item_id(s) for s in skill_names if clean_item_id(s)}
    if not clean_targets:
        return {}

    groups = load_groups()
    result = {}
    for gname, ginfo in groups.items():
        skills = _extract_group_skills(ginfo)
        matched = [s for s in skills if s in clean_targets]
        if matched:
            result[gname] = matched
    return result


def find_groups_for_skill(skill_name):
    """
    Find which groups contain a specific skill.
    Returns list of group names.
    """
    cs = clean_item_id(skill_name)
    if not cs:
        return []
    res = find_groups_for_skills([cs])
    return list(res.keys())


def add_skills_to_group(gname, new_skills):
    """
    Add one or more skills to an existing group.
    Preserves existing order, deduplicates, and avoids duplicate additions.
    Returns True on success/change, False otherwise.
    """
    clean_gname = clean_item_id(gname).removeprefix("group:")
    groups = load_groups()
    if clean_gname not in groups:
        return False

    ginfo = groups[clean_gname]
    current_skills = _extract_group_skills(ginfo)
    added = False
    for s in new_skills:
        cs = clean_item_id(s)
        if cs and cs not in current_skills:
            current_skills.append(cs)
            added = True

    if not added:
        return False

    if isinstance(ginfo, dict):
        groups[clean_gname]["skills"] = current_skills
    else:
        groups[clean_gname] = current_skills
    return save_groups(groups)


def remove_skill_from_group(gname, skill_to_remove):
    """
    Remove a skill from an existing group.
    Returns True if skill was present and group was saved, False otherwise.
    """
    clean_gname = clean_item_id(gname).removeprefix("group:")
    cs = clean_item_id(skill_to_remove)
    groups = load_groups()
    if clean_gname not in groups or not cs:
        return False

    ginfo = groups[clean_gname]
    current_skills = _extract_group_skills(ginfo)
    if cs not in current_skills:
        return False

    current_skills = [s for s in current_skills if s != cs]
    if isinstance(ginfo, dict):
        groups[clean_gname]["skills"] = current_skills
    else:
        groups[clean_gname] = current_skills
    return save_groups(groups)


def remove_skill_from_all_groups(skill_to_remove):
    """
    Remove a skill from all groups where it is present.
    Returns list of group names from which the skill was removed.
    """
    cs = clean_item_id(skill_to_remove)
    if not cs:
        return []
    groups = load_groups()
    affected = []
    for gname, ginfo in groups.items():
        skills = _extract_group_skills(ginfo)
        if cs in skills:
            new_skills = [s for s in skills if s != cs]
            if isinstance(ginfo, dict):
                groups[gname]["skills"] = new_skills
            else:
                groups[gname] = new_skills
            affected.append(gname)

    if affected:
        save_groups(groups)
    return affected

