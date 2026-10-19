# PR 2 - 严格契约 codec

[中文](../../zh/development/0002-contract-codec.md) | [English](../../en/development/0002-contract-codec.md)

<!-- doc-sync: codec / 2026-10-19-r1 -->

日期: 2026-10-19. 状态: 已实现并通过 fixture 验证, 等待 review.
分支: `feat/strict-contract-codec`. [PR #2](https://github.com/Requora/TAPF_MAPF_TPG/pull/2).
基线: 已确认 PR #1 合并, `16f65e361b2d78876c789eaa42374a59cd5c7afb`.

## 范围与来源

在 `warehouse_api.codec` 中添加 `to_data`, `from_data`, `dumps` 和 `loads`.
复用未修改的 `contracts.py` 中的数据类与注解.
依据用户提供的英文 API 0.7 指南第 03, 14 节和 `DATA_TYPES_EN.md`.
改编参考 `package/warehouse_api/codec.py`; 原件 SHA256 为
`c922f107b678f4500489e30309a90a536d602a5e26e18379ff80c6b8908798b2`.
用户提供的参考包保持原状, 不作为运行或 CI 依赖.
本 PR 不包含 JSON Schema 导出.

从参考 `package/examples/` 原样复制两个选定的 JSON fixture:

| `tests/fixtures/` 中的 fixture | SHA256 |
| --- | --- |
| `task_delta.json` | `344235fe4e58ec1becc9801cb7b19978fc7038c3b9f07225f58ce33f5e5f94ff` |
| `fleet_plan.json` | `729232b1b3ae29a5c1d0f6741f573dff303f82297aba583ef1feb9691e9a9dca` |

## 决策与可观察行为

解码检查嵌套字段, 必填值, 精确标量类型, Literal,
联合类型和同类型元组数组. 可空字段仍须提供, 除非契约定义了默认值.
省略动作判别字段时使用其默认值.
JSON 整数可用于浮点字段; 布尔值不能用于数值字段.
构造新的冻结契约与元组, 不修改输入.

拒绝重复 JSON 键, 非字符串字典键, 非有限数和超出浮点范围的数字.
不静默保留重复键的最后一个值, 不将字典键强制转换成字符串.
编码转换数据类与 JSON 兼容值, 不重新检查字段注解.

测试中观察到的失败重放:

```text
Order.items[0].quantity = true
ValueError: $.items[0].quantity: expected int
{"x_m":0,"x_m":1,"y_m":0}
ValueError: Duplicate JSON field: x_m
```

结构检查有意接受整数数量 -1 和两个均为空的货架位置字段.
业务与安全验证器必须拒绝这类语义错误.
fixture 验证不能证明连续几何或停车安全.
未添加原生求解器, 模拟器, IPC 或 Runtime 实现.

## 验证与失败记录

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m venv /tmp/warehouse-codec-check
/tmp/warehouse-codec-check/bin/python -m pip install "$PWD"
/tmp/warehouse-codec-check/bin/python -I -m unittest discover -s tests -v
git diff --check
```

Python 3.14.7 上的实际结果: 从源码和新建 venv 运行, 12 项测试全部通过.
实际隔离验证使用 `/tmp/warehouse-codec-e0vywp9w`, 从 `/tmp` 运行,
通过绝对路径选择本仓库的测试. codec 从该 venv 的 `site-packages` 导入,
未导入参考包. 空白检查通过. 没有测试失败.

额外本地检查解码并往返转换了九个参考 payload:
backend_init, planning_request, task_delta, path_request, fleet_plan, motion_request,
proposal, ideal_control_frame 和 observation. 仅提交两个选定 fixture;
其余七项检查是本地证据, 不属于 CI 覆盖.
未测试后端配置 payload 和 JSON Schema 验证.

CI 在 Python 3.10 和 3.14 上对安装后的包运行 12 项测试.
远端结果见 PR; 本地仅运行了 Python 3.14.7.
首次 `gpt-6.1-sol` / `low` 文档检查通过. 按用户最新要求,
AGENTS.md 的文档检查配置已改为 `gpt-6-luna` / `low`.
修订后的文档已按新配置复核通过.
参考 SHA256 清单中的 149 个文件仍全部匹配.
首次探测 `gh` 因未安装 CLI 失败; GitHub connector 确认了已合并基线.
猜测的参考测试文件名不存在; 文件检索找到 `test_contracts.py`.
两项问题均未修改参考包.

## 行数与下一步

相对 main: 新增 Python 236 行, fixture 76 行, 共 312 行, 无删除.
保守地将 fixture 计入代码预算. CI 新增配置 2 行.
Git 将两个 JSON fixture 末尾未换行的内容各计为一行; 初次 `wc -l` 总计少了两行.
文档单独计数并在 PR 描述披露.
等待用户 review 和合并, 之后才开始阶段 3 的带 seed 订单源.
