# TAPF / MAPF / TPG

[中文](README_ZH.md) | [English](README.md) | [한국어](README_KO.md)

<!-- doc-sync: readme / 2026-10-19-r2 -->

依据 Warehouse API 0.7 英文规范构建模块化仓库规划系统.
当前仅提供共享契约. 规划器适配层和 Runtime 尚未实现.

Python 3.10+:

```bash
python -m pip install .
python -c 'from warehouse_api.contracts import API_VERSION; print(API_VERSION)'
```

契约包运行时只依赖 Python 标准库. 安装时使用 setuptools.
从 `warehouse_api.contracts` 导入类型.

用户提供的 `warehouse_api_v0_7/` 是本地参考文档包.
安装本项目不需要它, 本 PR 也未将其整体入库.
契约文件保留原 API; review 中统一了字段说明的标点.
原件与当前文件的哈希见开发日志.
保留后端边界类型; 模拟器实现不在本次范围内.

- [模块边界与分批计划](docs/development/ROADMAP_ZH.md)
- [首个 PR: 来源与验证](docs/development/0001-contract-foundation_ZH.md)
- [开发与 review 规则](AGENTS.md)
