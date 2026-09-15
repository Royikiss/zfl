"""Unit tests for skill_engine._repo."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from skill_engine._repo import parse_repo_target


def test_parse_repo_target_shorthand():
    res = parse_repo_target("owner/repo")
    assert res is not None
    assert res["owner"] == "owner"
    assert res["repo"] == "repo"
    assert res["repo_url"] == "https://github.com/owner/repo.git"
    assert res["branch"] is None
    assert res["subpath"] == ""
    assert res["cache_name"] == "owner__repo"


def test_parse_repo_target_with_branch_and_tag():
    res_branch = parse_repo_target("owner/repo#dev")
    assert res_branch["branch"] == "dev"

    res_tag = parse_repo_target("owner/repo@v1.2.0")
    assert res_tag["branch"] == "v1.2.0"


def test_parse_repo_target_tree_url():
    url = "https://github.com/anthropics/quickstarts/tree/main/skills/eval-creator"
    res = parse_repo_target(url)
    assert res is not None
    assert res["owner"] == "anthropics"
    assert res["repo"] == "quickstarts"
    assert res["branch"] == "main"
    assert res["subpath"] == "skills/eval-creator"
    assert res["cache_name"] == "anthropics__quickstarts"


def test_parse_repo_target_tree_url_direct_skill_md():
    url = "https://github.com/anthropics/quickstarts/blob/main/skills/eval-creator/SKILL.md"
    res = parse_repo_target(url)
    assert res is not None
    assert res["subpath"] == "skills/eval-creator"


def test_parse_repo_target_ssh():
    res = parse_repo_target("git@github.com:phuryn/pm-skills.git")
    assert res is not None
    assert res["owner"] == "phuryn"
    assert res["repo"] == "pm-skills"
    assert res["cache_name"] == "phuryn__pm-skills"


def test_parse_repo_target_local_dir():
    # Use existing directory
    curr = os.path.dirname(__file__)
    res = parse_repo_target(curr)
    assert res is not None
    assert res["is_local"] is True
    assert res["local_path"] == os.path.abspath(curr)


def test_parse_repo_target_empty():
    assert parse_repo_target("") is None
    assert parse_repo_target("   ") is None
