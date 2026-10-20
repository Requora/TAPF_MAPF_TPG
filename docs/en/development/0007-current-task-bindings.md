# PR 7 - New-task bindings for idle robots

[中文](../../zh/development/0007-current-task-bindings.md) | [English](../../en/development/0007-current-task-bindings.md)

<!-- doc-sync: current-task-bindings / 2026-10-20-r12 -->

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

Running `tests/compiler/test_candidate_bindings.py` and the replay command below produced:

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
from compiler.test_compiler import fixture
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

The user requested DeepSeek V4.1 Flash 1017 with automatic Chinese review findings on the corresponding PR lines.
After research, reuse [PR-Agent](https://github.com/The-PR-Agent/pr-agent) instead of maintaining custom API and comment-publication code.
The alternative [Serge](https://github.com/huggingface/serge) also supports custom OpenAI-compatible endpoints and inline comments,
but its default Action uses comment commands; PR-Agent already provides PR open/push triggers and Chinese configuration, matching this task.
[PR-Agent model configuration](https://docs.pr-agent.ai/usage-guide/changing_a_model/) supports custom endpoints,
and [review configuration](https://docs.pr-agent.ai/tools/review/) provides `inline_key_issues`, avoiding custom line mapping and publication.

The upstream version is PR-Agent 0.48.0, commit `981344be2755e303df501e18e3f60b848a188a80`, under the MIT license.
Use the official prebuilt `0.48.0-github_action` image with the pinned runtime digest:
`sha256:80edef71baa3df28c129d858d4b53784abfc14704c235efb32b6c461d5399a6d`.
Resolve the digest through Docker Registry and verify upstream build provenance with `gh attestation verify oci://index.docker.io/pragent/pr-agent@sha256:80edef71baa3df28c129d858d4b53784abfc14704c235efb32b6c461d5399a6d --repo The-PR-Agent/pr-agent`, exit 0.
This repository does not vendor or rebuild upstream code; GitHub Actions pulls and runs the pinned image. No new local project dependency.

Flow: same-repository PR open or push -> PR-Agent fetches diff and project rules -> DeepSeek -> Chinese summary and inline findings.
Enable only `/review`; disable automatic describe and improve to avoid extra model tasks. Set `inline_key_issues=true` and `response_language=zh-CN`.
Call `deepseek-flash` through the OpenAI-compatible route at `https://api.deepseek.com`.
[DeepSeek documentation](https://api-docs.deepseek.com/) states that this alias currently serves DeepSeek-V4.1-Flash-1017; the alias is not immutable.
Prioritize speed and reliable output after user feedback with none, the non-thinking mode; the model remains Flash 1017. Set total context budget 32768 tokens, reserving 16384 for output and leaving up to 16384 for input including prompts. Set AI timeout to 180 seconds.
Do not retry the same model after timeout or output exhaustion, and configure no fallback model. The workflow timeout is 6 minutes; run details record actual timing and calls.
These limits bound waiting and cost, not fixed latency or full-repository coverage. Upstream manages the diff budget and reports coverage limits when input is too large.

Store the key only in Actions Secret `DEEPSEEK_API_KEY`. The workflow does not check out or execute PR repository code, approve, or merge PRs.
Skip fork PRs. Same-repository writers can still modify the workflow and are within the credential trust boundary; no isolation from malicious repository writers is claimed.
Upstream handles comment anchors, deduplication, and publication verification; findings that cannot be published inline remain in the summary. Review failures fail the Action.
The Copilot automatic-review rule has been removed from ruleset `25432822`; other branch protections remain unchanged.

Distinguish configuration checks from real execution. Checked configuration keys and trigger logic in the pinned upstream version; YAML parsing passes.
After removing the custom review script and its dedicated fake-API tests, all existing 61 source and installed-wheel tests, Ruff, and diff checks pass.
The first upstream run `39350655372` failed before the model call because 16000 was mistakenly treated as an input budget, while upstream subtracts the 16384 output reserve from it.
Correct the total budget to 32768 per upstream token_budget.py, retaining the 16384 output reserve. That failed run did not complete a model review.
The second upstream run `39350828844` rejected EXTRA_BODY.thinking before sending the request because this version permits only specific extension fields.
Remove the redundant thinking field. The [DeepSeek API](https://api-docs.deepseek.com/api/create-chat-completion/) confirms that `reasoning_effort=low` itself enables thinking; no extra switch is required.
The third upstream run `39351061754` still returned EmptyTruncatedResponseError with low effort and finish_reason=length; no review was published.
Offline HTTP interception with the same LiteLLM 1.105.0 confirms that openai/deepseek-flash routes to api.deepseek.com/chat/completions,
with actual model=deepseek-flash, reasoning_effort=low, and max_tokens=16384. The openai/ prefix selects a protocol route, not the model provider.
The native deepseek/ route converts low to thinking.enabled and discards the specific effort, so retain the compatible route.
Switched to reasoning_effort=none and verified its transmission offline; this disables thinking to reduce waiting, without claiming equal review depth to thinking mode.
Actual PR-Agent Chinese inline publication and timing remain to be measured and will be recorded in the PR; old-script success is not upstream integration evidence.

Historical diagnosis: the first custom-script run `39348625815` refused incomplete output. The second run `39348844596`
confirmed all 16384 generated tokens were reasoning, with no content. After increasing the budget to 65536,
[run 39349073708](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39349073708) successfully published a
[review](https://github.com/Requora/TAPF_MAPF_TPG/pull/7#pullrequestreview-5579478108) attached to `d24384f` in about four minutes.
That response reported model=deepseek-flash, finish_reason=stop, prompt_tokens=24273, completion_tokens=57196,
and reasoning_tokens=56754. Large input and high reasoning caused long waits, motivating upstream reuse and lower reasoning effort.
Two publication issues in the old script were fixed; subsequent runs `39349634654` and `39349679929` were cancelled because of a new commit or implementation replacement.
These records describe the old implementation, not current PR-Agent performance or verification.

## Line counts and next step

Against main: code and workflow changes total +271/-9, including tests and the entire YAML; embedded code is not exempted as configuration. Documentation is counted separately.
Wait for user review and merge. Then pursue the smallest stage 5 allocation increment with stock/demand feasibility,
while continuing to defer reassignment and multi-task queues.
