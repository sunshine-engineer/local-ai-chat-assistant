# Validation status

Development snapshot: 2026-10-21. Results below separate real services from test doubles.

## Confirmed

| Layer | Evidence | Limit |
|---|---|---|
| Offline regression | 38 tests pass on host Python 3.14 and container Python 3.12: commands, CLI, UI chat/commands, recovery, source snapshots, citations, Unicode edits and tracker boundaries | Google/model doubles in workflow tests |
| Real local services | Three opt-in tests pass: Streamlit chat with Docker Qwen, synthetic supported/gap comparison, PostgreSQL message persistence | One small synthetic comparison is not a quality benchmark |
| App-owned Google login | Desktop browser consent, Drive/Docs/Sheets access and forced token refresh/persistence pass | Credentials remain private; testing-mode OAuth can need renewed consent |
| Google sandbox | Three supplied files copied/read back; copied resume has a validation tab with matching content/styles; preceding 36 tabs unchanged | Connector-assisted checks are distinct from app OAuth execution |
| App-owned tracker writes | Preview, RAW row write, exact readback and duplicate retry pass in the copied workbook; original tracker sample matches its pre-test snapshot | One synthetic application; existing custom tracker tabs are outside write scope |
| Real resume model calls | Comparison, suggestions and optional letter generated from a 5,718-character copied-resume snapshot | Snapshot checks alone do not prove Google writes; suggestions returned zero edits |
| Runtime | Docker Ollama and PostgreSQL plus a Streamlit test container run; Python 3.12 container regression exercised | Test runtime reused an existing dependency image |

Live testing found and fixed a missing chat import, empty JSON output, paraphrased evidence/requirements, and a cover-letter timeout. Action schemas now constrain literal quotations; response completion and schema validation run before domain checks. Human review still determines whether a claim follows from its evidence. A synthetic letter initially embellished scale despite a valid quote; stronger prompting reduces this risk but does not guarantee factual support.

CPU measurements on one test run: copied-resume comparison approximately 73 seconds, suggestions 122 seconds, and a successful letter retry 140 seconds. Some calls overlapped; these are observations, not benchmarks. Timeout defaults to 300 seconds and remains configurable. Qwen3:1.7b is a smoke-test baseline, not a model-quality recommendation.

## Acceptance result and remaining limits

- Full app-owned Google command sequence passes: JD save/retry, source refresh, comparison, resume draft/retry, suggestions, controlled reviewed edit/retry, local reset, approval, cover-letter save/reconciliation, tracker initialization/retry, row preview/write/retry, and final Prepared summary. The controlled edit is an explicit sandbox marker, not a model-generated recommendation. The first cover-letter save hit a network timeout; retry reconciled successfully. Existing resume tabs were checked for preservation during writes; all 38 tabs present before the final letter/tracker phase remained unchanged afterward.
- Clean build of the repository Dockerfile: dependency download timed out fetching PyArrow. Cache/retry settings were added, but the updated clean build has not passed. A reused dependency image was used for runtime checks.
- The copied template initially rendered across three pages, with education spilling onto page three. The new `/format_resume` preview/write command was exercised through app OAuth, including repeated writes. Exact text and all 37 other tabs were preserved, requested styles read back correctly, and approval was invalidated. A selected-tab PDF export then rendered as two readable pages; both were visually inspected and contained the validation marker. This sample passes page-fit inspection, but other inputs may need shortening. Approval and existing tracker reconciliation passed afterward without adding a row. No automatic page-count guarantee is provided.

## Practical limits

- Single user, one local state directory; no public deployment or simultaneous independent app instances.
- Sandbox writes only. Existing tracker sheets are preserved; new rows go into a dedicated Assistant Applications tab in the copied workbook.
- No source truth/semantic entailment guarantee: the app validates source quote existence and requires human review before edits and tracking.
- No voice, automation, MCP client or autonomous multi-agent runtime in this phase.

## Reproduce and review

Follow [TESTING.md](TESTING.md), including its opt-in real-service suite. Record sanitized outcomes with [TEST_REPORT_TEMPLATE.md](TEST_REPORT_TEMPLATE.md), and use [REVIEW.md](REVIEW.md) for the unmerged PR stack. Private tokens, source snapshots and live report files are excluded from Git.
