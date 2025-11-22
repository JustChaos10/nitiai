"""Lever and intervention data models."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Lever(BaseModel):
    """An actionable intervention lever to improve retention."""

    lever_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    hypothesis_id: str | None = Field(None, description="Source hypothesis if applicable")

    # Lever description
    name: str = Field(description="Short name for the lever")
    description: str = Field(description="Detailed description of the intervention")
    mechanism: str = Field(description="How this lever affects the outcome")

    # Target
    target_variable: str = Field(description="Variable this lever modifies")
    target_outcome: str = Field(description="Ultimate outcome (e.g., churn_30d)")

    # Impact estimate
    expected_effect: "InterventionEstimate"

    # Feasibility
    feasibility: "FeasibilityAssessment"

    # Ranking
    impact_score: float = Field(ge=0, le=1, description="Expected impact score (0-1)")
    feasibility_score: float = Field(ge=0, le=1, description="Feasibility score (0-1)")
    overall_score: float = Field(ge=0, le=1, description="Impact × Feasibility")
    rank: int | None = None

    # Confidence
    confidence: str = Field(pattern="^(low|medium|high)$")

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def __init__(self, **data: Any):
        """Initialize and compute overall score."""
        super().__init__(**data)
        if self.overall_score is None or self.overall_score == 0:
            self.overall_score = self.impact_score * self.feasibility_score


class InterventionEstimate(BaseModel):
    """Expected impact of an intervention."""

    # Effect estimates
    absolute_effect: float = Field(description="Absolute change in outcome metric")
    relative_effect: float = Field(description="Relative change (percentage points or %)")

    # Business impact
    affected_customers: int = Field(description="Number of customers affected")
    prevented_churn: int | None = Field(None, description="Customers saved from churning")
    ltv_impact: float | None = Field(None, description="Total LTV impact in dollars")
    revenue_impact: float | None = Field(None, description="Revenue impact in dollars")

    # Uncertainty
    confidence_interval: tuple[float, float] | None = Field(
        None, description="95% CI for effect"
    )
    uncertainty_note: str | None = Field(
        None, description="Notes on assumptions/uncertainty"
    )


class FeasibilityAssessment(BaseModel):
    """Assessment of intervention feasibility."""

    # Resource requirements
    cost: str = Field(description="low, medium, high", pattern="^(low|medium|high)$")
    timeline: str = Field(description="Expected timeline (e.g., '2 weeks', '3 months')")
    engineering_effort: str = Field(
        description="low, medium, high", pattern="^(low|medium|high)$"
    )
    marketing_effort: str | None = Field(
        None, description="low, medium, high", pattern="^(low|medium|high)$"
    )

    # Dependencies
    dependencies: list[str] = Field(default_factory=list, description="Required dependencies")
    blockers: list[str] = Field(default_factory=list, description="Known blockers")

    # Overall score
    score: float = Field(
        ge=0, le=1, description="Overall feasibility score (0=impossible, 1=trivial)"
    )

    notes: str | None = None
