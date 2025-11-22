"""Explanation generation node."""

from typing import Any
from loguru import logger


class ExplanationGeneratorNode:
    """Generates human-readable explanations of causal findings."""

    def __init__(self, llm: Any = None):
        """Initialize explanation generator.

        Args:
            llm: Language model for generation (unused for now)
        """
        self.llm = llm

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node function.

        Args:
            state: Graph state

        Returns:
            Updated state
        """
        logger.info("Explanation generation node")

        validated_causes = state.get("validated_causes", [])
        levers = state.get("recommended_levers", [])

        parts = []
        if validated_causes:
            parts.append(
                f"Identified {len(validated_causes)} causal factors: {', '.join(validated_causes)}."
            )
        else:
            parts.append("No validated causal factors identified.")

        if levers:
            lever_lines = []
            for lever in levers:
                lever_lines.append(
                    f"- {lever.name}: target {lever.target_variable} to affect {lever.target_outcome} "
                    f"(impact score {lever.impact_score:.2f}, feasibility {lever.feasibility.score:.2f})"
                )
            parts.append("Recommended levers:\n" + "\n".join(lever_lines))
        else:
            parts.append("No recommended levers yet.")

        explanation = "\n".join(parts)
        state["explanation"] = explanation
        return state
