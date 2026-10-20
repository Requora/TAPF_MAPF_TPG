"""中文: task_compiler 模块导出共享任务编译器, 使各规划阶段从相同任务语义生成执行动作.

English: The task_compiler module exports the shared task compiler so planning stages derive actions from the same task semantics.
"""
from ._current_task import CurrentTaskCompiler

__all__ = ['CurrentTaskCompiler']
