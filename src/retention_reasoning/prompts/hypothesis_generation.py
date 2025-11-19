"""Prompts for hypothesis generation."""

HYPOTHESIS_GENERATION_SYSTEM_PROMPT = """You are a retention data scientist specializing in causal analysis.

Your goal is to generate testable causal hypotheses that explain retention issues (churn, low repeat rate, etc.).

For each hypothesis:
1. Identify a plausible CAUSE (a specific feature/behavior)
2. Explain the MECHANISM (why would this cause the outcome?)
3. List potential CONFOUNDERS (variables that might create spurious correlation)
4. List potential MEDIATORS (variables that mediate the effect)
5. Assess LIKELIHOOD (low, medium, high) based on domain knowledge
6. Suggest STATISTICAL TESTS to validate the hypothesis

Key principles:
- Focus on ACTIONABLE causes (things the business can influence)
- Consider both behavioral and structural factors
- Think about temporal ordering (cause must precede effect)
- Be skeptical of obvious correlations (look for confounders)
- Prioritize hypotheses with strong theoretical grounding

Output format: JSON array of hypotheses with the following structure:
{
  "hypotheses": [
    {
      "cause": "feature_name",
      "effect": "outcome_variable",
      "mechanism": "Explanation of why cause leads to effect",
      "confounders": ["confounder1", "confounder2"],
      "mediators": ["mediator1"],
      "moderators": [],
      "test_methods": ["granger_causality", "propensity_matching"],
      "data_requirements": ["feature1", "feature2"],
      "likelihood": "high",
      "rationale": "Why this hypothesis is plausible"
    }
  ]
}
"""


def generate_hypothesis_prompt(
    opportunity_context: str,
    available_features: list[str],
    business_context: str | None = None,
) -> str:
    """Generate the prompt for hypothesis generation.

    Args:
        opportunity_context: Context about the retention opportunity
        available_features: List of available features in the data
        business_context: Optional business context

    Returns:
        Formatted prompt
    """
    feature_list = "\n".join([f"- {f}" for f in available_features[:50]])  # Limit to 50

    business_section = ""
    if business_context:
        business_section = f"""
## Recent Business Context
{business_context}
"""

    return f"""
{opportunity_context}

## Available Features
The following features are available in the enriched_customers dataset:
{feature_list}
... and {len(available_features)} total features.

{business_section}

## Task
Generate 5-10 testable causal hypotheses that could explain this retention issue.

Focus on:
1. Behavioral patterns (engagement, usage, frequency)
2. Product experience (delivery, quality, support)
3. Economic factors (price sensitivity, promotions, value perception)
4. Lifecycle timing (onboarding, activation, habit formation)

For each hypothesis:
- Be specific about the causal variable (not vague like "customer satisfaction")
- Explain the causal mechanism clearly
- Identify potential confounders that could create spurious correlation
- Suggest appropriate statistical tests

Return ONLY a JSON object with the hypotheses array. No other text.
""".strip()


CONFOUNDER_ANALYSIS_SYSTEM_PROMPT = """You are a causal inference expert analyzing confounding structures.

Your goal is to distinguish true causal relationships from spurious correlations.

Given a hypothesis and statistical test results, determine:
1. Is the relationship truly causal or confounded?
2. Are there mediating variables (indirect effects)?
3. What is the actionable lever (where to intervene)?

Key principles:
- Confounders affect BOTH treatment and outcome
- Mediators are on the CAUSAL PATH (treatment → mediator → outcome)
- Colliders should NOT be conditioned on (can create spurious correlation)
- The strongest direct effect is usually the best intervention point

Output format: JSON with causal structure analysis.
"""


def generate_confounder_analysis_prompt(
    hypothesis_description: str,
    test_results_summary: str,
    correlation_data: str,
) -> str:
    """Generate prompt for confounder analysis.

    Args:
        hypothesis_description: Description of the hypothesis
        test_results_summary: Summary of statistical test results
        correlation_data: Correlation matrix data

    Returns:
        Formatted prompt
    """
    return f"""
## Hypothesis
{hypothesis_description}

## Statistical Test Results
{test_results_summary}

## Correlation Structure
{correlation_data}

## Task
Analyze the causal structure and determine:

1. **Direct vs Indirect Effects**
   - Is the effect direct or mediated through other variables?
   - Calculate direct effect, indirect effect, and total effect

2. **Confounder Detection**
   - Which variables confound the relationship?
   - Are the observed correlations spurious?

3. **Actionable Lever**
   - What is the true causal driver?
   - Where should we intervene for maximum impact?

Return a JSON object with this structure:
{{
  "direct_effect": 0.XX,
  "indirect_effect": 0.XX,
  "total_effect": 0.XX,
  "true_cause": "variable_name",
  "proximate_cause": "variable_name",
  "actionable_lever": "variable_name",
  "explanation": "Detailed explanation of the causal structure",
  "confidence": "high"
}}
""".strip()


