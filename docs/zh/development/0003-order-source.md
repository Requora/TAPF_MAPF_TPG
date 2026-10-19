# PR 3 - 可重放订单源

[中文](../../zh/development/0003-order-source.md) | [English](../../en/development/0003-order-source.md)

<!-- doc-sync: order-source / 2026-10-19-r5 -->

日期: 2026-10-19. 状态: 已实现, 本地单元测试通过, 等待 review.
分支: `feat/replayable-order-source`. [PR #3](https://github.com/Requora/TAPF_MAPF_TPG/pull/3).
基线: 已通过 GitHub 确认 PR #2 合并至 `8412ad1a7733e6e19b9642fa9ef4dc287e54aca7`.

## 范围与来源

新增 `warehouse_api.orders.ReplayOrderSource` 和 `generate_orders`.
复用 `contracts.Order`, `Item` 和 `OrderSource` Protocol, 未修改契约.
依据本地 API 0.7 英文指南第 05A 节和 `DATA_TYPES_EN.md` 的 Order/Item 说明.
实现为本仓库原创 Python 代码, 只使用标准库, 无上游算法集成.

| 参考文件 | SHA256 |
| --- | --- |
| `warehouse_api_v0_7_visual_EN.md` | `f13bb9275af485e8dcc2ae47e76db411bf8b38581175dd71a14b50f5b8713e7f` |
| `DATA_TYPES_EN.md` | `5c3ffe789c8f43061961fd89bb7c217781ecda259ddb8c26c8c5d06c7d601b05` |

## 决策与可观察行为

`reset(orders)` 先验证全部输入, 合并同一订单内的重复 SKU, 按 SKU 排序,
再按 `(released_at_s, id)` 排序订单并清除游标. 输入保持不变.
`release(until_s)` 包含时间边界, 每个订单仅返回一次. 重复时间返回空元组.
时间倒退或 reset 验证失败时, 原发布游标和时间保持不变.

本实现拒绝重复订单 ID, 空白 ID/SKU, 空需求, 非正整数数量和无效时间.
时间必须有限且非负, 布尔值不视为数字. 软截止可以早于发布时间;
`None` 禁用截止目标. 空订单集合允许 reset. 错误直接抛出, 不捕获异常.

生成器参数显式传入: `seed`, `count`, `skus`, `release_interval_s=1.0`,
`max_quantity=5`, `due_after_s=None`. 从时间零开始, 每隔固定时间生成一单,
ID 为 `order-0`, `order-1` 等. SKU 目录排序后, 均匀抽取 1 到目录长度的
SKU 数量, 无放回抽取 SKU, 再为每个 SKU 均匀抽取 1 到 max_quantity 的数量.
重复目录 SKU 被拒绝. 零间隔允许同时发布, 同时发布时 ID 按字典序排序.
每次调用使用私有 RNG, 不改变全局随机状态. 相同参数与 Python 版本可重现.
跨 Python 版本应保存生成的 Order JSON; 不承诺跨版本随机序列一致.
多个生成批次 ID 会重复; 本 PR 不提供批次合并或库存可行性保证.

实际执行轨迹, 输入依次为 B@2, A@2, Z@0. B 含 Y:1, X:2, X:3:

| 调用 | 返回订单与关键需求 |
| --- | --- |
| `release(0.0)` | Z, Y:2 |
| `release(0.0)` | 空 |
| `release(1.999)` | 空 |
| `release(2.0)` | A, X:1; B, X:5 + Y:1 |
| `release(2.0)` | 空 |
| `reset(orders); release(2.0)` | Z, A, B |

执行 `generate_orders(seed=17, count=3, skus=("X", "Y"), release_interval_s=2.0)`:
Python 3.14.7 返回时间 0, 2, 4, 需求分别为 X:3 + Y:2, X:2 + Y:4, X:4 + Y:2.
每单截止为 None. 这些是订单模块真实运行结果, 不是求解器轨迹.

## 验证与失败记录

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m venv /tmp/warehouse-orders-check
/tmp/warehouse-orders-check/bin/python -m pip install "$PWD"
(cd /tmp && /tmp/warehouse-orders-check/bin/python -I -m unittest discover -s /home/yimin/research/TAPF_MAPF_TPG/tests -v)
git diff --check
```

Python 3.14.7 上源码与独立安装包均通过 23 项测试, 其中 9 项新增订单测试.
包括有序发布, SKU 合并, reset 重放, 不重复发布, 时间倒退, 失败不改变状态,
seed 重现, 全局 RNG 隔离, 参数拒绝及生成时间溢出检查. 没有非预期测试失败.
149 个参考文件的 SHA256 全部匹配. 空白检查通过.
最初 CI 在 Python 3.10 和 3.14 上运行全部测试; 当前设置见下文 CI 配置.
文档已通过 `gpt-6-luna` / `low` 检查, 双语一致性, 英文标点, 链接和技术事实均无问题.

失败重放, 预期退出码 1, 保留原始 traceback:

```bash
PYTHONPATH=src python -c 'from warehouse_api.orders import ReplayOrderSource; s = ReplayOrderSource(); s.release(2.0); s.release(1.0)'
```

```text
ValueError: until_s: time moved backward from 2.0 to 1.0
```

本轮初次探测 `gh` 失败, 原因为 CLI 未安装; 随后使用 GitHub connector 确认合并状态.
未实现 Runtime, 分配器或原生求解器, 未验证连续几何或停车安全.

## Review 修正: 集中输入校验

按用户要求, 将订单输入检查和错误消息集中到内部模块 `_order_validation.py`.
`reset`, `release` 和 `generate_orders` 分别调用 `validate_orders`,
`validate_release_time` 和 `validate_generation_parameters`. 主流程不再包含 raise 分支.
校验规则, 异常类型和错误消息不变. reset 先完成校验, 再合并 SKU 和重置状态.
原有 23 项测试在源码与重新安装的隔离包上再次通过, 未新增测试.
隔离安装命令使用 `pip install --force-reinstall "$PWD"`, 其余验证命令同上.
本次修订的 CI 状态见 PR; 文档已通过 `gpt-6-luna` / `low` 复核.

## Review 修正: 整理已有 codec

按用户要求, 同样整理之前的 `codec.py`. 输入结构检查, 标量解码校验和
JSON 重复键/非有限常量处理集中到内部模块 `_codec_validation.py`.
`to_data`, `from_data` 和 `loads` 调用对应函数, 主流程不再包含 raise 分支.
联合类型分支选择与递归转换保留在 codec; 未增加异常捕获.
公共接口, 异常类型, 错误路径与消息不变, 超大整数仍直接抛出原始 OverflowError.
已检查全部 `src/warehouse_api/` 文件; 显式 raise 现在仅存在于两个校验模块.
`contracts.py` 与 `__init__.py` 无同类报错分支, 不需要修改.
原有 23 项测试在源码与重新安装的隔离包上再次通过, 未新增测试.
本次修订的 CI 状态见 PR. 双语文档已通过 `gpt-6-luna` / `low` 复核.

## CI 配置

按用户要求, 将已有 Contracts workflow 扩展为 CI, 文件仍为
`.github/workflows/contracts.yml`. PR 更新, main 推送和手动触发均可运行;
手动触发入口需该 workflow 合并到默认分支后可用. 分支推送不重复运行 PR 检查.
采用 contents: read 权限, 同一 ref 的新运行取消旧运行.

- Static checks: 固定 Ruff 0.14.0, 用 E9/F 规则检查 src 和 tests, 超时 5 分钟.
- Tests (Python 3.14): 构建 wheel, 安装 wheel, 执行 pip check,
  在 Python 隔离模式运行全部 23 项测试及契约注解检查, 超时 10 分钟.
  按用户要求取消多版本矩阵, CI 仅使用 Python 3.14.
- CI gate: 汇总静态检查与测试任务, 只有全部成功才通过, 超时 2 分钟.
  它提供固定检查名称; 本次未修改 GitHub 分支保护设置.

本地 Python 3.14.7 已通过 Ruff, wheel 构建/安装, pip check, 23 项测试和注解检查.
隔离环境为 `/tmp/warehouse-ci-check`, 安装命令为 `python -m pip install ruff==0.14.0`;
其余命令见 workflow. 本地 wheel 输出至该环境的 dist 目录.
CI gate 的 16 种 success/failure/cancelled/skipped 组合均已检查,
只有 success/success 返回 0. Ruff 对 stdin 中的 `print(undefined_ci_probe)`
返回 F821 和退出码 1. 这些为预期失败探针, 没有修改项目文件.
本次实际远端测试结果见 PR 的 CI 链接. 双语文档经 gpt-6-luna / low 复核, 已同步单版本配置和完整测试说明.

配置参考 [GitHub 并发说明](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
和 [Ruff 0.14.0 发布记录](https://github.com/astral-sh/ruff/releases/tag/0.14.0).
CI 不运行原生求解器, 连续几何或停车验证.

## 行数与下一步

相对 main: Python +383/-54, 共 437 行变更, 低于 500 行限制.
订单实现与测试 +287, codec 校验模块 +83, codec 主流程 +13/-54.
配置 +59/-10, 包含 workflow 与 Ruff 配置. 文档单独在 PR 描述披露.
保守地计入 workflow 中变更的可执行命令 +8/-2, 代码预算为 447 行.
等待用户 review 和合并后, 才开始阶段 4 的共享任务编译器.
