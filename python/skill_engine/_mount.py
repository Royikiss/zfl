"""Project-level skill mount, link, eject, and sync engine."""

import os
import shutil
from datetime import datetime

from ._store import SKILLS_DIR, atomic_save_json, load_manifest
from ._display import clean_item_id
from ._groups import resolve_group_targets


def get_project_skills_dir(project_root=None):
    """
    Return the absolute path of .agents/skills for the given project root.
    If project_root is None, auto-discovers up to the git repository root.
    """
    if project_root:
        return os.path.join(os.path.abspath(project_root), ".agents", "skills")

    curr = os.path.abspath(os.getcwd())
    while True:
        candidate = os.path.join(curr, ".agents", "skills")
        if os.path.exists(candidate) and os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        if os.path.exists(os.path.join(curr, ".git")):
            break
        curr = parent
    return os.path.join(os.getcwd(), ".agents", "skills")


def get_connected_skills(project_root=None):
    """
    Inspect skills mounted in the project directory.
    Returns a sorted list of dicts with skill details.
    """
    proj_skills_dir = get_project_skills_dir(project_root)
    if not os.path.exists(proj_skills_dir):
        return []

    items = sorted(os.listdir(proj_skills_dir))
    connected = []

    for name in items:
        item_path = os.path.join(proj_skills_dir, name)
        is_link = os.path.islink(item_path)
        real_target = os.path.realpath(item_path) if is_link else item_path
        is_broken = is_link and not os.path.exists(real_target)

        connected.append({
            "name": name,
            "path": item_path,
            "is_link": is_link,
            "mode": "symlink" if is_link else "copy",
            "target_path": real_target,
            "is_broken": is_broken
        })

    return connected


def mount_skills_to_project(target_skills, copy_entity=False, project_root=None):
    """
    Mount (symlink or copy) global skills into project .agents/skills/.
    Automatically resolves group identifiers.
    Returns: {"resolved": list, "success": list, "failed": list}
    """
    resolved = resolve_group_targets(target_skills)
    if not resolved:
        return {"resolved": [], "success": [], "failed": []}

    proj_skills_dir = get_project_skills_dir(project_root)
    os.makedirs(proj_skills_dir, exist_ok=True)

    success_list = []
    failed_list = []

    for skill in resolved:
        src = os.path.join(SKILLS_DIR, skill)
        dest = os.path.join(proj_skills_dir, skill)

        if not os.path.isdir(src):
            failed_list.append({"name": skill, "error": "Global skill does not exist in ~/.agents/skills/"})
            continue

        if os.path.lexists(dest):
            try:
                if os.path.islink(dest) or os.path.isfile(dest):
                    os.unlink(dest)
                elif os.path.isdir(dest):
                    shutil.rmtree(dest)
            except Exception as e:
                failed_list.append({"name": skill, "error": f"Failed to clear existing destination: {e}"})
                continue

        try:
            if copy_entity:
                shutil.copytree(src, dest, symlinks=True)
            else:
                os.symlink(src, dest)
            success_list.append(skill)
        except Exception as e:
            failed_list.append({"name": skill, "error": str(e)})

    return {
        "resolved": resolved,
        "success": success_list,
        "failed": failed_list
    }


def unlink_skills_from_project(target_skills=None, unlink_all=False, project_root=None):
    """
    Safely unlink or remove skills from project directory without touching the global library.
    Returns: {"removed": list, "failed": list, "empty_dir": bool}
    """
    proj_skills_dir = get_project_skills_dir(project_root)
    if not os.path.exists(proj_skills_dir):
        return {"removed": [], "failed": [], "empty_dir": True}

    connected = get_connected_skills(project_root)
    all_names = [c["name"] for c in connected]

    to_remove = []
    if unlink_all:
        to_remove = all_names
    elif target_skills:
        resolved = resolve_group_targets(target_skills)
        to_remove = [s for s in resolved if s in all_names]
    else:
        return {"removed": [], "failed": [], "empty_dir": len(all_names) == 0}

    removed_list = []
    failed_list = []

    for name in to_remove:
        dest_path = os.path.join(proj_skills_dir, name)
        try:
            if os.path.islink(dest_path) or os.path.isfile(dest_path):
                os.unlink(dest_path)
            elif os.path.isdir(dest_path):
                shutil.rmtree(dest_path)
            removed_list.append(name)
        except Exception as e:
            failed_list.append({"name": name, "error": str(e)})

    # Clean up empty parent directories
    empty_dir = False
    try:
        if os.path.exists(proj_skills_dir) and not os.listdir(proj_skills_dir):
            os.rmdir(proj_skills_dir)
            empty_dir = True
            agents_dir = os.path.dirname(proj_skills_dir)
            if os.path.exists(agents_dir) and not os.listdir(agents_dir):
                os.rmdir(agents_dir)
    except Exception:
        pass

    return {
        "removed": removed_list,
        "failed": failed_list,
        "empty_dir": empty_dir
    }


def eject_skills_in_project(target_skills=None, project_root=None):
    """
    Convert symlinked skills in project directory into standalone physical copies.
    Returns: {"ejected": list, "skipped": list, "failed": list}
    """
    proj_skills_dir = get_project_skills_dir(project_root)
    if not os.path.exists(proj_skills_dir):
        return {"ejected": [], "skipped": [], "failed": []}

    connected = get_connected_skills(project_root)
    symlinked_map = {c["name"]: c for c in connected if c["is_link"]}

    to_eject_names = []
    skipped_list = []

    if target_skills:
        resolved = resolve_group_targets(target_skills)
        for s in resolved:
            if s in symlinked_map:
                to_eject_names.append(s)
            else:
                skipped_list.append(s)
    else:
        to_eject_names = list(symlinked_map.keys())

    ejected_list = []
    failed_list = []

    for name in to_eject_names:
        item_path = os.path.join(proj_skills_dir, name)
        real_src = os.path.realpath(item_path)
        if not os.path.exists(real_src):
            failed_list.append({"name": name, "error": f"Symlink target does not exist: {real_src}"})
            continue

        try:
            os.unlink(item_path)
            shutil.copytree(real_src, item_path, symlinks=True)
            ejected_list.append(name)
        except Exception as e:
            failed_list.append({"name": name, "error": str(e)})

    return {
        "ejected": ejected_list,
        "skipped": skipped_list,
        "failed": failed_list
    }


def export_project_manifest(project_root=None):
    """
    Generate and save .skillsrc specification for declarative tracking.
    Returns the generated dict or None on error.
    """
    root = os.path.abspath(project_root or os.getcwd())
    connected = get_connected_skills(root)
    if not connected:
        return None

    manifest = load_manifest()
    skills_map = {}

    for item in connected:
        name = item["name"]
        meta = manifest.get(name, {})
        skills_map[name] = {
            "mode": item["mode"],
            "source": meta.get("repo_url") or "local",
            "branch": meta.get("branch") or "HEAD",
            "commit": meta.get("commit_hash") or "unknown",
            "subpath": meta.get("subpath") or ""
        }

    rc_data = {
        "version": 1,
        "exported_at": datetime.now().isoformat(),
        "skills": skills_map
    }

    rc_path = os.path.join(root, ".skillsrc")
    if atomic_save_json(rc_path, rc_data):
        return rc_data
    return None


def read_project_manifest(project_root=None):
    """
    Find and load .skillsrc or .skillsrc.json from project root.
    Returns dict or None if not found.
    """
    root = os.path.abspath(project_root or os.getcwd())
    for fname in (".skillsrc", ".skillsrc.json"):
        path = os.path.join(root, fname)
        if os.path.exists(path):
            import json
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
    return None
