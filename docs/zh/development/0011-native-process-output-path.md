# 原生进程输出路径约束

[中文](../../zh/development/0011-native-process-output-path.md) | [English](../../en/development/0011-native-process-output-path.md)

<!-- doc-sync: native-process-output-path / 2026-10-22-r2 -->

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
