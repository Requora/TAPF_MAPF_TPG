# 运动结果边界

[中文](../../zh/development/0013-motion-result-boundary.md) | [English](../../en/development/0013-motion-result-boundary.md)

<!-- doc-sync: motion-result-boundary / 2026-10-23-r2 -->

## 范围与决策

PR #12 已合并, 远端基线为 `5563fac`. 本轮修复 StagedPipeline 将缺失停车尾段等坏结果直接包装为 ExecutableProposal 的问题. 规则集中在 planning 的 `_validation.py`, 编排主体只调用检查并传递 Failure. 公开 API 和模块依赖不变.

检查 common_prefix 和 stop_tail 各覆盖 join_state 中每台机器人一次, 节点非空且数值有限, 时间严格递增, 旧状态到前缀与前缀到尾段精确衔接, 全车队前缀结束时刻一致, 尾段终点速度为零. 按机器人 ID 匹配, 不依赖返回顺序. 依据 API 0.7 参考包的 MotionPlan 和轨迹语义, 保留单节点静止保持; 单节点移动前缀可表示零长度前缀, 但必须立即衔接完整停车尾段. target_end_s 是期望时间, 不在此强制等于结果终点.

此检查只负责结构. 动作时序, 运动限制, 连续几何, 资源容量和无限期停车占用仍待验证. 候选未被 Runtime 接受. 联合仓库适配和执行闭环仍为计划.

## 验证与失败记录

TDD: 15 个坏运动子用例最初全部错误返回 ExecutableProposal, 新检查后全部返回 BAD_INPUT. 测试还检查原始 TPG 结果仍留在 last_trace, 输入未变, 合法单节点尾段不被误拒绝. 双车替身检查返回顺序可变, 不同分支时刻被拒绝; 该用例不是多车原生集成证据.

`WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests -v`: 94 项, 93 通过, 1 项 CBS-TA 实验跳过. 完整输出在 `/tmp/motion-boundary-tests.log`. 真实 MAWPF/WinkTPG 链和 20 次成功边界组合均通过. 本轮复用已有二进制, 未重新构建. 上游版本仍为 MAWPF `0cdb8e4` 和 WinkTPG `dd96946`, 来源与构建记录见 [原生集成](0009-staged-pipeline.md).

`PYTHONPATH=src:tests python -m planning.replay` 提供 fixture 请求, 阶段 trace 与结果; `PYTHONPATH=src:tests python -m composition.replay /tmp/tapf-chain-bridges --output /tmp/motion-composition.json` 保留真实原生输出. 不用 fixture 代替连续安全证据. 当前 Python 环境没有 Ruff; 后续检查状态在下文记录.

## PR 与下一步

[PR #13](https://github.com/Requora/TAPF_MAPF_TPG/pull/13) 等待 review. 提交后等待 review, 不推进下一 PR. 进展网页同步当前工作和合并基线. 最终检查与发布记录见下文.

非有限值回归将 NaN/Inf 注入 x 坐标; 其他标量的有限性由同一检查覆盖, 未逐字段注入. Ruff 在独立工具环境安装后通过; JS 语法, diff 和网页双语/键盘/手机检查通过, 桌面与手机截图已检查. 初次 wheel 从旧 build/ 混入历史模块, 架构检查如期失败; 改用独立干净源码目录重建并重新验证.

干净 wheel: `/tmp/motion-wheel-env/bin/python -m unittest discover -s tests -v`, 设置同一 WAREHOUSE_NATIVE_BIN 后 93 通过, 1 跳过; pip check 通过. 独立 gpt-6-luna/low 双语审查完成, 已修正旧 PR 焦点链接并明确非有限值测试范围. 相对 `5563fac` 的代码含测试/网页共 136 行 (+121/-15), 配置无变化; 文档单独计数. 用户已有文件改动未加入.

私有发布成功: [进展页](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site). Sites 源码 `1c9a53097d2a07e709faf1ab0babd4afdc1bfce2`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_4c245494a37c8191849ae1af069b3db0`. 仅所有者访问保持不变; 托管登录流程未验证. 发布使用独立临时 checkout, 主仓库 remote 未改变. 最终提交远端 CI 仍待结果.

## Review 修正

用户意见 [r4355613142](https://github.com/Requora/TAPF_MAPF_TPG/pull/13#discussion_r4355613142) 要求解释 solve 注释. 注释现逐项说明阶段调用, 总预算, 车队覆盖, 衔接和停车终点; 明确候选不扣库存或更新进度, 安全验收与原子提交仍由未来 Runtime 负责.

采纳 [r4355588244](https://github.com/Requora/TAPF_MAPF_TPG/pull/13#discussion_r4355588244): TPG 返回 MotionPlan 后先检查 deadline, 再检查运动, 检查后再次复核 deadline. 迟到或检查期间耗尽预算时优先 TIMEOUT, 不把迟到的坏结果报成 BAD_INPUT. 适配器直接返回 Failure 的现有传播规则不变.

采纳 [r4355588241](https://github.com/Requora/TAPF_MAPF_TPG/pull/13#discussion_r4355588241): join_state 不保证静止. 移动单节点前缀只表示立即进入停车尾段的边界, 没有授权无限期移动. 删除额外静止限制, 保留尾段完整性, 精确衔接和终点零速度检查. 示例为初速 1 m/s, 1 s 内前进 0.5 m 并停稳; 此结构测试不证明通用运动安全.

TDD: 新增三个测试, 四个子场景先失败后通过, 覆盖迟到的坏运动, 检查期间超时的合法/坏结果和移动零长度前缀. 缺失尾段和单节点移动尾段仍被拒绝. `WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests -v`: 97 项, 96 通过, 1 项 CBS-TA 实验跳过. `/tmp/motion-review-red.log` 和 `/tmp/motion-review-tests.log` 保留失败与完整结果. Ruff 和 diff 检查通过. 真实原生链复用已有二进制, 没有重新构建. 上文 94 项与 136 行是初次提交快照, 非本次修订总数.

干净源码重建并安装的 wheel 同样 96 通过, 1 跳过, pip check 通过. 双语文档经独立 gpt-6-luna/low 审查, 已将路线图的 BAD_INPUT 限定为预算内结果, 并同步网页当前工作卡. 网页双语, 键盘和手机检查通过, 桌面与手机截图已检查. 最终 PR 相对 `5563fac` 的代码含测试/网页为 193 行 (+176/-17), 文档为 114 行 (+98/-16), 无配置修改.

本次私有发布成功: Sites 源码 `b772f42bf274a049e95d62fa15bdf594ad56a5bc`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_0639b3f51864819184efd4345040b906`. 继续使用上文网页地址, 仅所有者访问不变. 未验证托管登录; 新提交远端 CI 在推送后运行, 不用本地测试代替远端结果. Review 线程逐条回复, 不自动标记 resolved 或合并 PR.
