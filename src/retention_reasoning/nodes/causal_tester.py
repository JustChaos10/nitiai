"""Causal testing node that validates hypotheses using statistical tests."""

from __future__ import annotations

from typing import Any

import re

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

        # Check if cause is an expression (contains operators) or a simple column name
        is_expression = any(op in hypothesis.cause for op in ['=', '>', '<', ' IN ', ' AND ', ' OR ', 'NOT '])
        
        # For expressions, we'll build the treatment series; for simple columns, check they exist
        if is_expression:
            logger.info(f"Detected expression treatment: {hypothesis.cause}")
            try:
                treatment_series = self._build_treatment_series(hypothesis.cause, data)
            except Exception as e:
                logger.error(f"Failed to parse expression '{hypothesis.cause}': {e}")
                hypothesis.validated = False
                return hypothesis
        else:
            # Simple column name - must exist in data
            if hypothesis.cause not in data.columns:
                logger.warning(f"Treatment variable {hypothesis.cause} not in data")
                hypothesis.validated = False
                return hypothesis
            
            # Get the treatment series
            treatment_series = data[hypothesis.cause]
            
            # If treatment is continuous numeric, try to binarize it at median
            if treatment_series.dtype in ['int64', 'float64'] and treatment_series.nunique() > 10:
                logger.info(f"Binarizing continuous treatment '{hypothesis.cause}' at median")
                median_val = treatment_series.median()
                treatment_series = (treatment_series >= median_val).astype(int)

        # Check outcome variable exists
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

            except Exception as e:
                logger.error(f"Failed to run {test_method.value}: {e}")
                continue

        # If no test methods specified, default to t-test or regression
        if not test_results:
            logger.info("No test methods specified, running simple t-test")
            confounder_cols = [c for c in hypothesis.confounders if c in data.columns]
            if confounder_cols:
                # Regression with confounders
                result = self.statistical_tests.regression_adjustment(
                    treatment=treatment_series,
                    outcome=data[hypothesis.effect],
                    controls=data[confounder_cols],
                    hypothesis_id=hypothesis.hypothesis_id,
                )
            else:
                # Simple t-test without confounders
                result = self.statistical_tests.simple_ttest(
                    treatment=treatment_series,
                    outcome=data[hypothesis.effect],
                    hypothesis_id=hypothesis.hypothesis_id,
                )
            test_results.append(result)

        # Meta-analysis across tests
        if test_results:
            meta_results = self.statistical_tests.meta_analysis(test_results)
            hypothesis.validated = meta_results["consensus_causal"]
            hypothesis.test_results = test_results
            hypothesis.consensus = meta_results

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

    def _build_treatment_series(self, expression: str, data: pd.DataFrame) -> pd.Series:
        """Parse a logical treatment expression into a boolean series."""

        parser = _ExpressionParser(expression, data)
        return parser.parse().astype(int)

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

        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
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


