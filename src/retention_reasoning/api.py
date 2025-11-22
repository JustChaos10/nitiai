"""Minimal API skeleton for the Retention Reasoning Agent."""

from __future__ import annotations

from typing import Any, Dict, AsyncGenerator
import os
import json

import pandas as pd
from loguru import logger

from .agent import RetentionReasoningAgent
from .models import Opportunity
from .utils.ingestion import AlertIngestionService
from .services import StrategyComposer


def create_app(agent: RetentionReasoningAgent):
    """Return a FastAPI app wired to the provided agent.

    FastAPI is an optional dependency; this function will raise a clear error if it is missing.
    """
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import StreamingResponse
    except Exception as exc:  # pragma: no cover - import guard
        raise ImportError("FastAPI is required: pip install fastapi uvicorn") from exc

    app = FastAPI(title="Retention Reasoning Agent")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    ingest = AlertIngestionService()
    composer = StrategyComposer()

    class AnalyzeRequest(BaseModel):
        opportunity: Dict[str, Any]
        data_preview: list[dict[str, Any]] | None = None
        business_context: str | None = None

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/analyze")
    async def analyze(payload: AnalyzeRequest):
        try:
            opp = ingest.from_payload(payload.opportunity)
            df = pd.DataFrame(payload.data_preview) if payload.data_preview else pd.DataFrame()
            session = await agent.analyze_opportunity(opp, df, payload.business_context)
            campaigns = composer.compose_campaigns(session.agent_state.get("recommended_levers", []))
            return {
                "session_id": session.session_id,
                "status": session.status,
                "validated_causes": session.validated_causes,
                "recommended_levers": session.agent_state.get("actionable_levers"),
                "explanation": session.agent_state.get("explanation"),
                "campaigns": campaigns,
            }
        except Exception as exc:
            logger.exception("Analysis failed")
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/stream")
    async def stream(payload: AnalyzeRequest):
        """Minimal streaming endpoint (chunked text)."""
        async def event_gen() -> AsyncGenerator[bytes, None]:
            try:
                yield b"data: starting analysis\n\n"
                opp = ingest.from_payload(payload.opportunity)
                df = pd.DataFrame(payload.data_preview) if payload.data_preview else pd.DataFrame()
                session = await agent.analyze_opportunity(opp, df, payload.business_context)
                campaigns = composer.compose_campaigns(session.agent_state.get("recommended_levers", []))
                result = {
                    "session_id": session.session_id,
                    "status": session.status,
                    "validated_causes": session.validated_causes,
                    "recommended_levers": session.agent_state.get("actionable_levers"),
                    "explanation": session.agent_state.get("explanation"),
                    "campaigns": campaigns,
                }
                yield f"data: {json.dumps(result)}\n\n".encode()
                yield b"data: done\n\n"
            except Exception as exc:  # pragma: no cover - streaming best-effort
                yield f"data: error: {str(exc)}\n\n".encode()
        return StreamingResponse(event_gen(), media_type="text/event-stream")

    return app
