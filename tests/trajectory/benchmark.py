"""中文: 本基准测量合成车队的串行曲线读取成本, 不代表完整系统或原生求解器性能.
English: This benchmark measures serial curve access on synthetic fleets, not full-system or native-solver performance.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
from statistics import median
import subprocess
from time import perf_counter_ns

from warehouse_api.contracts import Knot, Pose2, Twist2
from warehouse_api.trajectory import evaluate, slice_curve
import warehouse_api.trajectory


# 中文: make_fleet 创建相互独立的匀速曲线, 让节点数和车队规模独立变化且结果可解析验证.
# English: make_fleet builds separate constant-speed curves so fleet size and knot count vary independently with analytic verification.
def make_fleet(robots, knots):
    return tuple(tuple(Knot(float(i), Pose2(float(i), float(robot), 0), Twist2(1, 0, 0))
                       for i in range(knots)) for robot in range(robots))


# 中文: measure 测量中段连续查询的整车队耗时, 包含公共 API 校验和结果分配, 排除建模与结果核对.
# English: measure times consecutive mid-curve fleet queries, including public validation and output allocation but excluding setup and result checks.
def measure(fleet, hz, operation, *, frames, repeats):
    dt = 1/hz
    start = (len(fleet[0]) - 1)/2 + 0.125
    assert start + frames*dt < fleet[0][-1].time_s, 'Queries must remain inside the curve'
    samples, max_error = [], 0.0
    for repeat in range(repeats + 1):
        for frame in range(frames):
            t = start + frame*dt
            before = perf_counter_ns()
            if operation == 'evaluate':
                outputs = [evaluate(curve, t) for curve in fleet]
            else:
                outputs = [slice_curve(curve, t, t + dt) for curve in fleet]
            elapsed = (perf_counter_ns() - before)/1e6
            if repeat:
                samples.append(elapsed)
            for robot, output in enumerate(outputs):
                nodes = (output,) if operation == 'evaluate' else output
                for node in nodes:
                    error = max(abs(node.pose.x_m - node.time_s), abs(node.pose.y_m - robot))
                    max_error = max(max_error, error)
                    assert error < 1e-9 and abs(node.velocity.vx_mps - 1) < 1e-9
    return {'robots': len(fleet), 'knots': len(fleet[0]), 'hz': hz, 'operation': operation,
            'frames_per_repeat': frames, 'repeats': repeats, 'warmup_frames': frames,
            'timed_calls': len(samples)*len(fleet), 'query_start_s': start,
            'frame_ms': samples, 'median_frame_ms': median(samples),
            'p95_frame_ms': sorted(samples)[math.ceil(0.95*len(samples)) - 1],
            'period_ms': 1000/hz, 'median_period_fraction': median(samples)/(1000/hz),
            'max_position_error_m': max_error}


# 中文: main 记录机器和源码身份并逐案例保存原始时间, 让审查者复现性能边界而非依赖单个平均值.
# English: main records machine/source identity and raw case timings so reviewers can reproduce limits rather than rely on one average.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--robots', type=int, nargs='+', default=[1, 100, 1000])
    parser.add_argument('--knots', type=int, nargs='+', default=[16, 128, 1024])
    parser.add_argument('--hz', type=int, nargs='+', default=[10, 50])
    parser.add_argument('--frames', type=int, default=3)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if min(*args.robots, *args.hz, args.frames, args.repeats) < 1 or min(args.knots) < 4:
        parser.error('Positive counts and at least four knots are required')
    source = Path(warehouse_api.trajectory.__file__).parent
    cpu = [line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
           if line.startswith('model name')][0]
    evidence = {'utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
                'platform': platform.platform(), 'cpu': cpu, 'affinity': sorted(os.sched_getaffinity(0)),
                'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'source_sha256': {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(source.glob('*.py'))},
                'benchmark_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
                'limits': 'Synthetic serial hot-repeat microbenchmark; no pacing, solver, geometry, IPC or backend. GC enabled; setup excluded. p95 describes only 15 frames by default.',
                'cases': []}
    for robots in args.robots:
        for knots in args.knots:
            fleet = make_fleet(robots, knots)
            for hz in args.hz:
                for operation in ('evaluate', 'slice_curve'):
                    row = measure(fleet, hz, operation, frames=args.frames, repeats=args.repeats)
                    evidence['cases'].append(row)
                    args.output.write_text(json.dumps(evidence, indent=2) + '\n')
                    print(f'{robots:4} robots {knots:4} knots {hz:2} Hz {operation:11} '
                          f'median={row["median_frame_ms"]:.3f} ms p95={row["p95_frame_ms"]:.3f} ms', flush=True)


if __name__ == '__main__':
    main()
