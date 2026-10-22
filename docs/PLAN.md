<!--
File: docs/PLAN.md
Purpose: Command-first job application assistant.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->

# Command-first job application assistant

Goal: turn a pasted JD into an evidence-based application package through explicit commands.

| Module | Capability | Boundary |
|---|---|---|
| 0–1 | Local setup, /help, /status, action registry | Self-hosted Ollama; no external tracing required |
| 2–3 | Google authentication, source settings, /save_jd | Configured folders only; preserve original JD |
| 4–5 | Source catalogue, /requirements, /review_requirements, /compare_resume, /review_comparison | Reviewed JD scope; read-only evidence; no ATS predictions |
| 6 | /draft_resume, /format_resume, /suggest_edits, /apply_edits | New tab only; originals preserved |
| 7 | /track_application | Dedicated copied-workbook tab; preserve existing tabs/formulas; status Prepared |
| 8–9 | Cover letter and application summary | Optional letter; no job submission |

Each module is reviewed in a separate stacked PR. Later branches target the preceding branch until merged. No merges are automatic. Commands share application IDs and persisted outcomes. Retries must not silently duplicate artifacts.

Deferred: voice, automated chains, recruiter messaging, scraping, autonomous agents, arbitrary Google edits. Adding an action requires a registry entry and tested handler. MCP adapters should remain separate from domain logic; Google APIs provide the initial concrete adapter.

For operation and transfer of ownership, use the [handover runbook](HANDOVER.md). This plan describes scope; it does not certify model accuracy or production readiness.

## Local start

Python 3.12+ recommended:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; fi
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3:1.7b
python -m assistant.cli /status
streamlit run app.py
```

SQLite is the local default. Docker Compose supplies PostgreSQL and Ollama; PostgreSQL overrides the local DATABASE_URL setting; run `docker compose up --build -d` and `docker compose exec ollama ollama pull qwen3:1.7b`. CPU operation is supported; performance is hardware-dependent. Model installation and a real prompt are required to validate inference.

Offline checks: `python -m unittest discover -s tests -v`.


## Next acceptance priority

The command flow, Google sandbox writes, read-only project ingestion, compact formatting and clean container image have been exercised. Model comparison quality remains a critical gap: real-JD tests produced valid JSON with unsupported judgments. Before reducing manual review, create representative reviewed comparison fixtures covering production qualifiers, partial skill coverage, name-only/irrelevant quotations, planned versus completed work, and independent portfolio versus commercial employment. Evaluate self-hosted models against those fixtures and block unsupported conclusions. A successful API call or exact quotation alone does not pass that gate. Voice and automation remain deferred.


Comparison control version 1 now separates model proposals from accepted reviewer decisions. It removes automatic resume selection, requires a snapshot-bound decision for each selected requirement, keeps override history, and limits generation to accepted quotations. Eight synthetic failure regressions exercise the gate. Model semantic accuracy remains an open evaluation task; these controls contain unreliable judgments rather than claim to fix model reasoning. Broader reviewed cases are required before considering any reduction in manual control.


A read-only comparison inspection panel now exposes proposal/decision differences and full frozen source context. It is a convenience for the existing command workflow; approvals remain explicit commands. It does not change model quality requirements or enable automation.
