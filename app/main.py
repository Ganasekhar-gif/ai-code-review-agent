# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import uvicorn
import os

# Local imports
from agent import call_llm, run_code_review
from qna import prepare_qna_inputs
from indexer import get_repo_path, _reset_collection, _collection_name


# -----------------------------
# FastAPI App
# -----------------------------
app = FastAPI(
    title="AI Code Review & QnA Agent",
    version="1.0.0",
    description="Endpoints for repository QnA and code review with LLM summarization."
)

# 👇 CORS MIDDLEWARE (fix for your React frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Root
# -----------------------------
@app.get("/")
def read_root():
    return {"status": "AI Code Review Agent is running 🚀"}


# -----------------------------
# Models
# -----------------------------
class QnaRequest(BaseModel):
    repo_url: str = Field(..., description="Git repository URL")
    query: str = Field(..., description="Natural-language question")
    top_k: int = Field(5, ge=1, le=10)


class QnaResponse(BaseModel):
    answer: str
    top_chunks: List[dict]


class ReviewRequest(BaseModel):
    repo_url: str = Field(..., description="Git repository URL")
    staged: bool = Field(False, description="If true, review only staged changes")
    auto_fix: bool = Field(False, description="If true, apply autopep8 fixes")


class ReviewResponse(BaseModel):
    summary: dict
    events: List[dict]
    formatted: str


class ResetRequest(BaseModel):
    repo_url: str = Field(..., description="Git repository URL")


# -----------------------------
# Health
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# -----------------------------
# QnA Endpoint
# -----------------------------
@app.post("/qna", response_model=QnaResponse)
def qna(req: QnaRequest):
    try:
        repo_path = get_repo_path(req.repo_url)
        _ = repo_path  # Ensure repo exists

        prepared = prepare_qna_inputs(req.repo_url, req.query)
        top_chunks = prepared.get("context", [])[:req.top_k]

        context_text = "\n\n---\n\n".join(
            [f"CHUNK {i+1}:\n{c['text']}" for i, c in enumerate(top_chunks)]
        )

        prompt = f"""
        You are an expert software assistant. I will provide you with README-like content,
        and you need to answer a question about it.

        Question: {req.query}

        Here is the content:
        {context_text}

        Based strictly on the content above, answer clearly.
        If you cannot find the answer, say:
        "I cannot find the relevant information in the README content."

        Answer:
        """

        answer = call_llm(prompt)
        return QnaResponse(answer=answer, top_chunks=top_chunks)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Review Endpoint
# -----------------------------
@app.post("/review", response_model=ReviewResponse)
def review(req: ReviewRequest):
    try:
        result = run_code_review(
            repo_url=req.repo_url,
            auto_fix=req.auto_fix,
            staged=req.staged
        )
        return ReviewResponse(
            summary=result["summary"],
            events=result["events"],
            formatted=result["formatted"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Reset Endpoint
# -----------------------------
@app.post("/reset")
def reset_chromadb(req: ResetRequest):
    try:
        collection_name = _collection_name(req.repo_url)
        _reset_collection(collection_name)
        return {"status": f"reset collection '{collection_name}' done"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Main Entrypoint
# -----------------------------
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
