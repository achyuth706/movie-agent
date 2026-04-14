"""
Agent Backend — FastAPI server
==============================
Exposes the LangChain/Gemini movie agent as an HTTP API consumed by the
React frontend. All heavy lifting (tool selection, OMDb calls) happens inside
run_agent(); this server is purely the HTTP boundary.

Endpoints
---------
GET  /health  — Liveness check. Returns service status and model name.
POST /chat    — Send a user message (and optional history) to the agent.
POST /reset   — Signal that the client has cleared its conversation history.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
from dotenv import load_dotenv

load_dotenv()

from agent import run_agent  # noqa: E402 — must come after load_dotenv

MODEL_NAME = "llama3.1-8b (Cerebras)"

app = FastAPI(title="Movie Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    chat_history: list[Any] = []


@app.get("/health")
def health():
    """Return service liveness status and the active model name.

    Returns:
        JSON with 'status' (ok) and 'model' (the Gemini model in use).
    """
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/chat")
def chat(request: ChatRequest):
    """Send a user message to the movie agent and return its response.

    The agent uses Cerebras API to decide which MCP server tools to call, fetches
    real movie data, and returns a natural-language reply.

    Args (JSON body):
        message:      The user's message (required).
        chat_history: Prior conversation turns as a list of LangChain message
                      objects. Defaults to an empty list for a fresh session.

    Returns:
        JSON with 'response' containing the agent's reply string.

    Raises:
        HTTPException 400: If the message field is missing or empty.
        HTTPException 500: If the agent raises an unexpected error.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty.")

    try:
        reply = run_agent(request.message, request.chat_history)
    except Exception as exc:
        err = str(exc)
        if "unreachable" in err.lower() or "connectionerror" in err.lower():
            raise HTTPException(
                status_code=500,
                detail="The movie data service (MCP server) is unreachable. "
                       "Make sure it is running on port 8001.",
            )
        raise HTTPException(status_code=500, detail=f"Agent error: {err}")

    return {"response": reply}


@app.post("/reset")
def reset():
    """Signal that the client has cleared its conversation history.

    The agent backend is stateless — conversation history is owned by the
    client and passed in on each /chat request. This endpoint exists so the
    frontend has a clean REST action to confirm a session reset.

    Returns:
        JSON confirmation that the history has been cleared.
    """
    return {"status": "ok", "message": "Conversation history cleared."}
