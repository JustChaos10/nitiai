# Retention Reasoning Agent

An explainable AI agent that reasons about retention causes using causal inference.

## Overview

Most retention tools tell you **"who"** to target. This agent tells you **"why"** they behave that way and **"which lever"** will most affect them.

### Example Output

```
"Customers with early negative first-week experience AND late delivery
are 5x likelier to churn — not because of delivery delay, but because
they engage less with onboarding."

Recommended lever: Improve onboarding engagement (not delivery speed)
Confidence: High (p < 0.01, effect size: 0.73)
```

## Features

- **Causal Hypothesis Generation**: LLM-powered generation of testable hypotheses
- **Statistical Validation**: Multiple causal inference methods (Granger causality, propensity matching, etc.)
- **Confounder Detection**: Distinguishes true causes from spurious correlations
- **Lever Identification**: Recommends highest-impact interventions
- **Explainability**: Human-readable reasoning chains

## Architecture

The agent uses a LangGraph pipeline with the following nodes:

```
Opportunity → Generate Hypotheses → Test Hypotheses → Analyze Confounders → Estimate Levers → Generate Explanation
```

See [RETENTION_REASONING_AGENT_DESIGN.md](./RETENTION_REASONING_AGENT_DESIGN.md) for detailed architecture.

## Installation

### Option 1: Using Poetry (Recommended)
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Option 2: Using pip
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development (includes testing/linting tools)
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .
```

### Setup Environment Variables
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
# GOOGLE_API_KEY=your_google_api_key_here
```

## Quick Start

```python
from retention_reasoning import RetentionReasoningAgent
from retention_reasoning.models import Opportunity, OpportunityType
from langchain_google_genai import ChatGoogleGenerativeAI
import pandas as pd

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")

# Define available features
features = [
    "first_delivery_days",
    "onboarding_engagement_score",
    "order_value",
    "product_category",
    "churn_30d",
    # ... more features
]

# Create agent
agent = RetentionReasoningAgent(
    llm=llm,
    available_features=features,
)

# Define an opportunity
opportunity = Opportunity(
    type=OpportunityType.CHURN_SPIKE,
    title="Q1 2025 Cohort High Churn",
    description="Customers acquired in Q1 2025 have 32% churn rate vs 15% baseline",
    affected_cohort={"acquisition_date": "2025-01-01 to 2025-03-31"},
    metric_name="churn_rate_30d",
    baseline_value=0.15,
    current_value=0.32,
    sample_size=1247,
    severity="high",
)

# Load your data
data = pd.read_csv("enriched_customers.csv")

# Run analysis
session = agent.analyze_opportunity_sync(
    opportunity=opportunity,
    data=data,
    business_context="Recent shipping delays due to warehouse issues",
)

# View results
print(f"Validated causes: {session.validated_causes}")
print(f"Confidence: {session.confidence_score:.2%}")
print(f"Hypotheses tested: {session.hypotheses_count}")
print(f"Validated: {session.validated_hypotheses_count}")

# Access detailed reasoning
for hypothesis in session.hypotheses:
    if hypothesis.validated:
        print(f"\n✓ {hypothesis.cause} → {hypothesis.effect}")
        print(f"  Mechanism: {hypothesis.mechanism}")
        if hypothesis.causal_structure:
            print(f"  Direct effect: {hypothesis.causal_structure.direct_effect:.3f}")
            print(f"  Actionable lever: {hypothesis.causal_structure.actionable_lever}")
```

## Data Requirements

The agent expects a pandas DataFrame with:
- **Treatment variables**: Features that could cause the outcome
- **Outcome variable**: The metric you're analyzing (e.g., `churn_30d`)
- **Confounders**: Features that might affect both treatment and outcome

Example schema:
```python
{
    "customer_id": str,
    "churn_30d": int,  # 0 or 1
    "first_delivery_days": float,
    "onboarding_engagement_score": float,
    "order_value": float,
    "product_category": str,
    # ... 100+ more features
}
```

## Causal Inference Methods

The agent uses multiple statistical methods to validate hypotheses:

1. **Granger Causality**: Tests temporal precedence (does X precede Y?)
2. **Propensity Score Matching**: Compares matched treated/control groups
3. **Regression Adjustment**: Controls for confounders via regression
4. **Causal DAGs**: Builds directed acyclic graphs to identify causal structure
5. **Mediation Analysis**: Identifies indirect effects through mediators

## Integration with Existing Platform

This agent is designed to integrate with the existing Niti retention platform:

```python
# Trigger from alert system
alert = detect_retention_issue()

# Convert to opportunity
opportunity = convert_alert_to_opportunity(alert)

# Run reasoning agent
session = agent.analyze_opportunity_sync(
    opportunity=opportunity,
    data=load_enriched_customers(),
)

# Feed into strategy generation
strategy = strategy_agent.generate(
    opportunity=opportunity,
    causal_insights=session.validated_causes,
    recommended_levers=session.agent_state["actionable_levers"],
)
```

## Frontend: Thesys/Crayon Integration

For the frontend, we recommend using **Crayon** (open-source, MIT license) for rendering the reasoning graph and explanations.

### Installation
```bash
npm install @crayonai/react-core @crayonai/react-ui
```

### Usage
```tsx
import { CrayonProvider, useAgent } from '@crayonai/react-core';
import { ReasoningGraph } from '@crayonai/react-ui';

function ReasoningView() {
  const { messages, sendMessage } = useAgent({
    agentEndpoint: '/api/reasoning',
  });

  return (
    <CrayonProvider>
      <ReasoningGraph
        hypotheses={messages.hypotheses}
        causalGraph={messages.causalGraph}
        explanation={messages.explanation}
      />
    </CrayonProvider>
  );
}
```

See [THESYS_EVALUATION.md](./THESYS_EVALUATION.md) for full evaluation and recommendations.

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=retention_reasoning
```

## Project Structure

```
retention_reasoning/
├── models/              # Pydantic data models
│   ├── opportunity.py
│   ├── hypothesis.py
│   ├── lever.py
│   └── reasoning.py
├── nodes/               # LangGraph nodes
│   ├── hypothesis_generator.py
│   ├── causal_tester.py
│   ├── confounder_analyzer.py
│   ├── lever_estimator.py
│   └── explanation_generator.py
├── utils/               # Utilities
│   ├── statistical_tests.py
│   └── causal_inference.py
├── prompts/             # LLM prompts
│   └── hypothesis_generation.py
└── agent.py             # Main agent
```

## Roadmap

### Milestone 1: Backend ✓ (Current)
- [x] Hypothesis generation with LLM
- [x] Statistical causal testing
- [x] Confounder analysis
- [x] Causal DAG construction
- [x] LangGraph pipeline

### Milestone 2: Integration (Week 2-3)
- [ ] BigQuery data loader
- [ ] Integration with existing Strategy Agent
- [ ] Performance optimization
- [ ] Caching layer

### Milestone 3: Frontend (Week 3-4)
- [ ] Evaluate Crayon components
- [ ] Build reasoning graph visualization
- [ ] Interactive hypothesis exploration
- [ ] Streaming responses

### Milestone 4: Production (Week 4-5)
- [ ] A/B test recommendations
- [ ] Lever impact simulation
- [ ] Heterogeneous effect estimation
- [ ] Active learning for data collection

## References

- [DoWhy: Causal Inference Framework](https://github.com/py-why/dowhy)
- [Crayon: Generative UI for AI Agents](https://github.com/thesysdev/crayon)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

## License

[Your License Here]

## Contributing

[Contribution Guidelines]
