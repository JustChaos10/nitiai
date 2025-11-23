#!/usr/bin/env python3
"""Test script using sample_data.csv - NO DEPENDENCIES REQUIRED for preview."""

import csv
import json

def main():
    print("=" * 80)
    print("SAMPLE DATA PREVIEW - Testing Retention Reasoning Agent Data Format")
    print("=" * 80)

    # Load sample data
    print("\n1. Loading sample data...")
    with open("sample_data.csv", 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)

    print(f"   ✓ Loaded {len(data)} customer records")

    # Calculate statistics
    delivery_days = [float(row['first_delivery_days']) for row in data]
    engagement = [float(row['onboarding_engagement_score']) for row in data]
    order_values = [float(row['order_value']) for row in data]
    churn = [int(row['churn_30d']) for row in data]

    churn_rate = sum(churn) / len(churn)
    avg_delivery = sum(delivery_days) / len(delivery_days)
    avg_engagement = sum(engagement) / len(engagement)
    avg_order = sum(order_values) / len(order_values)

    # Show data statistics
    print("\n2. Data Statistics:")
    print(f"   • Churn rate: {churn_rate:.1%}")
    print(f"   • Average delivery days: {avg_delivery:.1f}")
    print(f"   • Average engagement score: {avg_engagement:.1f}")
    print(f"   • Average order value: ${avg_order:.2f}")

    # Product category distribution
    categories = {}
    for row in data:
        cat = row['product_category']
        categories[cat] = categories.get(cat, 0) + 1

    print("\n3. Product Category Distribution:")
    for category, count in categories.items():
        print(f"   • {category}: {count} ({count/len(data)*100:.1f}%)")

    # Churned vs active analysis
    churned_data = [row for row in data if int(row['churn_30d']) == 1]
    active_data = [row for row in data if int(row['churn_30d']) == 0]

    churned_delivery = sum(float(r['first_delivery_days']) for r in churned_data) / len(churned_data)
    churned_engagement = sum(float(r['onboarding_engagement_score']) for r in churned_data) / len(churned_data)

    active_delivery = sum(float(r['first_delivery_days']) for r in active_data) / len(active_data)
    active_engagement = sum(float(r['onboarding_engagement_score']) for r in active_data) / len(active_data)

    print("\n4. Correlation Analysis:")
    print(f"   • Churned customers (n={len(churned_data)}):")
    print(f"     - Avg delivery days: {churned_delivery:.1f}")
    print(f"     - Avg engagement: {churned_engagement:.1f}")

    print(f"   • Active customers (n={len(active_data)}):")
    print(f"     - Avg delivery days: {active_delivery:.1f}")
    print(f"     - Avg engagement: {active_engagement:.1f}")

    print("\n5. Expected Causal Pattern:")
    print("   The data is designed with this causal structure:")
    print("   📦 Late Delivery → 😞 Low Engagement → 💔 Churn")
    print("   ")
    print("   This means:")
    print("   • Customers with delivery_days > 7 have LOWER engagement")
    print("   • Customers with engagement < 4 have HIGHER churn")
    print("   • The agent should discover this causal chain!")

    # API payload
    print("\n6. API Test Payload Structure:")
    api_payload = {
        "opportunity": {
            "type": "churn_spike",
            "title": "High churn in recent cohort",
            "description": "Customers acquired recently show elevated churn rates",
            "affected_cohort": {
                "description": "Recent customers with delivery issues"
            },
            "metric_name": "churn_30d",
            "baseline_value": 0.15,
            "current_value": round(churn_rate, 3),
            "sample_size": len(data),
            "severity": "high",
            "business_context": {
                "recent_changes": "Warehouse delays causing longer delivery times",
                "product_mix": "Mix of electronics, clothing, and home goods"
            }
        },
        "business_context": "Recent shipping delays due to warehouse issues"
    }

    print(json.dumps(api_payload, indent=2))

    print("\n" + "=" * 80)
    print("HOW TO TEST THE SYSTEM")
    print("=" * 80)

    print("\n📝 METHOD 1: Using Python Script (Requires GROQ_API_KEY)")
    print("   1. Set environment variable:")
    print("      export GROQ_API_KEY='your_api_key_here'")
    print("   ")
    print("   2. Install dependencies:")
    print("      pip install -r requirements.txt")
    print("   ")
    print("   3. Run the simple example:")
    print("      python examples/simple_example.py")
    print("   ")
    print("      Note: The example generates its own synthetic data internally")

    print("\n📝 METHOD 2: Using API Endpoint (Requires GROQ_API_KEY)")
    print("   1. Set environment variable:")
    print("      export GROQ_API_KEY='your_api_key_here'")
    print("   ")
    print("   2. Install dependencies:")
    print("      pip install -r requirements.txt")
    print("   ")
    print("   3. Start the API server:")
    print("      uvicorn src.retention_reasoning.api:create_app --factory --reload")
    print("   ")
    print("   4. In another terminal, send test request:")
    print('      curl -X POST http://localhost:8000/analyze \\')
    print('        -H "Content-Type: application/json" \\')
    print("        -d @api_test_payload.json")

    print("\n📝 METHOD 3: Using Frontend UI (Requires GROQ_API_KEY)")
    print("   1. Set environment variable:")
    print("      export GROQ_API_KEY='your_api_key_here'")
    print("   ")
    print("   2. Install backend dependencies:")
    print("      pip install -r requirements.txt")
    print("   ")
    print("   3. Install frontend dependencies:")
    print("      cd frontend/crayon && npm install")
    print("   ")
    print("   4. Start backend:")
    print("      uvicorn src.retention_reasoning.api:create_app --factory --reload")
    print("   ")
    print("   5. In another terminal, start frontend:")
    print("      cd frontend/crayon && npm run dev")
    print("   ")
    print("   6. Open browser: http://localhost:5173")
    print("   ")
    print("   7. Paste this into the input box:")
    print("      " + json.dumps(api_payload))

    print("\n📝 SAMPLE DATA FILE:")
    print("   • sample_data.csv - 200 customer records")
    print("   • Features:")
    print("     - customer_id: Unique identifier")
    print("     - first_delivery_days: Days until first delivery (1-10)")
    print("     - onboarding_engagement_score: Engagement score (0-10)")
    print("     - order_value: Order amount ($60-$165)")
    print("     - product_category: electronics, clothing, or home")
    print("     - churn_30d: Whether customer churned (0 or 1)")

    print("\n" + "=" * 80)
    print("⚠️  IMPORTANT: GET YOUR FREE GROQ API KEY")
    print("=" * 80)
    print("\n   The system requires a Groq API key to run the LLM reasoning.")
    print("\n   How to get it:")
    print("   1. Go to: https://console.groq.com/")
    print("   2. Sign up for free account")
    print("   3. Go to API Keys section")
    print("   4. Create new API key")
    print("   5. Copy the key")
    print("\n   Then set it:")
    print("   export GROQ_API_KEY='gsk_...'")

    print("\n" + "=" * 80)
    print("✅ DATA PREPARATION COMPLETE!")
    print("=" * 80)

    # Save API payload to file for easy curl testing
    with open("api_test_payload.json", "w") as f:
        json.dump(api_payload, f, indent=2)
    print("\n💾 Saved API test payload to: api_test_payload.json")
    print("   You can use this file for testing the API endpoint")

if __name__ == "__main__":
    main()
