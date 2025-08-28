# app/ingest.py
import tempfile, os, shutil
from git import Repo

def clone_repo(git_url, branch="main"):
    tmpdir = tempfile.mkdtemp(prefix="repo_")
    Repo.clone_from(git_url, tmpdir, branch=branch)
    return tmpdir

def find_docs(repo_path):
    candidates = ["contributing.md","contributing.rst","readme.md","readme"]
    found = {}
    
    print(f"[DEBUG] Searching for docs in: {repo_path}")
    
    for root, dirs, files in os.walk(repo_path):
        for f in files:
            if f.lower() in candidates:
                p = os.path.join(root, f)
                try:
                    with open(p, "r", encoding="utf-8") as fh:
                        content = fh.read()
                        found[f.lower()] = content
                        print(f"[DEBUG] Found doc: {p} (size: {len(content)} chars)")
                except Exception as e:
                    print(f"[WARN] Could not read {p}: {e}")
    
    print(f"[DEBUG] Found related docs: {list(found.keys())}")
    print(f"[DEBUG] Total docs found: {len(found)}")
    
    return found

