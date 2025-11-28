"""API for the Retention Reasoning Agent with data ingestion and insights."""

from __future__ import annotations

from typing import Any, Dict, AsyncGenerator, List
import os
import json

import pandas as pd
from loguru import logger

from .agent import RetentionReasoningAgent
from .models import Opportunity
from .services.ab_testing import ABTestRecommender
from .services.data_ingestion import DataIngestionService
from .services.metrics import MetricsService
from .services.insights import InsightsService
from .utils import (
    get_cache,
    HeterogeneousEffectEstimator,
    InterventionSimulator,
    InterventionScenario,
    ActiveLearner,
)
from .utils.hypothesis_utils import hypothesis_to_dict


def format_hypotheses_for_frontend(hypotheses: list[Any]) -> list[dict]:
    """Format hypotheses for frontend consumption."""
    formatted = []
    for hyp in hypotheses:
        hyp_dict = hypothesis_to_dict(hyp)
        validated_flag = hyp_dict.get("validated")
        formatted_hyp = {
            "id": hyp_dict.get("id")
            or hyp_dict.get("hypothesis_id")
            or f"h{len(formatted)}",
            "cause": hyp_dict.get("cause", "unknown"),
            "effect": hyp_dict.get("effect", "unknown"),
            "mechanism": hyp_dict.get("mechanism", ""),
            "validated": bool(validated_flag) if validated_flag is not None else False,
        }

        # Add test results if available
        consensus = hyp_dict.get("consensus") or {}
        if consensus:
            # Use coerce_to_float to handle various confidence formats
            from .utils.hypothesis_utils import coerce_to_float
            formatted_hyp["confidence"] = coerce_to_float(consensus.get("confidence"), 0.0)
            formatted_hyp["p_value"] = coerce_to_float(consensus.get("p_value"), 1.0)
            formatted_hyp["effect_size"] = coerce_to_float(consensus.get("effect_size"), 0.0)
        else:
            # Provide defaults if no consensus
            formatted_hyp["confidence"] = 0.0
            formatted_hyp["p_value"] = 1.0
            formatted_hyp["effect_size"] = 0.0

        # Add causal structure if available
        cs = hyp_dict.get("causal_structure") or {}
        if cs:
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
        hyp_dict = hypothesis_to_dict(hyp)

        if not hyp_dict.get("validated", False):
            continue

        cause = hyp_dict.get("cause", "")
        effect = hyp_dict.get("effect", "")

        if cause and effect:
            nodes_set.add(cause)
            nodes_set.add(effect)

            # Determine edge type and strength
            edge_type = "direct"
            strength = 0.5

            consensus = hyp_dict.get("consensus") or {}
            if consensus:
                strength = consensus.get("effect_size", 0.5)

            cs = hyp_dict.get("causal_structure") or {}
            if cs:
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


try:
    from fastapi import FastAPI, HTTPException, UploadFile, File, Form
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse, JSONResponse
    from fastapi.exceptions import RequestValidationError
    from pydantic import BaseModel
except ImportError:
    FastAPI = None
    BaseModel = object
    UploadFile = None
    File = None
    Form = None


class AnalyzeRequest(BaseModel):
    opportunity: Dict[str, Any]
    data_preview: list[dict[str, Any]] | None = None
    data: list[dict[str, Any]] | None = None  # Alternative field name
    business_context: str | None = None


class ABTestRequest(BaseModel):
    hypotheses: list[dict[str, Any]]
    baseline_rates: dict[str, float]
    daily_traffic: int = 1000


class HeterogeneousRequest(BaseModel):
    data: list[dict[str, Any]]
    treatment_col: str
    outcome_col: str
    subgroup_features: list[str]
    hypothesis_id: str = "unknown"


class SimulateRequest(BaseModel):
    data: list[dict[str, Any]]
    intervention_name: str
    target_variable: str
    intervention_type: str
    intervention_value: float
    outcome_variable: str
    condition: str | None = None


class UncertaintyRequest(BaseModel):
    hypothesis: dict[str, Any]
    data: list[dict[str, Any]]
    test_results: dict[str, Any] | None = None


class ContextRequest(BaseModel):
    brand_id: str | None = None
    days: int = 30


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    brand_id: str | None = None


