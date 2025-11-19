"""Hypothesis and causal testing data models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Likelihood(str, Enum):
    """Likelihood levels for hypotheses."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TestMethod(str, Enum):
    """Causal inference test methods."""

    GRANGER_CAUSALITY = "granger_causality"
    PROPENSITY_MATCHING = "propensity_matching"
    REGRESSION_ADJUSTMENT = "regression_adjustment"
    REGRESSION_DISCONTINUITY = "regression_discontinuity"
    INSTRUMENTAL_VARIABLES = "instrumental_variables"
    DIFFERENCE_IN_DIFFERENCES = "difference_in_differences"
    SYNTHETIC_CONTROL = "synthetic_control"
    DAG_BASED = "dag_based"


class Confidence(str, Enum):
    """Confidence levels for test results."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Hypothesis(BaseModel):
    """A testable causal hypothesis about retention."""

    hypothesis_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str = Field(description="Parent reasoning session ID")

    # Core hypothesis
    cause: str = Field(description="Proposed causal variable (e.g., 'late_first_delivery')")
    effect: str = Field(description="Outcome variable (e.g., 'churn_30d')")
    mechanism: str = Field(description="Proposed causal mechanism (why would X cause Y?)")

    # Context
    confounders: list[str] = Field(
        default_factory=list, description="Potential confounding variables"
    )
    mediators: list[str] = Field(
        default_factory=list, description="Potential mediating variables"
    )
    moderators: list[str] = Field(
        default_factory=list, description="Potential moderating variables"
    )

    # Testing
    test_methods: list[TestMethod] = Field(
        default_factory=list, description="Statistical tests to apply"
    )
    data_requirements: list[str] = Field(
        default_factory=list, description="Required features/data"
    )

    # Prior assessment
    likelihood: Likelihood = Field(description="Prior likelihood (before testing)")
    rationale: str = Field(description="Why is this hypothesis plausible?")

    # Results (populated after testing)
    validated: bool | None = None
    test_results: list["TestResult"] = Field(default_factory=list)
    causal_structure: "CausalStructure | None" = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tested_at: datetime | None = None

    def to_prompt_string(self) -> str:
        """Format hypothesis for LLM prompts."""
        return f"""
Hypothesis: {self.cause} → {self.effect}
Mechanism: {self.mechanism}
Likelihood: {self.likelihood.value}
Confounders: {', '.join(self.confounders) if self.confounders else 'None identified'}
        """.strip()


class TestResult(BaseModel):
    """Result of a single causal inference test."""

    test_id: str = Field(default_factory=lambda: str(uuid4()))
    hypothesis_id: str
    method: TestMethod

    # Results
    is_significant: bool = Field(description="Is the effect statistically significant?")
    p_value: float | None = Field(None, ge=0, le=1)
    effect_size: float | None = Field(None, description="Standardized effect size (e.g., Cohen's d)")
    effect_direction: str | None = Field(None, description="positive, negative, or none")

    # Effect estimates
    point_estimate: float | None = Field(None, description="Point estimate of causal effect")
    confidence_interval: tuple[float, float] | None = Field(
        None, description="95% confidence interval"
    )
    standard_error: float | None = None

    # Quality metrics
    confidence: Confidence = Field(description="Confidence in this test result")
    sample_size: int | None = None
    balance_score: float | None = Field(
        None, ge=0, le=1, description="Covariate balance (for matching methods)"
    )

    # Details
    test_statistics: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class CausalStructure(BaseModel):
    """Detailed causal structure after confounder analysis."""

    hypothesis_id: str
    graph_id: str = Field(default_factory=lambda: str(uuid4()))

    # Effects breakdown
    direct_effect: float = Field(description="Direct causal effect (X → Y)")
    indirect_effect: float = Field(description="Effect through mediators (X → M → Y)")
    total_effect: float = Field(description="Total causal effect")

    # Structure
    mediators: list[str] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)
    colliders: list[str] = Field(default_factory=list)

    # Interpretation
    true_cause: str = Field(description="The ultimate causal variable")
    proximate_cause: str = Field(description="The immediate/proximate cause")
    actionable_lever: str = Field(description="The most actionable intervention point")

    # Graph representation
    nodes: list[dict[str, Any]] = Field(
        default_factory=list, description="Causal graph nodes"
    )
    edges: list[dict[str, Any]] = Field(
        default_factory=list, description="Causal graph edges with weights"
    )

    # Confidence
    structure_confidence: float = Field(ge=0, le=1, description="Confidence in causal structure")

    created_at: datetime = Field(default_factory=datetime.utcnow)
