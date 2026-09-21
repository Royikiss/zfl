"""Unit tests for skill_engine._mount."""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from skill_engine import (
    get_project_skills_dir, get_connected_skills, mount_skills_to_project,
    unlink_skills_from_project, eject_skills_in_project,
    export_project_manifest, read_project_manifest
)
import skill_engine._mount as mount_mod
import skill_engine._store as store_mod


@pytest.fixture
def mock_env(monkeypatch, tmp_path):
    """Set up global skills directory and project root."""
    global_dir = tmp_path / "global_skills"
    global_dir.mkdir()
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    # Create dummy global skills
    s1 = global_dir / "skill-alpha"
    s1.mkdir()
    (s1 / "SKILL.md").write_text("# Skill Alpha\nDescription of Alpha")

    s2 = global_dir / "skill-beta"
    s2.mkdir()
    (s2 / "SKILL.md").write_text("# Skill Beta\nDescription of Beta")

    monkeypatch.setattr(mount_mod, "SKILLS_DIR", str(global_dir))
    monkeypatch.setattr(store_mod, "SKILLS_DIR", str(global_dir))

    return {
        "global_dir": str(global_dir),
        "project_dir": str(project_dir)
    }


def test_get_project_skills_dir(mock_env):
    proj = mock_env["project_dir"]
    expected = os.path.join(proj, ".agents", "skills")
    assert get_project_skills_dir(proj) == expected


def test_mount_symlinks(mock_env):
    proj = mock_env["project_dir"]
    res = mount_skills_to_project(["skill-alpha"], copy_entity=False, project_root=proj)

    assert res["resolved"] == ["skill-alpha"]
    assert res["success"] == ["skill-alpha"]
    assert res["failed"] == []

    # Check file system
    conn = get_connected_skills(proj)
    assert len(conn) == 1
    assert conn[0]["name"] == "skill-alpha"
    assert conn[0]["is_link"] is True
    assert conn[0]["mode"] == "symlink"
    assert conn[0]["is_broken"] is False


def test_mount_copy(mock_env):
    proj = mock_env["project_dir"]
    res = mount_skills_to_project(["skill-beta"], copy_entity=True, project_root=proj)

    assert res["success"] == ["skill-beta"]
    conn = get_connected_skills(proj)
    assert len(conn) == 1
    assert conn[0]["name"] == "skill-beta"
    assert conn[0]["is_link"] is False
    assert conn[0]["mode"] == "copy"


def test_eject_skills(mock_env):
    proj = mock_env["project_dir"]
    # First mount as symlink
    mount_skills_to_project(["skill-alpha"], copy_entity=False, project_root=proj)
    conn_before = get_connected_skills(proj)
    assert conn_before[0]["is_link"] is True

    # Eject symlink to physical copy
    res = eject_skills_in_project(["skill-alpha"], project_root=proj)
    assert "skill-alpha" in res["ejected"]
    assert res["failed"] == []

    conn_after = get_connected_skills(proj)
    assert len(conn_after) == 1
    assert conn_after[0]["name"] == "skill-alpha"
    assert conn_after[0]["is_link"] is False
    assert conn_after[0]["mode"] == "copy"


def test_unlink_skills(mock_env):
    proj = mock_env["project_dir"]
    mount_skills_to_project(["skill-alpha", "skill-beta"], copy_entity=False, project_root=proj)
    assert len(get_connected_skills(proj)) == 2

    res = unlink_skills_from_project(["skill-alpha"], project_root=proj)
    assert res["removed"] == ["skill-alpha"]
    assert res["failed"] == []

    conn_remaining = get_connected_skills(proj)
    assert len(conn_remaining) == 1
    assert conn_remaining[0]["name"] == "skill-beta"


def test_manifest_export_and_read(mock_env):
    proj = mock_env["project_dir"]
    mount_skills_to_project(["skill-alpha"], copy_entity=False, project_root=proj)
    mount_skills_to_project(["skill-beta"], copy_entity=True, project_root=proj)

    res = export_project_manifest(project_root=proj)
    assert res is not None
    rc_path = os.path.join(proj, ".skillsrc")
    assert os.path.exists(rc_path)

    data = read_project_manifest(project_root=proj)
    assert data is not None
    assert "skills" in data
    assert "skill-alpha" in data["skills"]
    assert data["skills"]["skill-alpha"]["mode"] == "symlink"
    assert "skill-beta" in data["skills"]
    assert data["skills"]["skill-beta"]["mode"] == "copy"
