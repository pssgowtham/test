# Azure Invoice Processing Pipeline with AI Remediation

A document processing service that **classifies** an incoming document,
**extracts** structured fields with **Azure Document Intelligence**, then uses
**Azure OpenAI** to **validate and fix** low-confidence extractions. Fields that
stay below a confidence threshold are routed to a **human review queue**. Every
run logs **accuracy, latency, and cost** for monitoring and optimization.

## Architecture

```
                upload
                  │
                  ▼
        ┌───────────────────┐
        │ 1. Classify        │  Azure DI prebuilt-read + heuristics
        │    (classify.py)   │  → document_type, DI model id
        └─────────┬──────────┘
                  ▼
        ┌───────────────────┐
        │ 2. Extract         │  Azure DI prebuilt-invoice/-receipt
        │    (extract.py)    │  → fields[] with per-field confidence
        └─────────┬──────────┘
                  ▼
        ┌───────────────────┐
        │ 3. Remediate       │  Azure OpenAI (JSON output)
        │    (remediate.py)  │  validate/correct fields < REMEDIATION_THRESHOLD
        └─────────┬──────────┘
                  ▼
        ┌───────────────────┐
        │ 4. Threshold       │  fields still < REVIEW_THRESHOLD
        │    (threshold.py)  │  → needs_review
        └─────────┬──────────┘
            ┌─────┴───────┐
            ▼             ▼
       accepted      5. Review queue (SQLite)
       (response)       (review/queue.py)
                  │
                  ▼
        6. Metrics (JSONL): latency per stage, DI page + OpenAI token cost,
           field counts, optional accuracy   (observability/)
```

Each stage lives in its own module under `app/pipeline/` and is wired together
by `app/pipeline/orchestrator.py`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your Azure credentials
```

Required environment variables (the app fails fast if any are missing):

| Variable | Purpose |
|----------|---------|
| `AZURE_DOC_INTELLIGENCE_ENDPOINT` / `_KEY` | Azure Document Intelligence resource |
| `AZURE_OPENAI_ENDPOINT` / `_API_KEY` / `_DEPLOYMENT` / `_API_VERSION` | Azure OpenAI resource + deployment |
| `REMEDIATION_THRESHOLD` (default 0.80) | fields below this go to Azure OpenAI |
| `REVIEW_THRESHOLD` (default 0.60) | fields still below this go to human review |
| `REVIEW_DB_PATH`, `METRICS_LOG_PATH` | storage locations |
| `COST_DI_PER_PAGE`, `COST_AOAI_PROMPT_PER_1K`, `COST_AOAI_COMPLETION_PER_1K` | cost model rates |

## Run

```bash
uvicorn app.main:app --reload
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness + which config vars are missing |
| `POST` | `/process` | Upload a document (`file`), optional `ground_truth` JSON; runs the pipeline |
| `GET`  | `/review` | List pending human-review items |
| `POST` | `/review/{id}/resolve` | Submit a corrected value for a review item |
| `GET`  | `/metrics/runs` | Recent per-run metric records |

Example:

```bash
curl -F "file=@invoice.pdf" \
     -F 'ground_truth={"InvoiceTotal":"1234.56"}' \
     http://localhost:8000/process
```

## Monitoring & Optimization

Every run appends one record to `METRICS_LOG_PATH` (JSONL) containing:

- **Accuracy** — when a `ground_truth` map is supplied, the fraction of fields
  whose extracted value matches. Track this to detect model/extraction drift.
- **Latency** — per-stage (`classify_ms`, `extract_ms`, `remediate_ms`) and
  total. Remediation calls dominate latency; the per-stage split shows where to
  optimize.
- **Cost** — Azure DI billed per analyzed page; Azure OpenAI billed per prompt
  and completion token. Rates are configurable so estimates match your contract.

**Threshold tuning is the core optimization lever.** Raising
`REMEDIATION_THRESHOLD` sends more fields to Azure OpenAI (higher cost/latency,
fewer items needing review). Raising `REVIEW_THRESHOLD` increases automation
confidence but grows the human review queue. The metrics log lets you quantify
that automation-rate vs. review-volume vs. cost trade-off per run.
