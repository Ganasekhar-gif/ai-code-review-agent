# test_qna.py
from indexer import get_repo_path
from qna import prepare_qna_inputs
from agent import call_llm

# -----------------------------
# Config
# -----------------------------
REPO_URL = "https://github.com/Ganasekhar-gif/real-time-credit-card-fraud-detection-system.git"
QUERY = "how can i setup the project locally?"
TOP_K_CHUNKS = 4


def main():
    print("\n🔍 Indexing repository...")
    repo_path = get_repo_path(REPO_URL)  # clone + index, returns local repo path
    print(f"✅ Repo indexed at: {repo_path}")

    print(f"\n📝 Query: {QUERY}")
    result = prepare_qna_inputs(REPO_URL, QUERY)

    if not result or not result.get("context"):
        print("⚠️ No context found. Did indexing succeed? Are there readable files?")
        return

    top_chunks = result["context"][:TOP_K_CHUNKS]

    print(f"\n📚 Retrieved {len(top_chunks)} chunks (showing top {TOP_K_CHUNKS}):")
    for i, chunk in enumerate(top_chunks, 1):
        print(f"\n--- Chunk {i} ---")
        print("Full text:")
        print(chunk["text"])
        print("\nMetadata:", chunk["metadata"])

    # Build final prompt with better formatting
    context_text = "\n\n---\n\n".join([f"CHUNK {i+1}:\n{c['text']}" for i, c in enumerate(top_chunks)])
    prompt = f"""You are an expert software assistant. I will provide you with content from a README.md file, and you need to answer a question about it.

Question: {QUERY}

Here is the content from the README.md file:

{context_text}

Based on the README.md content above, please answer the question clearly and accurately. If you cannot find the answer in the provided content, say "I cannot find the relevant information in the README.md content."

Answer:"""

    print("\n🤖 Generating answer...")
    answer = call_llm(prompt)

    print("\n✅ Answer:")
    print(answer)


if __name__ == "__main__":
    main()
