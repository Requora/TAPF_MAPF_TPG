"""中文: 该模块保存原生调用命令, 标准输出, 错误输出, 退出状态和实际耗时, 使上游运行结果可追溯.

English: This module retains native commands, stdout, stderr, exit status and elapsed wall time so upstream results remain traceable.
"""
import json
from pathlib import Path
import subprocess
from time import monotonic

from warehouse_api.contracts import Failure


# 中文: run_native 在剩余实际计算时间内运行已编译的上游桥接程序, 清理旧输出并保存命令, 标准输出, 错误输出及退出信息, 让调用可追溯且过期结果不会被当成新方案.
# English: run_native executes a compiled upstream bridge within the remaining wall-clock budget, removes
# stale output and retains the command, stdout, stderr and exit details so calls are traceable and
# expired output cannot become a new plan.
# 中文: 可选 cwd 指定子进程工作目录, 将上游辅助输出限制在证据目录内, 不改变调用者目录.
# English: Optional cwd selects the child working directory to contain upstream side files without changing the caller's directory.
def run_native(command: list[str], output: Path, *, budget_s: float, request_id: str,
               cwd: Path | None = None) -> Failure | None:
    if budget_s <= 0:
        return Failure("TIMEOUT", "Native process budget exhausted", (request_id,))
    output.unlink(missing_ok=True)
    started = monotonic()
    with output.with_suffix(".stdout").open("w") as stdout, output.with_suffix(".stderr").open("w") as stderr:
        try:
            result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=budget_s, cwd=cwd)
        except subprocess.TimeoutExpired:
            code = None
        else:
            code = result.returncode
    elapsed = monotonic() - started
    output.with_suffix(".run.json").write_text(json.dumps({
        "request_id": request_id, "command": command, "budget_s": budget_s,
        "elapsed_s": elapsed, "exit_code": code, "timed_out": code is None,
        "cwd": str((cwd or Path.cwd()).resolve()),
    }, indent=2))
    if code is None or elapsed > budget_s:
        return Failure("TIMEOUT", "Native process exceeded budget; result discarded", (request_id,))
    if code:
        return Failure("NO_PLAN" if code == 3 else "BACKEND_ERROR",
                       f"Native process exit {code}; evidence: {output.with_suffix('.run.json')}", (request_id,))
    if not output.is_file():
        return Failure("BACKEND_ERROR", "Native process produced no output", (request_id,))
    return None
