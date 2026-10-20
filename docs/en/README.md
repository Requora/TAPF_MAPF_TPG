# TAPF / MAPF / TPG

[中文](../zh/README.md) | [English](../en/README.md)

<!-- doc-sync: readme / 2026-10-19-r11 -->

Modular warehouse planning using the Warehouse API 0.7 English specification.
Current status: shared contracts, strict JSON shape codec, tested fixtures, replayable orders, shared action timing, and a limited current-task compiler.
Current development focuses on each robot's current task; defer queue scheduling and retain unused API fields.
Planner adapters and Runtime are not implemented.

Python 3.10+, from the repository root:

```bash
python -m pip install .
python -c 'from warehouse_api.contracts import API_VERSION; print(API_VERSION)'
python -I -m unittest discover -s tests -v
```

Runtime use of this contract package needs only the Python standard library.
Installing the package uses setuptools. Import types from `warehouse_api.contracts`.
Use `warehouse_api.codec.loads(TargetType, text)` to decode and `dumps(value)` to encode.
Decoding checks types and fields; encoding converts JSON-compatible values.
These operations do not validate business rules, continuous geometry, or safe stopping.

CI runs Ruff on PR updates and main pushes, then builds and tests wheels on
Python 3.14. See `CI gate` for the aggregate result. Run static checks locally:

```bash
python -m pip install ruff==0.14.0
ruff check src tests
```

The user-supplied `warehouse_api_v0_7/` directory is a local reference bundle.
It is not required to install this package and is not included wholesale in this PR.
The contract file preserves the supplied API; field-description punctuation was
normalized during review. See the development log for source and current hashes.
Backend boundary types remain for compatibility; simulator implementation is out of scope.

- [Module boundaries and incremental plan](development/ROADMAP.md)
- [First PR: provenance and verification](development/0001-contract-foundation.md)
- [Codec: scope, fixtures, and verification](development/0002-contract-codec.md)
- [Order source: seed, release trace, and verification](development/0003-order-source.md)
- [Action timing: rounding policy, traces, and verification](development/0004-action-durations.md)
- [Review decision: defer queue implementation, retain API](development/0005-candidate-queues.md)
- [Development and review rules (Chinese only)](../../AGENTS.md)
- [Current-task compilation: action locks and carry ownership](development/0006-current-task-compiler.md)
- [New-task bindings: idle robots and candidate checks](development/0007-current-task-bindings.md)

- [Module directories, public APIs, and dependency graph](architecture/MODULES.md)
- [Module split: compatibility and verification](development/0008-module-boundaries.md)
