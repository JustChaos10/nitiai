# Retention Reasoning Agent (RRA)

A sophisticated AI-powered system for analyzing customer retention patterns, identifying churn risks, and generating actionable business recommendations using causal inference and LLM-based reasoning.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Running the Application](#running-the-application)
5. [API Reference](#api-reference)
6. [Input Format](#input-format)
7. [Opportunity Types](#opportunity-types)
8. [Frontend Interface](#frontend-interface)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Retention Reasoning Agent is a complete end-to-end system that:

- **Analyzes retention data** to identify patterns and anomalies
- **Generates causal hypotheses** about why retention issues occur
- **Tests hypotheses** using statistical methods and causal inference
- **Identifies confounders** that may affect analysis
- **Estimates intervention levers** with expected ROI
- **Produces actionable explanations** for business stakeholders

### Key Features

- 🧠 **LLM-Powered Analysis**: Uses Groq LLM for intelligent hypothesis generation
- 📊 **Causal Inference**: DoWhy-based causal testing and confounder analysis
- 🔄 **LangGraph Pipeline**: Structured multi-step reasoning workflow
- 🛰️ **Event-Level Enrichment**: Aggregates delivery delays, onboarding steps, support tickets, and campaign engagement directly from the events stream
- 🧪 **Synthetic Ground Truth**: Ships with curated CSVs encoding known causal relationships for validation
- 🎨 **Modern UI**: Crayon/Thesys-powered chat interface with reasoning visualization
- 📈 **Statistical Testing**: Chi-square, t-tests, regression, propensity matching, and Granger causality
- 🎯 **Actionable Outputs**: Prioritized interventions with confidence scores

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RETENTION REASONING AGENT                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │   FastAPI    │───▶│  LangGraph   │───▶│    Groq      │           │
│  │   Backend    │    │   Pipeline   │    │     LLM      │           │
│  │  (Port 8000) │    │              │    │              │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│         │                   │                                        │
│         │                   ▼                                        │
│         │           ┌──────────────┐                                │
│         │           │    DoWhy     │                                │
│         │           │   Causal     │                                │
│         │           │  Inference   │                                │
│         │           └──────────────┘                                │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────┐                                                   │
│  │   Next.js    │                                                   │
│  │   Frontend   │                                                   │
│  │  (Port 3000) │                                                   │
│  │  Thesys C1   │                                                   │
│  └──────────────┘                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### LangGraph Processing Pipeline

The reasoning agent processes data through 5 specialized nodes:

```
┌───────────────────┐
│  1. HYPOTHESIS    │  Generate initial hypotheses about retention issues
│     GENERATOR     │  using LLM analysis of input data
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  2. CAUSAL        │  Test hypotheses using DoWhy causal inference
│     TESTER        │  and statistical methods
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  3. CONFOUNDER    │  Identify confounding variables that may
│     ANALYZER      │  affect the analysis
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  4. LEVER         │  Estimate intervention effectiveness and
│     ESTIMATOR     │  expected ROI for each action
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  5. EXPLANATION   │  Generate human-readable explanations
│     GENERATOR     │  and recommendations
└───────────────────┘
```

### Backend Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| API Server | FastAPI + Uvicorn | REST API and streaming |
| Orchestration | LangGraph | Multi-step reasoning workflow |
| LLM | Groq (llama3-70b-8192) | Hypothesis generation & explanation |
| Causal Inference | DoWhy | Causal testing & effect estimation |
| Statistics | SciPy, NumPy, Pandas | Statistical analysis |

### Frontend Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | Next.js 15 + React 19 | Full-stack React framework |
| Build Tool | Turbopack | Fast development & bundling |
| Chat UI | @thesysai/genui-sdk (C1) | AI-powered conversational interface |
| UI Components | @crayonai/react-ui | Styled chat components |
| Styling | Tailwind CSS | Utility-first styling |

### Data Sources & Enrichment

The repo ships with a synthetic-but-realistic retention dataset under `data/`:

| File | Description | Sample Rows |
|------|-------------|-------------|
| `retention_customers.csv` | Customer-level snapshot (600 rows) with churn labels, RFM scores, channels, etc. | 600 |
| `retention_events.csv` | Event stream (~10k rows) covering deliveries, onboarding steps, support tickets, sessions, and campaigns. | 10,696 |
| `retention_brand_metrics_daily.csv` | Daily aggregate metrics for trend visualizations. | 3,240 |
| `shopify_retention_synthetic_dataset.csv` | Alternate customer dataset for experimentation. | 500 |

`DataIngestionService` automatically:

1. Loads these CSVs (or user uploads via `/upload`).
2. Aggregates events into customer-level causal signals such as `avg_delivery_delay`, `max_delivery_delay`, `had_late_delivery`, `completed_onboarding`, `num_support_tickets`, `session_count`, and `email_open_rate`.
3. Builds composite risk flags (`high_delay_customer`, `high_causal_risk`, etc.) so downstream nodes can reason about treatment/control cohorts.

Back-end endpoints like `/context`, `/data/summary`, and `/analyze/from-data` consume the enriched dataset directly, so the LLM always sees experience-level signals instead of just static demographic fields.

---

## Installation

### Prerequisites

- **Python 3.11+** (required for backend)
- **Node.js 18+** (required for frontend)
- **Groq API Key** (get one at https://console.groq.com)

### Step 1: Clone and Setup Environment

```bash
# Navigate to project directory
cd RRA

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows CMD:
venv\Scripts\activate.bat

# Linux/macOS:
source venv/bin/activate
```

### Step 2: Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Or set it directly:

```bash
# Windows PowerShell
$env:GROQ_API_KEY="your_groq_api_key_here"

# Linux/macOS
export GROQ_API_KEY="your_groq_api_key_here"
```

### Step 4: Install Frontend Dependencies

```bash
cd frontend
npm install
```

---

## Running the Application

### Quick Start (Both Backend & Frontend)

**Terminal 1 - Start Backend:**
```bash
cd RRA
.\venv\Scripts\Activate.ps1  # Activate venv
uvicorn src.retention_reasoning.api:create_app --factory --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
cd RRA/frontend
npm run dev
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend UI** | http://localhost:3000 | Thesys C1 chat interface |
| **Backend API** | http://localhost:8000 | REST API endpoints |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger documentation |
| **Health Check** | http://localhost:8000/health | Backend status endpoint |

After the backend boots the default synthetic data is loaded automatically. If you want to swap in your own CSVs:

1. Call `POST /upload` with `customers`, `events`, and optional `metrics` files.
2. Visit `GET /data/summary` or `GET /context` to verify the new feature columns and row counts.
3. Run `POST /analyze/from-data` (or use the frontend “Analyze current data” flow) to execute the full reasoning loop on the enriched dataset.

---

## API Reference

### Core Endpoints

#### POST `/analyze`
Start a new retention analysis session.

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "opportunity": {
      "type": "churn_spike",
      "title": "High churn in recent cohort",
      "description": "Recent customers show elevated churn rates",
      "affected_cohort": {"description": "Premium users"},
      "metric_name": "churn_30d",
      "baseline_value": 0.08,
      "current_value": 0.15,
      "sample_size": 5000,
      "severity": "high",
      "business_context": {"recent_changes": "Pricing increase"}
    },
    "business_context": "Premium users showing 87% higher churn after price increase",
    "data_preview": null
  }'
```

#### POST `/stream`
Server-Sent Events stream of the same payload and response as `/analyze`.

```bash
curl -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"opportunity": {...}}'
```

#### GET `/health`
Simple readiness endpoint that returns `{"status": "ok"}`.

#### POST `/ab-test`
Design statistically powered experiments for validated hypotheses.

```bash
curl -X POST http://localhost:8000/ab-test \
  -H "Content-Type: application/json" \
  -d '{
    "hypotheses": [{"id": "h1", "cause": "late_delivery", "effect": "churn_30d"}],
    "baseline_rates": {"churn_30d": 0.12},
    "daily_traffic": 5000
  }'
```

#### POST `/heterogeneous`
Analyze treatment-effect heterogeneity across subgroups. Expects `data`, `treatment_col`, `outcome_col`, and `subgroup_features`.

#### POST `/simulate`
Run counterfactual simulations for a proposed intervention using the uploaded dataset and `InterventionScenario`.

#### POST `/uncertainty`
Quantify hypothesis uncertainty and recommend next data collection steps.

#### POST `/upload`
Upload `customers`, `events`, and optional `metrics_daily` CSV/Excel files. Populates the in-memory cache used by `/context` and `/analyze/from-data`.

#### GET `/data/summary`
Returns schema, row counts, and sample records for each loaded table plus derived feature lists.

#### GET `/context`
Returns aggregate metrics, trends, insights, and available features for the current data cache (used by the frontend to prime prompts).

#### POST `/chat/context`
Lightweight variant that returns just-enough context (metrics, insights, feature names) for a single chat thread.

#### POST `/analyze/from-data`
Runs the full reasoning pipeline directly on the cached/enriched dataset (no JSON payload required). Accepts optional `brand_id`, `metric_name`, and free-form `business_context`.

---

## Input Format

### JSON Input Schema

The agent accepts input in the following JSON format:

```json
{
  "opportunity": {
    "type": "string (required - see Opportunity Types)",
    "title": "string",
    "description": "string",
    "affected_cohort": {"description": "string"},
    "metric_name": "string",
    "baseline_value": 0.42,
    "current_value": 0.18,
    "sample_size": 500,
    "severity": "low|medium|high",
    "business_context": {"recent_changes": "string"}
  },
  "data_preview": [
    {"feature_a": 1, "feature_b": 0.35, "...": "..."}
  ],
  "business_context": "Optional free-form note surfaced to the LLM"
}
```

- `opportunity` mirrors the Pydantic `Opportunity` model (`src/retention_reasoning/models/opportunity.py`) and automatically derives `change_magnitude`/`change_percent`.
- `data_preview` (or the legacy alias `data`) is optional tabular data used for quick statistical validation; leave as `null` if you only want qualitative reasoning.
- `business_context` (string) supplements the structured context on the opportunity itself.

### Example Input

```json
{
  "opportunity": {
    "type": "engagement_drop",
    "title": "Free Trial to Paid Conversion Decline",
    "description": "Trial users not converting despite high signup volume",
    "affected_cohort": {"description": "14-day free trial users from Q3 2024"},
    "metric_name": "converted_to_paid",
    "baseline_value": 0.42,
    "current_value": 0.18,
    "sample_size": 50,
    "severity": "high",
    "business_context": {
      "recent_changes": "New paywall introduced, moved advanced features to paid tier"
    }
  },
  "data_preview": [
    {"trial_duration_days": 14, "feature_discovery_score": 85, "converted_to_paid": 1},
    {"trial_duration_days": 3, "feature_discovery_score": 25, "converted_to_paid": 0}
  ],
  "business_context": "Aggressive paywall placement causing friction"
}
```

---

## Opportunity Types

The system supports exactly **5 opportunity types**. Each type triggers specialized analysis:

### 1. `churn_spike`
**Use Case:** Sudden increase in customer churn rate

**Key Metrics:**
- `churn_rate` - Current churn rate
- `baseline_churn` - Historical baseline
- `sample_size` - Number of customers

**Analysis Focus:** Identifies root causes of churn acceleration, tests pricing, product, and service-related hypotheses.

---

### 2. `repeat_rate_drop`
**Use Case:** Decline in customer repeat purchase behavior

**Key Metrics:**
- `repeat_rate` - Current repeat purchase rate
- `baseline_repeat` - Historical baseline
- `cohort_size` - Number of customers analyzed

**Analysis Focus:** Examines purchase frequency patterns, product satisfaction, and competitive factors.

---

### 3. `ltv_decline`
**Use Case:** Decrease in customer lifetime value

**Key Metrics:**
- `current_ltv` - Current average LTV
- `historical_ltv` - Historical LTV
- `decline_percentage` - Rate of decline

**Analysis Focus:** Investigates revenue per customer trends, upsell effectiveness, and retention economics.

---

### 4. `engagement_drop`
**Use Case:** Reduction in product/service engagement

**Key Metrics:**
- `engagement_score` or `session_duration`
- `daily_active_users` / `weekly_active_users`
- `baseline` metrics for comparison

**Analysis Focus:** Analyzes feature usage, user experience issues, and engagement barriers.

---

### 5. `cohort_anomaly`
**Use Case:** Unusual behavior in a specific customer cohort

**Key Metrics:**
- `retention_day_X` - Retention at day X
- `expected_retention` - Expected value
- `cohort_size` - Cohort population
- `anomaly_score` - Statistical deviation

**Analysis Focus:** Compares cohort performance against baselines, identifies cohort-specific factors.

---

## Frontend Interface

### Chat Interface

The frontend provides a conversational chat interface powered by Thesys C1:

1. **Open** http://localhost:3000 in your browser
2. **Enter** your analysis request in natural language or paste JSON input
3. **View** the reasoning process in real-time
4. **Explore** the hypothesis graph and recommendations

### Features

- **Real-time Streaming:** Watch the agent's reasoning process as it happens
- **Hypothesis Visualization:** Interactive graph showing hypothesis relationships
- **Dark Theme:** Modern dark UI optimized for extended use
- **Markdown Support:** Rich formatting in responses

### Example Chat Prompts

```
Analyze why our premium users are churning at 15% when baseline is 8%
```

```
Our mobile app engagement dropped 50% after the last update. What's causing this?
```

```
January cohort has 25% day-30 retention vs expected 42%. Why?
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | - | Groq API key for LLM access |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Model name passed to `ChatGroq` |
| `GROQ_TEMPERATURE` | No | `0.2` | Sampling temperature for hypothesis/explanation generation |
| `GROQ_MAX_OUTPUT` | No | `4096` | Max tokens returned by the Groq client |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `CORS_ALLOW_ORIGINS` | No | `*` | Comma-separated origins for the FastAPI middleware |

### Business Rules Configuration

Edit `src/retention_reasoning/utils/config.py` for:

- Confidence thresholds
- Statistical significance levels
- ROI calculation parameters
- Hypothesis generation limits

### Frontend Configuration

Edit `frontend/next.config.ts` for:

- API proxy settings
- Build optimization

The frontend uses Thesys C1 SDK which connects to the Python backend at `http://localhost:8000` for context. Set `PYTHON_API_URL` environment variable to change this.

---

## Troubleshooting

### Common Issues

#### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'retention_reasoning'`

**Solution:** Make sure you're in the project root and venv is activated:
```bash
cd RRA
.\venv\Scripts\Activate.ps1
pip install -e .
```

---

#### Groq API errors

**Error:** `AuthenticationError` or `Invalid API Key`

**Solution:** Verify your API key:
```bash
$env:GROQ_API_KEY="your_actual_key_here"
```

---

#### Frontend can't connect to backend

**Error:** `Network Error` or `CORS error`

**Solution:** 
1. Ensure backend is running on port 8000
2. Check the `PYTHON_API_URL` environment variable in `frontend/.env.local`
3. Verify both services are running

---

#### Port already in use

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port (Windows)
netstat -ano | findstr :8000

# Kill process
taskkill /PID <process_id> /F
```

---

#### Frontend styling issues

**Error:** Fonts merging with background, broken layout

**Solution:** The styles in `frontend/src/app/globals.css` must be properly imported. If styling breaks, ensure Tailwind CSS is configured correctly.

---

### Verifying Installation

Run the integration tests:

```bash
cd RRA
.\venv\Scripts\Activate.ps1
python -m pytest test_integration.py -v
```

Run unit tests:

```bash
python -m pytest src/retention_reasoning/tests/ -v
```

---

## Project Structure

```
RRA/
├── src/
│   └── retention_reasoning/
│       ├── agent.py           # LangGraph agent orchestration
│       ├── api.py             # FastAPI endpoints
│       ├── models/            # Pydantic data models
│       │   ├── hypothesis.py  # Hypothesis model
│       │   ├── lever.py       # Intervention lever model
│       │   ├── opportunity.py # Opportunity types enum
│       │   └── reasoning.py   # Reasoning state model
│       ├── nodes/             # LangGraph processing nodes
│       │   ├── hypothesis_generator.py
│       │   ├── causal_tester.py
│       │   ├── confounder_analyzer.py
│       │   ├── lever_estimator.py
│       │   └── explanation_generator.py
│       ├── services/          # Business logic services
│       │   ├── ab_testing.py
│       │   ├── segmentation.py
│       │   ├── strategy.py
│       │   └── exporters.py
│       ├── utils/             # Utilities
│       │   ├── causal_inference.py
│       │   ├── statistical_tests.py
│       │   └── config.py
│       └── tests/             # Unit tests
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx       # Main page with C1 chat
│   │       ├── layout.tsx     # Root layout
│   │       ├── globals.css    # Global styles
│   │       └── api/
│   │           ├── chat/      # Chat API route (Thesys)
│   │           └── retention/ # Backend proxy routes
│   ├── package.json
│   └── next.config.ts
├── examples/                  # Usage examples
├── requirements.txt           # Python dependencies
└── pyproject.toml            # Project metadata
```

---

## Response Format

The agent returns structured JSON responses:

```json
{
  "session_id": "uuid",
  "status": "completed",
  "validated_causes": ["late_onboarding", "paywall_spam"],
  "recommended_levers": [
    "Restore advanced features during trial",
    "Add onboarding guardrails for short trials"
  ],
  "explanation": "Narrative summary of the validated hypotheses and levers.",
  "hypotheses": [
    {
      "id": "h1",
      "cause": "high_paywall_encounters",
      "effect": "converted_to_paid",
      "mechanism": "Users convert less when blocked before value discovery",
      "validated": true,
      "confidence": 0.81,
      "p_value": 0.02,
      "effect_size": 0.45,
      "causal_structure": {
        "direct_effect": 0.31,
        "indirect_effect": 0.11,
        "total_effect": 0.42,
        "mediators": ["feature_discovery_score"],
        "actionable_lever": "paywall_policy"
      }
    }
  ],
  "causal_graph": {
    "nodes": ["high_paywall_encounters", "feature_discovery_score", "converted_to_paid"],
    "edges": [
      {"from": "high_paywall_encounters", "to": "feature_discovery_score", "strength": 0.4, "type": "indirect"},
      {"from": "feature_discovery_score", "to": "converted_to_paid", "strength": 0.4, "type": "indirect"},
      {"from": "high_paywall_encounters", "to": "converted_to_paid", "strength": 0.3, "type": "direct"}
    ]
  }
}
```

---

## Support

For issues or questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review API documentation at http://localhost:8000/docs
3. Examine test files for usage examples

---

## License

This project is proprietary software. All rights reserved.
