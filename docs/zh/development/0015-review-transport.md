# 可观察的 OpenRouter 审查传输层

[中文](../../zh/development/0015-review-transport.md) | [English](../../en/development/0015-review-transport.md)

<!-- doc-sync: review-transport / 2026-10-23-r2 -->

## 范围与状态

本次是基于已合并基线 `cabdac3` 的独立基础设施修复; C++ 轨迹工作仍在 PR #14. 修复 PR: [#15](https://github.com/Requora/TAPF_MAPF_TPG/pull/15). 适配器保留 PR-Agent 的 diff 过滤, 中文审查格式, 解析和发布; 只替换模型传输层. 不修改仓库业务模块或 API.

## 失败证据

PR #14 的运行 [39979489425](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39979489425) 在客户端重试为零时仍调用两次. OpenRouter 账户记录为 Ionstream 供应商流内错误 (502), 并非正常结束. 15:35:32 UTC 的请求在 1864.211 秒内生成 360561 个推理 token; 16:06:37 UTC 的重试在 1864.265 秒内生成 406176 个推理 token. 两次可见正文及实际计费均为零. Generation ID: `gen-1792769732-WefTOj35tNYxkiMphWvu`, `gen-1792771597-A5ib1pHbt3tBV5lyzWr3`. 提示词及输出日志未开启; 元数据不能确定模型持续推理的原因.

## 实现与决策

`.github/review_transport.py` 在固定版本 PR-Agent runner 加载前替换 `LiteLLMAIHandler.chat_completion`. 它通过镜像内的 httpx 依赖直接处理 HTTP/SSE, 每个 handler 只允许一次模型调用. 上游提示词构造, 完整 diff 预算检查及审查发布器保持使用. HTTP 错误和流内错误立即失败; 缺少流结束标记, 非 stop 结束原因及空白正文均失败, 不发布部分审查. `REVIEW_AUDIT` 在可用时记录 generation/request ID, 供应商, 用量, 错误码和状态, 不记录提示词, 推理正文或凭据. 上游未提供的元数据保持缺失, 不估算.

请求排除 `ionstream`, 要求参数支持, 使用 low 推理, 65536 输出 token 及覆盖完整请求的 600 秒总时限. 这些是试验预算, 不是已验证的最佳值. workflow 为初始化和发布预留时间, 共允许 15 分钟. 模型为 `deepseek/deepseek-v4.1-flash-1017`. 不允许备用模型或同 handler 重试; OpenRouter 保留其供应商路由行为. 请求级参数不改变账户全局偏好.

手动 workflow 输入只接受同仓库的开放 PR, 读取其元数据并向原 runner 传入合成 opened 事件. 它不执行目标 PR 源码. 因此可在两个 PR 均未合并时, 用独立修复分支验证 PR #14.

## 来源

PR-Agent 0.48.0: [上游](https://github.com/qodo-ai/pr-agent), MIT, 固定镜像 `pragent/pr-agent@sha256:80edef71baa3df28c129d858d4b53784abfc14704c235efb32b6c461d5399a6d`. 保留现有镜像, 不复制或重新构建上游. 本地检查的上游 checkout 为 `981344be2755e303df501e18e3f60b848a188a80`; 固定镜像中的运行集成另行检查. [OpenRouter 路由文档](https://openrouter.ai/docs/guides/routing/provider-selection) 定义 provider.ignore 和 require_parameters. 公开供应商注册表确认 slug 为 `ionstream`.

## 验证与下一步

TDD: 传输测试先因适配器文件不存在而失败, 实现后通过. 六项传输测试覆盖流内 502, HTTP 502, 单次调用限制, 实际请求参数, 空白/截断/断流及总时限取消. Ruff 通过. 命令: `python -m unittest discover -s .github/tests -v` 和 `ruff check .github/review_transport.py .github/tests`. 测试在固定镜像内先于真实审查步骤运行. 最初六项测试在固定远端镜像中也已通过. 增加凭据隔离覆盖后, 本地七项测试通过; 加强后的总时限测试验证持续收到推理片段时仍能取消. 新隔离测试先因缺少独立测试 job 而失败, 实现后通过. 传输成功不证明审查意见正确. 下一步: 验证隔离后的 workflow jobs, 然后等待 PR #15 review, 再更新独立的轨迹 PR.

## 真实审查与安全修正

运行版本 `9de2738a19eb269f3aaf16f3c302894d7b44e95d` 已完成两次真实审查, 各只调用一次. PR #15 [运行 40013283451](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/40013283451) 使用 Alibaba, 提示词 7949 / 输出 64214 token (其中推理 63797), 正文 1039 字符, 费用 $0.043692825; generation 为 `gen-1792784478-NgKgKmlZFF92wIA4jRNz`. PR #14 [手动运行 40013469647](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/40013469647) 使用 Sail Research, 提示词 11026 / 输出 48105 token (其中推理 47627), 正文 1159 字符, 费用 $0.008329376; generation 为 `gen-1792784566-hYpbZocBzVUdNVbpnqjY`. 两次均以 stop 结束, 排除了 Ionstream 并发布行内意见 (分别 1 条和 2 条). OpenRouter 账户记录与供应商, 用量及费用一致. 模型调用仍约需九分钟; 这是有界运行成功, 不保证延迟. 常规 CI [40013283290](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/40013283290) 通过.

PR #15 审查指出 PR checkout 代码与模型凭据同处执行环境. 已采纳: 测试改为独立只读 runner 且不注入模型密钥; 发布 runner 只 checkout 上述已实际运行的不可变适配器 commit. Checkout 自身固定为 `11d5960a326750d5838078e36cf38b85af677262`. 后续适配器改动需单独验证并显式更新运行版本; 仅修改 PR 中的适配器不会改变持有凭据的运行代码. 仓库维护者仍控制 workflow 定义; 此隔离不防御有权限的恶意 workflow 修改. PR #14 的两条意见涉及头文件重编依赖和浮点测试容差, 与本次传输修复分开处理.
