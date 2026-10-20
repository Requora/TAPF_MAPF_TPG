"""Choose the only feasible robot/shelf and derive picks from available demand."""
from warehouse_api.contracts import (
    AssignmentRequest, Drop, Failure, Lift, Pick, RobotQueue, Serve, Task, TaskDelta, WorldModel,
)
from warehouse_api.validation import check_assignment, check_single_lane


class SingleShelfAllocator:
    def __init__(self, model: WorldModel):
        self.model = model

    def allocate(self, request: AssignmentRequest) -> TaskDelta | Failure:
        failure = check_single_lane(self.model, request.start) or check_assignment(self.model, request)
        if failure is not None:
            return failure
        positions = {node.id: node.position.x_m for node in self.model.nodes}
        _, station, storage = sorted(self.model.places, key=lambda place: positions[place.node_id])
        demand = request.demands[0]
        task = Task(f"{request.start.request_id}:task", (
            Lift(request.stock[0].object_id),
            Serve(station.id, (Pick(demand.order_id, demand.sku, demand.available_quantity),)),
            Drop(storage.id),
        ))
        return TaskDelta((task,), (RobotQueue(self.model.robots[0].id, (task.id,)),))
