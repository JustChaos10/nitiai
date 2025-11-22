"""Hypothesis generation node using LLM."""

import json
import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from ..models.hypothesis import Hypothesis, Likelihood, TestMethod
from ..models.opportunity import Opportunity
from ..prompts.hypothesis_generation import (
    HYPOTHESIS_GENERATION_SYSTEM_PROMPT,
    generate_hypothesis_prompt,
)


def _parse_test_method(method: str) -> TestMethod | None:
    """Normalize test method strings into a TestMethod enum."""

    normalized = method.strip().lower().replace(" ", "_").replace("-", "_")

    for option in TestMethod:
        if normalized == option.value:
            return option

    synonyms: dict[str, TestMethod] = {
        "logistic_regression": TestMethod.REGRESSION_ADJUSTMENT,
        "regression_analysis": TestMethod.REGRESSION_ADJUSTMENT,
        "treatment_effect_regression": TestMethod.REGRESSION_ADJUSTMENT,
        "survival_analysis": TestMethod.REGRESSION_ADJUSTMENT,
        "propensity_score_matching": TestMethod.PROPENSITY_MATCHING,
        "propensity_scoring": TestMethod.PROPENSITY_MATCHING,
        "propensity_score": TestMethod.PROPENSITY_MATCHING,
        "cox_proportional_hazards_model": TestMethod.REGRESSION_ADJUSTMENT,
        "cox_proportional_hazards": TestMethod.REGRESSION_ADJUSTMENT,
        "cox_hazard_model": TestMethod.REGRESSION_ADJUSTMENT,
        "cox_model": TestMethod.REGRESSION_ADJUSTMENT,
        "instrumental_variable": TestMethod.INSTRUMENTAL_VARIABLES,
        "instrumental_variables": TestMethod.INSTRUMENTAL_VARIABLES,
        "iv": TestMethod.INSTRUMENTAL_VARIABLES,
        "difference_in_difference": TestMethod.DIFFERENCE_IN_DIFFERENCES,
        "difference_in_differences": TestMethod.DIFFERENCE_IN_DIFFERENCES,
        "cohort_analysis": TestMethod.DIFFERENCE_IN_DIFFERENCES,
        "synthetic_control": TestMethod.SYNTHETIC_CONTROL,
        "synthetic_control_method": TestMethod.SYNTHETIC_CONTROL,
        "dag_analysis": TestMethod.DAG_BASED,
        "dag_based": TestMethod.DAG_BASED,
        "t_test": TestMethod.REGRESSION_ADJUSTMENT,
        "chi_squared_test": TestMethod.REGRESSION_ADJUSTMENT,
        "matching_on_product_category": TestMethod.PROPENSITY_MATCHING,
        "matching_on_onboarding_engagement_score": TestMethod.PROPENSITY_MATCHING,
        "matching_on_first_order_return_rate": TestMethod.PROPENSITY_MATCHING,
        "matching_on_time_since_last_order": TestMethod.PROPENSITY_MATCHING,
        "classification_tree": TestMethod.REGRESSION_ADJUSTMENT,
        "decision_tree": TestMethod.REGRESSION_ADJUSTMENT,
        "decision_trees": TestMethod.REGRESSION_ADJUSTMENT,
        "intention_to_treat_analysis": TestMethod.REGRESSION_ADJUSTMENT,
        "stratified_sampling": TestMethod.PROPENSITY_MATCHING,
        "generalized_linear_mixed_model": TestMethod.REGRESSION_ADJUSTMENT,
        "multiple_imputation": TestMethod.REGRESSION_ADJUSTMENT,
        "cluster_analysis": TestMethod.REGRESSION_ADJUSTMENT,
        "clustering": TestMethod.REGRESSION_ADJUSTMENT,
        "regression_tree": TestMethod.REGRESSION_ADJUSTMENT,
        "regression_trees": TestMethod.REGRESSION_ADJUSTMENT,
        "random_forest": TestMethod.REGRESSION_ADJUSTMENT,
        "random_forests": TestMethod.REGRESSION_ADJUSTMENT,
        "decision_tree_analysis": TestMethod.REGRESSION_ADJUSTMENT,
        "decision_tree": TestMethod.REGRESSION_ADJUSTMENT,
        "decision_trees": TestMethod.REGRESSION_ADJUSTMENT,
        "regression_discontinuity_design": TestMethod.REGRESSION_DISCONTINUITY,
        "instrumental_variable_analysis": TestMethod.INSTRUMENTAL_VARIABLES,
        "linear_regression": TestMethod.REGRESSION_ADJUSTMENT,
        "ordinary_least_squares": TestMethod.REGRESSION_ADJUSTMENT,
        "chi_square_test": TestMethod.REGRESSION_ADJUSTMENT,
        "chi_squared": TestMethod.REGRESSION_ADJUSTMENT,
        "chi_square": TestMethod.REGRESSION_ADJUSTMENT,
        "difference_in_means": TestMethod.REGRESSION_ADJUSTMENT,
        "marginal_effect": TestMethod.REGRESSION_ADJUSTMENT,
        "difference_of_means": TestMethod.REGRESSION_ADJUSTMENT,
    }

    return synonyms.get(normalized)


