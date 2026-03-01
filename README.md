# Automatic Reporting

This project generates reports based on interaction data. It fetches interaction logs from Supabase (and optionally CSV files), clusters and summarizes questions with an LLM pipeline, stores daily reports in Supabase, and indexes both interactions and reports in Chroma Cloud. It also produces **weekly and monthly summaries** by aggregating interaction data over date ranges.

Note: Email fetching is deprecated. Also frontend and backend development/test components are deprecated and not part of the active flow.

---

## Features

* **Automated Data Collection:** Fetches interaction logs from Supabase via RPC (`fetch_interactions_filtered`) for active companies/talking products; can also ingest CSV logs from `CSV_LOGS_DIR`.
* **Log Parsing & Enrichment:** Parses question/answer/match-score/time records, detects language for CSV ingestion, and adds vector embeddings to questions.
* **LLM-Powered Reports:** Generates structured reports using LangChain prompts + Pydantic schema with Gemini (and optional local Ollama model configured).
* **Database Integration:** Stores report payloads in Supabase tables (`daily`, `weekly`, `monthly`, `aggregated`).
* **Vector Storage (RAG-ready):** Stores interaction vectors and chunked report vectors in Chroma Cloud for retrieval and semantic search.
* **Extensible & Modular:** Clear module split for data access, prompting, embeddings, clustering/token budgeting, and storage.

### Vector Embedding Model
Current embedding model is `BAAI/bge-m3` (`config.EMBED_MODEL`) via `SentenceTransformer`.

Why this model:
* Multilingual-capable and suitable for semantic similarity clustering/retrieval.
* Works with normalized embeddings used in both clustering and Chroma indexing.

How to improve:
* Benchmark alternatives on your real question corpus (retrieval precision + cluster quality).
* Consider domain-tuned embedding models if your visitor questions are highly specialized.
* Track retrieval quality over time (`RETRIEVAL_K`, metadata filters, and chunk settings).

### Clustering
Questions are clustered with **HDBSCAN** (`src/utils.py`) on embeddings:
* Noise points are separated (`label = -1`).
* Cluster importance combines cluster size and low match-score pressure.
* Representative questions are chosen by frequency and centroid proximity.

#### Importance Filtering
Cluster importance is calculated as:
`importance = cluster_size * (1 - avg_match_score / 100)`

This gives more budget to large clusters with lower average match score (higher problem/ambiguity signal).

#### Token Budgeting
`format_clusters_for_llm` dynamically allocates token budget:
* Reserves tokens for static prompt/context.
* Splits remaining context window across clusters by relative importance.
* Enforces a minimum per-cluster budget (`MIN_TOKENS_PER_CLUSTER`).
* Fills leftover budget with unclustered (noise) questions when possible.

---

## Project Structure

```
.
├── main.py                    # Entry point: daily + weekly + monthly + manual aggregation orchestration
├── config.py                  # Runtime settings, model names, prompt paths, Supabase + Chroma clients
├── src/
│   ├── embed.py               # Embedding model loader and question embedding helpers
│   ├── prompt.py              # LangChain chains for report generation, SQL answering, and RAG answering
│   ├── report.py              # Pydantic report schema
│   ├── store.py               # Save reports/interactions to Supabase + Chroma chunk upserts
│   ├── utils.py               # CSV parsing, language detection, clustering, token budgeting, SQL validation
│   └── get/
│       ├── data.py            # Supabase/Chroma read helpers, RPC pagination, retrieval context
│       ├── models.py          # Gemini/Ollama/embedding model factories
│       └── templates.py       # Prompt/context file loaders
├── prompt_input/              # Prompt templates and context files consumed by src/get/templates.py
├── csv_logs/                  # Optional CSV drop folder for incremental ingestion
└── requirements.txt           # Python dependencies
```

---

## Installation

1. Clone the repository:

   ```bash
   git clone <repo-url>
   cd <repo-directory>
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables in `.env` for:
   * `SUPABASE_URL`
   * `SUPABASE_SERVICE_ROLE_KEY`
   * `CHROMA_KEY`
   * `CHROMA_TENANT`
   * `LLM_API_KEY`

4. Ensure prompt files exist in `prompt_input/`:
   * `daily_prompt.md`
   * `sql_prompt.md`
   * `llm_prompt.md`
   * `rag_prompt.md`
   * `context.md`

---

## **Configuration Options:**

* Update models in `config.py` (`EMBED_MODEL`, `LLM_MODEL`, `FREE_LOCAL_LLM_MODEL`).
* Adjust clustering/token settings in `config.py` (`CONTEXT_WINDOW`, `MIN_TOKENS_PER_CLUSTER`, `RETRIEVAL_K`).
* Update prompt/context file paths in `config.py`.
* Set `CSV_LOGS_DIR` for optional CSV ingestion.
* Control manual aggregation via:
  * `MANUAL_AGGREGATION_ENABLED`
  * `MANUAL_AGGREGATION_DATE_RANGE`
  * `MANUAL_AGGREGATION_COMPANY_NAME`

---

## Design Choices

- Daily reports run per active talking product for the current date.
- Weekly report runs every Sunday (`today.weekday() == 6`) for the previous 7-day window.
- Monthly report runs on the last day of each month for that month-to-date window.
- Reports are structured JSON validated by Pydantic (`src/report.py`) for consistent schema.
- Supabase is the relational source/store for interactions and reports.
- Chroma Cloud is used for vector storage of interactions and chunked report content.
- Clustering + representative selection + token budgeting reduce prompt noise while preserving signal.
- Email ingestion logic is deprecated in the active pipeline.

---

## Potential Improvements

* Add evaluation metrics for report quality, retrieval relevance, and cluster coherence.
* Improve clustering quality with parameter tuning and/or hybrid semantic + lexical grouping.
* Add stronger metadata filtering for retrieval by `doc_type`, `report_type`, and date windows.
* Add automated backfill and replay tooling for large historical reprocessing.
* Replace hardcoded absolute paths (e.g. `CSV_LOGS_DIR`) with environment-driven paths.

---

## Scheduling

The pipeline is scheduled with **GitHub Actions**.

- Workflow file: `.github/workflows/reports.yml`
- Daily trigger: `cron: "20 0 * * *"` (runs at **00:20 UTC** every day)
- Manual trigger: `workflow_dispatch` from the Actions tab

If you fork this repo, configure the required repository secrets used by the workflow (`SUPABASE_URL`, `SUPABASE_KEY`, `CHROMA_KEY`, `CHROMA_TENANT`, `LLM_API_KEY`, etc.) before enabling scheduled runs.

