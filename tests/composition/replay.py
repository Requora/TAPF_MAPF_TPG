"""中文: 本脚本选择公开模块边界并保存真实组合证据, 不增加生产编排或契约.

English: This script selects public module boundaries and saves real composition evidence without adding production orchestration or contracts.
"""
import argparse
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from native.replay import scenario
from warehouse_api.allocation import SingleShelfAllocator
from warehouse_api.contracts import (
    Do, Drop, Failure, FleetPlan, Lift, MotionRequest, Move, PathRequest,
    PhysicalAction, Pick, RobotJobs, RobotQueue, RobotRoute, Serve, StepRef, Task, TaskDelta,
)
from warehouse_api.mapf import NativeMawpfPlanner
from warehouse_api.serialization import dumps
from warehouse_api.task_compiler import CurrentTaskCompiler
from warehouse_api.tpg import NativeWinkTpgPlanner

STAGES = ('allocation', 'compilation', 'mapf', 'tpg')


# 中文: boundary_case 独立构造任务, 动作和路线输入及预期值, 避免被测前置模块生成后置模块的唯一测试输入.
# English: boundary_case independently constructs task, action and route inputs and expectations so upstream implementations do not supply the only downstream test inputs.
def boundary_case(quantity=1, station=3, destination=5):
    _, model, planning = scenario(quantity=quantity, stock=quantity, station=station, destination=destination)
    assignment = planning.assignment
    task_id = 'native-chain:task'
    draft = TaskDelta((Task(task_id, (Lift('shelf'), Serve('station', (Pick('O', 'X', quantity),)),
                                     Drop('return'))),), (RobotQueue('A', (task_id,)),))
    # 中文: 已知案例表给出独立的服务耗时预期, 不调用被测动作耗时函数来计算答案.
    # English: The known-case table supplies independent service-duration expectations without calling the timing function under test.
    service_duration = {1: 0.3, 3: 0.7}[quantity]
    actions = (
        PhysicalAction(StepRef(task_id, 0), 'lift', 'shelf', 'n1', 0, .3, ('pickup',)),
        PhysicalAction(StepRef(task_id, 1), 'serve', 'shelf', f'n{station}', 0, service_duration, ('station',)),
        PhysicalAction(StepRef(task_id, 2), 'drop', 'shelf', f'n{destination}', 0, .3, ('return',)),
    )
    jobs = (RobotJobs('A', actions),)
    steps = [Move('e0'), Do(actions[0].step)]
    steps.extend(Move(f'e{x}') for x in range(1, station))
    steps.append(Do(actions[1].step))
    steps.extend(Move(f'e{x}') for x in range(station, destination))
    steps.append(Do(actions[2].step))
    plan = FleetPlan(assignment.start.request_id, (RobotRoute('A', tuple(steps)),), ())
    inputs = (assignment, (assignment, draft), PathRequest(assignment.start, jobs, 20),
              MotionRequest(assignment.start, jobs, plan, 30, 20))
    return model, inputs, (draft, jobs, plan)


# 中文: run_slice 只运行选择的连续模块区间并显式连接公开契约, 使同模块或跨模块输入输出均可测试.
# 此测试驱动保留每次请求, 结果和原生文件, 失败后停止; 它不模拟 Runtime 或生产流水线的总预算策略.
# English: run_slice executes only a selected contiguous module interval and explicitly connects public contracts so same-module and cross-module boundaries are testable.
# This test driver retains requests, results and native files and stops on failure; it does not emulate Runtime or the production pipeline's total-budget policy.
def run_slice(model, first, last, request, binary_directory=None):
    if not 0 <= first <= last < len(STAGES):
        raise ValueError('Select an ordered interval within STAGES')
    trace, raw = [], {}
    result = None
    for index in range(first, last + 1):
        directory = None
        if index == 0:
            result = SingleShelfAllocator(model).allocate(request)
        elif index == 1:
            assignment, draft = request
            result = CurrentTaskCompiler(model, sim_dt_s=.1).compile_jobs(assignment, draft)
        elif index == 2:
            planner = NativeMawpfPlanner(model, str(binary_directory / 'warehouse_mawpf'))
            result = planner.plan(request)
            directory = planner.last_run_directory
        else:
            planner = NativeWinkTpgPlanner(model, str(binary_directory / 'warehouse_winktpg'), sim_dt_s=.1)
            result = planner.prepare(request)
            directory = planner.last_run_directory
        trace.append((STAGES[index], request, result))
        if directory is not None:
            raw[STAGES[index]] = {file.name: file.read_text() for file in directory.iterdir() if file.suffix != '.bin'}
        if isinstance(result, Failure):
            break
        if index < last:
            if index == 0:
                request = (request, result)
            elif index == 1:
                request = PathRequest(assignment.start, result, assignment.budget_s)
            else:
                request = MotionRequest(request.start, request.jobs, result, 30, request.budget_s)
    return {'trace': trace, 'result': result, 'native_evidence': raw}


# 中文: main 输出十种边界组合的真实证据和二进制哈希, 让审查者按入口与出口追溯实际运行.
# English: main outputs evidence for ten boundary combinations and binary hashes so reviewers can trace execution by entry and exit.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary_directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--first', choices=STAGES)
    parser.add_argument('--last', choices=STAGES)
    args = parser.parse_args()
    model, inputs, _ = boundary_case()
    pairs = [(first, last) for first in range(4) for last in range(first, 4)]
    if args.first is not None or args.last is not None:
        first = STAGES.index(args.first or 'allocation')
        last = STAGES.index(args.last or 'tpg')
        if first > last:
            parser.error('--first must precede or equal --last')
        pairs = [(first, last)]
    matrix = {f'{STAGES[first]}->{STAGES[last]}': run_slice(model, first, last, inputs[first], args.binary_directory)
              for first, last in pairs}
    assignment = inputs[0]
    stock_failure = replace(assignment, stock=(replace(assignment.stock[0], available_quantity=0),))
    stale = replace(inputs[3], fleet_plan=replace(inputs[3].fleet_plan, request_id='stale'))
    evidence = {
        'scope': 'Real modules; one robot/shelf eastbound unit lane; no continuous collision or parking safety proof.',
        'model': model, 'seed': 0,
        'sources': {
            'mawpf': 'https://github.com/HirokiNagai-39/mawpf/tree/0cdb8e43797aff3781e4cd3ddb2c6d7d36f3df17',
            'winktpg': 'https://github.com/JingtianYan/WinkTPG-IEEE-TASE/tree/dd96946f225e206de35b041320786eab43210658',
        },
        'binaries': {name: sha256((args.binary_directory / name).read_bytes()).hexdigest()
                     for name in ('warehouse_mawpf', 'warehouse_winktpg')},
        'matrix': matrix,
        'failures': {
            'allocation->tpg/stock=0': run_slice(model, 0, 3, stock_failure, args.binary_directory),
            'tpg->tpg/stale': run_slice(model, 3, 3, stale, args.binary_directory),
        },
    }
    args.output.write_text(dumps(evidence))
    for name, result in matrix.items():
        print(name, type(result['result']).__name__)


if __name__ == '__main__':
    main()
