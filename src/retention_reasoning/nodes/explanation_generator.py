"""Explanation generation node - creates rich, human-readable causal narratives."""

from typing import Any
from loguru import logger

from ..utils.hypothesis_utils import hypothesis_to_dict


class ExplanationGeneratorNode:
    """Generates human-readable explanations of causal findings using LLM."""

    def __init__(self, llm: Any = None):
        """Initialize explanation generator.

        Args:
            llm: Language model for generation
        """
        self.llm = llm

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node function - generates explanation.

        Args:
            state: Graph state containing validated hypotheses

        Returns:
            Updated state with rich explanation
        """
        logger.info("Generating causal explanation")

        validated_hypotheses = state.get("validated_hypotheses", [])
        validated_causes = state.get("validated_causes", [])
        opportunity = state.get("opportunity")
        business_context = state.get("business_context", "")

        # If no validated causes, return simple message
        if not validated_causes:
            state["explanation"] = (
                f"No statistically significant causal factors found for "
                f"{opportunity.title if opportunity else 'this opportunity'}. "
                f"This could indicate:\n"
                f"1. The metric change is due to external factors not in the data\n"
                f"2. More data collection is needed for conclusive analysis\n"
                f"3. The opportunity may be a false positive"
            )
            return state

        # Use LLM if available, otherwise generate structured explanation
        if self.llm:
            explanation = self._generate_with_llm(
                validated_hypotheses, validated_causes, opportunity, business_context
            )
        else:
            explanation = self._generate_structured_explanation(
                validated_hypotheses, validated_causes, opportunity, business_context
            )

        state["explanation"] = explanation
        return state

    def _generate_with_llm(
        self,
        validated_hypotheses: list[Any],
        validated_causes: list[str],
        opportunity: Any,
        business_context: str,
    ) -> str:
        """Generate rich explanation using LLM.

        Args:
            validated_hypotheses: List of validated hypothesis objects
            validated_causes: List of validated cause names
            opportunity: The retention opportunity being analyzed
            business_context: Business context string

        Returns:
            Rich natural language explanation
        """
        # Build context for LLM
        hypotheses_summary = []
        for hyp in validated_hypotheses:
            hyp_dict = hypothesis_to_dict(hyp)
            cause = hyp_dict.get("cause", "unknown")
            effect = hyp_dict.get("effect", "unknown")
            mechanism = hyp_dict.get("mechanism", "")

            # Get statistical evidence
            consensus = hyp_dict.get("consensus") or {}
            p_value = consensus.get("p_value", 1.0)
            effect_size = consensus.get("effect_size", 0.0)
            confidence = consensus.get("confidence", 0.0)

            # Get causal structure
            causal_structure = hyp_dict.get("causal_structure") or {}
            direct_effect = causal_structure.get("direct_effect", 0.0)
            indirect_effect = causal_structure.get("indirect_effect", 0.0)
            mediators = causal_structure.get("mediators", [])

            hyp_text = f"- {cause} → {effect}"
            if mechanism:
                hyp_text += f" (mechanism: {mechanism})"
            hyp_text += f"\n  Statistical evidence: p-value={p_value:.3f}, effect size={effect_size:.3f}, confidence={confidence:.1%}"

            if mediators:
                hyp_text += f"\n  Mediated through: {', '.join(mediators)}"
                hyp_text += f"\n  Direct effect: {direct_effect:.3f}, Indirect effect: {indirect_effect:.3f}"

            hypotheses_summary.append(hyp_text)

        prompt = f"""You are a retention analyst explaining causal findings to business stakeholders.

**Opportunity**: {opportunity.title if opportunity else 'Retention issue'}
{f'**Description**: {opportunity.description}' if opportunity and hasattr(opportunity, 'description') else ''}
{f'**Business Context**: {business_context}' if business_context else ''}

**Validated Causal Relationships**:
{chr(10).join(hypotheses_summary)}

Write a clear, insightful explanation (2-4 sentences) that:
1. Explains WHICH factors cause the retention issue
2. Explains WHY (the causal mechanism, not just correlation)
3. Distinguishes between direct causes and mediated effects
4. Uses concrete language business stakeholders can understand

Example style: "Customers with early negative first-week experience and late delivery are 5x likelier to churn — not because of delivery delay, but because they engage less with onboarding."

