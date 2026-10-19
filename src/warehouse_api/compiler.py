"""Compile accepted current tasks; candidate edits remain unsupported."""
from warehouse_api.codec import from_data, to_data
from warehouse_api.contracts import (
    AssignmentRequest, Drop, Failure, Lift, PhysicalAction, Pose2, RobotJobs,
    Serve, StepRef, TaskDelta, WorldModel,
)
from warehouse_api.durations import action_duration_s


class CurrentTaskCompiler:
    """SharedCompiler subset: one accepted Lift/Serve/Drop task per robot.

    Contract shape and timing errors raise without interception. Semantic
    failures return Failure. This compiler does not validate executable safety.
    """

    def __init__(self, model: WorldModel, *, sim_dt_s: float):
        from_data(WorldModel, to_data(model))
        action_duration_s(Lift("timing-check"), model.action_times, sim_dt_s=sim_dt_s)
        for name in ("nodes", "resources", "robots", "objects", "places"):
            entries = getattr(model, name)
            if len({entry.id for entry in entries}) != len(entries):
                raise ValueError(f"model.{name}: duplicate ID")
        self.model = model
        self.sim_dt_s = sim_dt_s
        self.nodes = {node.id: node for node in model.nodes}
        self.places = {place.id: place for place in model.places}
        resources = {resource.id for resource in model.resources}
        for place in model.places:
            if place.node_id not in self.nodes or place.resource_id not in resources:
                raise ValueError(f"place {place.id}: unknown node or resource")

    def compile_jobs(
        self, request: AssignmentRequest, draft: TaskDelta,
    ) -> tuple[RobotJobs, ...] | Failure:
        from_data(AssignmentRequest, to_data(request))
        from_data(TaskDelta, to_data(draft))
        if draft.tasks or draft.queues:
            return Failure("UNSUPPORTED", "Candidate task and queue edits are deferred", ())
        state = request.start.join_state
        if state.running_actions:
            return Failure("UNSUPPORTED", "Splice must not contain unfinished actions", ())
        robots = {robot.id for robot in self.model.robots}
        objects = {obj.id: obj for obj in self.model.objects}
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
        if {obj.object_id for obj in state.objects} != objects.keys():
            return Failure("BAD_INPUT", "Join state must contain every model shelf", ())
        carried = {}
        for obj in state.objects:
            if (obj.ground_pose is None) == (obj.carrier_id is None):
                return Failure("BAD_INPUT", "Shelf must have exactly one location", (obj.object_id,))
            if obj.carrier_id is not None:
                if obj.carrier_id not in robots or obj.carrier_id in carried:
                    return Failure("BAD_INPUT", "Unknown carrier or multiple carried shelves", (obj.object_id,))
                carried[obj.carrier_id] = obj.object_id
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
        jobs = {robot.id: RobotJobs(robot.id, ()) for robot in self.model.robots}
        claimed = set()
        locations = {obj.object_id: obj for obj in state.objects}
        for task_id, robot_id in owners.items():
            progress = tasks[task_id]
            if progress.next_step == len(progress.task.steps):
                continue
            if progress.blocked:
                return Failure("NO_PLAN", "Blocked task requires explicit recovery", (task_id,))
            steps = progress.task.steps
            if len(steps) != 3 or tuple(type(step) for step in steps) != (Lift, Serve, Drop):
                return Failure("UNSUPPORTED", "Expected one Lift, Serve, Drop sequence", (task_id,))
            shelf = steps[0].object_id
            if shelf not in objects:
                return Failure("BAD_INPUT", "Unknown task shelf", (task_id, shelf))
            if shelf in claimed:
                return Failure("CONFLICT", "Concurrent tasks claim the same shelf", (task_id, shelf))
            claimed.add(shelf)
            if objects[shelf].carry_offset != Pose2(0, 0, 0):
                return Failure("UNSUPPORTED", "Nonzero shelf carry offsets are deferred", (shelf,))
            if progress.next_step == 0:
                if robot_id in carried or locations[shelf].carrier_id is not None:
                    return Failure("CONFLICT", "Lift requires an empty robot and grounded shelf", (robot_id, shelf))
            elif carried.get(robot_id) != shelf:
                return Failure("CONFLICT", "Remaining task must stay with its shelf carrier", (task_id, robot_id, shelf))
            actions = []
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
        for robot_id, shelf in carried.items():
            if not jobs[robot_id].actions:
                return Failure("CONFLICT", "Carried shelf has no remaining current task", (robot_id, shelf))
        return tuple(jobs.values())

    def _target(self, step, ground_pose):
        if isinstance(step, Lift):
            matches = [place for place in self.model.places
                       if place.kind == "storage"
                       and Pose2(self.nodes[place.node_id].position.x_m,
                                 self.nodes[place.node_id].position.y_m,
                                 place.yaw_rad) == ground_pose]
            if len(matches) != 1:
                return Failure("UNSUPPORTED", "Lift requires one exact storage pose match", (step.object_id,))
            return matches[0]
        place_id = step.station_id if isinstance(step, Serve) else step.storage_id
        kind = "station" if isinstance(step, Serve) else "storage"
        place = self.places.get(place_id)
        if place is None or place.kind != kind:
            return Failure("BAD_INPUT", f"Expected a known {kind} place", (place_id,))
        return place
