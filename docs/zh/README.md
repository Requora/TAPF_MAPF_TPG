# TAPF / MAPF / TPG

[中文](../zh/README.md) | [English](../en/README.md)

<!-- doc-sync: readme / 2026-10-19-r5 -->

依据 Warehouse API 0.7 英文规范构建模块化仓库规划系统.
当前提供共享契约, 严格 JSON 结构 codec, 已测试的 fixture 和可重放订单源.
规划器适配层和 Runtime 尚未实现.

Python 3.10+, 从仓库根目录运行:

```bash
python -m pip install .
python -c 'from warehouse_api.contracts import API_VERSION; print(API_VERSION)'
python -I -m unittest discover -s tests -v
```

契约包运行时只依赖 Python 标准库. 安装时使用 setuptools.
从 `warehouse_api.contracts` 导入类型.
使用 `warehouse_api.codec.loads(TargetType, text)` 解码, `dumps(value)` 编码.
解码检查类型和字段; 编码转换 JSON 兼容值.
这些操作不验证业务规则, 连续几何或安全停车.

用户提供的 `warehouse_api_v0_7/` 是本地参考文档包.
安装本项目不需要它, 本 PR 也未将其整体入库.
契约文件保留原 API; review 中统一了字段说明的标点.
原件与当前文件的哈希见开发日志.
保留后端边界类型; 模拟器实现不在本次范围内.

- [模块边界与分批计划](development/ROADMAP.md)
- [首个 PR: 来源与验证](development/0001-contract-foundation.md)
- [Codec: 范围, fixture 与验证](development/0002-contract-codec.md)
- [订单源: seed, 发布轨迹与验证](development/0003-order-source.md)
- [开发与 review 规则](../../AGENTS.md)
