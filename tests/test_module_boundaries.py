"""Enforce package dependencies and public imports in source and wheels."""
import ast
from importlib import import_module
from importlib.util import resolve_name
from pathlib import Path
import unittest

import warehouse_api


DEPENDENCIES = {
    "contracts": set(),
    "serialization": set(),
    "order_source": {"contracts"},
    "action_timing": {"contracts"},
    "task_compiler": {"contracts", "serialization", "action_timing"},
    "planning": {"contracts"},
}
EXPORTS = {
    "serialization": {"dumps", "loads", "from_data", "to_data"},
    "order_source": {"ReplayOrderSource", "generate_orders"},
    "action_timing": {"action_duration_s", "action_duration_ticks"},
    "task_compiler": {"CurrentTaskCompiler"},
    "planning": {"StagedPipeline"},
}


def violations(source: str, module: str, package: str) -> list[str]:
    """Inspect static imports, including aliases and relative imports."""
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


class ModuleBoundaryTests(unittest.TestCase):
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
