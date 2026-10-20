"""Run upstream LaCAM once per action target on the supported unit lane."""
from pathlib import Path
from tempfile import mkdtemp
from time import monotonic

from warehouse_api.contracts import Do, Failure, FleetPlan, Move, PathRequest, RobotRoute, WorldModel
from warehouse_api.validation import check_jobs, check_single_lane
from warehouse_api.native_process import run_native
from ._validation import check_states


# 中文: 把公共路径请求适配到固定版本 LaCAM, 保留独立 MAPF 接口, 用真实上游路径验证模块连接.
# English: Adapt public path requests to pinned LaCAM so the replaceable MAPF boundary is exercised
# by real upstream routes.
class NativeMawpfPlanner:
    # 中文: 保存模型和绝对可执行路径, 初始化证据目录引用, 让每次原生调用可重放且不依赖工作目录.
    # English: Store the model and absolute executable path and initialize evidence tracking so
    # native calls are traceable and independent of the working directory.
    def __init__(self, model: WorldModel, executable: str):
        self.model = model
        self.executable = str(Path(executable).resolve())
        self.last_run_directory: Path | None = None

    # 中文: 逐个编译目标调用 LaCAM并转换为 Move/Do, 共享剩余预算, 保留动作身份以便 TPG 接续同一任务.
    # English: Call LaCAM for successive compiled targets and translate states to Move/Do while
    # sharing a deadline and retaining action identity for TPG.
    def plan(self, request: PathRequest) -> FleetPlan | Failure:
        failure = check_single_lane(self.model, request.start) or check_jobs(self.model, request.jobs)
        if failure is not None:
            return failure
        deadline = monotonic() + request.budget_s
        # 中文: 按物理 x 排序节点, 让原生格点索引与公共节点一一对应.
        # English: Sort nodes by physical x so native grid indices map to public node IDs.
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
