"""Reasoning session and explanation data models."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .hypothesis import Hypothesis
from .lever import Lever


class ReasoningStep(BaseModel):
    """A single step in the reasoning chain."""

    step_number: int
    claim: str = Field(description="The claim being made in this step")
    evidence: str = Field(description="Supporting evidence (stats, tests, etc.)")
    confidence: str = Field(pattern="^(low|medium|high)$")
    reasoning: str | None = Field(None, description="Explanation of the logic")


class ReasoningChain(BaseModel):
    """Complete reasoning chain explaining the causal analysis."""

    chain_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str

    # Summary
    summary: str = Field(description="One-sentence summary of findings")
    conclusion: str = Field(description="Main conclusion")

    # Reasoning steps
    steps: list[ReasoningStep] = Field(description="Step-by-step reasoning")

    # Recommendations
    primary_lever: str = Field(description="Primary recommended intervention")
    secondary_levers: list[str] = Field(default_factory=list)
    expected_impact: str = Field(description="Human-readable impact estimate")

    # Confidence & caveats
    overall_confidence: float = Field(ge=0, le=1)
    caveats: list[str] = Field(default_factory=list, description="Important caveats/limitations")

    # Visualization
    causal_graph_url: str | None = Field(None, description="URL to causal graph visualization")

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_markdown(self) -> str:
        """Format reasoning chain as markdown."""
        lines = [
            f"# {self.summary}",
            "",
            "## Analysis",
            "",
        ]

        for step in self.steps:
            lines.append(f"### Step {step.step_number}: {step.claim}")
            lines.append(f"**Evidence:** {step.evidence}")
            lines.append(f"**Confidence:** {step.confidence}")
            if step.reasoning:
                lines.append(f"**Reasoning:** {step.reasoning}")
            lines.append("")

        lines.extend([
            "## Conclusion",
            "",
            self.conclusion,
            "",
            "## Recommendations",
            "",
            f"**Primary Lever:** {self.primary_lever}",
            f"**Expected Impact:** {self.expected_impact}",
            "",
        ])

        if self.secondary_levers:
            lines.append("**Secondary Levers:**")
            for lever in self.secondary_levers:
                lines.append(f"- {lever}")
            lines.append("")

        if self.caveats:
            lines.append("## Caveats")
            lines.append("")
            for caveat in self.caveats:
                lines.append(f"- {caveat}")
            lines.append("")

        lines.append(f"**Overall Confidence:** {self.overall_confidence:.0%}")

        return "\n".join(lines)


class ReasoningSession(BaseModel):
    """A complete retention reasoning session."""

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    opportunity_id: str

    # Status
    status: str = Field(
        default="in_progress",
        pattern="^(in_progress|completed|failed|cancelled)$"
    )

    # Hypotheses
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    hypotheses_count: int = Field(default=0)
    validated_hypotheses_count: int = Field(default=0)

    # Results
    validated_causes: list[str] = Field(default_factory=list)
    recommended_levers: list[Lever] = Field(default_factory=list)
    reasoning_chain: ReasoningChain | None = None

    # Quality metrics
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    completeness_score: float = Field(default=0.0, ge=0, le=1)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error_message: str | None = None

    # Agent state (for LangGraph)
    agent_state: dict[str, Any] = Field(default_factory=dict)

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Add a hypothesis to the session."""
        self.hypotheses.append(hypothesis)
        self.hypotheses_count = len(self.hypotheses)
        self.updated_at = datetime.utcnow()

    def add_lever(self, lever: Lever) -> None:
        """Add a recommended lever to the session."""
        self.recommended_levers.append(lever)
        self.updated_at = datetime.utcnow()

    def mark_completed(self) -> None:
        """Mark the session as completed."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.validated_hypotheses_count = sum(
            1 for h in self.hypotheses if h.validated is True
        )

    def mark_failed(self, error: str) -> None:
        """Mark the session as failed."""
        self.status = "failed"
        self.error_message = error
        self.updated_at = datetime.utcnow()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the session."""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "hypotheses_tested": self.hypotheses_count,
            "validated_causes": self.validated_causes,
            "recommended_levers_count": len(self.recommended_levers),
            "confidence_score": self.confidence_score,
            "duration": (
                (self.completed_at or datetime.utcnow()) - self.created_at
            ).total_seconds(),
        }
