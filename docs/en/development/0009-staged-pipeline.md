# Real order-to-TPG planning chain

[中文](../../zh/development/0009-staged-pipeline.md) | [English](../../en/development/0009-staged-pipeline.md)

<!-- doc-sync: staged-pipeline / 2026-10-20-r9 -->

## Scope and status

The native planning chain now runs locally: order release -> feasible allocation -> shared compilation -> upstream MAWPF -> upstream WinkTPG -> candidate MotionPlan. No solver test doubles are used in `tests/native/replay.py`.

Supported scope is one robot, one grounded shelf, one demand/stock row, and an eastbound unit-spaced lane. The robot starts at node 0, reaches pickup, station, and a later empty return slot. All headings are zero, all starts are at rest, and obstacles are absent. Unsupported constraints return `UNSUPPORTED`; insufficient stock returns `NO_PLAN`. This is a narrow real integration, not a general warehouse solver or an execution loop.

[PR #9](https://github.com/Requora/TAPF_MAPF_TPG/pull/9) was submitted prematurely with fixture wiring only. After the user's correction, it was converted to draft. The user authorized continuing this same PR after the 500-line exception request. The native implementation is now included in this correction; no limit exception is implied for later PRs. No additional PR or merge was made.

Validation source snapshot: `a1d0d03b9e1fb7ee711c8ca8b783fa9b1d0885dd`. The historical SHA256 of that CI snapshot, not the later review working tree, is `1f8a35d1c83eedd502342d7f4d7aba3f82335b846752cea5fdf584e9267c170a`, computed over sorted `.py`, `.cpp`, `.html`, and `.txt` files under src, tests, integrations, excluding __pycache__, with each relative path and a null byte before its bytes. The source hash identifies the tested native implementation independently of later documentation commits.

## Implementation and decisions

```mermaid
flowchart LR
    O[ReplayOrderSource] -->|Order -> Demand: replay harness| A[SingleShelfAllocator]
    A -->|TaskDelta| C[CurrentTaskCompiler]
    C -->|RobotJobs / PathRequest| M[NativeMawpfPlanner / LaCAM]
    M -->|FleetPlan / MotionRequest| T[NativeWinkTpgPlanner / speedSolver]
    T -->|Exact knots + action holds| P[Candidate MotionPlan]
```

All public planning messages still use contracts.py. StagedPipeline injects each independent stage, shares one deadline, checks path/action identity, and retains the actual stage inputs/results in `last_trace`. Only Runtime may accept a candidate; Runtime is not implemented.

SingleShelfAllocator selects the only supported feasible robot/shelf, checks available SKU quantity, and creates picks from the released demand. Task IDs derive from the request ID. It does not reserve stock or optimize matching. Existing tasks, locked queues, and general allocation are unsupported by this allocator.

MAWPF is called for each action target. Its actual states become adjacent Move steps plus compiled Do references. WinkTPG consumes those chosen moves and returns its actual speed primitives for each leg. Each leg ends at rest so the compiled action can run. The adapter retains acceleration switches, including the midpoint of a zero-to-zero triangular primitive, as Hermite knots. It adds stationary time to reach a simulation tick before starting each action. Compiled duration and StepRef are preserved. The already stopped single robot receives an explicit hold tail.

`validation` currently owns supported-subset input/business checks, not the continuous Validator implementation. MAPF and TPG own local native-output validation. `native_process` retains commands, request IDs, budgets, elapsed time, exit codes, stdout, stderr, and raw outputs. TimeoutExpired is the only caught process exception, mapped to TIMEOUT after the child is killed by subprocess.run; unexpected errors keep their traceback. Old output files cannot satisfy a new call.

## Verification and replay

First clone the upstream URLs below and check out their exact commits. CMake verifies commits and rejects tracked source changes. In this environment CMake is in `/home/yimin/miniconda3/envs/lacam-tapf/bin`; Boost 1.85.0 and GCC 13.3.0 were used. Upstream sources remain outside this repository.

```bash
cmake -S integrations/native -B /tmp/tapf-chain-bridges \
  -DMAWPF_SOURCE_DIR=/tmp/tapf-chain-mawpf \
  -DWINKTPG_SOURCE_DIR=/tmp/tapf-chain-winktpg \
  -DCMAKE_PREFIX_PATH=/home/yimin/miniconda3/envs/lacam-tapf
cmake --build /tmp/tapf-chain-bridges -j 4
WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src:tests python -m native.replay /tmp/tapf-chain-bridges \
  --output /tmp/tapf-real-chain.json --html /tmp/tapf-real-chain.html
PYTHONPATH=src:tests python -m native.replay /tmp/tapf-chain-bridges \
  --quantity 3 --stock 3 --station 4 --destination 8 \
  --output /tmp/tapf-real-chain-changed.json --html /tmp/tapf-real-chain-changed.html
PYTHONPATH=src:tests python -m native.replay /tmp/tapf-chain-bridges --stock 0 \
  --output /tmp/tapf-real-chain-rejected.json --html /tmp/tapf-real-chain-rejected.html
ruff check src tests web/progress/check.py
```

Observed: 79 source tests and 79 clean installed-wheel tests pass with real binaries enabled. Ruff, pip check, and diff checks pass. Without WAREHOUSE_NATIVE_BIN the three native-chain tests are explicitly skipped. Native binaries remain optional package dependencies. A separate native CI job builds the pinned upstreams and uploads the real JSON/HTML replay. [Remote CI 39366365034](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39366365034) passed the native build, all 79 tests with binaries enabled, and the replay command. [Artifact 12239575773](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39366365034/artifacts/12239575773) contains HTML/JSON; zip SHA256 `d9e55990ca524a89cb324086568380069c9d855226f35a9365a2b8de308b983b`.

| Replay | Actual result |
| --- | --- |
| One unit, pickup 1, station 3, return 5 | Six successful native process calls; Lift at 2.0 s, Serve at 5.2 s, Drop at 8.4 s; completion 8.7 s; terminal speed zero |
| Three units, station 4, return 8 | Actual native path changes; service duration 0.7 s instead of 0.3 s; starts 2.0/5.9/10.7 s; completion 11.0 s |
| Stock zero | NO_PLAN at allocation; no native calls |
| Second robot | UNSUPPORTED |
| Real sleeping subprocess | TIMEOUT recorded; no successful result consumed |
| Exit zero without output | BACKEND_ERROR; stale output was removed |

Tests analytically check Hermite speed and acceleration extrema on every interval of the default replay, exact action holds, reference order, tick alignment, end pose, zero terminal speed, and tail splice. These checks are not continuous collision or indefinite parking validation. Input snapshots remain unchanged. JSON evidence contains executable SHA256 values, actual stage outputs, and the complete raw native records.

The standalone HTML replay uses the returned Hermite knots, not sampled invented paths. It supports time scrubbing, previous/next knots, playback, action/resource inspection, native output expansion, and a rejection view. Browser QA passed six-call and action-table checks, step control, terminal speed, mobile overflow, and rejection display. Desktop/mobile screenshots were inspected. The moving shelf illustration is derived from scheduled action completion, not backend observations.

## Upstream provenance and failures

| Source | Commit | License / integration |
| --- | --- | --- |
| [MAWPF](https://github.com/HirokiNagai-39/mawpf) | `0cdb8e43797aff3781e4cd3ddb2c6d7d36f3df17` | MIT; actual LaCAM routes exported by a thin wrapper |
| [WinkTPG](https://github.com/JingtianYan/WinkTPG-IEEE-TASE) | `dd96946f225e206de35b041320786eab43210658` | No license file found; no upstream source/binaries redistributed; actual speedSolver primitives exported |

The MAWPF stock scenario loader returned `invalid N` because its U indexing omits the omega dimension. The wrapper selects the correct zero-speed/east-facing vertices by their explicit attributes and sets the borrowed graph's ownership flag, which that upstream constructor leaves uninitialized. No search algorithm was rewritten.

WinkTPG originally failed to compile because simulator.h lacks unordered_map; the build adds `-include unordered_map`. Its CLI CSV is statistics, so the wrapper calls speedSolver and exports start time, cost, and start/end speeds directly. An initial infinite planning horizon overflowed an upstream integer bound; the wrapper now uses the finite path length. The upstream simEnv is only an initial-state container: no simulator step or new simulator/backend implementation was added.

Historical fixture-only validation passed 73 tests at `4277591`. An earlier dirty-workspace wheel included obsolete flat modules; clean export `c47f4a7` passed the then-current 72 tests. The native wheel was built from a new source-only directory. These historical counts are distinct from the current 79-test native run.

Automated review was checked against source: run_native rejects nonpositive remaining budgets before subprocess.run. The claimed zero-to-zero wait is instead the upstream acceleration/deceleration primitive: [sipp_ip.cpp lines 334-338](https://github.com/JingtianYan/WinkTPG-IEEE-TASE/blob/dd96946f225e206de35b041320786eab43210658/src/sipp_ip.cpp#L334-L338) assigns duration `2*sqrt(1/a_max)` to one-cell travel; its midpoint is x+0.5, speed 1 for the supported acceleration. The adapter retains that switch for exact Hermite interpolation. Zero demand is BAD_INPUT; positive demand with insufficient stock is NO_PLAN.

## Unverified boundaries and handoff

Multi-robot conflicts/precedence, turns, obstacles, moving splices, accepted task progress, reassignment, joint TAPF, Runtime transactions, continuous geometry, infinite parking occupancy, central execution, and physical backend operation remain unverified or unimplemented. The adapter explicitly rejects unsupported inputs. Its MotionPlan is a candidate, not Accepted.

PR #9 is ready for review after successful remote native CI; it is not merged. The user approved the one-PR line-limit exception. The final handoff records code, docs, and configuration counts separately below. The private progress website is updated with native evidence at `a1d0d03` and remote CI. The standalone replay is available both locally and as the CI artifact above.

Publication: Sites succeeded with the existing owner-only access. Source checkout `/tmp/tapf-chain-site`, source commit `b2bfcbaa6b79cae15f5134d3a3966a8c5b2be6fc`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_5bb6b11a3b488191bef27287333d8e58`. [Private website](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site/?lang=en). Dashboard browser checks passed both languages, both diagrams, keyboard operation, mobile layout, and no JS errors; desktop/mobile screenshots were inspected.

Before annotation, diff against `576e25d`: code 1,193 (+1,144/-49); docs 429 (+378/-51); config 58 (+57/-1). Before annotation, production source and upstream build configuration were unchanged since the passing native CI baseline; the earlier review follow-up only changed a test clock. No upstream vendoring or reference-bundle addition. Next: user review of PR #9; no further module work before merge.

## Review follow-up, 2026-10-20

Seven inline comments were checked against the current source and pinned upstream. One new test correction: the deadline test now uses `chain(repeat(0, expired_call), repeat(10))`. After expiry, extra clock reads stay expired instead of raising StopIteration. Stage-count and TIMEOUT assertions remain. This is +2/-2 test lines relative to `d612355`, with no production behavior or native evidence change. The published architecture snapshot remains applicable.

| Comment | Decision |
| --- | --- |
| [Compiler deadline](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321133366) | No change: solve checks the deadline after compilation, before MAPF. |
| [Path/job identity](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321133367) | Already fixed in 4277591: robot coverage and ordered Do references are checked; regression cases block motion. |
| [Shared-budget clock](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321133372) | Already fixed in 4277591 with unbounded count(). |
| [Deadline-test clock](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321153328) | Fixed in this follow-up with an unbounded expired tail. |
| [Native negative budget](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321287871) | No change: run_native returns TIMEOUT before launching any process. |
| [Zero-to-zero motion](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321287874) | No change: upstream defines one-cell acceleration/deceleration; removing the midpoint breaks exact interpolation. |
| [Zero demand/stock](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321287876) | No change: zero demand is invalid input; positive demand with zero stock is infeasible. The failure codes intentionally differ. |

Validation: `PYTHONPATH=src:tests python3 -m unittest planning.test_staged -v` passed all 9 tests. Ruff and diff checks passed. Direct checks confirmed budgets 0/-1 return TIMEOUT without launching a nonexistent executable or creating files; zero stock returns NO_PLAN and zero demand returns BAD_INPUT. Native scope, continuous safety limits, PR status, and website evidence baseline remain unchanged.

The user added a rule to root AGENTS.md: every function, class, and method needs Chinese and English comments or a docstring near its definition explaining its purpose, why it is needed, and why the work is necessary; update these explanations when it changes. Class documentation does not replace documentation for each method. Root AGENTS.md remains a Chinese-only rules file.

[Review-fix CI at 990b3f1](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39372553744) passed static checks, installed-wheel tests, real native tests, and CI gate.

The user added TDD: Red -> Green -> Refactor. First confirm the test fails because the target behavior is missing, then implement the minimum change, and finally refactor while keeping tests green. Bug fixes start with a reproducing regression test. This update changes only rules and bilingual records; diff checks pass and code tests were not rerun.

## Bilingual code explanations, 2026-10-20

As requested, bilingual explanations now cover 154 production definitions and 111 test definitions, including functions, classes, and each method. Comments sit near definitions and explain responsibilities and design reasons. Both C++ native entry points and functions/callbacks in the website and replay scripts are also documented. Protocol comments identify interface contracts without presenting Runtime or backend declarations as implementations.

Suggested reading order: `StagedPipeline.solve` in `planning/_staged.py` shows stage connections; `allocation/_single_shelf.py` explains task creation; `task_compiler/_current_task.py` explains conversion into actions; `mapf/_mawpf.py` and `tpg/_winktpg.py` explain actual upstream conversions; use `contracts.py` to look up stage messages. Additional bilingual comments explain snapshots, candidates, and progress protection at key orchestration and compilation steps.

Relative to `6f054fa`, 34 code files add only 911 comment lines, with no executable statement changes. These comments count toward raw code diff size. The ASTs of all 30 Python files match the baseline exactly; every non-Python diff line was also checked to be an added comment. No artificial failing tests were added because comments introduce no new behavior.

Validation: both native bridges rebuilt successfully; the unittest command above passed all 79 tests using the rebuilt binaries. Ruff, `node --check` for both JavaScript scripts, and `git diff --check` passed. The documentation subagent checked bilingual meaning and interface/implementation boundaries. Published website content, interaction, and evidence status are unchanged, so no republication is needed. These checks do not expand the previously stated planning or safety validation scope.

After annotation, the total PR diff against `576e25d` is: code 2,104 (+2,055/-49), docs 453 (+402/-51), configuration 58 (+57/-1). This follows the user-authorized line-limit exception for PR #9 without expanding functional scope.

## Comment readability review, 2026-10-20

This follow-up addresses four new user comments: [one-robot/one-shelf subset](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321797946), [public paths](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321824388), [successive compiled targets](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321829109), and [missing subjects](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321859405). All four comments are valid. The allocator and MAPF adapter now have rewritten class, method and sorting-callback explanations that identify inputs, outputs, the actor performing each operation and design reasons.

The allocator explanation now states that it accepts only one robot, one shelf and one item-demand row, then creates pickup, workstation-service and return tasks. The MAPF explanation identifies PathRequest as a message type between modules: plan reads already compiled actions and plans successive routes to their target nodes. Move means travel along a map edge; Do refers to execution of the original task step. The misleading phrase "public paths" is removed, and the comments explain how upstream cell indices map to node IDs.

AGENTS.md now requires explicit subjects in both languages and nearby explanations of nouns, abbreviations and project terms, including their meaning and role. This follow-up applies the rule to the two reviewed files; it does not claim a repository-wide audit under the new rule.

Relative to `5a21fb8`, the raw diff in two code files is 82 lines (+58/-24), consisting only of comments and module docstrings. The Python ASTs are identical after excluding module docstrings. No behavior changed, so no artificial failing tests were added. All 79 tests passed with real native binaries enabled; Ruff and diff checks passed. Supported scope, the website evidence snapshot and the PR's review status are unchanged, so no website republication is needed.
