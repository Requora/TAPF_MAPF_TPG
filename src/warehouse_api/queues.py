"""Pure candidate queue editing, before physical compilation or acceptance."""
from warehouse_api.contracts import (
    AssignmentRequest, Failure, RobotQueue, TaskDelta,
)


def candidate_queues(
    request: AssignmentRequest, draft: TaskDelta,
) -> tuple[RobotQueue, ...] | Failure:
    """Return complete candidate queues in join-state robot order.

    A listed draft queue replaces only the old mutable suffix. An omitted
    queue is unchanged; a missing old queue is empty. Validate definitions,
    references, unique ownership, prefix lengths, and explicit StepLocks.
    Success is not physical feasibility: carrying, progress, fixed motion,
    inventory, and action semantics require subsequent compilation/validation.
    Removed tasks remain accepted definitions; no reservation is released.
    """
    robots = tuple(robot.robot_id for robot in request.start.join_state.robots)
    if len(set(robots)) != len(robots):
        return Failure("BAD_INPUT", "Duplicate join-state robot ID", robots)
    tasks = {}
    for progress in request.tasks:
        task = progress.task
        if task.id in tasks:
            return Failure("BAD_INPUT", "Duplicate accepted task ID", (task.id,))
        tasks[task.id] = task

    old = {}
    for queue in request.queues:
        if queue.robot_id not in robots or queue.robot_id in old:
            return Failure("BAD_INPUT", "Unknown or duplicate old queue robot", (queue.robot_id,))
        count = queue.locked_prefix_count
        if type(count) is not int or not 0 <= count <= len(queue.task_ids):
            return Failure("BAD_INPUT", "Invalid locked prefix count", (queue.robot_id,))
        old[queue.robot_id] = queue
    old_queues = tuple(
        RobotQueue(robot, old[robot].task_ids if robot in old else ())
        for robot in robots
    )
    old_owners = _owners(old_queues, tasks, candidate=False)
    if isinstance(old_owners, Failure):
        return old_owners

    locked_steps = set()
    for lock in request.locks:
        ref = lock.step
        task = tasks.get(ref.task_id)
        if (task is None or type(ref.step_index) is not int
                or not 0 <= ref.step_index < len(task.steps)):
            return Failure("BAD_INPUT", "Invalid StepLock reference", (ref.task_id,))
        if ref in locked_steps:
            return Failure("BAD_INPUT", "Duplicate StepLock reference", (ref.task_id,))
        locked_steps.add(ref)
        if lock.robot_id not in robots or old_owners.get(ref.task_id) != lock.robot_id:
            return Failure("BAD_INPUT", "StepLock disagrees with old task owner",
                           (ref.task_id, lock.robot_id))

    for task in draft.tasks:
        if task.id in tasks:
            return Failure("BAD_INPUT", "Draft task ID is not new", (task.id,))
        tasks[task.id] = task
    edits = {}
    for queue in draft.queues:
        if queue.robot_id not in robots or queue.robot_id in edits:
            return Failure("BAD_INPUT", "Unknown or duplicate draft queue robot", (queue.robot_id,))
        edits[queue.robot_id] = queue.task_ids

    result = []
    for queue in old_queues:
        robot = queue.robot_id
        ids = queue.task_ids
        if robot in edits:
            count = old[robot].locked_prefix_count if robot in old else 0
            ids = ids[:count] + edits[robot]
        result.append(RobotQueue(robot, ids))
    owners = _owners(tuple(result), tasks, candidate=True)
    if isinstance(owners, Failure):
        return owners
    for lock in request.locks:
        if owners.get(lock.step.task_id) != lock.robot_id:
            return Failure("CONFLICT", "StepLock executor cannot change or be removed",
                           (lock.step.task_id, lock.robot_id))
    return tuple(result)


def _owners(queues, tasks, *, candidate):
    """Check all bindings, including those on omitted queues."""
    owners = {}
    for queue in queues:
        for task_id in queue.task_ids:
            if task_id not in tasks:
                return Failure("BAD_INPUT", "Queue references an unknown task", (task_id, queue.robot_id))
            if task_id in owners:
                code = "CONFLICT" if candidate else "BAD_INPUT"
                return Failure(code, "Task appears more than once in queues",
                               (task_id, owners[task_id], queue.robot_id))
            owners[task_id] = queue.robot_id
    return owners
