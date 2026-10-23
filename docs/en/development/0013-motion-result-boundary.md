# Motion-result boundary

[中文](../../zh/development/0013-motion-result-boundary.md) | [English](../../en/development/0013-motion-result-boundary.md)

<!-- doc-sync: motion-result-boundary / 2026-10-23-r2 -->

## Scope and decisions

PR #12 merged; remote baseline is `5563fac`. This increment fixes StagedPipeline wrapping malformed results, such as a missing stop tail, directly in ExecutableProposal. Rules live in planning's `_validation.py`; orchestration only invokes the check and propagates Failure. Public APIs and module dependencies are unchanged.

Checks require common_prefix and stop_tail each to cover every join_state robot once, nonempty finite knots, strictly increasing times, exact state-to-prefix and prefix-to-tail splices, one fleet prefix end time, and zero final tail velocity. Matching uses robot IDs rather than result order. API 0.7 MotionPlan and trajectory semantics allow stationary single-knot holds; moving single-knot prefixes may represent zero-duration prefixes, but must immediately join complete stopping tails. target_end_s is a desired time, not an enforced result endpoint here.

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

## Review corrections

User comment [r4355613142](https://github.com/Requora/TAPF_MAPF_TPG/pull/13#discussion_r4355613142) asks what the solve comment means. It now names stage calls, the shared budget, fleet coverage, splices and stop endpoints. It states that candidates do not deduct stock or update progress; safety acceptance and atomic submission remain the future Runtime's responsibility.

Accepted [r4355588244](https://github.com/Requora/TAPF_MAPF_TPG/pull/13#discussion_r4355588244): after TPG returns MotionPlan, check the deadline before motion validation and again afterward. Late output or budget exhaustion during validation returns TIMEOUT first, rather than reporting malformed late output as BAD_INPUT. Existing propagation of Failure returned directly by adapters is unchanged.

Accepted [r4355588241](https://github.com/Requora/TAPF_MAPF_TPG/pull/13#discussion_r4355588241): join_state need not be stationary. A moving single-knot prefix only marks an immediate switch to the stopping tail; it does not authorize indefinite motion. Remove the extra stationary constraint while retaining tail completeness, exact splices and zero final velocity. The example starts at 1 m/s and stops after 1 s over 0.5 m; this structural test does not prove general motion safety.

TDD: three added tests cover four initially failing subcases: late malformed motion, valid/malformed results timing out during validation, and moving zero-duration prefixes. All pass after the fixes. Missing tails and moving single-knot tails remain rejected. `WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests -v`: 97 tests, 96 pass, one CBS-TA experiment skips. `/tmp/motion-review-red.log` and `/tmp/motion-review-tests.log` retain failures and complete results. Ruff and diff checks pass. The real native chain reuses existing binaries without rebuilding. The 94-test and 136-line figures above describe the initial submission, not this revision's totals.

The wheel rebuilt and installed from clean source also yields 96 pass and one skip; pip check passes. Independent gpt-6-luna/low bilingual review completed; the roadmap now limits BAD_INPUT to within-budget results, and the dashboard's current-work card is synchronized. Bilingual, keyboard and mobile browser checks passed; desktop/mobile screenshots were inspected. The final PR against `5563fac` totals 193 code lines including tests/web (+176/-17), plus 114 document lines (+98/-16), with no configuration changes.

This private publication succeeded: Sites source `b772f42bf274a049e95d62fa15bdf594ad56a5bc`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_0639b3f51864819184efd4345040b906`. The URL above remains in use with unchanged owner-only access. Hosted sign-in is untested; new-commit remote CI runs after pushing, and local tests do not substitute for remote results. Review threads receive individual replies, without automatically resolving threads or merging the PR.
