"""中文: execution 公开共享控制帧构建器, 让后端接收同一曲线与动作语义.
English: execution exports the shared frame builder so backends receive consistent curves and actions.
"""
from ._executor import TrajectoryExecutor

__all__ = ['TrajectoryExecutor']
