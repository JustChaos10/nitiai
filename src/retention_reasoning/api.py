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
from .services import StrategyComposer, ABTestRecommender
from .utils import (
    get_cache,
    HeterogeneousEffectEstimator,
    InterventionSimulator,
    InterventionScenario,
    ActiveLearner,
)


def format_hypotheses_for_frontend(hypotheses: list[Any]) -> list[dict]:
    """Format hypotheses for frontend consumption."""
    formatted = []
    for hyp in hypotheses:
        formatted_hyp = {
            "id": hyp.get("id", f"h{len(formatted)}"),
            "cause": hyp.get("cause", "unknown"),
            "effect": hyp.get("effect", "unknown"),
            "mechanism": hyp.get("mechanism", ""),
            "validated": hyp.get("validated", False),
        }

        # Add test results if available
        if "consensus" in hyp:
            consensus = hyp["consensus"]
            formatted_hyp["confidence"] = consensus.get("confidence", 0.0)
            formatted_hyp["p_value"] = consensus.get("p_value", 1.0)
            formatted_hyp["effect_size"] = consensus.get("effect_size", 0.0)

        # Add causal structure if available
        if "causal_structure" in hyp:
            cs = hyp["causal_structure"]
            formatted_hyp["causal_structure"] = {
                "direct_effect": cs.get("direct_effect", 0.0),
                "indirect_effect": cs.get("indirect_effect", 0.0),
                "total_effect": cs.get("total_effect", 0.0),
                "mediators": cs.get("mediators", []),
                "actionable_lever": cs.get("actionable_lever", ""),
            }

        formatted.append(formatted_hyp)

    return formatted


