# 原生进程输出路径约束

[中文](../../zh/development/0011-native-process-output-path.md) | [English](../../en/development/0011-native-process-output-path.md)

<!-- doc-sync: native-process-output-path / 2026-10-23-r4 -->

## 范围与决策

PR #10 已合并, 远端基线为 `4560d8e`. 本轮修复 review r4353910675 指出的 cwd 与相对 output 的歧义. run_native 在 cwd 非空时要求绝对 output, 否则抛出 ValueError, 不删除旧文件, 不创建日志, 不启动子进程. 命令参数由调用方负责; 工具不猜测或改写任意命令中的路径. 现有适配器使用绝对输出路径. 本轮不改变模块依赖或仓库支持范围.

## 验证与失败记录

TDD: 新增回归测试先失败, 原因是 ValueError 未抛出; 加入入口约束后通过. 测试预置调用者文件, 并检查拒绝后文件保留, 子进程未启动, 日志未创建.

`PYTHONPATH=src python -m unittest discover -s tests -v`: 87 项, 83 通过, 4 项原生测试因未配置环境跳过. Ruff, 两个 JavaScript 文件的 node --check 和 git diff --check 通过. 原有绝对输出与 cwd 的真实 Python 子进程测试通过. 本轮没有重跑 MAWPF, WinkTPG 或 CBS-TA; 历史真实集成证据属于已合并 PR #10.

网页同步快照日期, 合并基线和当前工作. 首次预览端口占用, 改为系统分配端口. Sites 源码助手两次返回 Unable to prepare the Site, 未改变远端访问范围. 随后在独立 checkout 成功恢复源码, 标准助手完成推送与打包.

## PR 与下一步

[PR #11](https://github.com/Requora/TAPF_MAPF_TPG/pull/11) 已提交. 本轮仅修复路径约束, 提交后等待用户 review. 联合仓库适配, 连续验证, Runtime 和执行仍未实现.

网页检查: `web/progress/check.py http://127.0.0.1:37663` 通过双语, 两类图, 30 次模块选择, 键盘与手机检查, 无 JS 错误. 桌面和手机截图已检查. 独立 gpt-6-luna/low 文档审查已执行.

私有发布成功: [网页](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site), 源码 `dfe22019e35de4f95c6b758a5374f555adbda3d2`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_92830b6d6e288191834091f03d1f9050`. 返回 succeeded, 保持仅所有者访问; 未验证托管登录流程. 主仓库 remote 未改变. 相对 `4560d8e` 的代码为 44 行 (+34/-10), 含测试和网页; 文档单独计数, 无配置变更. 用户已有修改未加入.

## 自动 review 预算增至 5 倍

用户要求将输出和时间上限增至当前的 5 倍. 输出由 131072 改为 655360 token, AI 超时由 1200 改为 6000 s (100 min), job 由 22 改为 110 min. 总 token 预算改为 720896, 保留 65536 输入容量. high, 模型, OpenRouter 和无重试策略不变.

[失败 review 39861571315](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39861571315)在约 367 s 后返回空正文和 finish_reason=length, 未触及旧时间上限. 日志没有实际 token usage, 因此未证明耗尽 131072; 这次增大按用户要求执行, 不声称已证明根因或能保证 provider 接受和完成. 同提交 CI 39861571297 全部通过.

离线真实客户端拦截先因 max_tokens=131072 不满足 655360 而失败, 修改后通过; 同时校验输入容量, 总预算和两个时限, YAML 与 diff 检查通过. 本次仅工作流配置与双语日志变化; 规划代码和网页内容不变. 上文无配置变更与代码行数描述的是原始路径修复交付. 新远端 review 在推送后运行, 不将离线检查当成服务实际成功.

## Review 修正与回复, 2026-10-23

用户意见 r4355183212 已采纳. 路径配置规则移入 native_process 内部 `_validation.py` 的 check_output_path, run_native 在任何文件副作用前显式调用. 模块间公开 API 和依赖不变. 本次属于保持行为的重构: 原有四项进程行为测试先通过, 移动后仍通过; 未增加只重复实现结构的测试.

机器人意见 r4355212527 已核对, 暂不降低用户指定的 5 倍预算. [OpenRouter 端点目录](https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash-1017/endpoints)在检查时列出 OpenInference, Relace, Cloudflare 等端点支持 1048576 上下文和 943718 输出 token, 能容纳配置预算. 并非所有 provider 都支持该上限; 本次未固定 provider. [真实 review 39883608837](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39883608837)成功并发布意见, 汇总为输入 15473 / 输出 18983 token, AI 时间 50.9 s; [同提交 CI](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39883608860)全部通过. 这证明该请求成功, 不证明实际生成满 655360 token 或所有路由都能成功. 旧 length 失败仍没有 usage, 不据此认定耗尽指定上限. 两条线程均在推送后回复, 不自动标记 resolved.

重构后 `PYTHONPATH=src python -m unittest discover -s tests -v`: 83 通过, 4 原生测试跳过. Ruff 和 diff 检查通过. 本次未重跑原生规划器. 网页的公开行为, 模块连接和已展示验证范围不变, 不重复发布网页. 新提交的远端检查在推送后运行, 不用旧 CI 代替新提交验证.

## 自动 review 排除 Markdown

用户要求自动 review 不审查 .md 文件. 工作流通过 `IGNORE.REGEX` 的大小写不敏感后缀规则, 在 PR-Agent 生成 diff 前过滤根目录和子目录的 Markdown 文件. Python, YAML, JS 和原有 vendor 排除规则保留. 此规则限制变更文件审查范围, 不关闭必要的项目指令读取. 双语日志的人工检查仍按 AGENTS 执行.

使用固定 v0.48.0 上游实际配置加载器和 filter_ignored 离线验证: 修改前因 README.md, 嵌套 md 与大小写变体仍保留而失败; 修改后这些文件均被排除, Python/YAML/JS 保留, vendor 仍排除. 检查脚本位于 `/tmp/warehouse-review-md-check.py`, 命令为 `PYTHONPATH=/tmp/warehouse-pr-agent-research /tmp/warehouse-llm-probe/bin/python /tmp/warehouse-review-md-check.py`. 初次检查缺少 loguru 依赖, 在临时验证环境补齐后得到上述行为失败, 未改变项目依赖. YAML 和 diff 检查通过. 本次仅配置与双语日志修改, 不改变业务行为或网页内容. 推送后触发新 review, 不以离线结果代替远端验证.
