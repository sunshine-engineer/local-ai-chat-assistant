<!--
File: docs/REVIEW.md
Purpose: Review and merge guide.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->

# Review and merge guide

The implementation is split into stacked PRs. Nothing is merged automatically.

| Order | PR | Main review boundary |
|---|---|---|
| 1 | [#1](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/1) | Startup defaults, database sessions and explicit command routing |
| 2 | [#2](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/2) | App-owned Google OAuth and resumable JD capture |
| 3 | [#3](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/3) | Source catalogue, comparison and sandbox boundaries |
| 4 | [#4](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/4) | Owned resume draft tabs and reviewed edit execution |
| 5 | [#5](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/5) | Tracking, optional letter and package summary; live-tested style corrections |
| 6 | [#6](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/6) | CLI failures, conflict recovery, source snapshot stability and reviewer instructions |
| 7 | [#7](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/7) | Real model output contracts, restored chat, Google acceptance evidence and Docker/OAuth test instructions |
| 8 | [#8](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/8) | Preview-first compact formatting, renewed approval and two-page sandbox PDF validation |
| 9 | [#9](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/9) | Explicit JD scope review, bounded comparison batches and honest real-model limitations |
| 10 | [#10](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/10) | Read-only reference mount, actual project ingestion and clean-image Compose acceptance |
| 11 | [#11](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/11) | Snapshot-bound comparison review, accepted evidence only, protected edits, exact batch approval and cover-letter inclusion review |
| 12 | [#12](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/12) | Read-only comparison inspection, explicit proposal/decision separation and command-review walkthrough |
| 13 | [#13](https://github.com/sunshine-engineer/local-ai-chat-assistant/pull/13) | Documentation audit, corrected examples and development handover runbook |

PR #5 includes page/named style corrections found during live sandbox validation; assess the latest stack for the final behavior. Each PR diff is against its predecessor. Test the top branch before merging if you want to exercise the full app.

After merging a predecessor, inspect the next PR's base and diff before merging it. Retarget it to `main` if GitHub does not do so automatically. A squash merge can leave inherited commits visible in descendant PRs; rebase/resolve that stack deliberately rather than merging duplicate history. Do not delete predecessor branches until the next PR's base/diff is verified.

Start the recipient handover with [HANDOVER.md](HANDOVER.md), then record acceptance using the private test report template. Documentation coverage and unrun checks are listed in [DOCUMENTATION_AUDIT.md](DOCUMENTATION_AUDIT.md).

## Acceptance checklist

- CI is green on the exact commit under review; review the tests rather than treating green checks as proof of live integration.
- Follow [TESTING.md](TESTING.md) against copied Google resources and the intended local model.
- Check that original Docs/Sheets are not write targets, and no credentials or private document content are committed.
- Inspect generated resume claims and PDF layout; evidence quotes alone do not establish truth or relevance.
- Confirm tracking writes Prepared into the dedicated copied-workbook tab, preserving existing tabs/formulas.
- Confirm real failures remain visible and retries do not duplicate artifacts.
- Record any unrun OAuth/model/Docker/PDF checks in the test report before considering real use.

Scope remains text commands for one local user. Voice, automatic application flows, arbitrary Google editing, a live MCP client and autonomous multiple agents need separate future scope decisions.
