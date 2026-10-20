# PR 7 - 空闲机器人的新任务绑定

[中文](../../zh/development/0007-current-task-bindings.md) | [English](../../en/development/0007-current-task-bindings.md)

<!-- doc-sync: current-task-bindings / 2026-10-20-r8 -->

日期: 2026-10-19. 状态: 阶段 4 受限增量, 已通过 fixture 验证, 等待 review.
分支: `feat/current-task-bindings`. [PR #7](https://github.com/Requora/TAPF_MAPF_TPG/pull/7).
基线: GitHub 确认 PR #6 已合并至 `412ec329362320a644aa1aab29157d4adc888029`.

## 范围与来源

扩展 `CurrentTaskCompiler.compile_jobs(request, draft)`, 支持将新定义的
Lift/Serve/Drop 任务绑定到队列为空或省略队列的机器人. 不修改公开契约或版本.
已有当前任务继续按预测进度编译. 省略的绑定保持不变.
本次不实现任务选择, 库存预留, 分配优化或 Runtime 提交.

来源: API 0.7 英文指南第 05-06 节及 DATA_TYPES_EN.md.
SHA256: 指南 `f13bb9275af485e8dcc2ae47e76db411bf8b38581175dd71a14b50f5b8713e7f`;
类型说明 `5c3ffe789c8f43061961fd89bb7c217781ecda259ddb8c26c8c5d06c7d601b05`.
仓库原创代码, 仅使用标准库; 未引入上游依赖或原生求解器.

## 决策与可观察行为

Review 补充: AGENTS.md 要求每个 PR 完成后向用户说明要做什么, 怎么做的,
为什么这样做, 以及如何验证完成. 验证说明包含实际证据和未验证边界.

- `TaskDelta.tasks` 仅允许新定义. 与 request 中任务 ID 冲突时返回 CONFLICT,
  包括已完成任务. 没有历史账本, 不能检查 request 之外的历史 ID 复用.
- 每个新任务必须恰好绑定一次. 重复任务 ID, 重复机器人, 未知引用,
  未绑定定义或多个执行者返回 BAD_INPUT.
- 仅支持给空队列提交一个新任务. 此时保护前缀为空, 候选单任务后缀就是完整队列.
  已有非空队列不可修改, 即使其中任务已完成或 locked_prefix_count 为零.
  空候选后缀, 多任务候选, 空任务和旧未绑定任务的分配返回 UNSUPPORTED.
- 输入边界和候选绑定检查位于 `_compiler_validation.py`.
  编译器在局部字典中建立新任务的 `TaskProgress(task, 0, False)` 和绑定.
  现有动作检查处理候选的取货前置条件, 货架争用, 目标和量化耗时.
- 已接受任务的进度, 动作锁和携带归属仍有效. 错误的旧锁不能通过候选修复.
  成功和失败均不修改模型, 请求或草稿; 失败不返回部分 jobs.

实际运行 `tests/test_candidate_bindings.py` 和下面的重放命令得到:

| 场景 | A | B | 结果 |
| --- | --- | --- | --- |
| 空闲机器人, 新任务绑定 B | 空 | Lift(home-node), Serve(station-node), Drop(return-node), 各 0.3 s | Jobs |
| A 已携架, next_step=1 且 Lift 锁定 A; 新任务使用另一货架 | 原 Serve, Drop | 新 Lift, Serve, Drop | Jobs |
| A 的已有任务与 B 的新任务使用同一货架 | 无部分输出 | 无部分输出 | CONFLICT |

冲突诊断为 `Concurrent tasks claim the same shelf`, related_ids 为
`('new-task', 'shelf')`. 这是实际编译器的 fixture 输出, 不是运动执行轨迹.
重放成功和失败案例:

```bash
PYTHONPATH=src:tests python - <<'PY'
from dataclasses import replace
from test_compiler import fixture
from warehouse_api.codec import dumps
from warehouse_api.compiler import CurrentTaskCompiler
from warehouse_api.contracts import RobotQueue, TaskDelta
model, accepted = fixture()
compiler = CurrentTaskCompiler(model, sim_dt_s=0.1)
task = replace(accepted.tasks[0].task, id='new-task')
draft = TaskDelta((task,), (RobotQueue('B', (task.id,)),))
for name, request in [('idle', replace(accepted, tasks=(), queues=())), ('shelf-conflict', accepted)]:
    print(name, dumps(compiler.compile_jobs(request, draft)))
PY
```

## 验证与失败记录

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
/tmp/warehouse-ci-check/bin/ruff check src tests
python -m pip wheel --no-deps --wheel-dir /tmp/warehouse-bindings-wheel .
/tmp/warehouse-ci-check/bin/python -m pip install --force-reinstall /tmp/warehouse-bindings-wheel/warehouse_planning_api-0.7.0-py3-none-any.whl
/tmp/warehouse-ci-check/bin/python -m pip check
/tmp/warehouse-ci-check/bin/python -I -m unittest discover -s tests -v
git diff --check
```

源码和安装后 wheel 的 61 项测试全部通过, 包含 12 项新增候选绑定测试.
Ruff, pip check 和 diff 检查通过. 160 个参考文件哈希保持不变.
没有非预期测试失败. 首次状态查询因未安装 gh 失败, 改用 GitHub 连接器确认合并.
初次查找使用了不存在的 CI 文件名和 scripts 目录, 随后读取实际 contracts.yml.
双语文档通过 gpt-6-luna / low 复核. 远端 CI 结果将在 PR 中记录.

尚未验证分配器, 库存/需求可行性, MAPF/TPG/TAPF, Runtime 原子提交,
连续几何, 资源调度或停车安全. 编译 jobs 不代表可接受执行方案.

Copilot 触发诊断 (2026-10-20 UTC): 规则 `25432822` 已启用, 面向默认分支,
`review_on_push=true`, `review_draft_pull_requests=true`. 空提交 `da43cc8` 已推送,
CI 通过, 但 PR #7 的 review, review-request 和 Copilot work 事件均为空.
REST 请求 `copilot-pull-request-reviewer[bot]` 与 GraphQL `requestReviewsByLogin`
都返回成功响应, 但没有产生实际 review 事件, 因此不能将 HTTP 成功视为触发成功.
当前登录账号 TachikakaMin 的只读订阅查询返回 `access_type_sku=free_limited_copilot`,
高级请求额度为 0; Requora 组织席位数为 0. 账号查询使用非公开稳定契约的
`copilot_internal/user` 诊断端点, 不作为项目依赖. [官方说明](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/code-review)
确认 Copilot Free 不包含 code review. 当时需先获得对应订阅或组织付费使用资格,
再验证实际触发; 本次没有购买订阅或启用组织付费使用.

资格更新后的复测: 当前账号已返回 `free_educational_quota`, 高级额度 200.
[官方套餐表](https://docs.github.com/en/copilot/get-started/plans)列明学生套餐包含 code review.
空提交 `0a68b6a` 已推送且 CI 通过; push 和重新发出的手动请求仍未产生 review 事件.
此前 Free 套餐的诊断仅描述当时状态, 不能解释升级后仍未触发的问题.
目前自动 review 恢复尚未验证, 不能仅凭额度或成功响应宣称已恢复.


## DeepSeek 自动审查

用户要求接入 DeepSeek V4.1 Flash 1017, 自动将中文 review 意见发布到 PR 对应代码行.
调研后复用 [PR-Agent](https://github.com/The-PR-Agent/pr-agent), 替换自写 API 和评论发布脚本.
另一候选 [Serge](https://github.com/huggingface/serge)也支持自有 OpenAI 兼容接口与行内评论,
但其默认 Action 使用评论指令触发; PR-Agent 已提供 PR 新建/push 触发与中文配置, 更符合本次需求.
[PR-Agent 模型配置](https://docs.pr-agent.ai/usage-guide/changing_a_model/)支持自有模型接口,
[review 配置](https://docs.pr-agent.ai/tools/review/)提供 `inline_key_issues`, 不需要自行实现行号定位和发布.

上游版本为 PR-Agent 0.48.0, commit `981344be2755e303df501e18e3f60b848a188a80`, MIT 许可证.
使用官方预构建 `0.48.0-github_action` 镜像, 固定运行时 digest:
`sha256:80edef71baa3df28c129d858d4b53784abfc14704c235efb32b6c461d5399a6d`.
通过 Docker Registry 查询 digest, 并用 `gh attestation verify oci://index.docker.io/pragent/pr-agent@sha256:80edef71baa3df28c129d858d4b53784abfc14704c235efb32b6c461d5399a6d --repo The-PR-Agent/pr-agent` 验证上游构建证明, exit 0.
本仓库不 vendoring 或重建上游代码; GitHub Actions 拉取固定镜像运行. 本地无需新增项目依赖.

流程: 同仓库 PR 新建或 push -> PR-Agent 获取 diff 和项目规则 -> DeepSeek -> 中文摘要与行内意见.
仅启用 `/review`, 关闭自动 describe 和 improve, 不增加额外模型任务. `inline_key_issues=true`, `response_language=zh-CN`.
通过 OpenAI 兼容路由调用 `deepseek-flash`, endpoint 为 `https://api.deepseek.com`.
[DeepSeek 官方文档](https://api-docs.deepseek.com/)说明该别名当前由 DeepSeek-V4.1-Flash-1017 提供服务; 别名不是不可变版本.
按用户反馈优先速度, 使用 low 推理强度. 输入预算 16000 tokens, 输出预算 16384 tokens, 单次 AI 超时 180 秒,
不重试超时或耗尽输出的同一模型, 不配置备用模型. 工作流最长 6 分钟, 实际耗时和调用信息在运行详情中记录.
这些限制控制等待和成本, 不保证固定延迟或完整仓库覆盖. 输入过大时由上游管理 diff 预算并报告覆盖限制.

Key 仅存入 Actions Secret `DEEPSEEK_API_KEY`. 工作流不 checkout 或执行 PR 仓库代码, 不批准或合并 PR.
fork PR 跳过. 同仓库写权限用户仍可修改工作流, 属于凭据信任边界; 不声称隔离恶意仓库写入者.
上游负责评论定位, 去重和发布确认; 无法发布到行内的意见保留在摘要. review 失败使 Action 失败.
Copilot 自动审查规则已从 ruleset `25432822` 移除, 其余分支保护保持不变.

验证区分配置检查和真实运行. 已核对上游固定版本中的配置项与触发逻辑, YAML 解析通过.
删除自写审查脚本及其专用模拟测试后, 原有 61 项源码和安装后 wheel 测试通过, Ruff 和 diff 检查通过.
PR-Agent 的真实中文行内发布和耗时仍需实测, 结果将在 PR 中记录; 不能用旧脚本的成功代替上游集成验证.

历史诊断: 自写脚本首次运行 `39348625815` 因不完整输出拒绝发布. 第二次 `39348844596`
确认 16384 个生成 token 全用于推理, 正文为 0. 提高至 65536 后,
[运行 39349073708](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39349073708)在约 4 分钟内成功发布
[review](https://github.com/Requora/TAPF_MAPF_TPG/pull/7#pullrequestreview-5579478108), 绑定 `d24384f`.
该次 model=deepseek-flash, finish_reason=stop, prompt_tokens=24273, completion_tokens=57196,
reasoning_tokens=56754. 过大的输入和 high 推理预算导致等待较长, 因此改为复用上游并降低推理强度.
旧脚本发现的两项发布问题曾修复; 其后运行 `39349634654` 和 `39349679929` 因提交更新或方案替换取消.
这些记录是旧实现的证据, 不代表当前 PR-Agent 的性能或验证结果.

## 行数与下一步

相对 main 的代码和工作流变更合计 +271/-9, 包含测试及完整 YAML, 未通过配置豁免嵌入代码. 文档另计.
等待用户 review 和合并. 之后按阶段 5 推进库存/需求可行的最小分配增量,
仍暂缓重分配和多任务队列.
