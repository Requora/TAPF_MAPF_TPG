# Shared trajectory evaluation and exact slicing

[中文](../../zh/development/0014-shared-trajectory.md) | [English](../../en/development/0014-shared-trajectory.md)

<!-- doc-sync: shared-trajectory / 2026-10-23-r1 -->

## Scope and decisions

PR #13 is confirmed merged at `cabdac3572290707cbf3405d850031632ea62b1f`. Branch: `feat/shared-trajectory`. This PR adds `warehouse_api.trajectory.evaluate` and `slice_curve`, using the existing Knot/Pose2/Twist2 contracts. The only new production dependency is trajectory -> contracts. No solver, executor, Runtime or backend behavior changes.

API 0.7 sections 8 and 10 define cubic Hermite curves and exact slicing. The adapter already defines the curve; this utility reads it, rather than planning another curve. Source: the unchanged user reference `warehouse_api_v0_7/package/warehouse_api/trajectory.py`, SHA256 `13bb45ebb55468bd0af2c6f51f87df7ea359df1be51b0e97f4c566835d8eec62`. No external library or upstream version change. ReferenceExecutor is not ported.

Both APIs return immutable contract objects and raise ValueError for invalid curves/ranges. Package-local validation checks finite values, positive finite intervals and coverage. Position and velocity use the reference Hermite formulas, with unwrapped yaw. Slices preserve endpoints and every internal knot, including acceleration switches, up to floating-point arithmetic error.

Deliberate reference differences: no EPS snapping near knots; only exactly zero terminal velocity allows indefinite hold. A moving singleton may be queried at its exact instant, matching PR #13's immediate-braking prefix, but may not extend. Validation stays outside interpolation logic. Consumers must concatenate an immediate prefix with its valid tail before requesting a positive-duration slice across that boundary.

## Verification and failure record

TDD: the new analytic behavior tests first failed with ModuleNotFoundError because warehouse_api.trajectory did not exist (`/tmp/trajectory-red.log`). After implementation, all six pass: independent cubic position/derivative, unwrapped yaw, nested slicing/input immutability, acceleration switches/terminal hold, moving-end rejection, malformed inputs and sub-nanosecond intervals.

```bash
PYTHONPATH=src python -m unittest discover -s tests/trajectory -v
WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src:tests python -m trajectory.replay /tmp/tapf-chain-bridges --output /tmp/trajectory-native.json
/tmp/warehouse-ci-check/bin/ruff check src tests web/progress/check.py
git diff --check
```

Full suite: 103 tests, 102 pass, one optional CBS-TA test skips. The native replay executes MAWPF/WinkTPG and compares 36 original/sliced x-position and x-velocity states; maximum absolute error is 1.67e-15. Its JSON retains requests, original native outputs, binary hashes, stage trace and paired states. The x and vx error maximum combines different units for a numerical regression summary, not a physical safety metric. Logs: `/tmp/trajectory-tests.log`. Existing pinned binaries were reused, not rebuilt: MAWPF `0cdb8e4`, WinkTPG `dd96946`; see [native integration](0009-staged-pipeline.md).

## PR and next step

PR link and final installation, browser, document-review and publication evidence will be recorded before handoff. The dashboard and roadmap distinguish the implemented shared utility from the still interface-only CentralExecutor and continuous Validator. Await review after submission. No next PR is started.

Continuous collision, resource capacity, motion-limit validation, indefinite parking safety, runtime commits, action dispatch, event deduplication, joint warehouse adaptation and backend execution remain unverified or unimplemented. Curve preservation tests are not a safety proof.

Final local checks: a wheel built from clean source and installed separately passes 102 of 103 tests with one skip; pip check passes. Environment: `/tmp/trajectory-wheel-kt1j73tx/venv`; log: `/tmp/trajectory-wheel-tests.log`. Ruff, JS syntax and diff checks pass. Browser checks cover both languages, both graphs, 32 module selections, keyboard and mobile layout with no JS errors; desktop and mobile screenshots were inspected. Independent gpt-6-luna/low review verified bilingual facts and local links; its suggestion clarified roadmap stage 11 as executor integration of shared slicing. Hosted sign-in and this PR's remote CI are unverified.
