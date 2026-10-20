"""Reject constraints that the first native single-lane adapters cannot express."""
from math import isfinite

from warehouse_api.contracts import (
    AssignmentRequest, Failure, PlanningStart, Pose2, RobotJobs, Twist2, WorldModel,
)


# 中文: 集中声明原生适配器能表达的几何与初态子集, 不支持就拒绝, 避免偷偷简化多车或运动中续接约束.
# English: Declare the native adapters' supported geometry and start-state subset centrally so
# multi-robot or moving-splice constraints are rejected rather than silently simplified.
def check_single_lane(model: WorldModel, start: PlanningStart) -> Failure | None:
    unsupported = Failure("UNSUPPORTED", "Requires one stationary robot and shelf on an eastbound unit lane", ())
    if len(model.robots) != 1 or len(model.objects) != 1 or model.obstacles:
        return unsupported
    for entries in (model.nodes, model.edges, model.resources, model.places):
        if len({entry.id for entry in entries}) != len(entries):
            return Failure("BAD_INPUT", "Duplicate model ID", ())
    # 中文: 按 x 排序后逐格验证单位车道, 避免依赖输入容器的排列顺序.
    # English: Sort by x to check unit-lane spacing independently of input ordering.
    nodes = sorted(model.nodes, key=lambda node: node.position.x_m)
    if (len(nodes) < 4 or any(node.position.x_m != index or node.position.y_m != 0
                              for index, node in enumerate(nodes))):
        return unsupported
    if {(edge.from_node, edge.to_node) for edge in model.edges} != {
        (a.id, b.id) for a, b in zip(nodes, nodes[1:])
    } or len(model.edges) != len(nodes) - 1:
        return unsupported
    positions = {node.id: node.position.x_m for node in nodes}
    resources = {resource.id for resource in model.resources}
    if any(place.node_id not in positions or place.resource_id not in resources for place in model.places):
        return Failure("BAD_INPUT", "Place references an unknown node or resource", ())
    # 中文: 用节点坐标给位置排序, 确认业务目标符合向东服务顺序.
    # English: Order places by node position to check the eastbound service sequence.
    places = sorted(model.places, key=lambda place: positions[place.node_id])
    if ([place.kind for place in places] != ["storage", "station", "storage"]
            or any(place.yaw_rad != 0 for place in places)
            or not 0 < positions[places[0].node_id] < positions[places[1].node_id] < positions[places[2].node_id]
            or any(resource.capacity < 1 for resource in model.resources)):
        return unsupported
    limits = model.motion_limits
    if (limits.max_speed_mps, limits.acceleration_mps2, limits.braking_mps2) != (2, 1, 1):
        return Failure("UNSUPPORTED", "Pinned WinkTPG requires speed 2 and acceleration/braking 1", ())
    state = start.join_state
    shelf = model.objects[0]
    if (len(state.robots) != 1 or len(state.objects) != 1
            or state.robots[0].robot_id != model.robots[0].id or state.objects[0].object_id != shelf.id):
        return Failure("BAD_INPUT", "Join state does not match model IDs", ())
    if (start.fixed_prefix or state.running_actions or state.robots[0].pose != Pose2(0, 0, 0)
            or state.robots[0].velocity != Twist2(0, 0, 0)
            or state.objects[0].ground_pose != Pose2(positions[places[0].node_id], 0, 0)
            or state.objects[0].carrier_id is not None or shelf.carry_offset != Pose2(0, 0, 0)
            or not shelf.empty_robot_can_pass_under):
        return unsupported
    return None


# 中文: 要求一个机器人的 Lift/Serve/Drop 精确匹配支持位置和占用, 为 MAPF/TPG 共用作业检查, 防止接口相同却语义不同.
# English: Require Lift/Serve/Drop jobs to match supported places and resources so MAPF and TPG
# share semantic checks rather than merely compatible types.
def check_jobs(model: WorldModel, jobs: tuple[RobotJobs, ...]) -> Failure | None:
    if len(jobs) != 1 or jobs[0].robot_id != model.robots[0].id:
        return Failure("UNSUPPORTED", "Native subset requires one complete robot job", ())
    actions = jobs[0].actions
    nodes = {node.id: node.position.x_m for node in model.nodes}
    # 中文: 按车道顺序配对动作和位置, 防止同类位置被错误匹配.
    # English: Order places along the lane so actions are matched to the correct locations.
    places = sorted(model.places, key=lambda place: nodes[place.node_id])
    if (tuple(action.kind for action in actions) != ("lift", "serve", "drop")
            or len({action.step for action in actions}) != 3):
        return Failure("UNSUPPORTED", "Native subset requires distinct Lift, Serve, Drop references", ())
    for action, place in zip(actions, places):
        if (action.target_node != place.node_id or action.target_yaw_rad != 0
                or action.object_id != model.objects[0].id or not isfinite(action.duration_s) or action.duration_s <= 0
                or action.resource_ids != (place.resource_id,)):
            return Failure("UNSUPPORTED", "Action does not match the supported place sequence", ())
    return None


# 中文: 检查新任务快照及唯一需求/库存行, 区分非法输入与库存无解, 保证最小分配器不会覆盖已接受工作.
# English: Check a fresh task snapshot and the single demand/stock row, separating invalid input
# from infeasibility so allocation cannot overwrite accepted work.
def check_assignment(model: WorldModel, request: AssignmentRequest) -> Failure | None:
    if request.tasks or request.locks or any(queue.task_ids or queue.locked_prefix_count for queue in request.queues):
        return Failure("UNSUPPORTED", "First native chain requires a fresh task snapshot", ())
    if len(request.demands) != 1 or len(request.stock) != 1:
        return Failure("UNSUPPORTED", "First allocator supports one demand and stock row", ())
    demand, stock = request.demands[0], request.stock[0]
    if stock.object_id != model.objects[0].id or demand.available_quantity <= 0 or stock.available_quantity < 0:
        return Failure("BAD_INPUT", "Invalid demand or stock", ())
    if demand.sku != stock.sku or demand.available_quantity > stock.available_quantity:
        return Failure("NO_PLAN", "Available shelf stock cannot fulfill demand", (demand.order_id,))
    return None
