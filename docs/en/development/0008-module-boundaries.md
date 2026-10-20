# Module split and API boundaries

[中文](../../zh/development/0008-module-boundaries.md) | [English](../../en/development/0008-module-boundaries.md)

<!-- doc-sync: module-boundaries-log / 2026-10-20-r4 -->

## Scope and sources

Status: module refactoring passed fixture and installation checks; awaiting review.
The allocation increment is paused. Branch: `refactor/module-boundaries`. [PR #8](https://github.com/Requora/TAPF_MAPF_TPG/pull/8).
GitHub confirmed PR #7 merged; baseline is `6dbed6cdaddb21c9ecf50644eae7ff82b76a386a`.
Source is existing code at that baseline; API 0.7 is unchanged. No new upstream
dependency or native integration. The user reference bundle is unchanged and excluded.

## Decisions and structure

At the user's request, place order_source, task_compiler, action_timing, and serialization in separate
directories. Package entry points explicitly export public APIs; implementations and
validation stay internal to their packages. Group tests and fixtures accordingly.
Keep `contracts.py` as the sole contract source without copying DTOs or Protocols.
Apply descriptive responsibility names requested in review. Old package imports must migrate
to the new names, without aliases; class names, function names, and JSON contracts are unchanged.
The [directory graph and dependency rules](../architecture/MODULES.md) separate implemented
modules from planned interfaces. Add a static dependency gate and test that it rejects
internal imports and reverse dependencies. AGENTS defines module directory rules and
retains the user's clarification that docs do not count toward the 500-line limit.
Update fixture and replay paths in historical logs without changing historical verification claims.

## Actual replay

These are actual compiler fixture outputs, not motion execution traces:

| Input | Expected and observed result |
| --- | --- |
| Idle robots, new task bound to B | A has no actions; B has lift, serve, drop, each 0.3 s |
| Existing task and B's new task use the same shelf | CONFLICT, related_ids ('new-task', 'shelf') |

```bash
PYTHONPATH=src:tests python - <<'PYTHON'
from dataclasses import replace
from task_compiler.test_task_compiler import fixture
from warehouse_api.task_compiler import CurrentTaskCompiler
from warehouse_api.contracts import Failure, RobotQueue, TaskDelta
model, accepted = fixture()
compiler = CurrentTaskCompiler(model, sim_dt_s=0.1)
task = replace(accepted.tasks[0].task, id='new-task')
draft = TaskDelta((task,), (RobotQueue('B', (task.id,)),))
for name, request in [('idle', replace(accepted, tasks=(), queues=())), ('shelf-conflict', accepted)]:
    result = compiler.compile_jobs(request, draft)
    if isinstance(result, Failure):
        print(name, result)
    else:
        print(name, [(job.robot_id, [(action.kind, action.duration_s) for action in job.actions]) for job in result])
PYTHON
```

## Verification and failure record

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-names-7vku970l/wheels /tmp/warehouse-names-7vku970l/project
/tmp/warehouse-names-7vku970l/venv/bin/python -m pip check
/tmp/warehouse-names-7vku970l/venv/bin/python -I -m unittest discover -s tests
git diff --check
```

Source and the wheel installed in a new virtual environment both pass 64 tests:
61 existing behavior tests and 3 new API/dependency checks. Ruff, pip check, and diff checks pass.
Old build/lib files exist locally, so build from pyproject.toml and src copied into a
fresh temporary directory, excluding caches and egg-info. Install the wheel in a new
venv to avoid stale artifacts. The temporary paths above record this run; subsequent
verification requires a new clean build directory and environment.
No tests failed. Bilingual docs passed gpt-6-luna / low review, including execution
of the replay command above. Remote CI passed at `b8d9a29`; results for this review correction are pending confirmation.

Historical pickle compatibility, dynamic import constraints, allocation optimization,
native solvers, Runtime commits, continuous geometry, and parking safety are unverified.
This change only refactors module boundaries.

## Review triage and correction

Check all 3 PR #8 findings against the renamed code with actual reproductions:

| Finding | Decision and evidence |
| --- | --- |
| [Guard Bypass](https://github.com/Requora/TAPF_MAPF_TPG/pull/8#discussion_r4320624328) | No change needed. Root-package imports still pass through dependency checks after normalization; importing order_source from serialization or contracts returns forbidden dependency. Attribute access is already explicitly outside the architecture check's scope. |
| [Missing Module Check](https://github.com/Requora/TAPF_MAPF_TPG/pull/8#discussion_r4320624333) | No change needed. A temporary foo/bar.py causes assertIn to raise AssertionError mentioning foo before violations runs, without reaching a KeyError. |
| [Export Check Too Weak](https://github.com/Requora/TAPF_MAPF_TPG/pull/8#discussion_r4320624336) | Accepted. Assert that exported objects' __module__ belongs to their package. Temporarily replacing action_duration_s with an external lambda passed before the change and is rejected afterward. |

Add only 4 assertion lines in tests; production code is unchanged. All 64 tests pass
against source and the existing clean installed wheel; Ruff and diff checks pass.
Package source is unchanged, so reuse the naming revision's wheel without rebuilding.
The following command reproduces all three conclusions. Its two AssertionErrors are
expected rejections, not unhandled test failures.

```bash
PYTHONPATH=src:tests python - <<'PYTHON'
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import warehouse_api
from warehouse_api import action_timing
from test_module_boundaries import ModuleBoundaryTests, violations
for owner in ('serialization', 'contracts'):
    print(owner, violations('from warehouse_api import order_source', f'warehouse_api.{owner}', 'warehouse_api'))
with TemporaryDirectory() as directory:
    root = Path(directory)
    (root / 'foo').mkdir()
    (root / 'foo/bar.py').write_text('from warehouse_api.contracts import Order\n')
    with patch.object(warehouse_api, '__file__', str(root / '__init__.py')):
        with TestCase().assertRaises(AssertionError) as caught:
            ModuleBoundaryTests().test_source_uses_only_allowed_public_dependencies()
        print(type(caught.exception).__name__, caught.exception)
with patch.object(action_timing, 'action_duration_s', lambda: None):
    with TestCase().assertRaisesRegex(AssertionError, 'implementation must belong to this package'):
        ModuleBoundaryTests().test_public_exports_use_descriptive_import_paths()
    print('wrong export rejected')
PYTHON
```

## Project progress and architecture website

[Open the private website](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site) / [English](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site/?lang=en).
This is a manually maintained snapshot, not an execution trace or live GitHub dashboard.
The evidence baseline is `a785121`.

The user requested this maintained website as an addition to the current PR. Source lives in
`web/progress/`, using buildless static HTML/CSS/JS. Warm colors, whitespace, and clear hierarchy
draw on Apple/OpenAI's minimal visual style without using their brand marks.
The page supports Chinese/English switching, horizontal diagram scrolling on phones, and mouse
or keyboard module selection. Details show responsibilities, implemented scope, missing work,
inputs/outputs, and source links. It distinguishes 5 modules with implementations, 7 interface-only
modules, 1 planned joint TAPF module, and 1 out-of-scope backend. These counts are not completion scores.

The target workflow has 14 nodes and 15 planned connections, all dashed. The current code graph
has 5 nodes and 5 actual import dependencies, drawn solid. Current work, allocation work deferred
until merge, and the missing execution loop are shown separately. The page explicitly states that
the PR is unmerged, native solver integrations number 0, and continuous safety is unverified.
AGENTS now requires upkeep of status, diagrams, evidence, both languages, deployment, and checks.

Local verification:

```bash
# Start static preview in another terminal; choose a free port if occupied.
python -m http.server 38167 --bind 127.0.0.1 --directory web/progress/dist
# Playwright is only a website development tool, not a warehouse_api runtime dependency.
/tmp/warehouse-web-tools/bin/python web/progress/check.py http://127.0.0.1:38167
/tmp/warehouse-ci-check/bin/ruff check web/progress/check.py
```

Observed output: `PASS: two languages, both diagrams, 28 module selections, keyboard, mobile layout, no JS errors`.
Manually inspected 1440 px desktop and 390 px mobile screenshots. No page-level horizontal overflow;
the mobile diagram scrolls horizontally. Screenshots are stored at
`/tmp/warehouse-progress-desktop.png` and `/tmp/warehouse-progress-mobile.png`.
Also inspected the English flow diagram. Fixed edge labels hidden behind nodes and checked again.
Initial fixed port 8765 was occupied, so switched to automatically assigned port 38167.
The service on the original port was neither modified nor stopped.

Private publication succeeded with project_id `appgprj_6ad6c9324f348191aab84e8bfffe6102`.
Sites source commit: `614a297632fd55a9ff72d925e7b22bf47ed38fc3`.
version_id: `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_8ecaeb4ba3e48191aaf1a5b746d33f6d`.
The native tool returned `succeeded`; access scope was unchanged. Local browser verification and
hosted publication success are separate evidence. Hosted login flow was not browser-tested.
No scheduled updates or external connectors were added.

Maintenance entry points: content and graph data in `dist/project.js`, progress and evidence
presentation in `dist/app.js`, styling in `dist/style.css`, and page structure in `dist/index.html`.
Update the snapshot date, baseline, status, and evidence together. After PR merge, update the
awaiting-review text and baseline everywhere rather than changing a single status label.

For later publishing, reuse the project_id in `web/progress/.openai/hosting.json`. Follow the Sites
skill to fetch this Site and open its remote source with the source helper in a separate empty
directory. Sync reviewed website files from this repository. After checks, use that source helper
to commit, push, and package, then publish with the existing private audience. Never run a helper
that manages the Sites Git remote inside the main repository. Pass credentials through stdin only;
do not write them to disk.

## Line counts and next step

With Git rename detection, code and tests against origin/main are +473/-17, or 490 changed lines.
Without rename detection, the count is +1937/-1481, including entire moved files.
Moves do not compress or rewrite algorithms. Docs are counted separately, plus 8 configuration lines for Sites hosting and a Git ignore exception for static source. All 332 website and browser-check lines count as code.
After submission, await user review and merge before starting the smallest increment
in the separate allocation module.
