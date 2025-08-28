# app/indexer.py
import os
import subprocess
import hashlib
from sentence_transformers import SentenceTransformer
import chromadb
from ingest import find_docs
from typing import List, Tuple

# ---- Paths (Windows-safe absolute paths) ----
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
REPOS_DIR = os.path.join(BASE_DIR, "repos")

print(f"[DEBUG] Using CHROMA_DIR: {CHROMA_DIR}")
print(f"[DEBUG] Using REPOS_DIR: {REPOS_DIR}")

os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(REPOS_DIR, exist_ok=True)

# ---- Chroma client (persistent) ----
client = chromadb.PersistentClient(path=CHROMA_DIR)

# ---- Embedding model ----
model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
EMB_DIM = len(model.encode("test"))
RESET_THRESHOLD = float(os.getenv("CHROMA_RESET_THRESHOLD", "0.6"))  # if >60% broken → reset

# ------------------------
# Repo management
# ------------------------
def get_repo_path(repo_url: str, base_dir: str = REPOS_DIR) -> str:
    os.makedirs(base_dir, exist_ok=True)
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = os.path.join(base_dir, repo_name)

    if not os.path.exists(repo_path):
        print(f"[INFO] Cloning {repo_url} into {repo_path}")
        subprocess.run(["git", "clone", repo_url, repo_path], check=True)
    else:
        print(f"[INFO] Repo already exists at {repo_path}, pulling latest changes...")
        try:
            subprocess.run(["git", "-C", repo_path, "pull"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[WARN] Could not pull latest changes for {repo_url}: {e}")

    return repo_path

# ------------------------
# Helpers
# ------------------------
def chunk_text(text: str, max_chars: int = 1000) -> List[str]:
    paragraphs = text.split("\n\n")
    chunks, cur = [], ""
    for p in paragraphs:
        if len(cur) + len(p) > max_chars:
            if cur.strip():
                chunks.append(cur.strip())
            cur = p
        else:
            cur += ("\n\n" if cur else "") + p
    if cur.strip():
        chunks.append(cur.strip())
    return chunks

def make_chunk_id(repo_url: str, file_path: str, chunk_text_: str) -> str:
    raw = f"{repo_url}|{file_path}|{chunk_text_}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()

def _collection_name(repo_url: str) -> str:
    return repo_url.replace("https://", "").replace("http://", "").replace("/", "_")

def _get_or_create_collection(name: str):
    try:
        return client.get_collection(name=name)
    except Exception:
        return client.create_collection(name=name)

def _batched(seq: List[str], n: int) -> List[List[str]]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]

# ------------------------
# Indexing with auto-reset
# ------------------------
def index_repo(repo_url: str) -> bool:
    repo_path = get_repo_path(repo_url)
    docs = find_docs(repo_path)
    collection_name = _collection_name(repo_url)

    print(f"[DEBUG] Indexing repo: {repo_url}")
    if not docs:
        print("[WARN] No documents found to index!")
        return False

    # Build the full worklist once (ids + content)
    worklist: List[Tuple[str, str, str]] = []  # (fname, chunk, chunk_id)
    for fname, text in docs.items():
        chunks = chunk_text(text)
        for chunk in chunks:
            cid = make_chunk_id(repo_url, fname, chunk)
            worklist.append((fname, chunk, cid))

    col = _get_or_create_collection(collection_name)

    # Pass 1: assess existing embeddings in batches to detect corruption
    existing_ids = [cid for _, _, cid in worklist]
    broken, ok = 0, 0

    print(f"[DEBUG] Assessing existing embeddings for {len(existing_ids)} chunks...")
    for batch in _batched(existing_ids, 256):
        try:
            existing = col.get(ids=batch, include=["embeddings"])
        except Exception as e:
            # If even get() fails, assume broken and reset
            print(f"[WARN] col.get failed while assessing: {e}. Forcing reset.")
            _reset_collection(collection_name)
            col = _get_or_create_collection(collection_name)
            broken = len(existing_ids)
            ok = 0
            break

        ids = existing.get("ids", [])
        embs = existing.get("embeddings", [])
        by_id = {i: e for i, e in zip(ids, embs)} if ids and len(embs) > 0 else {}

        for cid in batch:
            emb = by_id.get(cid)
            if emb is None or len(emb) != EMB_DIM:
                broken += 1
            else:
                ok += 1

    total_seen = broken + ok
    broken_ratio = (broken / total_seen) if total_seen else 0.0
    print(f"[DEBUG] Existing check → ok={ok}, broken={broken}, broken_ratio={broken_ratio:.2f}")

    # If most are broken, drop & recreate collection
    if total_seen > 0 and broken_ratio >= RESET_THRESHOLD:
        print(f"[INFO] Broken ratio {broken_ratio:.2f} >= {RESET_THRESHOLD:.2f}. Resetting collection '{collection_name}'.")
        _reset_collection(collection_name)
        col = _get_or_create_collection(collection_name)

    # Pass 2: upsert all missing/mismatched (or everything after reset)
    added, skipped, repaired = 0, 0, 0
    for fname, chunk, cid in worklist:
        needs_update = True
        try:
            existing = col.get(ids=[cid], include=["embeddings"])
            if existing and existing.get("ids"):
                emb0 = (existing.get("embeddings") or [None])[0]
                if emb0 is not None and len(emb0) == EMB_DIM:
                    skipped += 1
                    needs_update = False
                else:
                    repaired += 1
        except Exception:
            pass

        if needs_update:
            emb = model.encode(chunk).tolist()
            metadata = {"repo": repo_url, "path": fname.lower()}
            col.upsert(
                documents=[chunk],
                metadatas=[metadata],
                ids=[cid],
                embeddings=[emb],
            )
            added += 1

    try:
        print(f"[DEBUG] Final collection count: {col.count()}")
    except Exception as e:
        print(f"[WARN] col.count() failed: {e}")

    print(f"[INFO] Indexed {added} new, repaired {repaired}, skipped {skipped} chunks for {repo_url}")
    return True

def _reset_collection(collection_name: str):
    try:
        client.delete_collection(name=collection_name)
        print(f"[INFO] Deleted collection: {collection_name}")
    except Exception as e:
        print(f"[WARN] delete_collection failed (may be fine if not exists): {e}")

# ------------------------
# Retrieval
# ------------------------
def retrieve_docs(repo_url: str, query: str, top_k: int = 5):
    collection_name = _collection_name(repo_url)
    print(f"[DEBUG] Collection name: {collection_name}")
    try:
        col = client.get_collection(name=collection_name)
    except Exception as e:
        print(f"[WARN] Could not open collection: {e}. Re-indexing…")
        col = client.create_collection(name=collection_name)
        if not index_repo(repo_url):
            print("[ERROR] Failed to index repository")
            return []

    query_emb = model.encode(query).tolist()
    try:
        print("[DEBUG] Running col.query …")
        results = col.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        print("[DEBUG] col.query completed")
    except Exception as e:
        print(f"[ERROR] Query failed: {e}. Attempting one-time reset + reindex.")
        # One-time recovery: reset & reindex then retry once
        _reset_collection(collection_name)
        col = client.create_collection(name=collection_name)
        if index_repo(repo_url):
            try:
                results = col.query(
                    query_embeddings=[query_emb],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"],
                )
            except Exception as e2:
                print(f"[ERROR] Query failed even after reset: {e2}")
                return []
        else:
            return []

    if not results.get("documents") or not results["documents"][0]:
        print("[DEBUG] No documents returned.")
        return []

    return [
        {"text": doc, "metadata": meta}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]
