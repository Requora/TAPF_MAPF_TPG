# Module split and API boundaries

[中文](../../zh/development/0008-module-boundaries.md) | [English](../../en/development/0008-module-boundaries.md)

<!-- doc-sync: module-boundaries-log / 2026-10-20-r2 -->

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
of the replay command above. Remote CI passed at `52f159d`; results for this naming revision are pending confirmation.

Historical pickle compatibility, dynamic import constraints, allocation optimization,
native solvers, Runtime commits, continuous geometry, and parking safety are unverified.
This change only refactors module boundaries.

## Line counts and next step

With Git rename detection, code and tests against origin/main are +137/-17, or 154 changed lines.
Without rename detection, the count is +1601/-1481, including entire moved files.
Moves do not compress or rewrite algorithms. Docs are counted separately; no configuration changes.
After submission, await user review and merge before starting the smallest increment
in the separate allocation module.