LEVER_RECOMMENDATION_SYSTEM_PROMPT = """You are a retention strategy expert translating causal insights into actionable recommendations.

Your goal is to identify the most impactful interventions based on causal analysis.

For each potential lever:
1. Estimate the expected IMPACT (effect size, customers affected, LTV impact)
2. Assess FEASIBILITY (cost, timeline, effort required)
3. Consider BUSINESS CONSTRAINTS
4. Rank levers by (impact × feasibility)

Output format: JSON array of levers with impact estimates and feasibility assessments.
"""


def generate_lever_recommendation_prompt(
    causal_findings: str,
    opportunity_context: str,
) -> str:
    """Generate prompt for lever recommendations.

    Args:
        causal_findings: Summary of causal analysis findings
        opportunity_context: Context about the opportunity

    Returns:
        Formatted prompt
    """
    return f"""
## Causal Analysis Findings
{causal_findings}

## Opportunity Context
{opportunity_context}

## Task
Based on the causal analysis, recommend 3-5 actionable levers (interventions) to improve retention.

For each lever, provide:

1. **Intervention Description**
   - What specific action should be taken?
   - What metric/behavior will it change?

2. **Impact Estimate**
   - Expected effect size
   - Number of customers affected
   - Prevented churn / increased repeat rate
   - LTV / revenue impact

3. **Feasibility Assessment**
   - Cost (low, medium, high)
   - Timeline (e.g., "2 weeks", "3 months")
   - Engineering effort (low, medium, high)
   - Marketing effort (low, medium, high)
   - Dependencies and blockers

4. **Confidence Level**
   - How confident are you in this recommendation?

Return a JSON object with this structure:
{{
  "levers": [
    {{
      "name": "Lever name",
      "description": "Detailed description",
      "mechanism": "How this lever affects the outcome",
      "target_variable": "variable_to_modify",
      "expected_effect": {{
        "absolute_effect": 0.XX,
        "relative_effect": 0.XX,
        "affected_customers": XXXX,
        "prevented_churn": XXX,
        "ltv_impact": XXXXX
      }},
      "feasibility": {{
        "cost": "low",
        "timeline": "2 weeks",
        "engineering_effort": "medium",
        "score": 0.XX
      }},
      "confidence": "high"
    }}
  ]
}}
""".strip()


EXPLANATION_GENERATION_SYSTEM_PROMPT = """You are a data storyteller translating complex causal analysis into clear, actionable insights.

Your goal is to create compelling narratives that explain:
1. WHAT we discovered (the causal finding)
2. WHY it matters (business impact)
3. HOW we know (evidence quality)
4. WHAT to do (recommendations)

Key principles:
- Lead with the insight, not the methodology
- Use concrete numbers and examples
- Acknowledge uncertainty and caveats
- Make recommendations specific and actionable

Output format: Structured reasoning chain with narrative flow.
"""


def generate_explanation_prompt(
    opportunity: str,
    hypotheses_tested: str,
    validated_causes: str,
    recommended_levers: str,
) -> str:
    """Generate prompt for explanation generation.

    Args:
        opportunity: Opportunity description
        hypotheses_tested: Summary of hypotheses tested
        validated_causes: Validated causal relationships
        recommended_levers: Recommended interventions

    Returns:
        Formatted prompt
    """
    return f"""
## Retention Issue
{opportunity}

## Hypotheses Tested
{hypotheses_tested}

## Validated Causes
{validated_causes}

## Recommended Levers
{recommended_levers}

## Task
Create a clear, compelling explanation of the causal analysis that a marketing manager can understand and act on.

Include:

1. **One-Sentence Summary**
   - What is the key finding?

2. **Step-by-Step Reasoning**
   - Walk through the causal logic (3-5 steps)
   - For each step: claim + evidence + confidence level

3. **Recommendations**
   - Primary lever (highest impact)
   - Expected impact (specific numbers)
   - Secondary levers

4. **Caveats**
   - Important limitations or assumptions
   - What we don't know

Return a JSON object with this structure:
{{
  "summary": "One-sentence summary",
  "conclusion": "Overall conclusion",
  "reasoning_steps": [
    {{
      "step_number": 1,
      "claim": "The claim",
      "evidence": "Supporting evidence",
      "confidence": "high",
      "reasoning": "Explanation of the logic"
    }}
  ],
  "primary_lever": "Lever name",
  "expected_impact": "Specific impact estimate",
  "secondary_levers": ["Lever 2", "Lever 3"],
  "overall_confidence": 0.XX,
  "caveats": ["Caveat 1", "Caveat 2"]
}}
""".strip()
