#!/usr/bin/env python3
"""Integration smoke test for Retention Reasoning Agent.

Tests the complete data flow without requiring dependencies to be installed.
"""

import sys
import ast
import json
import re
from pathlib import Path

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_pass(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_fail(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warn(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def test_backend_structure():
    """Test backend file structure and imports."""
    print("\n" + "="*60)
    print("Backend Structure Tests")
    print("="*60)

    # Test core files exist
    required_files = [
        'src/retention_reasoning/agent.py',
        'src/retention_reasoning/api.py',
        'src/retention_reasoning/models/opportunity.py',
        'src/retention_reasoning/utils/cache.py',
        'src/retention_reasoning/services/ab_testing.py',
        'src/retention_reasoning/utils/heterogeneous_effects.py',
        'src/retention_reasoning/utils/intervention_simulator.py',
        'src/retention_reasoning/utils/active_learning.py',
    ]

    for filepath in required_files:
        if Path(filepath).exists():
            print_pass(f"{filepath} exists")
        else:
            print_fail(f"{filepath} missing")
            return False

    return True

def test_api_endpoints():
    """Test API endpoint definitions."""
    print("\n" + "="*60)
    print("API Endpoint Tests")
    print("="*60)

    with open('src/retention_reasoning/api.py', 'r') as f:
        content = f.read()

    # Find all endpoints
    endpoints = re.findall(r'@app\.(get|post)\(["\']([^"\']+)["\']\)', content)

    required_endpoints = [
        ('get', '/health'),
        ('post', '/analyze'),
        ('post', '/ab-test'),
        ('post', '/heterogeneous'),
        ('post', '/simulate'),
        ('post', '/uncertainty'),
    ]

    for method, path in required_endpoints:
        if (method, path) in endpoints:
            print_pass(f"{method.upper():6} {path}")
        else:
            print_fail(f"{method.upper():6} {path} not found")
            return False

    # Check no campaign references
    if 'composer.compose_campaigns' in content:
        print_fail("API still references StrategyComposer")
        return False

    if 'ingest.from_payload' in content:
        print_fail("API still references AlertIngestionService")
        return False

    print_pass("No platform integration dependencies found")
    return True

def test_data_flow():
    """Test that data structures are compatible."""
    print("\n" + "="*60)
    print("Data Flow Tests")
    print("="*60)

    # Test payload structure matches Opportunity model
    test_payload = {
        "opportunity": {
            "type": "churn_spike",
            "title": "High churn in recent cohort",
            "description": "Recent customers show elevated churn rates",
            "metric_name": "churn_30d",
            "baseline_value": 0.15,
            "current_value": 0.18,
            "sample_size": 500,
            "severity": "high",
            "affected_cohort": {"description": "All customers"}
        },
        "data_preview": None,
        "business_context": "Recent shipping delays"
    }

    # Validate JSON serialization
    try:
        json_str = json.dumps(test_payload)
        reloaded = json.loads(json_str)
        if reloaded == test_payload:
            print_pass("Test payload JSON serialization works")
        else:
            print_fail("Test payload doesn't round-trip through JSON")
            return False
    except Exception as e:
        print_fail(f"JSON serialization error: {e}")
        return False

    # Check Opportunity model structure
    with open('src/retention_reasoning/models/opportunity.py', 'r') as f:
        content = f.read()

    required_fields = ['type', 'title', 'description', 'metric_name',
                      'baseline_value', 'current_value', 'sample_size']

    for field in required_fields:
        if field in content:
            print_pass(f"Opportunity.{field} field defined")
        else:
            print_fail(f"Opportunity.{field} field missing")
            return False

    return True

def test_frontend_integration():
    """Test frontend integration points."""
    print("\n" + "="*60)
    print("Frontend Integration Tests")
    print("="*60)

    # Test App.tsx
    with open('frontend/crayon/src/App.tsx', 'r') as f:
        content = f.read()

    # Check for correct API response handling
    if 'hypotheses' in content and 'causal_graph' in content:
        print_pass("App.tsx expects hypotheses and causal_graph")
    else:
        print_fail("App.tsx doesn't handle required response fields")
        return False

    # Check campaigns are removed
    if 'setCampaigns' in content or 'campaigns.length' in content:
        print_fail("App.tsx still references campaigns")
        return False

    print_pass("App.tsx has no campaign references")

    # Test components exist
    components = [
        'frontend/crayon/src/components/ReasoningGraph.tsx',
        'frontend/crayon/src/components/HypothesisExplorer.tsx',
    ]

    for comp in components:
        if Path(comp).exists():
            print_pass(f"{Path(comp).name} exists")
        else:
            print_fail(f"{comp} missing")
            return False

    return True

def test_advanced_features():
    """Test advanced features are integrated."""
    print("\n" + "="*60)
    print("Advanced Features Tests")
    print("="*60)

    features = [
        ('cache.py', 'ReasoningCache'),
        ('ab_testing.py', 'ABTestRecommender'),
        ('heterogeneous_effects.py', 'HeterogeneousEffectEstimator'),
        ('intervention_simulator.py', 'InterventionSimulator'),
        ('active_learning.py', 'ActiveLearner'),
    ]

    for filename, class_name in features:
        filepath = Path('src/retention_reasoning')
        if filename == 'ab_testing.py':
            filepath = filepath / 'services' / filename
        else:
            filepath = filepath / 'utils' / filename

        if filepath.exists():
            with open(filepath, 'r') as f:
                content = f.read()
            if class_name in content:
                print_pass(f"{class_name} implemented in {filename}")
            else:
                print_fail(f"{class_name} not found in {filename}")
                return False
        else:
            print_fail(f"{filename} missing")
            return False

    # Check they're used in api.py
    with open('src/retention_reasoning/api.py', 'r') as f:
        api_content = f.read()

    api_integrations = {
        'ReasoningCache': 'get_cache()',  # Cache uses get_cache() function
        'ABTestRecommender': 'ABTestRecommender()',
        'HeterogeneousEffectEstimator': 'HeterogeneousEffectEstimator()',
        'InterventionSimulator': 'InterventionSimulator()',
        'ActiveLearner': 'ActiveLearner()',
    }

    for class_name, usage_pattern in api_integrations.items():
        if usage_pattern in api_content:
            print_pass(f"{class_name} integrated in API as {usage_pattern}")
        else:
            print_fail(f"{class_name} not used in API (expected {usage_pattern})")
            return False

    return True

def test_documentation():
    """Test documentation exists."""
    print("\n" + "="*60)
    print("Documentation Tests")
    print("="*60)

    docs = [
        'QUICK_START.md',
        'TEST_RESULTS.md',
        'THESYS_EVALUATION.md',
        'README.md',
    ]

    for doc in docs:
        if Path(doc).exists():
            print_pass(f"{doc} exists")
        else:
            print_warn(f"{doc} missing")

    return True

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 Retention Reasoning Agent - Integration Test Suite")
    print("="*60)

    tests = [
        ("Backend Structure", test_backend_structure),
        ("API Endpoints", test_api_endpoints),
        ("Data Flow", test_data_flow),
        ("Frontend Integration", test_frontend_integration),
        ("Advanced Features", test_advanced_features),
        ("Documentation", test_documentation),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_fail(f"{name} test crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{name:30} {status}")

    print("\n" + "="*60)
    if passed == total:
        print(f"{GREEN}✅ All tests passed ({passed}/{total}){RESET}")
        print("="*60)
        print("\n🎉 System is ready for testing!")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Set up .env file with API keys")
        print("  3. Run: python examples/advanced_features_example.py")
        print("  4. Start API: uvicorn src.retention_reasoning.api:create_app --factory --reload")
        print("  5. Start frontend: cd frontend/crayon && npm run dev")
        return 0
    else:
        print(f"{RED}❌ {total - passed} test(s) failed{RESET}")
        print("="*60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
