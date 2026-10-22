# Manual commands

Outline: connect Google → configure sandbox copies → save JD → review scope/evidence → draft and review artifacts → track and inspect the summary.

This is a single-user local app. Use `streamlit run app.py` or the terminal CLI. Commands execute only their named action. Use `/help` for available commands. JSON payloads can span multiple lines.

## Google setup

1. Create a Google Cloud project and enable Drive, Docs and Sheets APIs.
2. In Google Auth Platform → Audience, choose **External** and publishing status **Testing** for a personal Gmail account. Add your Gmail address under **Test users**. Internal audience is restricted to the parent organization and causes `403 org_internal` for personal Gmail.
3. Create a **Desktop app** OAuth client and download its JSON outside the repository.
4. Install dependencies and run on your own desktop:
   `python -m assistant.cli /google_connect /absolute/private/client.json`
5. Complete consent in the browser. The token lives under `.assistant/token.json`, ignored by Git. Never paste credentials into chat. Testing-mode refresh tokens can expire; reconnect if prompted.

The initial adapter uses Google REST APIs, with OAuth scopes for reading Drive and editing Docs/Sheets. These permissions are account-wide; configured IDs restrict application behavior, not the OAuth grant itself. This app does not inherit Codex connector credentials. MCP can be introduced behind the adapter after server capabilities are validated.

## Configure resources

Resource IDs are the ID portions of Google URLs. Source folders are read only. Only explicitly configured output documents/folders and the tracker receive writes.

```text
/configure {"sandbox_folder_id":"SANDBOX_FOLDER_ID","source_folder_ids":["SOURCE_FOLDER_ID"],"local_source_dirs":["/absolute/project/docs"],"jd_folder_id":"SANDBOX_FOLDER_ID","resume_doc_id":"RESUME_DOC_ID","cover_letter_folder_id":"SANDBOX_FOLDER_ID","tracker_id":"SPREADSHEET_ID","tracker_tab":"Assistant Applications"}
/sources
```

Use [config.sample.json](../examples/config.sample.json) as the complete starting shape. `/configure` merges fields with existing settings; omitted keys are retained. Use empty arrays to clear source lists. Include `resume_tab_ids` to select actual resume tabs. A new clone contains no private configuration or OAuth token.

Configure only what the current module needs. The tracker module creates a dedicated Assistant Applications tab with an Application ID column for reliable retries; it preserves your existing sheets.

## Save a JD

```text
/save_jd {"company":"Example","role":"GenAI Engineer","url":"https://example.com/jobs/123","jd":"Full original job description..."}
```

Or put that JSON in a private file:

```bash
python -m assistant.cli /save_jd < /absolute/private/jd.json
```

The same input yields the same application ID. The generated Doc preserves the JD and labels missing metadata as unknown. Metadata comes from your supplied fields; no model extraction is claimed. It writes a readable heading and sections as plain text. JD summarization is deferred to the comparison module. Document content is read back; visual/PDF layout is not validated.

Remote documents carry an application key for retry reconciliation. Do not edit generated JD artifacts while a failed write is being retried. A content mismatch stops the action instead of overwriting your edits. Do not run two copies of the app against the same account with separate state folders.

