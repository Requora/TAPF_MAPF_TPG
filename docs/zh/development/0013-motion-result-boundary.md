# 运动结果边界

[中文](../../zh/development/0013-motion-result-boundary.md) | [English](../../en/development/0013-motion-result-boundary.md)

<!-- doc-sync: motion-result-boundary / 2026-10-23-r1 -->

## 范围与决策

PR #12 已合并, 远端基线为 `5563fac`. 本轮修复 StagedPipeline 将缺失停车尾段等坏结果直接包装为 ExecutableProposal 的问题. 规则集中在 planning 的 `_validation.py`, 编排主体只调用检查并传递 Failure. 公开 API 和模块依赖不变.

检查 common_prefix 和 stop_tail 各覆盖 join_state 中每台机器人一次, 节点非空且数值有限, 时间严格递增, 旧状态到前缀与前缀到尾段精确衔接, 全车队前缀结束时刻一致, 尾段终点速度为零. 按机器人 ID 匹配, 不依赖返回顺序. 依据 API 0.7 参考包的 MotionPlan 和轨迹语义, 保留单节点静止保持; 单节点移动前缀不接受. target_end_s 是期望时间, 不在此强制等于结果终点.

此检查只负责结构. 动作时序, 运动限制, 连续几何, 资源容量和无限期停车占用仍待验证. 候选未被 Runtime 接受. 联合仓库适配和执行闭环仍为计划.

## 验证与失败记录

TDD: 15 个坏运动子用例最初全部错误返回 ExecutableProposal, 新检查后全部返回 BAD_INPUT. 测试还检查原始 TPG 结果仍留在 last_trace, 输入未变, 合法单节点尾段不被误拒绝. 双车替身检查返回顺序可变, 不同分支时刻被拒绝; 该用例不是多车原生集成证据.

`WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests -v`: 94 项, 93 通过, 1 项 CBS-TA 实验跳过. 完整输出在 `/tmp/motion-boundary-tests.log`. 真实 MAWPF/WinkTPG 链和 20 次成功边界组合均通过. 本轮复用已有二进制, 未重新构建. 上游版本仍为 MAWPF `0cdb8e4` 和 WinkTPG `dd96946`, 来源与构建记录见 [原生集成](0009-staged-pipeline.md).

`PYTHONPATH=src:tests python -m planning.replay` 提供 fixture 请求, 阶段 trace 与结果; `PYTHONPATH=src:tests python -m composition.replay /tmp/tapf-chain-bridges --output /tmp/motion-composition.json` 保留真实原生输出. 不用 fixture 代替连续安全证据. 当前 Python 环境没有 Ruff; 后续检查状态在下文记录.

## PR 与下一步

PR 待创建. 提交后等待 review, 不推进下一 PR. 进展网页同步当前工作和合并基线. 发布和最终检查结果待记录.

非有限值回归将 NaN/Inf 注入 x 坐标; 其他标量的有限性由同一检查覆盖, 未逐字段注入. Ruff 在独立工具环境安装后通过; JS 语法, diff 和网页双语/键盘/手机检查通过, 桌面与手机截图已检查. 初次 wheel 从旧 build/ 混入历史模块, 架构检查如期失败; 改用独立干净源码目录重建并重新验证.
