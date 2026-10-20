"""中文: action_timing 模块导出动作耗时计算入口, 让编译器和运动规划器共用仿真步长量化规则.

English: The action_timing module exports action-duration calculations so compilation and motion planning share timestep quantization rules.
"""
from ._timing import action_duration_s, action_duration_ticks

__all__ = ['action_duration_s', 'action_duration_ticks']