References: [OAuth desktop flow](https://developers.google.com/identity/protocols/oauth2/native-app), [Drive file creation](https://developers.google.com/workspace/drive/api/guides/create-file), [Docs requests](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/request).

## Evidence and comparison

- `/refresh_sources`: reads Google Docs directly in configured folders (no recursive Drive scan), selected resume tabs, and local Markdown/text files recursively. Reports skipped files. No remote files change.
- `/show_sources`: lists catalogue IDs and links.
- `/requirements APPLICATION_ID`: lists every exact non-empty JD sentence/line candidate, without a model call or Google write.
- `/review_requirements {"application_id":"APPLICATION_ID","candidate_ids":[1,2,3],"reviewed":true}`: saves 1–30 reviewed candidate IDs. Include required and desirable skills, duties and qualifications; exclude marketing and application instructions. IDs depend on the JD; inspect the list first. Scope becomes fixed once a resume or letter draft exists.
- `/compare_resume APPLICATION_ID`: requires reviewed JD scope, assesses every selected sentence against each resume, keeps model counts provisional, then assesses supporting documents separately. Counts cover only selected sentences; they are not a complete-JD score. Saves a source snapshot with results. Exact quotations are validated; model interpretations still need review. Model calls assess at most three requirements per batch by default to bound output size.

Set `resume_tab_ids` to the tab IDs you want compared. Otherwise non-empty tabs except cover letters and app-generated drafts are candidates. Keep the candidate set small for initial tests. Readmes are portfolio evidence, not proof of production work. Source content is sent only to the configured Ollama endpoint. Set OLLAMA_CONTEXT (default 16384) and ASSISTANT_PROMPT_CHAR_LIMIT (default 24000) for your model and hardware; oversized input fails rather than being silently truncated. Model quality/latency is not validated by offline tests.

## Sandbox-only writes

All Google writes require `sandbox_folder_id`. Output folders must equal that folder. Resume and tracker writes additionally verify the target file is directly inside it. Use copies of your documents and workbook; keep originals outside this folder. An optional private `protected_original_ids` state record additionally blocks listed original IDs as write targets; it is not a `/configure` field. Keep originals outside the sandbox regardless. OAuth grants themselves are not folder-restricted.

Your existing tracker can stay unchanged inside its copy. The tracking module will create a dedicated `Assistant Applications` tab in the copied workbook, with stable headers for application IDs, artifact links and status. Existing Tracker, dashboard, formulas and other tabs are preserved.

## Resume draft and explicit edits

```text
/draft_resume APPLICATION_ID
/suggest_edits APPLICATION_ID
/apply_edits {"application_id":"APPLICATION_ID","edit_ids":[0,2],"edit_batch_id":"CURRENT_BATCH_ID","reviewed":true}
/approve_resume APPLICATION_ID
```

Drafting copies the explicitly selected, comparison-reviewed resume into a new `Assistant — APPLICATION_ID` tab inside the sandbox resume document. It preserves paragraph and text styles for paragraph-only templates. Tables, native lists, embedded objects, header/footer content and unresolved suggestions are rejected before creating a draft. The two general resume tabs inspected in the supplied sandbox copy use supported text/paragraph structures. Rendering/PDF fidelity still needs manual review.

Suggestions cite exact source excerpts but their factual meaning is not mechanically proven. Review them before applying. Only selected edits are applied, within the owned draft tab, with revision guards and readback. Other tabs are checked for changes. Repeating the same completed command does not apply edits twice. An ambiguous write must be reconciled using the same command before generating new suggestions. `/approve_resume` is your declaration that you inspected the current content and layout; the app does not claim automated PDF validation.

## Tracking and package summary

```text
/draft_cover_letter APPLICATION_ID
/show_cover_letter APPLICATION_ID
# If a letter was drafted, submit its completed approve/omit review template first.
/init_tracker
/track_application APPLICATION_ID
/track_application APPLICATION_ID --write
/application_summary APPLICATION_ID
```

`/init_tracker` creates only the dedicated `Assistant Applications` tab in the copied workbook. The original tracker layout contains custom scoring columns; this first version preserves them and uses a dedicated tab instead of forcing a new schema onto existing data. Configure `tracker_tab` as `Assistant Applications`. Custom tracker-column mappings are deferred; this version uses the documented fixed headers.

Tracking first previews the proposed row. `--write` saves only after comparison review, current resume approval and approval/omission of any generated letter. Dates use Asia/Kolkata. Status is Prepared, never Applied. The command checks duplicate application IDs and job URLs, refuses occupied/formula-containing reserved rows, writes RAW text and reads back the exact row. Capacity is 999 entries. Local state locking prevents two app commands from writing simultaneously; Sheets has no cell compare-and-swap here, so avoid manually editing the dedicated tab during a write. Existing tabs and formulas receive no update requests.

Cover letters are optional; skip both draft/show commands when no letter is needed. If drafted, [review or omit it](#review-optional-cover-letters-before-inclusion) before tracking. Evidence references are returned separately. Review every statement; citation existence does not prove semantic support. Creating a letter after tracking does not silently change the existing tracker row; update it manually in the sandbox if needed. Application summaries list missing steps and never claim a submitted application. Voice, automated chains, broad Google actions and multiple agents remain deferred.


## Recover from a conflicting external edit

`/reset_edits {"application_id":"APPLICATION_ID","keep_current":true}` reads the current draft, preserves it remotely, clears local suggestions/pending edit state and invalidates approval. Inspect the current draft before using it. It does not undo remote edits. Then generate new suggestions or review and approve again. Recomparison is blocked once a draft exists, preserving the draft's evidence snapshot.

See [TESTING.md](TESTING.md) for the full Windows/WSL walkthrough, retry checks, model quality checks and failure expectations.


## Google login troubleshooting

- **403 org_internal / organization-only app:** change Google Auth Platform → Audience to External, keep Testing, add your personal Google account as a test user, save, then restart/reopen consent. If organization policy prevents External, create the personal assistant in a project under your personal account instead. Changing audience in the same project does not require replacing its Desktop client JSON.
- **403 access_denied / app still being tested:** confirm that the exact account you selected is listed under Test users.
- **No popup:** the terminal prints a Google consent URL. Open it in your normal browser; browser launching may be unavailable in WSL/headless environments.
- **Localhost cannot be reached after consent:** the callback must reach the same machine running the CLI. Use the CLI on your desktop rather than inside a container. Do not paste callback codes/tokens into chat.
- **Google API disabled:** enable Drive API, Docs API and Sheets API in the same Cloud project as the OAuth client.

Reference: [Google Auth Platform audience and testing rules](https://support.google.com/cloud/answer/15549945?hl=en). Test-user authorizations and their offline refresh tokens expire after seven days while the app remains in Testing.


## Compact resume formatting

```text
/format_resume APPLICATION_ID
/format_resume APPLICATION_ID --write
/approve_resume APPLICATION_ID
```

The first command previews the preset without a Google request. The write command changes only the owned draft tab: 10.5-point text, 36-point margins, 105% line spacing, zero paragraph space above and 2 points below. It preserves text, bold, links and alignment; all text uses one font size. No model call or content shortening is involved.

A completed draft without pending edits is required. Writes use the current Google revision and verify requested styles, unchanged text and unchanged other tabs. Approval is invalidated before the remote write, including when the request times out. Retry the same command if its result is uncertain, then export and inspect the PDF before approving again. Different templates can still exceed two pages. The command has no automatic undo; restore formatting manually in the copied tab or create a separate application variant.

Reference: [Google Docs formatting request API](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/request).


## Requirement scope and comparison limits

The previous automatic extraction passed structural checks while selecting a marketing sentence and omitting technical requirements on a real JD. It has been replaced by explicit scope review. `/requirements` includes all candidates so no model silently removes a sentence. You must still check your selection for omissions; one sentence may contain multiple skills, and counts are sentence-level comparisons.

Reselecting requirements before a draft clears the old comparison and source snapshot. A changed JD invalidates review. More than 200 candidates requires a shorter JD; more than 30 selected candidates is rejected without truncation. Once a resume or letter draft exists, use a new application variant instead of changing its evidence scope.

`ASSISTANT_REQUIREMENT_BATCH_SIZE` defaults to 3 and accepts 1–5. Smaller batches reduce per-call output size, but a full comparison can take several minutes per resume on CPU. Every selected requirement must have exactly one validated match; missing or duplicate matches fail without saving a partial comparison.


## Local project evidence in Docker

Set `ASSISTANT_EVIDENCE_DIR` in your private `.env` to the host reference folder. Use the path syntax for the shell running Compose: an absolute `/mnt/c/...` path in WSL, or `C:/...` in Windows. Quote values containing spaces. Compose mounts it at `/evidence` read-only and refuses to create a missing host directory. Recreate the app container after changing this setting.

Configure `local_source_dirs` using paths **inside** the app container, such as `/evidence/projects`. Choose the directory containing actual project case studies or READMEs; exclude templates, maintenance instructions and aspirational notes. The catalogue reads Markdown/text recursively. Unsupported formats are not converted by this version.

Run command payloads in that same container so their paths resolve consistently:

```bash
docker compose exec -T chatbot python -m assistant.cli /configure < private-config.json
docker compose exec -T chatbot python -m assistant.cli /refresh_sources
docker compose exec -T chatbot python -m assistant.cli /show_sources
```

PowerShell: `Get-Content -Raw private-config.json | docker compose exec -T chatbot python -m assistant.cli /configure`.

The browser OAuth command still runs on the host, with private `.assistant` state shared into the app. A host Python UI/CLI uses actual host paths in `local_source_dirs`; `/evidence` is only the container mount. Do not alternate host and container catalogue refresh commands against one configuration whose paths only exist in one environment.


## Review comparison evidence before using it

```text
/compare_resume APPLICATION_ID
/show_comparison APPLICATION_ID
/review_comparison { ...completed review template... }
/draft_resume APPLICATION_ID
```

Every model verdict is returned as `proposed_status` alongside `status: needs_review`. `proposed_counts` are informational; accepted `counts` remain null and `recommended_source_id` remains null. There is no automatic ranking/selection based on model judgments. `/show_comparison` provides the frozen source texts/links, snapshot ID and an intentionally incomplete template that cannot be accepted unchanged.

For a **one-requirement** comparison, a completed payload has this shape:

```json
{
  "application_id": "APPLICATION_ID",
  "comparison_id": "EXACT_COMPARISON_ID",
  "source_id": "CHOSEN_RESUME_SOURCE_ID",
  "reviewed": true,
  "decisions": [{
    "requirement_id": 0,
    "status": "supported",
    "quote": "EXACT SUPPORTING SOURCE TEXT",
    "note": "Explain which requirement this evidence supports and what remains unproven.",
    "acknowledged_flags": []
  }]
}
```

Supply one unique decision for **every** selected requirement. Choose supported, partial or gap yourself. Gap quotations must be empty; other quotations must occur literally in that frozen source. Every decision needs a note. Reviewing a resume explicitly selects it. Review each project source needed for generation separately before creating a resume or cover-letter draft; project documentation alone cannot fully establish commercial/production experience.

Heuristic flags cover missing explicit technology terms, no specific term overlap, missing production/commercial qualifiers, and future/negated context. They are incomplete and can be wrong. Correct the verdict/quote, or explicitly list every remaining flag in `acknowledged_flags` with an explanatory note. Overrides are retained in review history. A clean flag list never makes a proposal accepted automatically.

Only the selected reviewed resume and reviewed projects contribute evidence to generation. Their generation text contains only accepted non-gap quotations. All-gap reviews can still lead to a manually inspected resume copy, but cannot generate unsupported suggestions/letters. Accepted quotes still do not prove that a model's new wording follows from them: inspect every proposed edit and letter.

Recomparison resets selection and decisions. Review payloads bind to the comparison ID, JD and source snapshot. Decisions freeze after a resume or letter draft exists. Comparisons created before review version 1 cannot authorize new generation, approval or tracking; their artifacts are preserved. Start a new application variant to use the controlled flow: submit the same `/save_jd` fields with an additional `"variant":"comparison-review-v1"`. The label creates separate state without changing JD text, role, company or job URL. Identical labels/inputs retry stably; existing artifacts are retained. Tracker duplicate-job-URL protection still applies, so reconcile an already tracked job manually instead of creating a second entry. No original document is changed by these review commands. `/show_comparison` includes personal reference text: keep its output private.


Tailoring also protects detected name/contact lines and rejects new digit-based numerical claims absent from both the original span and accepted citation. These checks are deliberately narrow heuristics, not factual certification. Edits and cached cover-letter paragraphs are revalidated immediately before remote writes. Each `/suggest_edits` response includes `edit_batch_id`; `/apply_edits` requires that exact ID, selected edit IDs and `reviewed:true`. Regenerating or changing proposals invalidates stale selections instead of reusing an old ID against different text. Legacy suggestions must be regenerated.


### Review optional cover letters before inclusion

`/draft_cover_letter APPLICATION_ID` creates a draft, never an approved letter. Run `/show_cover_letter APPLICATION_ID`, inspect the actual Google document against the accepted quotations, and submit its template:

```text
/review_cover_letter {"application_id":"APPLICATION_ID","text_hash":"CURRENT_TEXT_HASH","decision":"approve","reviewed":true,"note":"Explain the claim-by-claim review."}
```

Use `"decision":"omit"` to preserve the draft but exclude it from the package and tracker. An unreviewed draft blocks tracking and keeps the summary incomplete. Approval binds to the current document text; later changes require renewed review. Existing tracker rows are never silently rewritten when an inclusion decision changes: reconcile the exact conflicting row manually. Valid citations alone do not prove implementation, production experience, performance or impact.


## Diagnostics and command inventory

`/help` lists the live registry. `/status` checks model connectivity and installed models; it reports unavailable service in its message even when CLI exit code is 0. A reachable service does not establish model quality. Ordinary text remains chat and cannot execute application actions.

For every environment default, accepted configuration key, state location, backup boundary and handover acceptance check, use [HANDOVER.md](HANDOVER.md).
