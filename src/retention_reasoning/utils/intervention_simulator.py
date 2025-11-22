"""Intervention simulator for counterfactual analysis and what-if scenarios."""

from __future__ import annotations

from typing import Any, Optional
import numpy as np
import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field


class InterventionScenario(BaseModel):
    """Specification of an intervention to simulate."""

    intervention_name: str
    target_variable: str
    intervention_type: str  # "shift", "scale", "set_value", "conditional"
    intervention_value: float
    condition: Optional[str] = None  # For conditional interventions
    description: str = ""


class SimulationResult(BaseModel):
    """Results of simulating an intervention."""

    scenario_name: str
    intervention: InterventionScenario

    # Baseline (no intervention)
    baseline_mean: float
    baseline_std: float
    baseline_distribution: Optional[dict] = None

    # After intervention
    simulated_mean: float
    simulated_std: float
    simulated_distribution: Optional[dict] = None

    # Impact metrics
    absolute_change: float
    relative_change: float
    affected_population_pct: float
    affected_population_count: int

    # Downstream effects (if causal graph available)
    downstream_effects: dict[str, float] = Field(default_factory=dict)

    # Business impact
    estimated_revenue_impact: Optional[float] = None
    estimated_cost: Optional[float] = None
    estimated_roi: Optional[float] = None


