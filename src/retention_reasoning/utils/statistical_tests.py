"""Statistical testing utilities for causal inference."""

import warnings
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.stattools import grangercausalitytests

from ..models.hypothesis import Confidence, TestMethod, TestResult


class StatisticalTests:
    """Implements various causal inference statistical tests."""

    def __init__(self, significance_level: float = 0.05):
        """Initialize statistical tests.

        Args:
            significance_level: Significance level for hypothesis testing (default: 0.05)
        """
        self.significance_level = significance_level

    def granger_causality(
        self,
        treatment: pd.Series,
        outcome: pd.Series,
        hypothesis_id: str,
        max_lag: int = 7,
    ) -> TestResult:
        """Test Granger causality: does treatment temporally precede outcome?

        Args:
            treatment: Treatment variable time series
            outcome: Outcome variable time series
            hypothesis_id: ID of hypothesis being tested
            max_lag: Maximum number of lags to test

        Returns:
            TestResult with Granger causality test results
        """
        try:
            # Prepare data
            data = pd.DataFrame({"treatment": treatment, "outcome": outcome}).dropna()

            if len(data) < max_lag * 2:
                return TestResult(
                    hypothesis_id=hypothesis_id,
                    method=TestMethod.GRANGER_CAUSALITY,
                    is_significant=False,
                    confidence=Confidence.LOW,
                    warnings=[f"Insufficient data: {len(data)} samples < {max_lag * 2} required"],
                )

            # Run Granger causality test
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                results = grangercausalitytests(data[["outcome", "treatment"]], max_lag, verbose=False)

            # Extract minimum p-value across lags
            p_values = [results[lag][0]["ssr_ftest"][1] for lag in range(1, max_lag + 1)]
            min_p_value = min(p_values)
            best_lag = p_values.index(min_p_value) + 1

            is_significant = min_p_value < self.significance_level

            # Estimate effect size using correlation
            corr = data["treatment"].shift(best_lag).corr(data["outcome"])
            effect_size = abs(corr) if not np.isnan(corr) else 0.0

            confidence = self._determine_confidence(min_p_value, len(data), effect_size)

            return TestResult(
                hypothesis_id=hypothesis_id,
                method=TestMethod.GRANGER_CAUSALITY,
                is_significant=is_significant,
                p_value=min_p_value,
                effect_size=effect_size,
                effect_direction="positive" if corr > 0 else "negative" if corr < 0 else "none",
                confidence=confidence,
                sample_size=len(data),
                test_statistics={
                    "best_lag": best_lag,
                    "p_values_by_lag": {f"lag_{i+1}": p for i, p in enumerate(p_values)},
                },
            )

        except Exception as e:
            return TestResult(
                hypothesis_id=hypothesis_id,
                method=TestMethod.GRANGER_CAUSALITY,
                is_significant=False,
                confidence=Confidence.LOW,
                warnings=[f"Test failed: {str(e)}"],
            )

    def propensity_score_matching(
        self,
        treatment: pd.Series,
        outcome: pd.Series,
        confounders: pd.DataFrame,
        hypothesis_id: str,
        n_neighbors: int = 5,
    ) -> TestResult:
        """Test causal effect using propensity score matching.

        Args:
            treatment: Binary treatment variable
            outcome: Outcome variable
            confounders: DataFrame of confounding variables
            hypothesis_id: ID of hypothesis being tested
            n_neighbors: Number of neighbors for matching

        Returns:
            TestResult with propensity matching results
        """
        try:
            # Prepare data
            data = pd.DataFrame(
                {
                    "treatment": treatment,
                    "outcome": outcome,
                }
            )
            data = pd.concat([data, confounders], axis=1).dropna()

            if len(data) < 50:
                return TestResult(
                    hypothesis_id=hypothesis_id,
                    method=TestMethod.PROPENSITY_MATCHING,
                    is_significant=False,
                    confidence=Confidence.LOW,
                    warnings=["Insufficient sample size for matching (< 50)"],
                )

            # Estimate propensity scores
            X = data[confounders.columns]
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            ps_model = LogisticRegression(max_iter=1000)
            ps_model.fit(X_scaled, data["treatment"])
            propensity_scores = ps_model.predict_proba(X_scaled)[:, 1]

            # Match treated to control units
            treated_idx = data["treatment"] == 1
            control_idx = data["treatment"] == 0

            if treated_idx.sum() < 10 or control_idx.sum() < 10:
                return TestResult(
                    hypothesis_id=hypothesis_id,
                    method=TestMethod.PROPENSITY_MATCHING,
                    is_significant=False,
                    confidence=Confidence.LOW,
                    warnings=["Too few treated or control units"],
                )

            # Find nearest neighbors
            treated_ps = propensity_scores[treated_idx].reshape(-1, 1)
            control_ps = propensity_scores[control_idx].reshape(-1, 1)

            nn = NearestNeighbors(n_neighbors=min(n_neighbors, len(control_ps)))
            nn.fit(control_ps)
            distances, indices = nn.kneighbors(treated_ps)

            # Calculate ATE (Average Treatment Effect)
            treated_outcomes = data.loc[treated_idx, "outcome"].values
            control_outcomes = data.loc[control_idx, "outcome"].values[indices]
            matched_control_outcomes = control_outcomes.mean(axis=1)

            ate = (treated_outcomes - matched_control_outcomes).mean()
            ate_se = (treated_outcomes - matched_control_outcomes).std() / np.sqrt(len(treated_outcomes))

            # Statistical test
            t_stat = ate / ate_se if ate_se > 0 else 0
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=len(treated_outcomes) - 1))
            is_significant = p_value < self.significance_level

            # Effect size (Cohen's d)
            pooled_std = np.sqrt(
                (treated_outcomes.var() + matched_control_outcomes.var()) / 2
            )
            effect_size = ate / pooled_std if pooled_std > 0 else 0

            # Covariate balance (lower is better, < 0.1 is good)
            balance_score = self._calculate_balance(
                data.loc[treated_idx, confounders.columns],
                data.loc[control_idx, confounders.columns],
            )

            confidence = self._determine_confidence(p_value, len(treated_outcomes), abs(effect_size))

            return TestResult(
                hypothesis_id=hypothesis_id,
                method=TestMethod.PROPENSITY_MATCHING,
                is_significant=is_significant,
                p_value=p_value,
                effect_size=abs(effect_size),
                effect_direction="positive" if ate > 0 else "negative" if ate < 0 else "none",
                point_estimate=ate,
                standard_error=ate_se,
                confidence_interval=(ate - 1.96 * ate_se, ate + 1.96 * ate_se),
                confidence=confidence,
                sample_size=len(treated_outcomes),
                balance_score=balance_score,
                test_statistics={
                    "ate": ate,
                    "t_statistic": t_stat,
                    "n_treated": len(treated_outcomes),
                    "n_control": len(control_outcomes),
                    "avg_match_distance": distances.mean(),
                },
                warnings=["Balance score high (> 0.2), results may be biased"] if balance_score > 0.2 else [],
            )

        except Exception as e:
            return TestResult(
                hypothesis_id=hypothesis_id,
                method=TestMethod.PROPENSITY_MATCHING,
                is_significant=False,
                confidence=Confidence.LOW,
                warnings=[f"Test failed: {str(e)}"],
            )

    def regression_adjustment(
        self,
        treatment: pd.Series,
        outcome: pd.Series,
        controls: pd.DataFrame,
        hypothesis_id: str,
    ) -> TestResult:
        """Test causal effect using regression adjustment.

        Args:
            treatment: Treatment variable
            outcome: Outcome variable
            controls: DataFrame of control variables
            hypothesis_id: ID of hypothesis being tested

        Returns:
            TestResult with regression results
        """
        try:
            from sklearn.linear_model import LinearRegression

            # Prepare data
            data = pd.DataFrame(
                {
                    "treatment": treatment,
                    "outcome": outcome,
                }
            )
            data = pd.concat([data, controls], axis=1).dropna()

            if len(data) < 30:
                return TestResult(
                    hypothesis_id=hypothesis_id,
                    method=TestMethod.REGRESSION_ADJUSTMENT,
                    is_significant=False,
                    confidence=Confidence.LOW,
                    warnings=["Insufficient sample size for regression (< 30)"],
                )

            # Fit regression model
            X = data[["treatment"] + list(controls.columns)]
            y = data["outcome"]

            model = LinearRegression()
            model.fit(X, y)

            # Extract treatment coefficient
            treatment_coef = model.coef_[0]

            # Bootstrap for standard errors
            n_bootstrap = 1000
            bootstrap_coefs = []
            for _ in range(n_bootstrap):
                indices = np.random.choice(len(data), size=len(data), replace=True)
                X_boot = X.iloc[indices]
                y_boot = y.iloc[indices]
                boot_model = LinearRegression()
                boot_model.fit(X_boot, y_boot)
                bootstrap_coefs.append(boot_model.coef_[0])

            treatment_se = np.std(bootstrap_coefs)
            t_stat = treatment_coef / treatment_se if treatment_se > 0 else 0
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=len(data) - X.shape[1] - 1))

            is_significant = p_value < self.significance_level

            # Effect size
            outcome_std = y.std()
            effect_size = abs(treatment_coef / outcome_std) if outcome_std > 0 else 0

            confidence = self._determine_confidence(p_value, len(data), effect_size)

            return TestResult(
                hypothesis_id=hypothesis_id,
                method=TestMethod.REGRESSION_ADJUSTMENT,
                is_significant=is_significant,
                p_value=p_value,
                effect_size=effect_size,
                effect_direction="positive" if treatment_coef > 0 else "negative",
                point_estimate=treatment_coef,
                standard_error=treatment_se,
                confidence_interval=(
                    treatment_coef - 1.96 * treatment_se,
                    treatment_coef + 1.96 * treatment_se,
                ),
                confidence=confidence,
                sample_size=len(data),
                test_statistics={
                    "t_statistic": t_stat,
                    "r_squared": model.score(X, y),
                    "n_controls": len(controls.columns),
                },
            )

        except Exception as e:
            return TestResult(
                hypothesis_id=hypothesis_id,
                method=TestMethod.REGRESSION_ADJUSTMENT,
                is_significant=False,
                confidence=Confidence.LOW,
                warnings=[f"Test failed: {str(e)}"],
            )

    def _calculate_balance(self, treated: pd.DataFrame, control: pd.DataFrame) -> float:
        """Calculate covariate balance (standardized mean difference).

        Args:
            treated: Treated group covariates
            control: Control group covariates

        Returns:
            Average standardized mean difference (0-1, lower is better)
        """
        smd_values = []
        for col in treated.columns:
            mean_diff = abs(treated[col].mean() - control[col].mean())
            pooled_std = np.sqrt((treated[col].var() + control[col].var()) / 2)
            if pooled_std > 0:
                smd = mean_diff / pooled_std
                smd_values.append(smd)

        return np.mean(smd_values) if smd_values else 1.0

    def _determine_confidence(
        self, p_value: float, sample_size: int, effect_size: float
    ) -> Confidence:
        """Determine confidence level based on p-value, sample size, and effect size.

        Args:
            p_value: P-value from test
            sample_size: Sample size
            effect_size: Standardized effect size

        Returns:
            Confidence level (low, medium, high)
        """
        if p_value > 0.05 or sample_size < 30:
            return Confidence.LOW
        elif p_value < 0.01 and sample_size >= 100 and effect_size >= 0.5:
            return Confidence.HIGH
        else:
            return Confidence.MEDIUM

    def meta_analysis(self, test_results: list[TestResult]) -> dict[str, Any]:
        """Perform meta-analysis across multiple test methods.

        Args:
            test_results: List of test results from different methods

        Returns:
            Aggregated results with consensus
        """
        if not test_results:
            return {
                "consensus_causal": False,
                "confidence": Confidence.LOW,
                "effect_size": 0.0,
            }

        # Extract effect sizes (weighted by inverse variance if available)
        effect_sizes = []
        weights = []
        for result in test_results:
            if result.effect_size is not None:
                effect_sizes.append(result.effect_size)
                # Weight by inverse of standard error (if available)
                weight = 1 / (result.standard_error ** 2) if result.standard_error else 1.0
                weights.append(weight)

        if not effect_sizes:
            return {
                "consensus_causal": False,
                "confidence": Confidence.LOW,
                "effect_size": 0.0,
            }

        # Weighted average effect size
        weights_arr = np.array(weights)
        weights_normalized = weights_arr / weights_arr.sum()
        pooled_effect_size = np.average(effect_sizes, weights=weights_normalized)

        # Consensus on causality (majority vote weighted by confidence)
        significant_count = sum(1 for r in test_results if r.is_significant)
        consensus_causal = significant_count > len(test_results) / 2

        # Aggregate confidence
        confidence_scores = {
            Confidence.LOW: 0.3,
            Confidence.MEDIUM: 0.6,
            Confidence.HIGH: 0.9,
        }
        avg_confidence_score = np.mean([confidence_scores[r.confidence] for r in test_results])

        if avg_confidence_score >= 0.75:
            consensus_confidence = Confidence.HIGH
        elif avg_confidence_score >= 0.45:
            consensus_confidence = Confidence.MEDIUM
        else:
            consensus_confidence = Confidence.LOW

        # Effect direction
        directions = [r.effect_direction for r in test_results if r.effect_direction]
        consensus_direction = max(set(directions), key=directions.count) if directions else "none"

        return {
            "consensus_causal": consensus_causal,
            "effect_size": pooled_effect_size,
            "confidence": consensus_confidence,
            "effect_direction": consensus_direction,
            "n_tests": len(test_results),
            "n_significant": significant_count,
            "individual_results": [
                {
                    "method": r.method.value,
                    "is_significant": r.is_significant,
                    "p_value": r.p_value,
                    "effect_size": r.effect_size,
                }
                for r in test_results
            ],
        }