def create_app(agent: RetentionReasoningAgent | None = None):
    """Return a FastAPI app wired to the provided agent.

    FastAPI is an optional dependency; this function will raise a clear error if it is missing.
    """
    if FastAPI is None:
        raise ImportError("FastAPI is required: pip install fastapi uvicorn")

    # If no agent provided, create a default one
    if agent is None:
        from langchain_groq import ChatGroq
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        # Initialize LLM from environment variables
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        groq_temperature = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
        groq_max_output = int(os.getenv("GROQ_MAX_OUTPUT", "4096"))

        llm = ChatGroq(
            model=groq_model,
            groq_api_key=groq_api_key,
            temperature=groq_temperature,
            max_tokens=groq_max_output,
        )
        
        # Default available features
        available_features = [
            "first_delivery_days",
            "onboarding_engagement_score",
            "order_value",
            "product_category",
            "churn_30d",
        ]
        
        agent = RetentionReasoningAgent(
            llm=llm,
            available_features=available_features,
        )
    
    # Extract llm from agent for use in dynamic feature paths
    llm = agent.llm

    app = FastAPI(title="Retention Reasoning Agent")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        logger.error("Validation error %s", exc.errors())
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )
    # Initialize standalone services (no platform integration)
    ab_tester = ABTestRecommender()
    het_estimator = HeterogeneousEffectEstimator()
    simulator = InterventionSimulator()
    learner = ActiveLearner()
    cache = get_cache()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/analyze")
    async def analyze(payload: AnalyzeRequest):
        try:
            # Create Opportunity object directly from payload
            opp = Opportunity.model_validate(payload.opportunity)
            # Accept both 'data' and 'data_preview' for backwards compatibility
            data_source = payload.data or payload.data_preview
            df = pd.DataFrame(data_source) if data_source else pd.DataFrame()
            
            # Extract available features from the actual data columns
            if not df.empty:
                available_features = df.columns.tolist()
                
                # Detect feature types to help LLM generate proper expressions
                feature_types = {}
                for col in available_features:
                    if df[col].dtype == 'object' or isinstance(df[col].iloc[0], str):
                        # Categorical - get unique values
                        unique_vals = df[col].unique()[:5]  # Show first 5 values
                        feature_types[col] = f"categorical (e.g., {', '.join(map(str, unique_vals))})"
                    elif df[col].dtype in ['int64', 'float64']:
                        feature_types[col] = f"numeric (range: {df[col].min():.1f}-{df[col].max():.1f})"
                    else:
                        feature_types[col] = str(df[col].dtype)
                
                logger.info(f"Detected {len(available_features)} features from data: {available_features}")
                logger.info(f"Feature types: {feature_types}")
                
                # Create agent with actual data features
                agent_with_features = RetentionReasoningAgent(
                    llm=llm,
                    available_features=available_features,
                )
                session = await agent_with_features.analyze_opportunity(opp, df, payload.business_context)
            else:
                session = await agent.analyze_opportunity(opp, df, payload.business_context)

            # Format hypotheses and build causal graph for frontend
            hypotheses = format_hypotheses_for_frontend(session.hypotheses)
            causal_graph = build_causal_graph(session.hypotheses)

            return {
                "session_id": session.session_id,
                "status": session.status,
                "validated_causes": session.validated_causes,
                "recommended_levers": session.agent_state.get("actionable_levers"),
                "explanation": session.agent_state.get("explanation"),
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
                # Create Opportunity object directly from payload
                opp = Opportunity.model_validate(payload.opportunity)
                # Accept both 'data' and 'data_preview' for backwards compatibility
                data_source = payload.data or payload.data_preview
                df = pd.DataFrame(data_source) if data_source else pd.DataFrame()
                
                # Extract available features from the actual data columns
                if not df.empty:
                    available_features = df.columns.tolist()
                    logger.info(f"Stream mode: Detected {len(available_features)} features")
                    # Create agent with actual data features
                    agent_with_features = RetentionReasoningAgent(
                        llm=llm,
                        available_features=available_features,
                    )
                    session = await agent_with_features.analyze_opportunity(opp, df, payload.business_context)
                else:
                    session = await agent.analyze_opportunity(opp, df, payload.business_context)

                # Format hypotheses and build causal graph
                hypotheses = format_hypotheses_for_frontend(session.hypotheses)
                causal_graph = build_causal_graph(session.hypotheses)

                result = {
                    "session_id": session.session_id,
                    "status": session.status,
                    "validated_causes": session.validated_causes,
                    "recommended_levers": session.agent_state.get("actionable_levers"),
                    "explanation": session.agent_state.get("explanation"),
                    "hypotheses": hypotheses,
                    "causal_graph": causal_graph,
                }
                yield f"data: {json.dumps(result)}\n\n".encode()
                yield b"data: done\n\n"
            except Exception as exc:  # pragma: no cover - streaming best-effort
                yield f"data: error: {str(exc)}\n\n".encode()
        return StreamingResponse(event_gen(), media_type="text/event-stream")

    # New endpoints for advanced features

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

    # =========================================================================
    # NEW ENDPOINTS: Data Ingestion, Context, and Chat
    # =========================================================================

    # Initialize data services
    data_ingestion = DataIngestionService(data_dir="data")
    metrics_service = MetricsService()
    insights_service = InsightsService()
    
    # Cache for loaded data
    _data_cache: dict[str, Any] = {}

    @app.get("/context")
    async def get_retention_context(brand_id: str | None = None, days: int = 30):
        """Get retention context including metrics, trends, and insights.
        
        This endpoint provides all the context needed for the C1 chat UI.
        """
        try:
            # Load data from files
            if "data" not in _data_cache:
                _data_cache["data"] = data_ingestion.load_from_files()
            
            data = _data_cache["data"]
            
            # Get available brands
            brands = data_ingestion.get_brands(data)
            selected_brand = brand_id or (brands[0] if brands else None)
            
            # Compute current metrics
            metrics = metrics_service.compute_metrics(
                data.get("customers", pd.DataFrame()),
                brand_id=selected_brand,
            )
            
            # Compute daily trends
            trends = metrics_service.compute_all_trends(
                data.get("metrics_daily", pd.DataFrame()),
                brand_id=selected_brand,
                days=days,
            )
            
            # Generate insights
            insights = insights_service.generate_insights(
                metrics=metrics,
                trends=trends,
                customers=data.get("customers", pd.DataFrame()),
            )
            
            # Get available features and metrics
            features = data_ingestion.get_available_features(data)
            available_metrics = data_ingestion.get_available_metrics(data)
            
            return {
                "brand_id": selected_brand,
                "brands": brands,
                "metrics": metrics,
                "trends": trends,
                "insights": insights,
                "features": features,
                "available_metrics": available_metrics,
                "customer_count": len(data.get("customers", pd.DataFrame())),
                "event_count": len(data.get("events", pd.DataFrame())),
            }
        except Exception as exc:
            logger.exception("Failed to get retention context")
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/upload")
    async def upload_data(
        customers: UploadFile = File(None),
        events: UploadFile = File(None),
        metrics: UploadFile = File(None),
    ):
        """Upload CSV/Excel files for analysis.
        
        Accepts up to 3 files:
        - customers: Customer data (required)
        - events: Event stream data (optional)
        - metrics: Daily metrics data (optional)
        """
        try:
            files = {}
            
            if customers:
                content = await customers.read()
                files["customers"] = content
                logger.info(f"Received customers file: {customers.filename}")
            
            if events:
                content = await events.read()
                files["events"] = content
                logger.info(f"Received events file: {events.filename}")
            
            if metrics:
                content = await metrics.read()
                files["metrics_daily"] = content
                logger.info(f"Received metrics file: {metrics.filename}")
            
            if not files:
                raise HTTPException(
                    status_code=400, 
                    detail="At least one file must be uploaded"
                )
            
            # Load uploaded data
            loaded_data = data_ingestion.load_from_upload(files)
            
            # Store in cache
            _data_cache["data"] = loaded_data
            
            # Return summary
            summary = {}
            for key, df in loaded_data.items():
                summary[key] = {
                    "rows": len(df),
                    "columns": list(df.columns) if not df.empty else [],
                }
            
            return {
                "status": "uploaded",
                "files": summary,
                "message": "Data uploaded successfully. Use /context to get insights.",
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Upload failed")
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/data/summary")
    async def get_data_summary():
        """Get summary of currently loaded data."""
        try:
            if "data" not in _data_cache:
                _data_cache["data"] = data_ingestion.load_from_files()
            
            data = _data_cache["data"]
            
            summary = {
                "loaded": True,
                "tables": {},
            }
            
            for key, df in data.items():
                if df.empty:
                    summary["tables"][key] = {"rows": 0, "columns": []}
                else:
                    summary["tables"][key] = {
                        "rows": len(df),
                        "columns": list(df.columns),
                        "sample": df.head(3).to_dict(orient="records"),
                    }
            
            # Add brands and features
            summary["brands"] = data_ingestion.get_brands(data)
            summary["features"] = data_ingestion.get_available_features(data)
            summary["metrics"] = data_ingestion.get_available_metrics(data)
            
            return summary
        except Exception as exc:
            logger.exception("Failed to get data summary")
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/chat/context")
    async def get_chat_context(payload: ChatRequest):
        """Get context for chat message including relevant insights.
        
        This endpoint is called by the C1 frontend to get context
        that will be injected into the system prompt.
        """
        try:
            # Ensure data is loaded
            if "data" not in _data_cache:
                _data_cache["data"] = data_ingestion.load_from_files()
            
            data = _data_cache["data"]
            brand_id = payload.brand_id
            
            # Compute metrics and insights
            metrics = metrics_service.compute_metrics(
                data.get("customers", pd.DataFrame()),
                brand_id=brand_id,
            )
            
            trends = metrics_service.compute_all_trends(
                data.get("metrics_daily", pd.DataFrame()),
                brand_id=brand_id,
                days=14,
            )
            
            insights = insights_service.generate_insights(
                metrics=metrics,
                trends=trends,
                customers=data.get("customers", pd.DataFrame()),
            )
            
            # Format for LLM
            insights_text = insights_service.format_insights_for_llm(insights)
            features = data_ingestion.get_available_features(data)
            
            # Build system context
            context = f"""You are a Retention Intelligence Agent analyzing customer retention data.

## Current Data
- Total Customers: {metrics.get('total_customers', 0):,}
- Brand: {brand_id or 'All brands'}
- Available Features: {', '.join(features[:20])}{'...' if len(features) > 20 else ''}

## Key Metrics
- Churn Rate (30d): {metrics.get('churn_rate_30d', 0):.1%}
- Average Order Value: ${metrics.get('avg_order_value', 0):.2f}
- LTV/CAC Ratio: {metrics.get('ltv_cac_ratio', 0):.1f}x
- Repeat Purchase Rate: {metrics.get('repeat_purchase_rate', 0):.1%}

{insights_text}

When answering questions:
1. Reference specific metrics and insights from the data
2. Provide actionable recommendations
3. Use charts and tables when presenting data
4. Generate hypotheses about causal relationships when asked about "why"
"""
            
            return {
                "system_context": context,
                "metrics": metrics,
                "insights": insights[:5],  # Top 5 insights
                "features": features,
            }
        except Exception as exc:
            logger.exception("Failed to get chat context")
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/analyze/from-data")
    async def analyze_from_loaded_data(
        brand_id: str | None = None,
        metric_name: str = "churn_rate_30d",
        business_context: str | None = None,
    ):
        """Run full analysis using currently loaded data.
        
        This endpoint creates an opportunity from the loaded data
        and runs the full hypothesis generation and testing pipeline.
        """
        try:
            # Ensure data is loaded
            if "data" not in _data_cache:
                _data_cache["data"] = data_ingestion.load_from_files()
            
            data = _data_cache["data"]
            customers = data.get("customers", pd.DataFrame())
            
            if customers.empty:
                raise HTTPException(
                    status_code=400,
                    detail="No customer data loaded. Upload data first.",
                )
            
            # Filter by brand
            if brand_id and "brand_id" in customers.columns:
                customers = customers[customers["brand_id"] == brand_id]
            
            # Compute metrics for opportunity
            metrics = metrics_service.compute_metrics(customers, brand_id)
            
            # Create opportunity from data
            current_value = metrics.get(metric_name, 0.15)
            baseline_value = current_value * 0.7  # Assume 30% worse than baseline
            
            opportunity_data = {
                "type": "churn_spike" if "churn" in metric_name else "engagement_drop",
                "title": f"Analysis of {metric_name} for {brand_id or 'all brands'}",
                "description": f"Automated analysis of {metric_name} patterns",
                "affected_cohort": {"description": f"Customers from {brand_id or 'all brands'}"},
                "metric_name": metric_name,
                "baseline_value": baseline_value,
                "current_value": current_value,
                "sample_size": len(customers),
                "severity": "high" if current_value > baseline_value * 1.3 else "medium",
            }
            
            opp = Opportunity.model_validate(opportunity_data)
            
            # Get insights to include as business context
            trends = metrics_service.compute_all_trends(
                data.get("metrics_daily", pd.DataFrame()),
                brand_id=brand_id,
            )
            insights = insights_service.generate_insights(metrics, trends, customers)
            insights_text = insights_service.format_insights_for_llm(insights)
            
            full_context = f"{business_context or ''}\n\n{insights_text}"
            
            # Run analysis
            available_features = customers.columns.tolist()
            agent_with_features = RetentionReasoningAgent(
                llm=llm,
                available_features=available_features,
            )
            
            session = await agent_with_features.analyze_opportunity(
                opp, 
                customers, 
                full_context
            )
            
            # Format response
            hypotheses = format_hypotheses_for_frontend(session.hypotheses)
            causal_graph = build_causal_graph(session.hypotheses)
            
            return {
                "session_id": session.session_id,
                "status": session.status,
                "opportunity": opportunity_data,
                "metrics": metrics,
                "insights": insights[:10],
                "validated_causes": session.validated_causes,
                "recommended_levers": session.agent_state.get("actionable_levers"),
                "explanation": session.agent_state.get("explanation"),
                "hypotheses": hypotheses,
                "causal_graph": causal_graph,
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Analysis from data failed")
            raise HTTPException(status_code=500, detail=str(exc))

    return app
