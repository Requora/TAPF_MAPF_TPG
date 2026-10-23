# Joint planning composition

[中文](../../zh/development/0012-joint-pipeline.md) | [English](../../en/development/0012-joint-pipeline.md)

<!-- doc-sync: joint-pipeline / 2026-10-23-r1 -->

## Scope and decision

PR #11 merged at `5e35ee0`, confirmed remotely before starting. JointPipeline replaces separate allocation and routing with an injected JointPlanner. JointPlan combines existing TaskDelta and FleetPlan in contracts.py. The public DecisionPipeline input and output remain unchanged. No native objects or new cross-module imports are introduced.

The shared compiler recompiles the final draft to preserve progress, locks and action timing. Existing planning validation checks request identity, robot coverage and action order before TPG. The solver must itself use shared compilation semantics during search; final checks cannot prove route geometry. One wall-clock deadline covers joint search, compilation and motion. Synchronous calls cannot be preempted; late results are discarded. Only Runtime may accept and commit a proposal.

## Verification and failures

The initial focused test failed because JointPlan did not exist. After implementation, six focused tests pass. `PYTHONPATH=src python -m unittest discover -s tests` runs 93 tests: 89 pass and four native tests skip. Ruff and git diff --check pass. No native planners were rerun.

`PYTHONPATH=src:tests python -m planning.joint_replay` prints actual fixture stage I/O and a proposal. The shared compiler is real; joint search and motion use explicit doubles. Expected and observed stages: joint -> compilation -> tpg; actions: lift, serve, drop. The run was saved to `/tmp/warehouse-joint-replay.json`. Invalid queues, stale routes, missing/duplicate robots and missing actions stop before motion. Tests also cover failures, exceptions, trace reset, input immutability and shared timeouts.

## PR and next step

PR link will be recorded after creation. This increment implements composition with fixture evidence, not a native joint warehouse solver. Next, after review and merge, adapt supported warehouse tasks to joint native search. Continuous geometry, indefinite parking, Runtime and execution remain unimplemented. The standalone dashboard correction was set aside at the user's request to prioritize mainline development; status content is maintained with this increment.
