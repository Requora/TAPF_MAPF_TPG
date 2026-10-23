# Module boundary composition tests

[中文](../../zh/development/0012-module-composition.md) | [English](../../en/development/0012-module-composition.md)

<!-- doc-sync: module-composition / 2026-10-23-r2 -->

## Scope and decision

[PR #12](https://github.com/Requora/TAPF_MAPF_TPG/pull/12), based on merged PR #11 at `5e35ee0`, adds tests only to the planning implementation. Production source, contracts and module dependencies are unchanged. The test driver selects a contiguous slice from one module input to the same or a downstream module output. Existing DecisionPipeline remains the replacement boundary for future joint implementations.

Intermediate inputs are independently constructed TaskDelta, RobotJobs and FleetPlan values. The compiler entry uses its existing two arguments, AssignmentRequest and TaskDelta; there is no new DTO. Expected service times are explicit known-case values, not calls to the timing function under test. Tests call real SingleShelfAllocator, CurrentTaskCompiler, NativeMawpfPlanner and NativeWinkTpgPlanner. Each slice runs only its selected stages. The driver connects public contracts and preserves trace files; it does not implement production deadline scheduling or Runtime commits.

## Coverage and results

Each cell means input of the row module through output of the column module. PASS means both parameter cases passed with real implementations. Dashes indicate reverse paths that are not connected by the existing contracts, not skipped supported cases.

| Input / output | Allocation | Compilation | MAPF | TPG |
| --- | --- | --- | --- | --- |
| Allocation | PASS | PASS | PASS | PASS |
| Compilation | - | PASS | PASS | PASS |
| MAPF | - | - | PASS | PASS |
| TPG | - | - | - | PASS |

Cases: quantity/station/return = 1/3/5 and 3/4/8. The 20 successful slices check task quantities and robot queues, action targets/resources/durations, exact adjacent-edge routes, motion action locations, full stationary holds, tick alignment and stop-tail splice. Inputs remain unchanged. Each included native stage produces three successful process records.

Failure cases cover insufficient stock at allocation (NO_PLAN), missing queues at compilation (BAD_INPUT), missing jobs at MAPF (UNSUPPORTED), stale request identity at TPG (STALE_REQUEST), and noncontiguous routes at TPG (BAD_INPUT). Each returns after one stage without native evidence. This is behavioral rejection, not an exception swallowed by the driver.

## Verification and replay

The initial focused test failed because composition.replay did not exist; adding the test driver made all four focused tests pass with native binaries. Commands:

```bash
WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src:tests python -m composition.replay /tmp/tapf-chain-bridges --output /tmp/warehouse-composition.json
PYTHONPATH=src:tests python -m composition.replay /tmp/tapf-chain-bridges --first compilation --last mapf --output /tmp/warehouse-composition-selected.json
/tmp/warehouse-ci-check/bin/ruff check src tests
```

Full suite: 91 tests, 90 pass, one standalone CBS-TA comparison skips. Without native binaries: 86 pass, five skip. The full replay contains ten actual traces, raw native files, binary hashes and two failure replays; the selected replay contains only compilation -> MAPF in its success matrix. CI now uploads composition.json with native-chain evidence. Ruff and diff checks pass.

This run reused `/tmp/tapf-chain-bridges/warehouse_mawpf` and `warehouse_winktpg`. Local rebuild failed because cmake was unavailable. Existing build-cache source paths resolve to clean pinned checkouts: [MAWPF](https://github.com/HirokiNagai-39/mawpf/tree/0cdb8e43797aff3781e4cd3ddb2c6d7d36f3df17) and [WinkTPG](https://github.com/JingtianYan/WinkTPG-IEEE-TASE/tree/dd96946f225e206de35b041320786eab43210658). Binary hashes are in the replay; this does not claim a fresh reproducible local build. Upstream build/license details remain in [native integration evidence](0009-staged-pipeline.md).

Source and a clean installed wheel each pass 90 tests with one skip; clean build directory `/tmp/warehouse-composition-wheel-oaa55ar7`, pip check passes. Independent gpt-6-luna/low bilingual review passes. Dashboard checks pass for both languages, both diagrams, 30 module selections, keyboard and mobile, with no JS errors; desktop and mobile screenshots were inspected.

## Limits and next step

The matrix covers the currently connected four-stage lane subset, not arbitrary permutations, all possible inputs or every planned module. No mocks supply solver outputs. Continuous collision/indefinite parking safety, multi-robot warehouse planning, joint warehouse integration, Runtime and execution remain unverified or unimplemented. Wait for PR review and merge before extending the matrix to additional real modules or supported cases.
## Automated review covers code-related changes only

At the user's request, IGNORE.REGEX excludes the entire docs/ and web/ directories, the warehouse_api_v0_7/ reference package, and Markdown, RST, AsciiDoc, HTML, CSS, SVG, images and PDF at any depth before diff generation. Website JS and check scripts are therefore excluded too. Application source, tests, integration adapters, build and CI configuration remain, including CMakeLists.txt. Review instructions explicitly exclude website, documentation, styling, translation, publication records and progress statistics. Manual documentation checks remain; repository instruction injection is disabled as described below.

The pinned PR-Agent v0.48.0 real settings loader and filter_ignored failed the offline behavior check before the edit and passed afterward. Command: `PYTHONPATH=/tmp/warehouse-pr-agent-research /tmp/warehouse-llm-probe/bin/python /tmp/warehouse-review-scope-check.py`. The check covers excluded and retained files; the default vendor exclusion still works. YAML parsing and diff checks pass. This follow-up changes configuration and paired logs only, without changing planning code, model budgets or dashboard content. Pushing triggers a new review; offline verification does not establish remote success.

Private dashboard publication succeeded with owner-only access retained; hosted sign-in was not tested. [Site](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site), source `488596b7548860f7f6408adef82d9cb7be1f4ce0`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_6f9d95eaba7c8191b58b26321ed36d93`.

## Automated review omits development-process instructions

At the user's request, CONFIG.REPO_CONTEXT_FILES=[] disables injection of AGENTS.md and other repository instruction files. REQUIRE_CAN_BE_SPLIT_REVIEW is explicitly disabled, and the prompt excludes PR line limits and development-process rules even if mentioned in the PR description. AGENTS.md itself is unchanged; the development-stage 500-line convention remains. Model budgets and file filtering are unchanged; no dashboard republication is needed.

The pinned v0.48.0 real settings loader and build_repo_context were checked: before the edit, the effective list was ['AGENTS.md'] and the assertion failed; afterward, the list and context were empty and the provider received no calls. Initial import lacked html2text; the probe substitutes only the GitProvider type import to isolate unrelated dependencies, not the upstream context function. Command: `PYTHONPATH=/tmp/warehouse-pr-agent-research /tmp/warehouse-llm-probe/bin/python /tmp/warehouse-review-context-check.py`. Existing file-filter checks, YAML parsing and diff checks pass; remote execution remains to be confirmed after push.
