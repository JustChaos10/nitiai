"""End-to-end test using a fake LLM and synthetic data fixture."""

import asyncio
from typing import Any

import pandas as pd

from retention_reasoning.agent import RetentionReasoningAgent
from retention_reasoning.models import Opportunity, OpportunityType


class _FakeLLM:
    """Minimal async LLM stub returning fixed hypotheses JSON."""

    async def ainvoke(self, messages: Any):
        _ = messages
        content = """
        {
          "hypotheses": [
            {
              "cause": "first_delivery_days",
              "effect": "churn_30d",
              "mechanism": "Slower deliveries increase churn",
              "confounders": ["order_value"],
              "mediators": ["onboarding_engagement_score"],
              "moderators": [],
              "test_methods": ["regression_adjustment"],
              "data_requirements": [],
              "likelihood": "high",
              "rationale": "obvious operational bottleneck"
            }
          ]
        }
        """
        return type("Resp", (), {"content": content})


def _build_data() -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "customer_id": range(50),
            "first_delivery_days": [1, 2, 5, 7, 3] * 10,
            "order_value": [50, 60, 55, 45, 80] * 10,
            "onboarding_engagement_score": [0.9, 0.8, 0.4, 0.3, 0.7] * 10,
            "churn_30d": [0, 0, 1, 1, 0] * 10,
        }
    )
    return df


def test_e2e_pipeline_runs():
    llm = _FakeLLM()
    data = _build_data()
    features = list(data.columns)
    features.remove("customer_id")
    agent = RetentionReasoningAgent(llm=llm, available_features=features)

    opportunity = Opportunity(
        type=OpportunityType.CHURN_SPIKE,
        title="Fixture",
        description="Test",
        affected_cohort={"description": "fixture"},
        metric_name="churn_30d",
        baseline_value=0.1,
        current_value=0.3,
        sample_size=len(data),
        severity="high",
    )

    session = asyncio.run(agent.analyze_opportunity(opportunity, data))
    assert session.status == "completed"
    assert session.validated_causes is not None
    # Campaigns should be present in agent_state if any levers are recommended
    assert "campaigns" in session.agent_state
