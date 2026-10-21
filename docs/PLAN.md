# Command-first job application assistant

Goal: turn a pasted JD into an evidence-based application package through explicit commands.

| Module | Capability | Boundary |
|---|---|---|
| 0–1 | Local setup, /help, /status, action registry | Self-hosted Ollama; no external tracing required |
| 2–3 | Google authentication, source settings, /save_jd | Configured folders only; preserve original JD |
| 4–5 | Source catalogue, /requirements, /review_requirements, /compare_resume | Reviewed JD scope; read-only evidence; no ATS predictions |
| 6 | /draft_resume, /format_resume, /suggest_edits, /apply_edits | New tab only; originals preserved |
| 7 | /track_application | Dedicated copied-workbook tab; preserve existing tabs/formulas; status Prepared |
| 8–9 | Cover letter and application summary | Optional letter; no job submission |

Each module is reviewed in a separate stacked PR. Later branches target the preceding branch until merged. No merges are automatic. Commands share application IDs and persisted outcomes. Retries must not silently duplicate artifacts.

Deferred: voice, automated chains, recruiter messaging, scraping, autonomous agents, arbitrary Google edits. Adding an action requires a registry entry and tested handler. MCP adapters should remain separate from domain logic; Google APIs provide the initial concrete adapter.

## Local start

Python 3.12+ recommended:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3:1.7b
python -m assistant.cli /status
streamlit run app.py
```

SQLite is the local default. Docker Compose supplies PostgreSQL and Ollama; PostgreSQL overrides the local DATABASE_URL setting; run `docker compose up --build -d` and `docker compose exec ollama ollama pull qwen3:1.7b`. CPU operation is supported; performance is hardware-dependent. Model installation and a real prompt are required to validate inference.

Offline checks: `python -m unittest discover -s tests -v`.
