"""Unit tests for skill_engine._groups."""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from skill_engine import (
    get_all_groups, get_group, save_group_definition, delete_group,
    resolve_group_targets, get_groups_completion_data,
    find_groups_for_skill, find_groups_for_skills,
    add_skills_to_group, remove_skill_from_group, remove_skill_from_all_groups
)
import skill_engine._store as store_mod


@pytest.fixture(autouse=True)
def isolated_groups_file(monkeypatch, tmp_path):
    """Isolate GROUPS_FILE for testing to prevent mutating user data."""
    test_groups_file = str(tmp_path / "test_skills_groups.json")
    monkeypatch.setattr(store_mod, "GROUPS_FILE", test_groups_file)
    # Re-initialize default
    init_data = {
        "dev": {
            "name": "日常开发协作",
            "ordered": False,
            "skills": ["git-commit", "code-review"]
        },
        "workflow": {
            "name": "全流程编排",
            "ordered": True,
            "skills": ["planner", "coder", "tester"]
        }
    }
    store_mod.atomic_save_json(test_groups_file, init_data)
    return test_groups_file


def test_get_all_groups():
    groups = get_all_groups()
    assert isinstance(groups, dict)
    assert "dev" in groups
    assert "workflow" in groups
    assert groups["dev"]["skills"] == ["git-commit", "code-review"]


def test_get_group():
    grp = get_group("dev")
    assert grp is not None
    assert grp["name"] == "日常开发协作"

    # With group: prefix
    grp_pref = get_group("group:workflow")
    assert grp_pref is not None
    assert grp_pref["ordered"] is True

    # Nonexistent
    assert get_group("nonexistent") is None


def test_save_group_definition_new_and_update():
    # Save new group
    ok = save_group_definition("qa", ["pytest", "coverage", "pytest"], is_ordered=True, display_name="质量保证")
    assert ok is True

    grp = get_group("qa")
    assert grp is not None
    assert grp["name"] == "质量保证"
    assert grp["ordered"] is True
    # Deduplicated skills
    assert grp["skills"] == ["pytest", "coverage"]

    # Update existing group
    ok_up = save_group_definition("group:qa", ["pytest", "lint"], is_ordered=False)
    assert ok_up is True
    updated = get_group("qa")
    assert updated["skills"] == ["pytest", "lint"]
    assert updated["ordered"] is False
    assert updated["name"] == "质量保证"  # Preserved display name


def test_save_group_definition_invalid():
    assert save_group_definition("", ["skill1"]) is False
    assert save_group_definition("empty_skills", []) is False


def test_delete_group():
    assert delete_group("dev") is True
    assert get_group("dev") is None

    # Delete with group: prefix
    assert delete_group("group:workflow") is True
    assert get_group("workflow") is None

    # Delete non-existent
    assert delete_group("not_exist") is False


def test_resolve_group_targets():
    # Mixed list of skills, groups, and options
    inputs = ["--flag", "git-commit", "group:dev", "workflow", "git-commit", "extra-skill"]
    resolved = resolve_group_targets(inputs)

    # Expected order: git-commit, code-review (from dev), planner, coder, tester (from workflow), extra-skill
    assert resolved == ["git-commit", "code-review", "planner", "coder", "tester", "extra-skill"]

    # Empty inputs
    assert resolve_group_targets([]) == []
    assert resolve_group_targets(None) == []


def test_get_groups_completion_data():
    comp_zh = get_groups_completion_data(is_zh=True)
    assert any(line.startswith("dev:日常开发协作 (2 个技能)") for line in comp_zh)
    assert any(line.startswith("workflow:全流程编排 (3 个技能)") for line in comp_zh)

    comp_en = get_groups_completion_data(is_zh=False)
    assert any(line.startswith("dev:日常开发协作 (2 skills)") for line in comp_en)


def test_find_groups_for_skill_and_skills():
    # Initial data has:
    # dev: ["git-commit", "code-review"]
    # workflow: ["planner", "coder", "tester"]
    assert find_groups_for_skill("git-commit") == ["dev"]
    assert find_groups_for_skill("planner") == ["workflow"]
    assert find_groups_for_skill("nonexistent") == []
    assert find_groups_for_skill("") == []

    # find_groups_for_skills
    res = find_groups_for_skills(["git-commit", "coder"])
    assert "dev" in res
    assert res["dev"] == ["git-commit"]
    assert "workflow" in res
    assert res["workflow"] == ["coder"]

    assert find_groups_for_skills([]) == {}
    assert find_groups_for_skills(["none1", "none2"]) == {}


def test_add_skills_to_group():
    # Add new skill to existing group
    ok = add_skills_to_group("dev", ["git-diff"])
    assert ok is True
    grp = get_group("dev")
    assert grp["skills"] == ["git-commit", "code-review", "git-diff"]

    # Duplicate skill: should not add again and returns False
    ok_dup = add_skills_to_group("dev", ["git-commit", "code-review"])
    assert ok_dup is False
    assert get_group("dev")["skills"] == ["git-commit", "code-review", "git-diff"]

    # Multiple skills with one new, one duplicate
    ok_multi = add_skills_to_group("dev", ["git-commit", "git-log"])
    assert ok_multi is True
    assert get_group("dev")["skills"] == ["git-commit", "code-review", "git-diff", "git-log"]

    # With group: prefix
    ok_pref = add_skills_to_group("group:workflow", ["deployer"])
    assert ok_pref is True
    assert "deployer" in get_group("workflow")["skills"]

    # Non-existent group
    assert add_skills_to_group("not_exist", ["foo"]) is False


def test_remove_skill_from_group():
    # Remove existing skill
    ok = remove_skill_from_group("dev", "code-review")
    assert ok is True
    grp = get_group("dev")
    assert grp["skills"] == ["git-commit"]

    # Removing already removed / non-existent skill returns False
    assert remove_skill_from_group("dev", "code-review") is False
    assert remove_skill_from_group("dev", "nonexistent") is False
    assert remove_skill_from_group("not_exist", "git-commit") is False

    # Remove with group: prefix
    assert remove_skill_from_group("group:workflow", "coder") is True
    assert get_group("workflow")["skills"] == ["planner", "tester"]


def test_remove_skill_from_all_groups():
    # Add git-commit to workflow as well
    add_skills_to_group("workflow", ["git-commit"])
    assert "git-commit" in get_group("dev")["skills"]
    assert "git-commit" in get_group("workflow")["skills"]

    affected = remove_skill_from_all_groups("git-commit")
    assert set(affected) == {"dev", "workflow"}
    assert "git-commit" not in get_group("dev")["skills"]
    assert "git-commit" not in get_group("workflow")["skills"]

    # Non-existent skill
    assert remove_skill_from_all_groups("nonexistent") == []

