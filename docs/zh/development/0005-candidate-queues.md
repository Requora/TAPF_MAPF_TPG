# PR 5 - 候选队列编辑

[中文](../../zh/development/0005-candidate-queues.md) | [English](../../en/development/0005-candidate-queues.md)

<!-- doc-sync: candidate-queues / 2026-10-19-r1 -->

日期: 2026-10-19. 状态: 阶段 4 队列辅助函数已实现并通过 fixture 验证, 等待 review.
分支: `feat/candidate-queue-edits`. [PR #5](https://github.com/Requora/TAPF_MAPF_TPG/pull/5).
基线: GitHub 已确认 PR #4 合并至 `65e0738ea6e43f94b39c507bd49291ecb873f059`.

## 范围与来源

新增 `warehouse_api.queues.candidate_queues(request, draft)`, 返回
`tuple[RobotQueue, ...] | Failure`. 输入复用现有 `AssignmentRequest`
和 `TaskDelta` 契约. 输出是完整候选队列, 不是可放回新 TaskDelta 的后缀编辑.
未新增 DTO 或 Protocol. 这是阶段 4 的一个辅助函数;
尚未实现 `SharedCompiler.compile_jobs`.

来源: 本地 API 0.7 英文指南第 05-06 节, 以及 `DATA_TYPES_EN.md` 中的
TaskDelta, QueueState, AssignmentRequest 和 StepLock.
两份文件的 SHA256 仍为 `f13bb9275af485e8dcc2ae47e76db411bf8b38581175dd71a14b50f5b8713e7f`
和 `5c3ffe789c8f43061961fd89bb7c217781ecda259ddb8c26c8c5d06c7d601b05`.
代码为本仓库原创, 仅依赖标准库; 未集成上游求解器.

## 决策与可观察行为

对列出的机器人使用 `old[:locked_prefix_count] + proposed_suffix`.
省略队列表示保留原队列; 空后缀只清除可变部分. 缺少旧队列表示空闲.
按 join-state 输入顺序返回全部机器人的队列.
新定义可以不绑定; 已有未绑定任务可以分配.
移除绑定不删除定义, 不取消任务, 不释放预留.

统一检查全部最终绑定, 因此任务转移与编辑排列顺序无关.
未知任务/机器人引用, 重复定义/队列项, 无效前缀长度, 无效锁引用和
旧归属不一致返回 `BAD_INPUT`. 候选任务重复绑定, 包括同一队列内重复,
以及移除或更改 StepLock 执行者返回 `CONFLICT`.
每个失败包含诊断和相关 ID. 草稿不能隐式修复无效旧快照.
重复 StepLock 也作为无效输入拒绝.

本函数只覆盖 D1 中的显式锁部分, 不是完整 D1 验证.
函数信任 DTO 类型结构及传入的锁, 不从固定运动, 正在执行的动作或携带关系推导锁.
不验证任务动作语义, 投影进度, 阻塞任务执行, 库存/需求可行性, 几何或停车.
候选队列成功不代表可以执行. 任务 ID 新鲜性只对传入的已接受定义和本次草稿检查;
调用方必须保留历史 ID 才能保证整个 run 不复用.
成功和失败时, 全部请求字段和草稿数据均保持不变.

使用 `tests/test_queues.py` fixture 得到的真实函数输出:

| 案例 | 原状态 / 编辑 | 结果 |
| --- | --- | --- |
| 清空后缀 | R1=[A,B], prefix=1; R1 suffix=[] | R1=[A], R2=[C], R3=[] |
| 转移 B | R1 suffix=[], R2 suffix=[B,C] | R1=[A], R2=[B,C], R3=[] |
| 锁定 B | 相同转移; StepLock(B,0,R1) | CONFLICT; related_ids=[B,R1] |

使用真实辅助函数重放失败, 不是求解器或物理执行轨迹:

```bash
PYTHONPATH=src:tests python - <<'PY'
from dataclasses import replace
from test_queues import request_fixture
from warehouse_api.contracts import RobotQueue, StepLock, StepRef, TaskDelta
from warehouse_api.queues import candidate_queues
request = replace(request_fixture(), locks=(StepLock(StepRef('B', 0), 'R1'),))
draft = TaskDelta((), (RobotQueue('R1', ()), RobotQueue('R2', ('B', 'C'))))
print(candidate_queues(request, draft))
PY
```

```text
Failure(code='CONFLICT', message='StepLock executor cannot change or be removed', related_ids=('B', 'R1'))
```

## 验证与失败记录

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-queue-wheel .
/tmp/warehouse-ci-check/bin/python -m pip install --force-reinstall /tmp/warehouse-queue-wheel/warehouse_planning_api-0.7.0-py3-none-any.whl
/tmp/warehouse-ci-check/bin/python -m pip check
/tmp/warehouse-ci-check/bin/python -I -m unittest discover -s tests -v
git diff --check
```

Python 3.14.7: 源码和安装后的 wheel 均通过全部 44 项测试, 包含 11 项新增队列测试.
覆盖原子转移, 前缀边界, 空闲机器人, 定义新鲜性, 锁冲突, 无效快照, 输入不变及 JSON 重放.
Ruff 和 pip check 通过. 没有非预期测试失败.
最初 gh 探测因 CLI 缺失失败, 随后改用 GitHub connector 确认合并状态.
双语文档通过 gpt-6-luna / low 复核, 无发现项. 远端 CI 结果将在 PR 中记录.
未执行原生集成, 连续几何或停车验证.

## 行数与下一步

代码新增 255 行, 删除 0 行, 包含实现和测试. 文档行数在 PR 中单独披露; 配置不变.
等待用户 review 和合并后, 继续阶段 4 的携带归属, 投影剩余动作,
目标/资源解析和共用耗时集成.
