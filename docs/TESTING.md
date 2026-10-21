# How to test the assistant

Outline: choose the branch → run offline checks → configure local services and sandbox resources → walk through one application → test failures/recovery → record results for PR review.

## 1. Choose what you are testing

| Test level | Needs | Establishes | Does not establish |
|---|---|---|---|
| Offline suite | Python and project dependencies | Routing, workflow/state behavior with doubles, CLI exit codes, UI commands, recovery and write boundaries | Google authentication, real model quality, PDF layout |
| Local model check | Running Ollama and an installed model | Model connectivity and actual output for the selected model | Google access or factual accuracy of every suggestion |
| Sandbox acceptance | Your own Google OAuth client, copied Docs/Sheet, configured model | Actual manual application preparation against copies | Production readiness, public hosting, job submission |

The PRs are stacked. Test the latest stack branch to exercise all modules without merging:

```bash
git fetch origin
git switch feat/resume-formatting
```

If you already have uncommitted work, preserve it before switching. Review/merge order is documented in [REVIEW.md](REVIEW.md). Do not merge to run these tests.

## 2. Prepare Python and run offline checks

Run from the repository root. Python 3.12+ is the target.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**Linux/WSL:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

For the remaining commands, activate that environment, or replace `python` with its full environment executable:

```powershell
# PowerShell; activation is optional if execution policy blocks it
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux/WSL
source .venv/bin/activate
```

Expected: all tests pass, including CLI subprocess tests and the Streamlit AppTest. These require neither Google credentials nor a running Ollama service. Google and model responses are replaced with explicit test doubles in workflow tests. Temporary state is isolated from your normal `.assistant` directory.

Additional checks:

```bash
python -m compileall -q assistant app.py helpers.py postgres tests
git diff --check
docker compose --env-file .env.example config --quiet
```

The Docker command validates configuration only; it does not start or test containers.

CLI checks:

```bash
python -m assistant.cli /help
python -m assistant.cli /not_a_command
```

Expected: `/help` lists actions and exits 0. An unknown command prints guidance and exits 1. Missing/non-command CLI input exits 2. An action validation failure exits 1. Inspect `$LASTEXITCODE` in PowerShell or `$?` in Bash immediately after the command. `/status` is a diagnostic message: it can exit 0 while reporting that Ollama is unavailable, so read its output.

## 3. Prepare local services and sandbox resources

### Environment and model

Copy `.env.example` to `.env` only if `.env` does not already exist; preserve existing settings.

```powershell
# PowerShell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

```bash
# Linux/WSL
if [ ! -f .env ]; then cp .env.example .env; fi
```

Run Ollama in Docker; no host Ollama installation is needed:

```bash
docker compose up -d ollama
docker compose exec ollama ollama list
docker compose exec ollama ollama pull qwen3:1.7b
python -m assistant.cli /status
```

For the full container app, run `docker compose up --build -d` and open `http://localhost:8501`. The first build downloads Python dependencies and can take time. Complete Desktop OAuth using the host CLI before starting Google commands in the container; both use the repository's private `.assistant` directory. Keep the browser callback on the host.

Pull only if that model is not installed. It is the tested local smoke-test baseline; it still requires factual review and hardware-specific measurement. Expected: `/status` reports a reachable service and lists the model matching `OLLAMA_MODEL`. `OLLAMA_HOST` defaults to `http://localhost:11434` for local execution. See [COMMANDS.md](COMMANDS.md) for context-budget settings.

### Google account and copies

