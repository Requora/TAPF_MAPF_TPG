# Real goal assignment and CBS-TA comparison

[中文](../../zh/development/0010-native-tapf-comparison.md) | [English](../../en/development/0010-native-tapf-comparison.md)

<!-- doc-sync: native-tapf-comparison / 2026-10-21-r2 -->

## Scope and sources

PR #9 was confirmed merged by the user; the remote baseline is `04d4cda44f3ad9a78bed2f53946c5524702239c6`.
This increment uses branch `feat/native-tapf-comparison`, with implementation evidence at `b2a3f77`. [PR #10](https://github.com/Requora/TAPF_MAPF_TPG/pull/10) is submitted and awaits review.
Status: real upstream goal-assignment experiment verified, not a completed joint warehouse pipeline.
Warehouse planning APIs, DTOs, dependency graph and single-lane support remain unchanged. The process utility adds an optional cwd argument to isolate native side files. The 500-line limit applies.

Upstream [libMultiRobotPlanning](https://github.com/whoenig/libMultiRobotPlanning/tree/4c75fa20c435c440d8b6bd6dc81668ddc7296ba0)
is pinned at `4c75fa20c435c440d8b6bd6dc81668ddc7296ba0`, under the MIT license.
`integrations/tapf/CMakeLists.txt` directly builds the unmodified assignment, cbs and cbs_ta examples.
The build checks the commit and tracked-file differences; upstream code and binaries are not copied into this repository.
C++14, Boost program_options and yaml-cpp are build dependencies. PyYAML 6.0.3 reads research output only and is not a package runtime dependency.

## Decisions and real trace

The case uses two point robots; each unit-grid move or wait costs one tick. The main corridor runs from `(0,0)` to `(4,0)`,
with only `(2,1)` available as a passing bay. Starts are `(0,0)` and `(1,0)`; both robots may select `(3,0)` or `(4,0)`.
The independent-distance matrix is `[[3,4],[2,3]]`; both complete matchings cost 6.

| Plan | agent0 goal | agent1 goal | Native total path cost |
| --- | --- | --- | --- |
| Fixed assignment 0 + CBS | (3,0) | (4,0) | 6 |
| Fixed assignment 1 + CBS | (4,0) | (3,0) | 8 |
| Joint CBS-TA search | (3,0) | (4,0) | 6 |

The local native assignment program selected fixed assignment 1. Tie order may vary with implementation/environment; tests do not require a particular tie choice.
CBS runs both assignments, and CBS-TA is compared with their minimum cost. This verifies the optimum for this case, not a general performance advantage.
The actual fixed-assignment-1 trace below can be inspected step by step in the HTML:

| tick | agent0 | agent1 |
| --- | --- | --- |
| 0 | (0,0) | (1,0) |
| 1 | (1,0) | (2,0) |
| 2 | (2,0) | (2,1) |
| 3 | (3,0) | (2,0) |
| 4 | (4,0) | (3,0) |

The research validation module independently checks starts, goal eligibility, adjacent moves/waits, obstacles, contiguous time,
vertex conflicts, opposing edge swaps, retained goal occupancy and reported costs. Endpoints remain stationary beyond the latest arrival, so the discrete terminal state needs no infinite checking loop.
This does not validate robot shapes, continuous collisions between samples or physical stopping.
The experiment calls only the public `native_process.run_native` and adds only the process utility's optional cwd argument, with no new warehouse planning API or incompatible DTO.

## Validation and replay

Install CMake, a C++ compiler, Boost program_options, yaml-cpp and PyYAML 6.0.3 first.
Local versions are GCC 13.3.0, Boost 1.85.0 and yaml-cpp 0.8.0.
Local CMake is in `/home/yimin/miniconda3/envs/lacam-tapf/bin`; local configuration also uses
`-DCMAKE_PREFIX_PATH=/home/yimin/miniconda3/envs/lacam-tapf`.

```bash
git clone https://github.com/whoenig/libMultiRobotPlanning.git /tmp/warehouse-tapf-upstream
git -C /tmp/warehouse-tapf-upstream checkout 4c75fa20c435c440d8b6bd6dc81668ddc7296ba0
cmake -S integrations/tapf -B /tmp/warehouse-tapf-pinned \
  -DLMRP_SOURCE_DIR=/tmp/warehouse-tapf-upstream -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/warehouse-tapf-pinned -j 2
WAREHOUSE_TAPF_BIN=/tmp/warehouse-tapf-pinned PYTHONPATH=src:tests \
  python -m unittest tapf.test_comparison -v
PYTHONPATH=src:tests python -m tapf.replay /tmp/warehouse-tapf-pinned \
  --output /tmp/warehouse-tapf-evidence-new
```

Each replay requires a new or empty output directory. It holds inputs, YAML/stdout/stderr/run.json for four calls and side files in per-call subdirectories,
comparison.json and an offline replay.html. The summary retains the upstream commit, license, binary SHA256,
a 10 s budget per call and `seed: null` (no random generation). Errors retain their traceback.
Local results: 6/8/6, four exit codes of 0 and 86 passing source tests.
Without native binaries, 86 tests run in total: 82 pass and four explicitly skip; ordinary tests do not need PyYAML.
CI adds an independent native experiment job, required by the CI gate, and uploads the complete evidence directory.
Desktop/mobile replay checks pass: real passing-bay positions at tick 2, three panels, step buttons, keyboard and no overflow. The progress website check.py passes; desktop/mobile screenshots of both pages were inspected. A wheel built from clean source passes 86 tests in Python 3.14 isolated mode; pip check passes. Ruff, JavaScript syntax and diff checks pass. [Remote CI 39379639913](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39379639913) passes all jobs at `1d2ffe8`. Downloaded [experiment artifact 12244991832](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39379639913/artifacts/12244991832) confirms four successful calls, fixed costs 6/8, standalone choice 8 and joint cost 6. Artifact SHA256: `75cda758e375efeb8ce012ed76dce1ceb67d05ee43ea5363ced02d5995479225`.

## Failure record and limits

TDD Red: the new tests first failed because `tapf.replay` did not exist. After implementation, the real native test and four discrete checks passed.
An additional regression first showed that a nonempty directory continued to invoke a nonexistent binary, raising FileNotFoundError;
the fix raises FileExistsError before any call and preserves prior evidence, passing the sixth test.
The first regression attempt under the default Python exposed missing PyYAML; the configured environment then reproduced the target behavior.
The first local build failed with an unnamespaced yaml-cpp linker name; using the exported `yaml-cpp::yaml-cpp` target fixed it.
A real run found CBS-TA writing searchGraph.dot in the working directory. A new regression first failed because cwd was unsupported; the process utility then gained the parameter and records its child directory. The seventh new test passes, native side files stay in the evidence directory, and the caller directory is unchanged.
CMake/Node were absent from the default PATH; existing tools were used by absolute path without changing upstream sources.

Warehouse SKU, shelf selection, Lift/Serve/Drop, locks, shared compilation, TPG, Runtime, execution and continuous safety are not connected to this experiment.
Full enumeration of two goals is only this case's reference; it adds no general solver and makes no large-scale optimality claim.
Only after user review and merge of this PR will the next increment design a restricted mapping from joint goal results into shared warehouse contracts.

## Website, line counts and delivery

The progress website records merged PR #9 and the experiment boundary; joint workflow connections remain dashed.
The warehouse native-adapter integration count remains 2; the isolated goal experiment is not counted as a third warehouse adapter.
Website source is reviewed in this PR and published from a separate Sites checkout to the same private site.
Published to the same [private website](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site), with status succeeded. Sites source commit: `254ac62db093f3759c91ec331b7843cd2982d725`; version_id: `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_dfdebc47895881918bb2701928b2379e`. The page links PR #10 and the real experiment CI artifact. Access remains owner-only; the hosted login flow was not browser-tested. This repository's remote is unchanged.

Diff at goal-experiment delivery against `04d4cda`: code 381 (+361/-20), documentation 293 (+254/-39), configuration 52 (+51/-1). HTML/JS, tests and comments count as code. No line-limit exception, reference bundle or upstream source is included. Work now waits for review without merging or starting another PR.

## Automated review verification

The five automated comments identified no new defect: compare rejects nonempty directories before any call; retaining failed-call subdirectories matches evidence isolation; mapping keys/values are restricted to agent0/agent1 and goal0/goal1; forcing the joint result to equal the standalone assignment would reject this case's correct cost-6 plan; Python -I discover passed in the real remote native job. Bilingual review used gpt-6-luna / low; its test-count wording suggestion was applied and the recheck passed.

## OpenRouter review migration, 2026-10-21

The user requested routing automatic review through OpenRouter. This follow-up changes the review workflow in the same PR #10 without starting the next planning module.
The [official OpenRouter API guide](https://openrouter.ai/docs/quickstart) and live [model catalog](https://openrouter.ai/api/v1/models) support `https://openrouter.ai/api/v1` and `deepseek/deepseek-v4.1-flash-1017`. PR-Agent uses the LiteLLM compatible route `openai/deepseek/deepseek-v4.1-flash-1017`; `openai/` is only a protocol prefix.
The key was entered through hidden input into the repository Actions Secret `OPENROUTER_API_KEY`, read by the workflow's OPENAI_KEY. No key was written to the repository or logs. The user subsequently requested `reasoning_effort=medium`. The pinned PR-Agent image, Chinese inline review, 32768 model-token limit, 16384 output budget, no model fallback and existing retry policy are retained.
Validation sequence: offline HTTP interception with LiteLLM 1.105.0 first failed because the request still targeted api.deepseek.com; after the change it confirmed `https://openrouter.ai/api/v1/chat/completions`, actual model `deepseek/deepseek-v4.1-flash-1017`, reasoning_effort medium and max_tokens 16384. The earlier real OpenRouter request with reasoning_effort=none returned OK with finish_reason=stop; the full medium-effort review awaits remote verification. YAML and diff checks pass. No permanent test that merely repeats configuration was added.
This changes only the review service route; planning APIs, native experiments and architecture evidence are unchanged. Pre-existing .gitignore edits and helloworld.md are excluded from the commit. Full remote-review results will be recorded after pushing.
