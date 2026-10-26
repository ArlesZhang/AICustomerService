"""FastAPI entry point for the customer-service graph."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from .dify_client import DifyClient
from .graph import build_graph


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    session_id: str = ""
    conversation_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    intent: str
    handoff_required: bool
    handoff_reason: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    dify_error: str | None = None
    usage: dict[str, Any] | None = None
    latency_ms: float | None = None


def create_app(
    *,
    use_dify: bool = True,
    dify_client: DifyClient | None = None,
) -> FastAPI:
    """
    Build the FastAPI app.

    ``dify_client`` is injected for tests; production uses the lazy
    process-wide client from ``dify_client.get_dify_client``.
    """
    graph = build_graph(use_dify=use_dify, dify_client=dify_client)
    app = FastAPI(title="AICustomerService", version="0.1.0")
    app.state.graph = graph

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "dify": "configured" if os.getenv("DIFY_API_KEY") else "missing",
        }

    @app.post("/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        state: dict[str, Any] = {
            "user_id": payload.user_id,
            "session_id": payload.session_id,
            "question": payload.question,
            "dify_inputs": payload.inputs,
        }
        if payload.conversation_id:
            state["dify_conversation_id"] = payload.conversation_id

        result = request.app.state.graph.invoke(state)
        dify_result = result.get("dify_result") or {}

        return ChatResponse(
            answer=result.get("answer", ""),
            intent=result.get("intent", "unknown"),
            handoff_required=bool(result.get("handoff_required", False)),
            handoff_reason=result.get("handoff_reason") or None,
            conversation_id=(
                result.get("dify_conversation_id")
                or payload.conversation_id
                or None
            ),
            message_id=result.get("dify_message_id") or None,
            dify_error=result.get("dify_error") or None,
            usage=dify_result.get("usage") or None,
            latency_ms=dify_result.get("latency_ms"),
        )

    return app


app = create_app()
