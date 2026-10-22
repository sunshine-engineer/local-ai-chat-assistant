<!--
File: docs/CONVENTIONS.md
Purpose: Project conventions.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->

# Project conventions

Outline: file metadata → Python organization and docstrings → configuration boundaries → required checks.

## Metadata and ownership

Comment-capable files carry their repository-relative file name, purpose, `Maintainer: sunshine-engineer` and ISO modified date. The maintainer is the user-requested project convention, not an assertion about historical authorship. Update the date when modifying a file; do not rewrite historical test-run dates to make old evidence appear new.

Python modules use their module docstring as the file header. Markdown uses an HTML comment before the heading. YAML, TOML, environment examples, requirement lists and ignore files use `#` comments. The Docker syntax directive must remain the first line. Strict JSON and PNG files cannot receive comment headers: [FILE_INVENTORY.md](FILE_INVENTORY.md) supplies sidecar descriptions and review metadata. No JSON keys, source authors, capture timestamps or image ownership metadata are invented.

Text is UTF-8 with LF endings, a final newline and spaces for indentation. Python uses Ruff's formatter at 100 columns; JSON uses two spaces; YAML/TOML follow two-space indentation where nested. Markdown preserves intentional trailing spaces. Binary images are never passed through text formatters. Historical screenshots stay clearly labelled as historical, not current runtime evidence.

## Python layout and documentation

Order module documentation, standard-library imports, third-party imports, local imports, constants/default initialization, logically ordered functions/classes, and the guarded entry point. Dependencies can require exceptions: schema constants follow their builder; local imports remain when they avoid an adapter/domain cycle, defer optional OAuth dependencies, or initialize chat storage only after `.env` is loaded. Database initialization and Streamlit rendering run from explicit `main()` entry points.

Every named function, method and class, including fixtures and nested callbacks, has a purpose docstring. Function docstrings describe each non-self parameter, returned/yielded value where meaningful, and validation/provider exceptions where applicable. Use Google-style `Args`, `Returns`/`Yields`, `Raises` and `Examples` sections. Test methods describe the invariant under test; constructors and procedures need not repeat an implicit None return. Inline lambdas are short expressions rather than separately documentable declarations. Complex UTF-16 indexing and configuration helpers have small examples.

Docstrings describe actual behavior, not a promise that a quote proves a generated claim. Preserve human-review gates, exact-batch approvals, source ownership, retry checkpoints and unrelated-tab/range checks during structural edits. Keep public import paths unless a deliberate migration updates all callers.

## Configuration and fixed constants

`config/defaults.toml` contains non-secret compatibility defaults. `assistant.config.setting` resolves environment overrides at use time with the default's type. `.env.example` demonstrates public settings; private `.env`, OAuth credentials and workflow state remain ignored. The CLI/UI load `.env`; the defaults helper itself has no dotenv or database side effects.

Model endpoint/name/budgets, Google timeout, tracker timezone, chat starting values and workflow home are configurable. Compose supplies matching PostgreSQL fields, optional container names and host ports through environment interpolation. Existing volumes retain their own initialized database credentials; changing an environment value is not a database credential migration. Defaults preserve the prior local-demo values, which are not deployment secrets or production credentials.

Fixed Google API endpoints/scopes, document MIME types, supported verdicts, fixed tracker schema, review bounds and the compact-format preset remain application/protocol constants. Making those values editable by model output would weaken the established boundary. Synthetic provider URLs/credentials inside tests are fixtures, not real account secrets. [HANDOVER.md](HANDOVER.md) is the operator-facing settings reference.

## Required checks

Install `requirements-dev.txt`, then run from the repository root:

```bash
python -m ruff check .
python -m ruff format --check .
python scripts/check_consistency.py
python -m compileall -q assistant app.py helpers.py postgres tests scripts
python -m unittest discover -s tests -v
git diff --check
```

The consistency checker enumerates the Git index so it never crawls ignored personal state. Stage new files before running it. It parses Python, JSON and TOML, checks named-callable/parameter documentation, metadata, LF/newline conventions, JSON/binary sidecars and local Markdown targets/anchors. Ruff checks imports, common code errors, docstrings and formatting. External URLs are not fetched by these checks.

CI also validates default and customized Compose configurations, builds the actual Dockerfile and runs the complete offline suite inside that image with networking disabled. Google/model acceptance stays opt-in against copies/disposable services; a formatting/configuration PR does not itself prove live model accuracy. Do not label skipped/unavailable provider tests as passing.
