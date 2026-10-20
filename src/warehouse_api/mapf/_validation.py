"""中文: 该模块在转换为模块间共享的路线步骤前检查原生路径状态, 防止适配器丢失不支持的运动含义.

English: This module checks native path states before conversion to shared route steps so adapters cannot lose unsupported motion semantics.
"""
from warehouse_api.contracts import Failure


# 中文: check_states 检查上游路径的起终状态和逐格向东移动, 在转换为模块间共享的 Move 路线步骤前拒绝转向, 跳格等不支持的状态, 防止转换丢失运动含义.
# English: check_states checks upstream endpoints and adjacent eastbound motion before conversion to
# shared Move route steps, rejecting unsupported states such as turns or jumps so conversion cannot lose
# motion semantics.
def check_states(states: list[tuple[int, ...]], start: int, target: int) -> Failure | None:
    if not states or states[0] != (start, 0, 0, 0, 0) or states[-1] != (target, 0, 0, 0, 0):
        return Failure("BACKEND_ERROR", "MAWPF returned invalid endpoints", ())
    previous = start
    for x, y, heading, speed, omega in states:
        if y or heading or omega or x not in (previous, previous + 1) or speed not in (0, 1):
            return Failure("BACKEND_ERROR", "MAWPF returned an unsupported transition", ())
        previous = x
    return None
