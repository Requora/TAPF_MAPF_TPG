"""中文: native_process 模块导出带计算时间预算和执行证据的进程调用入口, 供原生适配器复用.

English: The native_process module exports budgeted process execution with retained evidence so native adapters can reuse one entry point.
"""
from ._run import run_native

__all__ = ["run_native"]
