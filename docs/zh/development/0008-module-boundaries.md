# 模块拆分与 API 边界

[中文](../../zh/development/0008-module-boundaries.md) | [English](../../en/development/0008-module-boundaries.md)

<!-- doc-sync: module-boundaries-log / 2026-10-20-r4 -->

## 范围与来源

状态: 模块重构已通过 fixture 和安装验证, 等待 review. 分配增量暂停.
分支: `refactor/module-boundaries`. [PR #8](https://github.com/Requora/TAPF_MAPF_TPG/pull/8).
GitHub 已确认 PR #7 合并, 基线为 `6dbed6cdaddb21c9ecf50644eae7ff82b76a386a`.
来源为该基线的既有代码, API 0.7 不变; 无新增上游依赖或原生集成.
用户参考包保持原状, 未加入 PR.

## 决策与结构

按用户要求, 将 order_source, task_compiler, action_timing, serialization 各自放入独立目录.
包入口显式导出公开 API, 内部实现和校验留在各自包内. 测试和 fixture 同步归类.
统一契约仍为 `contracts.py`, 不复制 DTO 或 Protocol. 按用户 review 改为明确的职责名称,
旧包导入需迁移到新名称, 不保留旧别名; 类名, 函数名和 JSON 契约不变.
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
from task_compiler.test_task_compiler import fixture
from warehouse_api.task_compiler import CurrentTaskCompiler
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
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-names-7vku970l/wheels /tmp/warehouse-names-7vku970l/project
/tmp/warehouse-names-7vku970l/venv/bin/python -m pip check
/tmp/warehouse-names-7vku970l/venv/bin/python -I -m unittest discover -s tests
git diff --check
```

源码和全新虚拟环境中的 wheel 均通过 64 项测试: 61 项原有行为测试,
3 项新增 API/依赖检查. Ruff, pip check 和 diff 检查通过.
本地存在旧 build/lib 文件, 因此在全新临时目录复制 pyproject.toml 与 src 构建,
排除缓存和 egg-info; 新建 venv 后安装 wheel, 避免旧产物影响验证.
上述临时目录为本次证据路径, 重新验证时需创建新的干净构建目录和环境.
没有测试失败. 双语文档已通过 gpt-6-luna / low 复核, 并实际重放上述命令.
命名修正 `b8d9a29` 的远端 CI 已通过; 本次 review 修正的远端结果待确认.

尚未验证历史 pickle 兼容性, 动态导入约束, 分配优化, 原生求解器,
Runtime 提交, 连续几何或停车安全. 本轮只重构模块边界.

## Review 核对与修正

逐条核对 PR #8 的 3 条意见, 使用命名修正后的代码实际重现:

| 意见 | 结论与证据 |
| --- | --- |
| [Guard Bypass](https://github.com/Requora/TAPF_MAPF_TPG/pull/8#discussion_r4320624328) | 无需修改. 根包导入被规范化后仍经过依赖检查; serialization 和 contracts 导入 order_source 均返回 forbidden dependency. 属性访问不在检查范围已在架构说明中明确. |
| [Missing Module Check](https://github.com/Requora/TAPF_MAPF_TPG/pull/8#discussion_r4320624333) | 无需修改. 临时创建 foo/bar.py 后, assertIn 在调用 violations 前产生包含 foo 的 AssertionError, 没有进入 KeyError 分支. |
| [Export Check Too Weak](https://github.com/Requora/TAPF_MAPF_TPG/pull/8#discussion_r4320624336) | 采纳. 增加导出对象 __module__ 必须属于本包的断言. 将 action_duration_s 临时替换为包外 lambda, 修改前测试通过, 修改后按预期拒绝. |

只增加 4 行测试断言, 生产代码不变. 源码和已有干净安装 wheel 各运行 64 项测试通过,
Ruff 和 diff 检查通过. 安装包源码未变, 本次复用命名修正时的 wheel, 未重新构建.
以下命令重现三项结论; 两个 AssertionError 是预期拒绝, 不是未处理的测试失败.

```bash
PYTHONPATH=src:tests python - <<'PYTHON'
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import warehouse_api
from warehouse_api import action_timing
from test_module_boundaries import ModuleBoundaryTests, violations
for owner in ('serialization', 'contracts'):
    print(owner, violations('from warehouse_api import order_source', f'warehouse_api.{owner}', 'warehouse_api'))
with TemporaryDirectory() as directory:
    root = Path(directory)
    (root / 'foo').mkdir()
    (root / 'foo/bar.py').write_text('from warehouse_api.contracts import Order\n')
    with patch.object(warehouse_api, '__file__', str(root / '__init__.py')):
        with TestCase().assertRaises(AssertionError) as caught:
            ModuleBoundaryTests().test_source_uses_only_allowed_public_dependencies()
        print(type(caught.exception).__name__, caught.exception)
with patch.object(action_timing, 'action_duration_s', lambda: None):
    with TestCase().assertRaisesRegex(AssertionError, 'implementation must belong to this package'):
        ModuleBoundaryTests().test_public_exports_use_descriptive_import_paths()
    print('wrong export rejected')
PYTHON
```

## 项目进展与架构网页

[打开私有网页](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site) / [English](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site/?lang=en).
这是人工维护的状态快照, 不是执行轨迹或实时 GitHub 看板. 验证基线为 `a785121`.

用户要求在本 PR 补充持续维护的网页. 源码位于 `web/progress/`, 采用无构建步骤的静态 HTML/CSS/JS.
暖色, 留白和清晰层级参考 Apple/OpenAI 的简洁风格, 不使用其品牌标识.
支持中英文切换, 手机横向查看架构图, 点击或键盘选择模块, 查看职责, 已完成内容,
未实现内容, 输入输出和代码链接. 页面区分 5 个已有实现模块, 7 个仅接口模块,
1 个计划中的联合 TAPF 模块和 1 个范围外后端. 这些计数不是完成率.

目标业务图有 14 个节点和 15 条计划连接, 全部使用虚线. 现有代码图有 5 个节点和
5 条实际导入依赖, 使用实线. 当前工作, 待合并后再做的分配增量和未完成的执行闭环分别展示.
当前 PR 未合并, 原生求解器集成数为 0, 连续安全未验证, 均明确标注.
AGENTS 已加入强制维护规则, 包括状态, 图, 证据, 双语, 发布和验证要求.

本地验证:

```bash
# 在独立终端启动静态预览, 若端口占用则选择空闲端口.
python -m http.server 38167 --bind 127.0.0.1 --directory web/progress/dist
# Playwright 仅用于网页开发检查, 不是 warehouse_api 的运行依赖.
/tmp/warehouse-web-tools/bin/python web/progress/check.py http://127.0.0.1:38167
/tmp/warehouse-ci-check/bin/ruff check web/progress/check.py
```

实际输出: `PASS: two languages, both diagrams, 28 module selections, keyboard, mobile layout, no JS errors`.
1440 px 桌面和 390 px 手机截图已人工检查, 页面没有横向溢出; 手机图内可横向滚动.
截图保存在 `/tmp/warehouse-progress-desktop.png`, `/tmp/warehouse-progress-mobile.png`.
额外检查了英文流程图. 修正过连线标签被节点遮挡的问题, 再次检查通过.
初次固定端口 8765 已占用, 后改用自动分配的 38167. 未修改或停止占用原端口的服务.

私有发布已成功, project_id 为 `appgprj_6ad6c9324f348191aab84e8bfffe6102`.
Sites 源码 commit 为 `614a297632fd55a9ff72d925e7b22bf47ed38fc3`;
version_id 为 `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_8ecaeb4ba3e48191aaf1a5b746d33f6d`.
工具返回 `succeeded`, 未更改访问范围. 本地浏览器检查与托管发布成功是分别验证的证据.
未进行托管登录流程的浏览器测试, 未添加定时更新或外部连接器.

维护入口: 页面内容与图数据在 `dist/project.js`, 进展和证据展示在 `dist/app.js`,
布局在 `dist/style.css`, 页面骨架在 `dist/index.html`. 内容改变时同步快照日期, 基线,
状态和证据. PR 合并后需更新 "待 review" 文案及新基线, 不能只改一处状态.

后续发布复用 `web/progress/.openai/hosting.json` 的 project_id. 按 Sites 技能获取该站点,
在独立空目录使用 source helper 打开远端源, 将本仓库审核后的网页文件同步过去.
完成检查后, 用同一 source helper 提交, 推送, 打包, 再按现有私有权限发布.
不得在主仓库内运行会管理 Sites Git remote 的 helper. 凭据只经 stdin 传递, 不落盘.

## 行数与下一步

Git 识别文件移动后, 相对 origin/main 的代码和测试 +473/-17, 共 490 行.
不识别重命名时为 +1937/-1481, 其中包含完整文件搬移.
文件搬移没有压缩或重写算法. 文档另计; 另有 8 行配置, 包含 Sites 托管配置和静态源码目录的 Git 忽略例外. 332 行网页源码及检查脚本全部计入代码限制.
提交后等待用户 review 和合并; 之后才继续独立 allocation 模块的最小增量.
