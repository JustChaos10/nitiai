"""A/B test recommendation module for validating causal hypotheses."""

from __future__ import annotations

import math
from typing import Any, Optional

from loguru import logger
from pydantic import BaseModel, Field

from ..utils.hypothesis_utils import hypothesis_to_dict


class ABTestDesign(BaseModel):
    """A/B test design specification."""

    hypothesis_id: str
    test_name: str
    objective: str
    treatment_description: str
    control_description: str

    # Sample size calculation
    required_sample_size: int
    required_sample_size_per_group: int
    expected_duration_days: int

    # Statistical parameters
    baseline_rate: float
    expected_effect_size: float
    minimum_detectable_effect: float
    significance_level: float = 0.05
    statistical_power: float = 0.80

    # Segmentation
    inclusion_criteria: list[str]
    exclusion_criteria: list[str]
    stratification_variables: Optional[list[str]] = None

    # Measurement
    primary_metric: str
    secondary_metrics: list[str] = Field(default_factory=list)
    measurement_window_days: int = 30

    # Implementation
    randomization_unit: str = "customer_id"
    allocation_ratio: float = 0.5  # 50/50 split
    guardrail_metrics: list[str] = Field(default_factory=list)

    # Recommendations
    launch_checklist: list[str] = Field(default_factory=list)
    analysis_plan: str = ""
    stopping_rules: list[str] = Field(default_factory=list)


