# Retention Reasoning Agent: Architecture & Design

## Vision

Build an explainable AI agent that doesn't just identify "who will churn" but reasons about **"why they churn"** and **"which lever will most affect them."**

### Example Output
```
"Customers with early negative first-week experience AND late delivery
are 5x likelier to churn — not because of delivery delay, but because
they engage less with onboarding."

Recommended lever: Fix onboarding engagement (not delivery speed)
Confidence: High (p < 0.01, effect size: 0.73)
```

---

## Core Capabilities

1. **Causal Hypothesis Generation**: Generate testable causal hypotheses about retention drivers
2. **Statistical Validation**: Test hypotheses using causal inference techniques
3. **Confounder Detection**: Identify spurious correlations vs true causes
4. **Lever Identification**: Recommend which actions will have the most impact
5. **Explainability**: Generate human-readable reasoning chains

---

## Architecture Overview

### LangGraph Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    Retention Reasoning Agent                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
        ┌─────────────────────┴─────────────────────┐
        │                                            │
        ↓                                            ↓
┌──────────────────┐                    ┌──────────────────────┐
│ Opportunity      │                    │ Data Explorer        │
│ Detection Node   │                    │ Node                 │
└──────────────────┘                    └──────────────────────┘
        │                                            │
        │ "High churn in cohort X"                  │
        ↓                                            ↓
┌──────────────────┐                    ┌──────────────────────┐
│ Hypothesis       │◄───────────────────│ Feature Analyzer     │
│ Generator Node   │                    │ Node                 │
└──────────────────┘                    └──────────────────────┘
        │                                            │
        │ [H1, H2, H3, ...]                         │ Feature stats
        ↓                                            ↓
┌──────────────────┐                    ┌──────────────────────┐
│ Causal Inference │                    │ Cohort Builder       │
│ Testing Node     │◄───────────────────│ Node                 │
└──────────────────┘                    └──────────────────────┘
        │                                            │
        │ Validated hypotheses                      │
        ↓                                            ↓
┌──────────────────┐                    ┌──────────────────────┐
│ Confounder       │                    │ Statistical Tests    │
│ Analysis Node    │◄───────────────────│ Node                 │
└──────────────────┘                    └──────────────────────┘
        │                                            │
        │ True causes (deconfounded)                │
        ↓                                            ↓
┌──────────────────┐                    ┌──────────────────────┐
│ Lever Impact     │                    │ Intervention         │
│ Estimator Node   │◄───────────────────│ Simulator Node       │
└──────────────────┘                    └──────────────────────┘
        │                                            │
        │ Ranked interventions                      │
        ↓                                            ↓
┌──────────────────┐                    ┌──────────────────────┐
│ Explanation      │                    │ Evidence Collector   │
│ Generator Node   │◄───────────────────│ Node                 │
└──────────────────┘                    └──────────────────────┘
        │
        │ Reasoning chain + recommendations
        ↓
┌──────────────────┐
│ Strategy         │
│ Integration Node │
└──────────────────┘
        │
        │ Feeds into existing Strategy Agent
        ↓
  Campaign generation
```

---

## Node Specifications

### 1. Opportunity Detection Node

**Purpose**: Identify retention issues that warrant causal investigation

**Input**:
- Daily metrics from BigQuery
- Alert definitions from Supabase
- Historical performance data

**Logic**:
- Monitor churn rate, repeat rate, LTV trends
- Detect cohort-specific anomalies
- Flag opportunities with sufficient data for causal analysis (n > 100)

**Output**:
```python
{
    "opportunity_id": "high_churn_early_cohort_2025_q1",
    "type": "churn_spike",
    "affected_cohort": {"acquisition_date": "2025-01-01 to 2025-03-31"},
    "metric": "churn_rate_30d",
    "baseline": 0.15,
    "current": 0.32,
    "sample_size": 1247,
    "severity": "high"
}
```

---

### 2. Hypothesis Generator Node

**Purpose**: Generate testable causal hypotheses using LLM + domain knowledge

**Input**:
- Opportunity context
- Feature metadata from Supabase (100+ features)
- Historical causal patterns
- Business context (product info, recent campaigns, etc.)

**Logic**:
- Prompt LLM with feature descriptions and opportunity
- Generate 5-10 plausible hypotheses
- Include potential confounders
- Suggest data to test each hypothesis

**Prompt Template**:
```
You are a retention data scientist analyzing why customers churn.

Context:
- Opportunity: {opportunity_description}
- Affected cohort: {cohort_description}
- Available features: {feature_list}
- Business context: {recent_changes}

