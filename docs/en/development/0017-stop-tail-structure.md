# Stop-tail structure checks

[中文](../../zh/development/0017-stop-tail-structure.md) | [English](../../en/development/0017-stop-tail-structure.md)

<!-- doc-sync: stop-tail-structure / 2026-11-15-r1 -->

## Scope and decisions

Baseline: merged PR #16, `19565310d116c2a4fbe763fe4ccd04e07b92c745`. Current branch: `feat/stop-tail-validation`. This change adds a shared structure check without contract, module-dependency or upstream-version changes.

`check_stop_tail_structure(model, start, motion)` returns shared Failure tuples. Inputs cover the full fleet with finite, strictly time-ordered knots. Prefixes exactly match join_state and end at one common time. Each tail exactly joins its prefix and ends with zero linear and angular velocity. One-knot stopped tails and different robot stopping times are valid. Inputs remain unchanged.

Rules stay in validation to avoid scattering them through future Runtime code. This helper checks structure without adding another Hermite interpolation implementation. Prefixes are required. Actions, collisions, resources, braking feasibility and indefinite terminal occupancy require separate validation. An empty result does not authorize submission or implement the full Validator Protocol.

## Verification and failure record

TDD: importing the absent API failed, confirming Red. All six new tests pass after implementation. Full suite: 113 tests, 112 pass, one optional CBS-TA skip. Rejections cover missing robots, duplicate IDs, unknown IDs, empty knots, NaN, duplicate times, initial jumps, inconsistent prefix horizons, tail jumps and nonzero terminal angular speed.

Explicit counterexample: both tails can end at the same point and pass this structure check. This test demonstrates that structural success is not collision-safety evidence. This is fixture evidence, not new real-upstream evidence.

```bash
PYTHONPATH=src:tests /tmp/trajectory-cpp-dev/bin/python -m unittest validation.test_stop_tail -v
PYTHONPATH=src WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges /tmp/trajectory-cpp-dev/bin/python -m unittest discover -s tests -q
```

## PR and next step

Current [PR #17](https://github.com/Requora/TAPF_MAPF_TPG/pull/17) awaits review. Await review after submission; do not merge automatically. Continuous geometry, braking and parking-occupancy checks remain planned. User-local .gitignore, helloworld.md and reference bundle remain unchanged.

Final checks: Ruff, git diff --check and bilingual dashboard checks pass. Desktop/mobile screenshots inspected. Independent gpt-6-luna/low bilingual review passed. Actual API calls: a complete fleet returns `()`, a missing robot returns `BAD_INPUT: stop tail must cover each model robot exactly once`.

Private progress publication through the Sites skill succeeded with owner-only access preserved. Source `8fa1529f4e006e2815275fbe973dd16e7fe0c223`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_7a665c34b5f081919b140f18ecd997ed`. The first source-helper attempt from the main repository failed; using an independent temporary checkout succeeded. The initial browser-check Python lacked Playwright; the existing browser environment passed. Port 8765 was occupied; this check used 8793. Hosted sign-in, clean wheel installation and full continuous safety remain unverified.
