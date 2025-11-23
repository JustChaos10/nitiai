"""Opportunity data models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OpportunityType(str, Enum):
    """Types of retention opportunities."""

    CHURN_SPIKE = "churn_spike"
    REPEAT_RATE_DROP = "repeat_rate_drop"
    LTV_DECLINE = "ltv_decline"
    ENGAGEMENT_DROP = "engagement_drop"
    COHORT_ANOMALY = "cohort_anomaly"


class Opportunity(BaseModel):
    """A detected retention opportunity that warrants causal investigation."""

    opportunity_id: str = Field(default_factory=lambda: str(uuid4()))
    type: OpportunityType
    title: str = Field(description="Human-readable title")
    description: str = Field(description="Detailed description of the opportunity")

    # Affected cohort
    affected_cohort: dict[str, Any] = Field(
        description="Cohort definition (e.g., acquisition_date, segment)"
    )

    # Metric details
    metric_name: str = Field(description="Metric showing the issue (e.g., churn_rate_30d)")
    baseline_value: float = Field(description="Expected/historical value")
    current_value: float = Field(description="Current observed value")
    change_magnitude: float = Field(
        description="Absolute change (current - baseline)", default=None
    )
    change_percent: float = Field(
        description="Percent change ((current - baseline) / baseline)", default=None
    )

    # Sample size
    sample_size: int = Field(description="Number of customers in affected cohort")
    min_sample_size: int = Field(default=100, description="Minimum required for causal analysis")

    # Severity
    severity: str = Field(description="low, medium, high", pattern="^(low|medium|high)$")
    priority: int = Field(default=50, ge=0, le=100, description="Priority score 0-100")

    # Context
    business_context: dict[str, Any] = Field(
        default_factory=dict, description="Recent campaigns, product changes, etc."
    )

    # Timestamps
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_window_start: datetime | None = None
    analysis_window_end: datetime | None = None

    # Status
    status: str = Field(
        default="pending", pattern="^(pending|in_progress|analyzed|closed)$"
    )

    def __init__(self, **data: Any):
        """Initialize and compute derived fields."""
        super().__init__(**data)
        if self.change_magnitude is None:
            self.change_magnitude = self.current_value - self.baseline_value
        if self.change_percent is None and self.baseline_value != 0:
            self.change_percent = (
                (self.current_value - self.baseline_value) / self.baseline_value * 100
            )

    @property
    def is_sufficient_sample(self) -> bool:
        """Check if sample size is sufficient for causal analysis."""
        return self.sample_size >= self.min_sample_size

    @property
    def severity_score(self) -> float:
        """Compute severity score (0-1) based on change magnitude and sample size."""
        change_score = min(abs(self.change_percent) / 100, 1.0)
        sample_score = min(self.sample_size / 1000, 1.0)
        return (change_score * 0.7 + sample_score * 0.3)

    def to_context_string(self) -> str:
        """Generate a concise context string for LLM prompts."""
        return f"""
Opportunity: {self.title}
Type: {self.type.value}
Description: {self.description}

Metric: {self.metric_name}
- Baseline: {self.baseline_value:.2%}
- Current: {self.current_value:.2%}
- Change: {self.change_percent:+.1f}%

Affected cohort: {self.affected_cohort}
Sample size: {self.sample_size:,} customers
Severity: {self.severity}

Business context:
{self._format_business_context()}
        """.strip()

    def _format_business_context(self) -> str:
        """Format business context for display."""
        if not self.business_context:
            return "None"
        lines = []
        for key, value in self.business_context.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
