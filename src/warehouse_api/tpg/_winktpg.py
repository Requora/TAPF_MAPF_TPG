"""中文: 该模块将 WinkTPG 时间和速度记录转换成 Hermite 轨迹的时间, 位置和速度节点, 并加入动作静止段, 让上游结果可由统一运动契约表达.

English: This module converts WinkTPG timing and speed records into time, position and velocity knots for Hermite trajectories and inserts stationary action intervals so shared motion contracts can represent upstream results.
"""
from math import ceil
from pathlib import Path
from tempfile import mkdtemp
from time import monotonic

from warehouse_api.contracts import (
    Failure, Knot, MotionPlan, MotionRequest, Move, Pose2, RobotSegment, TimedAction, Twist2, WorldModel,
)
from warehouse_api.native_process import run_native
from warehouse_api.validation import check_jobs, check_single_lane
from ._validation import check_profile, check_route


# 中文: NativeWinkTpgPlanner 将上游 WinkTPG 的每格时间和速度记录转换为模块间共享的连续轨迹, 沿已选路线安排机器人动作.
# 该类让路径选择与运动时序可分别替换, 当前只支持单车直线车道.
# English: NativeWinkTpgPlanner converts upstream WinkTPG per-cell time and speed records into shared
# continuous trajectories and schedules actions along the selected route so routing and motion timing
# remain separately replaceable; the adapter currently supports one robot on a straight lane.
class NativeWinkTpgPlanner:
    # 中文: NativeWinkTpgPlanner.__init__ 保存场景模型, 已编译的桥接程序路径和仿真步长, 为轨迹转换明确输入及动作对齐时间,
    # 避免读取隐藏的运行状态.
    # English: NativeWinkTpgPlanner.__init__ stores the scene model, compiled bridge path and simulation
    # timestep so trajectory conversion has explicit inputs and action-alignment times without reading
    # hidden runtime state.
    def __init__(self, model: WorldModel, executable: str, *, sim_dt_s: float):
        self.model = model
        self.executable = str(Path(executable).resolve())
        self.sim_dt_s = sim_dt_s
        self.last_run_directory: Path | None = None

    # 中文: prepare 沿已选路线调用上游程序计算速度曲线, 保留加减速切换点并插入完整的静止动作时段, 使编译器指定的动作位置和耗时在真实时间轴上成立.
    # English: prepare calls the upstream program to compute speed profiles along the selected route,
    # preserves acceleration-switch points and inserts complete stationary action intervals so compiled
    # targets and durations hold on the physical timeline.
    def prepare(self, request: MotionRequest) -> MotionPlan | Failure:
        failure = (check_single_lane(self.model, request.start) or check_jobs(self.model, request.jobs)
                   or check_route(self.model, request, self.sim_dt_s))
        if failure is not None:
            return failure
        deadline = monotonic() + request.budget_s
        root = Path(mkdtemp(prefix="warehouse-winktpg-"))
        self.last_run_directory = root
        positions = {node.id: int(node.position.x_m) for node in self.model.nodes}
        edges = {edge.id: edge for edge in self.model.edges}
        robot = request.start.join_state.robots[0]
        knots = [Knot(request.start.join_state.time_s, robot.pose, robot.velocity)]
        scheduled = []
        path = [0]
        for step in request.fleet_plan.routes[0].steps:
            if isinstance(step, Move):
                path.append(positions[edges[step.edge_id].to_node])
                continue
            index = len(scheduled)
            source = root / f"leg-{index}.path"
            source.write_text(" ".join(map(str, path)) + "\n")
            output = root / f"leg-{index}.txt"
            remaining = deadline - monotonic()
            failure = run_native([self.executable, str(source), str(output), str(remaining)], output,
                                 budget_s=remaining, request_id=request.start.request_id)
            if failure is not None:
                return failure
            rows = [tuple(map(float, line.split())) for line in output.read_text().splitlines()]
            failure = check_profile(rows, len(path) - 1)
            if failure is not None:
                return failure
            origin = knots[-1].time_s
            for x, (start, duration, v0, v1) in zip(path, rows):
                if origin + start > knots[-1].time_s + 1e-8:
                    knots.append(Knot(origin + start, Pose2(x, 0, 0), Twist2(v0, 0, 0)))
                # 中文: 上游起终速度均为零的记录表示机器人先加速再减速跨过一格; prepare 保留格子中点的切换状态以还原真实运动.
                # English: A zero-to-zero record crosses one cell by accelerating then braking; prepare keeps the midpoint switch to preserve the actual motion.
                if v0 == v1 == 0:
                    knots.append(Knot(origin + start + duration / 2, Pose2(x + 0.5, 0, 0), Twist2(1, 0, 0)))
                knots.append(Knot(origin + start + duration, Pose2(x + 1, 0, 0), Twist2(v1, 0, 0)))
            # 中文: prepare 让机器人静止等待到下一个仿真步长边界, 再安排完整动作耗时, 防止时间对齐缩短动作.
            # English: prepare holds the robot still until a simulation-step boundary, then schedules the full action duration so alignment cannot shorten the action.
            time = knots[-1].time_s
            aligned = ceil(time / self.sim_dt_s) * self.sim_dt_s
            if aligned > time:
                knots.append(Knot(aligned, knots[-1].pose, Twist2(0, 0, 0)))
            action = request.jobs[0].actions[index]
            scheduled.append(TimedAction(aligned, action.step))
            knots.append(Knot(aligned + action.duration_s, knots[-1].pose, Twist2(0, 0, 0)))
            path = [path[-1]]
        prefix = RobotSegment(robot.robot_id, tuple(knots), tuple(scheduled))
        last = knots[-1]
        tail = RobotSegment(robot.robot_id, (last, Knot(last.time_s + self.sim_dt_s, last.pose, last.velocity)), ())
        return MotionPlan((prefix,), (tail,))
