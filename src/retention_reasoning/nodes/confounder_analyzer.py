"""Confounder analysis node using causal inference engine."""

import re
from typing import Any

import pandas as pd
from loguru import logger

from ..models.hypothesis import Hypothesis
from ..utils.causal_inference import CausalInferenceEngine


class ConfounderAnalyzerNode:
    """Analyzes confounding structures and builds causal DAGs."""

    _column_guess_pattern = re.compile(r"(?P<column>[A-Za-z_][A-Za-z0-9_]*)")

    def _extract_column_name(self, expression: str, data: pd.DataFrame) -> str | None:
        """Extract a plausible column name from an expression that exists in data."""
        match = self._column_guess_pattern.match(expression.strip())
        if not match:
            return None
        col = match.group("column")
        return col if col in data.columns else None

    def __init__(self):
        """Initialize confounder analyzer."""
        self.causal_engine = CausalInferenceEngine()

    async def analyze_hypothesis(
        self,
        hypothesis: Hypothesis,
        data: pd.DataFrame,
    ) -> Hypothesis:
        """Analyze the causal structure of a validated hypothesis.

        Args:
            hypothesis: Validated hypothesis
            data: Data for analysis

        Returns:
            Hypothesis with causal_structure populated
        """
        if not hypothesis.validated:
            logger.debug(f"Skipping non-validated hypothesis {hypothesis.hypothesis_id}")
            return hypothesis

        logger.info(f"Analyzing causal structure for {hypothesis.cause} → {hypothesis.effect}")

        normalized_cause = self._extract_column_name(hypothesis.cause, data)
        if not normalized_cause:
            logger.warning(
                f"Skipping causal analysis for hypothesis {hypothesis.hypothesis_id} because "
                f"cause '{hypothesis.cause}' is not a data column"
            )
            return hypothesis

        if hypothesis.effect not in data.columns:
            logger.warning(
                f"Skipping causal analysis for hypothesis {hypothesis.hypothesis_id} because "
                f"effect '{hypothesis.effect}' is not in data"
            )
            return hypothesis

        hypothesis_for_analysis = hypothesis.model_copy(update={"cause": normalized_cause})

        try:
            # Build causal structure
            causal_structure = self.causal_engine.analyze_causal_structure(
                hypothesis_for_analysis, data
            )

            hypothesis.causal_structure = causal_structure

            logger.info(
                f"Causal structure: direct_effect={causal_structure.direct_effect:.3f}, "
                f"indirect_effect={causal_structure.indirect_effect:.3f}, "
                f"actionable_lever={causal_structure.actionable_lever}"
            )

        except Exception as e:
            logger.error(f"Failed to analyze causal structure: {e}")

        return hypothesis

    async def analyze_all_hypotheses(
        self,
        hypotheses: list[Hypothesis],
        data: pd.DataFrame,
    ) -> list[Hypothesis]:
        """Analyze causal structure for all validated hypotheses.

        Args:
            hypotheses: List of hypotheses
            data: Data for analysis

        Returns:
            List of hypotheses with causal structures
        """
        analyzed_hypotheses = []

        for hypothesis in hypotheses:
            if hypothesis.validated:
                analyzed = await self.analyze_hypothesis(hypothesis, data)
                analyzed_hypotheses.append(analyzed)
            else:
                analyzed_hypotheses.append(hypothesis)

        return analyzed_hypotheses

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node function (async)."""
        validated_hypotheses = state.get("validated_hypotheses", [])
        data = state.get("data")

        if data is None or data.empty:
            logger.error("No data provided for confounder analysis")
            return state

        analyzed_hypotheses = await self.analyze_all_hypotheses(validated_hypotheses, data)

        # Extract validated causes and actionable levers
        validated_causes = []
        actionable_levers = []

        for hypothesis in analyzed_hypotheses:
            if hypothesis.validated and hypothesis.causal_structure:
                validated_causes.append(hypothesis.causal_structure.true_cause)
                actionable_levers.append(hypothesis.causal_structure.actionable_lever)

        state["validated_hypotheses"] = analyzed_hypotheses
        state["validated_causes"] = list(set(validated_causes))
        state["actionable_levers"] = list(set(actionable_levers))

        logger.info(
            f"Identified {len(state['validated_causes'])} validated causes"
        )

        return state
