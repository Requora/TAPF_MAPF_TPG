"""中文: allocation 模块导出单货架任务分配器, 为当前支持的受限场景提供可替换的分配入口.

English: The allocation module exports the single-shelf task allocator to provide a replaceable allocation entry point for the supported subset.
"""
from ._single_shelf import SingleShelfAllocator

__all__ = ["SingleShelfAllocator"]
