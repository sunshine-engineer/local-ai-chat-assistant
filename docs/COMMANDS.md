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
/configure {"source_folder_ids":["SOURCE_FOLDER_ID"],"local_source_dirs":["/absolute/project/docs"],"jd_folder_id":"JD_FOLDER_ID","resume_doc_id":"RESUME_DOC_ID","cover_letter_folder_id":"LETTERS_FOLDER_ID","tracker_id":"SPREADSHEET_ID","tracker_tab":"Applications","tracker_columns":{"application_id":"Application ID","company":"Company","role":"Role","job_url":"Job URL","jd_url":"JD","resume_url":"Resume","status":"Status","prepared_date":"Prepared Date"}}
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
