"""Convert actual WinkTPG primitives to exact Hermite knots and action holds."""
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


class NativeWinkTpgPlanner:
    def __init__(self, model: WorldModel, executable: str, *, sim_dt_s: float):
        self.model = model
        self.executable = str(Path(executable).resolve())
        self.sim_dt_s = sim_dt_s
        self.last_run_directory: Path | None = None

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
                if v0 == v1 == 0:
                    knots.append(Knot(origin + start + duration / 2, Pose2(x + 0.5, 0, 0), Twist2(1, 0, 0)))
                knots.append(Knot(origin + start + duration, Pose2(x + 1, 0, 0), Twist2(v1, 0, 0)))
            # Hold at rest until a backend tick; never shorten a compiled action.
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
