"""Run one real order through allocation, compilation, MAWPF, and WinkTPG."""
import argparse
import copy
from hashlib import sha256
import json
from pathlib import Path

from warehouse_api.allocation import SingleShelfAllocator
from warehouse_api.contracts import (
    ActionTimes, AssignmentRequest, Demand, Edge, Failure, Item, MotionLimits, Node,
    ObjectSpec, ObjectState, Order, PhysicalState, Place, PlanningRequest, PlanningStart,
    Point2, Polygon, Pose2, Resource, RobotSpec, RobotState, Stock, Twist2, WorldModel,
)
from warehouse_api.mapf import NativeMawpfPlanner
from warehouse_api.order_source import ReplayOrderSource
from warehouse_api.planning import StagedPipeline
from warehouse_api.serialization import dumps
from warehouse_api.task_compiler import CurrentTaskCompiler
from warehouse_api.tpg import NativeWinkTpgPlanner


# 中文: scenario 函数构造直线场景, 允许测试调整订单数量和目标位置. 这些输入用于检查需求变化是否真正传到原生求解器.
# English: scenario builds a lane scenario with variable quantities and destinations so native integration can
# show that changed demand reaches the actual solvers.
def scenario(*, quantity=1, stock=1, station=3, destination=5):
    body = Polygon((Point2(-0.2, -0.2), Point2(0.2, -0.2), Point2(0.2, 0.2), Point2(-0.2, 0.2)))
    places = (Place("pickup", "storage", "n1", 0, "pickup"),
              Place("station", "station", f"n{station}", 0, "station"),
              Place("return", "storage", f"n{destination}", 0, "return"))
    positions = (1, station, destination)
    resources = tuple(Resource(place.id, Polygon(tuple(Point2(x + vertex.x_m, vertex.y_m)
                                                       for vertex in body.vertices)), 1)
                      for place, x in zip(places, positions))
    model = WorldModel(
        "native-lane", tuple(Node(f"n{x}", Point2(x, 0)) for x in range(destination + 1)),
        tuple(Edge(f"e{x}", f"n{x}", f"n{x+1}") for x in range(destination)), (), resources,
        (RobotSpec("A", body),), (ObjectSpec("shelf", body, Pose2(0, 0, 0), True),), places,
        MotionLimits(2, 1, 1, 0.5, 0.9, 1.5), ActionTimes(0.3, 0.3, 0.1, 0.2),
    )
    orders = ReplayOrderSource((Order("O", 0, (Item("X", quantity),), None),)).release(0)
    state = PhysicalState(0, (RobotState("A", Pose2(0, 0, 0), Twist2(0, 0, 0)),),
                          (ObjectState("shelf", Pose2(1, 0, 0), None),), ())
    start = PlanningStart("native-chain", 0, 0, state, (), 30)
    demands = tuple(Demand(order.id, item.sku, item.quantity, order.due_at_s)
                    for order in orders for item in order.items)
    request = PlanningRequest(AssignmentRequest(start, demands, (Stock("shelf", "X", stock),),
                                                (), (), (), 20), 30)
    return orders, model, request


# 中文: run 函数执行真实分配, 路径规划和 TPG 轨迹生成, 并收集阶段与原生程序文件. run 比较调用前后的输入快照, 让重放可检查输入污染并追溯真实求解证据.
# English: run executes real allocation, routing and TPG trajectory generation, and collects stage/native files.
# run compares input snapshots before and after execution so replay exposes mutation and actual solver evidence.
def run(binary_directory: Path, **parameters):
    orders, model, request = scenario(**parameters)
    before = copy.deepcopy((model, request))
    path = NativeMawpfPlanner(model, str(binary_directory / "warehouse_mawpf"))
    motion = NativeWinkTpgPlanner(model, str(binary_directory / "warehouse_winktpg"), sim_dt_s=0.1)
    pipeline = StagedPipeline(SingleShelfAllocator(model), CurrentTaskCompiler(model, sim_dt_s=0.1), path, motion)
    result = pipeline.solve(request)
    assert (model, request) == before
    raw = {}
    for stage, directory in (("mapf", path.last_run_directory), ("tpg", motion.last_run_directory)):
        if directory is not None:
            raw[stage] = {file.name: file.read_text() for file in directory.iterdir() if file.suffix != ".bin"}
    return {
        "status": "native planning chain completed" if not isinstance(result, Failure) else "rejected",
        "limits": "One robot, one shelf, eastbound unit lane; no Runtime acceptance or continuous collision proof.",
        "sources": {
            "mawpf": "https://github.com/HirokiNagai-39/mawpf/tree/0cdb8e43797aff3781e4cd3ddb2c6d7d36f3df17",
            "winktpg": "https://github.com/JingtianYan/WinkTPG-IEEE-TASE/tree/dd96946f225e206de35b041320786eab43210658",
        },
        "binaries": {name: sha256((binary_directory / name).read_bytes()).hexdigest()
                     for name in ("warehouse_mawpf", "warehouse_winktpg")},
        "seed": 0, "orders": orders, "model": model, "request": request,
        "trace": pipeline.last_trace, "native_evidence": raw, "result": result,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary_directory", type=Path)
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--stock", type=int, default=1)
    parser.add_argument("--station", type=int, default=3)
    parser.add_argument("--destination", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--html", type=Path)
    args = parser.parse_args()
    result = run(args.binary_directory, quantity=args.quantity, stock=args.stock,
                 station=args.station, destination=args.destination)
    args.output.write_text(dumps(result))
    if args.html:
        template = Path(__file__).with_suffix(".html").read_text()
        args.html.write_text(template.replace("__EVIDENCE__", dumps(result).replace("<", "\\u003c")))
    print(json.dumps({"status": result["status"], "trace": str(args.output)}))
