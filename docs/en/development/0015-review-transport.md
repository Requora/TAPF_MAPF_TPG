# Observable OpenRouter review transport

[中文](../../zh/development/0015-review-transport.md) | [English](../../en/development/0015-review-transport.md)

<!-- doc-sync: review-transport / 2026-11-15-r3 -->

## Scope and status

Independent infrastructure repair on merged baseline `cabdac3`; the C++ trajectory work remains in PR #14. Repair PR: [#15](https://github.com/Requora/TAPF_MAPF_TPG/pull/15). The adapter preserves PR-Agent diff filtering, Chinese review format, parsing and publication; only its model transport is replaced. No warehouse module or API changes.

## Failure evidence

The PR #14 run [39979489425](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39979489425) made two calls despite client retries being zero. OpenRouter account records identify Ionstream provider-stream errors (502), not successful stops. At 15:35:32 UTC the request generated 360561 reasoning tokens in 1864.211 seconds; at 16:06:37 UTC the retry generated 406176 reasoning tokens in 1864.265 seconds. Both had zero visible output and zero billed usage. Generation IDs: `gen-1792769732-WefTOj35tNYxkiMphWvu`, `gen-1792771597-A5ib1pHbt3tBV5lyzWr3`. Prompt/output logging was disabled; metadata cannot establish why the model kept reasoning.

## Implementation and decisions

`.github/review_transport.py` replaces `LiteLLMAIHandler.chat_completion` before the pinned PR-Agent runner loads. It sends raw HTTP/SSE through the image's httpx dependency and permits one model attempt per process. The upstream prompt builder, complete-diff fitting and review publisher remain in use. HTTP errors and stream errors fail immediately; missing stream completion, non-stop finish reasons and blank visible content fail instead of publishing a partial review. `REVIEW_AUDIT` logs generation/request IDs, provider, usage, error code and status when available, without prompts, reasoning text or credentials. Missing upstream metadata remains absent, not estimated.

The request excludes `ionstream`, requires parameter support and uses low reasoning, 65536 output tokens and a 600-second wall-clock deadline covering the entire request. These are trial budgets, not a demonstrated optimum. The workflow allows 15 minutes including setup/publication. Model: `deepseek/deepseek-v4.1-flash-1017`. No fallback model or retry within the process is allowed; OpenRouter retains its provider-routing behavior. Request-level settings do not change account-wide preferences.

The manual workflow input accepts an open same-repository PR, fetches its metadata and passes a synthetic opened event to the normal runner. It does not execute the target PR's source. This permits testing PR #14 with the independent repair branch before either PR merges.

## Sources

PR-Agent 0.48.0: [upstream](https://github.com/qodo-ai/pr-agent), MIT, immutable image `pragent/pr-agent@sha256:80edef71baa3df28c129d858d4b53784abfc14704c235efb32b6c461d5399a6d`. Existing image retained without vendoring or rebuilding upstream. Local inspected upstream checkout: `981344be2755e303df501e18e3f60b848a188a80`; runtime integration is separately checked in the pinned image. [OpenRouter routing](https://openrouter.ai/docs/guides/routing/provider-selection) defines provider.ignore and require_parameters. The public provider registry confirms the slug `ionstream`.

## Validation and next step

TDD: transport tests first failed because the adapter file was absent, then passed. Six transport tests cover stream 502, HTTP 502, one-attempt enforcement, actual request parameters, blank/truncated/disconnected streams and total deadline cancellation. Ruff passes. Commands: `python -m unittest discover -s .github/tests -v` and `ruff check .github/review_transport.py .github/tests`. Tests run inside the pinned image before the real review step. The initial six tests also pass in the pinned remote image. Seven tests now pass locally after adding credential-isolation coverage; the strengthened deadline test verifies cancellation while reasoning chunks keep arriving. The new isolation test first failed because the separate test job was absent, then passed. A successful transport is not proof that review findings are correct. At this stage the isolated workflow jobs awaited verification; their later result and current corrections are recorded below.

## Real review and security follow-up

Runtime commit `9de2738a19eb269f3aaf16f3c302894d7b44e95d` completed two real reviews with one attempt each. PR #15 [run 40013283451](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/40013283451) used Alibaba, 7949 prompt / 64214 completion tokens (63797 reasoning), 1039 visible characters and $0.043692825; generation `gen-1792784478-NgKgKmlZFF92wIA4jRNz`. PR #14 [manual run 40013469647](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/40013469647) used Sail Research, 11026 prompt / 48105 completion tokens (47627 reasoning), 1159 visible characters and $0.008329376; generation `gen-1792784566-hYpbZocBzVUdNVbpnqjY`. Both finished with stop, excluded Ionstream and published inline findings (one and two respectively). OpenRouter account records match the provider, usage and cost. Model calls still take about nine minutes; this is bounded functioning, not a latency guarantee. General CI [40013283290](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/40013283290) passes.

The PR #15 review identified PR-checkout code running with model credentials. Accepted: tests now run on a separate read-only runner without model secrets; the publishing runner checks out only the already exercised immutable adapter commit above. Checkout itself is pinned to `11d5960a326750d5838078e36cf38b85af677262`. Future adapter changes require separate validation and explicit runtime-pin updates; editing the PR adapter alone does not change the credential-bearing runtime. Repository maintainers still control workflow definitions; this isolation is not a defense against an authorized malicious workflow edit. The two PR #14 findings concern header rebuild dependencies and floating-point test tolerance, separate from this transport repair.

## Review corrections, 2026-11-15

The isolated workflow [40015138754](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/40015138754) and all CI checks on `1b6581d` passed. Its review reported two additional issues. The readable-flow request and both findings are accepted:

- `request_review` now owns request, deadline and reading only. `ReviewStream` owns SSE decoding, audit metadata, provider errors and final completeness validation. Explicit field checks remain inside those responsibilities; no reflective field dispatch is introduced.
- The attempt guard is process-wide. A regression using two handler instances reproduced a second request before the fix. The inspected upstream reviewer normally retains one handler; the test proves the boundary weakness, not an observed production retry through new instances.
- The secret-free test job checks out the exact runtime pin and uses `cmp` to require identical adapter bytes before tests. Both jobs pin `2428ea7834ee7b06cab632f441614346ade5c852`. Different commit IDs are allowed when adapter contents match. A stale pin fails the job before credentials are used. The workflow regression first failed because this checkout/comparison was absent.

Seven tests and Ruff pass locally after the changes. Replay: `python -m unittest discover -s .github/tests -v`; `ruff check .github/review_transport.py .github/tests`. The tests retain provider/HTTP failures, incomplete text and deadline coverage. New remote CI and a real review of this revision remain pending. The process supports one review per invocation; it deliberately rejects any second model call, including chunked review calls. The prior live successes remain evidence for the old runtime, not a claim that the refactor has already completed a live review. Next: review this correction within PR #15; do not merge automatically.

Publication: the private [progress page](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site) update succeeded. Source `a5408732f1ed284c8ec23df4cb235b7b9bc711ba`; version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_8b14f34160288191beb9eea3d6021b31`; deployment `appgdep_6afa32dbe1c4819183ee66b115eb523b`. JavaScript syntax checks pass; no interaction or layout change. Hosted login was not retested.
