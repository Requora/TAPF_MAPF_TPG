# Native process output path contract

[中文](../../zh/development/0011-native-process-output-path.md) | [English](../../en/development/0011-native-process-output-path.md)

<!-- doc-sync: native-process-output-path / 2026-10-22-r2 -->

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

[Failed review 39861571315](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39861571315)returned empty content and finish_reason=length after about 367 s, without reaching the old time limits. The logs contain no actual token usage, so exhaustion of 131072 is unproven. This increase follows the user request; it does not establish the root cause or guarantee provider acceptance or completion. CI 39861571297 passed all jobs on the same commit.

Offline real-client interception first failed because max_tokens=131072 did not meet 655360, then passed after the edit. Checks also cover input capacity, total budget and both time limits; YAML and diff checks pass. This follow-up changes only workflow configuration and bilingual logs; planning code and website content are unchanged. Earlier no-configuration-change and code-count statements describe the original path-fix delivery. Remote review runs after push; offline checks do not establish live service success.
