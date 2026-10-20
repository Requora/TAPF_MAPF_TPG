"""This module assigns the only robot and shelf to fulfill the supplied item demand."""
from warehouse_api.contracts import (
    AssignmentRequest, Drop, Failure, Lift, Pick, RobotQueue, Serve, Task, TaskDelta, WorldModel,
)
from warehouse_api.validation import check_assignment, check_single_lane


# 中文: SingleShelfAllocator 是任务分配器: 它决定由哪台机器人搬哪个货架, 到哪个工作站服务, 最后在哪里放下货架.
# 当前实现只接受一台机器人, 一个货架和一条商品需求, 并要求货架库存能满足这条需求.
# 分配器把这些输入转换成新任务和机器人任务队列, 让后续任务编译器可以生成具体动作.
# 本项目先用这个受限场景验证真实规划链的连接; 该类不比较多台机器人或多个货架, 也不寻找最优分配.
# English: SingleShelfAllocator assigns a robot to carry a shelf, serve a workstation and put the shelf down.
# This implementation accepts one robot, one shelf and one item-demand row, with enough shelf stock.
# The allocator creates a task and a robot task queue so the task compiler can produce concrete actions.
# This limited scenario lets the project verify the real planning chain; the class does not compare
# multiple robots or shelves or optimize their assignment.
class SingleShelfAllocator:
    # 中文: __init__ 保存调用方传入的 WorldModel, 即机器人, 货架, 地图和工作站等场景定义.
    # 分配器需要这些定义来选择机器人和服务位置; 显式传入模型让分配过程不必读取隐藏的全局状态.
    # English: __init__ stores the supplied WorldModel, which defines robots, shelves, the map and workstations.
    # The allocator needs these definitions to select a robot and service location without reading hidden global state.
    def __init__(self, model: WorldModel):
        self.model = model

    # 中文: allocate 检查场景和库存后, 为唯一的机器人创建 Lift(抬起货架), Serve(在工作站处理需求),
    # Drop(放下货架) 三步任务. Serve 中的 Pick 记录订单, 商品编号和处理数量.
    # 该方法返回 TaskDelta, 即建议新增的任务和机器人队列, 供任务编译器转换成物理动作.
    # 这些数据只是待接受的分配建议; 分配器不扣减库存, 以免尚未采用的方案改变实际库存记录.
    # English: allocate checks the scene and stock, then assigns Lift (raise the shelf), Serve (process demand
    # at the workstation) and Drop (put down the shelf) to the only robot. A Pick records the order, item and quantity.
    # The method returns a TaskDelta: proposed new tasks and robot queues for conversion into physical actions.
    # The allocator does not deduct stock because an unaccepted proposal must not change actual inventory records.
    def allocate(self, request: AssignmentRequest) -> TaskDelta | Failure:
        failure = check_single_lane(self.model, request.start) or check_assignment(self.model, request)
        if failure is not None:
            return failure
        positions = {node.id: node.position.x_m for node in self.model.nodes}
        # 中文: lambda 根据位置所属地图节点的 x 坐标提供排序值, 让分配器识别向东依次到达的取架位, 工作站和归还位.
        # English: The lambda returns each place's map-node x coordinate so the allocator can identify
        # the pickup, workstation and return locations in eastbound travel order.
        _, station, storage = sorted(self.model.places, key=lambda place: positions[place.node_id])
        demand = request.demands[0]
        task = Task(f"{request.start.request_id}:task", (
            Lift(request.stock[0].object_id),
            Serve(station.id, (Pick(demand.order_id, demand.sku, demand.available_quantity),)),
            Drop(storage.id),
        ))
        return TaskDelta((task,), (RobotQueue(self.model.robots[0].id, (task.id,)),))
