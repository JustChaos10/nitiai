"""Causal testing node that validates hypotheses using statistical tests."""

from typing import Any

import pandas as pd
from loguru import logger

from ..models.hypothesis import Hypothesis, TestMethod
from ..utils.statistical_tests import StatisticalTests


class CausalTesterNode:
    """Tests causal hypotheses using statistical methods."""

    def __init__(self, data_loader: Any = None):
        """Initialize causal tester.

        Args:
            data_loader: Optional data loader for BigQuery access
        """
        self.statistical_tests = StatisticalTests()
        self.data_loader = data_loader

    async def test_hypothesis(
        self,
        hypothesis: Hypothesis,
        data: pd.DataFrame,
    ) -> Hypothesis:
        """Test a single hypothesis using multiple methods.

        Args:
            hypothesis: Hypothesis to test
            data: Data for testing

        Returns:
            Hypothesis with test results populated
        """
        logger.info(f"Testing hypothesis: {hypothesis.cause} → {hypothesis.effect}")

        test_results = []

        # Prepare data
        required_cols = [hypothesis.cause, hypothesis.effect] + hypothesis.confounders
        available_cols = [col for col in required_cols if col in data.columns]

        if hypothesis.cause not in data.columns:
            logger.warning(f"Treatment variable {hypothesis.cause} not in data")
            hypothesis.validated = False
            return hypothesis

        if hypothesis.effect not in data.columns:
            logger.warning(f"Outcome variable {hypothesis.effect} not in data")
            hypothesis.validated = False
            return hypothesis

        # Run tests based on specified methods
        for test_method in hypothesis.test_methods:
            try:
                if test_method == TestMethod.GRANGER_CAUSALITY:
                    result = self.statistical_tests.granger_causality(
                        treatment=data[hypothesis.cause],
                        outcome=data[hypothesis.effect],
                        hypothesis_id=hypothesis.hypothesis_id,
                    )
                    test_results.append(result)

                elif test_method == TestMethod.PROPENSITY_MATCHING:
                    confounder_cols = [c for c in hypothesis.confounders if c in data.columns]
                    if confounder_cols:
                        result = self.statistical_tests.propensity_score_matching(
                            treatment=data[hypothesis.cause],
                            outcome=data[hypothesis.effect],
                            confounders=data[confounder_cols],
                            hypothesis_id=hypothesis.hypothesis_id,
                        )
                        test_results.append(result)

                elif test_method == TestMethod.REGRESSION_ADJUSTMENT:
                    confounder_cols = [c for c in hypothesis.confounders if c in data.columns]
                    if confounder_cols:
                        result = self.statistical_tests.regression_adjustment(
                            treatment=data[hypothesis.cause],
                            outcome=data[hypothesis.effect],
                            controls=data[confounder_cols],
                            hypothesis_id=hypothesis.hypothesis_id,
                        )
                        test_results.append(result)

            except Exception as e:
                logger.error(f"Failed to run {test_method.value}: {e}")
                continue

        # If no test methods specified, default to regression
        if not test_results:
            logger.info("No test methods specified, running regression adjustment")
            confounder_cols = [c for c in hypothesis.confounders if c in data.columns]
            if confounder_cols:
                result = self.statistical_tests.regression_adjustment(
                    treatment=data[hypothesis.cause],
                    outcome=data[hypothesis.effect],
                    controls=data[confounder_cols],
                    hypothesis_id=hypothesis.hypothesis_id,
                )
                test_results.append(result)

        # Meta-analysis across tests
        if test_results:
            meta_results = self.statistical_tests.meta_analysis(test_results)
            hypothesis.validated = meta_results["consensus_causal"]
            hypothesis.test_results = test_results

            logger.info(
                f"Hypothesis {hypothesis.hypothesis_id}: "
                f"validated={hypothesis.validated}, "
                f"effect_size={meta_results['effect_size']:.3f}"
            )
        else:
            hypothesis.validated = False
            logger.warning(f"No valid test results for hypothesis {hypothesis.hypothesis_id}")

        return hypothesis

    async def test_all_hypotheses(
        self,
        hypotheses: list[Hypothesis],
        data: pd.DataFrame,
    ) -> list[Hypothesis]:
        """Test all hypotheses.

        Args:
            hypotheses: List of hypotheses to test
            data: Data for testing

        Returns:
            List of tested hypotheses
        """
        tested_hypotheses = []

        for hypothesis in hypotheses:
            tested = await self.test_hypothesis(hypothesis, data)
            tested_hypotheses.append(tested)

        return tested_hypotheses

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node function (sync wrapper).

        Args:
            state: Graph state

        Returns:
            Updated state
        """
        import asyncio

        hypotheses = state.get("hypotheses", [])
        data = state.get("data")

        if not data:
            logger.error("No data provided for hypothesis testing")
            state["validated_hypotheses"] = []
            return state

        tested_hypotheses = asyncio.run(
            self.test_all_hypotheses(hypotheses, data)
        )

        # Separate validated and non-validated
        validated = [h for h in tested_hypotheses if h.validated]
        state["hypotheses"] = tested_hypotheses
        state["validated_hypotheses"] = validated
        state["validated_count"] = len(validated)

        logger.info(
            f"Tested {len(hypotheses)} hypotheses, {len(validated)} validated"
        )

        return state
