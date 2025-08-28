# app/reviewer.py
import subprocess
import os
import stat
import gc
from git import Repo


# -------------------------------
# Helpers
# -------------------------------
def run_command(cmd, cwd=None):
    """Run a shell command and return (code, stdout, stderr)."""
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return proc.returncode, proc.stdout, proc.stderr


def remove_readonly(func, path, _):
    """Force remove read-only files (Windows-safe)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def get_repo_path(repo_url: str, base_dir: str = "../repos") -> str:
    """
    Ensure repo is cloned locally. If not, clone it.
    If already cloned, pull latest changes.
    Returns the local repo path.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    base_dir = os.path.join(project_root, "repos")

    os.makedirs(base_dir, exist_ok=True)

    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join(base_dir, repo_name)

    if not os.path.exists(repo_path):
        print(f"[INFO] Cloning {repo_url} into {repo_path}")
        Repo.clone_from(repo_url, repo_path)
    else:
        print(f"[INFO] Repo already exists at {repo_path}, pulling latest changes...")
        try:
            repo = Repo(repo_path)
            repo.remotes.origin.pull()
        except Exception as e:
            print(f"[WARN] Could not pull latest changes for {repo_url}: {e}")

    return repo_path


def get_git_diff(repo_path: str, staged: bool = False) -> str:
    """
    Get git diff text for the repo.
    By default, compares working directory vs HEAD.
    If staged=True, compares staged changes.
    """
    cmd = "git diff --cached" if staged else "git diff HEAD"
    code, out, err = run_command(cmd, cwd=repo_path)
    if code != 0:
        raise Exception(f"Failed to get git diff: {err}")
    return out.strip()


def run_flake8_on_files(repo_dir, files):
    """Run flake8 on only the changed Python files."""
    for f in files:
        if f.endswith(".py"):
            code, out, _ = run_command(f"flake8 {f}", cwd=repo_dir)
            yield {
                "type": "lint",
                "file": f,
                "output": out.strip(),
                "returncode": code,
            }


def run_bug_checks(repo_dir, files):
    """Run pylint (basic bug detection & style)."""
    for f in files:
        if f.endswith(".py"):
            code, out, _ = run_command(f"pylint --disable=R,C {f}", cwd=repo_dir)
            yield {
                "type": "bugcheck",
                "file": f,
                "output": out.strip(),
                "returncode": code,
            }


def auto_fix_files(repo_dir, files):
    """Run autopep8 to automatically fix style issues."""
    for f in files:
        if f.endswith(".py"):
            # Run autopep8 with aggressive formatting
            code, out, err = run_command(f"autopep8 --in-place --aggressive --aggressive {f}", cwd=repo_dir)
            if code == 0:
                yield {
                    "type": "autofix",
                    "file": f,
                    "fixed": True,
                    "output": out.strip(),
                }
            else:
                yield {
                    "type": "autofix",
                    "file": f,
                    "fixed": False,
                    "output": err.strip(),
                    "returncode": code,
                }


def stream_review(repo_url, staged=False, auto_fix=False):
    """
    Generator that streams review results incrementally:
    - Diffs
    - Linting results
    - Bug checks
    - Auto-fixing (if enabled)
    - Post-fix re-checks
    """
    repo_dir = get_repo_path(repo_url)
    diff_text = get_git_diff(repo_dir, staged=staged)

    if not diff_text:
        yield {"type": "info", "message": "No changes found to review."}
        return

    # --- Original diff ---
    yield {"type": "original_diff", "diff": diff_text}

    # --- Get changed files ---
    code, out, _ = run_command("git diff --name-only HEAD", cwd=repo_dir)
    changed_files = [line.strip() for line in out.splitlines() if line.strip()]
    yield {"type": "changed_files", "files": changed_files}

    # --- Initial lint checks ---
    for lint in run_flake8_on_files(repo_dir, changed_files):
        yield {"stage": "before_fix", **lint}

    # --- Initial bug checks ---
    for bug in run_bug_checks(repo_dir, changed_files):
        yield {"stage": "before_fix", **bug}

    # --- Auto-fix if requested ---
    if auto_fix:
        yield {"type": "info", "message": "Applying automatic fixes..."}
        for fix_result in auto_fix_files(repo_dir, changed_files):
            yield fix_result
        
        # --- Re-check after fixes ---
        yield {"type": "info", "message": "Re-running checks after fixes..."}
        for lint in run_flake8_on_files(repo_dir, changed_files):
            yield {"stage": "after_fix", **lint}
        
        for bug in run_bug_checks(repo_dir, changed_files):
            yield {"stage": "after_fix", **bug}
        
        # --- Show post-fix diff ---
        try:
            post_diff = get_git_diff(repo_dir, staged=staged)
            if post_diff:
                yield {"type": "post_fix_diff", "diff": post_diff}
        except Exception as e:
            yield {"type": "warning", "message": f"Could not get post-fix diff: {e}"}

    gc.collect()
