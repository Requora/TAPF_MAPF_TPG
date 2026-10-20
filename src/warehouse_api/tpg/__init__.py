"""中文: tpg 模块导出固定上游版本的 WinkTPG 运动规划适配器, 为受限单车道场景提供轨迹生成入口.

English: The tpg module exports the pinned WinkTPG motion adapter to provide trajectory generation for the supported single-lane subset.
"""
from ._winktpg import NativeWinkTpgPlanner

__all__ = ["NativeWinkTpgPlanner"]
