# Manual commands

This is a single-user local app. Use `streamlit run app.py` or the terminal CLI. Commands execute only their named action. Use `/help` for available commands. JSON payloads can span multiple lines.

## Google setup

1. Create a Google Cloud project and enable Drive, Docs and Sheets APIs.
2. Configure OAuth consent for your personal account; add yourself as a test user if the app is in testing.
3. Create a **Desktop app** OAuth client and download its JSON outside the repository.
4. Install dependencies and run on your own desktop:
   `python -m assistant.cli /google_connect /absolute/private/client.json`
5. Complete consent in the browser. The token lives under `.assistant/token.json`, ignored by Git. Never paste credentials into chat. Testing-mode refresh tokens can expire; reconnect if prompted.

The initial adapter uses Google REST APIs, with OAuth scopes for reading Drive and editing Docs/Sheets. These permissions are account-wide; configured IDs restrict application behavior, not the OAuth grant itself. This app does not inherit Codex connector credentials. MCP can be introduced behind the adapter after server capabilities are validated.

## Configure resources

Resource IDs are the ID portions of Google URLs. Source folders are read only. Only explicitly configured output documents/folders and the tracker receive writes.

```text
/configure {"sandbox_folder_id":"SANDBOX_FOLDER_ID","source_folder_ids":["SOURCE_FOLDER_ID"],"local_source_dirs":["/absolute/project/docs"],"jd_folder_id":"SANDBOX_FOLDER_ID","resume_doc_id":"RESUME_DOC_ID","cover_letter_folder_id":"SANDBOX_FOLDER_ID","tracker_id":"SPREADSHEET_ID","tracker_tab":"Applications","tracker_columns":{"application_id":"Application ID","company":"Company","role":"Role","job_url":"Job URL","jd_url":"JD","resume_url":"Resume","status":"Status","prepared_date":"Prepared Date"}}
/sources
```

Configure only what the current module needs. Tracker headers must match your existing sheet; a dedicated Application ID column is required for reliable retries. No columns are silently created.

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
- `/compare_resume APPLICATION_ID`: extracts quoted JD requirements, assesses each resume separately, recommends by supported/partial counts, then assesses supporting documents separately. Saves a source snapshot with results. Exact quotations are validated; the model's interpretation still needs review.

Set `resume_tab_ids` to the tab IDs you want compared. Otherwise non-empty tabs except cover letters and app-generated drafts are candidates. Keep the candidate set small for initial tests. Readmes are portfolio evidence, not proof of production work. Source content is sent only to the configured Ollama endpoint. Set OLLAMA_CONTEXT (default 16384) and ASSISTANT_PROMPT_CHAR_LIMIT (default 24000) for your model and hardware; oversized input fails rather than being silently truncated. Model quality/latency is not validated by offline tests.

## Sandbox-only writes

All Google writes require `sandbox_folder_id`. Output folders must equal that folder. Resume and tracker writes additionally verify the target file is directly inside it. Use copies of your documents and workbook; keep originals outside this folder. Set a private `protected_original_ids` list in workflow state to additionally prevent original IDs being configured as write targets. OAuth grants themselves are not folder-restricted.

Your existing tracker can stay unchanged inside its copy. The tracking module will create a dedicated `Assistant Applications` tab in the copied workbook, with stable headers for application IDs, artifact links and status. Existing Tracker, dashboard, formulas and other tabs are preserved.

## Resume draft and explicit edits

```text
/draft_resume APPLICATION_ID
/suggest_edits APPLICATION_ID
/apply_edits {"application_id":"APPLICATION_ID","edit_ids":[0,2],"reviewed":true}
/approve_resume APPLICATION_ID
```

Drafting copies the recommended resume into a new `Assistant — APPLICATION_ID` tab inside the sandbox resume document. It preserves paragraph and text styles for paragraph-only templates. Tables, native lists, embedded objects, header/footer content and unresolved suggestions are rejected before creating a draft. The two general resume tabs inspected in the supplied sandbox copy use supported text/paragraph structures. Rendering/PDF fidelity still needs manual review.

Suggestions cite exact source excerpts but their factual meaning is not mechanically proven. Review them before applying. Only selected edits are applied, within the owned draft tab, with revision guards and readback. Other tabs are checked for changes. Repeating the same completed command does not apply edits twice. An ambiguous write must be reconciled using the same command before generating new suggestions. `/approve_resume` is your declaration that you inspected the current content and layout; the app does not claim automated PDF validation.

## Tracking and package summary

```text
/init_tracker
/track_application APPLICATION_ID
/track_application APPLICATION_ID --write
/draft_cover_letter APPLICATION_ID
/application_summary APPLICATION_ID
```

`/init_tracker` creates only the dedicated `Assistant Applications` tab in the copied workbook. The original tracker layout contains custom scoring columns; this first version preserves them and uses a dedicated tab instead of forcing a new schema onto existing data. Configure `tracker_tab` as `Assistant Applications`. `tracker_columns` is reserved for future existing-header mapping; this version uses fixed documented headers and does not interpret that setting.

Tracking first previews the proposed row. `--write` saves only after current resume approval. Dates use Asia/Kolkata. Status is Prepared, never Applied. The command checks duplicate application IDs and job URLs, refuses occupied/formula-containing reserved rows, writes RAW text and reads back the exact row. Capacity is 999 entries. Local state locking prevents two app commands from writing simultaneously; Sheets has no cell compare-and-swap here, so avoid manually editing the dedicated tab during a write. Existing tabs and formulas receive no update requests.

Cover letters are optional drafts with evidence references returned separately. Review every statement; citation existence does not prove semantic support. Creating a letter after tracking does not silently change the existing tracker row; update it manually in the sandbox if needed. Application summaries list missing steps and never claim a submitted application. Voice, automated chains, broad Google actions and multiple agents remain deferred.
