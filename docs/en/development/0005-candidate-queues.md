# PR 5 - Defer queue implementation and retain API 0.7

[中文](../../zh/development/0005-candidate-queues.md) | [English](../../en/development/0005-candidate-queues.md)

<!-- doc-sync: candidate-queues / 2026-10-19-r2 -->

Date: 2026-10-19. Status: scope decision documented, pending review; no new runtime behavior.
Branch: `feat/candidate-queue-edits`. [PR #5](https://github.com/Requora/TAPF_MAPF_TPG/pull/5).
Baseline: PR #4 merged at `65e0738ea6e43f94b39c507bd49291ecb873f059`.

## Scope and sources

Keep the API 0.7 contracts, package version 0.7.0, and reference fixtures unchanged.
Remove this PR's candidate queue helper and its 11 tests. Against main, the PR now
changes documentation only. It adds no replacement interface or assignment implementation.

The user's review sets the scope: each robot only needs its current task;
unused API fields stay available and can remain empty under their existing semantics.
The supplied API 0.7 guide and type definitions remain the specification.
The local reference bundle is unchanged.

## Decisions and observable behavior

Retain `RobotQueue`, `QueueState`, `locked_prefix_count`, and both `queues` fields.
Do not infer that every declared API feature must already have an implementation.
Multi-task queue scheduling and suffix editing are deferred. No API 0.8 migration.

For example, `TaskDelta(tasks=(), queues=())` still means no task edits.
It does not clear existing bindings. Empty values retain their API 0.7 meanings;
this decision does not permit discarding known state or ignoring supplied locks.
Current-task compilation and lock/carry checks remain planned. SharedCompiler,
Runtime, and atomic submission are not implemented by this PR.

## Verification and failures

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
git diff origin/main -- src tests pyproject.toml AGENTS.md
git diff --check
```

Python 3.14.7: all 33 existing tests pass. Ruff passes. The code/configuration diff
against main is empty. All 160 local reference file hashes match the snapshot taken
before this review correction. No unexpected test failures.
The attempted API changes were reverted before commit; no version or schema changes remain.
Remote CI and bilingual review results are recorded in the PR.
No new solver execution, continuous geometry, or parking validation.

## Line counts and next step

Against main: code +0/-0, configuration +0/-0. Documentation counts are disclosed
separately in the PR. Wait for review and merge before further development.
Then continue stage 4 current-task compilation within the existing API, without
implementing unused queue features in advance.
