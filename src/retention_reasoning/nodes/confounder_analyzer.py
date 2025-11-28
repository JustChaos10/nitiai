"""Confounder analysis node using causal inference engine."""

from typing import Any

import pandas as pd
from loguru import logger

from ..models.hypothesis import Hypothesis

# Try to import CausalInferenceEngine, but make it optional
try:
    from ..utils.causal_inference import CausalInferenceEngine
    CAUSAL_ENGINE_AVAILABLE = True
except ImportError:
    CAUSAL_ENGINE_AVAILABLE = False
    logger.warning("CausalInferenceEngine not available (DoWhy not installed). Causal analysis will be skipped.")


class ConfounderAnalyzerNode:
    """Analyzes confounding structures and builds causal DAGs."""

    def __init__(self):
        """Initialize confounder analyzer.
        
        If DoWhy is not installed, the causal engine will be None and
        causal analysis will be skipped gracefully.
        """
        self.causal_engine = None
        if CAUSAL_ENGINE_AVAILABLE:
            try:
                self.causal_engine = CausalInferenceEngine()
            except ImportError as e:
                logger.warning(f"Could not initialize CausalInferenceEngine: {e}")

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

        # Skip causal analysis if engine is not available
        if self.causal_engine is None:
            logger.debug(f"Skipping causal analysis for {hypothesis.hypothesis_id} (DoWhy not available)")
            return hypothesis

        logger.info(f"Analyzing causal structure for {hypothesis.cause} → {hypothesis.effect}")

        try:
            # Build causal structure
            causal_structure = self.causal_engine.analyze_causal_structure(
                hypothesis, data
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

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node function (sync wrapper).

        Args:
            state: Graph state

        Returns:
            Updated state
        """
        import asyncio

        validated_hypotheses = state.get("validated_hypotheses", [])
        data = state.get("data")

        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            logger.error("No data provided for confounder analysis")
            return state

        analyzed_hypotheses = asyncio.run(
            self.analyze_all_hypotheses(validated_hypotheses, data)
        )

        # Extract validated causes and actionable levers
        validated_causes = []
        actionable_levers = []

        for hypothesis in analyzed_hypotheses:
            if hypothesis.validated:
                # Use causal_structure if available, otherwise use hypothesis cause
                if hypothesis.causal_structure:
                    validated_causes.append(hypothesis.causal_structure.true_cause)
                    actionable_levers.append(hypothesis.causal_structure.actionable_lever)
                else:
                    # Fallback when causal analysis was skipped
                    validated_causes.append(hypothesis.cause)
                    actionable_levers.append(hypothesis.cause)

        state["validated_hypotheses"] = analyzed_hypotheses
        state["validated_causes"] = list(set(validated_causes))
        state["actionable_levers"] = list(set(actionable_levers))

        logger.info(
            f"Identified {len(state['validated_causes'])} validated causes"
        )

        return state
