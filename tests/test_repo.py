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


def test_scan_skills_in_dir(tmp_path):
    from skill_engine._repo import scan_skills_in_dir

    skill_dir = tmp_path / "skills" / "awesome-skill"
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("---\nname: awesome-skill\ndescription: An awesome test skill\n---\n# Content\n", encoding="utf-8")

    discovered = scan_skills_in_dir(str(tmp_path))
    assert len(discovered) == 1
    assert discovered[0]["name"] == "awesome-skill"
    assert discovered[0]["description"] == "An awesome test skill"
    assert discovered[0]["rel_subpath"] == "skills/awesome-skill"


def test_reconcile_skills_manifest_from_sources(tmp_path):
    import subprocess
    from skill_engine._repo import reconcile_skills_manifest

    skills_dir = tmp_path / "global_skills"
    skills_dir.mkdir()
    local_s = skills_dir / "my-skill"
    local_s.mkdir()
    (local_s / "SKILL.md").write_text("---\nname: my-skill\ndescription: Local copy\n---\n", encoding="utf-8")

    sources_dir = tmp_path / "sources"
    repo_dir = sources_dir / "test__repo"
    repo_skill = repo_dir / "skills" / "my-skill"
    repo_skill.mkdir(parents=True)
    (repo_skill / "SKILL.md").write_text("---\nname: my-skill\ndescription: Source copy\n---\n", encoding="utf-8")

    # Initialize git repo in repo_dir
    subprocess.run(["git", "-C", str(repo_dir), "init"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(repo_dir), "remote", "add", "origin", "https://github.com/test/repo.git"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    manifest = {}
    reconciled = reconcile_skills_manifest(
        skills_dir=str(skills_dir),
        sources_dir=str(sources_dir),
        manifest=manifest,
        auto_save=False
    )
    assert "my-skill" in reconciled
    assert reconciled["my-skill"]["repo_url"] == "https://github.com/test/repo.git"
    assert reconciled["my-skill"]["subpath"] == "skills/my-skill"


def test_reconcile_skills_manifest_from_local_git(tmp_path):
    import subprocess
    from skill_engine._repo import reconcile_skills_manifest

    skills_dir = tmp_path / "global_skills"
    skills_dir.mkdir()
    git_skill = skills_dir / "git-skill"
    git_skill.mkdir()
    (git_skill / "SKILL.md").write_text("---\nname: git-skill\ndescription: Git cloned skill\n---\n", encoding="utf-8")

    # Initialize git inside git_skill itself
    subprocess.run(["git", "-C", str(git_skill), "init"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(git_skill), "remote", "add", "origin", "https://github.com/creator/git-skill.git"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    manifest = {}
    reconciled = reconcile_skills_manifest(
        skills_dir=str(skills_dir),
        sources_dir=str(tmp_path / "sources"),
        manifest=manifest,
        auto_save=False
    )
    assert "git-skill" in reconciled
    assert reconciled["git-skill"]["repo_url"] == "https://github.com/creator/git-skill.git"

