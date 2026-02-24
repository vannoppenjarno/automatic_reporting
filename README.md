# Automatic Reporting

## Project Overview
This project generates structured reports from interaction logs and serves them through an API and a lightweight frontend.

Current production flow in `main.py`:
- Reads interaction data from Supabase via RPC (`fetch_interactions_filtered`)
- Generates structured report JSON with LangChain + Gemini
- Stores report JSON in Supabase (`daily`, `weekly`, `monthly`, `aggregated`)
- Splits report markdown into chunks and upserts vectors into Chroma Cloud
- Runs daily, plus weekly (Sunday) and monthly (last day of month) aggregations

Also included:
- FastAPI backend for report retrieval and Q&A (`src/app/api.py`)
- Static frontend dashboard (`frontend/`)
- Optional CSV ingestion (`csv_logs/*.csv`)
- Legacy Gmail ingestion helpers (`src/fetch.py`) not used by default in `main.py`

## Features
- Automated daily, weekly, monthly, and manual aggregated report generation
- Structured report output validated with Pydantic (`src/report.py`)
- Chroma vector indexing for interactions and report chunks
- SQL-based Q&A endpoint (`/ask`) scoped to the authenticated user's company
- Google ID token authentication for API tenancy isolation

## Quickstart
```powershell
# 1) Create and activate Python 3.11 environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3) Ensure required prompt files exist
Copy-Item archive\daily_prompt_template_old.md prompt_input\daily_prompt.md

# 4) Run the reporting pipeline
python main.py
```

## Installation / Requirements
- Python: `3.11` (matches CI in `.github/workflows/reports.yml`)
- Required external services:
  - Supabase project and schema
  - Chroma Cloud tenant/database
  - Google Gemini API key

Install:
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration
Configuration is loaded in `config.py` using `.env` + hard-coded defaults.

Environment variables:

| Variable | Required | Default | Used by |
|---|---|---|---|
| `SUPABASE_URL` | Yes | None | Supabase client init (`config.py`) |
| `SUPABASE_KEY` | Yes | None | Supabase client init (`config.py`) |
| `CHROMA_KEY` | Yes | None | Chroma Cloud client init (`config.py`) |
| `CHROMA_TENANT` | Yes | None | Chroma Cloud client init (`config.py`) |
| `LLM_API_KEY` | Yes | None | Gemini model (`src/get/models.py`) |
| `COMPANY_NAME` | Optional | None | `python -m src.store` bootstrap |
| `TALKING_PRODUCTS` | Optional | None | `python -m src.store` bootstrap |
| `TALKING_PRODUCT_ADMIN_URLS` | Optional | `""` | `python -m src.store` bootstrap |
| `TALKING_PRODUCT_URLS` | Optional | `""` | `python -m src.store` bootstrap |
| `TALKING_PRODUCT_QR_CODES` | Optional | `""` | `python -m src.store` bootstrap |

Non-env defaults in `config.py` you may want to edit:
- `CSV_LOGS_DIR` is an absolute local path
- `DAILY_PROMPT_PATH` defaults to `prompt_input/daily_prompt.md` (must exist)
- `CHROMA_DATABASE` default is `"Test"`
- `CHROMA_COLLECTION_NAME` default is `"digiole_automatic_reporting"`
- `FREE_LOCAL_LLM_MODEL` and `LLM_MODEL` defaults

## Usage
### 1) Run scheduled reporting locally
```powershell
python main.py
```

### 2) Bootstrap company + talking products (optional)
```powershell
$env:COMPANY_NAME="Example Company"
$env:TALKING_PRODUCTS="Product A,Product B"
python -m src.store
```

### 3) Run backend API
```powershell
python -m uvicorn src.app.api:app --reload --host 127.0.0.1 --port 8000
```

### 4) Run frontend
```powershell
python -m http.server 5500 --directory frontend
```
Then open `http://127.0.0.1:5500`.

### API endpoints
- `GET /me/talking-products`
- `GET /reports?report_type=<daily|weekly|monthly|aggregated>&report_date=YYYY-MM-DD&talking_product_id=<id>`
- `GET /reports/latest?report_type=<...>&talking_product_id=<id>`
- `POST /ask`

All endpoints require `Authorization: Bearer <google_id_token>`.

Example:
```bash
curl -H "Authorization: Bearer <GOOGLE_ID_TOKEN>" \
  "http://127.0.0.1:8000/me/talking-products"
```

## Development
There is currently no configured test/lint/typecheck toolchain in this repository (`pytest`, `ruff`, `mypy`, etc. are not configured).

Recommended local checks:
```powershell
python -m compileall src main.py config.py
```

## Project Structure
```text
.
|-- main.py                    # Scheduled report pipeline entrypoint
|-- config.py                  # Runtime config, env loading, clients
|-- requirements.txt
|-- .github/workflows/reports.yml
|-- src/
|   |-- fetch.py               # Gmail + CSV parsing helpers
|   |-- embed.py               # Sentence-transformer embeddings
|   |-- prompt.py              # Report, SQL, and RAG chains
|   |-- report.py              # Pydantic report schema
|   |-- store.py               # Supabase + Chroma persistence
|   |-- utils.py               # Clustering, token budgeting, SQL validation
|   |-- get/
|   |   |-- data.py            # Supabase/Chroma data access + RPC helpers
|   |   |-- models.py          # LLM and embedding model factories
|   |   `-- templates.py       # Prompt/context file loaders
|   `-- app/api.py             # FastAPI app
|-- prompt_input/              # Prompt/context files
|-- frontend/                  # Static dashboard UI
|-- csv_logs/                  # Optional CSV drop folder
`-- archive/                   # Historical prompt/templates
```

## Deployment / CI Notes
- GitHub Actions workflow: `.github/workflows/reports.yml`
- Trigger:
  - Daily schedule: `20 0 * * *` (00:20 UTC)
  - Manual `workflow_dispatch`
- CI job:
  - Uses Python 3.11
  - Runs `python -m pip install --upgrade pip`
  - Runs `pip install -r requirements.txt`
  - Runs `python main.py` with secrets-based env vars

## Troubleshooting
- `pip install -r requirements.txt` fails with `json2markdown==0.1.3` not found:
  - Use `json2markdown==0.1.1` (available on PyPI; matches current import in `src/store.py`).
- `FileNotFoundError: prompt_input/daily_prompt.md`:
  - Create the file, for example:
  - `Copy-Item archive\daily_prompt_template_old.md prompt_input\daily_prompt.md`
- Chroma connection retries then fails:
  - Verify `CHROMA_KEY` and `CHROMA_TENANT`.
- API returns `403 User not linked to a company yet`:
  - The authenticated user exists but has no `company_id` in Supabase `users` table.

## License
No `LICENSE` file is currently present in this repository.