Generate 5-10 testable causal hypotheses that could explain this retention issue.
For each hypothesis:
1. State the proposed cause clearly
2. Explain the mechanism (why would this cause churn?)
3. Identify potential confounders
4. Suggest statistical tests to validate
5. Estimate likelihood (low/medium/high)

Format as structured JSON.
```

**Output**:
```python
{
    "hypotheses": [
        {
            "id": "h1",
            "cause": "late_first_delivery",
            "mechanism": "Customers frustrated by slow delivery disengage before second purchase window",
            "proposed_effect": "churn_30d",
            "confounders": ["order_value", "product_category", "seasonal_demand"],
            "test_methods": ["granger_causality", "propensity_matching"],
            "likelihood": "high",
            "data_requirements": ["delivery_timestamps", "churn_labels"]
        },
        {
            "id": "h2",
            "cause": "low_onboarding_engagement",
            "mechanism": "Users who don't engage with onboarding don't understand product value",
            "proposed_effect": "churn_30d",
            "confounders": ["prior_experience", "device_type", "acquisition_source"],
            "test_methods": ["regression_discontinuity", "iv_analysis"],
            "likelihood": "medium",
            "data_requirements": ["onboarding_events", "engagement_scores"]
        }
        // ... more hypotheses
    ]
}
```

---

### 3. Data Explorer Node

**Purpose**: Gather and prepare data for hypothesis testing

**Input**:
- Hypotheses from generator
- Feature requirements

**Logic**:
- Query BigQuery enriched_customers for required features
- Build analysis dataset with treatment, outcome, and confounders
- Compute summary statistics
- Check data quality (missing values, outliers, etc.)

**Output**:
```python
{
    "hypothesis_id": "h1",
    "dataset": {
        "n_samples": 1247,
        "features": ["late_first_delivery", "churn_30d", "order_value", "product_category"],
        "treatment_prevalence": 0.23,
        "outcome_prevalence": 0.32,
        "missing_data": {"late_first_delivery": 0.02, "order_value": 0.00},
        "correlation_matrix": {...}
    },
    "quality_score": 0.87
}
```

---

### 4. Causal Inference Testing Node

**Purpose**: Statistically test causal hypotheses using multiple methods

**Input**:
- Hypothesis
- Analysis dataset
- Test methods specified

**Techniques**:
1. **Granger Causality**: Does X temporally precede Y?
2. **Propensity Score Matching**: Compare matched treated/control groups
3. **Regression Discontinuity**: Exploit natural thresholds
4. **Instrumental Variables**: Find exogenous variation
5. **Difference-in-Differences**: Compare before/after treatment groups
6. **Causal DAGs**: Build directed acyclic graphs and test d-separation

**Logic**:
```python
def test_hypothesis(hypothesis, data):
    results = {}

    # Test 1: Granger causality
    results['granger'] = granger_causality_test(
        treatment=data[hypothesis.cause],
        outcome=data[hypothesis.effect],
        lags=7  # 7-day window
    )

    # Test 2: Propensity matching
    results['psm'] = propensity_score_matching(
        treatment=data[hypothesis.cause],
        outcome=data[hypothesis.effect],
        confounders=data[hypothesis.confounders],
        n_neighbors=5
    )

    # Test 3: Regression adjustment
    results['regression'] = regression_adjustment(
        treatment=data[hypothesis.cause],
        outcome=data[hypothesis.effect],
        controls=data[hypothesis.confounders]
    )

    # Aggregate evidence
    return aggregate_tests(results)
```

**Output**:
```python
{
    "hypothesis_id": "h1",
    "tests": [
        {
            "method": "granger_causality",
            "result": "significant",
            "p_value": 0.003,
            "effect_direction": "positive",
            "effect_size": 0.42,
            "confidence": "high"
        },
        {
            "method": "propensity_matching",
            "result": "significant",
            "p_value": 0.012,
            "ate": 0.17,  # average treatment effect
            "effect_size": 0.38,
            "confidence": "medium"
        }
    ],
    "consensus": {
        "causal": true,
        "effect_size": 0.40,  # meta-analysis across methods
        "confidence": "high",
        "effect_direction": "positive"
    }
}
```

---

### 5. Confounder Analysis Node

**Purpose**: Distinguish true causes from spurious correlations

**Input**:
- Validated hypotheses
- Feature correlation data

**Logic**:
- Build causal DAG (Directed Acyclic Graph)
- Test mediation (is effect direct or through another variable?)
- Detect colliders and confounders
- Use LLM to reason about causal structure

**Example**:
```
Initial hypothesis: late_delivery → churn