class ABTestRecommender:
    """Generate A/B test recommendations to validate causal hypotheses."""

    def __init__(
        self,
        default_significance: float = 0.05,
        default_power: float = 0.80,
    ) -> None:
        self.default_significance = default_significance
        self.default_power = default_power

    def calculate_sample_size(
        self,
        baseline_rate: float,
        expected_effect_size: float,
        significance: float = 0.05,
        power: float = 0.80,
        allocation_ratio: float = 0.5,
    ) -> int:
        """Calculate required sample size for proportions test.

        Uses the formula for comparing two proportions.
        """
        # Z-scores for significance and power
        from scipy.stats import norm

        z_alpha = norm.ppf(1 - significance / 2)  # Two-tailed
        z_beta = norm.ppf(power)

        p1 = baseline_rate
        p2 = baseline_rate + expected_effect_size
        p_avg = (p1 + p2) / 2

        # Calculate sample size per group (assumes equal allocation)
        numerator = (z_alpha * math.sqrt(2 * p_avg * (1 - p_avg)) + z_beta * math.sqrt(
            p1 * (1 - p1) + p2 * (1 - p2)
        )) ** 2
        denominator = (p2 - p1) ** 2

        n_per_group = math.ceil(numerator / denominator)

        # Adjust for allocation ratio
        if allocation_ratio != 0.5:
            n_treatment = n_per_group
            n_control = math.ceil(n_treatment * (1 - allocation_ratio) / allocation_ratio)
            total_n = n_treatment + n_control
        else:
            total_n = 2 * n_per_group

        return total_n

    def calculate_minimum_detectable_effect(
        self,
        baseline_rate: float,
        sample_size: int,
        significance: float = 0.05,
        power: float = 0.80,
    ) -> float:
        """Calculate minimum detectable effect given sample size."""
        from scipy.stats import norm

        z_alpha = norm.ppf(1 - significance / 2)
        z_beta = norm.ppf(power)

        n_per_group = sample_size / 2
        p1 = baseline_rate

        # Iterative search for MDE
        for mde in [0.01, 0.02, 0.03, 0.05, 0.10, 0.15, 0.20]:
            p2 = p1 + mde
            p_avg = (p1 + p2) / 2

            required_n = (
                (z_alpha * math.sqrt(2 * p_avg * (1 - p_avg)) + z_beta * math.sqrt(
                    p1 * (1 - p1) + p2 * (1 - p2)
                )) ** 2
            ) / ((p2 - p1) ** 2)

            if required_n <= n_per_group:
                return mde

        return 0.20  # Default upper bound

    def estimate_duration(
        self,
        required_sample_size: int,
        daily_eligible_users: int,
    ) -> int:
        """Estimate test duration in days."""
        if daily_eligible_users <= 0:
            logger.warning("Daily eligible users <= 0, defaulting to 30 days")
            return 30

        days = math.ceil(required_sample_size / daily_eligible_users)
        # Add measurement window
        return days + 30  # 30-day measurement window

    def design_test(
        self,
        hypothesis: dict[str, Any],
        baseline_rate: float,
        expected_effect_size: float,
        daily_eligible_users: int = 100,
        significance: Optional[float] = None,
        power: Optional[float] = None,
    ) -> ABTestDesign:
        """Design an A/B test to validate a causal hypothesis."""
        significance = significance or self.default_significance
        power = power or self.default_power

        # Calculate sample size
        sample_size = self.calculate_sample_size(
            baseline_rate=baseline_rate,
            expected_effect_size=expected_effect_size,
            significance=significance,
            power=power,
        )

        # Calculate MDE
        mde = self.calculate_minimum_detectable_effect(
            baseline_rate=baseline_rate,
            sample_size=sample_size,
            significance=significance,
            power=power,
        )

        # Estimate duration
        duration = self.estimate_duration(sample_size, daily_eligible_users)

        # Extract hypothesis details
        cause = hypothesis.get("cause", "unknown")
        effect = hypothesis.get("effect", "unknown")
        mechanism = hypothesis.get("mechanism", "")

        # Build test name
        test_name = f"Test: {cause} → {effect}"

        # Determine treatment
        treatment_desc = self._generate_treatment_description(cause, mechanism)
        control_desc = "No intervention (business as usual)"

        # Inclusion/exclusion criteria
        inclusion = self._generate_inclusion_criteria(hypothesis)
        exclusion = self._generate_exclusion_criteria(hypothesis)

        # Metrics
        primary_metric = effect
        secondary_metrics = self._generate_secondary_metrics(effect)

        # Guardrails
        guardrails = ["revenue_per_user", "user_complaints", "system_errors"]

        # Launch checklist
        checklist = [
            "Review test design with stakeholders",
            "Implement randomization logic",
            "Set up metric tracking",
            "Configure guardrail alerts",
            "Run pre-launch simulation with synthetic data",
            "Prepare analysis notebook",
            "Document expected timeline and success criteria",
        ]

        # Analysis plan
        analysis_plan = f"""
## Analysis Plan

**Primary Analysis**: Compare {effect} between treatment and control groups using two-sample proportion test.

**Statistical Test**: Two-tailed z-test for proportions
- H0: p_treatment = p_control
- H1: p_treatment ≠ p_control
- Significance level: {significance}
- Power: {power}

**Adjustment for Multiple Testing**: Bonferroni correction if analyzing secondary metrics.

**Subgroup Analysis**: Examine effect heterogeneity by customer segment (if stratified).

**Sensitivity Analysis**:
- Check for selection bias using covariate balance tests
- Perform intention-to-treat (ITT) analysis
- Check for spillover effects between treatment and control

**Reporting**: Document effect size, confidence intervals, p-value, and business impact.
        """.strip()

        # Stopping rules
        stopping_rules = [
            f"Stop for efficacy if p < {significance} and observed effect > MDE",
            "Stop for futility if observed effect < 50% of MDE after 75% of planned duration",
            "Stop for harm if any guardrail metric degrades by >10% (p < 0.01)",
        ]

        return ABTestDesign(
            hypothesis_id=hypothesis.get("id", "unknown"),
            test_name=test_name,
            objective=f"Validate that {cause} causally affects {effect}",
            treatment_description=treatment_desc,
            control_description=control_desc,
            required_sample_size=sample_size,
            required_sample_size_per_group=sample_size // 2,
            expected_duration_days=duration,
            baseline_rate=baseline_rate,
            expected_effect_size=expected_effect_size,
            minimum_detectable_effect=mde,
            significance_level=significance,
            statistical_power=power,
            inclusion_criteria=inclusion,
            exclusion_criteria=exclusion,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics,
            guardrail_metrics=guardrails,
            launch_checklist=checklist,
            analysis_plan=analysis_plan,
            stopping_rules=stopping_rules,
        )

    def _generate_treatment_description(self, cause: str, mechanism: str) -> str:
        """Generate treatment description from cause variable."""
        cause_lower = cause.lower()

        if "delivery" in cause_lower:
            return "Expedite delivery (3-day shipping instead of 5-day)"
        elif "onboarding" in cause_lower or "engagement" in cause_lower:
            return "Enhanced onboarding program (in-app tutorials + email sequence)"
        elif "price" in cause_lower or "discount" in cause_lower:
            return "Price intervention (10% discount on next purchase)"
        elif "support" in cause_lower:
            return "Proactive customer support (reach out within 24h of first purchase)"
        else:
            return f"Intervention targeting {cause} ({mechanism or 'details TBD'})"

    def _generate_inclusion_criteria(self, hypothesis: dict[str, Any]) -> list[str]:
        """Generate inclusion criteria from hypothesis."""
        criteria = [
            "New customers only (acquisition_date within test period)",
            "Completed at least one purchase",
            "Not part of other concurrent experiments",
        ]

        # Add hypothesis-specific criteria
        confounders = hypothesis.get("confounders", [])
        if "order_value" in confounders:
            criteria.append("Order value > $20 (exclude very low value)")

        return criteria

    def _generate_exclusion_criteria(self, hypothesis: dict[str, Any]) -> list[str]:
        """Generate exclusion criteria."""
        return [
            "Existing VIP/loyalty members",
            "Employee accounts",
            "Test accounts",
            "Customers who previously churned and returned",
        ]

    def _generate_secondary_metrics(self, primary_metric: str) -> list[str]:
        """Generate relevant secondary metrics."""
        if "churn" in primary_metric.lower():
            return [
                "repeat_purchase_rate",
                "time_to_second_purchase",
                "lifetime_value_30d",
                "engagement_score",
            ]
        elif "ltv" in primary_metric.lower() or "value" in primary_metric.lower():
            return [
                "average_order_value",
                "purchase_frequency",
                "margin_per_customer",
            ]
        else:
            return [
                "engagement_score",
                "session_count",
                "time_on_platform",
            ]

    def recommend_tests(
        self,
        hypotheses: list[dict[str, Any]],
        baseline_rates: dict[str, float],
        daily_traffic: int = 1000,
    ) -> list[ABTestDesign]:
        """Recommend A/B tests for multiple hypotheses.

        Args:
            hypotheses: List of validated hypotheses
            baseline_rates: Baseline rates for each effect variable
            daily_traffic: Average daily eligible users

        Returns:
            List of A/B test designs, sorted by feasibility
        """
        designs = []

        for hyp in hypotheses:
            hyp_dict = hypothesis_to_dict(hyp)
            effect = hyp_dict.get("effect", "churn_30d")
            baseline = baseline_rates.get(effect, 0.15)

            # Use validated effect size if available
            effect_size = 0.10  # Default
            consensus = hyp_dict.get("consensus", {})
            if consensus.get("effect_size") is not None:
                effect_size = consensus["effect_size"]
            elif "expected_effect" in hyp_dict:
                effect_size = hyp_dict["expected_effect"]

            try:
                design = self.design_test(
                    hypothesis=hyp_dict,
                    baseline_rate=baseline,
                    expected_effect_size=effect_size,
                    daily_eligible_users=daily_traffic,
                )
                designs.append(design)
            except Exception as exc:
                hyp_id = hyp_dict.get("id") or hyp_dict.get("hypothesis_id")
                logger.warning(f"Failed to design test for hypothesis {hyp_id}: {exc}")

        # Sort by feasibility (duration ascending)
        designs.sort(key=lambda d: d.expected_duration_days)

        return designs
