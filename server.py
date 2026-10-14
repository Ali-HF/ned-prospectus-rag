"""FastAPI backend server for the React/TypeScript frontend.

Exposes REST endpoint /api/chat that invokes rag.answer_with_sources()
and serves conversation history, dynamic status, and citations.
"""

from typing import Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import rag

app = FastAPI(title="NED Guide API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    history: list[dict[str, Any]] = []


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "NED Guide RAG API"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    result = rag.answer_with_sources(req.question, history=req.history)
    return {
        "answer": result["answer"],
        "sources": [
            {"page": s[0], "section": s[1], "similarity": round(float(s[2]), 3)}
            for s in result.get("sources", [])
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
