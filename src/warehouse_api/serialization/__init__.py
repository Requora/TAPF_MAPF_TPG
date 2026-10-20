"""中文: serialization 模块导出共享数据契约的 JSON 转换入口, 使实验输入和结果可保存及恢复.

English: The serialization module exports JSON conversion for shared contracts so experiment inputs and results can be saved and restored.
"""
from ._json import dumps, from_data, loads, to_data

__all__ = ['dumps', 'from_data', 'loads', 'to_data']
