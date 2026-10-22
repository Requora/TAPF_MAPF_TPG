# Real goal assignment and CBS-TA comparison

[中文](../../zh/development/0010-native-tapf-comparison.md) | [English](../../en/development/0010-native-tapf-comparison.md)

<!-- doc-sync: native-tapf-comparison / 2026-10-22-r6 -->

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
The key was entered through hidden input into the repository Actions Secret `OPENROUTER_API_KEY`, read by the workflow's OPENAI_KEY. No key was written to the repository or logs. The user subsequently requested `reasoning_effort=medium`. The pinned PR-Agent image, Chinese inline review, no model fallback and existing retry policy are retained. The final model-token limit is 81920, reserving 65536 for output including reasoning and retaining 16384 for input; AI timeout is 300 s and the migration initially set the workflow timeout to 8 min, later restored to 6 min by the review follow-up below.
Validation sequence: offline HTTP interception with LiteLLM 1.105.0 first failed because the request still targeted api.deepseek.com; after the change it confirmed `https://openrouter.ai/api/v1/chat/completions`, actual model `deepseek/deepseek-v4.1-flash-1017`, reasoning_effort medium and final max_tokens 65536. The earlier real OpenRouter request with reasoning_effort=none returned OK with finish_reason=stop; the first full medium [run 39544133063](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39544133063) returned empty text and finish_reason=length under the former 16384 output budget. Following [OpenRouter reasoning-budget guidance](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens), output capacity was increased while retaining medium effort; the new-budget [run 39544399291](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39544399291) succeeded at `a822172`, with reasoning_effort=medium confirmed in logs, four inline findings and a [Chinese summary](https://github.com/Requora/TAPF_MAPF_TPG/pull/10#issuecomment-6284755464). Model time was 60.6 s, with 16121 input tokens and 13317 output tokens. The input budget still trims some diff content; success does not imply coverage of every PR file. YAML and diff checks pass. No permanent test that merely repeats configuration was added.
This changes the review service route and reasoning effort; planning APIs, native experiments and architecture evidence are unchanged. Pre-existing .gitignore edits and helloworld.md are excluded from the commit. [CI at the same commit](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39544399105) passed all jobs. This evidence is pinned to `a822172`; the following commit only records documentation evidence.

## PR comment verification, 2026-10-22

The [human comment](https://github.com/Requora/TAPF_MAPF_TPG/pull/10#discussion_r4333078654) asks why the job timeout increased from 6 min to 8 min. This only added margin around the 300 s model request and surrounding operations; it did not fix an observed timeout. Two successful jobs took 108 s and 117 s; the [latest run](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39544812671) and [same-commit CI](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39544812778) passed. Without evidence requiring a larger job limit, this follow-up restores 6 min. OpenRouter, medium effort, the 65536 output budget and the 300 s AI timeout remain unchanged. The 6 min limit covers the entire job, including surrounding operations, so it does not guarantee a full 300 s model window.
The five automated findings still need no algorithm changes: compare rejects nonempty directories at entry; failed directories retain evidence; goal names are already restricted and both assignments are enumerated; joint search must be allowed to change the standalone assignment; isolated test discovery imports successfully. Re-running `WAREHOUSE_TAPF_BIN=/tmp/warehouse-tapf-pinned /tmp/warehouse-tapf-wheel-venv/bin/python -I -m unittest discover -s tests -p test_comparison.py -v` passed all six tests, including real upstream calls. The first command mistakenly treated the wheel installation directory as a virtual environment and did not start; using the existing virtual environment passed. YAML and diff checks pass; [CI with the restored 6 min limit](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39852122416) passed, but [review 39852122481](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39852122481) was cancelled. The GitHub annotation explicitly states that the job exceeded 6 min; the last model-request log was at 20:50:00 UTC and cancellation at 20:55:46 UTC, without a logged model response. The earlier fast successes therefore do not prove that 6 min is enough for every request, and the 300 s AI setting did not produce an observable request termination in this run. The 6 min total runtime cap is retained, with the incomplete review recorded; this does not claim a successful review validation or that 8 min would certainly succeed.
This follow-up changes one configuration line and synchronizes bilingual logs, without changing planning modules, experiment conclusions or the progress website. All six comments received individual evidence-based replies; the [timeout reply](https://github.com/Requora/TAPF_MAPF_TPG/pull/10#discussion_r4353378181) was updated with this cancelled run. Review threads were not closed and the PR was not merged.

## High reasoning configuration, 2026-10-22

The user requested high effort for review. The workflow changes `CONFIG.REASONING_EFFORT` from medium to high and updates both budget comments. OpenRouter, DeepSeek V4.1 Flash1017, the 65536 output budget, 16384 input budget, 300 s AI timeout and 6 min job limit remain unchanged.
The [OpenRouter model catalog](https://openrouter.ai/api/v1/models) retrieved for this change lists supported_efforts max/high/low/none for this model, without medium. Earlier request-level verification did not establish native model support for medium. The [latest medium review](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39853238713) logged empty content with finish_reason=length after about 322 s and reached the job limit; [same-commit CI](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39853238750) passed. The effort mismatch is not a proven cause of the empty output, and high is not guaranteed to avoid output exhaustion or timeouts.
Offline HTTP interception first required high and failed on actual medium; after the change, it confirmed reasoning_effort=high in the real client's request to OpenRouter, with the same model and max_tokens=65536. YAML and diff checks pass, with no business-code changes. Remote review and CI run after pushing; their results are recorded in the PR description, without treating offline request verification as a successful service run. Bilingual logs are synchronized; the progress website and planning architecture are unchanged.

## Review input budget and timeout correction, 2026-10-22

[High review 39855330148](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39855330148) was cancelled at the 6 min job limit. The last model-call log was at 21:13:04 UTC and cancellation at 21:18:52 UTC, without a logged model response. [Same-commit CI](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39855329923) passed. This is actual evidence that high reached the time limit, so this follow-up raises the job cap to 8 min instead of relying on the earlier assumption made without timeout evidence. AI_TIMEOUT=300 is not a verified wall-clock deadline for the entire request; the job still supplies a total runtime cap.
That run logged about 37706 input tokens, but the 81920 total budget minus the 65536 output reserve left only 16384 for input, causing diff pruning. Both CUSTOM_MODEL_MAX_TOKENS and MAX_MODEL_TOKENS now become 131072; the output reserve stays 65536, leaving 65536 for input. The model catalog publishes a 1048576 context window, above this local budget. High effort, model, route, key mapping, 300 s AI setting and no-retry policy remain unchanged. Larger input capacity can increase per-call cost and latency; the bounded budget does not guarantee every PR will fit.
Missing optional .secrets.toml files do not require creating credential files. The Actions token's /user 403 falls back to github-actions[bot] in upstream code, requiring neither broader permissions nor a personal token. This follow-up neither changes nor suppresses upstream warnings.
The budget reproduction first failed because 16384 could not fit the observed 37706 tokens plus 4096 headroom; afterward 65536 fits the same input. Real-client HTTP interception confirms unchanged high effort, OpenRouter routing and max_tokens=65536; YAML and diff checks pass. These validate budgets and request parameters, not successful service review. Actual diff coverage and model results after pushing are recorded in the PR description. No business code or website changes are included; bilingual logs are synchronized.

## Output cap and runtime estimate, 2026-10-22

[Review 39856505842 after the input-budget correction](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39856505842) confirms `Tokens: 38758` and `returning full diff`, verifying that diff pruning was removed for that commit. However, the model call from 21:21:38 to 21:27:32 returned empty content with finish_reason=length and failed review, rather than merely reaching the job timeout. The user then explicitly requested another output-cap increase and a corresponding time estimate.
The user supplied generation ID `gen-1792703584-tN4b4ljB9eB9KKym0mMO`. The [OpenRouter generation API](https://openrouter.ai/docs/api/api-reference/generations/get-request-&-usage-metadata-for-a-generation) identifies the earlier high request at 21:13:04 UTC: provider=InferenceNet, generation_time=362093 ms, native_tokens_completion=51685, native_tokens_reasoning=51685, cancelled=true, upstream status 499 and finish_reason=null. This is not the request from 39856505842. All generated tokens counted as reasoning, with no visible text; this matches client cancellation, without interpreting 499 as an independent provider failure.
Measured average throughput is `51685 / 362.093 = 142.74 tokens/s`. At that rate, the new 131072 output cap takes about `131072 / 142.74 = 918.26 s = 15.30 min`. Adding 25% margin gives about 1147.82 s, rounded up to a 1200 s AI timeout. Another 2 min for startup and publishing sets the job cap to 22 min. This estimates speed from one interrupted request; it is not a service SLA or a guarantee that the model finishes. Actual speed, first-token latency, routing and input processing time vary, and the AI timeout is not claimed as a wall-clock deadline for the entire streaming request.
The workflow sets MAX_OUTPUT_TOKENS to 131072 and both CUSTOM_MODEL_MAX_TOKENS and MAX_MODEL_TOKENS to 196608, retaining 65536 input tokens. High effort, model, OpenRouter, key mapping and no-retry policy stay unchanged. The new budget does not guarantee visible output. The key was supplied through hidden input for this read-only query and was not written to the repository or logs; raw account metadata is not committed.
Offline client verification first failed on the old max_tokens=65536, then confirmed high and max_tokens=131072 after the edit. Budget checks retain 65536 input tokens and reproduce AI=1200 s/job=22 min from the time formula. YAML and diff checks pass. Remote results after pushing are recorded in the PR description, without treating parameter checks as successful live review. This change only updates configuration and bilingual logs, not business code or the website.
