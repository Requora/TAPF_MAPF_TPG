# 模块边界组合测试

[中文](../../zh/development/0012-module-composition.md) | [English](../../en/development/0012-module-composition.md)

<!-- doc-sync: module-composition / 2026-10-23-r1 -->

## 范围与决策

[PR #12](https://github.com/Requora/TAPF_MAPF_TPG/pull/12) 基于已合并 PR #11 的 `5e35ee0`, 对规划实现仅增加测试. 生产源码, 契约和模块依赖不变. 测试驱动选择从一个模块输入到同模块或下游模块输出的连续区间. 未来联合实现仍使用已有 DecisionPipeline 替换边界.

中间入口使用独立构造的 TaskDelta, RobotJobs 和 FleetPlan. 编译入口使用已有两个参数 AssignmentRequest 和 TaskDelta, 不新增 DTO. 预期服务耗时来自明确的已知案例值, 不调用被测耗时函数. 测试调用真实 SingleShelfAllocator, CurrentTaskCompiler, NativeMawpfPlanner 和 NativeWinkTpgPlanner. 每个组合只运行选定阶段. 驱动连接公开契约并保留 trace 文件, 不实现生产截止时间调度或 Runtime 提交.

## 覆盖与结果

每个单元格表示从行模块的输入到列模块的输出. PASS 表示两组参数均通过真实实现验证. 横线表示现有契约未连接的反向路径, 不是跳过受支持案例.

| 输入 / 输出 | 分配 | 编译 | MAPF | TPG |
| --- | --- | --- | --- | --- |
| 分配 | PASS | PASS | PASS | PASS |
| 编译 | - | PASS | PASS | PASS |
| MAPF | - | - | PASS | PASS |
| TPG | - | - | - | PASS |

案例为数量/工作站/归还位 = 1/3/5 和 3/4/8. 20 次成功组合检查任务数量与机器人队列, 动作目标/资源/耗时, 精确相邻边路线, 运动动作位置, 完整静止耗时, tick 对齐和停车尾段拼接. 输入保持不变. 每个被调用的原生阶段产生三条成功进程记录.

失败案例覆盖分配库存不足 (NO_PLAN), 编译缺失队列 (BAD_INPUT), MAPF 缺失动作队列 (UNSUPPORTED), TPG 请求身份过期 (STALE_REQUEST), TPG 路线不连续 (BAD_INPUT). 每项均只执行一个阶段即返回, 没有原生证据. 这是行为拒绝, 不是驱动吞掉异常.

## 验证与重放

初始定向测试因 composition.replay 尚不存在而失败; 增加测试驱动后, 配置原生二进制时四项定向测试全部通过. 命令:

```bash
WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src:tests python -m composition.replay /tmp/tapf-chain-bridges --output /tmp/warehouse-composition.json
PYTHONPATH=src:tests python -m composition.replay /tmp/tapf-chain-bridges --first compilation --last mapf --output /tmp/warehouse-composition-selected.json
/tmp/warehouse-ci-check/bin/ruff check src tests
```

全套 91 项: 90 通过, 1 项独立 CBS-TA 对照测试跳过. 无原生二进制时 86 通过, 5 跳过. 完整重放包含十条真实 trace, 原生文件, 二进制哈希和两个失败重放; 选定重放的成功矩阵仅含 compilation -> MAPF. CI 现随原生链证据上传 composition.json. Ruff 和 diff 检查通过.

本次复用 `/tmp/tapf-chain-bridges/warehouse_mawpf` 与 `warehouse_winktpg`. 本地重新构建因 cmake 不可用而失败. 现有构建缓存的源码路径对应干净固定版本: [MAWPF](https://github.com/HirokiNagai-39/mawpf/tree/0cdb8e43797aff3781e4cd3ddb2c6d7d36f3df17) 和 [WinkTPG](https://github.com/JingtianYan/WinkTPG-IEEE-TASE/tree/dd96946f225e206de35b041320786eab43210658). 重放包含二进制哈希; 不声称本轮完成了全新可重现本地构建. 上游构建/许可证说明仍见 [原生集成证据](0009-staged-pipeline.md).

源码和干净安装 wheel 均为 90 通过, 1 跳过; 干净构建目录 `/tmp/warehouse-composition-wheel-oaa55ar7`, pip check 通过. 独立 gpt-6-luna/low 双语审查通过. 网页双语, 两类图, 30 次模块选择, 键盘和手机检查通过, 无 JS 错误; 桌面和手机截图已检查.

## 边界与下一步

矩阵覆盖当前已连接的四阶段单车道子集, 不代表任意排列, 全部可能输入或所有计划模块. 求解器输出没有使用 mock. 连续碰撞/无限期停车安全, 多车仓库规划, 联合仓库集成, Runtime 和执行仍未验证或未实现. 等待 PR review 与合并后, 再扩展其他真实模块或受支持案例.
## 自动 review 仅审查代码相关改动

按用户要求, IGNORE.REGEX 在生成 diff 前排除 docs/, web/ 全目录, warehouse_api_v0_7/ 参考包, 以及任意目录的 Markdown, RST, AsciiDoc, HTML, CSS, SVG, 图片和 PDF. 因此网页中的 JS 和检查脚本也不参与自动 review. 业务源码, 测试, 集成适配器, 构建及 CI 配置仍保留, 包括 CMakeLists.txt. 审查提示明确不评论网页, 文档, 样式, 翻译, 发布记录或进展统计. 项目指令读取和人工文档校验不受影响.

固定 PR-Agent v0.48.0 的真实配置加载器和 filter_ignored 离线验证先失败, 修改后通过. 命令: `PYTHONPATH=/tmp/warehouse-pr-agent-research /tmp/warehouse-llm-probe/bin/python /tmp/warehouse-review-scope-check.py`. 测试覆盖排除项和保留项, 原有 vendor 排除仍有效. YAML 解析和 diff 检查通过. 本次仅配置和双语日志变化, 不改变规划代码, 模型预算或网页内容. 推送后触发新 review; 离线验证不代表远端运行成功.

私有网页发布成功, 保持仅所有者访问; 未验证托管登录流程. [Site](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site), source `488596b7548860f7f6408adef82d9cb7be1f4ce0`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_6f9d95eaba7c8191b58b26321ed36d93`.
