# Local AI Job Application Assistant

A single-user, command-first assistant built with Python, Streamlit, Ollama and Google Workspace APIs. It prepares job-application material; you review and submit applications yourself.

## Current capabilities

| Module | Commands | Boundary |
|---|---|---|
| Local chat and routing | `/help`, `/status` | Self-hosted Ollama; tracing optional |
| Google configuration | `/google_connect`, `/configure`, `/sources` | App-owned OAuth; sandbox writes only |
| JD capture | `/save_jd` | Original text preserved in a new Google Doc |
| Source catalogue | `/refresh_sources`, `/show_sources` | Selected resume tabs, Docs, local Markdown/text |
| JD scope and comparison | `/requirements`, `/review_requirements`, `/compare_resume`, `/show_comparison`, `/review_comparison` | Review selected JD sentences before model comparison; judgments require review |
| Resume tailoring | `/draft_resume`, `/format_resume`, `/suggest_edits`, `/apply_edits`, `/reset_edits`, `/approve_resume` | New tab; explicit reviewed edits only |
| Tracking | `/init_tracker`, `/track_application` | Dedicated tab in copied workbook; Prepared status |
| Application package | `/draft_cover_letter`, `/show_cover_letter`, `/review_cover_letter`, `/application_summary` | Optional letter; no automatic submission |

This is a development implementation, not a verified production deployment. Voice, automation, autonomous multi-agent workflows, and general-purpose Google editing are deferred. Google REST access is behind a separate adapter; an MCP client is not implemented yet.

The **Inspect comparison evidence** panel provides a read-only view of proposed verdicts, recorded decisions, flags and full source context. Load an application ID and choose a source/requirement. Review decisions still use `/review_comparison`; opening the panel grants no approval. See [the review walkthrough](docs/TESTING.md#comparison-inspection-panel).

## Start locally

Python 3.12+ and Docker are used below; Ollama runs in a container.

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

On Windows PowerShell use `.venv\Scripts\Activate.ps1` or the explicit interpreter commands in [TESTING.md](docs/TESTING.md). Local chat history defaults to SQLite. No paid model API or LangSmith key is required. The default model is qwen3:1.7b, exercised locally against synthetic data and a copied resume. This is a limited smoke test, not a quality benchmark; review generated claims and evaluate your own hardware.

For Docker reference files, set `ASSISTANT_EVIDENCE_DIR` in private `.env`; the app sees that folder read-only at `/evidence`. Configure a relevant subfolder in `local_source_dirs` and refresh sources inside the container. See [project evidence setup](docs/COMMANDS.md#local-project-evidence-in-docker).

Docker alternative: `docker compose up --build -d`, then `docker compose exec ollama ollama pull qwen3:1.7b`. Compose uses PostgreSQL and CPU-capable Ollama by default. It binds services to localhost and mounts private workflow state. Authenticate using the local CLI before starting the container; browser OAuth inside Docker is not supported.

## Configure and use commands

See [command guide](docs/COMMANDS.md) for OAuth setup, configuration and exact payloads. Use only copies inside a dedicated sandbox folder. Keep credentials outside the repository. The connected Codex account does not authenticate this app.

Typical sequence:

```text
/save_jd {"company": "Example Company - TEST ONLY","role": "Python Data and GenAI Engineer - TEST ONLY","url": "https://example.com/jobs/assistant-sandbox-test","jd": "This is a synthetic test job, not a real vacancy. Required: Python, SQL and ETL troubleshooting. Familiarity with RAG and LLM evaluation is desirable. Candidates should distinguish commercial production experience from independent portfolio work."}
/refresh_sources
/requirements APPLICATION_ID
/review_requirements {"application_id":"APPLICATION_ID","candidate_ids":[1,2,3],"reviewed":true}
/compare_resume APPLICATION_ID
/show_comparison APPLICATION_ID
# Fill its review template, then submit /review_comparison with that JSON.
/draft_resume APPLICATION_ID
/suggest_edits APPLICATION_ID
/apply_edits {"application_id":"APPLICATION_ID","edit_ids":[0],"edit_batch_id":"CURRENT_BATCH_ID","reviewed":true}
/approve_resume APPLICATION_ID
/draft_cover_letter APPLICATION_ID
/show_cover_letter APPLICATION_ID
# Inspect every claim, then approve or omit using its review template.
/init_tracker
/track_application APPLICATION_ID
/track_application APPLICATION_ID --write
/application_summary APPLICATION_ID
```

If the copied resume needs tighter spacing, preview `/format_resume APPLICATION_ID`, then use `--write` to apply the compact preset. Text stays unchanged; approval is invalidated. Export and inspect the PDF before approving again. Formatting does not guarantee a page count.

The candidate IDs above apply only to the synthetic sample JD. For your own JD, inspect `/requirements` and select every relevant duty, qualification and required/desirable skill. The small model is not trusted to choose comparison scope or certify its own judgments. All returned verdicts remain `needs_review`, with accepted counts unset and no selected resume. Use `/show_comparison` to get an incomplete review template; complete every decision and submit `/review_comparison`. Review projects needed for generation before creating any draft. Generation uses only accepted quotations; final resume edits and tracking still require their own review.

Cover letters are optional. `/track_application` previews; adding `--write` saves. Use the application ID returned by `/save_jd`. CLI commands also accept JSON on stdin: `python -m assistant.cli /save_jd < jd.json`.

## Architecture and extension

Streamlit/CLI → command registry → application handlers → Google/model adapters.

Workflow state is private local SQLite under `.assistant/`; chat history uses the configured SQLAlchemy database. Add a command by registering an `Action` and implementing a bounded handler. Model output cannot invoke tools directly. External text is treated as source material. Quotation checks reduce fabricated citations but cannot establish semantic truth; human review remains necessary.

The initial copier supports paragraph/text resumes with page and named styles. Complex native structures are rejected before writing. PDF/page-fit review is manual. Do not expose this single-user app publicly without adding authentication and per-user credential/state isolation.

## Documentation

- [Handover runbook: configuration, operation, backup and ownership](docs/HANDOVER.md)
- [Documentation audit and remaining handover checks](docs/DOCUMENTATION_AUDIT.md)
- [Setup and exact command payloads](docs/COMMANDS.md)
- [How to test: Windows/WSL, sandbox walkthrough and recovery](docs/TESTING.md)
- [Review and merge the PR stack](docs/REVIEW.md)
- [Manual test report template](docs/TEST_REPORT_TEMPLATE.md)
- [Current validation and limitations](docs/VALIDATION.md)
- [Module plan and boundaries](docs/PLAN.md)
- [How to add a module or command](docs/EXTENDING.md)

## Validation

```bash
python -m unittest discover -s tests -v
```

Tests include a complete manual workflow with Google/model doubles, interrupted-write reconciliation, citation checks, preserved source tabs, Unicode edit ranges and tracker duplicate/formula protections. See [validation status](docs/VALIDATION.md) for the distinction between offline coverage and live checks, and [module plan](docs/PLAN.md) for scope.

CLI exit codes: 0 for a handled command, 1 for an unknown command/action failure, 2 for missing or non-command input. `/status` reports connectivity in its message. See the testing guide for exact expectations.
