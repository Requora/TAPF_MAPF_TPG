"""Retain the command, stdout, stderr, exit status, and elapsed wall time."""
import json
from pathlib import Path
import subprocess
from time import monotonic

from warehouse_api.contracts import Failure


def run_native(command: list[str], output: Path, *, budget_s: float, request_id: str) -> Failure | None:
    if budget_s <= 0:
        return Failure("TIMEOUT", "Native process budget exhausted", (request_id,))
    output.unlink(missing_ok=True)
    started = monotonic()
    with output.with_suffix(".stdout").open("w") as stdout, output.with_suffix(".stderr").open("w") as stderr:
        try:
            result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=budget_s)
        except subprocess.TimeoutExpired:
            code = None
        else:
            code = result.returncode
    elapsed = monotonic() - started
    output.with_suffix(".run.json").write_text(json.dumps({
        "request_id": request_id, "command": command, "budget_s": budget_s,
        "elapsed_s": elapsed, "exit_code": code, "timed_out": code is None,
    }, indent=2))
    if code is None or elapsed > budget_s:
        return Failure("TIMEOUT", "Native process exceeded budget; result discarded", (request_id,))
    if code:
        return Failure("NO_PLAN" if code == 3 else "BACKEND_ERROR",
                       f"Native process exit {code}; evidence: {output.with_suffix('.run.json')}", (request_id,))
    if not output.is_file():
        return Failure("BACKEND_ERROR", "Native process produced no output", (request_id,))
    return None
