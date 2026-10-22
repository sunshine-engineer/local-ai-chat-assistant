<!--
File: docs/HANDOVER.md
Purpose: Handover runbook.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->

# Handover runbook

Reviewed 2026-10-23 against the command registry, handlers, sample files, environment defaults and Compose configuration. This is a development handover for one local user; it is not a production-readiness sign-off.

Outline: obtain the full branch → start local services → connect and configure copies → prepare one application → verify/recover → back up and transfer ownership.

## 1. What is ready and what is open

| Area | Handover state | Next owner action |
|---|---|---|
| Manual text commands | Implemented; 73 established workflow tests plus configuration/entry-point regressions; see latest validation | Repeat [offline checks](TESTING.md#2-prepare-python-and-run-offline-checks) on your exact commit |
| Google operations | App-owned OAuth and copied-resource acceptance previously exercised | Connect your account and verify sandbox IDs before writes |
| Comparison and generation | Model suggestions require explicit evidence and artifact review | Inspect every factual claim; schema/citation checks do not prove support |
| Read-only comparison panel | Proposal/decision inspection implemented | Reload after commands; approve through commands only |
| Model quality | Unresolved; Qwen3:1.7b passed only 2/8 synthetic diagnostic cases | Build broader reviewed real-JD cases and evaluate models before reducing review |
| Merge/deployment | Stacked, unmerged review branches; local development runtime | Follow [REVIEW.md](REVIEW.md); do not treat the default branch as the full implementation yet |
| Voice, automation, MCP client, autonomous agents | Deferred | Define and approve a separate bounded module later |

[VALIDATION.md](VALIDATION.md) records what was actually exercised and its limits. No job submission is implemented. A Prepared summary means the reviewed artifacts and tracker steps are complete, not that the app has independently proven their facts.

## 2. Fresh checkout and startup

Clone `https://github.com/sunshine-engineer/local-ai-chat-assistant.git`, enter its directory, and select the latest full-stack branch listed in [TESTING.md](TESTING.md#1-choose-what-you-are-testing). No merge is needed to test it. Preserve existing local changes before switching branches.

Use Python 3.12 and Docker Compose v2 as the baseline. Python 3.14 also passed the offline suite; other versions are not established by that result. Install dependencies in a virtual environment using the platform commands in [TESTING.md](TESTING.md#2-prepare-python-and-run-offline-checks). Dependencies and container tags are not fully pinned, so record the resolved versions and image IDs when reproducing a run.

Choose one execution mode:

| Mode | Start | Model endpoint and evidence paths |
|---|---|---|
| Host Streamlit/CLI + Docker Ollama | Start only `ollama`, install the configured model, then `streamlit run app.py` | Host endpoint `http://localhost:11434`; actual host source paths; SQLite chat by default |
| Full Compose | Complete OAuth on the host, then `docker compose up --build -d`; install the configured model in `ollama` | App endpoint `http://ollama:11434`; `/evidence/...` source paths; PostgreSQL chat |

Copy `.env.example` to `.env` only if absent. From the repository root:

```bash
# Bash/WSL; retain an existing .env
if [ ! -f .env ]; then cp .env.example .env; fi
docker compose config --quiet
docker compose up -d ollama
docker compose exec ollama ollama list
# Run the pull only when the configured model is absent.
docker compose exec ollama ollama pull qwen3:1.7b
python -m assistant.cli /status
```

For PowerShell setup and JSON input, use [TESTING.md](TESTING.md). `/status` is diagnostic: read its message even when exit code is 0. Set `OLLAMA_MODEL` to an installed model; changing its name does not download it. The default small model is a smoke-test baseline, not a quality recommendation.

Open `http://localhost:8501` after starting Streamlit or the full Compose app. Test readiness with `docker compose ps`, `docker compose logs --tail=50 chatbot`, and the health endpoint `http://localhost:8501/_stcore/health`. Do not publish raw logs containing private text.

Compose defaults to container names `ollama`, `qa-chatbot`, `postgres` and loopback ports 8501, 5432 and 11434. These names and host ports now have environment overrides. Existing services can conflict. Set the documented name/port environment overrides, or use a deliberate Compose override, rather than stopping unrelated containers. If changing `OLLAMA_PORT`, also change host `OLLAMA_HOST` to match; Compose's app endpoint stays the internal service address. The existing developer review runtime uses an isolated private override; it is not part of a fresh clone.

## 3. Configuration reference

### Environment

| Setting | Default | Purpose / boundary |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` on host | Model endpoint; Compose overrides the app to `http://ollama:11434` |
| `OLLAMA_PORT` | `11434` | Compose host publication only |
| `OLLAMA_MODEL` | `qwen3:1.7b` | Installed self-hosted model for chat and actions |
| `OLLAMA_CONTEXT` | `16384` | Structured action context tokens; hardware must support the allocation |
| `OLLAMA_TIMEOUT_SECONDS` | `300` | Structured action request timeout |
| `OLLAMA_OUTPUT_TOKENS` | `4096` | Structured action output limit |
| `ASSISTANT_PROMPT_CHAR_LIMIT` | `24000` | Structured action prompt character guard; not a token estimator |
| `ASSISTANT_REQUIREMENT_BATCH_SIZE` | `3` | Comparison requirements per call; valid range 1–5 |
| `OLLAMA_KEEP_ALIVE` | `1m` in Compose | Ollama model retention setting |
| `ASSISTANT_EVIDENCE_DIR` | `./examples` in Compose | Existing host folder mounted read-only at `/evidence`; missing paths fail |
| `ASSISTANT_HOME` | `.assistant` relative to working directory | Private workflow/token directory; keep CLI and UI on the same directory |
| `DATABASE_URL` | `sqlite:///assistant.db` locally | Chat database; Compose clears this variable and uses its DB_* service fields |
| `LANGSMITH_TRACING` | `false` in example | Tracing is opt-in; enabling external tracing can expose private prompt text |
| `TZ` | `Asia/Kolkata` in example | Runtime timezone |
| `TRACKER_TIMEZONE` | `Asia/Kolkata` | Preparation-date timezone for new tracker entries |
| `GOOGLE_TIMEOUT_SECONDS` | `60` | Google REST timeout, including write/readback requests |
| `CHAT_TEMPERATURE`, `CHAT_MAX_TOKENS` | `0.7`, `150` | Ordinary-chat slider starting values; valid UI ranges 0–1 and 50–300 |
| `CHATBOT_PORT`, `POSTGRES_PORT` | `8501`, `5432` | Compose loopback host publication; internal ports remain fixed |
| `OLLAMA_CONTAINER_NAME`, `CHATBOT_CONTAINER_NAME`, `POSTGRES_CONTAINER_NAME` | `ollama`, `qa-chatbot`, `postgres` | Optional Compose container-name overrides |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Public local-demo `chatbot` defaults | Compose database initialization and matching app connection fields; use a private password outside demos |

`DB_HOST`, `DB_PORT` (5432), `DB_NAME`, `DB_USER` and `DB_PASSWORD` are fallback connection fields only when `DATABASE_URL` is absent or empty; Compose supplies its own database settings. Example PostgreSQL credentials are local development defaults, not deployment credentials. Do not publish this app or expose its ports externally.

Defaults come from `config/defaults.toml`; private environment values take precedence. Real credentials belong only in private environment configuration, never in that public TOML file. The public demo values are retained for compatibility.

The sidebar temperature/output sliders control ordinary chat. Structured actions use fixed temperature 0 and the environment budgets above. They do not inherit those sidebar sliders. `ASSISTANT_CLI` is set internally by the CLI; users need not configure it. Opt-in service test variables are documented in [TESTING.md](TESTING.md#6-optional-real-service-regression-tests).

If setting `ASSISTANT_HOME` for a container, use a persistent mounted path. The supplied Compose file mounts `/app/.assistant`; it does not automatically mount a different home path. Keep secrets out of environment examples and Git.

### Resource configuration

Start with [config.sample.json](../examples/config.sample.json), replace every placeholder privately, and submit `/configure` via stdin. The complete accepted keys are:

| Key | Value and boundary |
|---|---|
| `sandbox_folder_id` | Dedicated temporary Drive folder ID; originals stay outside |
| `jd_folder_id`, `cover_letter_folder_id` | Must equal the sandbox folder ID for document creation |
| `resume_doc_id` | Copied resume document directly inside the sandbox |
| `resume_tab_ids` | Explicit source tab IDs recommended; empty/unset considers eligible non-empty tabs |
| `tracker_id` | Copied spreadsheet directly inside the sandbox |
| `tracker_tab` | Exactly `Assistant Applications` |
| `source_folder_ids` | Read-only Drive folders; direct native Docs only, not recursive |
| `local_source_dirs` | Local UTF-8 `.md`/`.txt` directories recursively; container mode uses `/evidence/...` |

`/configure` merges supplied fields with the saved configuration; omitted fields are retained. Use `[]` to clear source lists. `/sources` displays current settings. A new clone has no saved configuration, OAuth token, copied Google resources or private acceptance artifacts. The app does not provide a command to clone source files: create the sandbox copies manually in Drive first. Authentication alone does not grant permission to edit originals.

The optional `protected_original_ids` record is an additional private-state safeguard, not a `/configure` key. The normal setup boundary is to keep originals outside the sandbox and configure only copies. OAuth scopes themselves are account-wide. Never point an output ID at an original.

## 4. Prepare and review one application

Follow the full [command walkthrough](TESTING.md#4-walk-through-one-synthetic-application). The order matters:

1. Connect using the host Desktop OAuth CLI; verify output copies with `/sources`.
2. Save the JD and retain its application ID. Refresh only selected source tabs/project folders.
3. Inspect `/requirements`; explicitly review the complete relevant scope.
4. Compare, inspect source context, and review every selected requirement for the chosen resume and any project evidence needed for generation.
5. Draft the resume. Inspect suggestions; apply only reviewed edits using the exact current `edit_batch_id`. No acceptable suggestion is a valid outcome; keep/review the copied resume instead.
6. Optionally format the draft; export the selected tab to PDF and inspect every page. Approve only after content and layout review.
7. Optionally draft a cover letter. Inspect `/show_cover_letter`; explicitly approve the current text hash or omit the draft.
8. Initialize the dedicated tracker tab, preview the row, then explicitly write. Read the summary and resolve every remaining step. Submit the job application yourself.

Scope and evidence decisions freeze after a resume or letter draft exists. A new `variant` label supports a separate attempt without deleting prior state. Existing-job-URL tracker protection still prevents duplicate tracking; old rows are not silently overwritten. See [command review and recovery](COMMANDS.md#review-comparison-evidence-before-using-it).

### Supported input and tracker limits

JD input is limited to 100,000 characters; requirement enumeration allows up to 200 sentence/line candidates and review selects 1–30. Local sources must be UTF-8 `.md`/`.txt`, at most 100,000 bytes per file; hidden paths and symlinks are excluded. The catalogue limit is 2 million characters, while each model request has the smaller configured prompt guard. Native Google Docs are read directly; remote Markdown/text files, PDFs and DOCX files are not converted. Resume copying supports paragraph/text structures and rejects unsupported native lists, tables, embedded objects and related complex structures.

The dedicated tracker headers are `Application ID`, `Company`, `Role`, `Job URL`, `JD`, `Resume`, `Cover Letter`, `Status`, `Prepared Date`. Capacity is 999 application rows. Custom mappings, existing dashboard integration and Applied/submission status are outside this version. Existing custom tabs/formulas remain untouched.

## 5. State, backups and recovery

| Asset | Location | What a backup must preserve |
|---|---|---|
| Workflow config, catalogue, snapshots, approvals and retries | `.assistant/workflow.sqlite3` | Required for safe resume/retry and artifact ownership; contains private source text |
| OAuth token | `.assistant/token.json` | Sensitive account credential; prefer reconnecting on a new machine |
| Desktop OAuth client JSON | User-selected path outside repository | Keep privately; not included in a clone |
| Local chat history | `assistant.db`, unless `DATABASE_URL` overrides | Separate from workflow state |
| Compose chat history | `postgres-data` Docker volume | Separate PostgreSQL backup required |
| Model weights | `ollama-data` Docker volume | Can re-download the same model; record its identity |
| JD/resume/letter/tracker artifacts | Google sandbox | Local SQLite is not a backup of the actual remote artifacts |
| `.env` and private configuration/overrides | Local files outside committed examples | Preserve privately and update paths on a new machine |

Before a workflow backup, finish/reconcile pending commands and stop the host app/CLI and Compose chatbot (`docker compose stop chatbot`) that share this state. Copy the stopped workflow directory to private protected storage. Back up local chat separately. Keep credentials and personal text out of Git and shared handover reports. For a credential-free transfer, omit the token and complete OAuth again on the target machine. Preserve the workflow database; deleting it loses ownership and retry checkpoints.

Changing POSTGRES_* initialization values does not change users/passwords inside an existing PostgreSQL volume. Coordinate any credential migration with the existing database owner and backup first; do not delete volumes just to apply new settings. Compose passes discrete DB_* fields to SQLAlchemy so reserved password characters are encoded safely.

For Compose PostgreSQL, use a database backup rather than copying a live Docker volume. This example creates a portable archive inside the database container; replace `PRIVATE_BACKUP_PATH` before copying it to private host storage:

```bash
docker compose exec -T postgres pg_dump -U chatbot -d chatbot -Fc -f /tmp/assistant-chat.dump
docker compose cp postgres:/tmp/assistant-chat.dump PRIVATE_BACKUP_PATH
```

Verify that the host archive exists before removing the temporary container archive. A restore rehearsal must use a separate empty disposable database, with the account and target verified before invoking `pg_restore`; do not restore into the active developer database. PostgreSQL restore and fresh-machine transfer have not been live-tested in this project.

For workflow recovery, stop all writers first, preserve the current failed state, then restore the backup into the intended home directory. Start only one instance, run `/sources`, check IDs/paths and authenticate if needed. Reconcile uncertain writes with the identical saved command before new edits. Never run independent restored state directories against the same Google artifacts simultaneously.

`docker compose stop` preserves volumes. `docker compose down` removes containers/network but normally retains named volumes; **`down -v` deletes named volumes and loses chat/model data**. Do not use volume deletion as routine troubleshooting. Google changes are not rolled back by stopping containers or restoring local state.

For external-edit conflicts, `/reset_edits` explicitly keeps the current remote draft and clears only local edit/review state. It is not an undo. See [failure checks](TESTING.md#5-retry-and-failure-checks).

## 6. Maintainer map and acceptance

| Responsibility | Files |
|---|---|
| UI/chat and read-only comparison view | `app.py`, `assistant/review_ui.py`, `helpers.py` |
| Routing, CLI, workflow records/lock | `assistant/commands.py`, `runtime.py`, `cli.py`, `state.py` |
| Configuration and JD capture | `assistant/jobs.py` |
| Google adapter and ownership checks | `assistant/google.py` |
| Source ingestion, scope and comparison review | `assistant/evidence.py`, `requirements.py`, `comparison_review.py` |
| JSON model contracts and diagnostics | `assistant/model.py`, `schemas.py`, `evaluate.py`, `comparison_cases.json` |
| Resume edits and formatting | `assistant/resumes.py`, `edit_policy.py`, `layout.py` |
| Letter inclusion, tracker and summary | `assistant/package.py`, `tracking.py` |
| Chat persistence | `postgres/`, `helpers.py` |
| Deployment and CI | `Dockerfile`, `docker-compose.yml`, `.github/workflows/tests.yml` |

Use [EXTENDING.md](EXTENDING.md) for new modules. Before accepting the handover, record the exact commit, passing checks, private sandbox target confirmation, one manually reviewed application, unresolved quality issues and all unrun checks using [TEST_REPORT_TEMPLATE.md](TEST_REPORT_TEMPLATE.md). Browser layout, fresh-empty-volume Compose startup, backup restore and representative model accuracy are separate from passing offline tests.

A handover is complete when the recipient can explain the write boundaries, reproduce the chosen startup mode, prepare a reviewed sandbox package and recover an uncertain write without deleting ownership state. User acceptance and merge decisions remain with the reviewer.
