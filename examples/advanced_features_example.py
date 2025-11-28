"""Example demonstrating all advanced features of the Retention Reasoning Agent."""

import os
import pandas as pd
import numpy as np
from retention_reasoning import RetentionReasoningAgent
from retention_reasoning.models import Opportunity, OpportunityType
from retention_reasoning.utils import (
    get_cache,
    InMemoryCache,
    HeterogeneousEffectEstimator,
    InterventionSimulator,
    InterventionScenario,
    ActiveLearner,
)
from retention_reasoning.services import ABTestRecommender
from langchain_groq import ChatGroq


def create_sample_data(n=1000):
    """Create sample customer data for demonstration."""
    np.random.seed(42)

    data = {
        "customer_id": [f"cust_{i}" for i in range(n)],
        "delivery_days": np.random.normal(5, 2, n).clip(1, 10),
        "onboarding_engagement": np.random.normal(3, 1, n).clip(0, 5),
        "order_value": np.random.normal(100, 30, n).clip(20, 200),
        "product_category": np.random.choice(["electronics", "clothing", "home"], n),
        "churn_30d": np.random.binomial(1, 0.2, n),
    }

    df = pd.DataFrame(data)

    # Create correlations for realism
    # Late delivery → lower engagement → higher churn
    df.loc[df["delivery_days"] > 6, "onboarding_engagement"] *= 0.7
    df.loc[df["onboarding_engagement"] < 2, "churn_30d"] = np.random.binomial(1, 0.4, (df["onboarding_engagement"] < 2).sum())

    return df


