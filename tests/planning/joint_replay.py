"""中文: 本脚本重放联合入口的 fixture, 让审查者检查真实编译器的阶段输入输出.

English: This script replays a joint-entry fixture so reviewers can inspect real compiler stage I/O.
"""
from unittest.mock import Mock

from .replay import scenario
from warehouse_api.contracts import JointPlan, JointPlanner
from warehouse_api.planning import JointPipeline
from warehouse_api.serialization import dumps


# 中文: main 用显式替身返回固定联合候选, 打印编译和运动请求, 便于检查联接而不冒充原生运行.
# English: main returns a fixed joint candidate through an explicit double and prints compilation and motion requests to inspect wiring without claiming native execution.
def main():
    _, request, staged, trace = scenario()
    staged.solve(request)
    solver = Mock(spec=JointPlanner)
    solver.plan.return_value = JointPlan(trace[1]["output"], trace[3]["output"])
    pipeline = JointPipeline(solver, staged.compiler, staged.motion_planner)
    result = pipeline.solve(request)
    print(dumps({
        "verification": "fixture joint solver and motion; real shared compiler; no native TAPF or safety acceptance",
        "request": request, "trace": pipeline.last_trace, "result": result,
    }))


if __name__ == "__main__":
    main()
