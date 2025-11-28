"""Tests for FastAPI endpoints."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


# Skip tests if FastAPI is not installed
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient


class _FakeLLM:
    """Minimal async LLM stub returning fixed hypotheses JSON."""

    async def ainvoke(self, messages):
        content = """
        {
          "hypotheses": [
            {
              "cause": "first_delivery_days",
              "effect": "churn_30d",
              "mechanism": "Slower deliveries increase churn",
              "confounders": ["order_value"],
              "mediators": [],
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
    
    def invoke(self, prompt):
        """Sync invoke for explanation generator."""
        return type("Resp", (), {"content": "Test explanation for the analysis."})


@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    return _FakeLLM()


@pytest.fixture
def test_client(mock_llm):
    """Create a test client with mocked LLM."""
    from retention_reasoning.agent import RetentionReasoningAgent
    from retention_reasoning.api import create_app
    
    # Create agent with mock LLM
    agent = RetentionReasoningAgent(
        llm=mock_llm,
        available_features=["first_delivery_days", "order_value", "churn_30d"],
    )
    
    app = create_app(agent)
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, test_client):
        """Test that health endpoint returns ok status."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestContextEndpoint:
    """Tests for /context endpoint."""

    def test_context_returns_data(self, test_client):
        """Test that context endpoint returns expected structure."""
        response = test_client.get("/context")
        assert response.status_code == 200
        data = response.json()
        
        # Check expected fields exist
        assert "metrics" in data
        assert "insights" in data
        assert "features" in data


class TestDataSummaryEndpoint:
    """Tests for /data/summary endpoint."""

    def test_data_summary_returns_structure(self, test_client):
        """Test that data summary returns expected structure."""
        response = test_client.get("/data/summary")
        assert response.status_code == 200
        data = response.json()
        
        assert "loaded" in data
        assert "tables" in data


class TestAnalyzeEndpoint:
    """Tests for /analyze endpoint."""

    def test_analyze_with_valid_opportunity(self, test_client):
        """Test analyze endpoint with valid opportunity."""
        payload = {
            "opportunity": {
                "type": "churn_spike",
                "title": "Test Opportunity",
                "description": "Testing the API",
                "affected_cohort": {"description": "Test cohort"},
                "metric_name": "churn_30d",
                "baseline_value": 0.1,
                "current_value": 0.2,
                "sample_size": 100,
                "severity": "medium",
            },
            "data_preview": [
                {"first_delivery_days": 3, "order_value": 50, "churn_30d": 0},
                {"first_delivery_days": 7, "order_value": 40, "churn_30d": 1},
            ],
        }
        
        response = test_client.post("/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Check expected fields
        assert "session_id" in data
        assert "status" in data
        assert "hypotheses" in data
        assert data["status"] == "completed"

    def test_analyze_with_invalid_opportunity_type(self, test_client):
        """Test analyze endpoint rejects invalid opportunity type."""
        payload = {
            "opportunity": {
                "type": "invalid_type",
                "title": "Test",
                "description": "Test",
                "affected_cohort": {"description": "Test"},
                "metric_name": "test",
                "baseline_value": 0.1,
                "current_value": 0.2,
                "sample_size": 100,
                "severity": "medium",
            },
        }
        
        response = test_client.post("/analyze", json=payload)
        # Should return 422 (validation error) or 500 (server error)
        assert response.status_code in [422, 500]


class TestABTestEndpoint:
    """Tests for /ab-test endpoint."""

    def test_ab_test_generates_design(self, test_client):
        """Test A/B test endpoint generates designs."""
        payload = {
            "hypotheses": [
                {
                    "id": "h1",
                    "cause": "late_delivery",
                    "effect": "churn_30d",
                }
            ],
            "baseline_rates": {"churn_30d": 0.12},
            "daily_traffic": 5000,
        }
        
        response = test_client.post("/ab-test", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "designs" in data
        assert isinstance(data["designs"], list)

