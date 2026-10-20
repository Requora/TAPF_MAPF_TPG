# PR 6 - 已接受当前任务编译器

[中文](../../zh/development/0006-current-task-compiler.md) | [English](../../en/development/0006-current-task-compiler.md)

<!-- doc-sync: current-task-compiler / 2026-10-20-r3 -->

日期: 2026-10-19. 状态: 阶段 4 受限实现, 已通过 fixture 验证, 等待 review.
分支: `feat/current-task-compiler`. [PR #6](https://github.com/Requora/TAPF_MAPF_TPG/pull/6).
基线: GitHub 确认 PR #5 已合并至 `526589d6c86341e9ce06ad313f029da854a2dba6`.

## 范围与来源

新增 `warehouse_api.compiler.CurrentTaskCompiler(model, sim_dt_s=...)`, 实现现有
`SharedCompiler.compile_jobs(request, draft)` 签名. 不修改契约.
仅编译已接受的当前任务. 每台机器人已有 QueueState 中最多一个任务.
省略队列表示空闲; 未绑定且未开始的任务保持未绑定.
空 TaskDelta 保留已有绑定. 任何非空草稿返回 UNSUPPORTED,
包括明确提出空后缀的草稿. 多任务队列仍不支持.
本次不实现分配, 重新分配或可变后缀替换.

来源: 本地 API 0.7 英文指南第 04-06 节及 DATA_TYPES_EN.md.
SHA256: 指南 `f13bb9275af485e8dcc2ae47e76db411bf8b38581175dd71a14b50f5b8713e7f`;
类型说明 `5c3ffe789c8f43061961fd89bb7c217781ecda259ddb8c26c8c5d06c7d601b05`.
仓库原创代码, 仅使用标准库; 未集成上游求解器.

## 决策与可观察行为

Review 重构: `_compiler_validation.py` 集中处理模型引用, 请求结构,
绑定, 动作锁, Lift 前置条件, 携带归属, 重复货架占用,
目标合法性及携货机器人无任务的检查. 模型使用 `model.nodes` 等显式属性访问,
不再用 getattr 遍历固定字段.
编译器在模型/请求入口, 每个未完成任务之前, 目标解析之后及返回 jobs 之前
调用校验. 编译器传递失败结果, 不内联构造失败.
编译器保留目标解析, 动作转换和候选状态记录.
失败码, 消息, 相关 ID 及检查顺序保持不变.
这些私有检查不实现阶段 9 安全 Validator.
AGENTS.md 记录此职责划分, 包括业务前置条件.

- 直接使用已预测到 join_state 的 next_step, 不重复推进进度.
- 每个未完成的已绑定任务只支持一个 Lift, Serve, Drop 序列.
  按模型顺序返回全部机器人, 空闲机器人的 actions 为空.
- Lift 仅支持唯一精确匹配的存储位姿, 且 carry_offset 为零.
  离散节点外或不唯一的取货位姿, 以及非零偏移, 返回 UNSUPPORTED.
  Serve 和 Drop 解析工作站/存储位的节点, 朝向和资源.
- 每个输出动作使用共用量化 action_duration_s. 保留 StepRef 和货架标识;
  不传递拣选项, 不预留库存.
- 独立于 locked_prefix_count 检查 StepLock 引用和执行者绑定.
  即使锁引用较早的动作, 也要求保留当前执行者.
- Lift 前要求机器人空载且货架落地. Lift 后要求同一机器人携带该货架.
  拒绝多个任务争用同一货架, 或携货机器人没有对应剩余任务.
- 续接状态有未完成动作时返回 UNSUPPORTED. 已绑定且未完成的 blocked
  任务返回 NO_PLAN, 不自动重试. 完成的任务不输出动作.
- 引用/状态语义错误返回 BAD_INPUT. 归属/动作锁冲突返回 CONFLICT.
  契约结构和耗时/配置错误保留原始异常, 不使用 try/except 隐藏错误.
  成功或失败都不修改输入.

使用 `tests/compiler/test_compiler.py:fixture`, sim_dt_s=0.1 的真实编译输出:

| 场景 | 机器人 A 的动作, 每个 0.3 s | 机器人 B | 结果 |
| --- | --- | --- | --- |
| next_step=0, 货架落地 | 0 Lift(home-node), 1 Serve(station-node), 2 Drop(return-node) | 空 | Jobs |
| next_step=1, carrier=A | 1 Serve(station-node), 2 Drop(return-node) | 空 | Jobs |
| next_step=3 | 空 | 空 | Jobs |
| 绑定 A, StepLock(T,0) 要求 B | 无部分结果 | 无部分结果 | CONFLICT |

最后一项诊断为 `Committed action executor must be preserved`, 相关 ID
为 `('T', 'B')`. 这是实际编译器 fixture 轨迹, 不是物理执行或求解器输出.

## 验证与失败记录

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-compiler-wheel .
/tmp/warehouse-ci-check/bin/python -m pip install --force-reinstall /tmp/warehouse-compiler-wheel/warehouse_planning_api-0.7.0-py3-none-any.whl
/tmp/warehouse-ci-check/bin/python -m pip check
/tmp/warehouse-ci-check/bin/python -I -m unittest discover -s tests -v
git diff --check
```

源码与安装后 wheel 的 49 项测试全部通过, 包含 16 项编译器测试.
Ruff 和 pip check 通过. 没有非预期测试失败. 首次 gh 状态查询因缺少 gh 失败,
随后通过 GitHub 连接器确认合并状态. 参考包的 160 个文件保持原样.
双语文档通过 gpt-6-luna / low 复核. 远端 CI 结果将在 PR 中记录.

Review 新增两种 Lift 失败场景的回归检查: 目标货架由 B 携带,
或 A 已携带另一货架. 两种场景均保留精确的 CONFLICT 诊断和输入快照.
模型检查覆盖五类索引集合的重复 ID, 以及未知的存储位/工作站节点和资源.
临时比较程序用 review 前 `6e47781` 的实现和重构实现运行编译器测试:
11 个 jobs 结果和 43 个 Failure 结果完全一致.
异常场景由单独运行的原始回归测试验证. 比较程序不作为仓库产物保存.

未执行分配器, MAPF/TPG/TAPF 集成, Runtime 提交, 库存/需求可行性,
连续几何, 资源调度或停车验证. 返回 jobs 仅为编译结果, 不是可接受的执行方案.

## 行数与下一步

相对 main 的代码 +412/-0, 包含 16 项测试. 文档行数包含 AGENTS.md,
在 PR 中单独披露; 构建/CI 配置不变.
等待用户 review 和合并. 之后继续阶段 4/5 所需的最小当前任务分配增量,
继续遵守暂缓多任务调度和后缀编辑的决定.
