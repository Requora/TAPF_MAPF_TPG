# PR 1 - 共享契约与 review 流程

[中文](0001-contract-foundation_ZH.md) | [English](0001-contract-foundation.md) | [한국어](0001-contract-foundation_KO.md)

<!-- doc-sync: foundation / 2026-10-19-r2 -->

日期: 2026-10-19. 状态: review 修正已准备, 等待用户 review 和合并.
分支: `feat/api-contract-foundation`. [PR #1](https://github.com/Requora/TAPF_MAPF_TPG/pull/1).

## 范围与来源

初始仓库在 `4f0109145ca3fbe3a8130a3cb94c757e2544d17e` 时只有 README.md 和 .gitignore.
用户提供了未跟踪的 `warehouse_api_v0_7/` 参考包.
已阅读英文指南, 类型定义, 参考代码及验证记录.
保持参考包原状, 仅将共享契约引入开发包.

`src/warehouse_api/contracts.py` 最初复制自
`warehouse_api_v0_7/package/warehouse_api/contracts.py` (445 行).
本次 review 仅将中文字段说明中的标点改为英文标点.
文件不再与原件字节一致; API 字段, 默认值, 类型和 Protocol 均未改变.

- 原件 SHA256: `8608f438a78470fae3535dbc0b1180583a7ae83875921bf717251a2518318bbd`.
- 当前 SHA256: `ad02ec8870b84e01389ba8d8ef986038bf4dccb63e295a2cbc92cf0b1e13906a`.

生产代码导入本包, 不导入参考包. 本 PR 增加打包配置, 导入 CI, 开发规则和模块/调研计划.
保留后端边界类型, 不实现模拟器. 尚未构建或集成任何原生求解器.

## 验证

初始基线命令, 从仓库根目录运行:

```bash
PYTHONPATH=warehouse_api_v0_7/package python -m unittest discover -s warehouse_api_v0_7/package/tests -v
```

结果: Python 3.14.7 上 38 项通过. 首次在参考包目录运行时找不到 `python`;
改用根目录 shell 和显式 PYTHONPATH 后解决. 此环境问题未要求修改源码.

最初使用 `python -m pip install /home/yimin/research/TAPF_MAPF_TPG`
在临时 venv 中构建安装本包. 在仓库外使用 `python -I` 加载已安装的包,
解析 72 个类和 82 个带注解方法. 此检查不依赖参考包或源码路径导入.

本次 review 的 AST 对比只忽略字段辅助函数 `F` 的第一个参数.
其余 AST 节点与参考代码一致. 注解解析再次通过.
以下命令让 38 项参考测试使用修改后的源码契约:

```bash
PYTHONPATH=src python - <<'PYTHON'
from pathlib import Path
import unittest, warehouse_api
warehouse_api.__path__.append(str(Path('warehouse_api_v0_7/package/warehouse_api').resolve()))
suite = unittest.defaultTestLoader.discover('warehouse_api_v0_7/package/tests')
result = unittest.TextTestRunner().run(suite)
raise SystemExit(not result.wasSuccessful())
PYTHON
```

实际观察: 契约来自 `src/warehouse_api/contracts.py`; 72 个类和 82 个带注解方法解析成功;
38 项测试通过. 参考辅助模块由上述包搜索路径提供, 未包含在本 PR 中.

review 前提交 `8d1e4f1` 的 Python 3.10 和 3.14 CI 已通过:
[run 39304485036](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39304485036).
修改后提交的 CI 见 PR 检查页. 这些测试不证明生产规划器, Runtime,
连续碰撞检查或原生模拟器的正确性.

## Review 修正

- 已由 `gpt-6.1-sol` 模型, `low` 推理强度的 subagent 只读检查全部 12 份文档.
  三语一致性, 标点, 本地链接, 修订标识, 已记录哈希和行数均未发现问题.
  本次未重新核验远程链接及上游结论. AGENTS 已要求文档检查使用此委派方式.
- [三语同步](https://github.com/Requora/TAPF_MAPF_TPG/pull/1#discussion_r4317490698): README, 规则, 开发计划和本日志均提供中英韩三版, 增加语言链接和一致的修订标识.
- [英文标点](https://github.com/Requora/TAPF_MAPF_TPG/pull/1#discussion_r4317495406): 统一项目文档和契约字段说明的标点, 保留用户提供的参考包原状.
- [表达原则](https://github.com/Requora/TAPF_MAPF_TPG/pull/1#discussion_r4317507084): 在 AGENTS 中补齐要求的六条原则, 包括接近 80% ASD-STE100, 真实轨迹, 标注教学简化, 仅采用有助理解的可视化.
- 用户在聊天中明确: 文档和配置不计入 500 行限制. 三语规则同步更新.

相对 main 新增代码 446 行 (契约 445 + 包入口 1), 无代码删除.
打包和 CI 共 39 行配置, 单独统计. 文档也单独统计.
代码计数包含注释和空行, 因此有效代码行数仍低于 500.

## 发布与下一步

SSH 推送成功, 但首次通过 GitHub 连接读取仓库和创建 PR 均返回 HTTP 404.
本地没有已认证的 CLI 可供替代. 用户为组织安装并授权连接后,
重试成功, PR #1 于 2026-10-19 创建. 访问问题已解决.

在同一个 PR 中 review 本次修正. 未开始后续开发阶段.
用户合并后, 确认远端合并状态, 再开始下一小步 codec/fixture PR.
不自行合并或自动解决用户的 review 线程.
