"""Enforce package dependencies and public imports in source and wheels."""
import ast
from importlib import import_module
from importlib.util import resolve_name
from pathlib import Path
import unittest

import warehouse_api


DEPENDENCIES = {
    "contracts": set(),
    "trajectory": {"contracts"},
    "serialization": set(),
    "order_source": {"contracts"},
    "action_timing": {"contracts"},
    "task_compiler": {"contracts", "serialization", "action_timing"},
    "planning": {"contracts"},
    "validation": {"contracts"},
    "allocation": {"contracts", "validation"},
    "native_process": {"contracts"},
    "mapf": {"contracts", "validation", "native_process"},
    "tpg": {"contracts", "validation", "native_process"},
}
EXPORTS = {
    "trajectory": {"evaluate", "slice_curve"},
    "serialization": {"dumps", "loads", "from_data", "to_data"},
    "order_source": {"ReplayOrderSource", "generate_orders"},
    "action_timing": {"action_duration_s", "action_duration_ticks"},
    "task_compiler": {"CurrentTaskCompiler"},
    "planning": {"StagedPipeline"},
    "validation": {"check_single_lane", "check_jobs", "check_assignment"},
    "allocation": {"SingleShelfAllocator"},
    "native_process": {"run_native"},
    "mapf": {"NativeMawpfPlanner"},
    "tpg": {"NativeWinkTpgPlanner"},
}


# 中文: violations 函数静态解析模块导入并检查模块入口允许的依赖方向, 为架构提供可执行门禁, 防止内部实现被跨模块耦合.
# English: violations inspects static imports against allowed module-entry dependencies so architectural boundaries cannot
# be bypassed by cross-module internal imports.
def violations(source: str, module: str, package: str) -> list[str]:
    """violations 检查导入别名和相对导入, 防止依赖规则被绕过.

    violations checks aliases and relative imports so dependency rules cannot be bypassed.
    """
    owner = module.split(".")[1]
    errors = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            targets = [(alias.name, None) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level:
                target = resolve_name("." * node.level + target, package)
            targets = [(target, alias.name) for alias in node.names]
        else:
            continue
        for target, symbol in targets:
            if target == "warehouse_api" and symbol is not None:
                target, symbol = f"{target}.{symbol}", None
            if not target.startswith("warehouse_api."):
                continue
            parts = target.split(".")
            dependency = parts[1]
            if dependency == owner:
                continue
            if dependency not in DEPENDENCIES[owner]:
                errors.append(f"{module}: forbidden dependency {target}")
            elif len(parts) != 2 or (symbol is not None and (
                symbol.startswith("_") or symbol == "*"
                or (dependency in EXPORTS and symbol not in EXPORTS[dependency])
            )):
                errors.append(f"{module}: non-public import {target}:{symbol}")
    return errors


# 中文: ModuleBoundaryTests 测试类验证依赖检查器和公开导出, 保持模块可独立替换, 防止重构后形成逆向或私有依赖.
# English: ModuleBoundaryTests tests dependency enforcement and public exports so refactoring preserves replaceable
# modules without reverse or private dependencies.
class ModuleBoundaryTests(unittest.TestCase):
    # 中文: 本测试遍历实际安装包源码核对所有导入, 让架构约定在源码与安装用的 wheel 包上都生效, 避免仅检查文档声明.
    # English: This test inspects imports in the actual installed package so dependency rules hold in source
    # and installable wheel packages rather than only in architecture documents.
    def test_source_uses_only_allowed_public_dependencies(self):
        root = Path(warehouse_api.__file__).parent
        errors = []
        for path in sorted(root.rglob("*.py")):
            relative = path.relative_to(root).with_suffix("")
            parts = list(relative.parts)
            is_package = parts[-1] == "__init__"
            if is_package:
                parts.pop()
            if not parts:
                continue
            self.assertIn(parts[0], DEPENDENCIES)
            module = ".".join(["warehouse_api", *parts])
            package = module if is_package else module.rpartition(".")[0]
            errors.extend(violations(path.read_text(), module, package))
        self.assertEqual(errors, [])

    # 中文: 本测试用故意违规的绝对和相对导入检验守卫, 防止检查器漏报时所有模块测试仍假通过.
    # English: This test feeds deliberately invalid absolute and relative imports to the guard so missing
    # enforcement cannot make architecture tests falsely pass.
    def test_guard_rejects_private_and_reverse_dependencies(self):
        for source in (
            "from warehouse_api.order_source import ReplayOrderSource",
            "from warehouse_api.action_timing._timing import action_duration_s",
            "from warehouse_api.action_timing import _validation",
            "import warehouse_api.serialization._json as json_codec",
            "from ..serialization._json import dumps",
            "from warehouse_api.serialization import *",
        ):
            with self.subTest(source=source):
                self.assertTrue(violations(
                    source, "warehouse_api.task_compiler._current_task", "warehouse_api.task_compiler",
                ))
        self.assertTrue(violations(
            "from warehouse_api.task_compiler import CurrentTaskCompiler",
            "warehouse_api.action_timing._timing", "warehouse_api.action_timing",
        ))

    # 中文: 本测试检查每个包供其他模块调用的 API 及其实现归属, 保证调用方可从模块入口导入, 防止实现被藏在不相关包中.
    # English: This test checks APIs exposed to other modules and their implementation ownership so callers can use module entry points
    # without depending on unrelated packages.
    def test_public_exports_use_descriptive_import_paths(self):
        for name, exports in EXPORTS.items():
            module = import_module(f"warehouse_api.{name}")
            self.assertEqual(set(module.__all__), exports)
            for symbol in exports:
                self.assertTrue(callable(vars(module)[symbol]))
                self.assertTrue(
                    vars(module)[symbol].__module__.startswith(f"warehouse_api.{name}."),
                    f"{module.__name__}.{symbol}: implementation must belong to this package",
                )
