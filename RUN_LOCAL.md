# Running the pipeline locally

The pipeline calls **real** Azure Document Intelligence and Azure OpenAI, so it
must run somewhere with outbound internet access to your Azure endpoints (a
normal laptop/server — not a locked-down sandbox).

## 1. Clone and install

```bash
git clone <your-repo-url> test
cd test
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure credentials

Create a file named `.env` in the project root (it is gitignored):

```
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://<your-di>.cognitiveservices.azure.com/
AZURE_DOC_INTELLIGENCE_KEY=<key>
AZURE_OPENAI_ENDPOINT=https://<your-aoai>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

`AZURE_OPENAI_DEPLOYMENT` is the **deployment name** you created in Azure AI
Foundry (e.g. `agent-invoice`), not the model name.

## 3. Generate a sample invoice (optional)

```bash
pip install reportlab
python samples/make_invoice.py        # writes samples/sample_invoice.pdf
```

Or use any real invoice PDF/image of your own.

## 4. Start the service

```bash
uvicorn app.main:app --reload
```

Confirm config loaded:

```bash
curl http://localhost:8000/health
# -> {"status":"ok","config":"valid"}
```

## 5. Process a document

```bash
curl -F "file=@samples/sample_invoice.pdf" \
     -F 'ground_truth={"InvoiceId":"INV-2026-00042","InvoiceTotal":"599.40"}' \
     http://localhost:8000/process
```

The response shows accepted fields, fields routed to human review, and the
run's latency/cost metrics. Then:

```bash
curl http://localhost:8000/review        # items needing human review
curl http://localhost:8000/metrics/runs  # per-run accuracy/latency/cost
```
