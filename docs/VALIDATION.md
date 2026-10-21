# Validation status

Development snapshot: 2026-10-21. Results below separate real services from test doubles.

## Confirmed

| Layer | Evidence | Limit |
|---|---|---|
| Offline regression | 47 tests pass on host Python 3.14 and in the clean repository-built Python 3.12 image with networking disabled: commands, CLI, UI chat/commands, recovery, source snapshots, citations, Unicode edits and tracker boundaries | Google/model doubles in workflow tests |
| Real local services | Three opt-in tests pass: Streamlit chat with Docker Qwen, synthetic supported/gap comparison, PostgreSQL message persistence | One small synthetic comparison is not a quality benchmark |
| App-owned Google login | Desktop browser consent, Drive/Docs/Sheets access and forced token refresh/persistence pass | Credentials remain private; testing-mode OAuth can need renewed consent |
| Google sandbox | Three supplied files copied/read back; copied resume has a validation tab with matching content/styles; preceding 36 tabs unchanged | Connector-assisted checks are distinct from app OAuth execution |
| App-owned tracker writes | Preview, RAW row write, exact readback and duplicate retry pass in the copied workbook; original tracker sample matches its pre-test snapshot | One synthetic application; existing custom tracker tabs are outside write scope |
| Real resume model calls | Comparison, suggestions and optional letter generated from a 5,718-character copied-resume snapshot | Snapshot checks alone do not prove Google writes; suggestions returned zero edits |
| Runtime | Clean repository Dockerfile build succeeded after download retries; all 47 offline tests passed in that image without network access | Dependencies remain unpinned; future builds may resolve newer releases |

Live testing found and fixed a missing chat import, empty JSON output, paraphrased evidence/requirements, and a cover-letter timeout. Action schemas now constrain literal quotations; response completion and schema validation run before domain checks. Human review still determines whether a claim follows from its evidence. A synthetic letter initially embellished scale despite a valid quote; stronger prompting reduces this risk but does not guarantee factual support.

CPU measurements on one test run: copied-resume comparison approximately 73 seconds, suggestions 122 seconds, and a successful letter retry 140 seconds. Some calls overlapped; these are observations, not benchmarks. Timeout defaults to 300 seconds and remains configurable. Qwen3:1.7b is a smoke-test baseline, not a model-quality recommendation.

## Acceptance result and remaining limits

- Full app-owned Google command sequence passes: JD save/retry, source refresh, comparison, resume draft/retry, suggestions, controlled reviewed edit/retry, local reset, approval, cover-letter save/reconciliation, tracker initialization/retry, row preview/write/retry, and final Prepared summary. The controlled edit is an explicit sandbox marker, not a model-generated recommendation. The first cover-letter save hit a network timeout; retry reconciled successfully. Existing resume tabs were checked for preservation during writes; all 38 tabs present before the final letter/tracker phase remained unchanged afterward.
- Clean Docker build now passes. Earlier attempts failed on a network timeout and a package-integrity mismatch; a later retry succeeded with hash verification unchanged. Valid cached downloads were reused. Runtime checks no longer depend solely on the reused dependency image.
- The copied template initially rendered across three pages, with education spilling onto page three. The new `/format_resume` preview/write command was exercised through app OAuth, including repeated writes. Exact text and all 37 other tabs were preserved, requested styles read back correctly, and approval was invalidated. A selected-tab PDF export then rendered as two readable pages; both were visually inspected and contained the validation marker. This sample passes page-fit inspection, but other inputs may need shortening. Approval and existing tracker reconciliation passed afterward without adding a row. No automatic page-count guarantee is provided.

## Practical limits

- Single user, one local state directory; no public deployment or simultaneous independent app instances.
- Sandbox writes only. Existing tracker sheets are preserved; new rows go into a dedicated Assistant Applications tab in the copied workbook.
- No source truth/semantic entailment guarantee: the app validates source quote existence and requires human review before edits and tracking.
- No voice, automation, MCP client or autonomous multi-agent runtime in this phase.

## Reproduce and review

Follow [TESTING.md](TESTING.md), including its opt-in real-service suite. Record sanitized outcomes with [TEST_REPORT_TEMPLATE.md](TEST_REPORT_TEMPLATE.md), and use [REVIEW.md](REVIEW.md) for the unmerged PR stack. Private tokens, source snapshots and live report files are excluded from Git.


## Real-JD quality correction

A real JD from the copied archive exposed a failure missed by the synthetic smoke test: automatic extraction selected one marketing sentence and omitted technical requirements. A Boolean classifier experiment also selected marketing and hiring-process text. Neither approach is accepted as reliable scope selection.

`/requirements` now enumerates every exact non-empty sentence/line, and `/review_requirements` requires explicit selection before `/compare_resume`. The model cannot remove items from the selected scope. Comparisons use bounded batches and reject missing or duplicate matches. The reviewer remains responsible for selecting the complete relevant scope; counts are sentence-level and apply only to that selection.

A tester-reviewed 17-sentence real-JD comparison completed in approximately 212 seconds with qwen3:1.7b. Every selected sentence had one structurally valid match, but semantic review found bad evidence choices, including a name-only quote supporting a technical requirement. Its judgments/counts are not accepted as reliable matching advice. Human review or a better evaluated model remains necessary. A first qwen3:4b attempt timed out during model startup. Retrying with a 6 GiB container limit completed three reviewed requirements in approximately 182 seconds, but manual review still found weak judgments. A reasoning-enabled experiment returned no usable JSON and was rejected. These experiments do not establish improved matching quality.

The supplied local reference folder was inspected read-only. Four project case studies under its project-content subfolder were ingested exactly and verified unchanged; profile maintenance files and templates were excluded by choosing that narrower directory. Full project-evidence model acceptance remains separate from this ingestion check.


## Container project references

The review app now runs from the clean repository-built image, launched through Compose with an isolated service-name/database/model override. The older manual app container was stopped after the Compose health check passed. The selected reference folder is mounted at `/evidence` with Docker reporting `RW: false`; private state remains writable separately. Its catalogue contains one selected GenAI resume and four project case studies. All four text values match the independently read host files, and the Streamlit health endpoint returns `ok`. Profile-maintenance files and templates remain outside the configured source subfolder.

Compose now supports `ASSISTANT_EVIDENCE_DIR` with a read-only bind and `create_host_path: false`. Container configurations use `/evidence/...` paths; host OAuth still uses the shared private state. Catalogue ingestion is not proof that model judgments about those files are accurate. Larger source sets may require narrower selection or a measured context budget for suggestion/letter generation.

The Compose acceptance reused the isolated PostgreSQL/Ollama services rather than starting another database/model. Both safe defaults and private source configuration passed `docker compose config --quiet`. The actual Compose-created app mount reports `/evidence RW=false`, shared state is present, and the UI health endpoint returns `ok` on the standard local port. This is not a fresh-empty-volume acceptance test for all three Compose services.

A focused real-service check against the selected Document QA case study passed after the lightweight model finished loading: RAG document question-answering was marked supported, commercial production Kubernetes was marked gap, and project evidence remained separate from resume experience. Elapsed time was approximately 106 seconds after an initial cold-load timeout. The returned RAG quotation covered the indexing pipeline; the surrounding source text was manually checked for question-answering context. This narrow smoke test does not overturn the poor judgments observed on the longer real JD.
