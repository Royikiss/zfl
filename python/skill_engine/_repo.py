"""Git repository parsing, cloning, and cache management for the skill engine."""

import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime

from ._store import SOURCES_DIR, SKILLS_DIR, load_manifest, save_manifest
from ._display import IS_ZH, c_print
from ._frontmatter import parse_yaml_frontmatter


def parse_repo_target(raw_input):
    """
    Parse various GitHub / Git URL formats or local directory paths into target metadata.
    Examples:
    - /path/to/local/dir -> local import
    - owner/repo@v1.0.0 or owner/repo#branch -> specific branch/tag
    - owner/repo -> https://github.com/owner/repo.git
    - https://github.com/owner/repo/tree/main/skills/my-skill
    - git@github.com:owner/repo.git
    """
    raw = raw_input.strip()
    if not raw:
        return None

    # Check if input is an existing local directory
    expanded_path = os.path.abspath(os.path.expanduser(raw))
    if os.path.isdir(expanded_path):
        base_name = os.path.basename(expanded_path.rstrip(os.sep))
        return {
            "is_local": True,
            "local_path": expanded_path,
            "repo_url": "local",
            "owner": "local",
            "repo": base_name,
            "branch": None,
            "subpath": "",
            "cache_name": f"local__{base_name}"
        }

    # Normalize url: github.com/... -> https://github.com/...
    if raw.startswith("github.com/"):
        raw = "https://" + raw

    # Extract tag/branch override via @tag or #branch
    branch_override = None
    if "#" in raw:
        raw, branch_override = raw.split("#", 1)
    elif "@" in raw and not raw.startswith("git@"):
        raw, branch_override = raw.rsplit("@", 1)

    # Case 1: GitHub tree or blob URL (supports /tree/branch/subpath... or /blob/branch/subpath...)
    tree_match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/(?:tree|blob)/([^/]+)/?(.*)$", raw)
    if tree_match:
        owner, repo, branch, subpath = tree_match.groups()
        repo = repo.removesuffix(".git")
        repo_url = f"https://github.com/{owner}/{repo}.git"
        cache_name = f"{owner.lower()}__{repo.lower()}"
        subpath = subpath.rstrip("/")
        # If user pointed directly to a SKILL.md file, trim it to its parent directory
        if subpath.lower().endswith("/skill.md"):
            subpath = subpath[:-9].rstrip("/")
        elif subpath.lower() == "skill.md":
            subpath = ""

        return {
            "repo_url": repo_url,
            "owner": owner,
            "repo": repo,
            "branch": branch_override or branch,
            "subpath": subpath,
            "cache_name": cache_name
        }

    # Case 2: Standard GitHub HTTPS
    http_match = re.match(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git|/)?$", raw)
    if http_match:
        owner, repo = http_match.groups()
        repo = repo.removesuffix(".git")
        return {
            "repo_url": f"https://github.com/{owner}/{repo}.git",
            "owner": owner,
            "repo": repo,
            "branch": branch_override,
            "subpath": "",
            "cache_name": f"{owner.lower()}__{repo.lower()}"
        }

    # Case 3: SSH GitHub URL
    ssh_match = re.match(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", raw)
    if ssh_match:
        owner, repo = ssh_match.groups()
        repo = repo.removesuffix(".git")
        return {
            "repo_url": f"git@github.com:{owner}/{repo}.git",
            "owner": owner,
            "repo": repo,
            "branch": branch_override,
            "subpath": "",
            "cache_name": f"{owner.lower()}__{repo.lower()}"
        }

    # Case 4: Shorthand owner/repo
    shorthand_match = re.match(r"^([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)$", raw)
    if shorthand_match:
        owner, repo = shorthand_match.groups()
        repo = repo.removesuffix(".git")
        return {
            "repo_url": f"https://github.com/{owner}/{repo}.git",
            "owner": owner,
            "repo": repo,
            "branch": branch_override,
            "subpath": "",
            "cache_name": f"{owner.lower()}__{repo.lower()}"
        }

    # Fallback generic Git URL
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw.lower())
    return {
        "repo_url": raw,
        "owner": "custom",
        "repo": safe_name,
        "branch": branch_override,
        "subpath": "",
        "cache_name": safe_name
    }


