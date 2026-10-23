"""中文: 本重放对真实原生轨迹逐段切片并保留比较证据, 不声称连续安全.
English: This replay slices real native trajectories and retains comparison evidence, without claiming continuous safety.
"""
import argparse
from pathlib import Path

from native.replay import run
from warehouse_api.contracts import ExecutableProposal
from warehouse_api.serialization import dumps
from warehouse_api.trajectory import evaluate, slice_curve


# 中文: replay 运行原生链并比较每段内部切片, 让审查者查看真实节点, 查询状态及数值误差.
# English: replay runs the native chain and compares interior slices so reviewers can inspect real knots, query states and numerical errors.
def replay(binary_directory: Path):
    evidence = run(binary_directory)
    proposal = evidence["result"]
    assert isinstance(proposal, ExecutableProposal), proposal
    comparisons = []
    for segment in (*proposal.motion.common_prefix, *proposal.motion.stop_tail):
        for left, right in zip(segment.knots, segment.knots[1:]):
            h = right.time_s - left.time_s
            sliced = slice_curve(segment.knots, left.time_s + h/4, right.time_s - h/4)
            for fraction in (0.25, 0.5, 0.75):
                t = left.time_s + h*fraction
                # Use stored slice boundaries to avoid an independently rounded time outside coverage.
                # 中文: replay 使用已存储的边界时间, 避免独立舍入把查询移到切片之外.
                t = min(max(t, sliced[0].time_s), sliced[-1].time_s)
                original, cut = evaluate(segment.knots, t), evaluate(sliced, t)
                error = max(abs(original.pose.x_m - cut.pose.x_m),
                            abs(original.velocity.vx_mps - cut.velocity.vx_mps))
                assert error < 1e-10, (original, cut, error)
                comparisons.append({"original": original, "slice": cut, "max_x_vx_error": error})
    return {"native": evidence, "comparisons": comparisons,
            "max_x_vx_error": max(row["max_x_vx_error"] for row in comparisons)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.binary_directory)
    args.output.write_text(dumps(result))
    print(f"{len(result['comparisons'])} comparisons; max x/vx error: {result['max_x_vx_error']:.3g}")
