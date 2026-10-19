"""Warehouse API 0.7: data contracts, not implementations of the planners.
Python 3.10+. Standard library only. All fields are required unless defaulted.
Frozen dataclasses + tuples keep requests read-only. IDs are run-local strings.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Protocol

API_VERSION = "0.7"

def F(zh: str, en: str):
    return field(metadata={"zh": zh, "en": en})

@dataclass(frozen=True)
class Point2:
    x_m: float = F("世界坐标 x, 米.", "World x in meters.")
    y_m: float = F("世界坐标 y, 米.", "World y in meters.")

@dataclass(frozen=True)
class Pose2:
    x_m: float = F("世界坐标 x, 米.", "World x in meters.")
    y_m: float = F("世界坐标 y, 米.", "World y in meters.")
    yaw_rad: float = F("朝向, 弧度; 连续曲线中的角度不折回 ±pi.", "Heading in radians; unwrap yaw along a trajectory.")

@dataclass(frozen=True)
class Twist2:
    vx_mps: float = F("世界坐标系 x 方向速度, 米/秒.", "World-frame x velocity in m/s.")
    vy_mps: float = F("世界坐标系 y 方向速度, 米/秒.", "World-frame y velocity in m/s.")
    omega_radps: float = F("朝向变化率, 弧度/秒.", "Yaw rate in rad/s.")

@dataclass(frozen=True)
class Knot:
    time_s: float = F("仿真时间, 不是 MAPF 步数.", "Simulation time, not a MAPF step.")
    pose: Pose2 = F("该时刻的参考位姿.", "Reference pose at this time.")
    velocity: Twist2 = F("该位姿参考点的时间导数.", "Time derivative at the pose reference point.")

@dataclass(frozen=True)
class StepRef:
    task_id: str = F("任务 ID.", "Task ID.")
    step_index: int = F("任务中的动作下标, 从 0 开始.", "Zero-based action index within the task.")

ErrorCode = Literal["NO_PLAN", "TIMEOUT", "UNSUPPORTED", "BAD_INPUT", "STALE_REQUEST", "CONFLICT", "BAD_FRAME", "BAD_ACTION", "BACKEND_ERROR"]
@dataclass(frozen=True)
class Failure:
    code: ErrorCode = F("可供程序分支处理的错误码.", "Machine-readable failure code.")
    message: str = F("说明哪里失败, 不只写 error.", "Explain what failed, not just 'error'.")
    related_ids: tuple[str, ...] = F("相关机器人, 任务或资源 ID; 没有则空元组.", "Related robot/task/resource IDs; empty if none.")

# Static model: initialize once. No USD objects or Python callbacks in these DTOs.
@dataclass(frozen=True)
class Node:
    id: str = F("路网节点 ID.", "Route-graph node ID.")
    position: Point2 = F("节点的世界坐标.", "Node position in the world.")

@dataclass(frozen=True)
class Edge:
    id: str = F("有向直线边 ID.反向行驶使用另一条边.", "Directed straight-edge ID. Reverse travel uses a separate edge.")
    from_node: str = F("起点节点 ID.", "Start-node ID.")
    to_node: str = F("终点节点 ID.", "End-node ID.")

@dataclass(frozen=True)
class Polygon:
    vertices: tuple[Point2, ...] = F("至少三个逆时针顶点; 首版使用凸多边形.", "At least three counterclockwise vertices; convex in V0.")

@dataclass(frozen=True)
class Resource:
    id: str = F("需协调的路口, 边或工作站区域 ID.", "ID of a coordinated crossing, edge, or station region.")
    region: Polygon = F("该资源在世界坐标系中的区域.", "Resource region in the world frame.")
    capacity: int = F("最多同时使用的机器人数量, 至少 1.", "Maximum simultaneous users, at least one.")

@dataclass(frozen=True)
class RobotSpec:
    id: str = F("机器人 ID.", "Robot ID.")
    footprint: Polygon = F("车体坐标系的空载外形; x 向前, y 向左.", "Unloaded footprint in the body frame: x forward, y left.")

@dataclass(frozen=True)
class ObjectSpec:
    id: str = F("货架 ID.", "Shelf ID.")
    footprint: Polygon = F("货架自身坐标系的外形.", "Footprint in the shelf frame.")
    carry_offset: Pose2 = F("载货时货架相对车体的固定变换.", "Fixed shelf pose relative to the carrying robot.")
    empty_robot_can_pass_under: bool = F("空载车能否在未携带该货架时穿过其下方.", "Whether an empty robot can pass under the grounded shelf.")

@dataclass(frozen=True)
class Place:
    id: str = F("存储位或工作站 ID.", "Storage-slot or station ID.")
    kind: Literal["storage", "station"] = F("位置用途.", "Place purpose.")
    node_id: str = F("关联的路网节点.", "Associated route node.")
    yaw_rad: float = F("执行取放或服务时要求的朝向.", "Required heading for handling or service.")
    resource_id: str = F("关联的占用资源 ID.", "Associated occupancy-resource ID.")

@dataclass(frozen=True)
class MotionLimits:
    max_speed_mps: float = F("统一的执行限速.不是上游整数速度档.", "Uniform execution speed limit, not an abstract speed level.")
    acceleration_mps2: float = F("直线加速度上限.", "Forward acceleration limit.")
    braking_mps2: float = F("直线减速度绝对值上限.", "Maximum magnitude of braking acceleration.")
    turn_90_s: float = F("完整 90 度转向的最短时间.", "Minimum duration of a complete 90-degree turn.")
    turn_180_s: float = F("完整 180 度转向的最短时间.", "Minimum duration of a complete 180-degree turn.")
    turn_270_s: float = F("指定方向 270 度转向的最短时间.", "Minimum duration of a directed 270-degree turn.")

@dataclass(frozen=True)
class ActionTimes:
    lift_s: float = F("举架固定耗时.", "Fixed lift duration.")
    drop_s: float = F("放架固定耗时.", "Fixed drop duration.")
    service_base_s: float = F("一次服务的基础耗时.", "Base duration per service action.")
    service_per_unit_s: float = F("每件商品额外服务耗时.", "Additional service time per item unit.")

@dataclass(frozen=True)
class WorldModel:
    model_id: str = F("不可变场景模型版本 ID.", "Immutable scene-model version ID.")
    nodes: tuple[Node, ...] = F("带米制坐标的节点.", "Nodes with metric coordinates.")
    edges: tuple[Edge, ...] = F("有向可通行边.", "Directed traversable edges.")
    obstacles: tuple[Polygon, ...] = F("静态障碍的世界坐标外形.", "Static obstacles in world coordinates.")
    resources: tuple[Resource, ...] = F("需要协调的区域及容量.", "Coordinated regions and capacities.")
    robots: tuple[RobotSpec, ...] = F("机器人几何规格.", "Robot geometry specifications.")
    objects: tuple[ObjectSpec, ...] = F("货架几何与携带规则.", "Shelf geometry and carrying rules.")
    places: tuple[Place, ...] = F("存储位与工作站.", "Storage slots and stations.")
    motion_limits: MotionLimits = F("WinkTPG/验证器使用的统一物理模型.", "Uniform physical model for WinkTPG and validation.")
    action_times: ActionTimes = F("动作耗时规则, 所有模块共用.", "Shared action-duration rules.")

@dataclass(frozen=True)
class PlannerConfig:
    max_speed_level: int = F("MAWPF 最大整数速度档, 示例值 2.", "Maximum abstract MAWPF level; trial value 2.")
    rotation_steps: int = F("MAWPF 的 90 度转向步数.", "Abstract steps for a 90-degree turn.")
    lookahead_steps: int = F("多步 PIBT 的窗口长度.", "Multi-step PIBT lookahead length.")
    seed: int = F("随机种子.", "Random seed.")

@dataclass(frozen=True)
class RunConfig:
    sim_dt_s: float = F("一次 backend.step 推进的仿真秒数.", "Simulation seconds advanced by one backend.step.")
    commit_horizon_s: float = F("每次希望增加的前缀长度, 不是安全保证.", "Desired prefix extension, not a safety guarantee.")
    replan_period_s: float = F("暂停规划模式下的常规重规划间隔.", "Regular replan interval in paused-planning mode.")
    planner_budget_s: float = F("一次规划总墙钟预算.", "Wall-clock budget for one planning round.")
    seed: int = F("本轮实验随机种子.", "Experiment seed.")

# Business data.
@dataclass(frozen=True)
class Item:
    sku: str = F("商品种类 ID.", "Product-type ID.")
    quantity: int = F("正整数件数.", "Positive integer quantity.")

@dataclass(frozen=True)
class Order:
    id: str = F("订单 ID.", "Order ID.")
    released_at_s: float = F("订单进入系统的仿真时间.", "Simulation release time.")
    items: tuple[Item, ...] = F("需求清单, 同 SKU 合并.", "Requested items; merge repeated SKUs.")
    due_at_s: float | None = F("软截止; None 表示无截止.", "Soft due time; None means no due time.")

@dataclass(frozen=True)
class Pick:
    order_id: str = F("被满足的订单.", "Order being fulfilled.")
    sku: str = F("商品种类.", "Product type.")
    quantity: int = F("本次服务完成的件数.", "Quantity fulfilled by this service.")

@dataclass(frozen=True)
class Lift:
    object_id: str = F("要取的货架.", "Shelf to pick up.")
    kind: Literal["lift"] = "lift"

@dataclass(frozen=True)
class Serve:
    station_id: str = F("目标工作站.", "Target station.")
    picks: tuple[Pick, ...] = F("服务成功后满足哪些订单需求.", "Demand fulfilled only after service succeeds.")
    kind: Literal["serve"] = "serve"

@dataclass(frozen=True)
class Drop:
    storage_id: str = F("目标存储位.", "Target storage slot.")
    kind: Literal["drop"] = "drop"

TaskAction = Lift | Serve | Drop
@dataclass(frozen=True)
class Task:
    id: str = F("任务 ID; 同一 run 内不能复用.", "Task ID; never reused within a run.")
    steps: tuple[TaskAction, ...] = F("有序动作; V0 为 Lift, Serve, Drop.", "Ordered actions; Lift, Serve, Drop in V0.")

@dataclass(frozen=True)
class RobotQueue:
    robot_id: str = F("执行这些任务的机器人.", "Robot assigned these tasks.")
    task_ids: tuple[str, ...] = F("任务执行顺序.", "Ordered task IDs.")

@dataclass(frozen=True)
class QueueState:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    task_ids: tuple[str, ...] = F("当前完整任务队列.", "Current complete task queue.")
    locked_prefix_count: int = F("前多少个任务绑定不可改; 输出队列只替换这个下标之后的部分.", "Count of protected tasks at the front; a proposal replaces only the suffix after this index.")

@dataclass(frozen=True)
class TaskDelta:
    tasks: tuple[Task, ...] = F("只包含本次新建任务, 不含旧任务副本.", "New task definitions only, not copies of old tasks.")
    queues: tuple[RobotQueue, ...] = F("替换所列机器人尚未固定的任务队列后缀.", "Replace the mutable queue suffix of each listed robot.")

@dataclass(frozen=True)
class Demand:
    order_id: str = F("订单 ID.", "Order ID.")
    sku: str = F("商品种类.", "Product type.")
    available_quantity: int = F("尚未完成且没有被正式任务预留的数量.", "Unfulfilled quantity not reserved by accepted tasks.")
    due_at_s: float | None = F("原订单软截止.", "Original order soft due time.")

@dataclass(frozen=True)
class Stock:
    object_id: str = F("存放商品的货架.", "Shelf containing the stock.")
    sku: str = F("商品种类.", "Product type.")
    available_quantity: int = F("尚未被正式任务预留的数量.", "Quantity not reserved by accepted tasks.")

@dataclass(frozen=True)
class TaskProgress:
    task: Task = F("已接受且不可就地修改的任务定义.", "Accepted immutable task definition.")
    next_step: int = F("按旧承诺预测到 join_state 后, 下一未完成动作下标; 等于动作数表示完成, 不提前更新正式账本.", "Next unfinished index projected to join_state under the old commitment; the action count means predicted completion, without changing the live ledger.")
    blocked: bool = F("失败后暂停, 不能自动重试.", "Blocked after failure; no automatic retry.")

@dataclass(frozen=True)
class StepLock:
    step: StepRef = F("已经承诺, 必须保护的动作.", "Committed action that must be preserved.")
    robot_id: str = F("该动作不可更换的执行者.", "Executor that cannot be reassigned.")

# Physical state: business quantities never travel to the simulator.
@dataclass(frozen=True)
class RobotState:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    pose: Pose2 = F("当前理想位姿.", "Current ideal pose.")
    velocity: Twist2 = F("当前理想速度.", "Current ideal velocity.")

@dataclass(frozen=True)
class ObjectState:
    object_id: str = F("货架 ID.", "Shelf ID.")
    ground_pose: Pose2 | None = F("在地面时的位姿; 载货时为 None.", "Ground pose; None while carried.")
    carrier_id: str | None = F("载货机器人 ID; 在地面时为 None.两字段恰有一个非空.", "Carrier ID; None on the ground. Exactly one location field is non-null.")

@dataclass(frozen=True)
class RunningAction:
    robot_id: str = F("正在执行动作的机器人.", "Robot executing the action.")
    step: StepRef = F("动作引用.", "Action reference.")
    started_at_s: float = F("开始时间.", "Start time.")
    ends_at_s: float = F("确定性完成时间.", "Deterministic completion time.")

@dataclass(frozen=True)
class PhysicalState:
    time_s: float = F("这份状态对应的仿真时刻.", "Simulation time represented by this state.")
    robots: tuple[RobotState, ...] = F("全部机器人状态.", "All robot states.")
    objects: tuple[ObjectState, ...] = F("全部货架的位置或携带关系.", "All shelf locations or carrying relations.")
    running_actions: tuple[RunningAction, ...] = F("当前未完成动作; 没有则空元组.", "Unfinished actions; empty when none.")

@dataclass(frozen=True)
class ActionResult:
    time_s: float = F("动作结果发生的仿真时间.", "Simulation time of the result.")
    step: StepRef = F("用来更新任务及订单的动作引用.", "Action reference for task and order updates.")
    success: bool = F("是否成功.", "Whether the action succeeded.")
    reason: str = F("成功时为空字符串; 失败时说明原因.", "Empty on success; diagnostic on failure.")

@dataclass(frozen=True)
class Observation:
    state: PhysicalState = F("本步完成后的完整理想状态.", "Full ideal state after the step.")
    events: tuple[ActionResult, ...] = F("本步新增结果, 按时间和动作引用排序.", "New results in this step, sorted by time and action reference.")

# Shared planning start; every field is visible, rather than hidden behind a View.
@dataclass(frozen=True)
class TimedAction:
    start_s: float = F("开始执行动作的精确仿真时间.", "Exact action start time.")
    step: StepRef = F("动作定义从统一动作表查询.", "Look up the definition in the shared action table.")

@dataclass(frozen=True)
class RobotSegment:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    knots: tuple[Knot, ...] = F("按时间递增的曲线节点.", "Knots in strictly increasing time order.")
    actions: tuple[TimedAction, ...] = F("这段运动内开始的动作.", "Actions starting in this segment.")

@dataclass(frozen=True)
class PlanningStart:
    request_id: str = F("本轮请求 ID; 整个分层或联合求解共用.", "Round ID shared by staged or fused solving.")
    state_version: int = F("任务/预留/已接受运动版本, 不是每步位置版本.", "Task/reservation/accepted-plan version, not a per-tick pose version.")
    now_s: float = F("发起规划的当前仿真时间.", "Current simulation time when planning is requested.")
    join_state: PhysicalState = F("旧前缀结束时的精确预测状态.time_s 就是续接时刻.", "Exact state predicted at the end of the old prefix; time_s is the splice time.")
    fixed_prefix: tuple[RobotSegment, ...] = F("当前至续接时刻不可修改的轨迹; 包含未完成动作引用.", "Immutable motion from now to the splice, including references to unfinished actions.")
    submit_before_s: float = F("必须严格早于此时刻接受新方案.", "New plans must be accepted strictly before this time.")

@dataclass(frozen=True)
class AssignmentRequest:
    start: PlanningStart = F("共同规划起点与版本.", "Shared planning start and versions.")
    demands: tuple[Demand, ...] = F("可以新分配的订单需求.", "Demand available for new assignment.")
    stock: tuple[Stock, ...] = F("可以新预留的库存.", "Stock available for new reservation.")
    tasks: tuple[TaskProgress, ...] = F("既有任务与进度, 包括未绑定任务.", "Existing task definitions and progress, including unbound tasks.")
    queues: tuple[QueueState, ...] = F("当前完整队列及不能修改的前缀长度.", "Current complete queues and protected-prefix lengths.")
    locks: tuple[StepLock, ...] = F("不能更换执行者的动作.", "Actions whose executors cannot change.")
    budget_s: float = F("本次模块调用的墙钟预算.", "Wall-clock budget for this call.")

@dataclass(frozen=True)
class PhysicalAction:
    step: StepRef = F("与业务任务关联的引用, 不含商品列表.", "Link to the business task without product details.")
    kind: Literal["lift", "serve", "drop"] = F("动作类型.", "Action kind.")
    object_id: str = F("相关货架; Serve/Drop 也明确是哪一架.", "Relevant shelf, also specified for Serve/Drop.")
    target_node: str = F("必须到达的节点, 由共享编译函数解析.", "Required node, resolved by the shared compiler.")
    target_yaw_rad: float = F("动作要求的朝向.", "Required action heading.")
    duration_s: float = F("由共享模型计算并量化的耗时, 模块不得自行缩短.", "Duration derived and quantized by the shared model, not shortened by plugins.")
    resource_ids: tuple[str, ...] = F("整个动作期间占用的资源.", "Resources held throughout the action.")

@dataclass(frozen=True)
class RobotJobs:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    actions: tuple[PhysicalAction, ...] = F("从 join_state 开始尚需执行的有序动作.", "Ordered actions remaining after join_state.")

@dataclass(frozen=True)
class PathRequest:
    start: PlanningStart = F("精确续接状态与旧前缀.", "Exact splice state and old prefix.")
    jobs: tuple[RobotJobs, ...] = F("草稿任务解析成的物理动作队列.", "Physical action queues compiled from the draft.")
    budget_s: float = F("本次路径规划墙钟预算.", "Wall-clock budget for route planning.")

@dataclass(frozen=True)
class Move:
    edge_id: str = F("相邻节点之间的边; 首个 Move 可沿这条边走完剩余部分.", "Adjacent-node edge; the first Move may traverse its remaining partial length.")
    kind: Literal["move"] = "move"

@dataclass(frozen=True)
class Turn:
    angle_rad: float = F("有符号旋转角; 正数为逆时针.", "Signed turn angle; positive is counterclockwise.")
    kind: Literal["turn"] = "turn"

@dataclass(frozen=True)
class Do:
    step: StepRef = F("执行哪个物理动作.", "Physical action to execute.")
    kind: Literal["do"] = "do"

RouteStep = Move | Turn | Do
@dataclass(frozen=True)
class RobotRoute:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    steps: tuple[RouteStep, ...] = F("相邻移动, 转向与作业的顺序; 不带抽象时间.", "Adjacent moves, turns and actions in order, without abstract timestamps.")

@dataclass(frozen=True)
class VisitEvent:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    route_step: int = F("路线动作下标, 区分重复访问.", "Route-step index, distinguishing repeat visits.")
    resource_id: str = F("进入或清空的资源.", "Resource being entered or cleared.")
    phase: Literal["enter", "clear"] = F("按完整组合外形首次进入/最后清空该区域.", "First entry / final clearance by the full combined footprint.")

@dataclass(frozen=True)
class Precedence:
    first: VisitEvent = F("先发生的 clear 事件.", "Preceding clear event.")
    second: VisitEvent = F("后发生的 enter 事件.", "Following enter event.")

@dataclass(frozen=True)
class FleetPlan:
    request_id: str = F("对应的规划请求.", "Associated planning request.")
    routes: tuple[RobotRoute, ...] = F("全部机器人的路线; 静止机器人可用空 steps.", "Routes for all robots; stationary robots may have no steps.")
    before: tuple[Precedence, ...] = F("必须保持的跨车通行顺序.", "Required cross-robot precedence.")

@dataclass(frozen=True)
class MotionRequest:
    start: PlanningStart = F("同一轮的规划起点.", "The same round's planning start.")
    jobs: tuple[RobotJobs, ...] = F("动作定义与合法耗时.", "Action definitions and valid durations.")
    fleet_plan: FleetPlan = F("已选路线和先后关系.", "Selected routes and precedence.")
    target_end_s: float = F("希望延长到的仿真时间, 可返回其他经验证的边界.", "Desired end time; another verified boundary may be returned.")
    budget_s: float = F("本次轨迹计算墙钟预算.", "Wall-clock budget for motion planning.")

@dataclass(frozen=True)
class MotionPlan:
    common_prefix: tuple[RobotSegment, ...] = F("从旧边界到新共同边界的追加运动, 覆盖全车队.", "Fleet-wide extension from the old to the new common boundary.")
    stop_tail: tuple[RobotSegment, ...] = F("从新边界出发的完整车队停车轨迹, 终点持续占用.", "Complete fleet stopping trajectories; final occupancy persists.")

@dataclass(frozen=True)
class ExecutableProposal:
    request_id: str = F("对应请求 ID; Runtime 据此复核版本.", "Request ID used for version revalidation.")
    task_delta: TaskDelta = F("与本次运动一起接受的任务修改.", "Task edits accepted together with this motion.")
    motion: MotionPlan = F("前缀和停车后缀; 没有未授权 continue_tail.", "Prefix and stop tail; no unauthorized continue tail.")

@dataclass(frozen=True)
class Accepted:
    commit_id: str = F("已发布方案 ID.", "Published plan ID.")
    state_version: int = F("新的业务/执行版本.", "New business/execution version.")

# Execution and simulator messages.
@dataclass(frozen=True)
class ExecutionInput:
    state: PhysicalState = F("当前状态, 提供切片开始时间.", "Current state and slicing start time.")
    active_segments: tuple[RobotSegment, ...] = F("Runtime 选定分支的曲线, 覆盖本步或结束后保持.", "Curves of the selected branch, covering the step or holding afterward.")
    action_table: tuple[PhysicalAction, ...] = F("已接受的动作定义, 仅包含物理字段.", "Accepted action definitions with physical fields only.")

@dataclass(frozen=True)
class RobotMotion:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    knots: tuple[Knot, ...] = F("当前步两端和所有内部切换点.", "Step endpoints and every internal switch knot.")

@dataclass(frozen=True)
class ActionStart:
    robot_id: str = F("动作执行者.", "Action executor.")
    action: PhysicalAction = F("本步开始的动作定义; 后端无须查询订单.", "Action beginning now; the backend need not query orders.")

@dataclass(frozen=True)
class IdealControlFrame:
    from_s: float = F("这一控制步的开始时刻.", "Start of this control step.")
    to_s: float = F("结束时刻; 必须等于 from_s + sim_dt_s.", "End time; must equal from_s + sim_dt_s.")
    motion: tuple[RobotMotion, ...] = F("全体机器人当前步的曲线, 静止也发送保持曲线.", "Current-step curves for all robots, including explicit holds.")
    start_actions: tuple[ActionStart, ...] = F("恰在 from_s 开始的动作; 不能重复发送.", "Actions starting exactly at from_s; never resend.")

@dataclass(frozen=True)
class BackendInit:
    run_id: str = F("一次实验的 ID.", "Experiment run ID.")
    model: WorldModel = F("初始化一次的静态模型.", "Static model sent once at initialization.")
    initial_state: PhysicalState = F("time_s=0 的静止初态.", "Stationary initial state at time_s=0.")
    sim_dt_s: float = F("理想步进间隔.", "Ideal simulation step interval.")

@dataclass(frozen=True)
class PlanningRequest:
    assignment: AssignmentRequest = F("完整但无隐藏对象的本轮输入.", "Complete round input without hidden runtime objects.")
    target_end_s: float = F("本轮希望延长到的时间.", "Desired extension end time.")

# Ports: implement these signatures independently. Constructors receive model/config.
class OrderSource(Protocol):
    def reset(self, orders: tuple[Order, ...]) -> None: ...
    def release(self, until_s: float) -> tuple[Order, ...]: ...

class Allocator(Protocol):
    def allocate(self, request: AssignmentRequest) -> TaskDelta | Failure: ...

class PathPlanner(Protocol):
    def plan(self, request: PathRequest) -> FleetPlan | Failure: ...

class MotionPlanner(Protocol):
    def prepare(self, request: MotionRequest) -> MotionPlan | Failure: ...

class DecisionPipeline(Protocol):
    def solve(self, request: PlanningRequest) -> ExecutableProposal | Failure: ...

class CentralExecutor(Protocol):
    def build_frame(self, data: ExecutionInput, dt_s: float) -> IdealControlFrame | Failure: ...

class IdealBackend(Protocol):
    def reset(self, request: BackendInit) -> Observation | Failure: ...
    def step(self, frame: IdealControlFrame) -> Observation | Failure: ...
    def close(self) -> None: ...

class Runtime(Protocol):
    def reset(self, model: WorldModel, config: RunConfig, initial: Observation, stock: tuple[Stock, ...]) -> None: ...
    def add_orders(self, orders: tuple[Order, ...]) -> None: ...
    def make_request(self) -> PlanningRequest: ...
    def submit(self, proposal: ExecutableProposal) -> Accepted | Failure: ...
    def process_due_branch(self) -> None: ...
    def execution_input(self) -> ExecutionInput: ...
    def observe(self, observation: Observation) -> None: ...

class SharedCompiler(Protocol):
    def compile_jobs(self, request: AssignmentRequest, draft: TaskDelta) -> tuple[RobotJobs, ...] | Failure: ...

class Validator(Protocol):
    def check_proposal(self, request: PlanningRequest, proposal: ExecutableProposal) -> tuple[Failure, ...]: ...
    def check_frame(self, model: WorldModel, state: PhysicalState, frame: IdealControlFrame, dt_s: float) -> tuple[Failure, ...]: ...