class InterventionSimulator:
    """Simulate interventions and predict their effects using causal models."""

    def __init__(self, random_seed: int = 42) -> None:
        self.random_seed = random_seed
        np.random.seed(random_seed)

    def apply_intervention(
        self,
        data: pd.DataFrame,
        scenario: InterventionScenario,
    ) -> pd.DataFrame:
        """Apply an intervention to the data (in-place on a copy).

        Args:
            data: Original data
            scenario: Intervention specification

        Returns:
            Modified DataFrame with intervention applied
        """
        data_copy = data.copy()
        target = scenario.target_variable

        if target not in data_copy.columns:
            logger.warning(f"Target variable {target} not in data")
            return data_copy

        # Apply condition if specified
        if scenario.condition:
            try:
                mask = data_copy.eval(scenario.condition)
            except Exception as exc:
                logger.warning(f"Failed to evaluate condition '{scenario.condition}': {exc}")
                mask = pd.Series([True] * len(data_copy))
        else:
            mask = pd.Series([True] * len(data_copy))

        # Apply intervention based on type
        if scenario.intervention_type == "shift":
            # Add a constant value
            data_copy.loc[mask, target] = data_copy.loc[mask, target] + scenario.intervention_value

        elif scenario.intervention_type == "scale":
            # Multiply by a factor
            data_copy.loc[mask, target] = data_copy.loc[mask, target] * scenario.intervention_value

        elif scenario.intervention_type == "set_value":
            # Set to a fixed value
            data_copy.loc[mask, target] = scenario.intervention_value

        elif scenario.intervention_type == "conditional":
            # More complex conditional logic (placeholder)
            logger.warning("Conditional intervention type not fully implemented")

        else:
            logger.warning(f"Unknown intervention type: {scenario.intervention_type}")

        return data_copy

    def simulate_intervention(
        self,
        data: pd.DataFrame,
        scenario: InterventionScenario,
        outcome_variable: str,
        causal_model: Optional[dict] = None,
    ) -> SimulationResult:
        """Simulate an intervention and estimate its effects.

        Args:
            data: Historical data
            scenario: Intervention to simulate
            outcome_variable: Target outcome to measure (e.g., churn_30d)
            causal_model: Optional causal model (dict of variable -> coefficient)

        Returns:
            SimulationResult with predicted impact
        """
        # Baseline statistics
        baseline_mean = data[outcome_variable].mean()
        baseline_std = data[outcome_variable].std()

        # Apply intervention
        intervened_data = self.apply_intervention(data, scenario)

        # Re-calculate outcome if causal model is provided
        if causal_model and scenario.target_variable in causal_model:
            # Simple linear causal model: outcome = sum(coef * feature)
            intervened_outcome = self._apply_causal_model(
                intervened_data,
                outcome_variable,
                causal_model,
            )
            intervened_data[outcome_variable] = intervened_outcome

        # Post-intervention statistics
        simulated_mean = intervened_data[outcome_variable].mean()
        simulated_std = intervened_data[outcome_variable].std()

        # Impact metrics
        absolute_change = simulated_mean - baseline_mean
        relative_change = (absolute_change / baseline_mean) if baseline_mean != 0 else 0.0

        # Affected population
        if scenario.condition:
            try:
                affected_mask = data.eval(scenario.condition)
                affected_count = affected_mask.sum()
            except Exception:
                affected_count = len(data)
        else:
            affected_count = len(data)

        affected_pct = (affected_count / len(data)) * 100

        # Downstream effects (if causal model provided)
        downstream_effects = {}
        if causal_model:
            downstream_effects = self._estimate_downstream_effects(
                intervened_data,
                data,
                causal_model,
                outcome_variable,
            )

        return SimulationResult(
            scenario_name=scenario.intervention_name,
            intervention=scenario,
            baseline_mean=float(baseline_mean),
            baseline_std=float(baseline_std),
            simulated_mean=float(simulated_mean),
            simulated_std=float(simulated_std),
            absolute_change=float(absolute_change),
            relative_change=float(relative_change),
            affected_population_pct=float(affected_pct),
            affected_population_count=int(affected_count),
            downstream_effects=downstream_effects,
        )

    def _apply_causal_model(
        self,
        data: pd.DataFrame,
        outcome_variable: str,
        causal_model: dict[str, float],
    ) -> pd.Series:
        """Apply a linear causal model to predict outcome.

        Args:
            data: Data with feature values
            outcome_variable: Name of outcome variable
            causal_model: Dict mapping feature names to coefficients

        Returns:
            Predicted outcome values
        """
        prediction = pd.Series([0.0] * len(data), index=data.index)

        for feature, coef in causal_model.items():
            if feature in data.columns:
                prediction += data[feature] * coef
            elif feature == "intercept":
                prediction += coef

        return prediction

    def _estimate_downstream_effects(
        self,
        intervened_data: pd.DataFrame,
        original_data: pd.DataFrame,
        causal_model: dict[str, float],
        outcome_variable: str,
    ) -> dict[str, float]:
        """Estimate effects on other variables (downstream in causal graph)."""
        downstream_effects = {}

        # For each variable in the model, compare intervened vs original
        for var in causal_model.keys():
            if var in intervened_data.columns and var != outcome_variable:
                original_mean = original_data[var].mean()
                intervened_mean = intervened_data[var].mean()
                change = intervened_mean - original_mean

                if abs(change) > 1e-6:  # Non-negligible change
                    downstream_effects[var] = float(change)

        return downstream_effects

    def compare_scenarios(
        self,
        data: pd.DataFrame,
        scenarios: list[InterventionScenario],
        outcome_variable: str,
        causal_model: Optional[dict] = None,
    ) -> list[SimulationResult]:
        """Compare multiple intervention scenarios.

        Args:
            data: Historical data
            scenarios: List of interventions to compare
            outcome_variable: Target outcome
            causal_model: Optional causal model

        Returns:
            List of SimulationResults, sorted by absolute impact (descending)
        """
        results = []

        for scenario in scenarios:
            try:
                result = self.simulate_intervention(
                    data,
                    scenario,
                    outcome_variable,
                    causal_model,
                )
                results.append(result)
            except Exception as exc:
                logger.warning(f"Failed to simulate scenario {scenario.intervention_name}: {exc}")

        # Sort by absolute impact
        results.sort(key=lambda r: abs(r.absolute_change), reverse=True)

        return results

    def estimate_business_impact(
        self,
        result: SimulationResult,
        avg_customer_value: float,
        intervention_cost_per_customer: float = 0.0,
    ) -> SimulationResult:
        """Add business impact estimates to a simulation result.

        Args:
            result: Simulation result
            avg_customer_value: Average LTV or revenue per customer
            intervention_cost_per_customer: Cost to deliver intervention per customer

        Returns:
            Updated SimulationResult with business metrics
        """
        # Estimate revenue impact
        # If outcome is churn reduction, saved customers * LTV
        affected_count = result.affected_population_count
        absolute_change = result.absolute_change

        # Assuming outcome is churn rate (higher = worse)
        # Negative change = reduction in churn = good
        saved_customers = -absolute_change * affected_count
        revenue_impact = saved_customers * avg_customer_value

        # Estimate cost
        total_cost = intervention_cost_per_customer * affected_count

        # ROI
        roi = ((revenue_impact - total_cost) / total_cost) if total_cost > 0 else 0.0

        # Update result
        result.estimated_revenue_impact = float(revenue_impact)
        result.estimated_cost = float(total_cost)
        result.estimated_roi = float(roi)

        return result

    def generate_scenario_from_lever(
        self,
        lever: dict[str, Any],
        intervention_magnitude: float = 1.0,
    ) -> InterventionScenario:
        """Generate intervention scenario from a lever recommendation.

        Args:
            lever: Lever object with target_variable, mechanism, etc.
            intervention_magnitude: How much to change the lever (1.0 = full effect)

        Returns:
            InterventionScenario
        """
        target_var = lever.get("target_variable", "unknown")
        lever_name = lever.get("name", "intervention")
        mechanism = lever.get("mechanism", "")

        # Infer intervention type and value from mechanism
        # This is heuristic-based; in production, would be more sophisticated
        if "increase" in mechanism.lower():
            intervention_type = "shift"
            intervention_value = intervention_magnitude  # Increase by this amount
        elif "decrease" in mechanism.lower() or "reduce" in mechanism.lower():
            intervention_type = "shift"
            intervention_value = -intervention_magnitude  # Decrease
        elif "improve" in mechanism.lower():
            intervention_type = "scale"
            intervention_value = 1.0 + intervention_magnitude  # Scale up
        else:
            intervention_type = "shift"
            intervention_value = intervention_magnitude

        return InterventionScenario(
            intervention_name=lever_name,
            target_variable=target_var,
            intervention_type=intervention_type,
            intervention_value=intervention_value,
            description=mechanism,
        )
