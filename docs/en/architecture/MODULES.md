# Module directories and public APIs

[中文](../../zh/architecture/MODULES.md) | [English](../../en/architecture/MODULES.md)

<!-- doc-sync: module-boundaries / 2026-10-20-r2 -->

## Implemented directories

Each module owns its implementation and local validation directory.
`__init__.py` explicitly exports entry points; underscore files are internal.
`contracts.py` remains the sole source of DTOs and Protocols.
Tests are grouped by module; test cases and serialization fixtures retain their behavior.

```text
src/warehouse_api/
  contracts.py
  serialization/
    __init__.py
    _json.py
    _validation.py
  order_source/
    __init__.py
    _replay.py
    _validation.py
  action_timing/
    __init__.py
    _timing.py
    _validation.py
  task_compiler/
    __init__.py
    _current_task.py
    _validation.py
tests/
  serialization/fixtures/
  task_compiler/
  action_timing/
  order_source/
  test_module_boundaries.py
```

## Allowed dependencies

Arrows show import dependencies, not execution order. The serialization module converts generic
structures and does not depend on concrete contracts or business modules.

```mermaid
flowchart LR
    Compiler[task_compiler] --> Contracts[contracts.py]
    Compiler --> Codec[serialization]
    Compiler --> Durations[action_timing]
    Orders[order_source] --> Contracts
    Durations --> Contracts
```

| Module | Public API | Responsibility |
| --- | --- | --- |
| contracts.py | Existing Request/Result, DTO, Protocol types | Shared communication types, no algorithms |
| order_source | ReplayOrderSource, generate_orders | Order release and generation |
| task_compiler | CurrentTaskCompiler | Compile supported current tasks and new bindings |
| action_timing | action_duration_s, action_duration_ticks | Shared action timing |
| serialization | dumps, loads, from_data, to_data | JSON structure conversion |

Cross-module imports use package entry points or contracts. For example, the
task_compiler uses `from warehouse_api.action_timing import action_duration_s`.
Each package's `_validation.py` owns its input or business rules.
The future continuous geometry validator has a separate responsibility from
these local checks.

Composition code selects implementations; consumers use Protocols from contracts.
Public entry points use descriptive responsibility names, such as
`from warehouse_api.task_compiler import CurrentTaskCompiler`. Migrate old package imports
using the table below; no aliases retain the old names. Class and function names are unchanged.
Internal Python `__module__` paths change; historical pickle and internal module imports
are not guaranteed compatible. Public JSON contracts
are unchanged. This change adds no runtime orchestrator or complete planning pipeline.


| Previous name | New name |
| --- | --- |
| `codec` | `serialization` |
| `compiler` | `task_compiler` |
| `durations` | `action_timing` |
| `orders` | `order_source` |

## Future module boundaries

The following interfaces are defined and directories planned; no empty implementation
packages have been created.

| Planned directory | Interface in contracts | Status |
| --- | --- | --- |
| allocation/ | Allocator | Interface defined |
| mapf/ | PathPlanner | Interface defined |
| tpg/ | MotionPlanner | Interface defined |
| planning/ | DecisionPipeline | Composition entry point for staged and joint TAPF defined |
| validation/ | Validator | Continuous validation interface defined |
| runtime/ | Runtime | Transaction and atomic commit interface defined |
| execution/ | CentralExecutor | Execution interface defined |

Modules communicate through public Request/Result types; native objects remain
inside adapters. New modules get separate directories and dependency checks.
Simulator, backend, IPC, and scene assets remain out of scope.

## Verification boundary

`tests/test_module_boundaries.py` checks static imports in actual Python files.
It rejects reverse dependencies, cross-module internal imports, and cross-module
star imports; it also checks public exports. Relative imports and aliases are
covered, both in source and installed wheels. It does not intercept dynamic
imports or runtime attribute access and is not a Python sandbox.
Business fixtures verify existing behavior after refactoring, not real solvers
or execution safety.
