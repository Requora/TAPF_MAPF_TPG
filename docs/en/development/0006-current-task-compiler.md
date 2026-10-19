# PR 6 - Accepted current-task compiler

[中文](../../zh/development/0006-current-task-compiler.md) | [English](../../en/development/0006-current-task-compiler.md)

<!-- doc-sync: current-task-compiler / 2026-10-19-r1 -->

Date: 2026-10-19. Status: restricted stage 4 implementation, fixture-tested; pending review.
Branch: `feat/current-task-compiler`. PR link will be added after creation.
Baseline: GitHub confirmed PR #5 merged at `526589d6c86341e9ce06ad313f029da854a2dba6`.

## Scope and sources

Add `warehouse_api.compiler.CurrentTaskCompiler(model, sim_dt_s=...)`, implementing
the existing `SharedCompiler.compile_jobs(request, draft)` signature. No contract changes.
Compile only accepted current tasks. Each robot may have zero or one task in its
existing QueueState. An omitted queue is idle; an unbound, unstarted task stays unbound.
An empty TaskDelta keeps existing bindings. Any nonempty draft returns UNSUPPORTED,
including an explicitly empty proposed suffix. Multi-task queues remain unsupported.
This does not implement assignment, reassignment, or mutable suffix replacement.

Sources: local API 0.7 English guide, sections 04-06, and DATA_TYPES_EN.md.
SHA256: guide `f13bb9275af485e8dcc2ae47e76db411bf8b38581175dd71a14b50f5b8713e7f`;
types `5c3ffe789c8f43061961fd89bb7c217781ecda259ddb8c26c8c5d06c7d601b05`.
Original repository code using the standard library; no upstream solver integrated.

## Decisions and observable behavior

- Use next_step already projected to join_state. Do not advance it again.
- Support exactly one Lift, Serve, Drop sequence per unfinished bound task.
  Return every model robot in model order, including empty actions for idle robots.
- Resolve Lift only at one exact storage pose match, with zero carry_offset.
  Off-grid or ambiguous pickup poses and nonzero offsets return UNSUPPORTED.
  Serve and Drop resolve the station/storage node, heading, and resource.
- Use the shared quantized action_duration_s for every emitted action. Keep StepRef
  and shelf identity; do not forward picks or reserve inventory.
- Check StepLock references and executor bindings independently of locked_prefix_count.
  Even a lock referencing an earlier step requires the same current executor.
- Require an empty robot and grounded shelf before Lift. After Lift, require the
  same shelf carrier. Reject duplicate shelf claims and orphaned carried shelves.
- Reject unfinished actions at the splice with UNSUPPORTED. A blocked unfinished
  bound task returns NO_PLAN; no automatic retry. Completed tasks emit no actions.
- Semantic reference/state errors return BAD_INPUT. Ownership/lock conflicts return
  CONFLICT. Contract shape and timing/configuration errors propagate original exceptions;
  no try/except hides failures. Inputs remain unchanged after success or failure.

Actual compiler execution using `tests/test_compiler.py:fixture`, sim_dt_s=0.1:

| Case | Robot A actions, each 0.3 s | Robot B | Result |
| --- | --- | --- | --- |
| next_step=0, grounded shelf | 0 Lift(home-node), 1 Serve(station-node), 2 Drop(return-node) | Empty | Jobs |
| next_step=1, carrier=A | 1 Serve(station-node), 2 Drop(return-node) | Empty | Jobs |
| next_step=3 | Empty | Empty | Jobs |
| Bound to A, StepLock(T,0) requires B | No partial result | No partial result | CONFLICT |

The last diagnostic is `Committed action executor must be preserved`, related IDs
`('T', 'B')`. This is a real compiler fixture trace, not physical execution or solver output.

## Verification and failure record

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-compiler-wheel .
/tmp/warehouse-ci-check/bin/python -m pip install --force-reinstall /tmp/warehouse-compiler-wheel/warehouse_planning_api-0.7.0-py3-none-any.whl
/tmp/warehouse-ci-check/bin/python -m pip check
/tmp/warehouse-ci-check/bin/python -I -m unittest discover -s tests -v
git diff --check
```

All 48 tests passed from source and the installed wheel, including 15 compiler tests.
Ruff and pip check passed. No unexpected test failures. Initial gh status lookup failed
because gh is absent; the GitHub connector confirmed merge status. The reference package
has 160 unchanged files. Bilingual docs passed gpt-6-luna / low review.
Remote CI results will be recorded in the PR.

No allocator, MAPF/TPG/TAPF integration, Runtime commit, inventory/demand feasibility,
continuous geometry, resource scheduling, or parking validation was performed.
Returned jobs are compiler output, not accepted executable proposals.

## Line counts and next step

Code: +322/-0, including 15 tests. Documentation counts are disclosed separately in
the PR; configuration is unchanged. Wait for user review and merge. Then continue
stage 4/5 with the smallest required current-task assignment increment, preserving
the decision to defer multi-task scheduling and suffix editing.
