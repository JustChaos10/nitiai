"""Simple Streamlit frontend for the Retention Reasoning Agent."""

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from retention_reasoning import RetentionReasoningAgent
from retention_reasoning.models import OpportunityType
from retention_reasoning.utils.data_loader import BigQueryLoader, load_feature_metadata
from retention_reasoning.utils.ingestion import AlertIngestionService
from examples.simple_example import generate_synthetic_data


load_dotenv()
ROOT_DIR = Path(__file__).resolve().parent.parent


def _create_llm():
    """Initialize the Groq Cloud chat model with env-driven settings."""
    if not os.getenv("GROQ_API_KEY"):
        st.error("Set GROQ_API_KEY (and optionally GROQ_MODEL) in your environment.")
        return None
    try:
        groq_module = __import__("langchain_groq")
        ChatGroq = getattr(groq_module, "ChatGroq")
    except Exception:
        st.error("langchain_groq is required. Install dependencies first.")
        return None

    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        temperature=float(os.getenv("GROQ_TEMPERATURE", 0.3)),
        service_tier=os.getenv("GROQ_SERVICE_TIER", "on_demand"),
        max_retries=int(os.getenv("GROQ_MAX_RETRIES", 2)),
    )


def build_agent(llm):
    bq_loader = BigQueryLoader()
    # Fallback to feature list if we can't load BigQuery yet
    fallback_data = generate_synthetic_data(n_samples=200)
    available_features = list(fallback_data.columns)
    available_features.remove("customer_id")
    agent = RetentionReasoningAgent(
        llm=llm,
        available_features=available_features,
        data_loader=bq_loader,
    )
    return agent, fallback_data


def main():
    st.title("Retention Reasoning Agent (Streamlit)")
    st.sidebar.header("Data Options")
    max_rows = st.sidebar.number_input("Max rows to load", 100, 10000, 2000, 100)

    default_alert = {
        "type": OpportunityType.CHURN_SPIKE.value,
        "title": "High churn in recent cohort",
        "description": "Recent customers show elevated churn rates",
        "metric_name": "churn_30d",
        "baseline_value": 0.15,
        "current_value": 0.18,
        "sample_size": 500,
        "severity": "high",
        "cohort": {"description": "All customers in dataset"},
        "business_context": {"recent_changes": "Warehouse delays"},
    }

    alert_text = st.text_area(
        "Alert/Opportunity payload (JSON)", json.dumps(default_alert, indent=2), height=220
    )
    run_button = st.button("Run Analysis")

    if not run_button:
        st.info("Configure the payload and click 'Run Analysis'.")
        return

    try:
        payload = json.loads(alert_text)
    except Exception as exc:
        st.error(f"Invalid JSON: {exc}")
        return

    llm = _create_llm()
    if not llm:
        return

    agent, fallback_data = build_agent(llm)
    ingest = AlertIngestionService()

    try:
        opp = ingest.from_payload(payload)
    except Exception as exc:
        st.error(f"Failed to parse opportunity: {exc}")
        return

    # Try loading live data; fallback to synthetic
    data = None
    try:
        data = agent.data_loader.load_enriched_customers(limit=max_rows)  # type: ignore[attr-defined]
        st.success(f"Loaded {len(data)} rows from BigQuery enriched_customers")
    except Exception as exc:
        st.warning(f"BigQuery load failed, using synthetic data. ({exc})")
        data = fallback_data.head(max_rows)

    st.write("Running analysis...")
    with st.spinner("Analyzing..."):
        session = agent.analyze_opportunity_sync(
            opportunity=opp,
            data=data,
            business_context=payload.get("business_context", ""),
        )

    st.subheader("Results")
    st.write(f"Status: {session.status}")
    st.write(f"Validated causes: {session.validated_causes}")
    st.write(f"Confidence: {session.confidence_score:.1%}")

    if session.agent_state.get("explanation"):
        st.markdown("**Explanation**")
        st.write(session.agent_state["explanation"])

    if session.agent_state.get("campaigns"):
        st.markdown("**Campaigns**")
        for c in session.agent_state["campaigns"]:
            st.json(c)

    st.markdown("**Hypotheses**")
    for h in session.hypotheses:
        st.write(f"- {h.cause} → {h.effect}, validated={h.validated}")


if __name__ == "__main__":
    main()
