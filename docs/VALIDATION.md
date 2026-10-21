# Validation status

## Confirmed

- Repository cloned locally; module branches and review PRs created without merging.
- 18 offline unit/integration tests pass, including manual workflow execution using explicit in-memory Google and model doubles.
- Streamlit initial rendering and /help submission pass in AppTest; CLI /help works.
- Three user-supplied Google files were copied into a temporary Drive sandbox using the connected Google Drive plugin, then listed/read back. Original files received no write requests.
- A general resume was copied into a new sandbox-only validation tab using the application's request builder and Google Docs batchUpdate via the connector. Content readback matches; the preceding 36 sandbox tabs' body, page and named styles are unchanged.
- Live request validation caught and corrected a page-size field mismatch and a read-only header/footer style flag. Page and named style requests now succeed on the inspected template.

## Not yet verified

- End-to-end app-owned OAuth, token refresh and Google API execution: the app needs a user-created Desktop OAuth client and consent on the user's machine. Connector authorization is separate and was not copied into the app.
- Real Ollama inference, comparison quality and generation latency: Ollama is not installed in this execution environment. Tests use model doubles. The inherited phi3:mini model remains a configurable starting point, not a validated recommendation.
- Actual tracker row writes and cover-letter creation through app OAuth.
- Docker services and PostgreSQL runtime: Docker CLI is present but daemon access is unavailable to this execution user. Compose configuration passes `docker compose --env-file .env.example config --quiet`.
- Rendered resume/PDF pagination. Content and style readback do not prove page fit.

## Practical limits

- Single user, one local state directory; no public deployment or simultaneous independent app instances.
- Sandbox writes only. Existing tracker sheets are preserved; new rows go into a dedicated Assistant Applications tab in the copied workbook.
- No source truth/semantic entailment guarantee: the app validates source quote existence, and requires human review before edits and tracking.
- No voice, automation, MCP client or autonomous multi-agent runtime in this phase.
