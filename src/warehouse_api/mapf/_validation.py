"""Check native path states before translating them to public route steps."""
from warehouse_api.contracts import Failure


def check_states(states: list[tuple[int, ...]], start: int, target: int) -> Failure | None:
    if not states or states[0] != (start, 0, 0, 0, 0) or states[-1] != (target, 0, 0, 0, 0):
        return Failure("BACKEND_ERROR", "MAWPF returned invalid endpoints", ())
    previous = start
    for x, y, heading, speed, omega in states:
        if y or heading or omega or x not in (previous, previous + 1) or speed not in (0, 1):
            return Failure("BACKEND_ERROR", "MAWPF returned an unsupported transition", ())
        previous = x
    return None
