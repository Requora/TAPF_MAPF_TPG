"""Input and business checks for the current-task compiler subset."""
from warehouse_api.codec import from_data, to_data
from warehouse_api.contracts import (
    AssignmentRequest, Drop, Failure, Lift, ObjectSpec, ObjectState, Place,
    Pose2, RobotJobs, Serve, TaskDelta, TaskProgress, WorldModel,
)
from warehouse_api.durations import action_duration_s


def validate_model(model: WorldModel, sim_dt_s: float) -> None:
    from_data(WorldModel, to_data(model))
    action_duration_s(Lift("timing-check"), model.action_times, sim_dt_s=sim_dt_s)
    for name, entries in (
        ("nodes", model.nodes), ("resources", model.resources),
        ("robots", model.robots), ("objects", model.objects), ("places", model.places),
    ):
        if len({entry.id for entry in entries}) != len(entries):
            raise ValueError(f"model.{name}: duplicate ID")
    nodes = {node.id for node in model.nodes}
    resources = {resource.id for resource in model.resources}
    for place in model.places:
        if place.node_id not in nodes or place.resource_id not in resources:
            raise ValueError(f"place {place.id}: unknown node or resource")


def validate_request(
    model: WorldModel, request: AssignmentRequest, draft: TaskDelta,
) -> Failure | None:
    from_data(AssignmentRequest, to_data(request))
    from_data(TaskDelta, to_data(draft))
    state = request.start.join_state
    if state.running_actions:
        return Failure("UNSUPPORTED", "Splice must not contain unfinished actions", ())
    robots = {robot.id for robot in model.robots}
    objects = {obj.id for obj in model.objects}
    for label, ids in (
        ("robot state", [robot.robot_id for robot in state.robots]),
        ("object state", [obj.object_id for obj in state.objects]),
        ("task", [progress.task.id for progress in request.tasks]),
        ("queue", [queue.robot_id for queue in request.queues]),
    ):
        if len(set(ids)) != len(ids):
            return Failure("BAD_INPUT", f"Duplicate {label} ID", tuple(ids))
    if {robot.robot_id for robot in state.robots} != robots:
        return Failure("BAD_INPUT", "Join state must contain every model robot", ())
    if {obj.object_id for obj in state.objects} != objects:
        return Failure("BAD_INPUT", "Join state must contain every model shelf", ())
    carriers = set()
    for obj in state.objects:
        if (obj.ground_pose is None) == (obj.carrier_id is None):
            return Failure("BAD_INPUT", "Shelf must have exactly one location", (obj.object_id,))
        if obj.carrier_id is not None:
            if obj.carrier_id not in robots or obj.carrier_id in carriers:
                return Failure("BAD_INPUT", "Unknown carrier or multiple carried shelves", (obj.object_id,))
            carriers.add(obj.carrier_id)
    tasks = {progress.task.id: progress for progress in request.tasks}
    owners = {}
    for queue in request.queues:
        if queue.robot_id not in robots:
            return Failure("BAD_INPUT", "Unknown queue robot", (queue.robot_id,))
        if not 0 <= queue.locked_prefix_count <= len(queue.task_ids):
            return Failure("BAD_INPUT", "Invalid locked prefix length", (queue.robot_id,))
        if len(queue.task_ids) > 1:
            return Failure("UNSUPPORTED", "Only one current task per robot is supported", (queue.robot_id,))
        for task_id in queue.task_ids:
            if task_id not in tasks or task_id in owners:
                return Failure("BAD_INPUT", "Unknown or multiply bound task", (task_id,))
            owners[task_id] = queue.robot_id
    for task_id, progress in tasks.items():
        if not 0 <= progress.next_step <= len(progress.task.steps):
            return Failure("BAD_INPUT", "Invalid projected task progress", (task_id,))
        if 0 < progress.next_step < len(progress.task.steps) and task_id not in owners:
            return Failure("CONFLICT", "Started task has no executor", (task_id,))
    for lock in request.locks:
        progress = tasks.get(lock.step.task_id)
        if (progress is None or lock.robot_id not in robots
                or not 0 <= lock.step.step_index < len(progress.task.steps)):
            return Failure("BAD_INPUT", "Invalid action lock reference", (lock.step.task_id,))
        if owners.get(lock.step.task_id) != lock.robot_id:
            return Failure("CONFLICT", "Committed action executor must be preserved", (lock.step.task_id, lock.robot_id))
    return None


