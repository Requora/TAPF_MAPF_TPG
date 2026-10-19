# PR 4 - 共用动作耗时

[中文](../../zh/development/0004-action-durations.md) | [English](../../en/development/0004-action-durations.md)

<!-- doc-sync: action-durations / 2026-10-19-r1 -->

日期: 2026-10-19. 状态: 阶段 4 耗时函数已实现并通过单元测试, 等待 review.
分支: `feat/shared-action-durations`. [PR #4](https://github.com/Requora/TAPF_MAPF_TPG/pull/4).
基线: GitHub 已确认 PR #3 合并至 `b310d6ab19944eff0044a2d9ea5e6bfc1eae8a89`.

## 范围与来源

新增 `warehouse_api.durations.action_duration_ticks` 和 `action_duration_s`.
两者接收 `(action, times, *, sim_dt_s)`, 复用 `TaskAction` 和 `ActionTimes`.
未修改 DTO 或 Protocol. 这是阶段 4 的首个小改动, 尚未实现 SharedCompiler.
编译器和运动适配器将共用这些纯函数; 两处集成都尚未实现.

来源: 本地 API 0.7 英文指南第 06 节, 以及 `DATA_TYPES_EN.md` 中的
ActionTimes 和 PhysicalAction. 两份文件的 SHA256 分别为
`f13bb9275af485e8dcc2ae47e76db411bf8b38581175dd71a14b50f5b8713e7f` 和
`5c3ffe789c8f43061961fd89bb7c217781ecda259ddb8c26c8c5d06c7d601b05`.
代码为本仓库原创, 只依赖标准库; 未集成上游求解器.

## 决策与可观察行为

Lift 和 Drop 使用模型固定耗时. Serve 累加全部 pick 件数, 包含重复 SKU
和不同订单, 使用 `service_base_s + units * service_per_unit_s` 计算.
最后一次性向上取整为完整仿真步数.

规范要求共用向上量化, 但未指定浮点策略. 本实现通过 `str(value)`
把每个数值输入解释为精确十进制有理数. 使用 `Fraction` 计算服务公式,
再取整数上界, 不使用 epsilon. 这样 0.07 / 0.01 等十进制边界不会误加一步.
明确传入的 0.30000000000000004 仍大于 0.3, 必须增加一步.

整数步数是量化依据. 秒数由精确步数乘积一次转换为 float, 存在正常的浮点表示误差.
极大步数仍为精确整数; 秒数超出 float 范围时保留原始 OverflowError.
调用方比较时间网格时应保留整数步数.
这些函数计算完整动作耗时, 不计算续接点处正在执行动作的剩余耗时.

耗时校验集中在 `_duration_validation.py`. 拒绝非有限值, 负数, 布尔值和非数值时间;
sim_dt_s 必须大于零. 校验全部四个模型字段, 包括当前动作未用到的字段.
模型耗时允许为零. 动作必须为 Lift/Serve/Drop 且 kind 匹配;
Serve 的 picks 非空, 件数为正整数. 上述无效输入抛出 ValueError;
其他动作类型抛出 TypeError. 整数时间过大而无法通过有限数检查时,
保留原始 OverflowError. 不捕获异常. ID, 库存, 需求, 携带状态和任务序列
合法性不属于耗时校验范围. 输入保持不变, 不预留库存, 不写实时状态.

实际函数执行结果, 使用 `ActionTimes(0.21, 0.3, 0.1, 0.2)` 和 sim_dt_s=0.1:

| 输入 | 步数 | 秒数 |
| --- | --- | --- |
| Lift(P17) | 3 | 0.3 |
| Serve(S2), 一件商品 | 3 | 0.3 |
| Drop(H17) | 3 | 0.3 |
| 单独模型: lift_s=0.3 | 3 | 0.3 |
| 单独模型: lift_s=0.30000000000000004 | 4 | 0.4 |

以上为真实耗时函数输出, 不是求解器或物理执行轨迹.

## 验证与失败记录

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-duration-wheel .
/tmp/warehouse-ci-check/bin/python -m pip install --force-reinstall /tmp/warehouse-duration-wheel/warehouse_planning_api-0.7.0-py3-none-any.whl
/tmp/warehouse-ci-check/bin/python -m pip check
/tmp/warehouse-ci-check/bin/python -I -m unittest discover -s tests -v
git diff --check
```

Python 3.14.7: 源码与安装后的 wheel 均通过全部 33 项测试, 包含 10 项新增耗时测试.
独立 Decimal 计算核对了 80 种模型/网格组合. 其余覆盖相邻浮点数, 重复 pick,
零耗时, 无效输入, 次正规数网格, 极大步数, 溢出, 输入不变和 JSON 重放.
Ruff 与 pip check 通过. 149 个参考文件的哈希与原清单一致.
没有非预期测试失败. 最初 gh 探测因 CLI 缺失失败, 随后改用 GitHub connector
确认合并状态.

预期失败重放, 退出码 1, 保留原始 traceback:

```bash
PYTHONPATH=src python -c 'from warehouse_api.contracts import ActionTimes, Lift; from warehouse_api.durations import action_duration_s; action_duration_s(Lift("P17"), ActionTimes(1, 1, 0, 0), sim_dt_s=0)'
```

```text
ValueError: sim_dt_s: expected a positive time
```

澄清整数输入溢出后, 文档通过 gpt-6-luna / low 复核.
远端 CI 状态将在 PR 中记录.
未执行原生集成, 连续几何或停车验证.

## 行数与下一步

代码新增 184 行, 删除 0 行, 包含校验和测试.
文档行数在 PR 中单独披露; 配置不变.
等待用户 review 和合并后, 继续以小 PR 实现阶段 4 的候选队列后缀编辑,
D1 锁, 携带归属和剩余动作编译.
