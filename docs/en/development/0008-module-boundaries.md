# Module split and API boundaries

[中文](../../zh/development/0008-module-boundaries.md) | [English](../../en/development/0008-module-boundaries.md)

<!-- doc-sync: module-boundaries-log / 2026-10-20-r1 -->

## Scope and sources

Status: module refactoring passed fixture and installation checks; awaiting review.
The allocation increment is paused. Branch: `refactor/module-boundaries`. PR: pending creation.
GitHub confirmed PR #7 merged; baseline is `6dbed6cdaddb21c9ecf50644eae7ff82b76a386a`.
Source is existing code at that baseline; API 0.7 is unchanged. No new upstream
dependency or native integration. The user reference bundle is unchanged and excluded.

## Decisions and structure

At the user's request, first place orders, compiler, durations, and codec in separate
directories. Package entry points explicitly export public APIs; implementations and
validation stay internal to their packages. Group tests and fixtures accordingly.
Keep `contracts.py` as the sole contract source without copying DTOs or Protocols.
Preserve public imports so existing callers do not need business-code changes when files move.
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
from compiler.test_compiler import fixture
from warehouse_api.compiler import CurrentTaskCompiler
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
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-modules-4v_xlj0q/wheels /tmp/warehouse-modules-4v_xlj0q/project
/tmp/warehouse-modules-4v_xlj0q/venv/bin/python -m pip check
/tmp/warehouse-modules-4v_xlj0q/venv/bin/python -I -m unittest discover -s tests
git diff --check
```

Source and the wheel installed in a new virtual environment both pass 64 tests:
61 existing behavior tests and 3 new API/dependency checks. Ruff, pip check, and diff checks pass.
Old build/lib files exist locally, so build from pyproject.toml and src copied into a
fresh temporary directory, excluding caches and egg-info. Install the wheel in a new
venv to avoid stale artifacts. The temporary paths above record this run; subsequent
verification requires a new clean build directory and environment.
No tests failed. Bilingual docs passed gpt-6-luna / low review, including execution
of the replay command above. Remote CI is pending PR creation.

Historical pickle compatibility, dynamic import constraints, allocation optimization,
native solvers, Runtime commits, continuous geometry, and parking safety are unverified.
This change only refactors module boundaries.

## Line counts and next step

With Git rename detection, code and tests against origin/main are +125/-5, or 130 changed lines.
Without rename detection, the count is +1601/-1481, including entire moved files.
Moves do not compress or rewrite algorithms. Docs are counted separately; no configuration changes.
After submission, await user review and merge before starting the smallest increment
in the separate allocation module.
