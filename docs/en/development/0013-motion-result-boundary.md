# Motion-result boundary

[中文](../../zh/development/0013-motion-result-boundary.md) | [English](../../en/development/0013-motion-result-boundary.md)

<!-- doc-sync: motion-result-boundary / 2026-10-23-r1 -->

## Scope and decisions

PR #12 merged; remote baseline is `5563fac`. This increment fixes StagedPipeline wrapping malformed results, such as a missing stop tail, directly in ExecutableProposal. Rules live in planning's `_validation.py`; orchestration only invokes the check and propagates Failure. Public APIs and module dependencies are unchanged.

Checks require common_prefix and stop_tail each to cover every join_state robot once, nonempty finite knots, strictly increasing times, exact state-to-prefix and prefix-to-tail splices, one fleet prefix end time, and zero final tail velocity. Matching uses robot IDs rather than result order. API 0.7 MotionPlan and trajectory semantics allow stationary single-knot holds; moving single-knot prefixes are rejected. target_end_s is a desired time, not an enforced result endpoint here.

These checks cover structure only. Action timing, motion limits, continuous geometry, resource capacity and indefinite parking occupancy remain unvalidated. Runtime has not accepted the candidate. Joint warehouse adaptation and the execution loop remain planned.

## Validation and failure record

TDD: all 15 malformed-motion subcases initially returned ExecutableProposal incorrectly; all return BAD_INPUT after the fix. Tests also check that last_trace retains raw TPG results, inputs remain unchanged and valid single-knot tails remain accepted. A two-robot double checks reordered results and rejects different branch times; this is not native multi-robot integration evidence.

`WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests -v`: 94 tests, 93 pass, one CBS-TA experiment skips. Full output is in `/tmp/motion-boundary-tests.log`. The real MAWPF/WinkTPG chain and 20 successful boundary combinations pass. Existing binaries were reused, not rebuilt. Upstream versions remain MAWPF `0cdb8e4` and WinkTPG `dd96946`; provenance and builds are recorded in [native integration](0009-staged-pipeline.md).

`PYTHONPATH=src:tests python -m planning.replay` provides fixture requests, stage traces and results; `PYTHONPATH=src:tests python -m composition.replay /tmp/tapf-chain-bridges --output /tmp/motion-composition.json` retains real native output. Fixtures do not establish continuous safety. Ruff is absent from the current Python environment; subsequent check status is recorded below.

## PR and next step

[PR #13](https://github.com/Requora/TAPF_MAPF_TPG/pull/13) awaits review. Wait for review after submission; do not start another PR. The progress dashboard reflects current work and the merged baseline. Final check and publication records follow below.

The non-finite regression injects NaN/Inf into x coordinates; the same check covers other scalar fields, without per-field injection tests. Ruff passed after installation in an isolated tools environment; JS syntax, diff and bilingual/keyboard/mobile browser checks passed, and desktop/mobile screenshots were inspected. The first wheel included historical modules from stale build/ output and failed the architecture check as expected; the wheel was rebuilt from an independent clean source directory and revalidated.

Clean wheel: `/tmp/motion-wheel-env/bin/python -m unittest discover -s tests -v` with the same WAREHOUSE_NATIVE_BIN yields 93 pass, one skip; pip check passes. Independent gpt-6-luna/low bilingual review completed; the stale PR focus link was fixed and the non-finite test scope clarified. Against `5563fac`, code including tests/web totals 136 lines (+121/-15), with no configuration changes; documents are counted separately. Existing user changes are excluded.

Private publication succeeded: [progress page](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site). Sites source `1c9a53097d2a07e709faf1ab0babd4afdc1bfce2`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_4c245494a37c8191849ae1af069b3db0`. Owner-only access is unchanged; hosted sign-in is untested. Publication used an independent temporary checkout; the main repository remote is unchanged. Final-commit remote CI results remain pending.