1. Use a dedicated temporary Drive folder. Copy your resume document and tracker workbook into it; keep originals outside this folder.
2. Follow [Google OAuth setup](COMMANDS.md#google-setup). The app needs its own Desktop OAuth client; this chat's connector authorization does not carry over.
3. Keep the client JSON outside Git. Authenticate on your desktop with `python -m assistant.cli /google_connect /absolute/private/client.json`. On Windows pass the actual private Windows path in quotes.
4. Copy `examples/config.sample.json` into a private working folder and replace every `REPLACE_WITH_...` value with a copied resource ID. The three output folder values must be the same sandbox folder ID.
5. Select one actual resume tab initially. Its Google Docs URL contains `tab=t...`; use that value for `resume_tab_ids`. Exclude cover-letter tabs. Add copied project Markdown sources later through `local_source_dirs` if needed.
6. Set `tracker_tab` to `Assistant Applications`. The app creates this dedicated tab in the copied workbook; it does not populate the original workbook's custom Tracker tab.

Configuration is already saved privately in `.assistant/workflow.sqlite3` in the development checkout for the supplied sandbox copies. `/sources` shows the current configuration. Do not overwrite that configuration just to follow an example.

**PowerShell payload input:**

```powershell
Get-Content -Raw 'C:\private\assistant-config.json' | python -m assistant.cli /configure
```

**Linux/WSL payload input:**

```bash
python -m assistant.cli /configure < /absolute/private/assistant-config.json
```

Use real paths for your machine. Then run `/sources` and inspect the IDs carefully. Tokens and private workflow state must remain ignored by Git; `git status --short` should not show them. Do not paste credentials or personal document contents into GitHub test reports.

## 4. Walk through one synthetic application

Use [the synthetic JD](../examples/jd.sample.json) first. It is test data, not a real role. The same unchanged input produces the same application ID, which supports retry checks.

Start the UI with `streamlit run app.py`, or use the CLI. Enter each slash command separately. Replace `APPLICATION_ID` with the ID returned by `/save_jd`.

To load the sample JD via CLI:

```powershell
Get-Content -Raw examples/jd.sample.json | python -m assistant.cli /save_jd
```

```bash
python -m assistant.cli /save_jd < examples/jd.sample.json
```

| Step | Command | Expected result / acceptance check | Google writes |
|---|---|---|---|
| 1 | `/help` | Available commands appear; ordinary text remains chat | None |
| 2 | `/sources` | Only intended sandbox outputs and selected references appear | None |
| 3 | `/save_jd` with sample JSON | Application ID and new JD link; original text preserved; missing fields are unknown | New Doc in sandbox |
| 4 | `/refresh_sources` | Selected resume and evidence sources listed; skipped files reported | None |
| 5 | `/show_sources` | Catalogue IDs and source links are inspectable | None |
| 6 | `/compare_resume APPLICATION_ID` | Every extracted requirement quotes the JD; matches cite source text; gaps and counts are explained | None |
| 7 | `/draft_resume APPLICATION_ID` | Exactly one new draft tab; previous tabs and source resume remain intact | New tab in copied Doc |
| 8 | `/suggest_edits APPLICATION_ID` | Proposed before/after text and source citations; no remote resume edit | None |
| 9 | `/apply_edits` with reviewed JSON | Only selected edits appear in the owned draft tab | Draft tab only |
| 10 | Inspect the draft in Google Docs/PDF | Facts, headings, links, page count and spacing are acceptable | Manual review |
| 11 | `/approve_resume APPLICATION_ID` | Your review of the current content/layout is recorded | None |
| 12, optional | `/draft_cover_letter APPLICATION_ID` | Draft link and evidence list; review wording and layout manually | New Doc in sandbox |
| 13 | `/init_tracker` | Dedicated Assistant Applications tab; existing tabs/formulas unchanged | New tab in copied Sheet |
| 14 | `/track_application APPLICATION_ID` | Proposed row appears; sheet has no new row yet | None |
| 15 | `/track_application APPLICATION_ID --write` | One verified row with artifact links and Prepared status | Dedicated tracker tab |
| 16 | `/application_summary APPLICATION_ID` | Links and missing steps appear; complete package says prepared for you to apply | None |

For step 9, use only edit IDs you actually reviewed. Example payload:

```json
{"application_id":"APPLICATION_ID","edit_ids":[0],"reviewed":true}
```

Paste the payload after `/apply_edits` in the UI, or save it privately and pipe it into `python -m assistant.cli /apply_edits` using the same stdin patterns above. If no suggestions are suitable, skip applying edits, review the copied resume, and approve that version.

Create an optional cover letter before writing the tracker row so its link is included. If added later, the app does not silently update the existing row. The summary never means that an application was submitted.

### Formatting acceptance

On a sandbox draft, preview `/format_resume APPLICATION_ID`. Confirm the preset and that approval is unchanged. Run `/format_resume APPLICATION_ID --write`, then repeat it. Expected: no text change, no new tab, verified compact styles, other tabs unchanged, and approval cleared. Pending edits must block formatting. Export the selected draft tab to PDF and inspect every page; confirm that dates, contact details and education remain readable. Only then run `/approve_resume APPLICATION_ID` again. Repeating the preset does not guarantee two pages on arbitrary input.

### Quality review

Check at least these cases in actual model output:

- A skill explicitly supported by a source: quotation must exist and support the proposed claim in context.
- A requirement with no evidence: report a gap instead of inventing experience.
- Personal RAG/agent projects: do not turn these into commercial GenAI employment.
- Dates, company names, metrics and years of experience: preserve verified facts.
- Instructions embedded inside a JD: treat them as source text, never as permission to invoke tools or alter files.

Record the model name, context settings and elapsed time for comparison/suggestion commands. An exact quotation check is necessary but does not prove semantic accuracy. One successful sample is not a benchmark.

## 5. Retry and failure checks

Use sandbox copies only. Never deliberately test failures on original documents.

| Scenario | Expected behavior |
|---|---|
| Repeat the same JD input | Same application ID and JD artifact; no duplicate |
| Repeat `/draft_resume` | Existing draft link; no additional tab |
| Repeat the same successful `/apply_edits` payload | No second application of replacements |
| Repeat tracker `--write` | Same verified row; no duplicate |
| Tracker preview | No remote row change |
| Resume changes after approval | Tracking stops until another review/approval |
| Resume source changes before drafting | Drafting stops; refresh/recompare before creating the draft |
| Recompare after a draft exists | Stops to preserve the draft's evidence snapshot |
| Output target outside sandbox | Write stops; original files remain unchanged |
| Occupied/formula-containing reserved tracker row | Stops; existing values remain intact |
| Network interruption with uncertain write result | Retry the identical command and input; reconcile before starting a different edit batch |
| Model returns invalid/truncated JSON or fabricated quote | Command fails; no proposed remote edit is applied |

Offline tests simulate uncertain remote success; you do not need to interrupt your network to prove that case.

If a draft was changed externally and the old pending batch can no longer be reconciled:

1. Open the current draft and inspect the exact text you want to keep.
2. Run `/reset_edits {"application_id":"APPLICATION_ID","keep_current":true}`.
3. Expected: remote draft unchanged, pending local edits/suggestions cleared, prior approval invalidated.
4. Generate fresh suggestions or review/approve the current draft again. Reset does not undo remote changes.

Do not delete `.assistant` to recover a failed command: that removes local checkpoints and protected-original configuration. Back it up privately before moving machines. Do not publish a backup containing OAuth tokens or personal documents.

### Troubleshooting

| Symptom | Next check |
|---|---|
| Missing module/import | Confirm the active Python environment; install requirements with that interpreter |
| `/status` reports unavailable | Start Ollama; check OLLAMA_HOST and `ollama list` |
| Model input exceeds budget | Narrow resume tabs/evidence; adjust model/context only after measuring memory and quality |
| Google not connected / expired | Run the desktop OAuth command again; do not put tokens into `.env` or chat |
| Google 403 org_internal | Set Audience to External/Testing and add your personal account as a test user |
| Google HTTP 403 | Check enabled APIs, OAuth scopes and permission on the sandbox copies |
| Sandbox write refused | Confirm the copied document/workbook is directly inside the configured folder |
| Unsupported resume structure | Use a paragraph/text template; tables/lists/embedded objects are not copied by this version |
| Unexpected tracker headers | Use the dedicated Assistant Applications tab; do not overwrite your existing custom tracker |
| Another command running | Let it finish, then retry; do not start a second instance with separate state |

## 6. Optional real-service regression tests

These tests are separate from the default suite. Use an isolated PostgreSQL database named `assistant_test`; the test creates chat records. Point the model URL at your Docker Ollama endpoint. In Bash:

```bash
export ASSISTANT_LIVE_OLLAMA=http://127.0.0.1:11434
export ASSISTANT_LIVE_MODEL=qwen3:1.7b
export ASSISTANT_LIVE_DATABASE_URL=postgresql+psycopg2://TEST_USER:TEST_PASSWORD@127.0.0.1:TEST_PORT/assistant_test
python -m unittest discover -s tests/live -v
```

In PowerShell set the same names with `$env:NAME = 'value'`. Omit the database variable to skip that test. These checks exercise real chat, a synthetic supported/gap comparison, and database persistence; they do not run Google writes. Run model checks serially to avoid CPU queueing. For Google acceptance, use the manual command sequence above against sandbox copies.

## 7. Record the result

Use [TEST_REPORT_TEMPLATE.md](TEST_REPORT_TEMPLATE.md) for review evidence. Distinguish offline pass, actual app OAuth execution, connector-only checks, real model checks and manual PDF review. A missing credential/service is **not run**, not pass. See [VALIDATION.md](VALIDATION.md) for the current development snapshot.
