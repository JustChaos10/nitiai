"""Heterogeneous treatment effect estimation - detect different causal patterns in subgroups."""

from __future__ import annotations

from typing import Any, Optional
import numpy as np
import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field


class SubgroupEffect(BaseModel):
    """Effect estimate for a specific subgroup."""

    subgroup_name: str
    subgroup_filter: str
    sample_size: int

    # Effect estimates
    treatment_mean: float
    control_mean: float
    effect_size: float
    relative_effect: float

    # Statistical significance
    p_value: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    significant: bool

    # Metadata
    baseline_prevalence: Optional[float] = None


class HeterogeneityAnalysis(BaseModel):
    """Results of heterogeneous treatment effect analysis."""

    hypothesis_id: str
    treatment_variable: str
    outcome_variable: str

    # Overall effect
    overall_effect: float
    overall_p_value: float

    # Subgroup effects
    subgroup_effects: list[SubgroupEffect] = Field(default_factory=list)

    # Heterogeneity test
    heterogeneity_detected: bool
    heterogeneity_p_value: Optional[float] = None
    heterogeneity_metric: Optional[str] = None

    # Recommendations
    recommended_segments: list[str] = Field(default_factory=list)
    insights: str = ""


class HeterogeneousEffectEstimator:
    """Estimate treatment effects across different subgroups."""

    def __init__(self, min_subgroup_size: int = 50, significance_level: float = 0.05) -> None:
        self.min_subgroup_size = min_subgroup_size
        self.significance_level = significance_level

    def _split_by_feature(
        self,
        data: pd.DataFrame,
        feature: str,
        method: str = "median",
    ) -> dict[str, pd.DataFrame]:
        """Split data into subgroups by feature."""
        if feature not in data.columns:
            logger.warning(f"Feature {feature} not in data")
            return {}

        subgroups = {}

        # Determine split method
        if data[feature].dtype in ["object", "category", "bool"]:
            # Categorical: split by unique values
            for value in data[feature].unique():
                if pd.notna(value):
                    mask = data[feature] == value
                    subgroup = data[mask]
                    if len(subgroup) >= self.min_subgroup_size:
                        subgroups[f"{feature}={value}"] = subgroup
        else:
            # Numerical: split by median or tertiles
            if method == "median":
                median_val = data[feature].median()
                subgroups[f"{feature} < {median_val:.2f}"] = data[data[feature] < median_val]
                subgroups[f"{feature} >= {median_val:.2f}"] = data[data[feature] >= median_val]
            elif method == "tertiles":
                tertiles = data[feature].quantile([1/3, 2/3])
                subgroups[f"{feature} < {tertiles.iloc[0]:.2f}"] = data[data[feature] < tertiles.iloc[0]]
                subgroups[f"{tertiles.iloc[0]:.2f} <= {feature} < {tertiles.iloc[1]:.2f}"] = data[
                    (data[feature] >= tertiles.iloc[0]) & (data[feature] < tertiles.iloc[1])
                ]
                subgroups[f"{feature} >= {tertiles.iloc[1]:.2f}"] = data[data[feature] >= tertiles.iloc[1]]

        # Filter by min size
        return {k: v for k, v in subgroups.items() if len(v) >= self.min_subgroup_size}

    def _estimate_subgroup_effect(
        self,
        subgroup: pd.DataFrame,
        treatment_col: str,
        outcome_col: str,
        subgroup_name: str,
    ) -> Optional[SubgroupEffect]:
        """Estimate treatment effect within a subgroup."""
        try:
            # Split into treatment and control
            treated = subgroup[subgroup[treatment_col] == 1]
            control = subgroup[subgroup[treatment_col] == 0]

            if len(treated) < 10 or len(control) < 10:
                logger.debug(f"Insufficient samples in subgroup {subgroup_name}")
                return None

            # Calculate means
            treatment_mean = treated[outcome_col].mean()
            control_mean = control[outcome_col].mean()
            effect = treatment_mean - control_mean

            # Calculate relative effect
            relative_effect = (effect / control_mean) if control_mean != 0 else 0.0

            # Statistical test (t-test)
            from scipy.stats import ttest_ind

            t_stat, p_value = ttest_ind(
                treated[outcome_col].dropna(),
                control[outcome_col].dropna(),
                equal_var=False,
            )

            # Confidence interval (95%)
            from scipy.stats import sem

            se_treated = sem(treated[outcome_col].dropna())
            se_control = sem(control[outcome_col].dropna())
            se_diff = np.sqrt(se_treated**2 + se_control**2)

            ci_lower = effect - 1.96 * se_diff
            ci_upper = effect + 1.96 * se_diff

            return SubgroupEffect(
                subgroup_name=subgroup_name,
                subgroup_filter=subgroup_name,  # Simplified
                sample_size=len(subgroup),
                treatment_mean=float(treatment_mean),
                control_mean=float(control_mean),
                effect_size=float(effect),
                relative_effect=float(relative_effect),
                p_value=float(p_value),
                confidence_interval_lower=float(ci_lower),
                confidence_interval_upper=float(ci_upper),
                significant=(p_value < self.significance_level),
                baseline_prevalence=float(control_mean),
            )

        except Exception as exc:
            logger.warning(f"Failed to estimate effect for subgroup {subgroup_name}: {exc}")
            return None

    def _test_heterogeneity(self, subgroup_effects: list[SubgroupEffect]) -> tuple[bool, float]:
        """Test if treatment effects differ significantly across subgroups.

        Uses Cochran's Q test for heterogeneity.
        """
        if len(subgroup_effects) < 2:
            return False, 1.0

        try:
            # Extract effect sizes and variances
            effects = np.array([s.effect_size for s in subgroup_effects])
            variances = np.array([
                ((s.confidence_interval_upper - s.confidence_interval_lower) / (2 * 1.96)) ** 2
                for s in subgroup_effects
            ])

            # Weighted mean effect
            weights = 1 / variances
            weighted_mean = np.sum(weights * effects) / np.sum(weights)

            # Q statistic
            Q = np.sum(weights * (effects - weighted_mean) ** 2)

            # Chi-square test
            from scipy.stats import chi2

            df = len(effects) - 1
            p_value = 1 - chi2.cdf(Q, df)

            heterogeneity_detected = p_value < self.significance_level

            return heterogeneity_detected, float(p_value)

        except Exception as exc:
            logger.warning(f"Heterogeneity test failed: {exc}")
            return False, 1.0

    def analyze_heterogeneity(
        self,
        data: pd.DataFrame,
        treatment_col: str,
        outcome_col: str,
        subgroup_features: list[str],
        hypothesis_id: str = "unknown",
    ) -> HeterogeneityAnalysis:
        """Analyze treatment effect heterogeneity across multiple features.

        Args:
            data: DataFrame with treatment, outcome, and features
            treatment_col: Name of treatment variable (binary)
            outcome_col: Name of outcome variable
            subgroup_features: List of features to split by
            hypothesis_id: ID of the hypothesis being tested

        Returns:
            HeterogeneityAnalysis with subgroup effects and recommendations
        """
        # Calculate overall effect
        treated = data[data[treatment_col] == 1]
        control = data[data[treatment_col] == 0]
        overall_effect = treated[outcome_col].mean() - control[outcome_col].mean()

        from scipy.stats import ttest_ind
        _, overall_p = ttest_ind(
            treated[outcome_col].dropna(),
            control[outcome_col].dropna(),
            equal_var=False,
        )

        # Analyze subgroups
        all_subgroup_effects = []

        for feature in subgroup_features:
            if feature not in data.columns:
                logger.warning(f"Feature {feature} not in data, skipping")
                continue

            subgroups = self._split_by_feature(data, feature, method="median")

            for subgroup_name, subgroup_data in subgroups.items():
                effect = self._estimate_subgroup_effect(
                    subgroup_data,
                    treatment_col,
                    outcome_col,
                    subgroup_name,
                )
                if effect is not None:
                    all_subgroup_effects.append(effect)

        # Test for heterogeneity
        heterogeneity_detected, heterogeneity_p = self._test_heterogeneity(all_subgroup_effects)

        # Identify recommended segments (subgroups with strongest effects)
        significant_effects = [e for e in all_subgroup_effects if e.significant]
        significant_effects.sort(key=lambda e: abs(e.effect_size), reverse=True)

        recommended_segments = [e.subgroup_name for e in significant_effects[:3]]

        # Generate insights
        insights = self._generate_insights(
            overall_effect,
            all_subgroup_effects,
            heterogeneity_detected,
        )

        return HeterogeneityAnalysis(
            hypothesis_id=hypothesis_id,
            treatment_variable=treatment_col,
            outcome_variable=outcome_col,
            overall_effect=float(overall_effect),
            overall_p_value=float(overall_p),
            subgroup_effects=all_subgroup_effects,
            heterogeneity_detected=heterogeneity_detected,
            heterogeneity_p_value=heterogeneity_p,
            heterogeneity_metric="Cochran's Q",
            recommended_segments=recommended_segments,
            insights=insights,
        )

    def _generate_insights(
        self,
        overall_effect: float,
        subgroup_effects: list[SubgroupEffect],
        heterogeneity_detected: bool,
    ) -> str:
        """Generate human-readable insights from heterogeneity analysis."""
        if not subgroup_effects:
            return "Insufficient data to detect heterogeneous effects."

        insights = []

        if heterogeneity_detected:
            insights.append("✓ **Heterogeneity detected**: Treatment effect varies significantly across subgroups.")

            # Find strongest and weakest effects
            sorted_effects = sorted(subgroup_effects, key=lambda e: e.effect_size, reverse=True)
            strongest = sorted_effects[0]
            weakest = sorted_effects[-1]

            insights.append(
                f"\n**Strongest effect**: {strongest.subgroup_name} "
                f"(effect = {strongest.effect_size:.3f}, p = {strongest.p_value:.3f})"
            )
            insights.append(
                f"**Weakest effect**: {weakest.subgroup_name} "
                f"(effect = {weakest.effect_size:.3f}, p = {weakest.p_value:.3f})"
            )

            # Recommendation
            insights.append(
                f"\n**Recommendation**: Target intervention to high-impact segments like '{strongest.subgroup_name}' "
                f"to maximize ROI."
            )
        else:
            insights.append(
                "✗ **No significant heterogeneity detected**: Treatment effect is consistent across subgroups."
            )
            insights.append(
                "\n**Recommendation**: Broad targeting strategy is appropriate; no need for complex segmentation."
            )

        # Summary stats
        significant_count = sum(1 for e in subgroup_effects if e.significant)
        insights.append(
            f"\n**Summary**: {significant_count}/{len(subgroup_effects)} subgroups show significant effects."
        )

        return "\n".join(insights)
