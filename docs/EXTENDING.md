<!--
File: docs/EXTENDING.md
Purpose: Adding a command or module.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->

# Adding a command or module

Outline: define the boundary → implement a handler → register the command → test offline → validate against sandbox resources → document the result.

Follow [CONVENTIONS.md](CONVENTIONS.md) for headers, docstrings, runtime defaults and the required validation commands. New adjustable settings belong in `config/defaults.toml` and must have documented environment overrides; preserve legitimate safety/protocol constants.

## 1. Define one action

| Decision | Example from resume formatting |
|---|---|
| Input | Application ID and optional `--write` |
| Read targets | Saved draft state and the copied resume document |
| Write target | That application's owned draft tab |
| Preview | Show exact preset without requesting a remote write |
| Failure boundary | Stop on pending edits, wrong ownership, revision conflict or failed readback |
| Retry | Reapply the same style preset without changing content or creating tabs |
| Approval | Clear approval before a potentially successful remote write |
| Output | Verified result and draft link; require PDF review |

Keep each command small enough to test on its own. Automating a sequence later should reuse these handlers rather than introduce a second write path.

## 2. Implement the handler

Use [layout.py](../assistant/layout.py) as the concrete example. Handlers receive `jobs` and the argument string. Parse input before writing. Return a string, normally JSON for structured output. Raise `ValueError` for an expected validation failure so CLI/UI can report it consistently.

Use `jobs.application(id)` to load the application and `jobs.save(id, app)` for checkpoints. Save recovery state before remote writes. Local state and Google requests are not one transaction: a timeout can happen after Google commits a change.

Use `jobs.google` for Google requests. Call `check_write` for the target and apply the module's narrower ownership rule as well. Sandbox membership alone does not mean that every copied tab or occupied tracker row is safe to change. Document writes use a revision guard; read the exact result back. Preserve unrelated tabs and formulas.

Keep adapters separate from domain decisions. A future MCP adapter should expose the bounded operations the handler needs; changing transport must preserve ownership, retry and readback checks. The current project uses Google REST, not an MCP client.

## 3. Register it once

Add the handler to the `commands` list in [Jobs.register](../assistant/jobs.py). The list supplies name, help text and a callable receiving the argument string. Its wrapper already acquires the local action lock; do not acquire that lock again inside the handler.

Both Streamlit and the CLI build the same registry through [runtime.py](../assistant/runtime.py). `/help` comes from registry descriptions. Unknown slash commands fail instead of reaching the chat model. Ordinary chat does not directly execute tools.

Resource IDs and local source directories belong in `/configure`. Its allowed-key list is explicit: add validation when introducing a new configuration field. Model, timeout and context settings belong in the environment. Credentials remain outside Git.

## 4. If the action uses a model

Call `generate_json` with an explicit output schema from [schemas.py](../assistant/schemas.py), then validate domain meaning and exact citations before offering a write. Pass external text as source data. Model output cannot choose arbitrary tools or invoke another command.

A schema can enforce shape and literal quotations, but cannot prove that a paragraph follows from a quotation. Keep employment and independent portfolio evidence distinct and require review of generated claims.

## 5. Verify and document

Use a temporary `Store` and explicit provider doubles for offline tests. Exercise the actual handler, including no-write preview, wrong target, approval invalidation, uncertain remote success, retry and preservation of unrelated data. See [test_layout.py](../tests/test_layout.py) and [test_workflow.py](../tests/test_workflow.py).

Then run only the authorized sandbox acceptance path against real services. A passing mock test does not prove the API accepts a request or that a document renders correctly. Check output at the layer users consume it: Google readback, tracker range and rendered PDF where relevant.

Update `README.md`, `COMMANDS.md`, `TESTING.md` and `VALIDATION.md`; update `HANDOVER.md` for changed settings, state, recovery or ownership boundaries and `DOCUMENTATION_AUDIT.md` for affected coverage. Publish sanitized evidence in an unmerged PR. Never commit tokens, OAuth client files, personal source text, live test artifacts or credential-bearing logs.


## Preserve the comparison control boundary

Treat model results as proposals. Do not derive remote writes or accepted counts from `proposed_status`/`proposed_counts`, and do not select a resume automatically. Comparison review requires explicit decisions for every selected requirement bound to a comparison/JD/source snapshot; it is a human step. A future agent or automation must not generate reviewer acknowledgements on the user's behalf.

Use `reviewed_sources` for downstream gates and `generation_sources` for the accepted quotation pool. Do not send the full unreviewed catalogue back into generation. Preserve review history and separate project evidence from employment claims. Add sanitized failures to `assistant/comparison_cases.json`, test both the controls and the configured model, and report service failures separately from semantic errors. Passing fixtures never authorizes removing human control.