def validate_candidate_bindings(
    model: WorldModel, request: AssignmentRequest, draft: TaskDelta,
) -> Failure | None:
    """Accept only new definitions bound once to robots with empty queues.

    The request has already passed boundary validation. An empty old queue has
    no protected prefix, so its proposed singleton is also the complete queue.
    Existing bindings, progress, and action locks remain unchanged.
    """
    new_ids = [task.id for task in draft.tasks]
    robot_ids = [queue.robot_id for queue in draft.queues]
    if len(set(new_ids)) != len(new_ids):
        return Failure("BAD_INPUT", "Duplicate candidate task ID", tuple(new_ids))
    if len(set(robot_ids)) != len(robot_ids):
        return Failure("BAD_INPUT", "Duplicate candidate queue robot", tuple(robot_ids))
    existing = {progress.task.id for progress in request.tasks}
    for task in draft.tasks:
        if task.id in existing:
            return Failure("CONFLICT", "Candidate task ID already exists", (task.id,))
        if not task.steps:
            return Failure("UNSUPPORTED", "Empty candidate tasks are not supported", (task.id,))
    robots = {robot.id for robot in model.robots}
    occupied = {queue.robot_id for queue in request.queues if queue.task_ids}
    bound = set()
    for queue in draft.queues:
        if queue.robot_id not in robots:
            return Failure("BAD_INPUT", "Unknown candidate robot", (queue.robot_id,))
        if queue.robot_id in occupied:
            return Failure("UNSUPPORTED", "Existing current bindings cannot be edited", (queue.robot_id,))
        if len(queue.task_ids) != 1:
            return Failure("UNSUPPORTED", "Candidate binding requires exactly one task", (queue.robot_id,))
        task_id = queue.task_ids[0]
        if task_id in existing:
            return Failure("UNSUPPORTED", "Only newly defined tasks can be assigned", (task_id,))
        if task_id not in new_ids:
            return Failure("BAD_INPUT", "Unknown candidate task", (task_id,))
        if task_id in bound:
            return Failure("BAD_INPUT", "Candidate task has multiple executors", (task_id,))
        bound.add(task_id)
    for task_id in new_ids:
        if task_id not in bound:
            return Failure("BAD_INPUT", "Candidate task has no executor", (task_id,))
    return None


def validate_current_task(
    progress: TaskProgress, robot_id: str, objects: dict[str, ObjectSpec],
    locations: dict[str, ObjectState], carried: dict[str, str], claimed: set[str],
) -> Failure | None:
    """Check an unfinished bound task without changing candidate bookkeeping."""
    task_id, steps = progress.task.id, progress.task.steps
    if progress.blocked:
        return Failure("NO_PLAN", "Blocked task requires explicit recovery", (task_id,))
    if len(steps) != 3 or tuple(type(step) for step in steps) != (Lift, Serve, Drop):
        return Failure("UNSUPPORTED", "Expected one Lift, Serve, Drop sequence", (task_id,))
    shelf = steps[0].object_id
    if shelf not in objects:
        return Failure("BAD_INPUT", "Unknown task shelf", (task_id, shelf))
    if shelf in claimed:
        return Failure("CONFLICT", "Concurrent tasks claim the same shelf", (task_id, shelf))
    if objects[shelf].carry_offset != Pose2(0, 0, 0):
        return Failure("UNSUPPORTED", "Nonzero shelf carry offsets are deferred", (shelf,))
    if progress.next_step == 0:
        if robot_id in carried or locations[shelf].carrier_id is not None:
            return Failure("CONFLICT", "Lift requires an empty robot and grounded shelf", (robot_id, shelf))
    elif carried.get(robot_id) != shelf:
        return Failure("CONFLICT", "Remaining task must stay with its shelf carrier", (task_id, robot_id, shelf))
    return None


def validate_lift_target(step: Lift, matches: list[Place]) -> Failure | None:
    if len(matches) != 1:
        return Failure("UNSUPPORTED", "Lift requires one exact storage pose match", (step.object_id,))
    return None


def validate_place(place: Place | None, place_id: str, kind: str) -> Failure | None:
    if place is None or place.kind != kind:
        return Failure("BAD_INPUT", f"Expected a known {kind} place", (place_id,))
    return None


def validate_carried_jobs(
    jobs: dict[str, RobotJobs], carried: dict[str, str],
) -> Failure | None:
    for robot_id, shelf in carried.items():
        if not jobs[robot_id].actions:
            return Failure("CONFLICT", "Carried shelf has no remaining current task", (robot_id, shelf))
    return None
