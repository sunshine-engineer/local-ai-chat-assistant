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

PR #5 includes page/named style corrections found during live sandbox validation; assess the latest stack for the final behavior. Each PR diff is against its predecessor. Test the top branch before merging if you want to exercise the full app.

After merging a predecessor, inspect the next PR's base and diff before merging it. Retarget it to `main` if GitHub does not do so automatically. A squash merge can leave inherited commits visible in descendant PRs; rebase/resolve that stack deliberately rather than merging duplicate history. Do not delete predecessor branches until the next PR's base/diff is verified.

## Acceptance checklist

- CI is green on the exact commit under review; review the tests rather than treating green checks as proof of live integration.
- Follow [TESTING.md](TESTING.md) against copied Google resources and the intended local model.
- Check that original Docs/Sheets are not write targets, and no credentials or private document content are committed.
- Inspect generated resume claims and PDF layout; evidence quotes alone do not establish truth or relevance.
- Confirm tracking writes Prepared into the dedicated copied-workbook tab, preserving existing tabs/formulas.
- Confirm real failures remain visible and retries do not duplicate artifacts.
- Record any unrun OAuth/model/Docker/PDF checks in the test report before considering real use.

Scope remains text commands for one local user. Voice, automatic application flows, arbitrary Google editing, a live MCP client and autonomous multiple agents need separate future scope decisions.