def main():
    print("=" * 80)
    print("RETENTION REASONING AGENT - ADVANCED FEATURES DEMO")
    print("=" * 80)

    # Initialize LLM
    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        temperature=float(os.getenv("GROQ_TEMPERATURE", 0.7)),
    )

    # Create sample data
    print("\n1. Creating sample customer data...")
    data = create_sample_data(1000)
    print(f"   Generated {len(data)} customer records")
    print(f"   Churn rate: {data['churn_30d'].mean():.1%}")

    # Initialize agent with caching
    print("\n2. Initializing agent with caching enabled...")
    cache = get_cache(InMemoryCache())
    agent = RetentionReasoningAgent(
        llm=llm,
        available_features=list(data.columns),
        cache=cache,
    )
    print("   ✓ Agent initialized with in-memory cache")

    # Define opportunity
    opportunity = Opportunity(
        type=OpportunityType.CHURN_SPIKE,
        title="High churn in recent cohort",
        description="Recent customers show elevated churn rates",
        affected_cohort={"acquisition_date": "2025-01 to 2025-03"},
        metric_name="churn_30d",
        baseline_value=0.15,
        current_value=0.32,
        sample_size=1000,
        severity="high",
    )

    # Run core analysis
    print("\n3. Running causal reasoning analysis...")
    session = agent.analyze_opportunity_sync(
        opportunity=opportunity,
        data=data,
        business_context="Recent shipping delays and warehouse issues",
    )
    print(f"   ✓ Analysis complete")
    print(f"   - Hypotheses tested: {session.hypotheses_count}")
    print(f"   - Validated causes: {', '.join(session.validated_causes) if session.validated_causes else 'none'}")
    print(f"   - Confidence score: {session.confidence_score:.1%}")

    # Feature 1: A/B Test Recommendations
    print("\n" + "=" * 80)
    print("FEATURE 1: A/B TEST RECOMMENDATIONS")
    print("=" * 80)

    ab_tester = ABTestRecommender()

    if session.hypotheses:
        print(f"\nGenerating A/B test designs for {len(session.hypotheses)} hypotheses...")

        baseline_rates = {"churn_30d": 0.20}
        designs = ab_tester.recommend_tests(
            hypotheses=session.hypotheses,
            baseline_rates=baseline_rates,
            daily_traffic=500,
        )

        print(f"\n✓ Generated {len(designs)} test designs:")
        for i, design in enumerate(designs[:2], 1):  # Show first 2
            print(f"\n  Test {i}: {design.test_name}")
            print(f"  - Required sample size: {design.required_sample_size:,}")
            print(f"  - Expected duration: {design.expected_duration_days} days")
            print(f"  - Minimum detectable effect: {design.minimum_detectable_effect:.1%}")
            print(f"  - Treatment: {design.treatment_description}")

    # Feature 2: Heterogeneous Effect Estimation
    print("\n" + "=" * 80)
    print("FEATURE 2: HETEROGENEOUS EFFECT ESTIMATION")
    print("=" * 80)

    het_estimator = HeterogeneousEffectEstimator()

    # Create treatment variable (late delivery = 1, on-time = 0)
    data["late_delivery"] = (data["delivery_days"] > 6).astype(int)

    print("\nAnalyzing treatment effect heterogeneity across subgroups...")
    analysis = het_estimator.analyze_heterogeneity(
        data=data,
        treatment_col="late_delivery",
        outcome_col="churn_30d",
        subgroup_features=["order_value", "product_category"],
        hypothesis_id="late_delivery_hypothesis",
    )

    print(f"\n✓ Heterogeneity analysis complete:")
    print(f"  - Overall effect: {analysis.overall_effect:.3f}")
    print(f"  - Heterogeneity detected: {analysis.heterogeneity_detected}")
    print(f"  - Subgroups analyzed: {len(analysis.subgroup_effects)}")

    if analysis.recommended_segments:
        print(f"\n  📊 Top recommended segments:")
        for segment in analysis.recommended_segments[:3]:
            print(f"     • {segment}")

    print(f"\n  {analysis.insights}")

    # Feature 3: Intervention Simulator
    print("\n" + "=" * 80)
    print("FEATURE 3: INTERVENTION SIMULATOR")
    print("=" * 80)

    simulator = InterventionSimulator()

    print("\nSimulating intervention: Reduce delivery time by 2 days...")

    scenario = InterventionScenario(
        intervention_name="Speed up delivery",
        target_variable="delivery_days",
        intervention_type="shift",
        intervention_value=-2.0,  # Reduce by 2 days
        description="Improve logistics to reduce delivery time from 5 to 3 days average",
    )

    result = simulator.simulate_intervention(
        data=data,
        scenario=scenario,
        outcome_variable="churn_30d",
    )

    print(f"\n✓ Simulation complete:")
    print(f"  - Baseline churn rate: {result.baseline_mean:.1%}")
    print(f"  - Simulated churn rate: {result.simulated_mean:.1%}")
    print(f"  - Absolute change: {result.absolute_change:.1%}")
    print(f"  - Relative change: {result.relative_change:.1%}")
    print(f"  - Affected customers: {result.affected_population_count:,} ({result.affected_population_pct:.0f}%)")

    # Add business impact
    result_with_roi = simulator.estimate_business_impact(
        result=result,
        avg_customer_value=500,  # $500 LTV
        intervention_cost_per_customer=5,  # $5 per customer
    )

    print(f"\n  💰 Business impact:")
    print(f"     Revenue impact: ${result_with_roi.estimated_revenue_impact:,.0f}")
    print(f"     Total cost: ${result_with_roi.estimated_cost:,.0f}")
    print(f"     ROI: {result_with_roi.estimated_roi:.1f}x")

    # Feature 4: Active Learning (Uncertainty Analysis)
    print("\n" + "=" * 80)
    print("FEATURE 4: ACTIVE LEARNING & UNCERTAINTY ANALYSIS")
    print("=" * 80)

    learner = ActiveLearner(min_sample_size=500)

    if session.hypotheses:
        print(f"\nAnalyzing uncertainty for hypothesis: {session.hypotheses[0].get('cause', 'unknown')} → {session.hypotheses[0].get('effect', 'unknown')}...")

        uncertainty = learner.analyze_uncertainty(
            hypothesis=session.hypotheses[0],
            data=data,
        )

        print(f"\n✓ Uncertainty analysis complete:")
        print(f"  - Overall uncertainty: {uncertainty.overall_uncertainty:.1%}")
        print(f"  - Sample size uncertainty: {uncertainty.sample_size_uncertainty:.1%}")
        print(f"  - Measurement uncertainty: {uncertainty.measurement_uncertainty:.1%}")
        print(f"  - Confounding uncertainty: {uncertainty.confounding_uncertainty:.1%}")
        print(f"  - Model uncertainty: {uncertainty.model_uncertainty:.1%}")

        print(f"\n  {uncertainty.summary}")

        if uncertainty.recommendations:
            print(f"\n  📋 Top data collection recommendations:")
            for rec in uncertainty.recommendations[:3]:
                print(f"\n     Priority {rec.priority}: {rec.recommendation}")
                print(f"     Rationale: {rec.rationale}")
                print(f"     Expected value: {rec.expected_value:.1%}")
                print(f"     Cost: {rec.estimated_cost}, Difficulty: {rec.implementation_difficulty}")

    # Feature 5: Caching Performance
    print("\n" + "=" * 80)
    print("FEATURE 5: CACHING PERFORMANCE")
    print("=" * 80)

    print("\nDemonstrating cache performance...")

    # Store a test result in cache
    cache.set_hypothesis_test(
        cause="late_delivery",
        effect="churn_30d",
        method="granger",
        test_result={"p_value": 0.003, "effect_size": 0.42},
    )

    # Retrieve from cache
    cached_result = cache.get_hypothesis_test(
        cause="late_delivery",
        effect="churn_30d",
        method="granger",
    )

    print(f"\n✓ Cache test:")
    print(f"  - Stored: hypothesis test for late_delivery → churn_30d")
    print(f"  - Retrieved: {cached_result}")
    print(f"  - Cache hit successful! ✓")

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\n✅ All 5 advanced features demonstrated successfully!")
    print("\nFeatures showcased:")
    print("  1. A/B Test Recommendations - Statistical test design automation")
    print("  2. Heterogeneous Effects - Subgroup analysis for targeted interventions")
    print("  3. Intervention Simulator - 'What if' scenario modeling with ROI")
    print("  4. Active Learning - Data collection recommendations")
    print("  5. Caching - Performance optimization for repeated queries")

    print("\n💡 Next steps:")
    print("  - Run the FastAPI server: uvicorn retention_reasoning.api:create_app --factory")
    print("  - Explore the frontend: cd frontend/crayon && npm run dev")
    print("  - See IMPLEMENTATION_SUMMARY.md for integration details")


if __name__ == "__main__":
    main()
