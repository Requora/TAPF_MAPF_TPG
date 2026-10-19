# PR 1 — shared contracts and review workflow

Date: 2026-10-19. Status: branch pushed; PR creation blocked by GitHub connection.
Branch: `feat/api-contract-foundation`. No PR number has been created.
[Review diff / create PR](https://github.com/Requora/TAPF_MAPF_TPG/compare/main...feat/api-contract-foundation?expand=1).

## Scope and rationale

The tracked repository initially contained only README.md and .gitignore at
`4f0109145ca3fbe3a8130a3cb94c757e2544d17e`.
The user supplied the untracked `warehouse_api_v0_7/` specification bundle.
Read the English guide, type definitions, reference implementation and validation
notes. Keep the bundle intact and import only its shared contracts in this PR.

`src/warehouse_api/contracts.py` is a byte-for-byte copy of
`warehouse_api_v0_7/package/warehouse_api/contracts.py` (445 source lines).
Its SHA256 is
`8608f438a78470fae3535dbc0b1180583a7ae83875921bf717251a2518318bbd`.
Retain the supplied bilingual field metadata to avoid an API change.
Production code will import this single package, not the local reference bundle.

Add package metadata, import CI, AGENTS.md, and a module/research roadmap.
Backend message types and Protocols are retained; no simulator is implemented.
No upstream solver is vendored, compiled, or represented as operational.

## Verification

Reference baseline command, run from the repository root:

```bash
PYTHONPATH=warehouse_api_v0_7/package python -m unittest discover -s warehouse_api_v0_7/package/tests -v
```

Result: **38 passed**, Python 3.14.7. These are existing reference-package tests,
including its backend helper tests. They do not verify a production planner,
Runtime, continuous validator, or native simulator. The reference bundle remains
local and is not required by CI or package installation.

An initial test attempt used `python` inside the reference package directory;
that shell could not find the interpreter. Running from the repository root
with explicit PYTHONPATH resolved the environment issue; no source change was needed.

Standalone check: created a temporary venv, installed the repository using
`python -m pip install /home/yimin/research/TAPF_MAPF_TPG`, changed to a temporary
directory outside the repository, and imported with `python -I` (isolated mode).
Resolved all public class and annotated method types using `typing.get_type_hints`.
Observed output:

```text
Successfully installed warehouse-planning-api-0.7.0
API: 0.7
Loaded: /tmp/warehouse-pr1-57l_4xev/venv/lib/python3.14/site-packages/warehouse_api/contracts.py
Resolved classes: 72 annotated methods: 82
```

This verifies installation without the local reference bundle or source-path
imports. CI repeats installation and annotation resolution on Python 3.10 and
3.14; remote results are pending. Annotations describe data shapes; they do not
enforce runtime values, semantic constraints, or solver conformance.

Code/config scope: 485 raw added lines (445 contracts, 1 package initializer,
12 packaging metadata, 27 CI). No code deletions. This conservative count includes
comments and blank lines and is below the 500 effective-code-line limit.
README, AGENTS and development notes are documentation and are reported separately.

## Review focus and next step

- Verify that the source hash matches the supplied contract file.
- Review module boundaries, upstream candidates and the simulator exclusion.
- Review the <=500-code-line rule and the stop-until-user-merge rule in AGENTS.md.
- After this PR is merged, begin only the next small codec/fixture PR.

No work on that next PR is authorized before the user merges this one.

## Publication result

SSH push to `origin/feat/api-contract-foundation` succeeded. The connected GitHub
app returned HTTP 404 for both repository lookup and PR creation. Plugin discovery
confirmed GitHub is installed; accessible app installations did not include the
repository owner. No local GitHub CLI, CLI login, token environment variable or
Git credential helper was available for an authenticated API fallback.

The repository needs access through the GitHub connection to create the PR here.
Alternatively, the user can open the comparison link above and create the PR.
The branch contains all reviewable changes. Do not treat the comparison link as
an existing PR. Remote CI results could not be read (HTTP 404); local checks passed.
