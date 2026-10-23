# Native process output path contract

[中文](../../zh/development/0011-native-process-output-path.md) | [English](../../en/development/0011-native-process-output-path.md)

<!-- doc-sync: native-process-output-path / 2026-10-23-r4 -->

## Scope and decision

PR #10 is merged; remote baseline is `4560d8e`. This increment addresses review r4353910675 about cwd with relative output. run_native requires absolute output when cwd is supplied; otherwise it raises ValueError before deleting files, creating logs or starting a child. Callers own command arguments; the utility does not guess or rewrite paths inside arbitrary commands. Existing adapters use absolute output paths. Module dependencies and warehouse support remain unchanged.

## Validation and failure record

TDD: the new regression first failed because ValueError was not raised, then passed after the entry guard. The test preserves a caller file and checks that rejection retains it, starts no child and creates no logs.

`PYTHONPATH=src python -m unittest discover -s tests -v`: 87 tests, 83 passed and four native tests skipped because their environment was not configured. Ruff, node --check for both JavaScript files and git diff --check passed. The existing absolute-output/cwd test with a real Python child passed. This increment did not rerun MAWPF, WinkTPG or CBS-TA; historical real integration evidence belongs to merged PR #10.

The website updates its snapshot date, merged baseline and current work. The first preview port was occupied; a system-assigned port replaced it. The Sites source helper twice returned Unable to prepare the Site; remote access was unchanged. Source was subsequently restored in an isolated checkout; the standard helper pushed and packaged successfully.

## PR and next step

[PR #11](https://github.com/Requora/TAPF_MAPF_TPG/pull/11) is submitted. This increment only fixes the path contract and waits for user review after submission. Joint warehouse adaptation, continuous validation, Runtime and execution remain unimplemented.

Website check: `web/progress/check.py http://127.0.0.1:37663` passed both languages, both diagrams, 30 module selections, keyboard and mobile checks, with no JS errors. Desktop and mobile screenshots were inspected. Independent gpt-6-luna/low documentation review was performed.

Private publication succeeded: [website](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site), source `dfe22019e35de4f95c6b758a5374f555adbda3d2`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_92830b6d6e288191834091f03d1f9050`. The result was succeeded, retaining owner-only access; hosted sign-in was not verified. The main repository remote was unchanged. Code against `4560d8e` totals 44 lines (+34/-10), including tests and website; documentation is counted separately, with no configuration changes. Existing user edits are excluded.

## Fivefold automated review budget

The user requested fivefold output and time limits. Output rises from 131072 to 655360 tokens, AI timeout from 1200 to 6000 s (100 min), and job timeout from 22 to 110 min. Total token capacity becomes 720896, retaining 65536 input tokens. High effort, model, OpenRouter and the no-retry policy remain unchanged.

[Failed review 39861571315](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39861571315) returned empty content and finish_reason=length after about 367 s, without reaching the old time limits. The logs contain no actual token usage, so exhaustion of 131072 is unproven. This increase follows the user request; it does not establish the root cause or guarantee provider acceptance or completion. CI 39861571297 passed all jobs on the same commit.

Offline real-client interception first failed because max_tokens=131072 did not meet 655360, then passed after the edit. Checks also cover input capacity, total budget and both time limits; YAML and diff checks pass. This follow-up changes only workflow configuration and bilingual logs; planning code and website content are unchanged. Earlier no-configuration-change and code-count statements describe the original path-fix delivery. Remote review runs after push; offline checks do not establish live service success.

## Review fixes and replies, 2026-10-23

User finding r4355183212 is accepted. Path configuration rules move into check_output_path in the internal native_process `_validation.py`; run_native calls it explicitly before any file side effects. Cross-module public API and dependencies are unchanged. This is a behavior-preserving refactor: the four existing process behavior tests passed before and after extraction. No tests were added merely to mirror implementation structure.

Bot finding r4355212527 was checked; the user-requested fivefold budget is retained. The [OpenRouter endpoint catalog](https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash-1017/endpoints) at inspection lists endpoints including OpenInference, Relace and Cloudflare with 1048576 context and 943718 output tokens, sufficient for the configured budget. Not every provider supports that limit; this increment does not pin a provider. [Live review 39883608837](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39883608837) succeeded and published a finding, reporting 15473 input / 18983 output tokens and 50.9 s AI time; [CI on the same commit](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39883608860) passed all jobs. This proves that request succeeded, not full 655360-token generation or success on every route. The earlier length failure still lacks usage and does not establish exhaustion of the configured cap. Both threads receive replies after push and are not automatically marked resolved.

After refactoring, `PYTHONPATH=src python -m unittest discover -s tests -v`: 83 passed, four native tests skipped. Ruff and diff checks pass. Native planners were not rerun locally. Public behavior, module connections and the website verification scope are unchanged, so the website is not republished. New remote checks run after push; old CI does not validate the new commit.

## Exclude Markdown from automated review

The user requested that automated review skip .md files. A case-insensitive suffix rule in workflow `IGNORE.REGEX` filters root and nested Markdown files before PR-Agent generates the review diff. Python, YAML, JS and the existing vendor exclusion are retained. This rule limits changed-file review scope; it does not disable required project instruction loading. Manual bilingual log checks still follow AGENTS.

Offline verification used the actual pinned v0.48.0 upstream settings loader and filter_ignored. Before the edit, it failed because README.md, nested Markdown and mixed-case extensions remained; afterward those files were excluded, Python/YAML/JS were retained, and vendor files stayed excluded. The script is `/tmp/warehouse-review-md-check.py`, run with `PYTHONPATH=/tmp/warehouse-pr-agent-research /tmp/warehouse-llm-probe/bin/python /tmp/warehouse-review-md-check.py`. Initial verification lacked loguru; after adding it to the temporary verification environment, the expected behavioral failure was observed. Project dependencies were unchanged. YAML and diff checks pass. Only configuration and bilingual logs change; business behavior and website content are unchanged. A new remote review runs after push; offline results do not substitute for remote verification.
