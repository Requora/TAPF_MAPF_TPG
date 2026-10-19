"""Compile accepted current tasks; candidate edits remain unsupported."""
from warehouse_api import _compiler_validation as validation
from warehouse_api.contracts import (
    AssignmentRequest, Failure, Lift, PhysicalAction, Place, Pose2, RobotJobs,
    Serve, StepRef, TaskAction, TaskDelta, WorldModel,
)
from warehouse_api.durations import action_duration_s


class CurrentTaskCompiler:
    """SharedCompiler subset: one accepted Lift/Serve/Drop task per robot.

    Contract shape and timing errors raise without interception. Semantic
    failures return Failure. This compiler does not validate executable safety.
    """

    def __init__(self, model: WorldModel, *, sim_dt_s: float):
        validation.validate_model(model, sim_dt_s)
        self.model = model
        self.sim_dt_s = sim_dt_s
        self.nodes = {node.id: node for node in model.nodes}
        self.places = {place.id: place for place in model.places}

    def compile_jobs(
        self, request: AssignmentRequest, draft: TaskDelta,
    ) -> tuple[RobotJobs, ...] | Failure:
        failure = validation.validate_request(self.model, request, draft)
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
