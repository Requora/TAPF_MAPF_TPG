# TAPF / MAPF / TPG

[中文](../zh/README.md) | [English](../en/README.md)

<!-- doc-sync: readme / 2026-10-20-r13 -->

依据 Warehouse API 0.7 英文规范构建模块化仓库规划系统.
当前提供共享契约, 严格 JSON 结构 codec, 已测试的 fixture, 可重放订单源, 共用动作耗时和受限当前任务编译器.
当前开发关注每台机器人的当前任务; 暂不实现队列调度, 保留 API 中未使用的字段.
规划器适配层和 Runtime 尚未实现.

Python 3.10+, 从仓库根目录运行:

```bash
python -m pip install .
python -c 'from warehouse_api.contracts import API_VERSION; print(API_VERSION)'
python -I -m unittest discover -s tests -v
```

契约包运行时只依赖 Python 标准库. 安装时使用 setuptools.
从 `warehouse_api.contracts` 导入类型.
使用 `warehouse_api.serialization.loads(TargetType, text)` 解码, `dumps(value)` 编码.
解码检查类型和字段; 编码转换 JSON 兼容值.
这些操作不验证业务规则, 连续几何或安全停车.

CI 在 PR 更新和 main 推送时运行 Ruff 静态检查, 并在 Python 3.14
上构建和测试 wheel. 汇总结果见 `CI gate`. 本地静态检查命令:

```bash
python -m pip install ruff==0.14.0
ruff check src tests
```

用户提供的 `warehouse_api_v0_7/` 是本地参考文档包.
安装本项目不需要它, 本 PR 也未将其整体入库.
契约文件保留原 API; review 中统一了字段说明的标点.
原件与当前文件的哈希见开发日志.
保留后端边界类型; 模拟器实现不在本次范围内.

- [模块边界与分批计划](development/ROADMAP.md)
- [首个 PR: 来源与验证](development/0001-contract-foundation.md)
- [Codec: 范围, fixture 与验证](development/0002-contract-codec.md)
- [订单源: seed, 发布轨迹与验证](development/0003-order-source.md)
- [动作耗时: 量化策略, 轨迹与验证](development/0004-action-durations.md)
- [Review 决定: 暂缓队列实现, 保留 API](development/0005-candidate-queues.md)
- [开发与 review 规则](../../AGENTS.md)
- [当前任务编译: 动作锁和携带归属](development/0006-current-task-compiler.md)
- [新任务绑定: 空闲机器人和候选检查](development/0007-current-task-bindings.md)

- [模块目录, 公开 API 与依赖图](architecture/MODULES.md)
- [模块拆分: 兼容性与验证](development/0008-module-boundaries.md)

- [项目进展与交互架构网页, 私有访问](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site)
