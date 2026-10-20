"""中文: planning 模块导出分阶段规划入口, 让调用方通过统一契约组合可替换的求解阶段.

English: The planning module exports staged planning so callers can compose replaceable solver stages through shared contracts.
"""
from ._staged import StagedPipeline

__all__ = ["StagedPipeline"]
