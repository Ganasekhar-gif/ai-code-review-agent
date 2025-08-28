# app/qna.py
from indexer import index_repo, retrieve_docs, get_repo_path
import os

def prepare_qna_inputs(repo_url: str, query: str):
    """
    Fetch relevant context for answering queries.
    """
    print("[QNA] preparing to retrieve chunks")

    # Ensure local clone exists (index_repo calls this too; keeping it here is harmless)
    _ = get_repo_path(repo_url)

    # Make sure the repo is indexed (idempotent; will skip existing healthy chunks)
    ok = index_repo(repo_url)
    if not ok:
        print("[ERROR] Failed to index repository")
        return {"query": query, "context": []}

    chunks = retrieve_docs(repo_url, query)
    print("[QNA] retrieved chunks")

    return {
        "query": query,
        "context": chunks
    }

def answer_question(query: str, docs):
    if not docs:
        return "I couldn't find any relevant documents to answer your question. Please make sure the repository is properly indexed."
    # Minimal baseline answer (your agent already uses LLM for final output)
    return f"Found {len(docs)} relevant chunk(s) for: {query}"
