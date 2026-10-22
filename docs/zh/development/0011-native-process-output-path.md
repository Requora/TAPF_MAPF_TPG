# 原生进程输出路径约束

[中文](../../zh/development/0011-native-process-output-path.md) | [English](../../en/development/0011-native-process-output-path.md)

<!-- doc-sync: native-process-output-path / 2026-10-22-r1 -->

## 范围与决策

PR #10 已合并, 远端基线为 `4560d8e`. 本轮修复 review r4353910675 指出的 cwd 与相对 output 的歧义. run_native 在 cwd 非空时要求绝对 output, 否则抛出 ValueError, 不删除旧文件, 不创建日志, 不启动子进程. 命令参数由调用方负责; 工具不猜测或改写任意命令中的路径. 现有适配器使用绝对输出路径. 本轮不改变模块依赖或仓库支持范围.

## 验证与失败记录

TDD: 新增回归测试先失败, 原因是 ValueError 未抛出; 加入入口约束后通过. 测试预置调用者文件, 并检查拒绝后文件保留, 子进程未启动, 日志未创建.

`PYTHONPATH=src python -m unittest discover -s tests -v`: 87 项, 83 通过, 4 项原生测试因未配置环境跳过. Ruff, 两个 JavaScript 文件的 node --check 和 git diff --check 通过. 原有绝对输出与 cwd 的真实 Python 子进程测试通过. 本轮没有重跑 MAWPF, WinkTPG 或 CBS-TA; 历史真实集成证据属于已合并 PR #10.

网页同步快照日期, 合并基线和当前工作. 首次预览端口占用, 改为系统分配端口. Sites 源码助手两次返回 Unable to prepare the Site, 未改变远端访问范围. 发布和网页检查最终结果在下文补充.

## PR 与下一步

PR 链接待创建后补充. 本轮仅修复路径约束, 提交后等待用户 review. 联合仓库适配, 连续验证, Runtime 和执行仍未实现.

网页检查: `web/progress/check.py http://127.0.0.1:37663` 通过双语, 两类图, 30 次模块选择, 键盘与手机检查, 无 JS 错误. 桌面和手机截图已检查. 独立 gpt-6-luna/low 文档审查已执行.
