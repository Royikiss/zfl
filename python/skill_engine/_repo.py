"""Git repository parsing, cloning, and cache management for the skill engine."""

import os
import re
import subprocess
import sys

from ._store import SOURCES_DIR
from ._display import IS_ZH, c_print


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
        
        # Reset any local state in cache
        subprocess.run(["git", "-C", cache_dir, "reset", "--hard", "HEAD"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        cmd = ["git", "-C", cache_dir, "pull", "--ff-only"]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=git_timeout)
            if res.returncode != 0:
                # Fallback to fetch origin
                subprocess.run(["git", "-C", cache_dir, "fetch", "--depth", "1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=git_timeout)
        except subprocess.TimeoutExpired:
            c_print("1;33", f"Git pull timed out after {git_timeout}s, using cached revision.", file=sys.stderr)

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