Explanation:"""

        try:
            response = self.llm.invoke(prompt)
            explanation = response.content if hasattr(response, 'content') else str(response)
            return explanation.strip()
        except Exception as e:
            logger.warning(f"LLM explanation generation failed: {e}, falling back to structured")
            return self._generate_structured_explanation(
                validated_hypotheses, validated_causes, opportunity, business_context
            )

    def _generate_structured_explanation(
        self,
        validated_hypotheses: list[Any],
        validated_causes: list[str],
        opportunity: Any,
        business_context: str,
    ) -> str:
        """Generate structured explanation without LLM.

        Args:
            validated_hypotheses: List of validated hypothesis objects
            validated_causes: List of validated cause names
            opportunity: The retention opportunity being analyzed
            business_context: Business context string

        Returns:
            Structured explanation text
        """
        parts = []

        # Header
        parts.append(
            f"## Causal Analysis: {opportunity.title if opportunity else 'Retention Opportunity'}\n"
        )

        # Summary
        parts.append(f"**Found {len(validated_causes)} validated causal factors**\n")

        # Business context
        if business_context:
            parts.append(f"**Context**: {business_context}\n")

        # Detailed findings
        parts.append("### Causal Relationships:\n")

        for hyp in validated_hypotheses:
            hyp_dict = hypothesis_to_dict(hyp)
            cause = hyp_dict.get("cause", "unknown")
            effect = hyp_dict.get("effect", "unknown")
            mechanism = hyp_dict.get("mechanism", "")

            consensus = hyp_dict.get("consensus") or {}
            p_value = consensus.get("p_value", 1.0)
            effect_size = consensus.get("effect_size", 0.0)

            causal_structure = hyp_dict.get("causal_structure") or {}
            direct_effect = causal_structure.get("direct_effect", 0.0)
            indirect_effect = causal_structure.get("indirect_effect", 0.0)
            mediators = causal_structure.get("mediators", [])
            actionable_lever = causal_structure.get("actionable_lever", "")

            # Build finding
            finding = f"**{cause.replace('_', ' ').title()}** → **{effect.replace('_', ' ').title()}**"

            if mechanism:
                finding += f"\n- Mechanism: {mechanism}"

            finding += f"\n- Strength: {abs(effect_size):.2f} (p={p_value:.3f})"

            if mediators:
                finding += f"\n- Mediated through: {', '.join(m.replace('_', ' ') for m in mediators)}"
                finding += f"\n- Direct effect: {abs(direct_effect):.2f}, Indirect: {abs(indirect_effect):.2f}"
            else:
                finding += "\n- Direct causal effect (no mediators)"

            if actionable_lever:
                finding += f"\n- **Recommended lever**: {actionable_lever}"

            parts.append(finding + "\n")

        # Key insights
        parts.append("### Key Insights:\n")

        # Identify strongest cause
        strongest = None
        if validated_hypotheses:
            strongest = max(
                (hypothesis_to_dict(h) for h in validated_hypotheses),
                key=lambda h: abs(h.get("consensus", {}).get("effect_size", 0.0)),
                default=None,
            )
        if strongest:
            cause = strongest.get("cause", "").replace("_", " ")
            effect_size = strongest.get("consensus", {}).get("effect_size", 0.0)
            parts.append(
                f"- **Primary driver**: {cause.title()} has the strongest effect "
                f"(effect size: {abs(effect_size):.2f})\n"
            )

        # Identify mediated effects
        mediated = [
            hypothesis_to_dict(h)
            for h in validated_hypotheses
            if (hypothesis_to_dict(h).get("causal_structure", {}) or {}).get("mediators")
        ]
        if mediated:
            parts.append(
                f"- **Indirect effects detected**: {len(mediated)} factor(s) work through mediating variables\n"
            )

        # Add recommendation
        parts.append("\n### Recommendation:\n")
        if strongest:
            actionable_lever = (strongest.get("causal_structure", {}) or {}).get("actionable_lever", "")
            if actionable_lever:
                parts.append(
                    f"Focus intervention on: **{actionable_lever}** to address the primary causal driver.\n"
                )
            else:
                parts.append(
                    f"Target interventions at **{strongest.get('cause', '').replace('_', ' ')}** "
                    f"as the primary driver.\n"
                )

        return "".join(parts)
