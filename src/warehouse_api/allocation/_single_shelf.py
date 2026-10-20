"""Choose the only feasible robot/shelf and derive picks from available demand."""
from warehouse_api.contracts import (
    AssignmentRequest, Drop, Failure, Lift, Pick, RobotQueue, Serve, Task, TaskDelta, WorldModel,
)
from warehouse_api.validation import check_assignment, check_single_lane


# 中文: 实现一车一架子集的可行分配, 为真实端到端链提供最小分配器, 不声称具备多车匹配或优化能力.
# English: Implement feasible allocation for the one-robot, one-shelf subset so the real chain has
# an allocator without claiming general matching or optimization.
class SingleShelfAllocator:
    # 中文: 保存静态场景模型供分配时使用, 避免从实时账本隐式取数据, 让候选计算依赖显式输入.
    # English: Retain the static model for allocation so candidate decisions depend on explicit
    # inputs rather than hidden live-ledger reads.
    def __init__(self, model: WorldModel):
        self.model = model

    # 中文: 先检查支持范围和库存, 再生成 Lift/Serve/Drop 候选, 将订单数量转成可编译决策而不预留真实库存.
    # English: Check capabilities and stock before creating a Lift/Serve/Drop candidate so demand
    # becomes compilable work without reserving live inventory.
    def allocate(self, request: AssignmentRequest) -> TaskDelta | Failure:
        failure = check_single_lane(self.model, request.start) or check_assignment(self.model, request)
        if failure is not None:
            return failure
        positions = {node.id: node.position.x_m for node in self.model.nodes}
        # 中文: 排序键把业务位置按车道 x 排列, 以识别取架后的服务和归还顺序.
        # English: Sort places by lane x to identify the service and return order after pickup.
        _, station, storage = sorted(self.model.places, key=lambda place: positions[place.node_id])
        demand = request.demands[0]
        task = Task(f"{request.start.request_id}:task", (
            Lift(request.stock[0].object_id),
            Serve(station.id, (Pick(demand.order_id, demand.sku, demand.available_quantity),)),
            Drop(storage.id),
        ))
        return TaskDelta((task,), (RobotQueue(self.model.robots[0].id, (task.id,)),))
