# PR 5 - 暂缓队列实现, 保留 API 0.7

[中文](../../zh/development/0005-candidate-queues.md) | [English](../../en/development/0005-candidate-queues.md)

<!-- doc-sync: candidate-queues / 2026-10-19-r2 -->

日期: 2026-10-19. 状态: 已记录范围决定, 等待 review; 没有新增运行行为.
分支: `feat/candidate-queue-edits`. [PR #5](https://github.com/Requora/TAPF_MAPF_TPG/pull/5).
基线: PR #4 已合并至 `65e0738ea6e43f94b39c507bd49291ecb873f059`.

## 范围与来源

保留 API 0.7 契约, 包版本 0.7.0 和原参考 fixture.
删除本 PR 的候选队列辅助函数及其 11 项测试. 相对 main, 本 PR 现在仅修改文档.
不新增替代接口或分配实现.

用户 review 确定本轮范围: 每台机器人只需要关注当前任务;
暂不需要的 API 字段保留, 按原语义可以为空.
用户提供的 API 0.7 指南和类型说明仍是规范. 本地参考包保持原样.

## 决策与可观察行为

保留 `RobotQueue`, `QueueState`, `locked_prefix_count` 及两个 `queues` 字段.
接口已定义不代表当前必须实现全部功能. 暂缓多任务队列调度和后缀编辑.
不迁移至 API 0.8.

例如, `TaskDelta(tasks=(), queues=())` 仍表示没有任务修改, 不清除已有绑定.
空值保留 API 0.7 原有含义; 本次决定不允许丢弃已知状态或忽略传入的锁.
当前任务编译, 动作锁及携带归属检查仍为计划.
本 PR 尚未实现 SharedCompiler, Runtime 或原子提交.

## 验证与失败记录

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
git diff origin/main -- src tests pyproject.toml AGENTS.md
git diff --check
```

Python 3.14.7: 原有 33 项测试全部通过. Ruff 通过. 相对 main 的代码/配置 diff 为空.
本地 160 个参考文件的哈希与本次 review 修正前的快照一致. 没有非预期测试失败.
尝试的 API 修改已在提交前撤回, 没有遗留版本或 schema 变更.
远端 CI 和双语复核结果记录在 PR 中.
未新增求解器运行, 连续几何或停车验证.

## 行数与下一步

相对 main: 代码 +0/-0, 配置 +0/-0. 文档行数在 PR 中单独披露.
等待 review 和合并后, 再在现有 API 内继续阶段 4 当前任务编译,
不提前实现暂不需要的队列功能.
