# 可观察的 OpenRouter 审查传输层

[中文](../../zh/development/0015-review-transport.md) | [English](../../en/development/0015-review-transport.md)

<!-- doc-sync: review-transport / 2026-10-23-r1 -->

## 范围与状态

本次是基于已合并基线 `cabdac3` 的独立基础设施修复; C++ 轨迹工作仍在 PR #14. PR 链接: 待创建. 适配器保留 PR-Agent 的 diff 过滤, 中文审查格式, 解析和发布; 只替换模型传输层. 不修改仓库业务模块或 API.

## 失败证据

PR #14 的运行 [39979489425](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39979489425) 在客户端重试为零时仍调用两次. OpenRouter 账户记录为 Ionstream 供应商流内错误 (502), 并非正常结束. 15:35:32 UTC 的请求在 1864.211 秒内生成 360561 个推理 token; 16:06:37 UTC 的重试在 1864.265 秒内生成 406176 个推理 token. 两次可见正文及实际计费均为零. Generation ID: `gen-1792769732-WefTOj35tNYxkiMphWvu`, `gen-1792771597-A5ib1pHbt3tBV5lyzWr3`. 提示词及输出日志未开启; 元数据不能确定模型持续推理的原因.

## 实现与决策

`.github/review_transport.py` 在固定版本 PR-Agent runner 加载前替换 `LiteLLMAIHandler.chat_completion`. 它通过镜像内的 httpx 依赖直接处理 HTTP/SSE, 每个 handler 只允许一次模型调用. 上游提示词构造, 完整 diff 预算检查及审查发布器保持使用. HTTP 错误和流内错误立即失败; 缺少流结束标记, 非 stop 结束原因及空白正文均失败, 不发布部分审查. `REVIEW_AUDIT` 在可用时记录 generation/request ID, 供应商, 用量, 错误码和状态, 不记录提示词, 推理正文或凭据. 上游未提供的元数据保持缺失, 不估算.

请求排除 `ionstream`, 要求参数支持, 使用 low 推理, 65536 输出 token 及覆盖完整请求的 600 秒总时限. 这些是试验预算, 不是已验证的最佳值. workflow 为初始化和发布预留时间, 共允许 15 分钟. 模型为 `deepseek/deepseek-v4.1-flash-1017`. 不允许备用模型或同 handler 重试; OpenRouter 保留其供应商路由行为. 请求级参数不改变账户全局偏好.

手动 workflow 输入只接受同仓库的开放 PR, 读取其元数据并向原 runner 传入合成 opened 事件. 它不执行目标 PR 源码. 因此可在两个 PR 均未合并时, 用独立修复分支验证 PR #14.

## 来源

PR-Agent 0.48.0: [上游](https://github.com/qodo-ai/pr-agent), MIT, 固定镜像 `pragent/pr-agent@sha256:80edef71baa3df28c129d858d4b53784abfc14704c235efb32b6c461d5399a6d`. 保留现有镜像, 不复制或重新构建上游. 本地检查的上游 checkout 为 `981344be2755e303df501e18e3f60b848a188a80`; 固定镜像中的运行集成另行检查. [OpenRouter 路由文档](https://openrouter.ai/docs/guides/routing/provider-selection) 定义 provider.ignore 和 require_parameters. 公开供应商注册表确认 slug 为 `ionstream`.

## 验证与下一步

TDD: 传输测试先因适配器文件不存在而失败, 实现后通过. 六项传输测试覆盖流内 502, HTTP 502, 单次调用限制, 实际请求参数, 空白/截断/断流及总时限取消. Ruff 通过. 命令: `python -m unittest discover -s .github/tests -v` 和 `ruff check .github/review_transport.py .github/tests`. 测试在固定镜像内先于真实审查步骤运行. 远端镜像执行, 实际供应商路由及审查发布仍待验证. 传输成功不证明审查意见正确. 下一步: 对 PR #14 运行修复后的 workflow, 核对 GitHub 和 OpenRouter 证据, 然后等待 review.
