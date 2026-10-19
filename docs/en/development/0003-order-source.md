# PR 3 - Replayable order source

[中文](../../zh/development/0003-order-source.md) | [English](../../en/development/0003-order-source.md)

<!-- doc-sync: order-source / 2026-10-19-r3 -->

Date: 2026-10-19. Status: implemented, local unit tests passed, pending review.
Branch: `feat/replayable-order-source`. [PR #3](https://github.com/Requora/TAPF_MAPF_TPG/pull/3).
Baseline: GitHub confirmed PR #2 merged at `8412ad1a7733e6e19b9642fa9ef4dc287e54aca7`.

## Scope and sources

Add `warehouse_api.orders.ReplayOrderSource` and `generate_orders`.
Reuse `contracts.Order`, `Item`, and the `OrderSource` Protocol without contract changes.
Follow section 05A of the local API 0.7 English guide and Order/Item in `DATA_TYPES_EN.md`.
This is original repository Python code using only the standard library, with no upstream algorithm integration.

| Reference file | SHA256 |
| --- | --- |
| `warehouse_api_v0_7_visual_EN.md` | `f13bb9275af485e8dcc2ae47e76db411bf8b38581175dd71a14b50f5b8713e7f` |
| `DATA_TYPES_EN.md` | `5c3ffe789c8f43061961fd89bb7c217781ecda259ddb8c26c8c5d06c7d601b05` |

## Decisions and observable behavior

`reset(orders)` validates all inputs, merges repeated SKUs within each order, sorts
items by SKU, then sorts orders by `(released_at_s, id)` and clears the cursor.
Inputs remain unchanged. `release(until_s)` includes the time boundary and returns
each order once. Repeating a time returns an empty tuple. Backward time or a failed
reset leaves the existing release cursor and time unchanged.

This implementation rejects duplicate order IDs, blank IDs/SKUs, empty demand,
quantities that are not positive integers, and invalid times. Times must be finite
and nonnegative; booleans are not numbers. Soft deadlines may precede release;
`None` disables the due-time objective. Reset accepts an empty order collection.
Errors propagate directly without exception handling.

Generator parameters are explicit: `seed`, `count`, `skus`, `release_interval_s=1.0`,
`max_quantity=5`, and `due_after_s=None`. Releases start at zero with a fixed interval;
IDs are `order-0`, `order-1`, etc. Sort the SKU catalog, draw a uniform SKU count from
1 to the catalog size, sample SKUs without replacement, then draw each quantity
uniformly from 1 to max_quantity. Duplicate catalog SKUs are rejected.
A zero interval allows simultaneous releases; tied releases use lexicographic ID order.
Each call uses a private RNG without changing global random state. Identical parameters
and Python versions reproduce results. Persist generated Order JSON for use across
Python versions; random sequences are not guaranteed to match across versions.
IDs repeat across generated batches; batch merging and inventory feasibility are outside this PR.

Actual execution trace, with input B@2, A@2, Z@0. B contains Y:1, X:2, X:3:

| Call | Returned orders and key demand |
| --- | --- |
| `release(0.0)` | Z, Y:2 |
| `release(0.0)` | Empty |
| `release(1.999)` | Empty |
| `release(2.0)` | A, X:1; B, X:5 + Y:1 |
| `release(2.0)` | Empty |
| `reset(orders); release(2.0)` | Z, A, B |

Running `generate_orders(seed=17, count=3, skus=("X", "Y"), release_interval_s=2.0)`
on Python 3.14.7 returns times 0, 2, 4 and demand X:3 + Y:2, X:2 + Y:4, X:4 + Y:2,
respectively. All deadlines are None. These are actual order-module results, not solver traces.

## Verification and failure record

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m venv /tmp/warehouse-orders-check
/tmp/warehouse-orders-check/bin/python -m pip install "$PWD"
(cd /tmp && /tmp/warehouse-orders-check/bin/python -I -m unittest discover -s /home/yimin/research/TAPF_MAPF_TPG/tests -v)
git diff --check
```

All 23 tests passed from source and an independently installed package on Python 3.14.7,
including 9 new order tests. Coverage includes ordered release, SKU merging, reset replay,
no repeated release, backward time, unchanged state on failure, seed reproducibility,
global RNG isolation, rejected parameters, and generated time overflow checks.
No unexpected test failures occurred. All 149 reference file SHA256 hashes still match.
Whitespace checks passed. CI continues to run all tests on Python 3.10 and 3.14;
see the PR for remote status. Documentation review by `gpt-6-luna` / `low` passed,
with no issues in bilingual parity, English punctuation, links, or technical facts.

Failure replay, expected exit code 1, with the original traceback preserved:

```bash
PYTHONPATH=src python -c 'from warehouse_api.orders import ReplayOrderSource; s = ReplayOrderSource(); s.release(2.0); s.release(1.0)'
```

```text
ValueError: until_s: time moved backward from 2.0 to 1.0
```

The initial `gh` probe failed because the CLI is absent; the GitHub connector then confirmed merge status.
Runtime, allocators, and native solvers remain unimplemented. Continuous geometry and safe stopping are unverified.

## Review correction: centralize input validation

As requested, move order input checks and error messages into the internal `_order_validation.py` module.
`reset`, `release`, and `generate_orders` call `validate_orders`, `validate_release_time`,
and `validate_generation_parameters`, respectively. The main flows contain no raise branches.
Validation rules, exception types, and messages are unchanged. Reset validates before merging SKUs and replacing state.
All existing 23 tests passed again from source and the reinstalled isolated package; no tests were added.
The isolated installation uses `pip install --force-reinstall "$PWD"`; other verification commands are unchanged.
See the PR for this revision's CI status. Documentation passed another review with `gpt-6-luna` / `low`.

## Review correction: clean up the existing codec

As requested, apply the same cleanup to the earlier `codec.py`. Input shape checks,
scalar decoding checks, and JSON duplicate-key/non-finite constant handling now live
in the internal `_codec_validation.py` module. `to_data`, `from_data`, and `loads`
call these functions, with no raise branches in the main flows.
Union selection and recursive conversion remain in the codec; no exception handling was added.
Public interfaces, exception types, error paths, and messages are unchanged;
oversized integers still raise the original OverflowError directly.
All `src/warehouse_api/` files were checked; explicit raises now occur only in the two validation modules.
`contracts.py` and `__init__.py` contain no such error branches and need no changes.
All existing 23 tests passed again from source and the reinstalled isolated package; no tests were added.
See the PR for this revision's CI status. Bilingual documentation passed `gpt-6-luna` / `low` review.

## Line counts and next step

Against main: Python +383/-54, or 437 changed lines, below the 500-line limit.
Order implementation and tests +287, codec validation module +83, codec main flow +13/-54.
Configuration +1/-1 only renames the CI step. Documentation counts are disclosed separately in the PR body.
Wait for user review and merge before starting the stage 4 shared task compiler.
