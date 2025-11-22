# Running the Retention Reasoning Agent (API + Crayon UI)

## Backend (FastAPI)
```bash
pip install -r requirements.txt
uvicorn retention_reasoning.api:create_app --factory --host 0.0.0.0 --port 8000
```
Environment:
- `CORS_ALLOW_ORIGINS` (comma-separated, default `*`)
- `BQ_PROJECT_ID`, `BQ_DATASET`, `BQ_CUSTOMERS_TABLE` (optional BigQuery loader)
- `GROQ_API_KEY`, `GROQ_MODEL` (for real LLM; tests use fake stubs)

## Frontend (Crayon React)
```bash
cd frontend/crayon
npm install
VITE_API_BASE=http://localhost:8000 npm run dev
```
The UI posts to `/analyze` and can be wired to `/stream` for SSE.

## Where to inject business rules
- Segmentation SQL/attributes: `src/retention_reasoning/services/segmentation.py`
- Offers/pricing rules: `src/retention_reasoning/services/offers.py`
- Channel/cadence/copy: `src/retention_reasoning/services/playbook.py`
- Performance grading: `src/retention_reasoning/services/performance.py`
- Exporters: `src/retention_reasoning/services/exporters.py`

## Tests/CI
```bash
pytest
```
CI workflow at `.github/workflows/ci.yml`.
