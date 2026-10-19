# PR 1 - shared contracts and review workflow

[中文](../../zh/development/0001-contract-foundation.md) | [English](../../en/development/0001-contract-foundation.md)

<!-- doc-sync: foundation / 2026-10-19-r3 -->

Date: 2026-10-19. Status: review fixes prepared; waiting for user review and merge.
Branch: `feat/api-contract-foundation`. [PR #1](https://github.com/Requora/TAPF_MAPF_TPG/pull/1).

## Scope and provenance

The initial repository contained README.md and .gitignore at
`4f0109145ca3fbe3a8130a3cb94c757e2544d17e`.
The user supplied the untracked `warehouse_api_v0_7/` reference bundle.
Read the English guide, type definitions, reference code, and validation notes.
Keep that bundle unchanged. Import only its shared contracts into the package.

`src/warehouse_api/contracts.py` was initially copied from
`warehouse_api_v0_7/package/warehouse_api/contracts.py` (445 lines).
Review changed only Chinese field-description punctuation to English punctuation.
The file is no longer byte-identical; API fields, defaults, types, and Protocols remain unchanged.

- Original SHA256: `8608f438a78470fae3535dbc0b1180583a7ae83875921bf717251a2518318bbd`.
- Current SHA256: `ad02ec8870b84e01389ba8d8ef986038bf4dccb63e295a2cbc92cf0b1e13906a`.

Production code imports this package, not the reference bundle. Add package metadata,
import CI, development rules, and a module/research roadmap. Keep backend boundary
types; no simulator is implemented. No native solver has been built or integrated.

## Verification

Original baseline command, from the repository root:

```bash
PYTHONPATH=warehouse_api_v0_7/package python -m unittest discover -s warehouse_api_v0_7/package/tests -v
```

Result: 38 passed on Python 3.14.7. The first attempt inside the package directory
could not find `python`; using the root shell and explicit PYTHONPATH resolved it.
No source change was needed for that environment issue.

The initial package was built and installed into a temporary venv using
`python -m pip install /home/yimin/research/TAPF_MAPF_TPG`. From outside the repository,
`python -I` loaded the installed package and resolved 72 classes and 82 annotated methods.
This check did not depend on the reference bundle or a source-path import.

For this review, AST comparison ignored only the first argument of field helper `F`.
All remaining AST nodes matched the reference. Annotation resolution passed again.
Reran the 38 reference tests against the revised source contracts with this command:

```bash
PYTHONPATH=src python - <<'PYTHON'
from pathlib import Path
import unittest, warehouse_api
warehouse_api.__path__.append(str(Path('warehouse_api_v0_7/package/warehouse_api').resolve()))
suite = unittest.defaultTestLoader.discover('warehouse_api_v0_7/package/tests')
result = unittest.TextTestRunner().run(suite)
raise SystemExit(not result.wasSuccessful())
PYTHON
```

Observed: contracts loaded from `src/warehouse_api/contracts.py`; 72 classes and
82 annotated methods resolved; 38 tests passed. Reference helpers are supplied
through the package search path above. They are not shipped in this PR.

CI for the latest code commit `cb83b1c` passed on Python 3.10 and 3.14:
[run 39306082944](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39306082944).
Revised-commit CI is tracked on the PR checks page. These tests do not establish
production planner, Runtime, continuous collision, or native simulator correctness.

## Review fixes

- Per the latest user request, project documents now have only Chinese and English editions. Store them in `docs/zh/` and `docs/en/` with matching relative filenames and synchronized updates.
- The root README contains navigation only. Keep only the Chinese AGENTS file at the root; remove its English and Korean copies. Remove all Korean project documents added in this PR.
- This bilingual requirement supersedes the earlier [three-language request](https://github.com/Requora/TAPF_MAPF_TPG/pull/1#discussion_r4317490698). Preserve the supplied reference bundle.
- [English punctuation](https://github.com/Requora/TAPF_MAPF_TPG/pull/1#discussion_r4317495406): retain the normalized punctuation in project documents and contract field descriptions.
- [Communication principles](https://github.com/Requora/TAPF_MAPF_TPG/pull/1#discussion_r4317507084): AGENTS retains all six principles, including the 80% ASD-STE100 target, real traces, labeled teaching simplifications, and useful-only visualization.
- Documentation and configuration are excluded from the 500-line limit. Document checks remain delegated to a `gpt-6.1-sol` subagent with `low` reasoning.
- This revision only changes document layout, rules, and links. Code and configuration are unchanged, so code tests are not rerun. Record this round's document check results in the PR description.

Size against main: 446 added code lines (445 contracts + 1 initializer), no code
deletions. Packaging and CI are 39 configuration lines, counted separately.
Documentation is also separate. This includes raw code comments and blank lines,
so the effective code count remains below 500.

## Publication and next step

SSH push succeeded, but initial GitHub repository lookup and PR creation returned
HTTP 404. No authenticated local CLI fallback was available. The user installed
and authorized the connector for the organization. Retry succeeded and PR #1 opened
on 2026-10-19. The access failure is resolved.

Review these fixes in the same PR. No later development stage has started.
After the user merges this PR, confirm the remote merge and begin only the next
small codec/fixture PR. Do not merge or resolve the user's review threads automatically.
