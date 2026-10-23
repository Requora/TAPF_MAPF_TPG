"""中文: 本模块定义 Warehouse API 0.7 的跨模块数据契约与接口, 不实现规划算法.
本模块仅依赖 Python 3.10+ 标准库. 字段在未提供默认值时必须由调用方传入.
冻结数据类和元组让请求保持只读; 字符串 ID 在一次运行内标识对象.
Protocol 类声明可替换模块必须提供的方法签名, 不代表对应实现已经完成.

English: This module defines Warehouse API 0.7 data contracts and interfaces, not planners.
The module uses only the Python 3.10+ standard library. Callers supply fields without defaults.
Frozen dataclasses and tuples keep requests read-only; string IDs identify objects within a run.
Protocol classes declare signatures for replaceable modules; they do not imply completed implementations.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Protocol

API_VERSION = "0.7"

# 中文: F 把双语字段说明存入 dataclass 元数据, 即数据类字段附带的描述信息.
# 代码与文档可以读取同一份描述, 无须分别维护字段含义.
# English: F stores bilingual descriptions in dataclass metadata, the descriptive information attached to each field.
# Code and documentation can read the same descriptions instead of maintaining separate definitions.
def F(zh: str, en: str):
    return field(metadata={"zh": zh, "en": en})

# 中文: Point2 保存以米为单位的二维位置, 让路网与几何计算共用坐标, 避免把网格编号当作距离.
# English: Point2 stores a metric 2D position so graph and geometry consumers share coordinates
# without treating grid indices as distances.
@dataclass(frozen=True)
class Point2:
    x_m: float = F("世界坐标 x, 米.", "World x in meters.")
    y_m: float = F("世界坐标 y, 米.", "World y in meters.")

# 中文: Pose2 同时保存位置与朝向, 让目标和轨迹区分到达节点与满足朝向要求.
# English: Pose2 stores position and heading so targets and trajectories distinguish reaching a
# node from facing the required direction.
@dataclass(frozen=True)
class Pose2:
    x_m: float = F("世界坐标 x, 米.", "World x in meters.")
    y_m: float = F("世界坐标 y, 米.", "World y in meters.")
    yaw_rad: float = F("朝向, 弧度; 连续曲线中的角度不折回 ±pi.", "Heading in radians; unwrap yaw along a trajectory.")

# 中文: Twist2 保存世界坐标系中的线速度与角速度. 规划器在旧轨迹终点接上新轨迹时, 需要保留这些速度.
# 规划器和物理约束检查器共用这个类型, 避免对同一速度采用不同单位.
# English: Twist2 stores world-frame linear and angular velocity, which planners must preserve when joining a new trajectory to an old endpoint.
# Planners and physical-limit checkers share this type so they use consistent velocity units.
@dataclass(frozen=True)
class Twist2:
    vx_mps: float = F("世界坐标系 x 方向速度, 米/秒.", "World-frame x velocity in m/s.")
    vy_mps: float = F("世界坐标系 y 方向速度, 米/秒.", "World-frame y velocity in m/s.")
    omega_radps: float = F("朝向变化率, 弧度/秒.", "Yaw rate in rad/s.")

# 中文: Knot 记录某时刻的位置, 朝向和速度. Hermite 插值用相邻两个 Knot 的这些值确定两者之间的运动曲线.
# 执行器按控制时间段截取轨迹时需要保留内部 Knot, 以免丢失加减速等运动切换点.
# English: Knot records position, heading and velocity at a time. Hermite interpolation uses two adjacent knots to determine the curve between them.
# An executor must retain internal knots when extracting a control interval so it preserves motion switches such as acceleration changes.
@dataclass(frozen=True)
class Knot:
    time_s: float = F("仿真时间, 不是 MAPF 步数.", "Simulation time, not a MAPF step.")
    pose: Pose2 = F("该时刻的参考位姿.", "Reference pose at this time.")
    velocity: Twist2 = F("该位姿参考点的时间导数.", "Time derivative at the pose reference point.")

# 中文: StepRef 用任务 ID 和从零开始的动作下标定位一个业务动作, 让规划和执行共用动作身份, 无须复制任务定义.
# English: StepRef identifies a business action by task ID and zero-based step index so planning
# and execution share action identity without copying task definitions.
@dataclass(frozen=True)
class StepRef:
    task_id: str = F("任务 ID.", "Task ID.")
    step_index: int = F("任务中的动作下标, 从 0 开始.", "Zero-based action index within the task.")

ErrorCode = Literal["NO_PLAN", "TIMEOUT", "UNSUPPORTED", "BAD_INPUT", "STALE_REQUEST", "CONFLICT", "BAD_FRAME", "BAD_ACTION", "BACKEND_ERROR"]
# 中文: Failure 携带失败码, 原因与关联 ID, 让调用方在模块之间统一区分无解, 超时和非法输入.
# English: Failure carries a code, reason and related IDs so callers distinguish infeasibility,
# timeout and invalid input consistently across modules.
@dataclass(frozen=True)
class Failure:
    code: ErrorCode = F("可供程序分支处理的错误码.", "Machine-readable failure code.")
    message: str = F("说明哪里失败, 不只写 error.", "Explain what failed, not just 'error'.")
    related_ids: tuple[str, ...] = F("相关机器人, 任务或资源 ID; 没有则空元组.", "Related robot/task/resource IDs; empty if none.")

# Static model: initialize once. No USD objects or Python callbacks in these DTOs.
# 中文: Node 为路网位置提供稳定 ID 和米制坐标, 让路线与几何计算在替换规划器后仍能引用同一位置.
# English: Node gives a graph position a stable ID and metric coordinates so routing and geometry
# retain the same position across planner replacements.
@dataclass(frozen=True)
class Node:
    id: str = F("路网节点 ID.", "Route-graph node ID.")
    position: Point2 = F("节点的世界坐标.", "Node position in the world.")

# 中文: Edge 表示两个路网节点之间的有向直线连接, 让路线明确引用合法移动; 反向行驶需要另一条边.
# English: Edge represents a directed straight connection between graph nodes so routes name legal
# moves; reverse travel requires a separate edge.
@dataclass(frozen=True)
class Edge:
    id: str = F("有向直线边 ID.反向行驶使用另一条边.", "Directed straight-edge ID. Reverse travel uses a separate edge.")
    from_node: str = F("起点节点 ID.", "Start-node ID.")
    to_node: str = F("终点节点 ID.", "End-node ID.")

# 中文: Polygon 保存机器人, 货架或障碍的轮廓, 为连续几何检查提供实际外形, 避免仅凭节点占用判断碰撞.
# English: Polygon stores robot, shelf or obstacle outlines so continuous geometry checks can use
# physical shapes instead of only node occupancy.
@dataclass(frozen=True)
class Polygon:
    vertices: tuple[Point2, ...] = F("至少三个逆时针顶点; 首版使用凸多边形.", "At least three counterclockwise vertices; convex in V0.")

# 中文: Resource 关联一个空间区域与其容量, 让协调模块表达区域共享占用, 而不只检查路线交点.
# English: Resource associates a spatial region with its capacity so coordination can express
# shared occupancy beyond route intersections.
@dataclass(frozen=True)
class Resource:
    id: str = F("需协调的路口, 边或工作站区域 ID.", "ID of a coordinated crossing, edge, or station region.")
    region: Polygon = F("该资源在世界坐标系中的区域.", "Resource region in the world frame.")
    capacity: int = F("最多同时使用的机器人数量, 至少 1.", "Maximum simultaneous users, at least one.")

# 中文: RobotSpec 保存机器人的静态外形, 与变化的位姿分开, 让规划和几何检查复用同一份模型.
# English: RobotSpec stores static robot geometry separately from changing poses so planning and
# geometry checks reuse one model.
@dataclass(frozen=True)
class RobotSpec:
    id: str = F("机器人 ID.", "Robot ID.")
    footprint: Polygon = F("车体坐标系的空载外形; x 向前, y 向左.", "Unloaded footprint in the body frame: x forward, y left.")

# 中文: ObjectSpec 保存货架外形与携带规则, 让规划区分空载穿架和机器人载货后的组合外形.
# English: ObjectSpec stores shelf geometry and carrying rules so planning distinguishes unloaded
# passage from the combined robot-and-shelf footprint.
@dataclass(frozen=True)
class ObjectSpec:
    id: str = F("货架 ID.", "Shelf ID.")
    footprint: Polygon = F("货架自身坐标系的外形.", "Footprint in the shelf frame.")
    carry_offset: Pose2 = F("载货时货架相对车体的固定变换.", "Fixed shelf pose relative to the carrying robot.")
    empty_robot_can_pass_under: bool = F("空载车能否在未携带该货架时穿过其下方.", "Whether an empty robot can pass under the grounded shelf.")

# 中文: Place 将存储位或工作站关联到节点, 朝向与占用资源, 让编译器统一解释业务位置的物理含义.
# English: Place links a storage slot or station to a node, heading and occupancy resource so the
# compiler gives business locations one physical meaning.
@dataclass(frozen=True)
class Place:
    id: str = F("存储位或工作站 ID.", "Storage-slot or station ID.")
    kind: Literal["storage", "station"] = F("位置用途.", "Place purpose.")
    node_id: str = F("关联的路网节点.", "Associated route node.")
    yaw_rad: float = F("执行取放或服务时要求的朝向.", "Required heading for handling or service.")
    resource_id: str = F("关联的占用资源 ID.", "Associated occupancy-resource ID.")

# 中文: MotionLimits 汇总速度, 加减速与转向限制, 让运动规划和验证共用物理约束, 避免不同的动力学假设.
# English: MotionLimits groups speed, acceleration, braking and turn limits so motion planning and
# validation share physical constraints and assumptions.
@dataclass(frozen=True)
class MotionLimits:
    max_speed_mps: float = F("统一的执行限速.不是上游整数速度档.", "Uniform execution speed limit, not an abstract speed level.")
    acceleration_mps2: float = F("直线加速度上限.", "Forward acceleration limit.")
    braking_mps2: float = F("直线减速度绝对值上限.", "Maximum magnitude of braking acceleration.")
    turn_90_s: float = F("完整 90 度转向的最短时间.", "Minimum duration of a complete 90-degree turn.")
    turn_180_s: float = F("完整 180 度转向的最短时间.", "Minimum duration of a complete 180-degree turn.")
    turn_270_s: float = F("指定方向 270 度转向的最短时间.", "Minimum duration of a directed 270-degree turn.")

# 中文: ActionTimes 集中保存举架, 放架与服务耗时, 让编译器和规划器共用动作时间规则.
# English: ActionTimes centralizes handling and service durations so compilers and planners share
# action timing rules.
@dataclass(frozen=True)
class ActionTimes:
    lift_s: float = F("举架固定耗时.", "Fixed lift duration.")
    drop_s: float = F("放架固定耗时.", "Fixed drop duration.")
    service_base_s: float = F("一次服务的基础耗时.", "Base duration per service action.")
    service_per_unit_s: float = F("每件商品额外服务耗时.", "Additional service time per item unit.")

# 中文: WorldModel 汇总不可变路网, 几何与物理规则, 为模块提供显式共享输入, 避免求解器依赖隐藏场景对象.
# English: WorldModel bundles immutable topology, geometry and physical rules as explicit shared
# input so solvers need no hidden scene objects.
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

# 中文: PlannerConfig 保存上游离散规划参数, 与物理限制分开, 避免规划器把整数速度档直接当作执行速度.
# English: PlannerConfig stores discrete planner settings separately from physical limits so
# planners do not mistake abstract speed levels for execution speeds.
@dataclass(frozen=True)
class PlannerConfig:
    max_speed_level: int = F("MAWPF 最大整数速度档, 示例值 2.", "Maximum abstract MAWPF level; trial value 2.")
    rotation_steps: int = F("MAWPF 的 90 度转向步数.", "Abstract steps for a 90-degree turn.")
    lookahead_steps: int = F("多步 PIBT 的窗口长度.", "Multi-step PIBT lookahead length.")
    seed: int = F("随机种子.", "Random seed.")

# 中文: RunConfig 记录实验步长, 规划预算与重规划间隔, 让运行策略可复现.
# 规划预算限制程序实际计算耗时; 仿真步长描述模型中的时间推进, 两者不能混用.
# English: RunConfig records experiment timing, planning budgets and replan intervals for reproducibility.
# The budget limits actual computation time; the simulation timestep describes time advances in the model.
@dataclass(frozen=True)
class RunConfig:
    sim_dt_s: float = F("一次 backend.step 推进的仿真秒数.", "Simulation seconds advanced by one backend.step.")
    commit_horizon_s: float = F("每次希望增加的前缀长度, 不是安全保证.", "Desired prefix extension, not a safety guarantee.")
    replan_period_s: float = F("暂停规划模式下的常规重规划间隔.", "Regular replan interval in paused-planning mode.")
    planner_budget_s: float = F("一次规划总墙钟预算.", "Wall-clock budget for one planning round.")
    seed: int = F("本轮实验随机种子.", "Experiment seed.")

# Business data.
# 中文: Item 表示一种商品的需求数量; sku 是商品种类标识, 让订单能按同类商品合并需求.
# English: Item represents demand for one product type; sku identifies that type so orders can
# combine demand for the same product.
@dataclass(frozen=True)
class Item:
    sku: str = F("商品种类 ID.", "Product-type ID.")
    quantity: int = F("正整数件数.", "Positive integer quantity.")

# 中文: Order 保存需求, 发布时间与软截止时间, 让订单源表达何时出现需求, 而由分配模块决定如何搬运货架.
# English: Order stores demand, release time and soft due time so the order source describes when
# demand appears while allocation decides shelf movement.
@dataclass(frozen=True)
class Order:
    id: str = F("订单 ID.", "Order ID.")
    released_at_s: float = F("订单进入系统的仿真时间.", "Simulation release time.")
    items: tuple[Item, ...] = F("需求清单, 同 SKU 合并.", "Requested items; merge repeated SKUs.")
    due_at_s: float | None = F("软截止; None 表示无截止.", "Soft due time; None means no due time.")

# 中文: Pick 将一次服务的数量关联到订单和商品种类, 让成功服务能更新对应需求, 而不只记录货架移动.
# English: Pick links a service quantity to its order and product type so successful service can
# update the corresponding demand rather than only record shelf movement.
@dataclass(frozen=True)
class Pick:
    order_id: str = F("被满足的订单.", "Order being fulfilled.")
    sku: str = F("商品种类.", "Product type.")
    quantity: int = F("本次服务完成的件数.", "Quantity fulfilled by this service.")

# 中文: Lift 表达要举起的货架, 由共享编译器补全物理目标与耗时, 避免每个分配器重复解释物理规则.
# English: Lift identifies the shelf to lift while the shared compiler supplies physical targets
# and duration, so allocators need not repeat physical rules.
@dataclass(frozen=True)
class Lift:
    object_id: str = F("要取的货架.", "Shelf to pick up.")
    kind: Literal["lift"] = "lift"

# 中文: Serve 表达目标工作站与待满足的需求, 将服务意图和实际执行分开, 避免计划生成就被视为订单完成.
# English: Serve describes a target station and demand to fulfill separately from execution, so a
# planned service is not treated as completed demand.
@dataclass(frozen=True)
class Serve:
    station_id: str = F("目标工作站.", "Target station.")
    picks: tuple[Pick, ...] = F("服务成功后满足哪些订单需求.", "Demand fulfilled only after service succeeds.")
    kind: Literal["serve"] = "serve"

# 中文: Drop 表达货架的归还存储位, 由编译器解析位置与资源, 让分配决策独立于具体路径规划器.
# English: Drop identifies a shelf's return slot for compiler resolution into position and
# resources, so assignment stays independent of a specific path planner.
@dataclass(frozen=True)
class Drop:
    storage_id: str = F("目标存储位.", "Target storage slot.")
    kind: Literal["drop"] = "drop"

TaskAction = Lift | Serve | Drop
# 中文: Task 用稳定 ID 组织有序业务动作, 让进度记录和执行者保护规则在重规划时仍能引用同一动作.
# English: Task groups ordered business actions under a stable ID so progress records and executor
# protections retain action identity during replanning.
@dataclass(frozen=True)
class Task:
    id: str = F("任务 ID; 同一 run 内不能复用.", "Task ID; never reused within a run.")
    steps: tuple[TaskAction, ...] = F("有序动作; V0 为 Lift, Serve, Drop.", "Ordered actions; Lift, Serve, Drop in V0.")

# 中文: RobotQueue 表达候选任务执行顺序, 为模块间的分配结果提供统一数据类型, 避免候选计算直接修改实时队列.
# English: RobotQueue represents a proposed task order as a shared allocation result type, so
# candidate computation does not directly change live queues.
@dataclass(frozen=True)
class RobotQueue:
    robot_id: str = F("执行这些任务的机器人.", "Robot assigned these tasks.")
    task_ids: tuple[str, ...] = F("任务执行顺序.", "Ordered task IDs.")

# 中文: QueueState 保存当前任务队列和不可改动的开头部分, 让求解器保留已承诺的任务顺序及机器人绑定.
# English: QueueState stores the current task queue and its protected prefix so solvers preserve
# committed task order and robot bindings.
@dataclass(frozen=True)
class QueueState:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    task_ids: tuple[str, ...] = F("当前完整任务队列.", "Current complete task queue.")
    locked_prefix_count: int = F("前多少个任务绑定不可改; 输出队列只替换这个下标之后的部分.", "Count of protected tasks at the front; a proposal replaces only the suffix after this index.")

# 中文: TaskDelta 保存本次新增的任务, 以及机器人队列中允许修改的后半部分的新内容.
# 运行协调模块 Runtime 将这些任务修改和运动方案一起接受或一起拒绝, 避免队列与运动计划不一致.
# English: TaskDelta stores new tasks and replacement content for the modifiable trailing part of robot queues.
# Runtime, the run coordinator, accepts or rejects these task edits and motion together so queues and motion plans stay consistent.
@dataclass(frozen=True)
class TaskDelta:
    tasks: tuple[Task, ...] = F("只包含本次新建任务, 不含旧任务副本.", "New task definitions only, not copies of old tasks.")
    queues: tuple[RobotQueue, ...] = F("替换所列机器人尚未固定的任务队列后缀.", "Replace the mutable queue suffix of each listed robot.")

# 中文: Demand 表示尚未完成且未被正式任务预留的需求, 让分配器选择可用数量, 避免重复分配.
# English: Demand represents unfulfilled quantities not reserved by accepted tasks so allocation
# can select available demand without assigning it twice.
@dataclass(frozen=True)
class Demand:
    order_id: str = F("订单 ID.", "Order ID.")
    sku: str = F("商品种类.", "Product type.")
    available_quantity: int = F("尚未完成且没有被正式任务预留的数量.", "Unfulfilled quantity not reserved by accepted tasks.")
    due_at_s: float | None = F("原订单软截止.", "Original order soft due time.")

# 中文: Stock 表示货架上未被正式任务预留的库存, 让新分配使用可用数量, 避免重复消耗已有预留.
# English: Stock represents shelf quantities not reserved by accepted tasks so new assignments use
# available inventory without reusing reservations.
@dataclass(frozen=True)
class Stock:
    object_id: str = F("存放商品的货架.", "Shelf containing the stock.")
    sku: str = F("商品种类.", "Product type.")
    available_quantity: int = F("尚未被正式任务预留的数量.", "Quantity not reserved by accepted tasks.")

# 中文: TaskProgress 保存按已接受运动预测到续接时刻的任务进度, 让编译器仅生成剩余动作, 不提前修改实时账本.
# English: TaskProgress stores task progress projected through accepted motion to the splice time
# so compilation emits only remaining actions without updating the live ledger early.
@dataclass(frozen=True)
class TaskProgress:
    task: Task = F("已接受且不可就地修改的任务定义.", "Accepted immutable task definition.")
    next_step: int = F("按旧承诺预测到 join_state 后, 下一未完成动作下标; 等于动作数表示完成, 不提前更新正式账本.", "Next unfinished index projected to join_state under the old commitment; the action count means predicted completion, without changing the live ledger.")
    blocked: bool = F("失败后暂停, 不能自动重试.", "Blocked after failure; no automatic retry.")

# 中文: StepLock 记录已承诺动作与不可更换的执行机器人; 这种锁保护任务归属, 即使队列保护长度为零也不能转移责任.
# English: StepLock records a committed action and its fixed robot executor; this lock protects
# task ownership even when the protected queue prefix is empty.
@dataclass(frozen=True)
class StepLock:
    step: StepRef = F("已经承诺, 必须保护的动作.", "Committed action that must be preserved.")
    robot_id: str = F("该动作不可更换的执行者.", "Executor that cannot be reassigned.")

# Physical state: business quantities never travel to the simulator.
# 中文: RobotState 记录一台机器人的位姿与速度, 供规划续接和观测使用, 避免移动状态被当作静止起点.
# English: RobotState records one robot's pose and velocity for planning splices and observation so
# a moving state is not mistaken for a stationary start.
@dataclass(frozen=True)
class RobotState:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    pose: Pose2 = F("当前理想位姿.", "Current ideal pose.")
    velocity: Twist2 = F("当前理想速度.", "Current ideal velocity.")

# 中文: ObjectState 记录货架的落地位置或携带者, 为取放前置条件检查提供依据, 让校验器能拒绝矛盾的位置状态.
# English: ObjectState records a shelf's ground pose or carrier so handling-precondition checks can
# reject contradictory location states.
@dataclass(frozen=True)
class ObjectState:
    object_id: str = F("货架 ID.", "Shelf ID.")
    ground_pose: Pose2 | None = F("在地面时的位姿; 载货时为 None.", "Ground pose; None while carried.")
    carrier_id: str | None = F("载货机器人 ID; 在地面时为 None.两字段恰有一个非空.", "Carrier ID; None on the ground. Exactly one location field is non-null.")

# 中文: RunningAction 记录未结束动作及其时间窗, 让重规划和执行保护正在进行的工作, 避免重复启动或中途替换.
# English: RunningAction records an unfinished action and its time interval so replanning and
# execution protect ongoing work from restart or replacement.
@dataclass(frozen=True)
class RunningAction:
    robot_id: str = F("正在执行动作的机器人.", "Robot executing the action.")
    step: StepRef = F("动作引用.", "Action reference.")
    started_at_s: float = F("开始时间.", "Start time.")
    ends_at_s: float = F("确定性完成时间.", "Deterministic completion time.")

# 中文: PhysicalState 保存同一仿真时刻的全部机器人, 货架与未完成动作, 为模块提供同一时刻的状态快照, 避免混用不同时刻的数据.
# English: PhysicalState stores all robots, shelves and unfinished actions at one simulation time,
# giving modules a state snapshot that avoids mixing different instants.
@dataclass(frozen=True)
class PhysicalState:
    time_s: float = F("这份状态对应的仿真时刻.", "Simulation time represented by this state.")
    robots: tuple[RobotState, ...] = F("全部机器人状态.", "All robot states.")
    objects: tuple[ObjectState, ...] = F("全部货架的位置或携带关系.", "All shelf locations or carrying relations.")
    running_actions: tuple[RunningAction, ...] = F("当前未完成动作; 没有则空元组.", "Unfinished actions; empty when none.")

# 中文: ActionResult 将成功或失败事件关联到 StepRef 指定的任务动作, 让记账依据执行结果, 而不是计划完成时间.
# English: ActionResult links success or failure to the task action identified by StepRef so
# accounting uses execution results rather than planned completion times.
@dataclass(frozen=True)
class ActionResult:
    time_s: float = F("动作结果发生的仿真时间.", "Simulation time of the result.")
    step: StepRef = F("用来更新任务及订单的动作引用.", "Action reference for task and order updates.")
    success: bool = F("是否成功.", "Whether the action succeeded.")
    reason: str = F("成功时为空字符串; 失败时说明原因.", "Empty on success; diagnostic on failure.")

# 中文: Observation 同时携带完整物理状态和本步新增结果, 让 Runtime 分别核对持续状态与只需处理一次的动作结果.
# English: Observation carries full physical state and newly produced results so Runtime can
# reconcile ongoing state separately from one-time action results.
@dataclass(frozen=True)
class Observation:
    state: PhysicalState = F("本步完成后的完整理想状态.", "Full ideal state after the step.")
    events: tuple[ActionResult, ...] = F("本步新增结果, 按时间和动作引用排序.", "New results in this step, sorted by time and action reference.")

# Shared planning start; every field is visible, rather than hidden behind a View.
# 中文: TimedAction 为 StepRef 指定的任务动作记录精确开始时刻, 让运动层保留动作身份, 无须复制业务定义.
# English: TimedAction records an exact start time for the task action identified by StepRef so
# motion retains action identity without copying business definitions.
@dataclass(frozen=True)
class TimedAction:
    start_s: float = F("开始执行动作的精确仿真时间.", "Exact action start time.")
    step: StepRef = F("动作定义从统一动作表查询.", "Look up the definition in the shared action table.")

# 中文: RobotSegment 合并一台机器人的连续曲线和动作开始时刻, 让执行器切片时保持移动与作业时间一致.
# English: RobotSegment bundles one robot's continuous curve and action starts so executor slicing
# keeps motion and service timing consistent.
@dataclass(frozen=True)
class RobotSegment:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    knots: tuple[Knot, ...] = F("按时间递增的曲线节点.", "Knots in strictly increasing time order.")
    actions: tuple[TimedAction, ...] = F("这段运动内开始的动作.", "Actions starting in this segment.")

# 中文: PlanningStart 提供版本, 不可改动的旧轨迹和旧轨迹结束时的预测状态, 让各求解阶段从同一续接点开始, 不覆盖已接受运动.
# English: PlanningStart supplies versions, immutable old motion and its predicted end state so
# each solving stage starts at the same splice without overwriting accepted motion.
@dataclass(frozen=True)
class PlanningStart:
    request_id: str = F("本轮请求 ID; 整个分层或联合求解共用.", "Round ID shared by staged or fused solving.")
    state_version: int = F("任务/预留/已接受运动版本, 不是每步位置版本.", "Task/reservation/accepted-plan version, not a per-tick pose version.")
    now_s: float = F("发起规划的当前仿真时间.", "Current simulation time when planning is requested.")
    join_state: PhysicalState = F("旧前缀结束时的精确预测状态.time_s 就是续接时刻.", "Exact state predicted at the end of the old prefix; time_s is the splice time.")
    fixed_prefix: tuple[RobotSegment, ...] = F("当前至续接时刻不可修改的轨迹; 包含未完成动作引用.", "Immutable motion from now to the splice, including references to unfinished actions.")
    submit_before_s: float = F("必须严格早于此时刻接受新方案.", "New plans must be accepted strictly before this time.")

# 中文: AssignmentRequest 汇总可分配需求, 库存与受保护进度, 为分配器提供本轮只读快照, 避免算法读取或修改隐藏账本.
# English: AssignmentRequest bundles available demand, stock and protected progress as a read-only
# snapshot for one allocation round, avoiding hidden ledger reads or writes.
@dataclass(frozen=True)
class AssignmentRequest:
    start: PlanningStart = F("共同规划起点与版本.", "Shared planning start and versions.")
    demands: tuple[Demand, ...] = F("可以新分配的订单需求.", "Demand available for new assignment.")
    stock: tuple[Stock, ...] = F("可以新预留的库存.", "Stock available for new reservation.")
    tasks: tuple[TaskProgress, ...] = F("既有任务与进度, 包括未绑定任务.", "Existing task definitions and progress, including unbound tasks.")
    queues: tuple[QueueState, ...] = F("当前完整队列及不能修改的前缀长度.", "Current complete queues and protected-prefix lengths.")
    locks: tuple[StepLock, ...] = F("不能更换执行者的动作.", "Actions whose executors cannot change.")
    budget_s: float = F("本次模块调用的墙钟预算.", "Wall-clock budget for this call.")

# 中文: PhysicalAction 保存共享编译器输出的动作位置, 朝向, 耗时与占用资源, 让路径规划和轨迹定时共用业务动作的物理含义.
# English: PhysicalAction stores action position, heading, duration and occupied resources from the
# shared compiler so routing and trajectory timing share the same physical action meaning.
@dataclass(frozen=True)
class PhysicalAction:
    step: StepRef = F("与业务任务关联的引用, 不含商品列表.", "Link to the business task without product details.")
    kind: Literal["lift", "serve", "drop"] = F("动作类型.", "Action kind.")
    object_id: str = F("相关货架; Serve/Drop 也明确是哪一架.", "Relevant shelf, also specified for Serve/Drop.")
    target_node: str = F("必须到达的节点, 由共享编译函数解析.", "Required node, resolved by the shared compiler.")
    target_yaw_rad: float = F("动作要求的朝向.", "Required action heading.")
    duration_s: float = F("由共享模型计算并量化的耗时, 模块不得自行缩短.", "Duration derived and quantized by the shared model, not shortened by plugins.")
    resource_ids: tuple[str, ...] = F("整个动作期间占用的资源.", "Resources held throughout the action.")

# 中文: RobotJobs 保存一台机器人在续接时刻后尚需执行的有序物理动作, 让路径规划保留服务顺序, 避免重做已完成动作.
# English: RobotJobs stores one robot's ordered physical actions remaining after the splice so
# routing preserves service order without repeating completed actions.
@dataclass(frozen=True)
class RobotJobs:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    actions: tuple[PhysicalAction, ...] = F("从 join_state 开始尚需执行的有序动作.", "Ordered actions remaining after join_state.")

# 中文: PathRequest 将共同起点, 编译后的动作和预算交给多机器人路径规划器 MAPF, 让路径算法独立替换且无须解释订单.
# English: PathRequest passes the shared start, compiled actions and budget to multi-agent path
# finding (MAPF), so routing remains replaceable without interpreting orders.
@dataclass(frozen=True)
class PathRequest:
    start: PlanningStart = F("精确续接状态与旧前缀.", "Exact splice state and old prefix.")
    jobs: tuple[RobotJobs, ...] = F("草稿任务解析成的物理动作队列.", "Physical action queues compiled from the draft.")
    budget_s: float = F("本次路径规划墙钟预算.", "Wall-clock budget for route planning.")

# 中文: Move 用边 ID 表达一次相邻移动, 让路径保留可校验的路网连接, 避免任意坐标跳转.
# English: Move represents an adjacent move by edge ID so routes retain a checkable graph
# connection instead of an arbitrary coordinate jump.
@dataclass(frozen=True)
class Move:
    edge_id: str = F("相邻节点之间的边; 首个 Move 可沿这条边走完剩余部分.", "Adjacent-node edge; the first Move may traverse its remaining partial length.")
    kind: Literal["move"] = "move"

# 中文: Turn 明确记录旋转方向与角度, 让路线保留朝向变化, 为后续计算实际转向耗时提供依据.
# English: Turn records rotation direction and angle so routes preserve heading changes needed to
# calculate physical turn duration.
@dataclass(frozen=True)
class Turn:
    angle_rad: float = F("有符号旋转角; 正数为逆时针.", "Signed turn angle; positive is counterclockwise.")
    kind: Literal["turn"] = "turn"

# 中文: Do 在路线中引用共享编译器生成的物理动作, 将到达目标与执行作业连接, 避免路线遗漏服务.
# English: Do references a physical action from the shared compiler within a route so reaching a
# target remains linked to performing the required operation.
@dataclass(frozen=True)
class Do:
    step: StepRef = F("执行哪个物理动作.", "Physical action to execute.")
    kind: Literal["do"] = "do"

RouteStep = Move | Turn | Do
# 中文: RobotRoute 记录移动, 转向与作业的顺序, 让 MAPF 决定路线, 让负责轨迹定时的 TPG 适配器分配实际时间.
# English: RobotRoute records moves, turns and actions in order so MAPF decides routes and the TPG
# trajectory-timing adapter assigns physical time.
@dataclass(frozen=True)
class RobotRoute:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    steps: tuple[RouteStep, ...] = F("相邻移动, 转向与作业的顺序; 不带抽象时间.", "Adjacent moves, turns and actions in order, without abstract timestamps.")

# 中文: VisitEvent 标识一次资源进入或清空事件, 用路线动作下标区分重复访问, 让先后约束指向具体通行次数.
# English: VisitEvent identifies a resource entry or clearance by route-step index so precedence
# constraints refer to a specific visit, including repeat visits.
@dataclass(frozen=True)
class VisitEvent:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    route_step: int = F("路线动作下标, 区分重复访问.", "Route-step index, distinguishing repeat visits.")
    resource_id: str = F("进入或清空的资源.", "Resource being entered or cleared.")
    phase: Literal["enter", "clear"] = F("按完整组合外形首次进入/最后清空该区域.", "First entry / final clearance by the full combined footprint.")

# 中文: Precedence 约束一个机器人清空资源后另一个才能进入, 为跨车协调保留明确事件顺序, 避免仅依赖离散采样无碰撞的结论.
# English: Precedence requires one robot to clear a resource before another enters, preserving
# explicit coordination order beyond collision-free discrete samples.
@dataclass(frozen=True)
class Precedence:
    first: VisitEvent = F("先发生的 clear 事件.", "Preceding clear event.")
    second: VisitEvent = F("后发生的 enter 事件.", "Following enter event.")

# 中文: FleetPlan 打包全车队路线与资源先后关系, 为 MAPF 到 TPG 的数据传递保留请求身份和协调决策.
# English: FleetPlan bundles fleet routes and resource precedence for transfer from MAPF to TPG,
# preserving request identity and coordination decisions.
@dataclass(frozen=True)
class FleetPlan:
    request_id: str = F("对应的规划请求.", "Associated planning request.")
    routes: tuple[RobotRoute, ...] = F("全部机器人的路线; 静止机器人可用空 steps.", "Routes for all robots; stationary robots may have no steps.")
    before: tuple[Precedence, ...] = F("必须保持的跨车通行顺序.", "Required cross-robot precedence.")

# 中文: MotionRequest 将已选路线, 原始动作约束与续接状态交给 TPG, 让轨迹定时保留业务含义和已确定的起点.
# English: MotionRequest passes selected routes, original action constraints and splice state to
# TPG so trajectory timing preserves business meaning and the agreed start.
@dataclass(frozen=True)
class MotionRequest:
    start: PlanningStart = F("同一轮的规划起点.", "The same round's planning start.")
    jobs: tuple[RobotJobs, ...] = F("动作定义与合法耗时.", "Action definitions and valid durations.")
    fleet_plan: FleetPlan = F("已选路线和先后关系.", "Selected routes and precedence.")
    target_end_s: float = F("希望延长到的仿真时间, 可返回其他经验证的边界.", "Desired end time; another verified boundary may be returned.")
    budget_s: float = F("本次轨迹计算墙钟预算.", "Wall-clock budget for motion planning.")

# 中文: MotionPlan 同时保存新增运动和从其终点开始的完整停车轨迹, 为候选提供停车尾段; 目标时限本身不能证明安全.
# English: MotionPlan stores a motion extension and complete stopping trajectories from its
# endpoint, providing a stop tail; the requested horizon alone proves no safety.
@dataclass(frozen=True)
class MotionPlan:
    common_prefix: tuple[RobotSegment, ...] = F("从旧边界到新共同边界的追加运动, 覆盖全车队.", "Fleet-wide extension from the old to the new common boundary.")
    stop_tail: tuple[RobotSegment, ...] = F("从新边界出发的完整车队停车轨迹, 终点持续占用.", "Complete fleet stopping trajectories; final occupancy persists.")

# 中文: ExecutableProposal 将任务修改与运动候选关联到同一请求, 供 Runtime 一起校验和提交; 对象存在不表示候选已被接受.
# English: ExecutableProposal binds task edits and motion to one request for joint Runtime
# validation and submission; its existence does not mean acceptance.
@dataclass(frozen=True)
class ExecutableProposal:
    request_id: str = F("对应请求 ID; Runtime 据此复核版本.", "Request ID used for version revalidation.")
    task_delta: TaskDelta = F("与本次运动一起接受的任务修改.", "Task edits accepted together with this motion.")
    motion: MotionPlan = F("前缀和停车后缀; 没有未授权 continue_tail.", "Prefix and stop tail; no unauthorized continue tail.")

# 中文: Accepted 携带正式提交 ID 和新状态版本, 让调用方区分候选计算成功与账本已经完整更新.
# English: Accepted carries the committed plan ID and new state version so callers distinguish a
# computed candidate from a complete ledger update.
@dataclass(frozen=True)
class Accepted:
    commit_id: str = F("已发布方案 ID.", "Published plan ID.")
    state_version: int = F("新的业务/执行版本.", "New business/execution version.")

# Execution and simulator messages.
# 中文: ExecutionInput 将选定运动分支和已接受动作表交给执行器, 让执行器仅切片正式计划, 无须重新分配任务.
# English: ExecutionInput supplies the selected motion branch and accepted action table so the
# executor slices committed plans without reallocating tasks.
@dataclass(frozen=True)
class ExecutionInput:
    state: PhysicalState = F("当前状态, 提供切片开始时间.", "Current state and slicing start time.")
    active_segments: tuple[RobotSegment, ...] = F("Runtime 选定分支的曲线, 覆盖本步或结束后保持.", "Curves of the selected branch, covering the step or holding afterward.")
    action_table: tuple[PhysicalAction, ...] = F("已接受的动作定义, 仅包含物理字段.", "Accepted action definitions with physical fields only.")

# 中文: RobotMotion 保存一个控制步内的精确曲线节点, 让内部切换点保留在执行数据中, 避免端点采样改变原运动.
# English: RobotMotion stores exact curve knots for one control step so internal switches remain in
# execution data instead of being replaced by endpoint samples.
@dataclass(frozen=True)
class RobotMotion:
    robot_id: str = F("机器人 ID.", "Robot ID.")
    knots: tuple[Knot, ...] = F("当前步两端和所有内部切换点.", "Step endpoints and every internal switch knot.")

# 中文: ActionStart 将本步开始的物理动作与执行机器人传给后端, 让后端无须查询订单或解释业务任务.
# English: ActionStart sends the physical action starting in this step and its robot executor to
# the backend, which need not query orders or interpret business tasks.
@dataclass(frozen=True)
class ActionStart:
    robot_id: str = F("动作执行者.", "Action executor.")
    action: PhysicalAction = F("本步开始的动作定义; 后端无须查询订单.", "Action beginning now; the backend need not query orders.")

# 中文: IdealControlFrame 汇总全车队本步曲线和动作开始事件, 让后端按同一时间窗推进所有机器人, 避免时间不同步.
# English: IdealControlFrame groups fleet curves and action starts for one interval so the backend
# advances all robots on the same clock.
@dataclass(frozen=True)
class IdealControlFrame:
    from_s: float = F("这一控制步的开始时刻.", "Start of this control step.")
    to_s: float = F("结束时刻; 必须等于 from_s + sim_dt_s.", "End time; must equal from_s + sim_dt_s.")
    motion: tuple[RobotMotion, ...] = F("全体机器人当前步的曲线, 静止也发送保持曲线.", "Current-step curves for all robots, including explicit holds.")
    start_actions: tuple[ActionStart, ...] = F("恰在 from_s 开始的动作; 不能重复发送.", "Actions starting exactly at from_s; never resend.")

# 中文: BackendInit 携带静态模型, 静止初态与步长, 为未来后端保留初始化输入边界, 避免接口绑定具体模拟器.
# English: BackendInit carries the static model, stationary initial state and timestep as
# initialization input for a future backend, without binding the API to a simulator.
@dataclass(frozen=True)
class BackendInit:
    run_id: str = F("一次实验的 ID.", "Experiment run ID.")
    model: WorldModel = F("初始化一次的静态模型.", "Static model sent once at initialization.")
    initial_state: PhysicalState = F("time_s=0 的静止初态.", "Stationary initial state at time_s=0.")
    sim_dt_s: float = F("理想步进间隔.", "Ideal simulation step interval.")

# 中文: PlanningRequest 合并分配输入快照与期望规划终点, 让分阶段和联合求解器共用可整体替换的入口.
# English: PlanningRequest combines the allocation input snapshot and desired horizon so staged and
# joint solvers share one replaceable entry point.
@dataclass(frozen=True)
class PlanningRequest:
    assignment: AssignmentRequest = F("完整但无隐藏对象的本轮输入.", "Complete round input without hidden runtime objects.")
    target_end_s: float = F("本轮希望延长到的时间.", "Desired extension end time.")

# Ports: implement these signatures independently. Constructors receive model/config.
# 中文: OrderSource 声明订单重置与按时间发布的方法签名, 让需求生成可替换, 并与库存和分配职责分开.
# English: OrderSource declares reset and timed-release signatures so demand generation remains
# replaceable and separate from inventory and allocation.
class OrderSource(Protocol):
    # 中文: OrderSource.reset 约定替换订单序列并重新开始发布, 让实验重放不继承上一轮的发布游标.
    # English: OrderSource.reset specifies replacing the order schedule and restarting release so
    # experiment replay does not inherit the previous run's release cursor.
    def reset(self, orders: tuple[Order, ...]) -> None: ...
    # 中文: OrderSource.release 约定返回截止指定时刻的新订单, 让订单源管理发布时间, 避免调用方重复注入需求.
    # English: OrderSource.release specifies returning newly due orders through a given time so the
    # source owns release timing and callers do not inject demand twice.
    def release(self, until_s: float) -> tuple[Order, ...]: ...

# 中文: Allocator 声明只读分配快照到任务候选的接口, 让分配算法可替换, 同时保留不得修改实时账本的约束.
# English: Allocator declares the read-only allocation-snapshot-to-task-candidate interface so
# allocators remain replaceable without gaining live-ledger mutation rights.
class Allocator(Protocol):
    # 中文: Allocator.allocate 约定从可用需求与库存提出任务修改, 让后续编译和原子提交收到完整候选或明确失败.
    # English: Allocator.allocate specifies task edits from available demand and stock so
    # compilation and atomic submission receive a complete candidate or explicit failure.
    def allocate(self, request: AssignmentRequest) -> TaskDelta | Failure: ...

# 中文: PathPlanner 声明物理作业到路线的接口, 让不同 MAPF 实现共用任务含义, 避免上游原生对象进入模块间接口.
# English: PathPlanner declares the jobs-to-routes interface so MAPF implementations share task
# meaning without exposing native upstream objects across modules.
class PathPlanner(Protocol):
    # 中文: PathPlanner.plan 约定根据编译器输出的动作目标生成车队路线与先后关系, 让离散路线和连续定时可独立替换.
    # English: PathPlanner.plan specifies fleet routes and precedence for action targets from the
    # compiler so discrete routing and continuous timing remain independently replaceable.
    def plan(self, request: PathRequest) -> FleetPlan | Failure: ...

# 中文: MotionPlanner 声明路线到物理轨迹的接口, 让 TPG 适配器可替换, 同时保留统一运动限制和动作约束.
# English: MotionPlanner declares the route-to-motion interface so TPG adapters remain replaceable
# while retaining shared motion limits and action constraints.
class MotionPlanner(Protocol):
    # 中文: MotionPlanner.prepare 约定生成新增运动和完整停车尾段候选, 供后续验证与提交; 计算成功本身不赋予执行权限.
    # English: MotionPlanner.prepare specifies a motion extension and complete stop-tail candidate
    # for later validation and submission; planning success grants no execution authority.
    def prepare(self, request: MotionRequest) -> MotionPlan | Failure: ...

# 中文: DecisionPipeline 声明完整规划入口, 让分阶段求解与联合任务分配和路径规划 TAPF 可以整体替换, Runtime 无须了解内部顺序.
# English: DecisionPipeline declares a complete planning entry point so staged solving and joint
# task assignment and path finding (TAPF) can be exchanged without exposing internal order
# to Runtime.
class DecisionPipeline(Protocol):
    # 中文: DecisionPipeline.solve 约定将规划快照转换为完整候选或失败, 让任务修改与运动一起返回, 避免提交不完整方案.
    # English: DecisionPipeline.solve specifies a complete proposal or failure from a planning
    # snapshot so task edits and motion return together instead of forming a partial
    # submission.
    def solve(self, request: PlanningRequest) -> ExecutableProposal | Failure: ...

# 中文: CentralExecutor 声明正式计划到控制帧的接口, 集中约定精确切片职责, 避免各后端分别解释轨迹与动作.
# English: CentralExecutor declares the committed-plan-to-control-frame interface, centralizing
# exact slicing responsibility so backends need not reinterpret trajectories and actions.
class CentralExecutor(Protocol):
    # 中文: CentralExecutor.build_frame 约定切出下一步的曲线与动作开始事件, 让后端获得保留内部切换点且不重复启动动作的输入.
    # English: CentralExecutor.build_frame specifies the next step's curves and action starts so
    # backend input preserves internal switches and does not restart actions.
    def build_frame(self, data: ExecutionInput, dt_s: float) -> IdealControlFrame | Failure: ...

# 中文: IdealBackend 声明理想后端的初始化, 步进与释放接口, 为未来实现保留边界; 此声明不代表模拟器已实现.
# English: IdealBackend declares ideal backend initialization, stepping and cleanup interfaces for
# future implementations; this declaration is not a simulator implementation.
class IdealBackend(Protocol):
    # 中文: IdealBackend.reset 约定装载模型与初态并返回观测, 让新运行从独立状态开始, 避免继承后端旧场景.
    # English: IdealBackend.reset specifies loading a model and initial state and returning an
    # observation so a new run starts without old backend scene state.
    def reset(self, request: BackendInit) -> Observation | Failure: ...
    # 中文: IdealBackend.step 约定执行一个控制帧并返回状态和事件, 让 Runtime 获得完成依据, 无须向后端传入订单逻辑.
    # English: IdealBackend.step specifies executing one control frame and returning state and
    # events so Runtime receives completion evidence without sending order logic to the
    # backend.
    def step(self, frame: IdealControlFrame) -> Observation | Failure: ...
    # 中文: IdealBackend.close 约定释放后端运行资源, 为调用方提供统一生命周期出口, 避免依赖具体清理方式.
    # English: IdealBackend.close specifies releasing backend resources so callers have a common
    # lifecycle endpoint independent of the cleanup implementation.
    def close(self) -> None: ...

# 中文: Runtime 声明运行协调模块的接口. 该模块应统一管理库存, 需求和任务进度等账本,
# 并选择机器人继续运动或停车的已接受方案, 让候选计算与正式提交分开. 此处仅声明接口, 没有实现协调逻辑.
# English: Runtime declares the run coordinator's interface. The coordinator must manage inventory, demand and task-progress records
# and select accepted continuation or stopping plans, keeping candidate calculation separate from acceptance.
# This declaration does not implement the coordination logic.
class Runtime(Protocol):
    # 中文: Runtime.reset 约定初始化模型, 配置, 观测与库存账本, 让每次实验建立独立状态, 避免沿用上一轮预留.
    # English: Runtime.reset specifies initializing the model, configuration, observation and stock
    # ledger so each experiment starts without reservations from an earlier run.
    def reset(self, model: WorldModel, config: RunConfig, initial: Observation, stock: tuple[Stock, ...]) -> None: ...
    # 中文: Runtime.add_orders 约定将已发布订单登记到需求账本, 让需求通过单一入口进入系统, 而规划器只读取快照.
    # English: Runtime.add_orders specifies registering released orders in the demand ledger so
    # demand enters through one boundary and planners only read snapshots.
    def add_orders(self, orders: tuple[Order, ...]) -> None: ...
    # 中文: Runtime.make_request 约定从正式状态构造只读规划输入, 按已接受运动预测到续接点, 让求解器计算时不修改实时状态.
    # English: Runtime.make_request specifies read-only planning input projected through accepted
    # motion to the splice so solvers can compute without changing live state.
    def make_request(self) -> PlanningRequest: ...
    # 中文: Runtime.submit 约定复核版本并一起接受任务与运动, 作为唯一提交入口, 避免过期或不完整候选进入执行.
    # English: Runtime.submit specifies version revalidation and joint acceptance of tasks and
    # motion as the sole submission boundary, preventing stale or partial candidates from
    # entering execution.
    def submit(self, proposal: ExecutableProposal) -> Accepted | Failure: ...
    # 中文: Runtime.process_due_branch 约定处理到期运动分支切换, 让已承诺停车方案及时生效, 避免依赖尚未接受的继续运动方案.
    # English: Runtime.process_due_branch specifies due motion-branch transitions so committed
    # stopping plans take effect without relying on an unaccepted continuation.
    def process_due_branch(self) -> None: ...
    # 中文: Runtime.execution_input 约定返回当前选定运动分支与动作表, 让中央执行器只处理已接受输入, 避免执行候选计划.
    # English: Runtime.execution_input specifies returning the selected motion branch and action
    # table so the central executor processes accepted input rather than candidate plans.
    def execution_input(self) -> ExecutionInput: ...
    # 中文: Runtime.observe 约定用后端状态与动作结果更新账本, 让业务进度依据执行证据推进, 避免规划阶段提前扣减需求.
    # English: Runtime.observe specifies updating ledgers from backend state and action results so
    # business progress follows execution evidence without reducing demand during
    # planning.
    def observe(self, observation: Observation) -> None: ...

# 中文: SharedCompiler 声明分配决策到物理动作的共享转换接口, 为求解器统一解释任务, 避免执行者保护与耗时规则出现分歧.
# English: SharedCompiler declares shared assignment-to-physical-action conversion so solvers
# interpret tasks consistently without diverging on executor protections or duration
# rules.
class SharedCompiler(Protocol):
    # 中文: SharedCompiler.compile_jobs 约定按既有进度与动作执行者保护规则编译剩余作业, 让分配器或 MAPF 的替换不改变任务含义.
    # English: SharedCompiler.compile_jobs specifies compiling remaining jobs under existing
    # progress and action-executor protections so replacing allocation or MAPF does not
    # change task meaning.
    def compile_jobs(self, request: AssignmentRequest, draft: TaskDelta) -> tuple[RobotJobs, ...] | Failure: ...

# 中文: Validator 声明候选与控制帧的独立检查接口, 让安全判断与求解分开; 接口存在不代表连续安全已通过验证.
# English: Validator declares independent proposal and control-frame checks so safety judgment
# stays separate from solving; the interface's existence proves no continuous safety.
class Validator(Protocol):
    # 中文: Validator.check_proposal 约定检查完整候选并返回失败原因, 为 Runtime 提交提供独立检查入口, 避免将求解成功等同安全.
    # English: Validator.check_proposal specifies checking a complete proposal and returning
    # failures so Runtime submission has an independent validation boundary beyond solver
    # success.
    def check_proposal(self, request: PlanningRequest, proposal: ExecutableProposal) -> tuple[Failure, ...]: ...
    # 中文: Validator.check_frame 约定根据当前状态检查控制帧的运动与动作, 让执行边界能拒绝错误切片, 避免其直接进入后端.
    # English: Validator.check_frame specifies checking frame motion and actions against current
    # state so the execution boundary can reject invalid slices before they reach the
    # backend.
    def check_frame(self, model: WorldModel, state: PhysicalState, frame: IdealControlFrame, dt_s: float) -> tuple[Failure, ...]: ...
