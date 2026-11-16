"""中文: 本模块把 Runtime 选定的曲线转换为控制帧, 复用共享 C++ 切片核心而不重新规划.
English: This module converts Runtime-selected curves to frames using shared C++ slicing without replanning.
"""
from warehouse_api.contracts import ActionStart, ExecutionInput, Failure, IdealControlFrame, RobotMotion
from warehouse_api.trajectory import PreparedTrajectory, evaluate, slice_curve
from ._validation import check_coverage, check_curve, check_input, same_tick


# 中文: TrajectoryExecutor 实现 CentralExecutor 协议, 为所有机器人切出下一步并解析当前动作; 调用方每个时间步只发送一个返回帧, 重试构帧不会提交状态.
# English: TrajectoryExecutor implements CentralExecutor by slicing each robot's next step and resolving current actions; callers dispatch one returned frame per tick, and rebuilding a frame commits no state.
class TrajectoryExecutor:
    # 中文: __init__ 建立仅保存当前曲线的快照缓存, 避免每步重复准备和无界保留历史计划.
    # English: __init__ creates a current-curve snapshot cache to avoid repeated preparation and unbounded plan history.
    def __init__(self):
        self._curves = {}

    # 中文: build_frame 保留原曲线内部节点并只输出当前时刻的新动作, 不修改输入或推断任务完成; 正在执行的动作不重复启动.
    # English: build_frame retains internal knots and emits only new actions at the current time without mutating inputs or inferring completion; running actions are not restarted.
    def build_frame(self, data: ExecutionInput, dt_s: float) -> IdealControlFrame | Failure:
        failure = check_input(data, dt_s)
        if failure is not None:
            return failure
        start, end = data.state.time_s, data.state.time_s + dt_s
        states = {robot.robot_id: robot for robot in data.state.robots}
        curves, motion = {}, []
        for segment in data.active_segments:
            cached = self._curves.get(segment.robot_id)
            if cached is None or cached[0] is not segment.knots:
                failure = check_curve(segment)
                if failure is not None:
                    return failure
                cached = (segment.knots, PreparedTrajectory(segment.knots))
            failure = check_coverage(segment, start, end)
            if failure is not None:
                return failure
            current = evaluate(cached[1], start)
            state = states[segment.robot_id]
            if current.pose != state.pose or current.velocity != state.velocity:
                return Failure('BAD_FRAME', 'Curve start must exactly match current state', (segment.robot_id,))
            motion.append(RobotMotion(segment.robot_id, slice_curve(cached[1], start, end)))
            curves[segment.robot_id] = cached
        self._curves = curves
        table = {action.step: action for action in data.action_table}
        running = {action.step for action in data.state.running_actions}
        actions = tuple(ActionStart(segment.robot_id, table[action.step])
                        for segment in data.active_segments for action in segment.actions
                        if same_tick(action.start_s, start, dt_s) and action.step not in running)
        return IdealControlFrame(start, end, tuple(motion), actions)
