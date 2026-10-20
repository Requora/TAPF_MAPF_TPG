"""中文: 该模块把编译器输出的动作执行位置交给上游 LaCAM 路径搜索, 使业务动作获得到达路线.

English: This module sends compiled action locations to upstream LaCAM route searches so business actions receive arrival routes.
"""
from pathlib import Path
from tempfile import mkdtemp
from time import monotonic

from warehouse_api.contracts import Do, Failure, FleetPlan, Move, PathRequest, RobotRoute, WorldModel
from warehouse_api.validation import check_jobs, check_single_lane
from warehouse_api.native_process import run_native
from ._validation import check_states


# 中文: NativeMawpfPlanner 将 PathRequest 转换成 MAWPF 项目中 LaCAM 路径搜索算法的输入,
# 再将搜索结果转换成 FleetPlan. 这两个类型是本仓库模块间约定的数据接口.
# PathRequest 携带机器人起始状态和待执行动作; FleetPlan 携带机器人沿地图移动并执行动作的顺序.
# 这个适配类隔离了上游程序的数据格式, 让后续模块可以读取统一结果, 而不必了解 LaCAM 的内部对象.
# MAPF 指多机器人路径规划, 但当前适配器只支持一台机器人沿向东直线车道移动.
# English: NativeMawpfPlanner converts a PathRequest into input for the LaCAM path-search algorithm
# in the MAWPF project, then converts its output into a FleetPlan. These types define messages between repository modules.
# PathRequest carries the robot start state and required actions; FleetPlan carries the resulting moves and action order.
# The adapter isolates the upstream program's data format so later modules need not understand LaCAM objects.
# MAPF means multi-agent path finding, but this adapter currently supports only one robot on an eastbound straight lane.
class NativeMawpfPlanner:
    # 中文: __init__ 保存场景模型, 并将 executable 转换成原生桥接程序的绝对文件路径.
    # 原生桥接程序是调用 MAWPF 的已编译 C++ 程序; 绝对路径让后续调用不依赖进程的工作目录.
    # last_run_directory 初始为空, plan 执行时会用它记录输入和输出文件的目录, 供开发者检查真实调用.
    # English: __init__ stores the scene model and resolves executable to the absolute path of the native bridge,
    # the compiled C++ program that calls MAWPF. The absolute path removes dependence on the process working directory.
    # last_run_directory starts empty; plan later records the input/output directory there so developers can inspect calls.
    def __init__(self, model: WorldModel, executable: str):
        self.model = model
        self.executable = str(Path(executable).resolve())
        self.last_run_directory: Path | None = None

    # 中文: plan 读取任务编译器已经生成的动作列表, 按顺序为每个动作规划到达路线; 该方法不编译任务.
    # 每个动作的 target_node 表示机器人执行该动作时必须到达的地图节点, 例如取架位或工作站.
    # 该方法每次调用 LaCAM, 从上一段终点规划到下一个 target_node, 再把相邻节点间的移动记为 Move.
    # 该方法在到达后追加 Do, 即对原任务步骤的引用, 表示机器人应在此处执行该步骤.
    # 所有调用共用请求的时间预算, 且 Do 保留原步骤引用, 让后续 TPG 运动规划阶段能沿选定路线安排同一组动作.
    # English: plan reads actions already produced by the task compiler and plans routes to them in order;
    # this method does not compile tasks. Each target_node is the map node where the robot must perform an action,
    # such as the pickup location or workstation. Each LaCAM call plans from the previous endpoint to the next target.
    # The method records travel between adjacent nodes as Move and appends Do, a reference to the original task step,
    # at arrival. The calls share one time budget, and the retained step references let the subsequent TPG motion
    # planning stage schedule the same actions along the selected route.
    def plan(self, request: PathRequest) -> FleetPlan | Failure:
        failure = check_single_lane(self.model, request.start) or check_jobs(self.model, request.jobs)
        if failure is not None:
            return failure
        deadline = monotonic() + request.budget_s
        # 中文: lambda 返回地图节点的 x 坐标, 让 sorted 按从西到东的顺序排列节点.
        # 上游程序用车道格子的整数序号表示位置; 这个排列让适配器能将序号转换回本仓库地图中的节点 ID.
        # English: The lambda returns each map node's x coordinate so sorted orders nodes from west to east.
        # The upstream program identifies lane cells by integer index; this ordering lets the adapter map each index
        # back to a node ID in the repository's map.
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
