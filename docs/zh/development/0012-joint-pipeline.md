# 联合规划编排

[中文](../../zh/development/0012-joint-pipeline.md) | [English](../../en/development/0012-joint-pipeline.md)

<!-- doc-sync: joint-pipeline / 2026-10-23-r2 -->

## 范围与决策

PR #11 合并于 `5e35ee0`, 开始前已确认远端状态. JointPipeline 用注入的 JointPlanner 替换独立分配和路径阶段. JointPlan 在 contracts.py 中组合已有 TaskDelta 与 FleetPlan. 公开 DecisionPipeline 输入输出不变. 不引入原生对象或新的跨模块导入.

共享编译器重新编译最终草稿, 保留进度, 锁和动作耗时. 既有规划校验在 TPG 前检查请求标识, 机器人覆盖和动作顺序. 求解器本身必须在搜索中使用共享编译语义; 最终检查不能证明路线几何正确. 联合搜索, 编译和运动共用一个墙钟截止时间. 同步调用不能被抢占; 迟到结果被丢弃. 只有 Runtime 可以验收和提交方案.

## 验证与失败记录

初始定向测试因 JointPlan 尚不存在而失败. 实现后 6 项定向测试通过. `PYTHONPATH=src python -m unittest discover -s tests` 运行 93 项: 89 通过, 4 项原生测试跳过. Ruff 和 git diff --check 通过. 未重跑原生规划器.

`PYTHONPATH=src:tests python -m planning.joint_replay` 打印实际 fixture 阶段输入输出和候选方案. 共享编译器为真实实现; 联合搜索和运动使用显式替身. 预期与实际阶段均为 joint -> compilation -> tpg; 动作为 lift, serve, drop. 本次运行保存于 `/tmp/warehouse-joint-replay.json`. 无效队列, 过期路线, 缺失/重复机器人和缺失动作均在运动前停止. 测试还覆盖失败, 异常, trace 重置, 输入不变和共享超时.

## PR 与下一步

[PR #12](https://github.com/Requora/TAPF_MAPF_TPG/pull/12) 已提交, 等待 review. 本轮实现编排并提供 fixture 证据, 不代表原生联合仓库求解器. review 和合并后, 下一步将受支持仓库任务适配到联合原生搜索. 连续几何, 无限期停车, Runtime 和执行仍未实现. 按用户要求优先主线, 独立网页修正已搁置; 本轮同步维护状态内容.

源码和干净安装 wheel 各 89 通过, 4 跳过; pip check 通过. 干净构建目录为 `/tmp/warehouse-joint-wheel-82xyvfjv`. gpt-6-luna/low 双语审查通过. 网页双语, 两类图, 30 次模块选择, 键盘和手机检查通过, 无 JS 错误; 已检查桌面和手机截图.

私有网页发布成功, 保持仅所有者访问; 未验证托管登录流程. [Site](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site), source `3f5aa0eafbc3afc7f619f4654086fcc69fb184b1`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_3acb3f2c6aec819187870c5cc05927b7`.

## 自动 review 仅审查代码相关改动

按用户要求, IGNORE.REGEX 在生成 diff 前排除 docs/, web/ 全目录, warehouse_api_v0_7/ 参考包, 以及任意目录的 Markdown, RST, AsciiDoc, HTML, CSS, SVG, 图片和 PDF. 因此网页中的 JS 和检查脚本也不参与自动 review. 业务源码, 测试, 集成适配器, 构建及 CI 配置仍保留, 包括 CMakeLists.txt. 审查提示明确不评论网页, 文档, 样式, 翻译, 发布记录或进展统计. 项目指令读取和人工文档校验不受影响.

固定 PR-Agent v0.48.0 的真实配置加载器和 filter_ignored 离线验证先失败, 修改后通过. 命令: `PYTHONPATH=/tmp/warehouse-pr-agent-research /tmp/warehouse-llm-probe/bin/python /tmp/warehouse-review-scope-check.py`. 测试覆盖排除项和保留项, 原有 vendor 排除仍有效. YAML 解析和 diff 检查通过. 本次仅配置和双语日志变化, 不改变规划代码, 模型预算或网页内容. 推送后触发新 review; 离线验证不代表远端运行成功.
