# PR 7 - New-task bindings for idle robots

[中文](../../zh/development/0007-current-task-bindings.md) | [English](../../en/development/0007-current-task-bindings.md)

<!-- doc-sync: current-task-bindings / 2026-10-20-r5 -->

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

Copilot trigger diagnosis (2026-10-20 UTC): ruleset `25432822` is active for the default branch,
with `review_on_push=true` and `review_draft_pull_requests=true`. Empty commit `da43cc8` was pushed
and CI passed, but PR #7 had no review, review-request, or Copilot work events.
Both the REST request for `copilot-pull-request-reviewer[bot]` and GraphQL `requestReviewsByLogin`
returned success without producing actual review events; HTTP success is not proof of a triggered review.
A read-only subscription query for the signed-in account TachikakaMin returned
`access_type_sku=free_limited_copilot` and zero premium request entitlement; Requora had zero seats.
The account query used the undocumented `copilot_internal/user` diagnostic endpoint,
which is not a project dependency. [Official documentation](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/code-review)
confirms that Copilot Free excludes code review. At that time, an eligible subscription or organization-paid access
is needed before verifying an actual trigger. No subscription was purchased or organization-paid usage enabled.

Retest after entitlement activation: the account now reports `free_educational_quota` with 200 premium entitlement.
The [official plan table](https://docs.github.com/en/copilot/get-started/plans) includes code review for students.
Empty commit `0a68b6a` was pushed and CI passed; push and renewed manual requests still produced no review events.
The earlier Free-plan diagnosis describes the earlier state and does not explain the missing trigger after activation.
Automatic review recovery remains unverified; quota or successful responses alone do not prove recovery.


## DeepSeek automatic review

The user requested switching automatic code review to DeepSeek V4.1 Flash 1017.
The [official API documentation](https://api-docs.deepseek.com/) specifies the current call name `deepseek-flash`,
served by DeepSeek-V4.1-Flash-1017. Use high reasoning effort and at most 8192 output tokens.
The model name is a provider alias, not an immutable version pinned by this repository; log the response model and usage.
Store the key only in Actions Secret `DEEPSEEK_API_KEY`, never in source or model input.
Removed the Copilot automatic-review rule from ruleset `25432822`; other branch protections remain unchanged.

Flow: PR open or push -> GitHub text patches + base AGENTS.md/contracts -> DeepSeek -> COMMENT review.
The workflow has no checkout, executes no PR code, and does not approve or merge PRs. Same-repository PRs only; skip forks.
Users with repository write access can modify the PR workflow and read the injected key and GitHub token.
These contributors are within the credential trust boundary; skipping forks does not prevent malicious repository writers from exposing credentials. Treat input content as untrusted data.
Check head/base and open state before and after the request. Never publish stale output; skip an existing bot review for the same head/base/model.
Missing keys, inputs above 160000 characters, and empty or truncated output fail explicitly. List files without patches as omissions.
Review only GitHub text patches and the two base files; do not claim full repository analysis or executed tests.
Published output includes the commit and run link, and replaces @ characters to prevent model-generated mention notifications.

Five new fake-API tests cover COMMENT commit binding, missing-key/fork rejection, stale/truncated output rejection,
duplicate-run skipping, and missing files/oversized input rejection.
All 66 source tests and Ruff pass; embedded workflow Python separately passes compilation and Ruff.
These tests do not replace a real DeepSeek call. Record actual run results in the PR.
The initial local lookup found no node, so the implementation uses standard-library Python without new runtime dependencies.

## Line counts and next step

Against main: code and workflow changes total +437/-9, including tests and the entire YAML; embedded code is not exempted as configuration. Documentation is counted separately.
Wait for user review and merge. Then pursue the smallest stage 5 allocation increment with stock/demand feasibility,
while continuing to defer reassignment and multi-task queues.