Confounder analysis discovers:
- late_delivery is correlated with low_onboarding_engagement
- low_onboarding_engagement → churn (stronger effect)
- late_delivery → low_onboarding_engagement (mediator)

Conclusion: late_delivery causes churn THROUGH reduced onboarding,
not directly. The true lever is onboarding engagement.
```

**Output**:
```python
{
    "hypothesis_id": "h1",
    "causal_structure": {
        "direct_effect": 0.08,  # late_delivery → churn (weak)
        "indirect_effect": 0.34,  # late_delivery → onboarding → churn (strong)
        "total_effect": 0.42,
        "mediators": ["low_onboarding_engagement"],
        "confounders": ["order_value"],
        "colliders": []
    },
    "true_cause": "low_onboarding_engagement",
    "proximate_cause": "late_delivery",
    "actionable_lever": "onboarding_engagement"
}
```

---

### 6. Lever Impact Estimator Node

**Purpose**: Rank interventions by expected impact

**Input**:
- Validated causal relationships
- Business constraints (cost, feasibility, timeline)

**Logic**:
- Estimate effect of intervention on outcome
- Consider intervention feasibility
- Calculate expected ROI
- Rank levers by impact × feasibility

**Output**:
```python
{
    "levers": [
        {
            "lever": "improve_onboarding_engagement",
            "mechanism": "Increase first-week app opens from 2.3 to 4.0",
            "expected_effect": {
                "churn_reduction": 0.17,  # 17 percentage points
                "affected_customers": 1247,
                "prevented_churn": 212,
                "ltv_impact": "$42,400"
            },
            "feasibility": {
                "cost": "low",
                "timeline": "2 weeks",
                "engineering_effort": "medium",
                "score": 0.85
            },
            "confidence": "high",
            "rank": 1
        },
        {
            "lever": "reduce_delivery_time",
            "mechanism": "Cut delivery time from 5.2 to 3.0 days",
            "expected_effect": {
                "churn_reduction": 0.08,  # indirect effect
                "affected_customers": 1247,
                "prevented_churn": 100,
                "ltv_impact": "$20,000"
            },
            "feasibility": {
                "cost": "high",
                "timeline": "3 months",
                "engineering_effort": "high",
                "score": 0.42
            },
            "confidence": "medium",
            "rank": 2
        }
    ]
}
```

---

### 7. Explanation Generator Node

**Purpose**: Create human-readable reasoning chains

**Input**:
- Causal analysis results
- Lever recommendations
- Evidence

**Logic**:
- Use LLM to synthesize findings into narrative
- Include evidence, confidence levels, and caveats
- Generate visualizations (causal graphs, effect plots)

**Output**:
```python
{
    "summary": "Customers with early negative first-week experience AND late delivery are 5x likelier to churn — not because of delivery delay, but because they engage less with onboarding.",
    "reasoning_chain": [
        {
            "step": 1,
            "claim": "Late delivery is correlated with 32% churn rate (vs 15% baseline)",
            "evidence": "Granger causality p=0.003, effect size d=0.42",
            "confidence": "high"
        },
        {
            "step": 2,
            "claim": "However, late delivery customers also have 60% lower onboarding engagement",
            "evidence": "Correlation r=0.67, p<0.001",
            "confidence": "high"
        },
        {
            "step": 3,
            "claim": "Mediation analysis shows the effect is indirect",
            "evidence": "Direct effect: 0.08, Indirect effect: 0.34 (through onboarding)",
            "confidence": "high"
        },
        {
            "step": 4,
            "claim": "The true driver is low onboarding engagement, not delivery speed",
            "evidence": "Propensity matching on onboarding engagement eliminates delivery effect",
            "confidence": "high"
        }
    ],
    "recommendation": {
        "primary_lever": "improve_onboarding_engagement",
        "expected_impact": "17 percentage point churn reduction (212 customers saved)",
        "secondary_levers": ["reduce_delivery_time", "improve_product_education"],
        "confidence": "high"
    },
    "caveats": [
        "Analysis limited to Q1 2025 cohort (n=1247)",
        "Effect may vary by product category",
        "Assumes onboarding intervention can achieve 4.0 engagement score"
    ]
}
```

---

## Data Model

### ReasoningSession (Supabase)
```python
{
    "session_id": UUID,
    "opportunity_id": str,
    "status": "in_progress" | "completed" | "failed",
    "hypotheses_count": int,
    "validated_causes": list[str],
    "recommended_levers": list[dict],
    "confidence_score": float,
    "created_at": timestamp,
    "updated_at": timestamp
}
```

### CausalHypothesis (Supabase)
```python
{
    "hypothesis_id": UUID,
    "session_id": UUID,
    "cause": str,
    "effect": str,
    "mechanism": str,
    "test_results": dict,
    "validated": bool,
    "confidence": float,
    "created_at": timestamp
}
```

### CausalGraph (Supabase)
```python
{
    "graph_id": UUID,
    "session_id": UUID,
    "nodes": list[dict],  # variables
    "edges": list[dict],  # causal relationships
    "strengths": dict,    # edge weights
    "created_at": timestamp
}
```

---

## Integration with Existing Pipeline

### Trigger Points
1. **Manual**: User requests "Why are Q1 customers churning?"
2. **Automatic**: Alert system flags anomaly → triggers reasoning agent
3. **Scheduled**: Weekly deep-dive on key cohorts

### Input to Strategy Agent
```python
{
    "insight_type": "causal_reasoning",
    "opportunity": {...},
    "root_causes": [...],
    "recommended_levers": [...],
    "confidence": 0.87,
    "reasoning_chain": [...]
}
```

### Strategy Agent Uses This To:
- Prioritize which lever to target (e.g., onboarding vs delivery)
- Craft more precise segments (customers with low onboarding engagement)
- Design interventions that address root causes
- Set realistic impact expectations

---

## Technical Stack

### Core Libraries
- **LangGraph**: Agent orchestration
- **Gemini/Claude**: LLM for reasoning
- **scikit-learn**: Statistical modeling
- **statsmodels**: Causal inference tests
- **DoWhy**: Causal inference framework (Microsoft Research)
- **NetworkX**: Causal graph construction
- **Pandas/Polars**: Data manipulation
- **BigQuery SDK**: Data access

### Dependencies
```toml
[dependencies]
langgraph = "^0.2.0"
langchain-google-genai = "^1.0.0"
dowhy = "^0.11"
statsmodels = "^0.14.0"
scikit-learn = "^1.4.0"
networkx = "^3.2"
polars = "^0.20.0"
google-cloud-bigquery = "^3.14.0"
pydantic = "^2.5.0"
```

---

## Performance Considerations

### Data Limits
- Minimum sample size: 100 per cohort
- Maximum features tested: 20 per hypothesis (combinatorial explosion)
- Query timeout: 30 seconds per BigQuery query

### Caching Strategy
- Cache feature statistics (daily refresh)
- Cache causal test results (1 week TTL)
- Cache similar opportunity patterns

### Optimization
- Parallel hypothesis testing (asyncio)
- Incremental DAG updates
- Approximate causal inference for large datasets

---

## Validation & Testing

### Unit Tests
- Each node's logic independently
- Statistical test correctness
- Edge cases (small samples, missing data)

### Integration Tests
- End-to-end reasoning pipeline
- BigQuery query correctness
- LangGraph state management

### Evaluation Metrics
1. **Precision**: % of validated hypotheses that are actually causal
2. **Recall**: % of true causes that are discovered
3. **Explanation Quality**: Human eval of reasoning chains
4. **Actionability**: % of recommendations that lead to campaign improvements

---

## Milestones

### Week 1: Foundation
- [x] Design architecture (this doc)
- [ ] Set up project structure
- [ ] Implement Opportunity Detection Node
- [ ] Implement Hypothesis Generator Node

### Week 2: Causal Inference
- [ ] Implement Data Explorer Node
- [ ] Implement Causal Inference Testing Node
- [ ] Integrate DoWhy framework

### Week 3: Advanced Analysis
- [ ] Implement Confounder Analysis Node
- [ ] Implement Lever Impact Estimator Node
- [ ] Build causal DAG visualization

### Week 4: Polish & Integration
- [ ] Implement Explanation Generator Node
- [ ] Integrate with existing Strategy Agent
- [ ] Testing and refinement
- [ ] Documentation

---

## Future Enhancements

1. **A/B Test Design**: Auto-generate test plans to validate hypotheses
2. **Temporal Causal Discovery**: Learn causal structure from time-series
3. **Heterogeneous Effects**: Identify sub-populations with different causal patterns
4. **Active Learning**: Suggest which data to collect to resolve uncertainty
5. **Counterfactual Simulation**: "What would have happened if we had intervened?"

---

## References

- **Causal Inference**: Pearl, J. (2009). Causality
- **DoWhy Framework**: https://github.com/py-why/dowhy
- **Granger Causality**: Granger, C.W.J. (1969)
- **Propensity Scores**: Rosenbaum & Rubin (1983)
- **DAG Methods**: Spirtes et al. (2000). Causation, Prediction, and Search
