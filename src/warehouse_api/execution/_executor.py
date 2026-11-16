"""中文: 本模块把 Runtime 选定的曲线转换为控制帧, 复用共享 C++ 切片核心而不重新规划.
English: This module converts Runtime-selected curves to frames using shared C++ slicing without replanning.
"""
from warehouse_api.contracts import ActionStart, ExecutionInput, Failure, IdealControlFrame, RobotMotion
from warehouse_api.trajectory import slice_curve
from ._preparation import prepare_frame
from ._validation import same_tick


# 中文: TrajectoryExecutor 实现 CentralExecutor 协议, 为所有机器人切出下一步并记录已输出的启动指令, 以识别漏步; 调用方每个时间步只发送一个返回帧, 重试构帧不会提交状态.
# English: TrajectoryExecutor implements CentralExecutor by slicing each robot's next step and tracking returned starts to detect skipped commands; callers dispatch one returned frame per tick, and rebuilding a frame commits no state.
class TrajectoryExecutor:
    # 中文: __init__ 缓存当前曲线和当前计划的启动输出记录, 避免重复准备并在漏步时拒绝无证据的过去动作.
    # English: __init__ caches current curves and their returned-start history to reuse preparation and reject missed past starts without evidence.
    def __init__(self):
        self._curves = {}
        self._started = set()

    # 中文: build_frame 保留原曲线内部节点并只输出当前时刻的新动作, 不修改输入或推断任务完成; 正在执行的动作不重复启动.
    # English: build_frame retains internal knots and emits only new actions at the current time without mutating inputs or inferring completion; running actions are not restarted.
    def build_frame(self, data: ExecutionInput, dt_s: float) -> IdealControlFrame | Failure:
        curves = prepare_frame(data, dt_s, self._curves, self._started)
        if isinstance(curves, Failure):
            return curves
        start, end = data.state.time_s, data.state.time_s + dt_s
        motion = tuple(RobotMotion(segment.robot_id, slice_curve(curves[segment.robot_id][1], start, end))
                       for segment in data.active_segments)
        self._curves = curves
        table = {action.step: action for action in data.action_table}
        running = {action.step for action in data.state.running_actions}
        actions = tuple(ActionStart(segment.robot_id, table[action.step])
                        for segment in data.active_segments for action in segment.actions
                        if same_tick(action.start_s, start, dt_s) and action.step not in running)
        self._started.intersection_update((segment.robot_id, action.step)
                                          for segment in data.active_segments for action in segment.actions)
        self._started.update((action.robot_id, action.action.step) for action in actions)
        return IdealControlFrame(start, end, motion, actions)
