"""Unit tests for manage_skills unified dispatch facade."""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

import manage_skills


def test_facade_list_groups_completion_routing():
    with patch("sys.argv", ["manage_skills.py", "--list-groups-completion"]), \
         patch("resolve_skills.cmd_list_groups_completion", return_value=0) as mock_fn:
        ret = manage_skills.main()
        assert ret == 0
        mock_fn.assert_called_once()


def test_facade_group_list_routing():
    with patch("sys.argv", ["manage_skills.py", "--group-list"]), \
         patch("resolve_skills.cmd_list_groups_detailed", return_value=0) as mock_fn:
        ret = manage_skills.main()
        assert ret == 0
        mock_fn.assert_called_once()


def test_facade_group_set_routing():
    with patch("sys.argv", ["manage_skills.py", "--group-set", "my-grp", "skill-a", "skill-b"]), \
         patch("resolve_skills.cmd_set_group", return_value=0) as mock_fn:
        ret = manage_skills.main()
        assert ret == 0
        mock_fn.assert_called_once_with(["my-grp", "skill-a", "skill-b"])


def test_facade_group_rm_routing():
    with patch("sys.argv", ["manage_skills.py", "--group-rm", "my-grp"]), \
         patch("resolve_skills.cmd_rm_group", return_value=0) as mock_fn:
        ret = manage_skills.main()
        assert ret == 0
        mock_fn.assert_called_once_with("my-grp")


def test_facade_view_routing():
    with patch("sys.argv", ["manage_skills.py", "--view"]), \
         patch("resolve_skills.cmd_view_connected", return_value=0) as mock_fn:
        ret = manage_skills.main()
        assert ret == 0
        mock_fn.assert_called_once()


def test_facade_translate_all_routing():
    with patch("sys.argv", ["manage_skills.py", "--translate-all"]), \
         patch("preview_skill.cmd_translate_all", return_value=0) as mock_fn:
        ret = manage_skills.main()
        assert ret == 0
        mock_fn.assert_called_once()


def test_facade_interactive_translate_routing():
    with patch("sys.argv", ["manage_skills.py", "--interactive-translate", "test-skill"]), \
         patch("preview_skill.cmd_force_translate", return_value=0) as mock_fn:
        ret = manage_skills.main()
        assert ret == 0
        mock_fn.assert_called_once_with("test-skill")


def test_facade_positional_skills_mount_routing():
    with patch("sys.argv", ["manage_skills.py", "skill-a", "skill-b"]), \
         patch("manage_skills.is_in_home_dir", return_value=False), \
         patch("manage_skills.mount_project_skills", return_value=0) as mock_fn:
        ret = manage_skills.main()
        assert ret == 0
        mock_fn.assert_called_once_with(target_skills=["skill-a", "skill-b"], copy_entity=False)


def test_facade_copy_flag_skills_mount_routing():
    with patch("sys.argv", ["manage_skills.py", "-c", "skill-a", "skill-b"]), \
         patch("manage_skills.is_in_home_dir", return_value=False), \
         patch("manage_skills.mount_project_skills", return_value=0) as mock_fn:
        ret = manage_skills.main()
        assert ret == 0
        mock_fn.assert_called_once_with(target_skills=["skill-a", "skill-b"], copy_entity=True)


def test_facade_smart_repo_auto_detect_routing():
    with patch("sys.argv", ["manage_skills.py", "anthropics/quickstarts", "skill-1"]), \
         patch("manage_skills.install_skills_workflow", return_value=0) as mock_fn:
        ret = manage_skills.main()
        assert ret == 0
        mock_fn.assert_called_once_with("anthropics/quickstarts", specific_skills=["skill-1"])


def test_facade_home_directory_protection():
    with patch("sys.argv", ["manage_skills.py", "skill-a"]), \
         patch("manage_skills.is_in_home_dir", return_value=True), \
         patch("manage_skills.mount_project_skills") as mock_mount:
        ret = manage_skills.main()
        assert ret == 1
        mock_mount.assert_not_called()

    with patch("sys.argv", ["manage_skills.py", "--eject"]), \
         patch("manage_skills.is_in_home_dir", return_value=True), \
         patch("manage_skills.eject_project_skills") as mock_eject:
        ret = manage_skills.main()
        assert ret == 1
        mock_eject.assert_not_called()


def test_facade_unknown_option_error():
    with patch("sys.argv", ["manage_skills.py", "--some-bogus-option"]):
        ret = manage_skills.main()
        assert ret == 2


