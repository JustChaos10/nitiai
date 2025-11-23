# Quick Start Guide - Test Everything in 5 Minutes

## Prerequisites
- Python 3.10+
- Node.js 18+
- Git

## Step 1: Install Backend Dependencies (2 min)

```bash
# In project root
pip install -r requirements.txt
```

## Step 2: Install Frontend Dependencies (1 min)

```bash
cd frontend/crayon
npm install
cd ../..
```

## Step 3: Set Up Environment (.env file)

```bash
# Create .env file
cat > .env << 'EOF'
# LLM Configuration (choose one)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TEMPERATURE=0.7
GROQ_MAX_OUTPUT=4096

# Or use Google Gemini
# GOOGLE_API_KEY=your_google_api_key_here

# Or use Anthropic Claude
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# API Configuration
CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:3000
EOF
```

## Step 4: Test Backend (1 min)

### Option A: Run Example Script

```bash
# Make sure you have an API key configured in .env
python examples/advanced_features_example.py
```

**Expected output**: Demonstrations of all 5 features with sample data

### Option B: Start API Server

```bash
# Terminal 1: Start API server
uvicorn src.retention_reasoning.api:create_app --factory --reload --port 8000
```

Visit http://localhost:8000/health to verify it's running.

### Option C: Quick API Test

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected: {"status":"ok"}
```

## Step 5: Test Frontend (1 min)

```bash
# Terminal 2: Start frontend dev server
cd frontend/crayon
npm run dev
```

Visit http://localhost:5173

> **Tip:** If your backend is not running on `http://localhost:8000`, create a `frontend/crayon/.env` file with `VITE_API_BASE=<your_api_url>` so the Crayon UI talks to the right server.

**Expected**:
- Crayon UI loads
- Three tabs: Chat, Hypotheses, Causal Graph
- Default opportunity JSON in input field

## Step 6: Test End-to-End Flow

### Via Frontend UI

1. Go to http://localhost:5173
2. Paste this test payload (or use the default):

```json
{
  "opportunity": {
    "title": "High churn in recent cohort",
    "description": "Recent customers show elevated churn rates",
    "metric_name": "churn_30d",
    "baseline_value": 0.15,
    "current_value": 0.32,
    "sample_size": 500,
    "severity": "high",
    "type": "churn_spike"
  },
  "business_context": "Recent shipping delays"
}
```

3. Press Enter
4. **Expected Results**:
   - Chat tab shows validated causes and explanation
   - Hypotheses tab displays hypothesis cards (if any validated)
   - Causal Graph tab shows visual DAG (if validated hypotheses exist)

### Via API (cURL)

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "opportunity": {
      "title": "Test churn",
      "description": "Test",
      "metric_name": "churn_30d",
      "baseline_value": 0.15,
      "current_value": 0.32,
      "sample_size": 100,
      "severity": "high",
      "type": "churn_spike"
    },
    "business_context": "Test"
  }'
```

## Step 7: Test Advanced Features

### Test A/B Test Generation

```bash
curl -X POST http://localhost:8000/ab-test \
  -H "Content-Type: application/json" \
  -d '{
    "hypotheses": [{
      "id": "h1",
      "cause": "late_delivery",
      "effect": "churn_30d",
      "mechanism": "Frustration leads to churn"
    }],
    "baseline_rates": {"churn_30d": 0.20},
    "daily_traffic": 1000
  }'
```

**Expected**: Test design with sample sizes, duration, metrics

### Test Intervention Simulation

```bash
curl -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"delivery_days": 5, "churn_30d": 0},
      {"delivery_days": 7, "churn_30d": 1},
      {"delivery_days": 4, "churn_30d": 0}
    ],
    "intervention_name": "Speed up delivery",
    "target_variable": "delivery_days",
    "intervention_type": "shift",
    "intervention_value": -2.0,
    "outcome_variable": "churn_30d"
  }'
```

**Expected**: Baseline vs simulated outcomes, predicted impact

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'retention_reasoning'"

**Solution**: Install in editable mode
```bash
pip install -e .
```

Or set PYTHONPATH:
```bash
export PYTHONPATH=/home/user/nitiai:$PYTHONPATH
```

### "No module named 'networkx'"

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### "ImportError: FastAPI is required"

**Solution**: Install FastAPI
```bash
pip install fastapi uvicorn
```

### Frontend won't start

**Solution**: Install dependencies
```bash
cd frontend/crayon
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### "reactflow not found"

**Solution**: Already in package.json, just run:
```bash
cd frontend/crayon
npm install
```

---

## Verification Checklist

- [ ] Backend dependencies installed
- [ ] Frontend dependencies installed
- [ ] .env file created with API key
- [ ] Example script runs successfully
- [ ] API server starts on port 8000
- [ ] Health endpoint returns {"status":"ok"}
- [ ] Frontend loads on port 5173
- [ ] Can submit opportunity through UI
- [ ] Advanced endpoints respond to cURL tests

---

## Success Criteria

✅ **All systems working** if you can:
1. Run the example script without errors
2. Start the API server
3. Access the health endpoint
4. Load the frontend UI
5. See the three tabs (Chat, Hypotheses, Graph)
6. Submit an opportunity and get a response

---

## Next Steps After Verification

1. **Add real data**: Connect to BigQuery or provide CSV data
2. **Configure LLM**: Set up your preferred LLM provider (Groq, Gemini, Claude)
3. **Test with production data**: Run analysis on actual customer data
4. **Deploy**: Set up production environment with proper infrastructure

---

## Quick Demo Script

```bash
#!/bin/bash
# Run this to test everything at once

echo "🚀 Testing Retention Reasoning Agent"
echo ""

echo "1. Testing imports..."
python -c "from src.retention_reasoning.utils import get_cache; print('✅ Imports work')" || echo "❌ Install dependencies first"

echo ""
echo "2. Starting API server in background..."
uvicorn src.retention_reasoning.api:create_app --factory --port 8000 &
API_PID=$!
sleep 3

echo ""
echo "3. Testing health endpoint..."
curl -s http://localhost:8000/health

echo ""
echo "4. Killing API server..."
kill $API_PID 2>/dev/null

echo ""
echo "✅ Basic tests complete!"
echo ""
echo "To test fully:"
echo "  1. pip install -r requirements.txt"
echo "  2. cd frontend/crayon && npm install"
echo "  3. Set GROQ_API_KEY in .env"
echo "  4. python examples/advanced_features_example.py"
```

Save as `test.sh`, make executable with `chmod +x test.sh`, then run `./test.sh`
