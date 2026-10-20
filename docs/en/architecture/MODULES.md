# Module directories and public APIs

[中文](../../zh/architecture/MODULES.md) | [English](../../en/architecture/MODULES.md)

<!-- doc-sync: module-boundaries / 2026-10-20-r7 -->

[Interactive architecture and progress website](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site/?lang=en).

The private website tracks merged PR #9 and the goal-assignment experiment at `b2a3f77`, retaining native-chain CI and remaining limits.

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
  allocation/
    __init__.py
    _single_shelf.py
  mapf/
    __init__.py
    _mawpf.py
    _validation.py
  tpg/
    __init__.py
    _winktpg.py
    _validation.py
  validation/
    __init__.py
    _single_lane.py
  native_process/
    __init__.py
    _run.py
  planning/
    __init__.py
    _staged.py
    _validation.py
  task_compiler/
    __init__.py
    _current_task.py
    _validation.py
tests/
  native/
  native_process/
  planning/
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
    Planning[planning] --> Contracts
    Compiler --> Codec[serialization]
    Compiler --> Durations[action_timing]
    Orders[order_source] --> Contracts
    Durations --> Contracts
    Allocation[allocation] --> Contracts
    Allocation --> Validation[validation: supported subset]
    MAPF[mapf] --> Contracts
    MAPF --> Validation
    MAPF --> Native[native_process]
    TPG[tpg] --> Contracts
    TPG --> Validation
    TPG --> Native
    Validation --> Contracts
    Native --> Contracts
```

| Module | Public API | Responsibility |
| --- | --- | --- |
| contracts.py | Existing Request/Result, DTO, Protocol types | Shared communication types, no algorithms |
| order_source | ReplayOrderSource, generate_orders | Order release and generation |
| task_compiler | CurrentTaskCompiler | Compile supported current tasks and new bindings |
| action_timing | action_duration_s, action_duration_ticks | Shared action timing |
| planning | StagedPipeline | Compose injected stages with a shared budget and actual stage trace; native single-lane chain verified locally |
| allocation | SingleShelfAllocator | One feasible shelf/robot; picks derived from demand |
| mapf | NativeMawpfPlanner | Pinned LaCAM output to adjacent moves and action references |
| tpg | NativeWinkTpgPlanner | Pinned speedSolver primitives to Hermite knots and action holds |
| validation | check_single_lane, check_jobs, check_assignment | Supported-subset checks; continuous Validator remains unimplemented |
| native_process | run_native | Process budgets and retained raw evidence |
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
are unchanged. StagedPipeline now composes four injected stages. The native replay uses real allocation, MAWPF, and WinkTPG on one supported unit lane. The earlier fixture replay remains a composition test. No Runtime acceptance is implemented. See [pipeline evidence](../development/0009-staged-pipeline.md).


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
| validation/ | Validator | Input subset implemented; continuous validation interface only |
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
Native tests exercise real upstreams and exact Hermite kinematic bounds. They do not establish continuous collision or indefinite parking safety. PR #9 merged at `04d4cda`.

## Joint goal-assignment experiment boundary

`tests/tapf/` and `integrations/tapf/` run pinned libMultiRobotPlanning assignment, CBS and CBS-TA. The experiment reuses `native_process.run_native` without adding production modules or module dependencies. Two point robots on the same grid have fixed-assignment total costs 6/8 and joint cost 6.

Experimental JSON is research evidence, not a new public DTO; it returns no ExecutableProposal. Joint TAPF connections in the target workflow remain planned. SKU, Lift/Serve/Drop, the shared compiler, TPG, Runtime and continuous safety are not connected to this experiment. See [development record and real replay](../development/0010-native-tapf-comparison.md).
