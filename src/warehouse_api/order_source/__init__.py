"""中文: order_source 模块导出订单生成和重放入口, 让实验使用独立于任务分配的需求来源.

English: The order_source module exports order generation and replay so experiments have a demand source independent of task allocation.
"""
from ._replay import ReplayOrderSource, generate_orders

__all__ = ['ReplayOrderSource', 'generate_orders']