def clone_or_fetch_repo(target_info, update_if_exists=False):
    """
    Clone or fetch remote repository into ~/.local/share/zfl/skill_sources/<cache_name>.
    Supports local paths, GitHub mirrors, and timeout protection.
    If update_if_exists is False and repository exists locally, it is reused directly without network fetch.
    Returns the local repository directory path or None on failure.
    """
    if target_info.get("is_local"):
        return target_info["local_path"]

    os.makedirs(SOURCES_DIR, exist_ok=True)
    cache_dir = os.path.join(SOURCES_DIR, target_info["cache_name"])
    repo_url = target_info["repo_url"]
    branch = target_info.get("branch")

    git_timeout = int(os.environ.get("ZFL_GIT_TIMEOUT", "35"))

    if not os.path.exists(os.path.join(cache_dir, ".git")):
        # Apply GitHub mirror if configured
        github_mirror = os.environ.get("ZFL_GITHUB_MIRROR", "").strip().rstrip("/")
        if github_mirror and repo_url.startswith("https://github.com/"):
            repo_url = f"{github_mirror}/{repo_url}"

        if IS_ZH:
            c_print("1;34", f"==> 正在克隆源仓库: {repo_url} ...")
        else:
            c_print("1;34", f"==> Cloning source repository: {repo_url} ...")
        
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["-b", branch])
        cmd.extend([repo_url, cache_dir])

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=git_timeout)
            if res.returncode != 0:
                c_print("1;31", f"Git clone failed:\n{res.stderr.strip()}", file=sys.stderr)
                if IS_ZH:
                    c_print("0;33", "提示: 若因网络超时失败，可设置镜像环境变量 ZFL_GITHUB_MIRROR (如 https://ghproxy.net)")
                return None
        except subprocess.TimeoutExpired:
            c_print("1;31", f"Git clone timed out after {git_timeout}s.", file=sys.stderr)
            if IS_ZH:
                c_print("0;33", "提示: 连接 GitHub 超时，建议配置代理或设置 ZFL_GITHUB_MIRROR 镜像加速。")
            return None
    elif not update_if_exists:
        # Repository already exists in local cache and update was not requested: reuse directly
        if IS_ZH:
            c_print("1;32", f"[*] 检测到本地已有仓库缓存: {target_info['cache_name']} (直接复用，免重复下载)")
        else:
            c_print("1;32", f"[*] Found local cached repository: {target_info['cache_name']} (reusing, skipping redownload)")
        return cache_dir
    else:
        if IS_ZH:
            c_print("1;34", f"==> 正在拉取源仓库最新变更: {target_info['cache_name']} ...")
        else:
            c_print("1;34", f"==> Fetching latest changes for: {target_info['cache_name']} ...")

        # Apply GitHub mirror if configured
        github_mirror = os.environ.get("ZFL_GITHUB_MIRROR", "").strip().rstrip("/")
        fetch_url = repo_url
        if github_mirror and repo_url.startswith("https://github.com/"):
            fetch_url = f"{github_mirror}/{repo_url}"

        # Clean any uncommitted / stale state in local cache
        subprocess.run(["git", "-C", cache_dir, "reset", "--hard", "HEAD"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Use shallow fetch to retrieve the latest commit of the target branch or HEAD
        fetch_cmd = ["git", "-C", cache_dir, "fetch", "--depth", "1", fetch_url]
        if branch and branch != "HEAD":
            fetch_cmd.append(branch)
        else:
            fetch_cmd.append("HEAD")

        try:
            res = subprocess.run(fetch_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=git_timeout)
            if res.returncode != 0:
                # Fallback to fetch from origin remote
                fallback_cmd = ["git", "-C", cache_dir, "fetch", "--depth", "1", "origin"]
                if branch and branch != "HEAD":
                    fallback_cmd.append(branch)
                res = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=git_timeout)

            if res.returncode != 0:
                c_print("1;31", f"Git fetch failed for {target_info['cache_name']}:\n{res.stderr.strip()}", file=sys.stderr)
                if IS_ZH:
                    c_print("0;33", "提示: 若因网络超时或连接失败，可配置代理或设置 ZFL_GITHUB_MIRROR 镜像加速。")
                return None

            # Reset local working tree and HEAD directly to FETCH_HEAD
            reset_res = subprocess.run(["git", "-C", cache_dir, "reset", "--hard", "FETCH_HEAD"],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if reset_res.returncode != 0:
                c_print("1;31", f"Git reset to FETCH_HEAD failed:\n{reset_res.stderr.strip()}", file=sys.stderr)
                return None
        except subprocess.TimeoutExpired:
            c_print("1;31", f"Git fetch timed out after {git_timeout}s for {target_info['cache_name']}.", file=sys.stderr)
            if IS_ZH:
                c_print("0;33", "提示: 连接 GitHub 超时，建议配置代理或设置 ZFL_GITHUB_MIRROR 镜像加速。")
            return None
        except Exception as e:
            c_print("1;31", f"Error updating repository {target_info['cache_name']}: {e}", file=sys.stderr)
            return None

    return cache_dir


def get_repo_head_commit(repo_dir):
    """Get the current HEAD commit hash of a git repository."""
    try:
        res = subprocess.run(["git", "-C", repo_dir, "rev-parse", "HEAD"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"


def get_repo_remote_commit(repo_dir, branch="HEAD"):
    """Get remote latest commit hash."""
    try:
        res = subprocess.run(["git", "-C", repo_dir, "rev-parse", f"origin/{branch}"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        # Fallback to HEAD
        return get_repo_head_commit(repo_dir)
    except Exception:
        return "unknown"


def scan_skills_in_dir(root_dir, limit_subpath=""):
    """
    Recursively scan root_dir (optionally restricted to limit_subpath) for all SKILL.md files.
    Returns a list of dicts with skill metadata and directory boundaries.
    """
    search_root = os.path.join(root_dir, limit_subpath) if limit_subpath else root_dir
    if not os.path.exists(search_root):
        return []

    discovered = []
    for dirpath, dirnames, filenames in os.walk(search_root):
        # Ignore hidden directories like .git
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        skill_file = None
        for f in filenames:
            if f.lower() == "skill.md":
                skill_file = os.path.join(dirpath, f)
                break

        if skill_file:
            rel_dir = os.path.relpath(dirpath, root_dir)
            if rel_dir == ".":
                rel_dir = ""

            frontmatter = parse_yaml_frontmatter(skill_file)
            fallback_name = os.path.basename(dirpath)
            if not fallback_name or fallback_name == os.path.basename(root_dir):
                fallback_name = frontmatter.get("name") or os.path.basename(root_dir)

            skill_name = frontmatter.get("name") or fallback_name
            skill_name = re.sub(r"[^a-zA-Z0-9_\-]", "-", skill_name.strip()).strip("-").lower()
            if not skill_name:
                skill_name = fallback_name.lower()

            desc = frontmatter.get("description") or ""

            # Count packaged files and subdirectories
            total_files = sum(len(files) for _, _, files in os.walk(dirpath))
            has_scripts = os.path.isdir(os.path.join(dirpath, "scripts"))
            has_refs = os.path.isdir(os.path.join(dirpath, "references"))

            discovered.append({
                "name": skill_name,
                "dir_path": dirpath,
                "rel_subpath": rel_dir,
                "description": desc,
                "file_count": total_files,
                "has_scripts": has_scripts,
                "has_refs": has_refs
            })

    # Disambiguate duplicate skill names within the same repository
    name_counts = Counter(d["name"] for d in discovered)
    generic_dirs = {"skills", "skill", "plugins", "plugin", "src", "packages", "extensions", "tools", "agents", "agent", ".agents"}

    for d in discovered:
        if name_counts[d["name"]] > 1:
            # Find distinctive directory segments from rel_subpath
            parts = [p.lower() for p in re.split(r"[/\\_]", d["rel_subpath"]) if p]
            distinctive = [p for p in parts if p not in generic_dirs and p != d["name"]]
            if distinctive:
                suffix = "-".join(distinctive)
                suffix = re.sub(r"[^a-zA-Z0-9_\-]", "-", suffix).strip("-")
                if suffix:
                    d["name"] = f"{d['name']}-{suffix}"

    # Sort by subpath depth and name
    discovered.sort(key=lambda x: (x["rel_subpath"].count(os.sep), x["name"]))
    return discovered


def reconcile_skills_manifest(skills_dir=None, sources_dir=None, manifest=None, auto_save=False):
    """
    Reconcile untracked local skills with upstream Git repositories.

    1. Checks if the skill folder has its own .git repository.
    2. Checks if the skill matches any cached repository in sources_dir.

    Returns a dict of newly reconciled skills:
    {
        "skill_name": {
            "repo_url": ...,
            "owner": ...,
            "repo": ...,
            "branch": ...,
            "subpath": ...,
            "commit_hash": ...,
            "installed_at": ...,
            "cache_name": ...
        }
    }
    """
    if skills_dir is None:
        skills_dir = SKILLS_DIR
    if sources_dir is None:
        sources_dir = SOURCES_DIR
    if manifest is None:
        manifest = load_manifest()

    if not os.path.exists(skills_dir):
        return {}

    untracked = [
        s for s in sorted(os.listdir(skills_dir))
        if os.path.isdir(os.path.join(skills_dir, s)) and s not in manifest
    ]
    if not untracked:
        return {}

    reconciled = {}

    # 1. Index all skills available across cached sources
    source_skills = {}
    if os.path.exists(sources_dir):
        for src in sorted(os.listdir(sources_dir)):
            src_dir = os.path.join(sources_dir, src)
            if not os.path.isdir(src_dir):
                continue
            try:
                url = subprocess.check_output(
                    ["git", "-C", src_dir, "remote", "get-url", "origin"],
                    stderr=subprocess.DEVNULL,
                    text=True
                ).strip()
            except Exception:
                url = ""
            commit = get_repo_head_commit(src_dir)
            discovered = scan_skills_in_dir(src_dir)
            for d in discovered:
                if d["name"] not in source_skills:
                    source_skills[d["name"]] = {
                        "repo_url": url,
                        "cache_name": src,
                        "commit_hash": commit,
                        "subpath": d["rel_subpath"]
                    }

    for s_name in untracked:
        s_path = os.path.join(skills_dir, s_name)
        git_dir = os.path.join(s_path, ".git")

        if os.path.exists(git_dir):
            url = ""
            try:
                url = subprocess.check_output(
                    ["git", "-C", s_path, "remote", "get-url", "origin"],
                    stderr=subprocess.DEVNULL,
                    text=True
                ).strip()
            except Exception:
                pass

            if url:
                commit = get_repo_head_commit(s_path)
                try:
                    branch = subprocess.check_output(
                        ["git", "-C", s_path, "rev-parse", "--abbrev-ref", "HEAD"],
                        stderr=subprocess.DEVNULL,
                        text=True
                    ).strip()
                except Exception:
                    branch = "HEAD"
                target = parse_repo_target(url) or {}
                mtime_str = datetime.fromtimestamp(os.path.getmtime(s_path)).isoformat()
                reconciled[s_name] = {
                    "repo_url": url,
                    "owner": target.get("owner", ""),
                    "repo": target.get("repo", s_name),
                    "branch": branch or "HEAD",
                    "subpath": "",
                    "commit_hash": commit or "unknown",
                    "installed_at": mtime_str,
                    "cache_name": target.get("cache_name", s_name)
                }
        elif s_name in source_skills:
            info = source_skills[s_name]
            target = parse_repo_target(info["repo_url"]) or {}
            mtime_str = datetime.fromtimestamp(os.path.getmtime(s_path)).isoformat()
            reconciled[s_name] = {
                "repo_url": info["repo_url"],
                "owner": target.get("owner", ""),
                "repo": target.get("repo", ""),
                "branch": "HEAD",
                "subpath": info["subpath"],
                "commit_hash": info["commit_hash"],
                "installed_at": mtime_str,
                "cache_name": info["cache_name"]
            }

    if auto_save and reconciled:
        manifest.update(reconciled)
        save_manifest(manifest)

    return reconciled
