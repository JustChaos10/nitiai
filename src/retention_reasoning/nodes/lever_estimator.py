"""Lever impact estimation node."""

from typing import Any
from loguru import logger

from ..models.lever import Lever, InterventionEstimate, FeasibilityAssessment


class LeverEstimatorNode:
    """Estimates impact of intervention levers."""

    def __init__(self):
        """Initialize lever estimator."""
        pass

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node function.

        Args:
            state: Graph state

        Returns:
            Updated state
        """
        logger.info("Lever estimation node")

        validated_hypotheses = state.get("validated_hypotheses", [])
        data = state.get("data")
        sample_size = len(data) if data is not None else 0

        levers: list[Lever] = []
        seen_targets: set[str] = set()

        for hyp in validated_hypotheses:
            # Skip if we already created a lever for this cause
            target_key = hyp.cause
            if target_key in seen_targets:
                continue
            seen_targets.add(target_key)

            # Pull effect sizes from causal structure or tests
            effect_estimate = 0.0
            if hyp.causal_structure:
                effect_estimate = abs(hyp.causal_structure.total_effect)
            elif hyp.test_results:
                # Use the largest observed effect size
                effect_estimate = max(
                    [abs(r.effect_size or 0.0) for r in hyp.test_results]
                )
            effect_direction = "negative"
            if hyp.test_results:
                # Choose the direction from the strongest effect
                ordered = sorted(
                    hyp.test_results, key=lambda r: abs(r.effect_size or 0.0), reverse=True
                )
                if ordered and ordered[0].effect_direction:
                    effect_direction = ordered[0].effect_direction

            effect_component = min(effect_estimate / 0.5, 1.0) if effect_estimate else 0.1
            sample_component = min(sample_size / 1000, 1.0) if sample_size else 0.0
            impact_score = min(effect_component * 0.7 + sample_component * 0.3, 1.0)

            feasibility_score = 0.6  # simple default; could be tuned by cause type
            if "delivery" in hyp.cause or "order" in hyp.cause:
                feasibility_score = 0.55
            elif "engagement" in hyp.cause:
                feasibility_score = 0.65

            # Name lever based on direction (assume higher cause increases churn if effect_direction positive)
            if effect_direction == "positive":
                lever_action = "Reduce"
            elif effect_direction == "negative":
                lever_action = "Improve"
            else:
                lever_action = "Adjust"

            lever_name = f"{lever_action} {hyp.cause}"

            lever = Lever(
                session_id=hyp.session_id,
                hypothesis_id=hyp.hypothesis_id,
                name=lever_name,
                description=f"Intervene on {hyp.cause} to improve {hyp.effect}",
                mechanism=hyp.mechanism,
                target_variable=hyp.cause,
                target_outcome=hyp.effect,
                expected_effect=InterventionEstimate(
                    absolute_effect=effect_estimate,
                    relative_effect=effect_estimate,
                    affected_customers=sample_size,
                    prevented_churn=int(sample_size * min(effect_estimate, 1.0) * 0.1)
                    if sample_size
                    else None,
                    ltv_impact=None,
                    revenue_impact=None,
                    confidence_interval=None,
                    uncertainty_note="Heuristic estimate from causal testing",
                ),
                feasibility=FeasibilityAssessment(
                    cost="medium",
                    timeline="4 weeks",
                    engineering_effort="medium",
                    marketing_effort="low",
                    dependencies=[],
                    blockers=[],
                    score=feasibility_score,
                    notes=None,
                ),
                impact_score=impact_score,
                feasibility_score=feasibility_score,
                overall_score=impact_score * feasibility_score,
                confidence="medium",
            )
            levers.append(lever)

        # Rank levers by overall score
        levers.sort(key=lambda l: l.overall_score, reverse=True)
        for idx, lever in enumerate(levers, start=1):
            lever.rank = idx

        state["recommended_levers"] = levers
        state["actionable_levers"] = [lever.target_variable for lever in levers]
        return state
