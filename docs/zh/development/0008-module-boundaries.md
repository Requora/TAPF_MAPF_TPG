# 模块拆分与 API 边界

[中文](../../zh/development/0008-module-boundaries.md) | [English](../../en/development/0008-module-boundaries.md)

<!-- doc-sync: module-boundaries-log / 2026-10-20-r1 -->

## 范围与来源

状态: 模块重构已通过 fixture 和安装验证, 等待 review. 分配增量暂停.
分支: `refactor/module-boundaries`. [PR #8](https://github.com/Requora/TAPF_MAPF_TPG/pull/8).
GitHub 已确认 PR #7 合并, 基线为 `6dbed6cdaddb21c9ecf50644eae7ff82b76a386a`.
来源为该基线的既有代码, API 0.7 不变; 无新增上游依赖或原生集成.
用户参考包保持原状, 未加入 PR.

## 决策与结构

按用户要求, 先将 orders, compiler, durations, codec 各自放入独立目录.
包入口显式导出公开 API, 内部实现和校验留在各自包内. 测试和 fixture 同步归类.
统一契约仍为 `contracts.py`, 不复制 DTO 或 Protocol. 保留既有公开导入,
因此现有调用者不必随文件移动修改业务代码.
[目录图与依赖规则](../architecture/MODULES.md)区分已实现模块和后续接口规划.
新增静态依赖门禁, 用被拒绝的内部导入和反向依赖样例检验门禁本身.
AGENTS 明确模块目录规则, 并保留用户要求的 500 行限制不计文档说明.
历史日志中的 fixture 和重放路径已更新, 历史验证结论不变.

## 真实重放

以下为真实编译器的 fixture 输出, 不是运动执行轨迹:

| 输入 | 预期与实际结果 |
| --- | --- |
| 空闲机器人, 新任务绑定 B | A 无动作; B 为 lift, serve, drop, 各 0.3 s |
| 已有任务与 B 新任务使用同一货架 | CONFLICT, related_ids 为 ('new-task', 'shelf') |

```bash
PYTHONPATH=src:tests python - <<'PYTHON'
from dataclasses import replace
from compiler.test_compiler import fixture
from warehouse_api.compiler import CurrentTaskCompiler
from warehouse_api.contracts import Failure, RobotQueue, TaskDelta
model, accepted = fixture()
compiler = CurrentTaskCompiler(model, sim_dt_s=0.1)
task = replace(accepted.tasks[0].task, id='new-task')
draft = TaskDelta((task,), (RobotQueue('B', (task.id,)),))
for name, request in [('idle', replace(accepted, tasks=(), queues=())), ('shelf-conflict', accepted)]:
    result = compiler.compile_jobs(request, draft)
    if isinstance(result, Failure):
        print(name, result)
    else:
        print(name, [(job.robot_id, [(action.kind, action.duration_s) for action in job.actions]) for job in result])
PYTHON
```

## 验证与失败记录

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-modules-4v_xlj0q/wheels /tmp/warehouse-modules-4v_xlj0q/project
/tmp/warehouse-modules-4v_xlj0q/venv/bin/python -m pip check
/tmp/warehouse-modules-4v_xlj0q/venv/bin/python -I -m unittest discover -s tests
git diff --check
```

源码和全新虚拟环境中的 wheel 均通过 64 项测试: 61 项原有行为测试,
3 项新增 API/依赖检查. Ruff, pip check 和 diff 检查通过.
本地存在旧 build/lib 文件, 因此在全新临时目录复制 pyproject.toml 与 src 构建,
排除缓存和 egg-info; 新建 venv 后安装 wheel, 避免旧产物影响验证.
上述临时目录为本次证据路径, 重新验证时需创建新的干净构建目录和环境.
没有测试失败. 双语文档已通过 gpt-6-luna / low 复核, 并实际重放上述命令.
远端 CI 已由 PR 触发, 结果待确认.

尚未验证历史 pickle 兼容性, 动态导入约束, 分配优化, 原生求解器,
Runtime 提交, 连续几何或停车安全. 本轮只重构模块边界.

## 行数与下一步

Git 识别文件移动后, 相对 origin/main 的代码和测试 +125/-5, 共 130 行.
不识别重命名时为 +1601/-1481, 其中包含完整文件搬移.
文件搬移没有压缩或重写算法. 文档另计, 无配置变更.
提交后等待用户 review 和合并; 之后才继续独立 allocation 模块的最小增量.
