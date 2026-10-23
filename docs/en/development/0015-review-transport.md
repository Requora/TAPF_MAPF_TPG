# Observable OpenRouter review transport

[中文](../../zh/development/0015-review-transport.md) | [English](../../en/development/0015-review-transport.md)

<!-- doc-sync: review-transport / 2026-10-23-r1 -->

## Scope and status

Independent infrastructure repair on merged baseline `cabdac3`; the C++ trajectory work remains in PR #14. PR link: pending creation. The adapter preserves PR-Agent diff filtering, Chinese review format, parsing and publication; only its model transport is replaced. No warehouse module or API changes.

## Failure evidence

The PR #14 run [39979489425](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39979489425) made two calls despite client retries being zero. OpenRouter account records identify Ionstream provider-stream errors (502), not successful stops. At 15:35:32 UTC the request generated 360561 reasoning tokens in 1864.211 seconds; at 16:06:37 UTC the retry generated 406176 reasoning tokens in 1864.265 seconds. Both had zero visible output and zero billed usage. Generation IDs: `gen-1792769732-WefTOj35tNYxkiMphWvu`, `gen-1792771597-A5ib1pHbt3tBV5lyzWr3`. Prompt/output logging was disabled; metadata cannot establish why the model kept reasoning.

## Implementation and decisions

`.github/review_transport.py` replaces `LiteLLMAIHandler.chat_completion` before the pinned PR-Agent runner loads. It sends raw HTTP/SSE through the image's httpx dependency and permits one model attempt per handler. The upstream prompt builder, complete-diff fitting and review publisher remain in use. HTTP errors and stream errors fail immediately; missing stream completion, non-stop finish reasons and blank visible content fail instead of publishing a partial review. `REVIEW_AUDIT` logs generation/request IDs, provider, usage, error code and status when available, without prompts, reasoning text or credentials. Missing upstream metadata remains absent, not estimated.

The request excludes `ionstream`, requires parameter support and uses low reasoning, 65536 output tokens and a 600-second wall-clock deadline covering the entire request. These are trial budgets, not a demonstrated optimum. The workflow allows 15 minutes including setup/publication. Model: `deepseek/deepseek-v4.1-flash-1017`. No fallback model or same-handler retry is allowed; OpenRouter retains its provider-routing behavior. Request-level settings do not change account-wide preferences.

The manual workflow input accepts an open same-repository PR, fetches its metadata and passes a synthetic opened event to the normal runner. It does not execute the target PR's source. This permits testing PR #14 with the independent repair branch before either PR merges.

## Sources

PR-Agent 0.48.0: [upstream](https://github.com/qodo-ai/pr-agent), MIT, immutable image `pragent/pr-agent@sha256:80edef71baa3df28c129d858d4b53784abfc14704c235efb32b6c461d5399a6d`. Existing image retained without vendoring or rebuilding upstream. Local inspected upstream checkout: `981344be2755e303df501e18e3f60b848a188a80`; runtime integration is separately checked in the pinned image. [OpenRouter routing](https://openrouter.ai/docs/guides/routing/provider-selection) defines provider.ignore and require_parameters. The public provider registry confirms the slug `ionstream`.

## Validation and next step

TDD: transport tests first failed because the adapter file was absent, then passed. Six transport tests cover stream 502, HTTP 502, one-attempt enforcement, actual request parameters, blank/truncated/disconnected streams and total deadline cancellation. Ruff passes. Commands: `python -m unittest discover -s .github/tests -v` and `ruff check .github/review_transport.py .github/tests`. Tests run inside the pinned image before the real review step. Remote image execution, actual provider routing and review publication remain pending. A successful transport is not proof that review findings are correct. Next: run the repaired workflow against PR #14, compare GitHub and OpenRouter evidence, then await review.