class HypothesisGeneratorNode:
    """Generates causal hypotheses using an LLM."""

    _column_guess_pattern = re.compile(r"(?P<column>[A-Za-z_][A-Za-z0-9_]*)")
    _alias_map: dict[str, str] = {
        "first_order_day": "first_delivery_days",
        "first_order_days": "first_delivery_days",
        "first_order_value": "order_value",
        "average_order_value": "order_value",
        "avg_order_value": "order_value",
        "product_mix": "product_category",
        "product_mix_high": "product_category",
        "order_frequency": "order_value",  # best-effort fallback
        "time_since_last_order": "first_delivery_days",  # best-effort fallback
    }

    def _extract_column_name(self, expression: str) -> str | None:
        """Extract a plausible column name from a human-readable description."""
        match = self._column_guess_pattern.match(expression.strip())
        return match.group("column") if match else None

    def _resolve_cause_feature(self, cause_expr: str) -> str | None:
        """Resolve a cause expression to an available feature name if possible."""
        candidate = (self._extract_column_name(cause_expr) or "").strip()
        if candidate in self.available_features:
            return candidate

        key = candidate.lower()
        alias = self._alias_map.get(key)
        if alias and alias in self.available_features:
            logger.info(f"Mapping cause '{cause_expr}' to available feature '{alias}'")
            return alias

        return None

    def __init__(
        self,
        llm: BaseChatModel,
        available_features: list[str],
        max_hypotheses: int = 10,
    ):
        """Initialize hypothesis generator.

        Args:
            llm: Language model for generation
            available_features: List of available features in the dataset
            max_hypotheses: Maximum number of hypotheses to generate
        """
        self.llm = llm
        self.available_features = available_features
        self.max_hypotheses = max_hypotheses

    async def generate(
        self,
        opportunity: Opportunity,
        session_id: str,
        business_context: str | None = None,
    ) -> list[Hypothesis]:
        """Generate hypotheses for the given opportunity.

        Args:
            opportunity: The retention opportunity to analyze
            session_id: ID of the reasoning session
            business_context: Optional business context

        Returns:
            List of generated hypotheses
        """
        logger.info(f"Generating hypotheses for opportunity: {opportunity.opportunity_id}")

        # Create prompt
        prompt = generate_hypothesis_prompt(
            opportunity_context=opportunity.to_context_string(),
            available_features=self.available_features,
            business_context=business_context,
        )

        # Call LLM
        messages = [
            SystemMessage(content=HYPOTHESIS_GENERATION_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Parse JSON response
            hypotheses_data = self._parse_response(response_text)

            # Convert to Hypothesis objects
            hypotheses = []
            seen_keys: set[tuple[str, str]] = set()
            for i, hyp_data in enumerate(hypotheses_data.get("hypotheses", [])[:self.max_hypotheses]):
                try:
                    normalized_cause = self._resolve_cause_feature(hyp_data["cause"])
                    if not normalized_cause:
                        logger.warning(
                            f"Skipping hypothesis {i+1} because cause '{hyp_data['cause']}' "
                            f"does not map to available features"
                        )
                        continue

                    effect_name = hyp_data.get("effect", opportunity.metric_name)
                    key = (normalized_cause, effect_name)
                    if key in seen_keys:
                        logger.info(
                            f"Skipping duplicate hypothesis for cause '{normalized_cause}' and effect '{effect_name}'"
                        )
                        continue

                    test_methods = []
                    for raw_method in hyp_data.get("test_methods", []):
                        parsed_method = _parse_test_method(raw_method)
                        if parsed_method:
                            test_methods.append(parsed_method)
                        else:
                            logger.warning(f"Skipping unknown test method '{raw_method}'")

                    hypothesis = Hypothesis(
                        session_id=session_id,
                        cause=normalized_cause,
                        effect=effect_name,
                        mechanism=hyp_data["mechanism"],
                        confounders=hyp_data.get("confounders", []),
                        mediators=hyp_data.get("mediators", []),
                        moderators=hyp_data.get("moderators", []),
                        test_methods=test_methods,
                        data_requirements=hyp_data.get("data_requirements", []),
                        likelihood=Likelihood(hyp_data.get("likelihood", "medium")),
                        rationale=hyp_data.get("rationale", ""),
                    )
                    seen_keys.add(key)
                    hypotheses.append(hypothesis)
                    logger.info(f"Generated hypothesis {i+1}: {hypothesis.cause} → {hypothesis.effect}")

                except Exception as e:
                    logger.warning(f"Failed to parse hypothesis {i+1}: {e}")
                    continue

            logger.info(f"Generated {len(hypotheses)} valid hypotheses")
            return hypotheses

        except Exception as e:
            logger.error(f"Failed to generate hypotheses: {e}")
            return []

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse JSON response from LLM.

        Args:
            response_text: Raw response text

        Returns:
            Parsed JSON object
        """
        # Try to extract JSON from markdown code blocks if present
        if "```json" in response_text:
            start = response_text.index("```json") + 7
            end = response_text.index("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.index("```") + 3
            end = response_text.index("```", start)
            response_text = response_text[start:end].strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return {"hypotheses": []}

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node function (async)."""
        opportunity = state["opportunity"]
        session_id = state["session_id"]
        business_context = state.get("business_context")

        hypotheses = await self.generate(opportunity, session_id, business_context)

        state["hypotheses"] = hypotheses
        state["hypotheses_count"] = len(hypotheses)

        return state
