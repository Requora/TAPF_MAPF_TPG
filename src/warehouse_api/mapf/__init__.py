"""中文: mapf 模块导出固定上游版本的 MAWPF 路径规划适配器, 使调用方无需接触上游对象.

English: The mapf module exports the pinned MAWPF path-planning adapter so callers do not need upstream objects.
"""
from ._mawpf import NativeMawpfPlanner

__all__ = ["NativeMawpfPlanner"]
