"""Run upstream LaCAM once per action target on the supported unit lane."""
from pathlib import Path
from tempfile import mkdtemp
from time import monotonic

from warehouse_api.contracts import Do, Failure, FleetPlan, Move, PathRequest, RobotRoute, WorldModel
from warehouse_api.validation import check_jobs, check_single_lane
from warehouse_api.native_process import run_native
from ._validation import check_states


class NativeMawpfPlanner:
    def __init__(self, model: WorldModel, executable: str):
        self.model = model
        self.executable = str(Path(executable).resolve())
        self.last_run_directory: Path | None = None

    def plan(self, request: PathRequest) -> FleetPlan | Failure:
        failure = check_single_lane(self.model, request.start) or check_jobs(self.model, request.jobs)
        if failure is not None:
            return failure
        deadline = monotonic() + request.budget_s
        nodes = sorted(self.model.nodes, key=lambda node: node.position.x_m)
        coordinates = {node.id: int(node.position.x_m) for node in nodes}
        edges = {(edge.from_node, edge.to_node): edge.id for edge in self.model.edges}
        steps = []
        current = 0
        root = Path(mkdtemp(prefix="warehouse-mawpf-"))
        self.last_run_directory = root
        grid = root / "lane.map"
        grid.write_text(f"type octile\nheight 1\nwidth {len(nodes)}\nmap\n" + "." * len(nodes) + "\n")
        for index, action in enumerate(request.jobs[0].actions):
            target = coordinates[action.target_node]
            output = root / f"leg-{index}.txt"
            remaining = deadline - monotonic()
            command = [self.executable, str(grid), str(output), str(current), str(target), str(remaining)]
            failure = run_native(command, output, budget_s=remaining, request_id=request.start.request_id)
            if failure is not None:
                return failure
            states = [tuple(map(int, line.split())) for line in output.read_text().splitlines()]
            failure = check_states(states, current, target)
            if failure is not None:
                return failure
            for x, y, heading, speed, omega in states:
                if x != current:
                    steps.append(Move(edges[nodes[current].id, nodes[x].id]))
                    current = x
            steps.append(Do(action.step))
        return FleetPlan(request.start.request_id, (RobotRoute(request.jobs[0].robot_id, tuple(steps)),), ())
