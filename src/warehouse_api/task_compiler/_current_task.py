"""中文: 该模块将当前任务及分给空闲机器人的新任务编译为执行动作, 使后续规划器保留已有工作进度.

English: This module compiles current tasks and new tasks assigned to idle robots into actions so downstream planners preserve existing work progress.
"""
from . import _validation as validation
from warehouse_api.contracts import (
    AssignmentRequest, Failure, Lift, PhysicalAction, Place, Pose2, RobotJobs,
    Serve, StepRef, TaskAction, TaskDelta, TaskProgress, WorldModel,
)
from warehouse_api.action_timing import action_duration_s


# 中文: CurrentTaskCompiler 将每台机器人的一个当前或新任务转换为执行动作的位置, 耗时和资源需求.
# 该类保留已接受的进度和执行归属, 为后续规划提供统一输入; 该类不承担安全验收.
# English: CurrentTaskCompiler converts one current or new task per robot into action targets, durations
# and resource requirements, preserving accepted progress and ownership to supply consistent planner
# input; the class does not perform safety acceptance.
class CurrentTaskCompiler:
    """CurrentTaskCompiler implements SharedCompiler for one Lift/Serve/Drop task per robot.

    Contract shape and timing errors raise without interception. Semantic
    failures return Failure. This compiler does not validate executable safety.
    """

    # 中文: CurrentTaskCompiler.__init__ 调用模型校验并建立节点和作业位置索引, 在输入入口集中准备静态查找, 避免每个动作重复解析场景.
    # English: CurrentTaskCompiler.__init__ validates the model and builds node and work-location indexes
    # at the input boundary so each action can resolve static targets without reparsing the scene.
    def __init__(self, model: WorldModel, *, sim_dt_s: float):
        validation.validate_model(model, sim_dt_s)
        self.model = model
        self.sim_dt_s = sim_dt_s
        self.nodes = {node.id: node for node in model.nodes}
        self.places = {place.id: place for place in model.places}

    # 中文: compile_jobs 校验已接受状态和建议任务绑定后, 只编译尚未完成的动作, 并保留 StepRef 中的任务标识和步骤索引,
    # 使重规划不会重复执行或改变已锁定的机器人责任.
    # English: compile_jobs validates accepted state and proposed task bindings, then compiles only
    # unfinished actions while retaining each StepRef task identifier and step index so replanning cannot
    # repeat work or change a locked robot assignment.
    def compile_jobs(
        self, request: AssignmentRequest, draft: TaskDelta,
    ) -> tuple[RobotJobs, ...] | Failure:
        failure = validation.validate_request(self.model, request, draft)
        if failure is not None:
            return failure
        failure = validation.validate_candidate_bindings(self.model, request, draft)
        if failure is not None:
            return failure
        state = request.start.join_state
        objects = {obj.id: obj for obj in self.model.objects}
        locations = {obj.object_id: obj for obj in state.objects}
        carried = {obj.carrier_id: obj.object_id for obj in state.objects
                   if obj.carrier_id is not None}
        tasks = {progress.task.id: progress for progress in request.tasks}
        owners = {task_id: queue.robot_id for queue in request.queues
                  for task_id in queue.task_ids}
        # 中文: compile_jobs 只在局部任务和归属映射中叠加新任务, 使原请求及已接受任务进度保持不变.
        # English: compile_jobs overlays new tasks only in local task/owner maps, preserving the request and accepted progress.
        tasks.update((task.id, TaskProgress(task, 0, False)) for task in draft.tasks)
        owners.update((task_id, queue.robot_id) for queue in draft.queues
                      for task_id in queue.task_ids)
        jobs = {robot.id: RobotJobs(robot.id, ()) for robot in self.model.robots}
        claimed: set[str] = set()
        for task_id, robot_id in owners.items():
            progress = tasks[task_id]
            if progress.next_step == len(progress.task.steps):
                continue
            failure = validation.validate_current_task(
                progress, robot_id, objects, locations, carried, claimed,
            )
            if failure is not None:
                return failure
            steps = progress.task.steps
            shelf = steps[0].object_id
            claimed.add(shelf)
            actions = []
            # 中文: next_step 表示新方案接入时刻预计尚未完成的第一步; compile_jobs 从此处编译, 避免重复推进任务进度.
            # English: next_step identifies the first unfinished step at the plan join; compile_jobs starts there to avoid advancing progress twice.
            for index in range(progress.next_step, len(steps)):
                step = steps[index]
                target = self._target(step, locations[shelf].ground_pose)
                if isinstance(target, Failure):
                    return target
                actions.append(PhysicalAction(
                    StepRef(task_id, index), step.kind, shelf, target.node_id,
                    target.yaw_rad,
                    action_duration_s(step, self.model.action_times, sim_dt_s=self.sim_dt_s),
                    (target.resource_id,),
                ))
            jobs[robot_id] = RobotJobs(robot_id, tuple(actions))
        failure = validation.validate_carried_jobs(jobs, carried)
        if failure is not None:
            return failure
        return tuple(jobs.values())

    # 中文: _target 将 Lift 抬架动作的货架落地位姿, 或 Serve 服务及 Drop 放架动作的目标标识解析为 Place 作业位置,
    # 使下游规划器统一使用该位置的地图节点和朝向.
    # English: _target resolves a Lift shelf-raising action's grounded shelf pose or a Serve service/Drop
    # shelf-lowering target identifier to a Place work location so downstream planners use the same map
    # node and heading.
    def _target(self, step: TaskAction, ground_pose: Pose2 | None) -> Place | Failure:
        if isinstance(step, Lift):
            matches = [place for place in self.model.places
                       if place.kind == "storage"
                       and Pose2(self.nodes[place.node_id].position.x_m,
                                 self.nodes[place.node_id].position.y_m,
                                 place.yaw_rad) == ground_pose]
            failure = validation.validate_lift_target(step, matches)
            if failure is not None:
                return failure
            return matches[0]
        place_id = step.station_id if isinstance(step, Serve) else step.storage_id
        kind = "station" if isinstance(step, Serve) else "storage"
        failure = validation.validate_place(self.places.get(place_id), place_id, kind)
        if failure is not None:
            return failure
        return self.places[place_id]