def test_uninstall_skill_with_group_cleanup(tmp_path, monkeypatch):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_a_dir = skills_dir / "skill-a"
    skill_a_dir.mkdir()
    (skill_a_dir / "SKILL.md").write_text("# Skill A")

    test_groups_file = str(tmp_path / "groups.json")
    test_manifest_file = str(tmp_path / "manifest.json")

    import skill_engine._store as store_mod
    monkeypatch.setattr(store_mod, "GROUPS_FILE", test_groups_file)
    monkeypatch.setattr(store_mod, "MANIFEST_FILE", test_manifest_file)
    monkeypatch.setattr(manage_skills, "SKILLS_DIR", str(skills_dir))
    monkeypatch.setattr(manage_skills, "GROUPS_FILE", test_groups_file)
    monkeypatch.setattr(manage_skills, "MANIFEST_FILE", test_manifest_file)

    init_groups = {
        "dev": {
            "name": "Dev",
            "ordered": False,
            "skills": ["skill-a", "skill-b"]
        }
    }
    store_mod.save_groups(init_groups)
    store_mod.save_manifest({"skill-a": {"repo_url": "dummy"}})

    # Test user says 'y' to remove from group
    with patch("sys.stdin.isatty", return_value=True), \
         patch("manage_skills.safe_input", return_value="y"):
        ret = manage_skills.uninstall_skill_workflow("skill-a")
        assert ret == 0
        assert not skill_a_dir.exists()
        updated_groups = store_mod.load_groups()
        assert "skill-a" not in updated_groups["dev"]["skills"]
        assert updated_groups["dev"]["skills"] == ["skill-b"]


def test_prompt_install_new_skills_auto_join_group(tmp_path, monkeypatch):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    test_groups_file = str(tmp_path / "groups.json")
    test_manifest_file = str(tmp_path / "manifest.json")

    import skill_engine._store as store_mod
    monkeypatch.setattr(store_mod, "GROUPS_FILE", test_groups_file)
    monkeypatch.setattr(store_mod, "MANIFEST_FILE", test_manifest_file)
    monkeypatch.setattr(manage_skills, "SKILLS_DIR", str(skills_dir))
    monkeypatch.setattr(manage_skills, "GROUPS_FILE", test_groups_file)
    monkeypatch.setattr(manage_skills, "MANIFEST_FILE", test_manifest_file)

    init_groups = {
        "my-team": {
            "name": "My Team",
            "ordered": False,
            "skills": ["old-skill"]
        }
    }
    store_mod.save_groups(init_groups)

    # Prepare dummy new skill bundle
    src_skill_dir = tmp_path / "src_skill"
    src_skill_dir.mkdir()
    (src_skill_dir / "SKILL.md").write_text("# New Skill")

    newly_available = {
        "owner__repo": {
            "meta": {"repo_url": "https://github.com/owner/repo", "owner": "owner", "repo": "repo"},
            "cache_dir": str(tmp_path),
            "latest_commit": "abcdef1234567890",
            "current_skills": ["old-skill"],
            "skills": [{
                "name": "new-skill",
                "dir_path": str(src_skill_dir),
                "rel_subpath": "new-skill",
                "description": "A new skill",
                "file_count": 1
            }]
        }
    }

    # Simulate user entering 'y' to install, and 'y' to join group 'my-team'
    inputs = iter(["y", "y"])
    with patch("sys.stdin.isatty", return_value=True), \
         patch("manage_skills.safe_input", side_effect=lambda prompt: next(inputs)):
        manage_skills.prompt_install_new_skills(newly_available)

    # Verify skill installed
    dest_path = skills_dir / "new-skill"
    assert dest_path.exists()
    assert (dest_path / "SKILL.md").exists()

    # Verify skill added to group
    updated_groups = store_mod.load_groups()
    assert "new-skill" in updated_groups["my-team"]["skills"]
    assert updated_groups["my-team"]["skills"] == ["old-skill", "new-skill"]


