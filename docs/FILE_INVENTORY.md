<!--
File: docs/FILE_INVENTORY.md
Purpose: Reviewed file inventory and sidecar metadata for strict JSON and binary assets.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->

# Reviewed file inventory

Review date: 2026-10-23. Maintainer convention: sunshine-engineer, as requested. This is a file-purpose audit, not an attribution of original authorship. No historical authors, binary capture dates or ownership are inferred.

Outline: supported metadata → directory placement → complete file inventory.

Python, Markdown and supported configuration files contain their metadata in native docstrings/comments. Strict JSON and PNG files use this document as their metadata sidecar so parsers and binary contents remain intact. Their historical evaluation/run dates remain unchanged; the date above records this review rather than inventing a new source modified date.

Directory placement was checked against the README tree. Files match their stated responsibilities; no package relocation is needed. Root chat helpers remain for import compatibility. Historical image names now use lowercase snake case; their bytes are preserved. Private state, tokens, databases and local overrides are intentionally excluded from this inventory.

| File | Type | Reviewed purpose |
|---|---|---|
| `.dockerignore` | Configuration / dependency list | Keep private state, credentials and generated caches out of Docker build contexts. |
| `.editorconfig` | Configuration / dependency list | Set shared UTF-8, LF and indentation conventions for editors. |
| `.env.example` | Configuration / dependency list | Document public runtime overrides without storing account secrets. |
| `.gitattributes` | Configuration / dependency list | Preserve LF text conventions and binary screenshot contents. |
| `.github/workflows/tests.yml` | Configuration / dependency list | Validate formatting, documentation, tests, deployment configuration and the runtime image. |
| `.gitignore` | Configuration / dependency list | Exclude private credentials, local databases and generated development files. |
| `.streamlit/config.toml` | Configuration / dependency list | Define the application visual theme. |
| `Dockerfile` | Configuration / dependency list | Build the Python application image with runtime dependencies and packaged defaults. |
| `README.md` | Markdown | Local AI Job Application Assistant. |
| `app.py` | Python | Streamlit entry point for local chat and explicit job-application commands. |
| `assets/README.md` | Markdown | Screenshot assets. |
| `assets/chat_window.png` | Binary PNG; sidecar metadata | Historical chat conversation screenshot; binary content unchanged. |
| `assets/docker_containers.png` | Binary PNG; sidecar metadata | Historical Docker Desktop service-list screenshot; binary content unchanged. |
| `assets/home_screen.png` | Binary PNG; sidecar metadata | Historical empty chat screenshot; binary content unchanged. |
| `assets/sidebar.png` | Binary PNG; sidecar metadata | Historical sidebar/model controls screenshot; binary content unchanged. |
| `assistant/__init__.py` | Python | Explicit actions for the personal assistant. |
| `assistant/cli.py` | Python | Run an action without starting Streamlit: python -m assistant.cli /help. |
| `assistant/commands.py` | Python | Command handlers are deterministic; plain chat alone goes to the model. |
| `assistant/comparison_cases.json` | Strict JSON; sidecar metadata | Define eight public synthetic known-failure comparison cases and expectations. |
| `assistant/comparison_review.py` | Python | Provisional model judgments and explicit, snapshot-bound reviewer decisions. |
| `assistant/config.py` | Python | Resolve typed runtime settings from environment variables and non-secret defaults. |
| `assistant/edit_policy.py` | Python | Narrow JD-tailoring boundaries; these checks do not establish semantic truth. |
| `assistant/evaluate.py` | Python | Small public synthetic regression diagnostic; never writes to Google or workflow state. |
| `assistant/evidence.py` | Python | Read-only source ingestion and provisional evidence comparison. |
| `assistant/google.py` | Python | Google REST adapter. Does not import chat or application business logic. |
| `assistant/jobs.py` | Python | Configuration and bounded job-application command registration. |
| `assistant/layout.py` | Python | Explicit formatting for assistant-owned drafts; never rewrites resume claims. |
| `assistant/model.py` | Python | Self-hosted model calls; no hosted fallback or tool execution. |
| `assistant/package.py` | Python | Optional letter drafting, explicit inclusion review and package summaries. |
| `assistant/requirements.py` | Python | Manual JD scope review: candidate enumeration never delegates coverage to a model. |
| `assistant/resumes.py` | Python | Create owned draft tabs and apply explicitly selected, reviewed changes. |
| `assistant/review_ui.py` | Python | Read-only comparison inspection; decisions still go through explicit commands. |
| `assistant/runtime.py` | Python | Shared command-registry construction and local-model diagnostics. |
| `assistant/schemas.py` | Python | Output contracts passed to Ollama and validated before domain checks. |
| `assistant/state.py` | Python | Local private workflow state, independent of chat history. |
| `assistant/tracking.py` | Python | Write prepared applications into a dedicated tab in the copied workbook. |
| `config/defaults.toml` | Configuration / dependency list | Provide public non-secret compatibility defaults with typed environment overrides. |
| `docker-compose.yml` | Configuration / dependency list | Run local Ollama, PostgreSQL and app services with bounded mounts and configurable host settings. |
| `docs/COMMANDS.md` | Markdown | Manual commands. |
| `docs/CONVENTIONS.md` | Markdown | Project conventions. |
| `docs/DOCUMENTATION_AUDIT.md` | Markdown | Documentation handover audit. |
| `docs/EXTENDING.md` | Markdown | Adding a command or module. |
| `docs/FILE_INVENTORY.md` | Markdown | Reviewed file inventory and sidecar metadata for strict JSON and binary assets. |
| `docs/HANDOVER.md` | Markdown | Handover runbook. |
| `docs/PLAN.md` | Markdown | Command-first job application assistant. |
| `docs/REVIEW.md` | Markdown | Review and merge guide. |
| `docs/TESTING.md` | Markdown | How to test the assistant. |
| `docs/TEST_REPORT_TEMPLATE.md` | Markdown | Manual test report. |
| `docs/VALIDATION.md` | Markdown | Validation status. |
| `docs/evaluations/qwen3-1.7b-comparison-2026-10-21.json` | Strict JSON; sidecar metadata | Retain the historical eight-case Qwen3 1.7b diagnostic and accuracy limitations. |
| `docs/evaluations/qwen3-4b-comparison-2026-10-21.json` | Strict JSON; sidecar metadata | Retain a historical model-startup failure report without claiming semantic accuracy. |
| `examples/config.sample.json` | Strict JSON; sidecar metadata | Demonstrate the complete resource configuration shape using placeholder IDs. |
| `examples/jd.sample.json` | Strict JSON; sidecar metadata | Supply a synthetic four-candidate job description for controlled acceptance tests. |
| `helpers.py` | Python | Transactional chat-history persistence helpers. |
| `postgres/__init__.py` | Python | Chat persistence package namespace. |
| `postgres/db.py` | Python | SQLAlchemy chat-database configuration and session factory. |
| `postgres/initialize.py` | Python | Command-line initialization of missing chat database tables. |
| `postgres/models.py` | Python | SQLAlchemy models for chat sessions and messages. |
| `pyproject.toml` | Configuration / dependency list | Configure shared Python formatting, import ordering and docstring lint checks. |
| `requirements-dev.txt` | Configuration / dependency list | Install runtime dependencies and the pinned repository validation tool. |
| `requirements.txt` | Configuration / dependency list | Declare runtime Python dependencies for the local assistant. |
| `scripts/check_consistency.py` | Python | Check tracked file metadata, Python documentation, data formats and local links. |
| `tests/live/test_services.py` | Python | Opt-in checks: explicitly select this folder and point at disposable services. |
| `tests/test_cli.py` | Python | CLI process tests verify public exit-code and stdin contracts without Google/model calls. |
| `tests/test_commands.py` | Python | Regression coverage for commands. |
| `tests/test_comparison_review.py` | Python | Regression coverage for comparison review. |
| `tests/test_config.py` | Python | Validate default compatibility and dynamic environment configuration overrides. |
| `tests/test_evidence.py` | Python | Regression coverage for evidence. |
| `tests/test_google.py` | Python | Regression coverage for google. |
| `tests/test_jobs.py` | Python | Regression coverage for jobs. |
| `tests/test_layout.py` | Python | Regression coverage for layout. |
| `tests/test_model.py` | Python | Regression coverage for model. |
| `tests/test_requirements.py` | Python | Regression coverage for requirements. |
| `tests/test_resumes.py` | Python | Regression coverage for resumes. |
| `tests/test_review_ui.py` | Python | Exercise actual Streamlit inspection without Google, a model or decision writes. |
| `tests/test_ui.py` | Python | Offline Streamlit smoke test; no credentials or model service needed. |
| `tests/test_workflow.py` | Python | Integration of commands/state with explicit in-memory Google and model doubles. |
