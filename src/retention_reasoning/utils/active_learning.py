"""Active learning module - suggest which data to collect to resolve uncertainty."""

from __future__ import annotations

from typing import Any, Optional
import numpy as np
import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field

from .hypothesis_utils import hypothesis_to_dict


class DataCollectionRecommendation(BaseModel):
    """Recommendation for data to collect."""

    priority: int  # 1 = highest priority
    data_type: str  # "feature", "experiment", "survey", "external_data"
    recommendation: str
    rationale: str
    expected_value: float  # Expected reduction in uncertainty
    estimated_cost: str  # "low", "medium", "high"
    implementation_difficulty: str  # "easy", "medium", "hard"

    # Specifics
    feature_name: Optional[str] = None
    sample_size_needed: Optional[int] = None
    collection_method: Optional[str] = None


class UncertaintyAnalysis(BaseModel):
    """Analysis of uncertainty in causal hypotheses."""

    hypothesis_id: str
    overall_uncertainty: float  # 0-1 scale

    # Sources of uncertainty
    sample_size_uncertainty: float
    measurement_uncertainty: float
    confounding_uncertainty: float
    model_uncertainty: float

    # Recommendations
    recommendations: list[DataCollectionRecommendation] = Field(default_factory=list)
    summary: str = ""


class ActiveLearner:
    """Suggest data collection strategies to reduce uncertainty in causal inference."""

    def __init__(
        self,
        min_sample_size: int = 100,
        target_confidence: float = 0.95,
    ) -> None:
        self.min_sample_size = min_sample_size
        self.target_confidence = target_confidence

    def analyze_uncertainty(
        self,
        hypothesis: dict[str, Any],
        data: pd.DataFrame,
        test_results: Optional[dict] = None,
    ) -> UncertaintyAnalysis:
        """Analyze sources of uncertainty in a hypothesis.

        Args:
            hypothesis: Hypothesis object with cause, effect, confounders
            data: Available data
            test_results: Results from statistical tests (optional)

        Returns:
            UncertaintyAnalysis with recommendations
        """
        hyp_dict = hypothesis_to_dict(hypothesis)
        cause = hyp_dict.get("cause", "unknown")
        effect = hyp_dict.get("effect", "unknown")
        confounders = hyp_dict.get("confounders", [])

        # Calculate different sources of uncertainty
        sample_uncertainty = self._assess_sample_size_uncertainty(data, cause, effect)
        measurement_uncertainty = self._assess_measurement_uncertainty(data, cause, effect)
        confounding_uncertainty = self._assess_confounding_uncertainty(
            data, cause, effect, confounders
        )
        model_uncertainty = self._assess_model_uncertainty(test_results)

        # Overall uncertainty (weighted average)
        overall_uncertainty = (
            0.3 * sample_uncertainty
            + 0.2 * measurement_uncertainty
            + 0.3 * confounding_uncertainty
            + 0.2 * model_uncertainty
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            hyp_dict,
            data,
            sample_uncertainty,
            measurement_uncertainty,
            confounding_uncertainty,
            model_uncertainty,
        )

        # Sort by expected value (descending)
        recommendations.sort(key=lambda r: r.expected_value, reverse=True)

        # Add priority ranks
        for i, rec in enumerate(recommendations):
            rec.priority = i + 1

        # Summary
        summary = self._generate_summary(overall_uncertainty, recommendations)

        return UncertaintyAnalysis(
            hypothesis_id=hyp_dict.get("id")
            or hyp_dict.get("hypothesis_id", "unknown"),
            overall_uncertainty=float(overall_uncertainty),
            sample_size_uncertainty=float(sample_uncertainty),
            measurement_uncertainty=float(measurement_uncertainty),
            confounding_uncertainty=float(confounding_uncertainty),
            model_uncertainty=float(model_uncertainty),
            recommendations=recommendations,
            summary=summary,
        )

    def _assess_sample_size_uncertainty(
        self,
        data: pd.DataFrame,
        cause: str,
        effect: str,
    ) -> float:
        """Assess uncertainty due to small sample size."""
        if cause not in data.columns or effect not in data.columns:
            return 1.0  # Maximum uncertainty

        # Count available samples
        valid_samples = data[[cause, effect]].dropna()
        n = len(valid_samples)

        # Uncertainty decreases with sample size (diminishing returns)
        if n < self.min_sample_size:
            uncertainty = 1.0 - (n / self.min_sample_size)
        else:
            # Asymptotic decay
            uncertainty = 1.0 / np.sqrt(n / self.min_sample_size)

        return min(max(uncertainty, 0.0), 1.0)

    def _assess_measurement_uncertainty(
        self,
        data: pd.DataFrame,
        cause: str,
        effect: str,
    ) -> float:
        """Assess uncertainty due to measurement quality."""
        uncertainty = 0.0

        for var in [cause, effect]:
            if var not in data.columns:
                uncertainty += 0.5
                continue

            # Check for missing data
            missing_pct = data[var].isna().mean()
            uncertainty += missing_pct * 0.3

            # Check for suspicious patterns (all same value, etc.)
            if data[var].nunique() == 1:
                uncertainty += 0.2  # No variation

        return min(max(uncertainty / 2, 0.0), 1.0)

    def _assess_confounding_uncertainty(
        self,
        data: pd.DataFrame,
        cause: str,
        effect: str,
        confounders: list[str],
    ) -> float:
        """Assess uncertainty due to unmeasured confounders."""
        if not confounders:
            # No confounders identified = high uncertainty
            return 0.7

        # Check how many confounders are actually measured
        measured_confounders = [c for c in confounders if c in data.columns]
        coverage = len(measured_confounders) / len(confounders) if confounders else 0

        # Uncertainty is inverse of coverage
        uncertainty = 1.0 - coverage

        return min(max(uncertainty, 0.0), 1.0)

    def _assess_model_uncertainty(self, test_results: Optional[dict]) -> float:
        """Assess uncertainty from statistical test results."""
        if not test_results:
            return 0.5  # Moderate uncertainty if no tests

        # Check for consensus across methods
        if "tests" in test_results:
            tests = test_results["tests"]
            if len(tests) < 2:
                return 0.6  # Only one test = higher uncertainty

            # Check agreement
            significant_count = sum(1 for t in tests if t.get("result") == "significant")
            agreement = significant_count / len(tests)

            # High agreement = low uncertainty
            uncertainty = 1.0 - agreement
            return min(max(uncertainty, 0.0), 1.0)

        return 0.5

    def _generate_recommendations(
        self,
        hypothesis: dict[str, Any],
        data: pd.DataFrame,
        sample_uncertainty: float,
        measurement_uncertainty: float,
        confounding_uncertainty: float,
        model_uncertainty: float,
    ) -> list[DataCollectionRecommendation]:
        """Generate data collection recommendations based on uncertainty sources."""
        recommendations = []

        hyp_dict = hypothesis_to_dict(hypothesis)
        cause = hyp_dict.get("cause", "unknown")
        effect = hyp_dict.get("effect", "unknown")
        confounders = hyp_dict.get("confounders", [])

        # Recommendation 1: Increase sample size
        if sample_uncertainty > 0.3:
            current_n = len(data)
            needed_n = max(self.min_sample_size - current_n, 0)

            if needed_n > 0:
                recommendations.append(
                    DataCollectionRecommendation(
                        priority=1,
                        data_type="feature",
                        recommendation=f"Collect {needed_n} more samples to reach minimum sample size",
                        rationale=f"Current sample size ({current_n}) is below recommended minimum ({self.min_sample_size})",
                        expected_value=sample_uncertainty * 0.8,
                        estimated_cost="low" if needed_n < 500 else "medium",
                        implementation_difficulty="easy",
                        sample_size_needed=needed_n,
                        collection_method="Continue existing data collection processes",
                    )
                )

        # Recommendation 2: Improve measurement quality
        if measurement_uncertainty > 0.3:
            recommendations.append(
                DataCollectionRecommendation(
                    priority=2,
                    data_type="feature",
                    recommendation=f"Improve measurement quality for '{cause}' and '{effect}'",
                    rationale=f"High missing data or measurement errors detected ({measurement_uncertainty:.1%} uncertainty)",
                    expected_value=measurement_uncertainty * 0.7,
                    estimated_cost="medium",
                    implementation_difficulty="medium",
                    collection_method="Implement data validation, reduce missing values, add measurement checks",
                )
            )

        # Recommendation 3: Measure unmeasured confounders
        if confounding_uncertainty > 0.3:
            unmeasured = [c for c in confounders if c not in data.columns]

            if unmeasured:
                recommendations.append(
                    DataCollectionRecommendation(
                        priority=3,
                        data_type="feature",
                        recommendation=f"Collect data for unmeasured confounders: {', '.join(unmeasured[:3])}",
                        rationale=f"{len(unmeasured)} potential confounders are not measured, risking spurious correlations",
                        expected_value=confounding_uncertainty * 0.9,
                        estimated_cost="medium" if len(unmeasured) <= 3 else "high",
                        implementation_difficulty="medium",
                        feature_name=unmeasured[0] if unmeasured else None,
                        collection_method="Add tracking for these variables in data pipeline",
                    )
                )

        # Recommendation 4: Run a controlled experiment
        if model_uncertainty > 0.4:
            recommendations.append(
                DataCollectionRecommendation(
                    priority=4,
                    data_type="experiment",
                    recommendation=f"Run A/B test to validate '{cause}' → '{effect}' causal relationship",
                    rationale="Observational data has high model uncertainty; controlled experiment provides stronger causal evidence",
                    expected_value=model_uncertainty * 1.0,
                    estimated_cost="high",
                    implementation_difficulty="hard",
                    collection_method="Design and execute randomized controlled trial",
                )
            )

        # Recommendation 5: Collect temporal data
        if "time" not in [c.lower() for c in data.columns]:
            recommendations.append(
                DataCollectionRecommendation(
                    priority=5,
                    data_type="feature",
                    recommendation="Collect temporal/longitudinal data to establish temporal precedence",
                    rationale="Causal inference requires demonstrating that cause precedes effect",
                    expected_value=0.3,
                    estimated_cost="low",
                    implementation_difficulty="easy",
                    feature_name="timestamp",
                    collection_method="Add timestamps to all events and state changes",
                )
            )

        # Recommendation 6: External data sources
        recommendations.append(
            DataCollectionRecommendation(
                priority=6,
                data_type="external_data",
                recommendation="Integrate external data sources (market data, competitor data, seasonality)",
                rationale="External factors may be unmeasured confounders affecting both cause and effect",
                expected_value=0.2,
                estimated_cost="medium",
                implementation_difficulty="medium",
                collection_method="API integrations or data partnerships",
            )
        )

        return recommendations

    def _generate_summary(
        self,
        overall_uncertainty: float,
        recommendations: list[DataCollectionRecommendation],
    ) -> str:
        """Generate human-readable summary of uncertainty and recommendations."""
        if overall_uncertainty < 0.2:
            uncertainty_level = "Low"
            action = "Current data is sufficient for confident causal inference."
        elif overall_uncertainty < 0.5:
            uncertainty_level = "Moderate"
            action = "Some data improvements would increase confidence."
        else:
            uncertainty_level = "High"
            action = "Significant data collection needed for reliable causal inference."

        summary = f"**Overall Uncertainty**: {uncertainty_level} ({overall_uncertainty:.1%})\n\n"
        summary += f"**Action**: {action}\n\n"

        if recommendations:
            summary += "**Top Recommendations**:\n"
            for i, rec in enumerate(recommendations[:3], 1):
                summary += f"{i}. {rec.recommendation} (Expected value: {rec.expected_value:.1%})\n"

        return summary

    def prioritize_features_to_collect(
        self,
        hypotheses: list[dict[str, Any]],
        data: pd.DataFrame,
    ) -> list[str]:
        """Prioritize which features to collect based on their value across hypotheses.

        Args:
            hypotheses: List of hypotheses under investigation
            data: Current available data

        Returns:
            List of feature names, sorted by priority
        """
        feature_scores = {}

        for hyp in hypotheses:
            hyp_dict = hypothesis_to_dict(hyp)
            cause = hyp_dict.get("cause", "")
            effect = hyp_dict.get("effect", "")
            confounders = hyp_dict.get("confounders", [])

            # Score based on availability
            for feature in [cause, effect] + confounders:
                if feature and feature not in data.columns:
                    feature_scores[feature] = feature_scores.get(feature, 0) + 1.0

        # Sort by score (descending)
        sorted_features = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)

        return [f[0] for f in sorted_features]
