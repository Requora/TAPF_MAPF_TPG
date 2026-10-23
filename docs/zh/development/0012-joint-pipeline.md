# 联合规划编排

[中文](../../zh/development/0012-joint-pipeline.md) | [English](../../en/development/0012-joint-pipeline.md)

<!-- doc-sync: joint-pipeline / 2026-10-23-r1 -->

## 范围与决策

PR #11 合并于 `5e35ee0`, 开始前已确认远端状态. JointPipeline 用注入的 JointPlanner 替换独立分配和路径阶段. JointPlan 在 contracts.py 中组合已有 TaskDelta 与 FleetPlan. 公开 DecisionPipeline 输入输出不变. 不引入原生对象或新的跨模块导入.

共享编译器重新编译最终草稿, 保留进度, 锁和动作耗时. 既有规划校验在 TPG 前检查请求标识, 机器人覆盖和动作顺序. 求解器本身必须在搜索中使用共享编译语义; 最终检查不能证明路线几何正确. 联合搜索, 编译和运动共用一个墙钟截止时间. 同步调用不能被抢占; 迟到结果被丢弃. 只有 Runtime 可以验收和提交方案.

## 验证与失败记录

初始定向测试因 JointPlan 尚不存在而失败. 实现后 6 项定向测试通过. `PYTHONPATH=src python -m unittest discover -s tests` 运行 93 项: 89 通过, 4 项原生测试跳过. Ruff 和 git diff --check 通过. 未重跑原生规划器.

`PYTHONPATH=src:tests python -m planning.joint_replay` 打印实际 fixture 阶段输入输出和候选方案. 共享编译器为真实实现; 联合搜索和运动使用显式替身. 预期与实际阶段均为 joint -> compilation -> tpg; 动作为 lift, serve, drop. 本次运行保存于 `/tmp/warehouse-joint-replay.json`. 无效队列, 过期路线, 缺失/重复机器人和缺失动作均在运动前停止. 测试还覆盖失败, 异常, trace 重置, 输入不变和共享超时.

## PR 与下一步

创建后补充 PR 链接. 本轮实现编排并提供 fixture 证据, 不代表原生联合仓库求解器. review 和合并后, 下一步将受支持仓库任务适配到联合原生搜索. 连续几何, 无限期停车, Runtime 和执行仍未实现. 按用户要求优先主线, 独立网页修正已搁置; 本轮同步维护状态内容.
