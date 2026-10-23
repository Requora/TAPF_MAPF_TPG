"""中文: 本模块集中校验原生进程的调用配置, 防止路径歧义在进程启动前破坏执行证据.

English: This module validates native process call configuration so ambiguous paths cannot damage evidence before execution.
"""
from pathlib import Path


# 中文: check_output_path 拒绝指定工作目录时的相对结果路径, 使父子进程使用同一输出位置, 并在任何文件副作用前报告配置错误.
# English: check_output_path rejects relative result paths with a working directory so parent and child share one output location and configuration errors precede file side effects.
def check_output_path(output: Path, cwd: Path | None) -> None:
    if cwd is not None and not output.is_absolute():
        raise ValueError("run_native requires absolute output when cwd is provided")
