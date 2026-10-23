"""中文: trajectory 提供统一曲线读取与切片, 让消费者保持规划器给定的运动.
English: trajectory exports shared evaluation and slicing so consumers preserve planned motion.
"""
from ._curve import evaluate, slice_curve

__all__ = ["evaluate", "slice_curve"]
