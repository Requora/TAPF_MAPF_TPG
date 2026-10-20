"""中文: validation 模块导出原生适配器支持范围检查, 让路径和运动规划共用限制; 该模块尚未实现连续运动候选的安全验证.

English: The validation module exports native-adapter subset checks so path and motion planning share restrictions; the module does not yet validate continuous-motion candidate safety.
"""
from ._single_lane import check_single_lane, check_jobs, check_assignment

__all__ = ["check_single_lane", "check_jobs", "check_assignment"]
