"""Causal testing node that validates hypotheses using statistical tests."""

import re
from typing import Any

import pandas as pd
from loguru import logger

from ..models.hypothesis import Hypothesis, TestMethod
from ..utils.statistical_tests import StatisticalTests


class CausalTesterNode:
    """Tests causal hypotheses using statistical methods."""

    _column_guess_pattern = re.compile(r"(?P<column>[A-Za-z_][A-Za-z0-9_]*)")

    def _extract_column_name(self, expression: str) -> str | None:
        """Extract a plausible column name from a human-readable description."""
        match = self._column_guess_pattern.match(expression.strip())
        return match.group("column") if match else None

    def _build_treatment_series(self, expression: str, data: pd.DataFrame) -> pd.Series | None:
        """Build a treatment series from an expression or column name."""
        expr = expression.strip()

        # Strip wrapping parentheses
        if expr.startswith("(") and expr.endswith(")"):
            return self._build_treatment_series(expr[1:-1], data)

        # Handle simple NOT prefix
        if expr.lower().startswith("not "):
            inner = expr[4:].strip()
            inner_series = self._build_treatment_series(inner, data)
            if inner_series is not None:
                return (1 - inner_series.astype(int)).astype(int)
            return None

        # Handle simple OR combinations like "col = a OR col = b"
        parts = self._split_top_level(expr, "or")
        if len(parts) > 1:
            series_list = []
            for part in parts:
                built = self._build_treatment_series(part.strip(), data)
                if built is not None:
                    series_list.append(built.astype(int))
            if not series_list:
                return None
            combined = series_list[0]
            for s in series_list[1:]:
                combined = ((combined.astype(int)) | (s.astype(int))).astype(int)
            return combined

        # Handle simple AND combinations like "col = a AND col2 > 3"
        parts = self._split_top_level(expr, "and")
        if len(parts) > 1:
            series_list = []
            for part in parts:
                built = self._build_treatment_series(part.strip(), data)
                if built is not None:
                    series_list.append(built.astype(int))
            if not series_list:
                return None
            combined = series_list[0]
            for s in series_list[1:]:
                combined = ((combined.astype(int)) & (s.astype(int))).astype(int)
            return combined

        return self._build_single_treatment_series(expr, data)

    def _split_top_level(self, expr: str, op: str) -> list[str]:
        """Split expression by top-level op (and/or) respecting parentheses."""
        parts = []
        depth = 0
        buf = []
        lower = expr
        op_lower = op.lower()
        i = 0
        while i < len(lower):
            ch = lower[i]
            if ch == "(":
                depth += 1
                buf.append(expr[i])
                i += 1
                continue
            if ch == ")":
                depth = max(depth - 1, 0)
                buf.append(expr[i])
                i += 1
                continue
            if depth == 0 and lower[i : i + len(op_lower) + 2].lower().startswith(f" {op_lower} "):
                parts.append("".join(buf).strip())
                buf = []
                i += len(op_lower) + 2
                continue
            buf.append(expr[i])
            i += 1
        if buf:
            parts.append("".join(buf).strip())
        return [p for p in parts if p]

    def _build_single_treatment_series(self, expression: str, data: pd.DataFrame) -> pd.Series | None:
        """Handle a single comparison or column reference."""
        expr = expression.strip()

        # Simple column reference
        if expr in data.columns:
            return data[expr]

        # Handle IN lists: col IN (a,b) or col IN ["a","b"]
        in_match = re.match(
            r"(?P<col>[A-Za-z_][A-Za-z0-9_]*)\s+in\s+\((?P<vals>.+)\)", expr, flags=re.IGNORECASE
        ) or re.match(
            r"(?P<col>[A-Za-z_][A-Za-z0-9_]*)\s+in\s+\[(?P<vals>.+)\]", expr, flags=re.IGNORECASE
        )
        if in_match:
            col = in_match.group("col")
            if col not in data.columns:
                return None
            raw_vals = in_match.group("vals")
            parts = [v.strip().strip("'").strip('"') for v in raw_vals.split(",")]
            return data[col].isin(parts).astype(int)

        # Try to parse comparison: col OP value
        comparison = re.match(
            r"(?P<col>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<op>>=|<=|>|<|=)\s*(?P<val>.+)",
            expr,
        )
        if comparison:
            col = comparison.group("col")
            op = comparison.group("op")
            raw_val = comparison.group("val").strip().strip('"').strip("'")

            if col not in data.columns:
                return None

            series = data[col]
            # Try to coerce numeric value
            try:
                val: Any = float(raw_val)
            except Exception:
                val = raw_val

            if op == ">":
                return (series > val).astype(int)
            if op == "<":
                return (series < val).astype(int)
            if op == ">=":
                return (series >= val).astype(int)
            if op == "<=":
                return (series <= val).astype(int)
            if op == "=":
                return (series == val).astype(int)

        # Fallback: try to extract column name and return it if present
        col = self._extract_column_name(expr)
        if col and col in data.columns:
            return data[col]

        return None

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
        treatment_series = data.get(hypothesis.cause)
        if treatment_series is None:
            # Try to parse expressions like "order_value < 100" or "product_category = 'electronics'"
            treatment_series = self._build_treatment_series(hypothesis.cause, data)
        if treatment_series is None:
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
                        treatment=treatment_series,
                        outcome=data[hypothesis.effect],
                        hypothesis_id=hypothesis.hypothesis_id,
                    )
                    test_results.append(result)

                elif test_method == TestMethod.PROPENSITY_MATCHING:
                    confounder_cols = [c for c in hypothesis.confounders if c in data.columns]
                    if confounder_cols:
                        result = self.statistical_tests.propensity_score_matching(
                            treatment=treatment_series,
                            outcome=data[hypothesis.effect],
                            confounders=data[confounder_cols],
                            hypothesis_id=hypothesis.hypothesis_id,
                        )
                        test_results.append(result)

                elif test_method == TestMethod.REGRESSION_ADJUSTMENT:
                    confounder_cols = [c for c in hypothesis.confounders if c in data.columns]
                    if confounder_cols:
                        result = self.statistical_tests.regression_adjustment(
                            treatment=treatment_series,
                            outcome=data[hypothesis.effect],
                            controls=data[confounder_cols],
                            hypothesis_id=hypothesis.hypothesis_id,
                        )
                        test_results.append(result)

                elif test_method == TestMethod.INSTRUMENTAL_VARIABLES:
                    instrument_cols = [c for c in hypothesis.confounders if c in data.columns]
                    control_cols = [c for c in hypothesis.mediators if c in data.columns]
                    result = self.statistical_tests.instrumental_variables(
                        treatment=treatment_series,
                        outcome=data[hypothesis.effect],
                        instruments=data[instrument_cols] if instrument_cols else None,
                        controls=data[control_cols] if control_cols else None,
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
                    treatment=treatment_series,
                    outcome=data[hypothesis.effect],
                    controls=data[confounder_cols],
                    hypothesis_id=hypothesis.hypothesis_id,
                )
                test_results.append(result)

        # Drop unusable results (e.g., failed fits with no effect size)
        valid_results = [r for r in test_results if r.effect_size is not None]

        # Meta-analysis across tests (or fallback)
        if not valid_results:
            fallback = self.statistical_tests.basic_correlation_test(
                treatment=treatment_series,
                outcome=data[hypothesis.effect],
                hypothesis_id=hypothesis.hypothesis_id,
            )
            hypothesis.test_results = [fallback]
            hypothesis.validated = fallback.is_significant
            if not fallback.is_significant:
                logger.warning(
                    f"No valid test results for hypothesis {hypothesis.hypothesis_id} "
                    "including fallback correlation test"
                )
        else:
            meta_results = self.statistical_tests.meta_analysis(valid_results)
            hypothesis.validated = meta_results["consensus_causal"]
            hypothesis.test_results = valid_results

            logger.info(
                f"Hypothesis {hypothesis.hypothesis_id}: "
                f"validated={hypothesis.validated}, "
                f"effect_size={meta_results['effect_size']:.3f}"
            )

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

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node function (async)."""
        hypotheses = state.get("hypotheses", [])
        data = state.get("data")

        if data is None or data.empty:
            logger.error("No data provided for hypothesis testing")
            state["validated_hypotheses"] = []
            return state

        tested_hypotheses = await self.test_all_hypotheses(hypotheses, data)

        # Separate validated and non-validated
        validated = [h for h in tested_hypotheses if h.validated]
        state["hypotheses"] = tested_hypotheses
        state["validated_hypotheses"] = validated
        state["validated_count"] = len(validated)

        logger.info(
            f"Tested {len(hypotheses)} hypotheses, {len(validated)} validated"
        )

        return state
