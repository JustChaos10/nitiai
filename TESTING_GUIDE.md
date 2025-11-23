# 🧪 Testing Guide - Retention Reasoning Agent

## ✅ What's Been Generated for You

I've created **sample data files** so you can test the system without needing to prepare your own data:

| File | Description | Size |
|------|-------------|------|
| **sample_data.csv** | 200 customer records with realistic retention data | 6.8 KB |
| **api_test_payload.json** | Ready-to-use JSON payload for API testing | 648 B |
| **test_with_sample_data.py** | Script to preview data and see testing instructions | 7.5 KB |

---

## 📊 Sample Data Overview

The sample data contains **200 customer records** with:

- **Churn rate**: 45.5% (elevated from baseline of 15%)
- **Average delivery time**: 5.6 days
- **Average engagement score**: 5.5/10
- **Product categories**: Electronics (34%), Clothing (33%), Home (33%)

### Key Insight in the Data

The data has a **built-in causal pattern** that the agent should discover:

```
📦 Late Delivery → 😞 Low Engagement → 💔 High Churn
```

**Evidence**:
- Churned customers: avg 7.8 delivery days, 3.4 engagement score
- Active customers: avg 3.9 delivery days, 7.3 engagement score

---

## 🚀 How to Test (3 Methods)

### ⚠️ FIRST: Get Your Free API Key

The system uses **Groq** (fast, free LLM API) for reasoning:

1. Go to: https://console.groq.com/
2. Sign up for free account (no credit card needed)
3. Go to "API Keys" section
4. Create new API key
5. Copy the key (starts with `gsk_...`)

Then set it in your terminal:
```bash
export GROQ_API_KEY='gsk_your_key_here'
```

---

### 🔧 METHOD 1: Quick Python Script Test

**Best for**: Quick testing without running servers

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key
export GROQ_API_KEY='your_key_here'

# 3. Run example (generates its own data)
python examples/simple_example.py
```

**What you'll see**: Full causal analysis showing validated hypotheses, confidence scores, and actionable levers.

---

### 🌐 METHOD 2: API Endpoint Test

**Best for**: Testing the backend API directly

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key
export GROQ_API_KEY='your_key_here'

# 3. Start API server
uvicorn src.retention_reasoning.api:create_app --factory --reload

# 4. In ANOTHER terminal, test the API
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d @api_test_payload.json
```

**What you'll see**: JSON response with hypotheses, validated causes, confidence scores, and causal graph.

---

### 🎨 METHOD 3: Full UI Test

**Best for**: Visual testing with chat interface and graph visualization

```bash
# 1. Install backend dependencies
pip install -r requirements.txt

# 2. Install frontend dependencies
cd frontend/crayon
npm install
cd ../..

# 3. Set API key
export GROQ_API_KEY='your_key_here'

# 4. Start backend (Terminal 1)
uvicorn src.retention_reasoning.api:create_app --factory --reload

# 5. Start frontend (Terminal 2)
cd frontend/crayon
npm run dev
```

**Then**:
1. Open browser: http://localhost:5173
2. You'll see a chat interface
3. Paste this into the input box:

```json
{
  "opportunity": {
    "type": "churn_spike",
    "title": "High churn in recent cohort",
    "description": "Customers acquired recently show elevated churn rates",
    "affected_cohort": {
      "description": "Recent customers with delivery issues"
    },
    "metric_name": "churn_30d",
    "baseline_value": 0.15,
    "current_value": 0.455,
    "sample_size": 200,
    "severity": "high",
    "business_context": {
      "recent_changes": "Warehouse delays causing longer delivery times",
      "product_mix": "Mix of electronics, clothing, and home goods"
    }
  },
  "business_context": "Recent shipping delays due to warehouse issues"
}
```

**What you'll see**:
- **Chat Tab**: Analysis results with validated causes
- **Hypotheses Tab**: Interactive cards showing each hypothesis
- **Graph Tab**: Visual causal diagram (ReactFlow visualization)

---

## 📁 Sample Data Schema

```csv
customer_id,first_delivery_days,onboarding_engagement_score,order_value,product_category,churn_30d
cust_001,3.2,7.5,120.50,electronics,0
cust_002,6.8,4.2,85.00,clothing,1
...
```

**Column Descriptions**:
- `customer_id`: Unique identifier (cust_001 to cust_200)
- `first_delivery_days`: Days until first delivery (1-10 days)
- `onboarding_engagement_score`: Engagement during onboarding (0-10 scale)
- `order_value`: First order amount ($60-$165)
- `product_category`: Product type (electronics, clothing, home)
- `churn_30d`: Whether customer churned within 30 days (0=active, 1=churned)

---

## 🎯 What the Agent Should Discover

Based on the sample data patterns, the agent should find:

### Expected Hypotheses:
1. **Late delivery → Higher churn** (direct effect)
2. **Late delivery → Lower engagement** (mediation)
3. **Low engagement → Higher churn** (primary cause)

### Expected Recommendation:
**Improve onboarding engagement** (not just faster delivery) because:
- Engagement is the mediating variable
- It has stronger direct effect on churn
- It's more actionable than delivery logistics

### Expected Confidence:
- High (>70%) because the pattern is clear in the data
- Multiple statistical tests should validate

---

## 🔍 Preview Your Data

To see data statistics before testing:

```bash
python3 test_with_sample_data.py
```

This will show:
- Churn rates
- Correlation between features
- Expected causal patterns
- All testing instructions

---

## ❓ Troubleshooting

### "ModuleNotFoundError"
→ Run: `pip install -r requirements.txt`

### "GROQ_API_KEY not set"
→ Get key from https://console.groq.com/ and run: `export GROQ_API_KEY='your_key'`

### "Port already in use"
→ Backend runs on port 8000, frontend on 5173. Kill existing processes or change ports.

### Frontend won't start
→ Make sure you're in `frontend/crayon` directory and ran `npm install`

### API returns empty results
→ Check that sample_data.csv exists and has 200 rows

---

## 📚 Next Steps After Testing

Once you've verified the system works:

1. **Replace sample data** with your real customer data
2. **Customize features** in the available_features list
3. **Adjust opportunity** definition for your use case
4. **Tune confidence thresholds** based on your needs
5. **Deploy to production** (see QUICK_START.md)

---

## ✅ Success Checklist

- [ ] Got Groq API key
- [ ] Installed Python dependencies
- [ ] Tested simple example script
- [ ] Started API server successfully
- [ ] Tested API endpoint with curl
- [ ] Installed frontend dependencies
- [ ] Saw UI in browser
- [ ] Analyzed sample data
- [ ] Saw validated hypotheses
- [ ] Understood causal graph

---

## 💡 Key Takeaway

**You now have everything needed to test the Retention Reasoning Agent!**

The sample data is realistic and demonstrates the agent's ability to:
- Generate causal hypotheses
- Test them statistically
- Identify mediating variables
- Recommend actionable levers
- Provide explainable reasoning

No code changes needed - just get your API key and start testing! 🚀
