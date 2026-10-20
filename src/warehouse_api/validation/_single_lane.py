"""中文: 该模块拒绝首批单车道原生适配器无法表达的约束, 防止实际调用静默扩大宣称支持的范围.

English: This module rejects constraints the initial single-lane native adapters cannot express so actual calls cannot silently exceed their declared scope.
"""
from math import isfinite

from warehouse_api.contracts import (
    AssignmentRequest, Failure, PlanningStart, Pose2, RobotJobs, Twist2, WorldModel,
)


# 中文: check_single_lane 检查原生适配器支持的地图几何和方案接入初态, 对多车或接入时仍在运动等情况明确返回不支持, 防止适配器静默简化这些约束.
# English: check_single_lane checks the map geometry and plan-join state supported by the native adapters
# and explicitly rejects cases such as multiple robots or a moving join state so adapters cannot silently
# simplify those constraints.
def check_single_lane(model: WorldModel, start: PlanningStart) -> Failure | None:
    unsupported = Failure("UNSUPPORTED", "Requires one stationary robot and shelf on an eastbound unit lane", ())
    if len(model.robots) != 1 or len(model.objects) != 1 or model.obstacles:
        return unsupported
    for entries in (model.nodes, model.edges, model.resources, model.places):
        if len({entry.id for entry in entries}) != len(entries):
            return Failure("BAD_INPUT", "Duplicate model ID", ())
    # 中文: lambda 提供节点的 x 坐标, 让 check_single_lane 按位置检查相邻节点是否间隔一米, 避免依赖输入顺序.
    # English: The lambda supplies node x coordinates so check_single_lane checks one-meter spacing independently of input order.
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
    # 中文: lambda 提供作业位置所在节点的 x 坐标, 让 check_single_lane 核对取架, 服务和归还位置的向东顺序.
    # English: The lambda supplies each place's node x coordinate so check_single_lane checks the eastbound pickup, service and return order.
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


# 中文: check_jobs 要求单个机器人的抬架, 工作站服务和放架动作分别匹配支持的位置及占用资源, 使路径规划与运动时序规划共用同一业务检查, 防止类型兼容却执行语义不同.
# English: check_jobs requires one robot's shelf lift, workstation service and shelf drop to match the
# supported places and occupied resources so routing and motion timing share business checks instead of
# merely compatible types.
def check_jobs(model: WorldModel, jobs: tuple[RobotJobs, ...]) -> Failure | None:
    if len(jobs) != 1 or jobs[0].robot_id != model.robots[0].id:
        return Failure("UNSUPPORTED", "Native subset requires one complete robot job", ())
    actions = jobs[0].actions
    nodes = {node.id: node.position.x_m for node in model.nodes}
    # 中文: lambda 提供作业位置所在节点的 x 坐标, 让 check_jobs 按车道顺序配对动作和位置, 防止两个存储位置被对调.
    # English: The lambda supplies each place's node x coordinate so check_jobs pairs actions with lane-ordered places without swapping the storage locations.
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


# 中文: check_assignment 检查请求没有已接受任务或锁, 且只有一条商品需求和库存记录, 区分错误输入与库存不足, 使最小分配器不会覆盖既有工作.
# English: check_assignment checks that the request has no accepted tasks or locks and has one item-
# demand row and one stock row, distinguishing invalid input from insufficient stock so the minimal
# allocator cannot overwrite existing work.
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
