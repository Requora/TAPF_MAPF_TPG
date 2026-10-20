"""Check native path states before translating them to public route steps."""
from warehouse_api.contracts import Failure


# 中文: 检查原生路径的起终状态及逐格向东移动, 在转换为公开路线前拒绝越界能力, 防止静默丢弃上游转向或跳格.
# English: Check native endpoints and adjacent eastbound transitions before route conversion so
# unsupported turns or jumps are not silently discarded.
def check_states(states: list[tuple[int, ...]], start: int, target: int) -> Failure | None:
    if not states or states[0] != (start, 0, 0, 0, 0) or states[-1] != (target, 0, 0, 0, 0):
        return Failure("BACKEND_ERROR", "MAWPF returned invalid endpoints", ())
    previous = start
    for x, y, heading, speed, omega in states:
        if y or heading or omega or x not in (previous, previous + 1) or speed not in (0, 1):
            return Failure("BACKEND_ERROR", "MAWPF returned an unsupported transition", ())
        previous = x
    return None