def build_causal_graph(hypotheses: list[Any]) -> dict:
    """Build causal graph structure from hypotheses."""
    nodes_set = set()
    edges = []

    for hyp in hypotheses:
        if not hyp.get("validated", False):
            continue

        cause = hyp.get("cause", "")
        effect = hyp.get("effect", "")

        if cause and effect:
            nodes_set.add(cause)
            nodes_set.add(effect)

            # Determine edge type and strength
            edge_type = "direct"
            strength = 0.5

            if "consensus" in hyp:
                strength = hyp["consensus"].get("effect_size", 0.5)

            if "causal_structure" in hyp:
                cs = hyp["causal_structure"]
                # Add mediators as nodes
                for mediator in cs.get("mediators", []):
                    nodes_set.add(mediator)
                    # Add indirect edges
                    edges.append({
                        "from": cause,
                        "to": mediator,
                        "strength": abs(cs.get("indirect_effect", 0.5)),
                        "type": "indirect"
                    })
                    edges.append({
                        "from": mediator,
                        "to": effect,
                        "strength": abs(cs.get("indirect_effect", 0.5)),
                        "type": "indirect"
                    })

                # Direct edge
                if cs.get("direct_effect", 0) != 0:
                    strength = abs(cs.get("direct_effect", 0.5))

            edges.append({
                "from": cause,
                "to": effect,
                "strength": abs(strength),
                "type": edge_type
            })

    return {
        "nodes": list(nodes_set),
        "edges": edges
    }


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
    ab_tester = ABTestRecommender()
    het_estimator = HeterogeneousEffectEstimator()
    simulator = InterventionSimulator()
    learner = ActiveLearner()
    cache = get_cache()

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

            # Format hypotheses and build causal graph for frontend
            hypotheses = format_hypotheses_for_frontend(session.hypotheses)
            causal_graph = build_causal_graph(session.hypotheses)

            return {
                "session_id": session.session_id,
                "status": session.status,
                "validated_causes": session.validated_causes,
                "recommended_levers": session.agent_state.get("actionable_levers"),
                "explanation": session.agent_state.get("explanation"),
                "campaigns": campaigns,
                "hypotheses": hypotheses,
                "causal_graph": causal_graph,
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

                # Format hypotheses and build causal graph
                hypotheses = format_hypotheses_for_frontend(session.hypotheses)
                causal_graph = build_causal_graph(session.hypotheses)

                result = {
                    "session_id": session.session_id,
                    "status": session.status,
                    "validated_causes": session.validated_causes,
                    "recommended_levers": session.agent_state.get("actionable_levers"),
                    "explanation": session.agent_state.get("explanation"),
                    "campaigns": campaigns,
                    "hypotheses": hypotheses,
                    "causal_graph": causal_graph,
                }
                yield f"data: {json.dumps(result)}\n\n".encode()
                yield b"data: done\n\n"
            except Exception as exc:  # pragma: no cover - streaming best-effort
                yield f"data: error: {str(exc)}\n\n".encode()
        return StreamingResponse(event_gen(), media_type="text/event-stream")

    # New endpoints for advanced features

    class ABTestRequest(BaseModel):
        hypotheses: list[dict[str, Any]]
        baseline_rates: dict[str, float]
        daily_traffic: int = 1000

    @app.post("/ab-test")
    async def generate_ab_tests(payload: ABTestRequest):
        """Generate A/B test designs for hypotheses."""
        try:
            designs = ab_tester.recommend_tests(
                hypotheses=payload.hypotheses,
                baseline_rates=payload.baseline_rates,
                daily_traffic=payload.daily_traffic,
            )
            return {
                "designs": [d.model_dump() for d in designs]
            }
        except Exception as exc:
            logger.exception("A/B test generation failed")
            raise HTTPException(status_code=500, detail=str(exc))

    class HeterogeneousRequest(BaseModel):
        data: list[dict[str, Any]]
        treatment_col: str
        outcome_col: str
        subgroup_features: list[str]
        hypothesis_id: str = "unknown"

    @app.post("/heterogeneous")
    async def analyze_heterogeneity(payload: HeterogeneousRequest):
        """Analyze treatment effect heterogeneity across subgroups."""
        try:
            df = pd.DataFrame(payload.data)
            analysis = het_estimator.analyze_heterogeneity(
                data=df,
                treatment_col=payload.treatment_col,
                outcome_col=payload.outcome_col,
                subgroup_features=payload.subgroup_features,
                hypothesis_id=payload.hypothesis_id,
            )
            return analysis.model_dump()
        except Exception as exc:
            logger.exception("Heterogeneity analysis failed")
            raise HTTPException(status_code=500, detail=str(exc))

    class SimulateRequest(BaseModel):
        data: list[dict[str, Any]]
        intervention_name: str
        target_variable: str
        intervention_type: str
        intervention_value: float
        outcome_variable: str
        condition: str | None = None

    @app.post("/simulate")
    async def simulate_intervention(payload: SimulateRequest):
        """Simulate an intervention and predict its effects."""
        try:
            df = pd.DataFrame(payload.data)
            scenario = InterventionScenario(
                intervention_name=payload.intervention_name,
                target_variable=payload.target_variable,
                intervention_type=payload.intervention_type,
                intervention_value=payload.intervention_value,
                condition=payload.condition,
            )
            result = simulator.simulate_intervention(
                data=df,
                scenario=scenario,
                outcome_variable=payload.outcome_variable,
            )
            return result.model_dump()
        except Exception as exc:
            logger.exception("Simulation failed")
            raise HTTPException(status_code=500, detail=str(exc))

    class UncertaintyRequest(BaseModel):
        hypothesis: dict[str, Any]
        data: list[dict[str, Any]]
        test_results: dict[str, Any] | None = None

    @app.post("/uncertainty")
    async def analyze_uncertainty(payload: UncertaintyRequest):
        """Analyze uncertainty and recommend data collection strategies."""
        try:
            df = pd.DataFrame(payload.data)
            analysis = learner.analyze_uncertainty(
                hypothesis=payload.hypothesis,
                data=df,
                test_results=payload.test_results,
            )
            return analysis.model_dump()
        except Exception as exc:
            logger.exception("Uncertainty analysis failed")
            raise HTTPException(status_code=500, detail=str(exc))

    return app
