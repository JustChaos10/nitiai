"""Simple example of using the Retention Reasoning Agent."""

import pandas as pd
import numpy as np
from langchain_google_genai import ChatGoogleGenerativeAI

from retention_reasoning import RetentionReasoningAgent
from retention_reasoning.models import Opportunity, OpportunityType


def generate_synthetic_data(n_samples: int = 1000) -> pd.DataFrame:
    """Generate synthetic customer data for demonstration.

    This creates a dataset where:
    - Late delivery causes lower onboarding engagement
    - Low onboarding engagement causes churn
    - (So late delivery causes churn INDIRECTLY)
    """
    np.random.seed(42)

    data = pd.DataFrame({
        "customer_id": range(n_samples),

        # Treatment: First delivery delay (days)
        "first_delivery_days": np.random.exponential(4, n_samples),

        # Confounder: Order value (affects both delivery and churn)
        "order_value": np.random.lognormal(4, 1, n_samples),

        # Product category
        "product_category": np.random.choice(["electronics", "clothing", "home"], n_samples),
    })

    # Mediator: Onboarding engagement (affected by delivery delay)
    # Late delivery → lower engagement
    data["onboarding_engagement_score"] = (
        5.0
        - 0.3 * data["first_delivery_days"]
        + 0.0002 * data["order_value"]
        + np.random.normal(0, 1, n_samples)
    ).clip(0, 10)

    # Outcome: Churn (affected by onboarding engagement)
    # Low engagement → higher churn
    churn_prob = 1 / (1 + np.exp(
        2.0
        - 0.8 * data["onboarding_engagement_score"]
        - 0.0001 * data["order_value"]
        + 0.1 * data["first_delivery_days"]  # Small direct effect
    ))
    data["churn_30d"] = (np.random.random(n_samples) < churn_prob).astype(int)

    return data


def main():
    """Run a simple example."""
    print("=" * 80)
    print("Retention Reasoning Agent - Simple Example")
    print("=" * 80)

    # Generate synthetic data
    print("\n1. Generating synthetic data...")
    data = generate_synthetic_data(n_samples=500)
    print(f"   Created {len(data)} customer records")
    print(f"   Churn rate: {data['churn_30d'].mean():.1%}")

    # Define available features
    features = list(data.columns)
    features.remove("customer_id")
    print(f"\n2. Available features: {features}")

    # Initialize LLM (you'll need to set GOOGLE_API_KEY environment variable)
    print("\n3. Initializing LLM...")
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.7,
        )
        print("   ✓ LLM initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize LLM: {e}")
        print("   Please set GOOGLE_API_KEY environment variable")
        return

    # Create agent
    print("\n4. Creating Retention Reasoning Agent...")
    agent = RetentionReasoningAgent(
        llm=llm,
        available_features=features,
    )
    print("   ✓ Agent created")

    # Define opportunity
    print("\n5. Defining retention opportunity...")
    opportunity = Opportunity(
        type=OpportunityType.CHURN_SPIKE,
        title="High Churn in Recent Cohort",
        description="Recent customers show elevated churn rates",
        affected_cohort={"description": "All customers in dataset"},
        metric_name="churn_30d",
        baseline_value=0.15,
        current_value=data["churn_30d"].mean(),
        sample_size=len(data),
        severity="high",
        business_context={
            "recent_changes": "Warehouse issues causing delivery delays",
            "product_mix": "Mix of electronics, clothing, and home goods",
        },
    )
    print(f"   Opportunity: {opportunity.title}")
    print(f"   Churn rate: {opportunity.current_value:.1%} (baseline: {opportunity.baseline_value:.1%})")

    # Run analysis
    print("\n6. Running causal analysis...")
    print("   This may take 30-60 seconds...")

    try:
        session = agent.analyze_opportunity_sync(
            opportunity=opportunity,
            data=data,
            business_context="Recent shipping delays due to warehouse issues",
        )

        # Display results
        print("\n" + "=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)

        print(f"\n✓ Status: {session.status}")
        print(f"✓ Confidence: {session.confidence_score:.1%}")
        print(f"✓ Hypotheses tested: {session.hypotheses_count}")
        print(f"✓ Validated hypotheses: {session.validated_hypotheses_count}")

        if session.validated_causes:
            print(f"\n📊 Validated Causal Factors:")
            for i, cause in enumerate(session.validated_causes, 1):
                print(f"   {i}. {cause}")

        print(f"\n📝 Detailed Hypotheses:")
        for i, hypothesis in enumerate(session.hypotheses, 1):
            status = "✓ VALIDATED" if hypothesis.validated else "✗ Not validated"
            print(f"\n   Hypothesis {i}: {status}")
            print(f"   Cause: {hypothesis.cause}")
            print(f"   Effect: {hypothesis.effect}")
            print(f"   Mechanism: {hypothesis.mechanism}")

            if hypothesis.validated and hypothesis.causal_structure:
                cs = hypothesis.causal_structure
                print(f"   Direct effect: {cs.direct_effect:.3f}")
                print(f"   Indirect effect: {cs.indirect_effect:.3f}")
                print(f"   Total effect: {cs.total_effect:.3f}")
                print(f"   Actionable lever: {cs.actionable_lever}")

            if hypothesis.test_results:
                print(f"   Test results:")
                for result in hypothesis.test_results:
                    print(f"     - {result.method.value}: p={result.p_value:.4f}, "
                          f"effect_size={result.effect_size:.3f}")

        # Explanation
        if session.agent_state.get("explanation"):
            print(f"\n💡 Explanation:")
            print(f"   {session.agent_state['explanation']}")

        print("\n" + "=" * 80)
        print("Analysis complete!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
