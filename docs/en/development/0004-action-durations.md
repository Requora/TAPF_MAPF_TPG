# PR 4 - Shared action durations

[中文](../../zh/development/0004-action-durations.md) | [English](../../en/development/0004-action-durations.md)

<!-- doc-sync: action-durations / 2026-10-19-r1 -->

Date: 2026-10-19. Status: stage 4 timing helper implemented and unit-tested; pending review.
Branch: `feat/shared-action-durations`. PR link will be added after creation.
Baseline: GitHub confirmed PR #3 merged at `b310d6ab19944eff0044a2d9ea5e6bfc1eae8a89`.

## Scope and sources

Add `warehouse_api.durations.action_duration_ticks` and `action_duration_s`.
Both take `(action, times, *, sim_dt_s)`, using the existing `TaskAction` and
`ActionTimes` contracts. No DTO or Protocol changes. This is the first small
part of stage 4, not a working SharedCompiler. Compiler and motion adapters
will use these pure helpers; neither integration exists yet.

Sources: local API 0.7 English guide, section 06, and `DATA_TYPES_EN.md`,
ActionTimes and PhysicalAction. Their SHA256 values are respectively
`f13bb9275af485e8dcc2ae47e76db411bf8b38581175dd71a14b50f5b8713e7f` and
`5c3ffe789c8f43061961fd89bb7c217781ecda259ddb8c26c8c5d06c7d601b05`.
Original repository code, standard library only; no upstream solver integration.

## Decisions and observable behavior

Lift and Drop use their fixed model times. Serve sums all pick quantities,
including repeated SKUs and different orders, then uses
`service_base_s + units * service_per_unit_s`. Round up once to whole simulation ticks.

The specification requires shared upward quantization but does not choose a
floating-point policy. This implementation interprets each numeric input via
`str(value)` as an exact decimal rational. It evaluates the service formula
with `Fraction`, then applies integer ceiling without epsilon. This avoids
an accidental extra tick for decimal boundaries such as 0.07 / 0.01.
An explicitly supplied 0.30000000000000004 remains above 0.3 and gets another tick.

The integer tick count is authoritative. Seconds convert the exact tick product
to float once and have normal float representation error. Very large tick
counts remain exact integers; seconds outside float range raise the original
OverflowError. Consumers should retain tick counts for grid comparisons.
These helpers return a complete action's duration, not a running action's
remaining time at the splice.

Timing validation is centralized in `_duration_validation.py`. Reject non-finite,
negative, boolean, and non-numeric times; require positive sim_dt_s. Validate
all four model fields even when unused by the selected action. Model times may
be zero. Require Lift/Serve/Drop with matching kind, nonempty Serve picks, and
positive integer quantities. The listed invalid inputs raise ValueError; other action
types raise TypeError. An integer time too large for the finite-number check raises
the original OverflowError. No exceptions are caught. IDs, inventory, demand,
carrying state, and task sequence validity are outside these timing checks.
Inputs are unchanged. No stock reservations or live state writes occur.

Actual helper execution, with `ActionTimes(0.21, 0.3, 0.1, 0.2)` and sim_dt_s=0.1:

| Input | Ticks | Seconds |
| --- | --- | --- |
| Lift(P17) | 3 | 0.3 |
| Serve(S2), one unit | 3 | 0.3 |
| Drop(H17) | 3 | 0.3 |
| Separate model: lift_s=0.3 | 3 | 0.3 |
| Separate model: lift_s=0.30000000000000004 | 4 | 0.4 |

This is actual timing-helper output, not a solver or physical execution trace.

## Verification and failure record

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-duration-wheel .
/tmp/warehouse-ci-check/bin/python -m pip install --force-reinstall /tmp/warehouse-duration-wheel/warehouse_planning_api-0.7.0-py3-none-any.whl
/tmp/warehouse-ci-check/bin/python -m pip check
/tmp/warehouse-ci-check/bin/python -I -m unittest discover -s tests -v
git diff --check
```

Python 3.14.7: all 33 tests passed from source and the installed wheel, including
10 new timing tests. An independent Decimal oracle covers 80 model/grid combinations.
Other cases cover adjacent floats, repeated picks, zero times, invalid inputs,
subnormal grids, large tick counts, overflow, unchanged inputs, and JSON replay.
Ruff and pip check passed. All 149 reference file hashes matched the supplied manifest.
No unexpected test failures. The initial gh probe failed because the CLI is absent;
the GitHub connector confirmed merge status instead.

Expected failure replay, exit code 1, with the original traceback retained:

```bash
PYTHONPATH=src python -c 'from warehouse_api.contracts import ActionTimes, Lift; from warehouse_api.durations import action_duration_s; action_duration_s(Lift("P17"), ActionTimes(1, 1, 0, 0), sim_dt_s=0)'
```

```text
ValueError: sim_dt_s: expected a positive time
```

Documentation passed gpt-6-luna / low review after clarifying integer-input overflow.
Remote CI status will be recorded in the PR.
No native integration, continuous geometry, or parking validation was performed.

## Line counts and next step

Code: 184 added lines, zero deletions, including validation and tests.
Documentation counts are disclosed separately in the PR; configuration is unchanged.
After user review and merge, continue stage 4 with candidate queue suffix editing,
D1 locks, carrying ownership, and remaining-action compilation in small PRs.