class _ExpressionParser:
    """Parser for logical treatment expressions."""

    def __init__(self, expression: str, data: pd.DataFrame):
        """Initialize parser.
        
        Args:
            expression: Logical expression string (e.g., 'cat = "a" OR cat = "b"')
            data: DataFrame to evaluate against
        """
        self.expression = expression.strip()
        self.data = data

    def parse(self) -> pd.Series:
        """Parse the expression and return a boolean series.
        
        Returns:
            Boolean series representing the parsed expression
        """
        # Handle NOT operator first
        if self.expression.upper().startswith('NOT '):
            inner_expr = self.expression[4:].strip()
            inner_parser = _ExpressionParser(inner_expr, self.data)
            return ~inner_parser.parse()
        
        # Handle IN operator before parentheses (to avoid confusing IN's parentheses)
        if ' IN ' in self.expression.upper():
            return self._parse_in()
        
        # Handle parentheses
        if '(' in self.expression:
            return self._parse_with_parentheses()
        
        # Handle OR operator
        if ' OR ' in self.expression.upper():
            return self._parse_or()
        
        # Handle AND operator
        if ' AND ' in self.expression.upper():
            return self._parse_and()
        
        # Handle simple comparison
        return self._parse_comparison()
    
    def _parse_with_parentheses(self) -> pd.Series:
        """Handle expressions with parentheses."""
        # Find matching parentheses
        paren_start = self.expression.index('(')
        paren_count = 0
        paren_end = -1
        
        for i, char in enumerate(self.expression[paren_start:], start=paren_start):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count == 0:
                    paren_end = i
                    break
        
        # Extract inner expression
        inner_expr = self.expression[paren_start + 1:paren_end]
        inner_parser = _ExpressionParser(inner_expr, self.data)
        inner_result = inner_parser.parse()
        
        # Check if there's more expression after the parentheses
        remaining = self.expression[paren_end + 1:].strip()
        if not remaining:
            return inner_result
        
        # Handle AND/OR after parentheses (with or without leading space)
        remaining_upper = remaining.upper()
        if remaining_upper.startswith(' AND '):
            right_expr = remaining[5:].strip()
            right_parser = _ExpressionParser(right_expr, self.data)
            return inner_result & right_parser.parse()
        elif remaining_upper.startswith(' OR '):
            right_expr = remaining[4:].strip()
            right_parser = _ExpressionParser(right_expr, self.data)
            return inner_result | right_parser.parse()
        elif remaining_upper.startswith('AND '):
            right_expr = remaining[4:].strip()
            right_parser = _ExpressionParser(right_expr, self.data)
            return inner_result & right_parser.parse()
        elif remaining_upper.startswith('OR '):
            right_expr = remaining[3:].strip()
            right_parser = _ExpressionParser(right_expr, self.data)
            return inner_result | right_parser.parse()
        
        return inner_result
    
    def _parse_or(self) -> pd.Series:
        """Handle OR operator."""
        # Split on OR (case insensitive)
        parts = re.split(r'\s+OR\s+', self.expression, flags=re.IGNORECASE)
        result = pd.Series([False] * len(self.data), index=self.data.index)
        
        for part in parts:
            parser = _ExpressionParser(part.strip(), self.data)
            result = result | parser.parse()
        
        return result
    
    def _parse_and(self) -> pd.Series:
        """Handle AND operator."""
        # Split on AND (case insensitive)
        parts = re.split(r'\s+AND\s+', self.expression, flags=re.IGNORECASE)
        result = pd.Series([True] * len(self.data), index=self.data.index)
        
        for part in parts:
            parser = _ExpressionParser(part.strip(), self.data)
            result = result & parser.parse()
        
        return result
    
    def _parse_in(self) -> pd.Series:
        """Handle IN operator (e.g., 'cat IN ("a","c")')."""
        match = re.match(r'(\w+)\s+IN\s+\((.+)\)', self.expression, re.IGNORECASE)
        if not match:
            raise ValueError(f"Invalid IN expression: {self.expression}")
        
        column = match.group(1)
        values_str = match.group(2)
        
        # Parse values
        values = [v.strip().strip('"').strip("'") for v in values_str.split(',')]
        
        if column not in self.data.columns:
            return pd.Series([False] * len(self.data), index=self.data.index)
        
        return self.data[column].isin(values)
    
    def _parse_comparison(self) -> pd.Series:
        """Handle simple comparison (e.g., 'cat = "a"', 'val > 1')."""
        # Match comparison operators
        match = re.match(r'(\w+)\s*(=|!=|>|<|>=|<=)\s*(.+)', self.expression)
        if not match:
            raise ValueError(f"Invalid comparison: {self.expression}")
        
        column = match.group(1)
        operator = match.group(2)
        value_str = match.group(3).strip().strip('"').strip("'")
        
        if column not in self.data.columns:
            return pd.Series([False] * len(self.data), index=self.data.index)
        
        # Try to convert value to numeric if possible
        try:
            value = float(value_str)
        except ValueError:
            value = value_str
        
        # Apply comparison
        if operator == '=':
            return self.data[column] == value
        elif operator == '!=':
            return self.data[column] != value
        elif operator == '>':
            return self.data[column] > value
        elif operator == '<':
            return self.data[column] < value
        elif operator == '>=':
            return self.data[column] >= value
        elif operator == '<=':
            return self.data[column] <= value
        
        return pd.Series([False] * len(self.data), index=self.data.index)
