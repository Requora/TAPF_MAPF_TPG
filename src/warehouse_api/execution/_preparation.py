"""中文: 本模块只准备执行曲线快照, 将具体合法性规则留给独立校验模块.
English: This module only prepares execution snapshots, leaving concrete legality rules to separate validation.
"""
from warehouse_api.contracts import ExecutionInput, Failure
from warehouse_api.trajectory import PreparedTrajectory
from ._validation import check_input, check_joins


# 中文: prepare_frame 在准备前后整体调用阶段校验, 缓存相同值的曲线, 不定义覆盖或衔接规则.
# English: prepare_frame calls aggregate checks before and after preparation and caches equal curves without defining coverage or join rules.
def prepare_frame(data: ExecutionInput, dt_s: float, cached: dict, started: set) -> dict | Failure:
    failure = check_input(data, dt_s, started)
    if failure is not None:
        return failure
    curves = {}
    for segment in data.active_segments:
        curve = cached.get(segment.robot_id)
        if curve is None or curve[0] != segment.knots:
            curve = (segment.knots, PreparedTrajectory(segment.knots))
        curves[segment.robot_id] = curve
    failure = check_joins(data, curves)
    return failure if failure is not None else curves
