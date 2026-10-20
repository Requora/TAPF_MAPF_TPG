"""Warehouse API 0.7: data contracts, not implementations of the planners.
Python 3.10+. Standard library only. All fields are required unless defaulted.
Frozen dataclasses + tuples keep requests read-only. IDs are run-local strings.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Protocol

API_VERSION = "0.7"

# 中文: 把双语字段说明存入 dataclass 元数据, 让同一契约同时服务代码和文档, 避免字段含义各写一份.
# English: Store bilingual field descriptions in dataclass metadata so code and documentation share
# one definition of each field.
def F(zh: str, en: str):
    return field(metadata={"zh": zh, "en": en})

# 中文: 表示米制二维位置, 为路网和几何提供统一坐标, 避免把网格编号当物理距离.
# English: Represent a metric 2D point so graph and geometry consumers share coordinates instead of
# treating grid indices as distances.
@dataclass(frozen=True)
class Point2:
    x_m: float = F("世界坐标 x, 米.", "World x in meters.")
    y_m: float = F("世界坐标 y, 米.", "World y in meters.")

# 中文: 表示位置和朝向, 供目标与轨迹共用, 使到达节点但朝向错误的状态可以被区分.
# English: Represent position and heading together so targets and trajectories can distinguish
# reaching a node from facing the required direction.
@dataclass(frozen=True)
class Pose2:
    x_m: float = F("世界坐标 x, 米.", "World x in meters.")
    y_m: float = F("世界坐标 y, 米.", "World y in meters.")
    yaw_rad: float = F("朝向, 弧度; 连续曲线中的角度不折回 ±pi.", "Heading in radians; unwrap yaw along a trajectory.")

# 中文: 表示世界坐标速度和角速度, 为曲线导数提供共同单位, 支持精确续接及运动约束检查.
# English: Represent world-frame linear and angular velocity so trajectory derivatives support exact
# splices and physical-limit checks.
@dataclass(frozen=True)
class Twist2:
    vx_mps: float = F("世界坐标系 x 方向速度, 米/秒.", "World-frame x velocity in m/s.")
    vy_mps: float = F("世界坐标系 y 方向速度, 米/秒.", "World-frame y velocity in m/s.")
    omega_radps: float = F("朝向变化率, 弧度/秒.", "Yaw rate in rad/s.")

# 中文: 记录某时刻的位姿及导数, 作为 Hermite 曲线边界, 让执行器保留区间内的真实运动切换.
# English: Record pose and derivative at a time boundary so Hermite trajectories preserve motion
# switches when sliced for execution.
@dataclass(frozen=True)
class Knot:
    time_s: float = F("仿真时间, 不是 MAPF 步数.", "Simulation time, not a MAPF step.")
    pose: Pose2 = F("该时刻的参考位姿.", "Reference pose at this time.")
    velocity: Twist2 = F("该位姿参考点的时间导数.", "Time derivative at the pose reference point.")

# 中文: 用任务 ID 和动作下标标识动作, 跨规划和执行传递同一引用, 避免复制动作后失去业务归属.
# English: Identify an action by task ID and step index so planning and execution retain its
# business identity without copying task definitions.
@dataclass(frozen=True)
class StepRef:
    task_id: str = F("任务 ID.", "Task ID.")
    step_index: int = F("任务中的动作下标, 从 0 开始.", "Zero-based action index within the task.")

ErrorCode = Literal["NO_PLAN", "TIMEOUT", "UNSUPPORTED", "BAD_INPUT", "STALE_REQUEST", "CONFLICT", "BAD_FRAME", "BAD_ACTION", "BACKEND_ERROR"]
# 中文: 传递失败码, 原因和关联 ID, 为模块提供统一拒绝结果, 让调用方区分无解, 超时和非法输入.
# English: Carry a failure code, reason and related IDs so callers can distinguish infeasibility,
# timeout and invalid input across modules.
@dataclass(frozen=True)
class Failure:
    code: ErrorCode = F("可供程序分支处理的错误码.", "Machine-readable failure code.")
    message: str = F("说明哪里失败, 不只写 error.", "Explain what failed, not just 'error'.")
    related_ids: tuple[str, ...] = F("相关机器人, 任务或资源 ID; 没有则空元组.", "Related robot/task/resource IDs; empty if none.")

# Static model: initialize once. No USD objects or Python callbacks in these DTOs.
# 中文: 给路网位置分配稳定 ID, 让路径引用拓扑而几何仍使用米制坐标, 便于替换规划器.
# English: Give a graph position a stable ID so routes reference topology while geometry keeps
# metric coordinates across planner replacements.
@dataclass(frozen=True)
class Node:
    id: str = F("路网节点 ID.", "Route-graph node ID.")
    position: Point2 = F("节点的世界坐标.", "Node position in the world.")

# 中文: 表示有向直线通行连接, 供路线引用合法移动, 明确反向行驶需要另一条边.
# English: Represent a directed straight connection so routes name legal moves and reverse travel
# requires a separate edge.
@dataclass(frozen=True)
class Edge:
    id: str = F("有向直线边 ID.反向行驶使用另一条边.", "Directed straight-edge ID. Reverse travel uses a separate edge.")
    from_node: str = F("起点节点 ID.", "Start-node ID.")
    to_node: str = F("终点节点 ID.", "End-node ID.")

# 中文: 统一表达机器人, 货架和障碍外形, 为连续几何检查保留真实轮廓, 而非只靠节点占用.
# English: Represent footprints and obstacle outlines so continuous geometry can use physical shapes
# rather than only node occupancy.
@dataclass(frozen=True)
class Polygon:
    vertices: tuple[Point2, ...] = F("至少三个逆时针顶点; 首版使用凸多边形.", "At least three counterclockwise vertices; convex in V0.")

# 中文: 把空间区域和容量关联起来, 供协调层表达共享占用, 避免把资源竞争仅当路径相交.
# English: Associate an area with a capacity so coordination can express shared occupancy beyond
# simple route intersections.
@dataclass(frozen=True)
class Resource:
    id: str = F("需协调的路口, 边或工作站区域 ID.", "ID of a coordinated crossing, edge, or station region.")
    region: Polygon = F("该资源在世界坐标系中的区域.", "Resource region in the world frame.")
    capacity: int = F("最多同时使用的机器人数量, 至少 1.", "Maximum simultaneous users, at least one.")

# 中文: 保存机器人静态外形, 与运行中的位姿分离, 让同一模型可供多次规划和几何校验复用.
# English: Store static robot geometry separately from changing poses so planning and geometry
# checks can reuse one model.
@dataclass(frozen=True)
class RobotSpec:
    id: str = F("机器人 ID.", "Robot ID.")
    footprint: Polygon = F("车体坐标系的空载外形; x 向前, y 向左.", "Unloaded footprint in the body frame: x forward, y left.")

# 中文: 保存货架外形及携带规则, 让规划区分空载穿架和载货外形, 避免把货架当无尺寸货物.
# English: Store shelf geometry and carrying rules so planning distinguishes unloaded passage from
# the combined loaded footprint.
@dataclass(frozen=True)
class ObjectSpec:
    id: str = F("货架 ID.", "Shelf ID.")
    footprint: Polygon = F("货架自身坐标系的外形.", "Footprint in the shelf frame.")
    carry_offset: Pose2 = F("载货时货架相对车体的固定变换.", "Fixed shelf pose relative to the carrying robot.")
    empty_robot_can_pass_under: bool = F("空载车能否在未携带该货架时穿过其下方.", "Whether an empty robot can pass under the grounded shelf.")

# 中文: 将业务存储位或工作站解析为节点, 朝向和资源, 让编译器统一解释服务位置.
# English: Map a storage slot or station to a node, heading and resource so the compiler gives
# service locations one physical meaning.
@dataclass(frozen=True)
class Place:
    id: str = F("存储位或工作站 ID.", "Storage-slot or station ID.")
    kind: Literal["storage", "station"] = F("位置用途.", "Place purpose.")
    node_id: str = F("关联的路网节点.", "Associated route node.")
    yaw_rad: float = F("执行取放或服务时要求的朝向.", "Required heading for handling or service.")
    resource_id: str = F("关联的占用资源 ID.", "Associated occupancy-resource ID.")

# 中文: 汇总物理速度, 加减速及转向限制, 供运动规划和验证共用, 避免各模块采用不同动力学假设.
# English: Share speed, acceleration, braking and turn limits so motion planning and validation use
# the same physical assumptions.
@dataclass(frozen=True)
class MotionLimits:
    max_speed_mps: float = F("统一的执行限速.不是上游整数速度档.", "Uniform execution speed limit, not an abstract speed level.")
    acceleration_mps2: float = F("直线加速度上限.", "Forward acceleration limit.")
    braking_mps2: float = F("直线减速度绝对值上限.", "Maximum magnitude of braking acceleration.")
    turn_90_s: float = F("完整 90 度转向的最短时间.", "Minimum duration of a complete 90-degree turn.")
    turn_180_s: float = F("完整 180 度转向的最短时间.", "Minimum duration of a complete 180-degree turn.")
    turn_270_s: float = F("指定方向 270 度转向的最短时间.", "Minimum duration of a directed 270-degree turn.")

# 中文: 集中定义举架, 放架和服务耗时, 供所有编译与规划模块复用, 避免自行缩短动作.
# English: Centralize handling and service durations so compilers and planners cannot assign
# inconsistent action times.
@dataclass(frozen=True)
class ActionTimes:
    lift_s: float = F("举架固定耗时.", "Fixed lift duration.")
    drop_s: float = F("放架固定耗时.", "Fixed drop duration.")
    service_base_s: float = F("一次服务的基础耗时.", "Base duration per service action.")
    service_per_unit_s: float = F("每件商品额外服务耗时.", "Additional service time per item unit.")

# 中文: 汇总不可变路网, 几何和物理规则, 作为模块共同输入, 避免求解器依赖隐藏场景对象.
# English: Bundle immutable topology, geometry and physical rules so solvers receive explicit shared
# data instead of hidden scene objects.
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

# 中文: 保存上游离散规划参数, 与真实物理限制分开, 避免把整数速度档直接当执行速度.
# English: Store discrete planner settings separately from physical limits so abstract speed levels
# are not mistaken for execution speeds.
@dataclass(frozen=True)
class PlannerConfig:
    max_speed_level: int = F("MAWPF 最大整数速度档, 示例值 2.", "Maximum abstract MAWPF level; trial value 2.")
    rotation_steps: int = F("MAWPF 的 90 度转向步数.", "Abstract steps for a 90-degree turn.")
    lookahead_steps: int = F("多步 PIBT 的窗口长度.", "Multi-step PIBT lookahead length.")
    seed: int = F("随机种子.", "Random seed.")

# 中文: 集中记录实验步长, 预算和重规划节奏, 让运行策略可复现, 并区分墙钟耗时与仿真时间.
# English: Record experiment timing, budgets and replan cadence for reproducibility while separating
# wall-clock cost from simulation time.
@dataclass(frozen=True)
class RunConfig:
    sim_dt_s: float = F("一次 backend.step 推进的仿真秒数.", "Simulation seconds advanced by one backend.step.")
    commit_horizon_s: float = F("每次希望增加的前缀长度, 不是安全保证.", "Desired prefix extension, not a safety guarantee.")
    replan_period_s: float = F("暂停规划模式下的常规重规划间隔.", "Regular replan interval in paused-planning mode.")
    planner_budget_s: float = F("一次规划总墙钟预算.", "Wall-clock budget for one planning round.")
    seed: int = F("本轮实验随机种子.", "Experiment seed.")

# Business data.
# 中文: 表示订单中的 SKU 数量, 为需求提供最小业务单元, 让同类商品可以合并统计.
# English: Represent a requested SKU quantity so demand has a minimal business unit that can be
# merged by product type.
@dataclass(frozen=True)
class Item:
    sku: str = F("商品种类 ID.", "Product-type ID.")
    quantity: int = F("正整数件数.", "Positive integer quantity.")

# 中文: 保存需求及发布时间和软截止, 供订单源输入, 将何时出现需求与如何搬运货架分开.
# English: Store demand, release time and soft due time so order generation stays separate from
# shelf assignment and movement.
@dataclass(frozen=True)
class Order:
    id: str = F("订单 ID.", "Order ID.")
    released_at_s: float = F("订单进入系统的仿真时间.", "Simulation release time.")
    items: tuple[Item, ...] = F("需求清单, 同 SKU 合并.", "Requested items; merge repeated SKUs.")
    due_at_s: float | None = F("软截止; None 表示无截止.", "Soft due time; None means no due time.")

# 中文: 把服务数量关联回订单和 SKU, 为成功服务后的需求记账保留依据, 避免只知道搬了哪个货架.
# English: Link serviced quantities to their orders and SKUs so successful service can update demand
# rather than merely record shelf movement.
@dataclass(frozen=True)
class Pick:
    order_id: str = F("被满足的订单.", "Order being fulfilled.")
    sku: str = F("商品种类.", "Product type.")
    quantity: int = F("本次服务完成的件数.", "Quantity fulfilled by this service.")

# 中文: 表达取哪个货架的业务动作, 由共享编译器补全位置和耗时, 避免分配器重复处理物理规则.
# English: Express which shelf to lift while leaving physical targets and duration to the shared
# compiler instead of each allocator.
@dataclass(frozen=True)
class Lift:
    object_id: str = F("要取的货架.", "Shelf to pick up.")
    kind: Literal["lift"] = "lift"

# 中文: 表达在哪个工作站满足哪些需求, 将服务意图与物理动作分离, 防止计划生成就被视为订单完成.
# English: Express station service and fulfilled demand separately from physical execution so a
# planned service is not treated as completed demand.
@dataclass(frozen=True)
class Serve:
    station_id: str = F("目标工作站.", "Target station.")
    picks: tuple[Pick, ...] = F("服务成功后满足哪些订单需求.", "Demand fulfilled only after service succeeds.")
    kind: Literal["serve"] = "serve"

# 中文: 表达归还存储位, 由编译器解析位置与资源, 让分配决策不绑定某个路径规划器.
# English: Express a return slot for compiler resolution so assignment decisions remain independent
# of a particular path planner.
@dataclass(frozen=True)
class Drop:
    storage_id: str = F("目标存储位.", "Target storage slot.")
    kind: Literal["drop"] = "drop"

TaskAction = Lift | Serve | Drop
# 中文: 用稳定 ID 组织有序业务动作, 供进度和锁共同引用, 避免重规划时失去动作身份.
# English: Group ordered business actions under a stable ID so progress and locks retain action
# identity during replanning.
@dataclass(frozen=True)
class Task:
    id: str = F("任务 ID; 同一 run 内不能复用.", "Task ID; never reused within a run.")
    steps: tuple[TaskAction, ...] = F("有序动作; V0 为 Lift, Serve, Drop.", "Ordered actions; Lift, Serve, Drop in V0.")

# 中文: 表达机器人候选任务顺序, 为分配结果提供公开类型, 让候选修改不直接写实时队列.
# English: Represent a proposed robot task order so assignment can return edits without mutating
# live queues.
@dataclass(frozen=True)
class RobotQueue:
    robot_id: str = F("执行这些任务的机器人.", "Robot assigned these tasks.")
    task_ids: tuple[str, ...] = F("任务执行顺序.", "Ordered task IDs.")

# 中文: 保存当前队列及受保护前缀, 给求解器标明不可改范围, 保证已承诺任务绑定可被保留.
# English: Expose the current queue and its protected prefix so solvers know which committed
# bindings cannot be changed.
@dataclass(frozen=True)
class QueueState:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    task_ids: tuple[str, ...] = F("当前完整任务队列.", "Current complete task queue.")
    locked_prefix_count: int = F("前多少个任务绑定不可改; 输出队列只替换这个下标之后的部分.", "Count of protected tasks at the front; a proposal replaces only the suffix after this index.")

# 中文: 打包新任务和队列后缀修改, 作为尚未提交的分配候选, 让 Runtime 能与运动方案一起原子接受.
# English: Package new tasks and queue-suffix edits as a candidate so Runtime can accept business
# and motion changes atomically.
@dataclass(frozen=True)
class TaskDelta:
    tasks: tuple[Task, ...] = F("只包含本次新建任务, 不含旧任务副本.", "New task definitions only, not copies of old tasks.")
    queues: tuple[RobotQueue, ...] = F("替换所列机器人尚未固定的任务队列后缀.", "Replace the mutable queue suffix of each listed robot.")

# 中文: 只暴露尚未完成且未预留的需求, 供分配器选择, 避免重复分配已被正式任务占用的数量.
# English: Expose unfulfilled, unreserved demand to allocation so quantities already reserved by
# accepted tasks are not allocated again.
@dataclass(frozen=True)
class Demand:
    order_id: str = F("订单 ID.", "Order ID.")
    sku: str = F("商品种类.", "Product type.")
    available_quantity: int = F("尚未完成且没有被正式任务预留的数量.", "Unfulfilled quantity not reserved by accepted tasks.")
    due_at_s: float | None = F("原订单软截止.", "Original order soft due time.")

# 中文: 只暴露货架可用库存, 与实际总库存区别, 防止候选分配重复消耗已有预留.
# English: Expose available shelf stock separately from total inventory so new assignments do not
# reuse accepted reservations.
@dataclass(frozen=True)
class Stock:
    object_id: str = F("存放商品的货架.", "Shelf containing the stock.")
    sku: str = F("商品种类.", "Product type.")
    available_quantity: int = F("尚未被正式任务预留的数量.", "Quantity not reserved by accepted tasks.")

# 中文: 描述旧承诺推演到续接时刻的任务进度, 供编译剩余动作, 避免再次推进或提前修改实时账本.
# English: Describe task progress projected to the splice so compilation emits remaining actions
# without advancing progress twice or changing the live ledger.
@dataclass(frozen=True)
class TaskProgress:
    task: Task = F("已接受且不可就地修改的任务定义.", "Accepted immutable task definition.")
    next_step: int = F("按旧承诺预测到 join_state 后, 下一未完成动作下标; 等于动作数表示完成, 不提前更新正式账本.", "Next unfinished index projected to join_state under the old commitment; the action count means predicted completion, without changing the live ledger.")
    blocked: bool = F("失败后暂停, 不能自动重试.", "Blocked after failure; no automatic retry.")

# 中文: 固定已承诺动作的执行者, 即使队列前缀长度为零也保留保护, 防止携带或服务责任被转移.
# English: Pin a committed action to its executor even with an empty protected queue prefix so
# carrying or service responsibility cannot be reassigned.
@dataclass(frozen=True)
class StepLock:
    step: StepRef = F("已经承诺, 必须保护的动作.", "Committed action that must be preserved.")
    robot_id: str = F("该动作不可更换的执行者.", "Executor that cannot be reassigned.")

# Physical state: business quantities never travel to the simulator.
# 中文: 记录某台机器人当前位姿和速度, 供规划续接与观测使用, 让移动状态不会被当作静止起点.
# English: Record a robot's pose and velocity for planning and observation so a moving state is not
# mistaken for a stationary start.
@dataclass(frozen=True)
class RobotState:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    pose: Pose2 = F("当前理想位姿.", "Current ideal pose.")
    velocity: Twist2 = F("当前理想速度.", "Current ideal velocity.")

# 中文: 明确货架落地位置或携带者, 为取放前置条件提供依据, 避免同一货架同时落地和载货.
# English: Identify a shelf's ground pose or carrier so handling preconditions can reject
# contradictory location states.
@dataclass(frozen=True)
class ObjectState:
    object_id: str = F("货架 ID.", "Shelf ID.")
    ground_pose: Pose2 | None = F("在地面时的位姿; 载货时为 None.", "Ground pose; None while carried.")
    carrier_id: str | None = F("载货机器人 ID; 在地面时为 None.两字段恰有一个非空.", "Carrier ID; None on the ground. Exactly one location field is non-null.")

# 中文: 记录尚未结束的动作及时间窗, 让续接和执行保护在途工作, 避免重复启动或中途替换.
# English: Record an unfinished action and its time interval so replanning and execution can protect
# it from restart or replacement.
@dataclass(frozen=True)
class RunningAction:
    robot_id: str = F("正在执行动作的机器人.", "Robot executing the action.")
    step: StepRef = F("动作引用.", "Action reference.")
    started_at_s: float = F("开始时间.", "Start time.")
    ends_at_s: float = F("确定性完成时间.", "Deterministic completion time.")

# 中文: 保存同一仿真时刻的完整机器人和货架状态, 为模块提供一致快照, 避免拼接不同时刻的数据.
# English: Bundle the complete physical state at one simulation time so modules do not combine
# observations from different instants.
@dataclass(frozen=True)
class PhysicalState:
    time_s: float = F("这份状态对应的仿真时刻.", "Simulation time represented by this state.")
    robots: tuple[RobotState, ...] = F("全部机器人状态.", "All robot states.")
    objects: tuple[ObjectState, ...] = F("全部货架的位置或携带关系.", "All shelf locations or carrying relations.")
    running_actions: tuple[RunningAction, ...] = F("当前未完成动作; 没有则空元组.", "Unfinished actions; empty when none.")

# 中文: 将成功或失败事件关联到动作引用, 为任务记账提供执行证据, 避免用计划时间代替真实结果.
# English: Associate success or failure with an action reference so task accounting uses execution
# evidence rather than planned completion times.
@dataclass(frozen=True)
class ActionResult:
    time_s: float = F("动作结果发生的仿真时间.", "Simulation time of the result.")
    step: StepRef = F("用来更新任务及订单的动作引用.", "Action reference for task and order updates.")
    success: bool = F("是否成功.", "Whether the action succeeded.")
    reason: str = F("成功时为空字符串; 失败时说明原因.", "Empty on success; diagnostic on failure.")

# 中文: 同时返回完整状态和本步新增事件, 供 Runtime 对账, 区分持续状态与只处理一次的结果.
# English: Return full state with newly produced events so Runtime can reconcile ongoing state
# separately from one-time action results.
@dataclass(frozen=True)
class Observation:
    state: PhysicalState = F("本步完成后的完整理想状态.", "Full ideal state after the step.")
    events: tuple[ActionResult, ...] = F("本步新增结果, 按时间和动作引用排序.", "New results in this step, sorted by time and action reference.")

# Shared planning start; every field is visible, rather than hidden behind a View.
# 中文: 只给统一动作引用安排精确开始时刻, 避免运动层复制业务定义, 保持执行与任务身份一致.
# English: Schedule an exact start time for a shared action reference so motion does not duplicate
# business definitions or lose task identity.
@dataclass(frozen=True)
class TimedAction:
    start_s: float = F("开始执行动作的精确仿真时间.", "Exact action start time.")
    step: StepRef = F("动作定义从统一动作表查询.", "Look up the definition in the shared action table.")

# 中文: 将一台机器人的连续曲线和动作开始时刻合在一起, 作为切片单位, 保持移动与作业时间对应.
# English: Bundle one robot's curve and action starts as a slicing unit so motion and service timing
# stay consistent.
@dataclass(frozen=True)
class RobotSegment:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    knots: tuple[Knot, ...] = F("按时间递增的曲线节点.", "Knots in strictly increasing time order.")
    actions: tuple[TimedAction, ...] = F("这段运动内开始的动作.", "Actions starting in this segment.")

# 中文: 公开版本, 续接状态和旧固定前缀, 为所有求解阶段建立同一起点, 防止候选覆盖旧承诺.
# English: Expose versions, splice state and fixed motion so every solving stage starts from the
# same commitment boundary.
@dataclass(frozen=True)
class PlanningStart:
    request_id: str = F("本轮请求 ID; 整个分层或联合求解共用.", "Round ID shared by staged or fused solving.")
    state_version: int = F("任务/预留/已接受运动版本, 不是每步位置版本.", "Task/reservation/accepted-plan version, not a per-tick pose version.")
    now_s: float = F("发起规划的当前仿真时间.", "Current simulation time when planning is requested.")
    join_state: PhysicalState = F("旧前缀结束时的精确预测状态.time_s 就是续接时刻.", "Exact state predicted at the end of the old prefix; time_s is the splice time.")
    fixed_prefix: tuple[RobotSegment, ...] = F("当前至续接时刻不可修改的轨迹; 包含未完成动作引用.", "Immutable motion from now to the splice, including references to unfinished actions.")
    submit_before_s: float = F("必须严格早于此时刻接受新方案.", "New plans must be accepted strictly before this time.")

# 中文: 汇总可分配需求, 库存及受保护进度, 给分配器完整快照, 防止依赖或修改隐藏账本.
# English: Provide allocation with demand, stock and protected progress so it works from a complete
# snapshot without hidden ledger access.
@dataclass(frozen=True)
class AssignmentRequest:
    start: PlanningStart = F("共同规划起点与版本.", "Shared planning start and versions.")
    demands: tuple[Demand, ...] = F("可以新分配的订单需求.", "Demand available for new assignment.")
    stock: tuple[Stock, ...] = F("可以新预留的库存.", "Stock available for new reservation.")
    tasks: tuple[TaskProgress, ...] = F("既有任务与进度, 包括未绑定任务.", "Existing task definitions and progress, including unbound tasks.")
    queues: tuple[QueueState, ...] = F("当前完整队列及不能修改的前缀长度.", "Current complete queues and protected-prefix lengths.")
    locks: tuple[StepLock, ...] = F("不能更换执行者的动作.", "Actions whose executors cannot change.")
    budget_s: float = F("本次模块调用的墙钟预算.", "Wall-clock budget for this call.")

# 中文: 把业务动作编译为明确目标, 耗时和占用, 为 MAPF/TPG 提供同一解释, 避免各求解器重复规则.
# English: Represent compiled targets, duration and occupancy so MAPF and TPG share action semantics
# instead of reimplementing warehouse rules.
@dataclass(frozen=True)
class PhysicalAction:
    step: StepRef = F("与业务任务关联的引用, 不含商品列表.", "Link to the business task without product details.")
    kind: Literal["lift", "serve", "drop"] = F("动作类型.", "Action kind.")
    object_id: str = F("相关货架; Serve/Drop 也明确是哪一架.", "Relevant shelf, also specified for Serve/Drop.")
    target_node: str = F("必须到达的节点, 由共享编译函数解析.", "Required node, resolved by the shared compiler.")
    target_yaw_rad: float = F("动作要求的朝向.", "Required action heading.")
    duration_s: float = F("由共享模型计算并量化的耗时, 模块不得自行缩短.", "Duration derived and quantized by the shared model, not shortened by plugins.")
    resource_ids: tuple[str, ...] = F("整个动作期间占用的资源.", "Resources held throughout the action.")

# 中文: 按机器人排列续接后的剩余物理动作, 为路径阶段确定服务顺序, 避免重新执行已完成步骤.
# English: Order each robot's remaining physical actions after the splice so routing preserves
# service order without repeating completed steps.
@dataclass(frozen=True)
class RobotJobs:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    actions: tuple[PhysicalAction, ...] = F("从 join_state 开始尚需执行的有序动作.", "Ordered actions remaining after join_state.")

# 中文: 把共同起点, 编译动作和预算传给 MAPF, 使路径算法可独立替换且不自行解释订单.
# English: Pass shared start, compiled actions and budget to MAPF so routing can be replaced without
# interpreting business orders itself.
@dataclass(frozen=True)
class PathRequest:
    start: PlanningStart = F("精确续接状态与旧前缀.", "Exact splice state and old prefix.")
    jobs: tuple[RobotJobs, ...] = F("草稿任务解析成的物理动作队列.", "Physical action queues compiled from the draft.")
    budget_s: float = F("本次路径规划墙钟预算.", "Wall-clock budget for route planning.")

# 中文: 用边 ID 表达一次相邻移动, 让路径结果保留可校验的拓扑连接, 而非直接跳到任意坐标.
# English: Represent an adjacent move by edge ID so route output retains a checkable graph
# connection rather than an arbitrary coordinate jump.
@dataclass(frozen=True)
class Move:
    edge_id: str = F("相邻节点之间的边; 首个 Move 可沿这条边走完剩余部分.", "Adjacent-node edge; the first Move may traverse its remaining partial length.")
    kind: Literal["move"] = "move"

# 中文: 明确带方向的旋转动作, 避免路线省略朝向变化, 为后续真实转向耗时提供语义.
# English: Represent a signed rotation explicitly so routes retain heading changes for later
# physical timing.
@dataclass(frozen=True)
class Turn:
    angle_rad: float = F("有符号旋转角; 正数为逆时针.", "Signed turn angle; positive is counterclockwise.")
    kind: Literal["turn"] = "turn"

# 中文: 在路线中引用编译动作, 将到达目标与执行作业连接, 防止路径只搬到位置却遗漏服务.
# English: Reference a compiled action within a route so reaching a target is linked to performing
# the required warehouse operation.
@dataclass(frozen=True)
class Do:
    step: StepRef = F("执行哪个物理动作.", "Physical action to execute.")
    kind: Literal["do"] = "do"

RouteStep = Move | Turn | Do
# 中文: 表达移动, 转向和作业的顺序, 将拓扑决策交给 MAPF, 把真实时间留给 TPG.
# English: Order moves, turns and actions so MAPF owns route decisions while TPG assigns physical
# time.
@dataclass(frozen=True)
class RobotRoute:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    steps: tuple[RouteStep, ...] = F("相邻移动, 转向与作业的顺序; 不带抽象时间.", "Adjacent moves, turns and actions in order, without abstract timestamps.")

# 中文: 标识某次资源进入或清空事件, 用路线下标区分重复访问, 让先后约束指向具体通行次数.
# English: Identify a resource entry or clearance at a route step so precedence refers to a specific
# visit, including repeated visits.
@dataclass(frozen=True)
class VisitEvent:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    route_step: int = F("路线动作下标, 区分重复访问.", "Route-step index, distinguishing repeat visits.")
    resource_id: str = F("进入或清空的资源.", "Resource being entered or cleared.")
    phase: Literal["enter", "clear"] = F("按完整组合外形首次进入/最后清空该区域.", "First entry / final clearance by the full combined footprint.")

# 中文: 要求先清空资源再进入, 为跨车协调传递明确事件顺序, 避免只保留离散采样无碰撞结论.
# English: Require one clearance before another entry so cross-robot coordination preserves event
# order beyond collision-free discrete samples.
@dataclass(frozen=True)
class Precedence:
    first: VisitEvent = F("先发生的 clear 事件.", "Preceding clear event.")
    second: VisitEvent = F("后发生的 enter 事件.", "Following enter event.")

# 中文: 打包全车队路线与资源先后关系, 作为 MAPF 到 TPG 的边界, 保留请求身份及协调决策.
# English: Bundle fleet routes and resource precedence as the MAPF-to-TPG boundary, preserving
# request identity and coordination decisions.
@dataclass(frozen=True)
class FleetPlan:
    request_id: str = F("对应的规划请求.", "Associated planning request.")
    routes: tuple[RobotRoute, ...] = F("全部机器人的路线; 静止机器人可用空 steps.", "Routes for all robots; stationary robots may have no steps.")
    before: tuple[Precedence, ...] = F("必须保持的跨车通行顺序.", "Required cross-robot precedence.")

# 中文: 把已选路线与原始动作约束一起交给 TPG, 让真实定时不能改变业务含义或旧续接状态.
# English: Pass selected routes together with action constraints to TPG so physical timing preserves
# business meaning and the splice state.
@dataclass(frozen=True)
class MotionRequest:
    start: PlanningStart = F("同一轮的规划起点.", "The same round's planning start.")
    jobs: tuple[RobotJobs, ...] = F("动作定义与合法耗时.", "Action definitions and valid durations.")
    fleet_plan: FleetPlan = F("已选路线和先后关系.", "Selected routes and precedence.")
    target_end_s: float = F("希望延长到的仿真时间, 可返回其他经验证的边界.", "Desired end time; another verified boundary may be returned.")
    budget_s: float = F("本次轨迹计算墙钟预算.", "Wall-clock budget for motion planning.")

# 中文: 同时表达追加前缀和完整停车尾段, 为提交后的安全退出保留候选, 不能把目标时间当安全证明.
# English: Represent an extension and complete stopping tail so a candidate includes a stopping
# option; a requested horizon alone is not a safety proof.
@dataclass(frozen=True)
class MotionPlan:
    common_prefix: tuple[RobotSegment, ...] = F("从旧边界到新共同边界的追加运动, 覆盖全车队.", "Fleet-wide extension from the old to the new common boundary.")
    stop_tail: tuple[RobotSegment, ...] = F("从新边界出发的完整车队停车轨迹, 终点持续占用.", "Complete fleet stopping trajectories; final occupancy persists.")

# 中文: 将任务修改与运动候选绑定到请求, 供 Runtime 原子校验提交, 对象存在并不表示已接受.
# English: Bind task edits and motion to a request for atomic Runtime validation; constructing this
# object does not mean it is accepted.
@dataclass(frozen=True)
class ExecutableProposal:
    request_id: str = F("对应请求 ID; Runtime 据此复核版本.", "Request ID used for version revalidation.")
    task_delta: TaskDelta = F("与本次运动一起接受的任务修改.", "Task edits accepted together with this motion.")
    motion: MotionPlan = F("前缀和停车后缀; 没有未授权 continue_tail.", "Prefix and stop tail; no unauthorized continue tail.")

# 中文: 返回正式提交 ID 和新版本, 让调用方区分候选计算成功与账本已经原子更新.
# English: Return a committed plan ID and version so callers distinguish a computed candidate from
# an atomic ledger update.
@dataclass(frozen=True)
class Accepted:
    commit_id: str = F("已发布方案 ID.", "Published plan ID.")
    state_version: int = F("新的业务/执行版本.", "New business/execution version.")

# Execution and simulator messages.
# 中文: 把选定运动分支和已接受动作表交给执行器, 使执行只切片正式计划, 不自行重新分配.
# English: Provide the selected motion branch and accepted action table so the executor slices
# committed work instead of reallocating tasks.
@dataclass(frozen=True)
class ExecutionInput:
    state: PhysicalState = F("当前状态, 提供切片开始时间.", "Current state and slicing start time.")
    active_segments: tuple[RobotSegment, ...] = F("Runtime 选定分支的曲线, 覆盖本步或结束后保持.", "Curves of the selected branch, covering the step or holding afterward.")
    action_table: tuple[PhysicalAction, ...] = F("已接受的动作定义, 仅包含物理字段.", "Accepted action definitions with physical fields only.")

# 中文: 表示一个控制步内的精确曲线节点, 保留内部切换点, 防止端点采样改变原计划运动.
# English: Represent exact curve knots for one control step so internal switches survive slicing
# instead of being replaced by endpoint samples.
@dataclass(frozen=True)
class RobotMotion:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    knots: tuple[Knot, ...] = F("当前步两端和所有内部切换点.", "Step endpoints and every internal switch knot.")

# 中文: 把本步开始的动作及执行者传给后端, 免去后端查询订单, 明确物理执行边界.
# English: Send the starting physical action and executor to the backend so it need not query orders
# or interpret business tasks.
@dataclass(frozen=True)
class ActionStart:
    robot_id: str = F("动作执行者.", "Action executor.")
    action: PhysicalAction = F("本步开始的动作定义; 后端无须查询订单.", "Action beginning now; the backend need not query orders.")

# 中文: 统一发送全车队本步曲线和动作开始事件, 使后端按一个时间窗推进, 避免机器人时间不同步.
# English: Send fleet curves and action starts for one interval so the backend advances all robots
# on the same clock.
@dataclass(frozen=True)
class IdealControlFrame:
    from_s: float = F("这一控制步的开始时刻.", "Start of this control step.")
    to_s: float = F("结束时刻; 必须等于 from_s + sim_dt_s.", "End time; must equal from_s + sim_dt_s.")
    motion: tuple[RobotMotion, ...] = F("全体机器人当前步的曲线, 静止也发送保持曲线.", "Current-step curves for all robots, including explicit holds.")
    start_actions: tuple[ActionStart, ...] = F("恰在 from_s 开始的动作; 不能重复发送.", "Actions starting exactly at from_s; never resend.")

# 中文: 给后端一次性传入模型, 静止初态和步长, 保留初始化边界而不绑定具体模拟器实现.
# English: Pass model, stationary initial state and timestep to a backend without coupling the
# public API to a simulator implementation.
@dataclass(frozen=True)
class BackendInit:
    run_id: str = F("一次实验的 ID.", "Experiment run ID.")
    model: WorldModel = F("初始化一次的静态模型.", "Static model sent once at initialization.")
    initial_state: PhysicalState = F("time_s=0 的静止初态.", "Stationary initial state at time_s=0.")
    sim_dt_s: float = F("理想步进间隔.", "Ideal simulation step interval.")

# 中文: 把分配快照与期望规划终点合并, 为分阶段和联合求解提供同一入口, 支持整体替换.
# English: Combine the assignment snapshot and desired horizon so staged and fused solvers can share
# one replaceable entry point.
@dataclass(frozen=True)
class PlanningRequest:
    assignment: AssignmentRequest = F("完整但无隐藏对象的本轮输入.", "Complete round input without hidden runtime objects.")
    target_end_s: float = F("本轮希望延长到的时间.", "Desired extension end time.")

# Ports: implement these signatures independently. Constructors receive model/config.
# 中文: 规定订单重置与按时间发布的接口, 让需求生成可替换, 不把库存或分配职责放进订单源.
# English: Specify reset and timed release so demand generation stays replaceable and independent of
# inventory or allocation.
class OrderSource(Protocol):
    # 中文: 约定替换订单序列并重新开始发布, 支持同一实验重放, 防止上轮游标影响新一轮.
    # English: Specify replacing the order schedule and restarting release so replay does not
    # inherit a previous run's cursor.
    def reset(self, orders: tuple[Order, ...]) -> None: ...
    # 中文: 约定返回截止指定时刻的新订单, 把发布时间交给订单源, 避免调用方重复注入需求.
    # English: Specify returning newly due orders so the source owns release timing and callers do
    # not inject demand twice.
    def release(self, until_s: float) -> tuple[Order, ...]: ...

# 中文: 规定快照到任务候选的边界, 让分配算法可替换, 同时保留不修改实时账本的约束.
# English: Specify the snapshot-to-task-candidate boundary so allocators can be replaced without
# gaining live-ledger mutation rights.
class Allocator(Protocol):
    # 中文: 约定从可用需求和库存提出任务修改, 返回失败或候选, 为后续编译和原子提交保留完整决策.
    # English: Specify proposing task edits from available demand and stock so compilation and
    # atomic submission receive a complete candidate or failure.
    def allocate(self, request: AssignmentRequest) -> TaskDelta | Failure: ...

# 中文: 规定物理作业到路线的接口, 让不同 MAPF 实现共用任务语义, 不泄露上游原生对象.
# English: Specify the jobs-to-routes boundary so MAPF implementations share task semantics without
# exposing native upstream objects.
class PathPlanner(Protocol):
    # 中文: 约定按编译目标生成车队路线和先后关系, 把离散规划与连续定时分开, 支持独立算法替换.
    # English: Specify fleet routes and precedence for compiled goals so discrete routing stays
    # separate from continuous timing.
    def plan(self, request: PathRequest) -> FleetPlan | Failure: ...

# 中文: 规定路线到物理轨迹的接口, 让 TPG 适配器可替换, 并保留统一动力学及动作约束.
# English: Specify route-to-motion conversion so TPG adapters can be replaced while retaining shared
# physical and action constraints.
class MotionPlanner(Protocol):
    # 中文: 约定生成追加曲线和停车尾段候选, 供后续验证提交, 不因计算成功就赋予执行权限.
    # English: Specify an extension and stop-tail candidate for later validation, without granting
    # execution authority merely because planning succeeded.
    def prepare(self, request: MotionRequest) -> MotionPlan | Failure: ...

# 中文: 规定完整规划入口, 让分层链和联合 TAPF 可以整体替换, Runtime 无需知道内部求解顺序.
# English: Specify one planning entry point so staged solving and joint TAPF can be exchanged
# without exposing internal stages to Runtime.
class DecisionPipeline(Protocol):
    # 中文: 约定将规划快照转换为完整候选或失败, 把任务修改与运动结果一起返回, 避免只提交半套方案.
    # English: Specify a complete proposal or failure so task changes and motion are returned
    # together rather than as a partial plan.
    def solve(self, request: PlanningRequest) -> ExecutableProposal | Failure: ...

# 中文: 规定正式计划到控制帧的边界, 集中处理精确切片, 防止各后端自行解释轨迹和动作.
# English: Specify the committed-plan-to-frame boundary so exact slicing is centralized instead of
# reinterpreted by each backend.
class CentralExecutor(Protocol):
    # 中文: 约定切出下一个步长的曲线与动作, 保留切换点且不重复启动, 为后端提供明确可执行输入.
    # English: Specify the next interval's curves and action starts, preserving switches and
    # avoiding repeated starts before backend execution.
    def build_frame(self, data: ExecutionInput, dt_s: float) -> IdealControlFrame | Failure: ...

# 中文: 保留理想后端的初始化, 步进和释放接口, 为未来实现提供边界, 当前声明不代表已实现模拟器.
# English: Preserve backend initialization, stepping and cleanup ports for future implementations;
# this protocol is not a simulator implementation.
class IdealBackend(Protocol):
    # 中文: 约定装载静态模型和初态并返回观测, 建立一次运行的起点, 避免后端保留旧场景状态.
    # English: Specify loading a model and initial state and returning an observation so a new run
    # does not inherit old backend state.
    def reset(self, request: BackendInit) -> Observation | Failure: ...
    # 中文: 约定执行一个理想控制帧并返回状态与事件, 为 Runtime 提供完成依据, 不接收订单业务逻辑.
    # English: Specify advancing one control frame and returning state and events so Runtime
    # receives completion evidence without sending order logic to the backend.
    def step(self, frame: IdealControlFrame) -> Observation | Failure: ...
    # 中文: 约定释放后端运行资源, 让调用方具有统一生命周期出口, 不依赖具体后端清理方式.
    # English: Specify backend resource cleanup so callers have a common lifecycle endpoint
    # independent of implementation details.
    def close(self) -> None: ...

# 中文: 规定账本和执行分支的唯一管理入口, 将候选计算与正式提交分离, 当前只有接口声明.
# English: Specify the owner of ledgers and execution branches so candidate calculation stays
# separate from acceptance; this is currently an interface only.
class Runtime(Protocol):
    # 中文: 约定初始化模型, 配置, 观测和库存账本, 为每次实验建立独立状态, 避免跨运行遗留预留.
    # English: Specify initializing model, settings, observation and stock so each experiment starts
    # without reservations from an earlier run.
    def reset(self, model: WorldModel, config: RunConfig, initial: Observation, stock: tuple[Stock, ...]) -> None: ...
    # 中文: 约定将发布订单登记到需求账本, 明确需求进入系统的单一入口, 使规划器只读取快照.
    # English: Specify registering released orders in the demand ledger so planners consume
    # snapshots instead of creating live demand themselves.
    def add_orders(self, orders: tuple[Order, ...]) -> None: ...
    # 中文: 约定从正式状态构造规划快照, 投影旧承诺到续接点, 让求解器计算时不修改实时状态.
    # English: Specify a planning snapshot projected through existing commitments so solvers can
    # compute without mutating live state.
    def make_request(self) -> PlanningRequest: ...
    # 中文: 约定复核版本并原子接受任务和运动, 作为唯一提交边界, 防止过期或部分候选进入执行.
    # English: Specify version revalidation and atomic acceptance of tasks and motion so stale or
    # partial candidates cannot enter execution.
    def submit(self, proposal: ExecutableProposal) -> Accepted | Failure: ...
    # 中文: 约定处理到期分支切换, 使已承诺的停车选择及时生效, 避免继续依赖尚未接受的新方案.
    # English: Specify processing due branch transitions so committed stopping choices take effect
    # without relying on an unaccepted continuation.
    def process_due_branch(self) -> None: ...
    # 中文: 约定暴露当前选定分支和动作表, 为中央执行器提供已接受输入, 避免执行候选计划.
    # English: Specify exposing the selected branch and action table so the executor consumes
    # accepted work rather than a candidate plan.
    def execution_input(self) -> ExecutionInput: ...
    # 中文: 约定用后端状态和结果更新账本, 让业务进度依据执行证据推进, 防止规划阶段提前扣减需求.
    # English: Specify reconciling backend state and results so business progress follows execution
    # evidence instead of speculative planning.
    def observe(self, observation: Observation) -> None: ...

# 中文: 规定分配决策到物理动作的共享转换, 为所有求解器集中解释任务, 防止锁和耗时规则分叉.
# English: Specify shared task-to-action compilation so solvers do not diverge on locks, durations
# or warehouse action meaning.
class SharedCompiler(Protocol):
    # 中文: 约定保护既有进度和锁后编译剩余动作, 返回统一机器人作业, 让替换分配或 MAPF 不改变任务解释.
    # English: Specify compiling remaining jobs while preserving progress and locks so replacing
    # allocation or MAPF does not change task semantics.
    def compile_jobs(self, request: AssignmentRequest, draft: TaskDelta) -> tuple[RobotJobs, ...] | Failure: ...

# 中文: 规定候选与控制帧的独立检查接口, 将安全判断与求解分离, 接口存在不等于连续安全已验证.
# English: Specify independent proposal and frame checks so safety judgment stays separate from
# solving; the interface itself proves no continuous safety.
class Validator(Protocol):
    # 中文: 约定检查完整候选并汇总失败原因, 为 Runtime 提交提供独立门禁, 防止把求解成功等同安全.
    # English: Specify checking a complete proposal and returning diagnostics so Runtime has a
    # validation boundary independent of solver success.
    def check_proposal(self, request: PlanningRequest, proposal: ExecutableProposal) -> tuple[Failure, ...]: ...
    # 中文: 约定检查当前状态下的控制帧, 在执行边界复核运动与动作, 防止错误切片直接进入后端.
    # English: Specify checking a control frame against current state so invalid motion slices or
    # actions are rejected at the execution boundary.
    def check_frame(self, model: WorldModel, state: PhysicalState, frame: IdealControlFrame, dt_s: float) -> tuple[Failure, ...]: ...
