"""Fixture wiring replay. Allocation, MAPF, and TPG are explicit test doubles."""
from dataclasses import replace
from unittest.mock import Mock

from task_compiler.test_task_compiler import fixture
from warehouse_api.contracts import (
    Allocator, Demand, Do, Edge, Item, Knot, MotionPlan, MotionPlanner, Move,
    Order, PathPlanner, PlanningRequest, Pose2, RobotQueue, RobotRoute,
    RobotSegment, TaskDelta, TimedAction, Twist2, FleetPlan, Stock,
)
from warehouse_api.order_source import ReplayOrderSource
from warehouse_api.planning import StagedPipeline
from warehouse_api.serialization import dumps
from warehouse_api.task_compiler import CurrentTaskCompiler


# 中文: 装配订单源和真实编译器以及显式求解器替身, 为编排单测隔离阶段边界, 此结果不作为原生算法证据.
# English: Wire an order source and real compiler to explicit solver doubles so orchestration tests
# isolate stage boundaries without claiming native algorithm evidence.
def scenario():
    model, accepted = fixture()
    model = replace(
        model, robots=model.robots[:1],
        places=tuple(replace(place, yaw_rad=0) for place in model.places),
        edges=(Edge("out", "home-node", "station-node"),
               Edge("return", "station-node", "return-node")),
    )
    state = replace(accepted.start.join_state, time_s=0,
                    robots=accepted.start.join_state.robots[:1])
    start = replace(accepted.start, now_s=0, join_state=state, submit_before_s=10)
    source = ReplayOrderSource((Order("O", 0, (Item("X", 1),), None),))
    orders = source.release(0)
    demands = tuple(Demand(order.id, item.sku, item.quantity, order.due_at_s)
                    for order in orders for item in order.items)
    assignment = replace(accepted, start=start, demands=demands,
                         stock=(Stock("shelf", "X", 1),), tasks=(), queues=(), budget_s=10)
    draft = TaskDelta((accepted.tasks[0].task,), (RobotQueue("A", ("T",)),))
    trace = [{"stage": "orders", "implementation": "ReplayOrderSource", "output": orders}]
    allocator = Mock(spec=Allocator)
    path = Mock(spec=PathPlanner)
    motion = Mock(spec=MotionPlanner)
    compiler = CurrentTaskCompiler(model, sim_dt_s=0.1)

    # 中文: 记录分配请求并返回固定草稿, 为编排测试提供可控阶段结果, 无库存选择或优化算法.
    # English: Record the allocation request and return a fixed draft so orchestration has a
    # controlled stage result rather than inventory selection or optimization.
    def allocate(request):
        trace.append({"stage": "allocation", "implementation": "fixture",
                      "input": request, "output": draft})
        return draft

    # 中文: 把编译动作放入固定路线并记录输入输出, 验证动作引用传递, 不执行真实路径搜索.
    # English: Place compiled actions on a fixed route and record I/O so tests verify reference
    # propagation without performing route search.
    def plan(request):
        trace.append({"stage": "compile", "implementation": "CurrentTaskCompiler",
                      "output": request.jobs})
        actions = request.jobs[0].actions
        result = FleetPlan(start.request_id, (RobotRoute("A", (
            Do(actions[0].step), Move("out"), Do(actions[1].step),
            Move("return"), Do(actions[2].step),
        )),), ())
        trace.append({"stage": "mapf", "implementation": "fixture",
                      "input": request, "output": result})
        return result

    # 中文: 从传入动作构造可追踪时间段, 检查编排保留耗时和引用, 不声称这条 fixture曲线具有物理安全性.
    # English: Construct traceable segments from supplied actions so orchestration can check
    # duration and reference propagation without claiming physical safety for fixture curves.
    def prepare(request):
        time = start.join_state.time_s
        zero = Twist2(0, 0, 0)
        knots = [Knot(time, Pose2(0, 0, 0), zero)]
        scheduled = []
        for index, action in enumerate(request.jobs[0].actions):
            if index:
                time += 4
                knots.append(Knot(time, Pose2(2 * index, 0, 0), zero))
            scheduled.append(TimedAction(time, action.step))
            time += action.duration_s
            knots.append(Knot(time, knots[-1].pose, zero))
        prefix = RobotSegment("A", tuple(knots), tuple(scheduled))
        tail = RobotSegment("A", (knots[-1], replace(knots[-1], time_s=time + 1)), ())
        result = MotionPlan((prefix,), (tail,))
        trace.append({"stage": "tpg", "implementation": "fixture",
                      "input": request, "output": result})
        return result

    allocator.allocate.side_effect = allocate
    path.plan.side_effect = plan
    motion.prepare.side_effect = prepare
    pipeline = StagedPipeline(allocator, compiler, path, motion)
    return model, PlanningRequest(assignment, 10), pipeline, trace


if __name__ == "__main__":
    _, request, pipeline, trace = scenario()
    result = pipeline.solve(request)
    print(dumps({
        "verification": "fixture wiring only; no native adapters or safety acceptance",
        "request": request, "trace": trace, "result": result,
    }))
