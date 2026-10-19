# PR 5 - Candidate queue edits

[中文](../../zh/development/0005-candidate-queues.md) | [English](../../en/development/0005-candidate-queues.md)

<!-- doc-sync: candidate-queues / 2026-10-19-r1 -->

Date: 2026-10-19. Status: stage 4 queue helper implemented and fixture verified, pending review.
Branch: `feat/candidate-queue-edits`. [PR #5](https://github.com/Requora/TAPF_MAPF_TPG/pull/5).
Baseline: GitHub confirmed PR #4 merged at `65e0738ea6e43f94b39c507bd49291ecb873f059`.

## Scope and sources

Add `warehouse_api.queues.candidate_queues(request, draft)` returning
`tuple[RobotQueue, ...] | Failure`. Inputs use existing `AssignmentRequest`
and `TaskDelta` contracts. The returned queues are complete candidates, not
suffix edits to pass back as a new TaskDelta. No new DTO or Protocol.
This helper is one part of stage 4; `SharedCompiler.compile_jobs` is not implemented.

Source: local API 0.7 English guide sections 05-06 and `DATA_TYPES_EN.md`
entries for TaskDelta, QueueState, AssignmentRequest, and StepLock.
Their SHA256 values remain `f13bb9275af485e8dcc2ae47e76db411bf8b38581175dd71a14b50f5b8713e7f`
and `5c3ffe789c8f43061961fd89bb7c217781ecda259ddb8c26c8c5d06c7d601b05`.
Original repository code, standard library only; no upstream solver integration.

## Decisions and observable behavior

For each listed robot, use `old[:locked_prefix_count] + proposed_suffix`.
Omission preserves the old queue; an empty suffix clears only the mutable part.
A missing old queue means idle. Return every join-state robot in input order.
New definitions may stay unbound; old unbound tasks may be assigned.
Removing a binding does not delete a definition, cancel a task, or release reservations.

Validate all final bindings together, so a transfer is independent of edit order.
Reject unknown task/robot references, duplicate definitions/queue entries, invalid
prefix counts, invalid lock references, and inconsistent old ownership with `BAD_INPUT`.
Reject repeated candidate task bindings, including repetition within one queue,
or removal/change of a StepLock executor with `CONFLICT`.
Each failure includes a diagnostic and related IDs. Invalid old snapshots cannot
be repaired implicitly by the draft. Duplicate StepLocks are rejected as bad input.

This is the explicit-lock portion of D1, not complete D1 validation.
The helper trusts typed DTO shapes and supplied locks. It does not derive locks from
fixed motion, running actions, or carried shelves. It does not validate task action
semantics, projected progress, blocked-task execution, stock/demand feasibility,
geometry, or parking. A successful queue candidate does not authorize execution.
Task ID freshness is checked against supplied accepted definitions and this draft;
the caller must retain historical IDs to enforce run-wide non-reuse.
All request fields and draft data remain unchanged, on success and failure.

Actual helper outputs from `tests/test_queues.py`'s fixture:

| Case | Old state / edit | Result |
| --- | --- | --- |
| Clear suffix | R1=[A,B], prefix=1; R1 suffix=[] | R1=[A], R2=[C], R3=[] |
| Transfer B | R1 suffix=[], R2 suffix=[B,C] | R1=[A], R2=[B,C], R3=[] |
| Locked B | Same transfer; StepLock(B,0,R1) | CONFLICT; related_ids=[B,R1] |

Reproduce the failure using the real helper, not a solver or physical execution trace:

```bash
PYTHONPATH=src:tests python - <<'PY'
from dataclasses import replace
from test_queues import request_fixture
from warehouse_api.contracts import RobotQueue, StepLock, StepRef, TaskDelta
from warehouse_api.queues import candidate_queues
request = replace(request_fixture(), locks=(StepLock(StepRef('B', 0), 'R1'),))
draft = TaskDelta((), (RobotQueue('R1', ()), RobotQueue('R2', ('B', 'C'))))
print(candidate_queues(request, draft))
PY
```

```text
Failure(code='CONFLICT', message='StepLock executor cannot change or be removed', related_ids=('B', 'R1'))
```

## Verification and failures

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-queue-wheel .
/tmp/warehouse-ci-check/bin/python -m pip install --force-reinstall /tmp/warehouse-queue-wheel/warehouse_planning_api-0.7.0-py3-none-any.whl
/tmp/warehouse-ci-check/bin/python -m pip check
/tmp/warehouse-ci-check/bin/python -I -m unittest discover -s tests -v
git diff --check
```

Python 3.14.7: all 44 tests pass from source and the installed wheel, including
11 new queue tests. Coverage includes atomic transfer, prefix boundaries, idle robots,
definition freshness, lock conflicts, malformed snapshots, input immutability,
and JSON replay. Ruff and pip check pass. No unexpected test failures.
The initial `gh` lookup failed because the CLI is absent; the GitHub connector
confirmed the merge instead. Bilingual docs passed gpt-6-luna / low review with no findings.
Remote CI results will be recorded in the PR.
No native integration, continuous geometry, or parking validation performed.

## Line counts and next step

Code: +255/-0 lines, including implementation and tests. Documentation changes
are disclosed separately in the PR; configuration is unchanged.
Wait for user review and merge. Then continue stage 4 carrying ownership,
projected remaining actions, target/resource resolution, and shared timing integration.
