"""Lever impact estimation node - ranks actionable levers by expected impact."""

from typing import Any
from loguru import logger


class LeverEstimatorNode:
    """Estimates and ranks intervention levers by expected impact."""

    def __init__(self):
        """Initialize lever estimator."""
        pass

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node function - estimates lever impact.

        Args:
            state: Graph state with validated hypotheses

        Returns:
            Updated state with ranked levers
        """
        logger.info("Estimating lever impact and ranking")

        validated_hypotheses = state.get("validated_hypotheses", [])
        actionable_levers = state.get("actionable_levers", [])

        if not validated_hypotheses:
            logger.warning("No validated hypotheses - cannot estimate lever impact")
            state["recommended_levers"] = []
            return state

        # Estimate impact for each lever
        lever_impacts = self._estimate_lever_impacts(validated_hypotheses)

        # Rank levers by expected impact
        ranked_levers = sorted(
            lever_impacts, key=lambda x: x["expected_impact"], reverse=True
        )

        # Store top levers
        state["recommended_levers"] = [lever["name"] for lever in ranked_levers]
        state["lever_impact_estimates"] = ranked_levers

        logger.info(
            f"Ranked {len(ranked_levers)} levers. "
            f"Top lever: {ranked_levers[0]['name'] if ranked_levers else 'none'}"
        )

        return state

    def _estimate_lever_impacts(
        self, validated_hypotheses: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Estimate expected impact for each actionable lever.

        Impact is estimated based on:
        1. Effect size from causal tests
        2. Direct vs indirect effect strength
        3. Statistical confidence
        4. Feasibility (can we actually intervene on this variable?)

        Args:
            validated_hypotheses: List of validated hypothesis objects

        Returns:
            List of lever impact estimates with rankings
        """
        lever_map = {}  # lever_name -> accumulated impact

        for hyp in validated_hypotheses:
            cause = hyp.get("cause", "")
            consensus = hyp.get("consensus", {})
            causal_structure = hyp.get("causal_structure", {})

            # Get statistical metrics
            effect_size = abs(consensus.get("effect_size", 0.0))
            p_value = consensus.get("p_value", 1.0)
            confidence = consensus.get("confidence", 0.0)

            # Get causal structure
            direct_effect = abs(causal_structure.get("direct_effect", 0.0))
            indirect_effect = abs(causal_structure.get("indirect_effect", 0.0))
            total_effect = abs(causal_structure.get("total_effect", effect_size))
            actionable_lever = causal_structure.get("actionable_lever", "")
            mediators = causal_structure.get("mediators", [])

            # Determine the lever to act on
            # Priority: explicit actionable_lever > direct cause > mediators
            lever_name = actionable_lever or cause

            if lever_name not in lever_map:
                lever_map[lever_name] = {
                    "name": lever_name,
                    "expected_impact": 0.0,
                    "confidence": 0.0,
                    "direct_effect": 0.0,
                    "indirect_effect": 0.0,
                    "affected_hypotheses": [],
                    "feasibility_score": 1.0,  # Default high feasibility
                }

            # Calculate impact score
            # Impact = total_effect * confidence * feasibility
            statistical_confidence = 1 - p_value  # Higher is better
            impact_score = total_effect * statistical_confidence

            # Accumulate impact (lever might affect multiple outcomes)
            lever_map[lever_name]["expected_impact"] += impact_score
            lever_map[lever_name]["confidence"] = max(
                lever_map[lever_name]["confidence"], confidence
            )
            lever_map[lever_name]["direct_effect"] += direct_effect
            lever_map[lever_name]["indirect_effect"] += indirect_effect
            lever_map[lever_name]["affected_hypotheses"].append(
                {
                    "cause": cause,
                    "effect": hyp.get("effect", ""),
                    "mechanism": hyp.get("mechanism", ""),
                    "effect_size": effect_size,
                }
            )

            # Adjust feasibility based on lever type
            lever_map[lever_name]["feasibility_score"] = self._assess_feasibility(
                lever_name, mediators
            )

            # Final expected impact = raw impact * feasibility
            lever_map[lever_name]["expected_impact"] *= lever_map[lever_name][
                "feasibility_score"
            ]

        # Convert to list with metadata
        levers = []
        for lever_data in lever_map.values():
            # Calculate impact tier
            impact = lever_data["expected_impact"]
            if impact > 0.5:
                tier = "High"
            elif impact > 0.2:
                tier = "Medium"
            else:
                tier = "Low"

            levers.append(
                {
                    "name": lever_data["name"],
                    "expected_impact": lever_data["expected_impact"],
                    "confidence": lever_data["confidence"],
                    "direct_effect": lever_data["direct_effect"],
                    "indirect_effect": lever_data["indirect_effect"],
                    "impact_tier": tier,
                    "feasibility_score": lever_data["feasibility_score"],
                    "num_affected_outcomes": len(lever_data["affected_hypotheses"]),
                    "affected_hypotheses": lever_data["affected_hypotheses"],
                    "recommendation": self._generate_lever_recommendation(
                        lever_data["name"],
                        lever_data["expected_impact"],
                        lever_data["affected_hypotheses"],
                    ),
                }
            )

        return levers

    def _assess_feasibility(self, lever_name: str, mediators: list[str]) -> float:
        """Assess how feasible it is to intervene on this lever.

        Args:
            lever_name: Name of the lever/variable
            mediators: List of mediating variables

        Returns:
            Feasibility score 0-1 (1 = highly feasible)
        """
        lever_lower = lever_name.lower()

        # High feasibility levers (easy to intervene)
        high_feasibility_patterns = [
            "onboarding",
            "communication",
            "email",
            "message",
            "offer",
            "discount",
            "support",
            "training",
            "feature",
            "tutorial",
        ]

        # Medium feasibility levers (moderate difficulty)
        medium_feasibility_patterns = [
            "delivery",
            "shipping",
            "product",
            "quality",
            "price",
            "timing",
        ]

        # Low feasibility levers (hard to change quickly)
        low_feasibility_patterns = [
            "demographic",
            "age",
            "gender",
            "location",
            "acquisition_source",
            "device_type",
        ]

        # Check patterns
        for pattern in high_feasibility_patterns:
            if pattern in lever_lower:
                return 1.0

        for pattern in medium_feasibility_patterns:
            if pattern in lever_lower:
                return 0.7

        for pattern in low_feasibility_patterns:
            if pattern in lever_lower:
                return 0.3

        # Default moderate feasibility
        return 0.6

    def _generate_lever_recommendation(
        self, lever_name: str, expected_impact: float, affected_hypotheses: list[dict]
    ) -> str:
        """Generate actionable recommendation for a lever.

        Args:
            lever_name: Name of the lever
            expected_impact: Expected impact score
            affected_hypotheses: Hypotheses affected by this lever

        Returns:
            Recommendation text
        """
        lever_display = lever_name.replace("_", " ").title()

        if expected_impact > 0.5:
            priority = "High Priority"
        elif expected_impact > 0.2:
            priority = "Medium Priority"
        else:
            priority = "Low Priority"

        # Build recommendation
        recommendation = f"{priority}: {lever_display}"

        # Add context about what it affects
        if len(affected_hypotheses) == 1:
            hyp = affected_hypotheses[0]
            recommendation += f" - impacts {hyp['effect'].replace('_', ' ')}"
        elif len(affected_hypotheses) > 1:
            effects = [h["effect"].replace("_", " ") for h in affected_hypotheses]
            recommendation += f" - impacts {len(effects)} outcomes: {', '.join(effects[:2])}"
            if len(effects) > 2:
                recommendation += f", +{len(effects) - 2} more"

        return recommendation