def test_update_skills_workflow_deprecated_skill_group_removal(tmp_path, monkeypatch):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_a_dir = skills_dir / "skill-a"
    skill_a_dir.mkdir()
    (skill_a_dir / "SKILL.md").write_text("# Skill A")

    test_groups_file = str(tmp_path / "groups.json")
    test_manifest_file = str(tmp_path / "manifest.json")

    import skill_engine._store as store_mod
    monkeypatch.setattr(store_mod, "GROUPS_FILE", test_groups_file)
    monkeypatch.setattr(store_mod, "MANIFEST_FILE", test_manifest_file)
    monkeypatch.setattr(manage_skills, "SKILLS_DIR", str(skills_dir))
    monkeypatch.setattr(manage_skills, "GROUPS_FILE", test_groups_file)
    monkeypatch.setattr(manage_skills, "MANIFEST_FILE", test_manifest_file)

    init_groups = {
        "dev": {
            "name": "Dev",
            "ordered": False,
            "skills": ["skill-a", "skill-b"]
        }
    }
    store_mod.save_groups(init_groups)
    store_mod.save_manifest({
        "skill-a": {
            "repo_url": "https://github.com/owner/repo",
            "owner": "owner",
            "repo": "repo",
            "cache_name": "owner__repo",
            "subpath": "skills/skill-a",
            "commit_hash": "1111111"
        }
    })

    empty_cache_dir = tmp_path / "cache_empty"
    empty_cache_dir.mkdir()

    with patch("manage_skills.clone_or_fetch_repo", return_value=str(empty_cache_dir)), \
         patch("manage_skills.get_repo_head_commit", return_value="2222222"), \
         patch("manage_skills.scan_skills_in_dir", return_value=[]), \
         patch("sys.stdin.isatty", return_value=True), \
         patch("manage_skills.safe_input", return_value="y"):
        ret = manage_skills.update_skills_workflow(target_skills=["skill-a"])
        assert ret == 0
        updated_groups = store_mod.load_groups()
        assert "skill-a" not in updated_groups["dev"]["skills"]
        assert updated_groups["dev"]["skills"] == ["skill-b"]


def test_facade_group_add_and_remove_routing(tmp_path, monkeypatch):
    test_groups_file = str(tmp_path / "groups.json")
    import skill_engine._store as store_mod
    monkeypatch.setattr(store_mod, "GROUPS_FILE", test_groups_file)
    init_groups = {
        "dev": {
            "name": "Dev",
            "ordered": False,
            "skills": ["skill-a"]
        }
    }
    store_mod.save_groups(init_groups)

    # CLI --group-add dev skill-b
    with patch("sys.argv", ["manage_skills.py", "--group-add", "dev", "skill-b"]):
        ret = manage_skills.main()
        assert ret == 0
        groups = store_mod.load_groups()
        assert groups["dev"]["skills"] == ["skill-a", "skill-b"]

    # CLI --group-remove dev skill-a
    with patch("sys.argv", ["manage_skills.py", "--group-remove", "dev", "skill-a"]):
        ret = manage_skills.main()
        assert ret == 0
        groups = store_mod.load_groups()
        assert groups["dev"]["skills"] == ["skill-b"]


def test_interactive_rm_on_skill_node(tmp_path, monkeypatch):
    test_groups_file = str(tmp_path / "groups.json")
    import skill_engine._store as store_mod
    monkeypatch.setattr(store_mod, "GROUPS_FILE", test_groups_file)
    init_groups = {
        "dev": {
            "name": "Dev",
            "ordered": False,
            "skills": ["skill-a", "skill-b"]
        }
    }
    store_mod.save_groups(init_groups)

    import resolve_skills
    # Focusing on tree-formatted child node '  ├── skill-a'
    with patch("resolve_skills.safe_input", side_effect=["y", ""]):
        ret = resolve_skills.cmd_interactive_rm(["  ├── skill-a"])
        assert ret == 0
        groups = store_mod.load_groups()
        assert groups["dev"]["skills"] == ["skill-b"]


def test_interactive_set_add_and_move_to_existing_group(tmp_path, monkeypatch):
    test_groups_file = str(tmp_path / "groups.json")
    import skill_engine._store as store_mod
    monkeypatch.setattr(store_mod, "GROUPS_FILE", test_groups_file)
    init_groups = {
        "dev": {
            "name": "Dev",
            "ordered": False,
            "skills": ["skill-a"]
        },
        "ops": {
            "name": "Ops",
            "ordered": False,
            "skills": ["skill-b"]
        }
    }
    store_mod.save_groups(init_groups)

    import resolve_skills

    # 1. Test Option 1 (Add to existing group 'dev')
    with patch("resolve_skills.safe_input", side_effect=["1", "1", ""]):
        resolve_skills.interactive_set(["skill-c"])
        groups = store_mod.load_groups()
        assert groups["dev"]["skills"] == ["skill-a", "skill-c"]

    # 2. Test Option 2 (Move skill-c from dev to ops)
    with patch("resolve_skills.safe_input", side_effect=["2", "ops", ""]):
        resolve_skills.interactive_set(["skill-c"])
        groups = store_mod.load_groups()
        assert "skill-c" not in groups["dev"]["skills"]
        assert "skill-c" in groups["ops"]["skills"]



