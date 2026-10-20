# PR 7 - New-task bindings for idle robots

[中文](../../zh/development/0007-current-task-bindings.md) | [English](../../en/development/0007-current-task-bindings.md)

<!-- doc-sync: current-task-bindings / 2026-10-19-r2 -->

Date: 2026-10-19. Status: limited stage 4 increment, fixture verified, awaiting review.
Branch: `feat/current-task-bindings`. [PR #7](https://github.com/Requora/TAPF_MAPF_TPG/pull/7).
Baseline: GitHub confirmed PR #6 merged at `412ec329362320a644aa1aab29157d4adc888029`.

## Scope and sources

Extend `CurrentTaskCompiler.compile_jobs(request, draft)` to bind newly defined
Lift/Serve/Drop tasks to robots whose queues are empty or omitted. Keep public contracts and version unchanged.
Existing current tasks continue from projected progress. Omitted bindings remain unchanged.
This does not implement task selection, stock reservations, assignment optimization, or Runtime commits.

Sources: API 0.7 English guide sections 05-06 and DATA_TYPES_EN.md.
SHA256: guide `f13bb9275af485e8dcc2ae47e76db411bf8b38581175dd71a14b50f5b8713e7f`;
types `5c3ffe789c8f43061961fd89bb7c217781ecda259ddb8c26c8c5d06c7d601b05`.
Original repository code using only the standard library; no upstream dependency or native solver added.

## Decisions and observable behavior

Review addition: AGENTS.md requires each completed PR to explain its objective, implementation,
rationale, and completion verification to the user. Verification must include actual evidence and unverified boundaries.

- `TaskDelta.tasks` accepts only new definitions. IDs already present in the request return CONFLICT,
  including completed tasks. There is no historical ledger to detect ID reuse outside the request.
- Each new task must have exactly one binding. Duplicate task IDs, duplicate robots, unknown references,
  unbound definitions, or multiple executors return BAD_INPUT.
- Only one new task may be proposed for an empty queue. Its protected prefix is empty, so the candidate
  singleton suffix is the complete queue. Existing nonempty queues cannot be edited, even if their task
  is complete or locked_prefix_count is zero. Empty candidate suffixes, multiple candidate tasks,
  empty tasks, and assignment of existing unbound tasks return UNSUPPORTED.
- Boundary and candidate binding checks live in `_compiler_validation.py`.
  The compiler builds `TaskProgress(task, 0, False)` and bindings in local dictionaries.
  Existing action checks handle candidate pickup preconditions, shelf claims, targets, and quantized timing.
- Accepted task progress, action locks, and carry ownership remain effective. Candidates cannot repair
  invalid old locks. Success and failure leave the model, request, and draft unchanged; failures return no partial jobs.

Running `tests/test_candidate_bindings.py` and the replay command below produced:

| Scenario | A | B | Result |
| --- | --- | --- | --- |
| Idle robots, new task bound to B | Empty | Lift(home-node), Serve(station-node), Drop(return-node), 0.3 s each | Jobs |
| A carries a shelf, next_step=1 and Lift locked to A; new task uses another shelf | Original Serve, Drop | New Lift, Serve, Drop | Jobs |
| A's accepted task and B's new task use the same shelf | No partial output | No partial output | CONFLICT |

The conflict diagnostic is `Concurrent tasks claim the same shelf`, with related_ids
`('new-task', 'shelf')`. This is actual compiler fixture output, not a motion execution trace.
Replay the success and failure cases:

```bash
PYTHONPATH=src:tests python - <<'PY'
from dataclasses import replace
from test_compiler import fixture
from warehouse_api.codec import dumps
from warehouse_api.compiler import CurrentTaskCompiler
from warehouse_api.contracts import RobotQueue, TaskDelta
model, accepted = fixture()
compiler = CurrentTaskCompiler(model, sim_dt_s=0.1)
task = replace(accepted.tasks[0].task, id='new-task')
draft = TaskDelta((task,), (RobotQueue('B', (task.id,)),))
for name, request in [('idle', replace(accepted, tasks=(), queues=())), ('shelf-conflict', accepted)]:
    print(name, dumps(compiler.compile_jobs(request, draft)))
PY
```

## Verification and failure log

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-bindings-wheel .
/tmp/warehouse-ci-check/bin/python -m pip install --force-reinstall /tmp/warehouse-bindings-wheel/warehouse_planning_api-0.7.0-py3-none-any.whl
/tmp/warehouse-ci-check/bin/python -m pip check
/tmp/warehouse-ci-check/bin/python -I -m unittest discover -s tests -v
git diff --check
```

All 61 source and installed-wheel tests pass, including 12 new candidate binding tests.
Ruff, pip check, and diff checks pass. Hashes of all 160 reference files are unchanged.
No unexpected test failures. The first status query failed because gh is absent; the GitHub connector confirmed the merge.
The initial lookup used a nonexistent CI filename and scripts directory; the actual contracts.yml was then read.
Bilingual docs passed gpt-6-luna / low review. Remote CI results will be recorded in the PR.

No allocator, stock/demand feasibility, MAPF/TPG/TAPF, Runtime atomic commit,
continuous geometry, resource scheduling, or parking safety verification. Compiled jobs are not an acceptable execution proposal.

## Line counts and next step

Against main: code +209/-9, including tests; disclose documentation lines separately in the PR, with configuration unchanged.
Wait for user review and merge. Then pursue the smallest stage 5 allocation increment with stock/demand feasibility,
while continuing to defer reassignment and multi-task queues.
