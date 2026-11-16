"""中文: 本重放把真实规划输出送入执行器, 用端点观测替身检查订单到控制帧的链路, 不模拟货架或 Runtime.
English: This replay feeds real plans into the executor with endpoint-observation doubles, checking orders to frames without simulating shelves or Runtime.
"""
import argparse
from dataclasses import replace
from pathlib import Path

from native.replay import run
from warehouse_api.contracts import ExecutableProposal, ExecutionInput, Failure, RobotSegment, RobotState
from warehouse_api.execution import TrajectoryExecutor
from warehouse_api.serialization import dumps


# 中文: replay 保留每步输入状态和实际控制帧, 让用户单步检查真实求解到动作启动的链路; 候选直连仅用于测试, 不绕过生产安全门禁.
# English: replay records each input state and actual frame for stepwise inspection from native solving to action starts; direct candidate wiring is test-only and does not bypass production safety gates.
def replay(binary_directory: Path):
    native = run(binary_directory)
    proposal = native['result']
    assert isinstance(proposal, ExecutableProposal), proposal
    tails = {segment.robot_id: segment for segment in proposal.motion.stop_tail}
    segments = tuple(RobotSegment(prefix.robot_id, prefix.knots + tails[prefix.robot_id].knots[1:],
                                  prefix.actions + tails[prefix.robot_id].actions)
                     for prefix in proposal.motion.common_prefix)
    jobs = native['trace'][1][2]
    table = tuple(action for job in jobs for action in job.actions)
    state = native['request'].assignment.start.join_state
    executor = TrajectoryExecutor()
    frames, starts = [], []
    tick, dt_s = 0, .1
    finish = max(segment.knots[-1].time_s for segment in segments) + 2 * dt_s
    while state.time_s < finish:
        frame = executor.build_frame(ExecutionInput(state, segments, table), dt_s)
        assert not isinstance(frame, Failure), (tick, frame)
        frames.append({'state': state, 'frame': frame})
        starts.extend((frame.from_s, action.robot_id, action.action.step) for action in frame.start_actions)
        tick += 1
        # 中文: 端点观测替身只回送控制帧末位姿和速度, 不产生动作完成事件或修改货架与账本.
        # English: The endpoint-observation double echoes final poses and velocities only; it produces no action results or shelf/ledger changes.
        state = replace(state, time_s=frame.to_s, robots=tuple(
            RobotState(motion.robot_id, motion.knots[-1].pose, motion.knots[-1].velocity)
            for motion in frame.motion))
    expected = tuple((action.start_s, segment.robot_id, action.step)
                     for segment in segments for action in segment.actions)
    assert len(starts) == len(expected), (starts, expected)
    for actual, planned in zip(starts, expected):
        assert actual[1:] == planned[1:] and abs(actual[0] - planned[0]) < 1e-9, (actual, planned)
    return {'status': 'real order-to-control-frame replay completed', 'native': native,
            'limits': 'Test-only candidate wiring and endpoint observations; no Runtime acceptance, action completion, shelf effects, backend or safety proof.',
            'frames': frames, 'action_starts': starts, 'final_state': state}


# 中文: main 保存 JSON 与单步 HTML, 让用户复现并检查本次真实输出而非静态示意动画.
# English: main saves JSON and stepwise HTML so users can reproduce and inspect actual output rather than a schematic animation.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary_directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--html', type=Path, required=True)
    args = parser.parse_args()
    evidence = replay(args.binary_directory)
    args.output.write_text(dumps(evidence))
    template = Path(__file__).with_suffix('.html').read_text()
    args.html.write_text(template.replace('__EVIDENCE__', dumps(evidence).replace('<', '\\u003c')))
    print(f"{len(evidence['frames'])} frames; action starts: {evidence['action_starts']}")


if __name__ == '__main__':
    main()
