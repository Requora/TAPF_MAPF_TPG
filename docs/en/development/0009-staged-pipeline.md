# Staged planning and fixture replay

[中文](../../zh/development/0009-staged-pipeline.md) | [English](../../en/development/0009-staged-pipeline.md)

<!-- doc-sync: staged-pipeline / 2026-10-20-r1 -->

## Scope and status

The user prioritizes running the order-to-TPG chain. PR #8 is merged at `576e25d`.
This first increment provides the composition entry point within the 500-line PR limit.
The native chain is **not complete**. Allocation, MAPF, and TPG in the replay are explicit
test doubles. Order release and task compilation use existing implementations.
PR: [#9](https://github.com/Requora/TAPF_MAPF_TPG/pull/9). Verification baseline: `c47f4a7`.

```mermaid
flowchart LR
    O[ReplayOrderSource] -->|Order to Demand: fixture harness| A[Allocator fixture]
    A -->|TaskDelta| C[CurrentTaskCompiler]
    C -->|RobotJobs / PathRequest| M[MAPF fixture]
    M -->|FleetPlan / MotionRequest| T[TPG fixture]
    T -->|MotionPlan| P[Candidate proposal only]
```

## Implementation and decisions

`planning.StagedPipeline` receives four Protocol implementations through its constructor.
It calls allocation, compilation, routing, and motion preparation in order. It creates a
candidate `ExecutableProposal`; it never accepts a plan or changes a ledger.
Runtime and continuous validation remain absent. The type name does not prove execution safety.

The pipeline imports only contracts. Existing DTOs and public signatures are unchanged.
One wall-clock deadline covers all stages, including compilation. Each budgeted stage receives
the remaining time. Synchronous calls cannot be interrupted here; successful late results are
discarded. Stage failures preserve their original code, message, and related IDs. Exceptions
propagate with their traceback. A path result for a different request stops before motion.
Input and path-identity rules live in `planning/_validation.py`.

Order-to-Demand conversion belongs to the replay harness until Runtime exists. The fixture
allocator returns one predefined task. Fixture motion contains holds for compiled action durations;
it is neither a speed solver nor a safety validator. No solver algorithms were implemented here.

## Verification and replay

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src:tests python -m planning.replay > /tmp/staged-fixture-trace.json
ruff check src tests web/progress/check.py
# Build the wheel from a clean checkout, install it in a fresh environment, then:
python -I -m unittest discover -s tests -v
python -m pip check
```

Observed: 72 source tests and 72 clean installed-wheel tests pass; Ruff and pip check pass.
The new cases cover all four failure boundaries, all deadline checkpoints, decreasing budgets,
compiler rejection, stale path identity, input snapshots, result JSON round trips, and exceptions.
The replay records each stage's implementation label, inputs or compiled output, and result.
Wall-clock budget fields vary between runs; the fixture proposal is repeatable.

| Trace stage | Observed result |
| --- | --- |
| Orders | O requests one X; harness supplies one available shelf item |
| Allocation fixture | Task T bound to robot A; Lift, Serve, Drop |
| Real compiler | Three actions, each 0.3 s, with StepRef and resource IDs |
| MAPF fixture | Do, Move(out), Do, Move(return), Do |
| TPG fixture | Action starts at 0.0, 4.3, 8.6 s; prefix ends at 8.9 s; hold tail ends at 9.9 s |
| Acceptance | Not performed; no Runtime or continuous safety evidence |

An initial wheel test failed because the workspace's ignored build directory retained old
flat modules, including `_codec_validation.py`. Rebuilding from `git archive c47f4a7` into
a new directory removed the stale build inputs; all 72 installed tests then passed.
The first Ruff attempt found no module in the base Python environment. A temporary isolated
environment supplied Ruff 0.14.0 and the wheel tools. No project dependency was added.

## Upstream probes and limits

These are separate build/run probes, not adapter integration or the fixture chain.
Sources remain outside this repository in `/tmp/tapf-chain-mawpf` and `/tmp/tapf-chain-winktpg`.

| Source | Pinned commit | License / result |
| --- | --- | --- |
| [MAWPF](https://github.com/HirokiNagai-39/mawpf) | `0cdb8e43797aff3781e4cd3ddb2c6d7d36f3df17` | MIT; built; one-agent scenario probe rejected with `invalid N, check instance` |
| [WinkTPG](https://github.com/JingtianYan/WinkTPG-IEEE-TASE) | `dd96946f225e206de35b041320786eab43210658` | No license file found; no upstream code redistributed; built with the include flag below |

Build commands, after checking out the pinned sources:

```bash
cmake -S /tmp/tapf-chain-mawpf -B /tmp/tapf-chain-mawpf/build -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/tapf-chain-mawpf/build -j 4
cmake -S /tmp/tapf-chain-winktpg -B /tmp/tapf-chain-winktpg/build \
  -DCMAKE_PREFIX_PATH=/home/yimin/miniconda3/envs/lacam-tapf \
  '-DCMAKE_CXX_FLAGS=-include unordered_map'
cmake --build /tmp/tapf-chain-winktpg/build -j 4
```

Use CMake from `/home/yimin/miniconda3/envs/lacam-tapf/bin` in this environment.
The initial WinkTPG build failed because `simulator.h` lacks an `unordered_map` include.
The compiler flag fixes this local build without changing upstream source.
Boost 1.85.0 and GCC 13.3.0 were used. A separate path `(0,0)` through `(4,0)` was
run with `tpg -p path.txt -m 1 -o winktpg.csv`, delay type 0. The CSV reports
success 1 and solution cost 4.5. It is statistics output, not an API MotionPlan.
MAWPF input was a 5-by-1 open map and scenario start `(0,0)`, goal `(4,0)`, one agent,
LaCAM, seed 0, time limit 5 s, path length 2, max speed 1, rotation steps 1.
Logs are in `/tmp/tapf-chain-native-smoke/`; no successful MAWPF path was produced.
No action-aware native chain, continuous geometry, splice safety, parking, or TAPF replacement is verified.

## Website, review, and next step

The maintained website now distinguishes fixture composition from missing native stages.
Current imports show 6 nodes and 6 dependencies; the target flow retains 14 nodes and 15
dashed target connections. Six modules have implementations; native adapter integrations remain 0.
Browser QA passed both languages and diagrams, 28 module selections, keyboard input, mobile overflow, and JS errors. Desktop and mobile screenshots were inspected. Private deployment succeeded. Hosted login was not browser-tested. Source remains in this repository;
Sites uses a separate checkout and preserves the existing project and owner-only access.

Against origin/main: code +306/-23 = 329 lines, including tests and website; configuration 0.
Documentation is counted separately in the PR description. Bilingual review by gpt-6-luna / low passed
for facts, relative links, doc-sync, and English punctuation. Await user review and merge.
After merge, replace the fixture stages with feasible allocation and pinned native adapters,
keeping the same composition entry point. Do not start later PRs before merge.

[Private website](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site/?lang=en).
Sites source commit: `69456164727f18ac4085eef0c978c3320eea6228`.
Version: `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_f20650b374ec8191bf4832b034aa39e4`.
Native publication result: `succeeded`; owner-only access and the main repository remote are unchanged.
