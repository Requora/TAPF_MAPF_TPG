# PR 2 - strict contract codec

[中文](../../zh/development/0002-contract-codec.md) | [English](../../en/development/0002-contract-codec.md)

<!-- doc-sync: codec / 2026-10-19-r1 -->

Date: 2026-10-19. Status: implemented and fixture-verified, pending review.
Branch: `feat/strict-contract-codec`. PR link: pending creation.
Baseline: PR #1 confirmed merged, `16f65e361b2d78876c789eaa42374a59cd5c7afb`.

## Scope and provenance

Add `to_data`, `from_data`, `dumps`, and `loads` in `warehouse_api.codec`.
Reuse the dataclasses and annotations in the unchanged `contracts.py`.
Follow the supplied English API 0.7 guide, sections 03 and 14, and `DATA_TYPES_EN.md`.
Adapt the reference `package/warehouse_api/codec.py`; its source SHA256 is
`c922f107b678f4500489e30309a90a536d602a5e26e18379ff80c6b8908798b2`.
The user-supplied bundle is preserved and is not a runtime or CI dependency.
JSON Schema export is outside this PR.

Copy two selected JSON fixtures byte-for-byte from the reference `package/examples/`:

| Fixture in `tests/fixtures/` | SHA256 |
| --- | --- |
| `task_delta.json` | `344235fe4e58ec1becc9801cb7b19978fc7038c3b9f07225f58ce33f5e5f94ff` |
| `fleet_plan.json` | `729232b1b3ae29a5c1d0f6741f573dff303f82297aba583ef1feb9691e9a9dca` |

## Decisions and observable behavior

Decoding checks nested fields, required values, exact scalar types, Literals,
unions, and homogeneous tuple arrays. Nullable fields remain required unless
the contract provides a default. Missing action discriminators use their defaults.
Integer JSON numbers may populate float fields; booleans cannot populate numbers.
Construct fresh frozen contracts and tuples without changing the input.

Reject duplicate JSON keys, non-string dictionary keys, non-finite numbers, and
numbers too large for float fields. Do not silently keep the last duplicate value
or stringify dictionary keys. Encoding converts dataclasses and JSON-compatible
values; it does not recheck field annotations.

Observed failure replay from the tests:

```text
Order.items[0].quantity = true
ValueError: $.items[0].quantity: expected int
{"x_m":0,"x_m":1,"y_m":0}
ValueError: Duplicate JSON field: x_m
```

Shape checks intentionally accept an integer quantity of -1 and two null shelf
location fields. Business and safety validators must reject such semantic errors.
Fixture verification does not establish continuous geometry or stopping safety.
No native solver, simulator, IPC, or Runtime implementation is added.

## Verification and failures

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m venv /tmp/warehouse-codec-check
/tmp/warehouse-codec-check/bin/python -m pip install "$PWD"
/tmp/warehouse-codec-check/bin/python -I -m unittest discover -s tests -v
git diff --check
```

Observed on Python 3.14.7: all 12 tests passed from source and from a fresh venv.
The actual isolated run used `/tmp/warehouse-codec-e0vywp9w`, ran from `/tmp`,
and selected this repository's tests by absolute path. The codec import resolved
inside that venv's `site-packages`, without importing the reference package.
Whitespace checks passed. No test failures occurred.

An additional local check decoded and round-tripped nine reference payloads:
backend_init, planning_request, task_delta, path_request, fleet_plan, motion_request,
proposal, ideal_control_frame, and observation. Only the two selected fixtures
are committed; the other seven checks are local evidence, not CI coverage.
Backend configuration payloads and JSON Schema validation were not tested.

CI runs the 12 tests against the installed package on Python 3.10 and 3.14.
Remote results are reported on the PR; local execution only covered Python 3.14.7.
The initial `gpt-6.1-sol` / `low` review passed document checks. Per the latest
user instruction, AGENTS.md now requires `gpt-6-luna` / `low` for document review.
The revised documents await a check with that configuration.
All 149 files in the reference SHA256 manifest still match.
The initial `gh` probe failed because the CLI is absent; the GitHub connector
confirmed the merged baseline. A guessed reference test filename did not exist;
file discovery found `test_contracts.py`. Neither issue changed the source bundle.

## Size and next step

Against main: 236 added Python lines and 76 added fixture lines, 312 total, no
deletions. Count fixtures in the code budget conservatively. CI adds 2 configuration
lines. Git counts the final unterminated line in each JSON fixture; `wc -l`
under-counted the initial total by two. Documentation is counted separately in the PR description.
Wait for user review and merge. Only then begin stage 3, seeded order sources.
