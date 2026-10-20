# 分阶段组合与 fixture 重放

[中文](../../zh/development/0009-staged-pipeline.md) | [English](../../en/development/0009-staged-pipeline.md)

<!-- doc-sync: staged-pipeline / 2026-10-20-r1 -->

## 范围与状态

用户优先要求跑通订单到 TPG 链路. PR #8 已合并至 `576e25d`.
本次首个增量在 500 行 PR 限制内提供组合入口.
真实链路**尚未完成**. 重放中的分配, MAPF, TPG 明确使用测试替身.
订单发布与任务编译使用已有实现.
PR: [#9](https://github.com/Requora/TAPF_MAPF_TPG/pull/9). 验证基线: `c47f4a7`.

```mermaid
flowchart LR
    O[ReplayOrderSource] -->|Order 转 Demand: fixture 驱动| A[分配 fixture]
    A -->|TaskDelta| C[CurrentTaskCompiler]
    C -->|RobotJobs / PathRequest| M[MAPF fixture]
    M -->|FleetPlan / MotionRequest| T[TPG fixture]
    T -->|MotionPlan| P[仅候选方案]
```

## 实现与决策

`planning.StagedPipeline` 通过构造函数接收四个 Protocol 实现.
它顺序调用分配, 编译, 路径和运动规划, 生成候选 `ExecutableProposal`.
它不接受方案, 不修改账本. Runtime 和连续验证仍未实现.
类型名称不能证明执行安全.

组合模块只导入 contracts. 既有 DTO 和公开签名不变.
一个墙钟截止时间覆盖所有阶段, 包含编译耗时. 有预算字段的阶段收到剩余时间.
此处不能中断同步调用; 超时后返回的成功结果会被丢弃.
阶段失败保留原始错误码, 说明和关联 ID. 异常保留 traceback 向外抛出.
路径结果属于其他请求时, 在运动阶段前停止.
输入和路径身份规则放在 `planning/_validation.py`.

Runtime 实现前, Order 转 Demand 只在重放驱动中完成. 分配 fixture 返回一个预定义任务.
运动 fixture 按编译后的动作耗时生成静止段, 不是速度求解器或安全验证器.
本 PR 没有自行实现求解器算法.

## 验证与重放

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src:tests python -m planning.replay > /tmp/staged-fixture-trace.json
ruff check src tests web/progress/check.py
# 从干净 checkout 构建 wheel 并安装到新环境, 然后运行:
python -I -m unittest discover -s tests -v
python -m pip check
```

实际结果: 源码 72 项与干净安装包 72 项测试通过; Ruff 和 pip check 通过.
新增用例覆盖四个失败边界, 所有截止时间检查点, 递减预算, 编译拒绝,
过期路径身份, 输入快照, 结果 JSON 往返和异常传播.
重放记录各阶段的实现标签, 输入或编译输出, 以及结果.
墙钟预算字段会随运行变化; fixture 候选方案可重复生成.

| 轨迹阶段 | 实际结果 |
| --- | --- |
| 订单 | O 需要一件 X; 驱动提供货架的一件可用库存 |
| 分配 fixture | 任务 T 绑定机器人 A; Lift, Serve, Drop |
| 真实编译器 | 三个动作均为 0.3 s, 带 StepRef 和资源 ID |
| MAPF fixture | Do, Move(out), Do, Move(return), Do |
| TPG fixture | 动作在 0.0, 4.3, 8.6 s 开始; 前缀止于 8.9 s; 静止尾段止于 9.9 s |
| 接受 | 未执行; 没有 Runtime 或连续安全证据 |

首次 wheel 检查失败, 原因是工作区被忽略的 build 目录保留了旧平铺模块,
包括 `_codec_validation.py`. 使用 `git archive c47f4a7` 导出到新目录重新构建,
消除旧构建输入后, 安装包 72 项测试全部通过.
首次 Ruff 检查发现基础 Python 环境未安装该模块. 临时隔离环境提供 Ruff 0.14.0
及 wheel 工具, 未增加项目依赖.

## 上游探测与边界

这些是独立构建/运行探测, 不是适配器集成或 fixture 链路.
源码位于仓库外的 `/tmp/tapf-chain-mawpf` 和 `/tmp/tapf-chain-winktpg`.

| 来源 | 固定 commit | 许可证 / 结果 |
| --- | --- | --- |
| [MAWPF](https://github.com/HirokiNagai-39/mawpf) | `0cdb8e43797aff3781e4cd3ddb2c6d7d36f3df17` | MIT; 构建成功; 单机器人场景探测返回 `invalid N, check instance` |
| [WinkTPG](https://github.com/JingtianYan/WinkTPG-IEEE-TASE) | `dd96946f225e206de35b041320786eab43210658` | 未发现许可证文件; 不再分发上游源码; 使用下述 include 参数构建成功 |

检出固定源码后执行:

```bash
cmake -S /tmp/tapf-chain-mawpf -B /tmp/tapf-chain-mawpf/build -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/tapf-chain-mawpf/build -j 4
cmake -S /tmp/tapf-chain-winktpg -B /tmp/tapf-chain-winktpg/build \
  -DCMAKE_PREFIX_PATH=/home/yimin/miniconda3/envs/lacam-tapf \
  '-DCMAKE_CXX_FLAGS=-include unordered_map'
cmake --build /tmp/tapf-chain-winktpg/build -j 4
```

本环境使用 `/home/yimin/miniconda3/envs/lacam-tapf/bin` 中的 CMake.
WinkTPG 首次构建因 `simulator.h` 缺少 `unordered_map` include 失败.
编译参数修正本地构建, 不改动上游源码. 使用 Boost 1.85.0 和 GCC 13.3.0.
另用 `(0,0)` 至 `(4,0)` 的路径执行 `tpg -p path.txt -m 1 -o winktpg.csv`, delay type 为 0.
CSV 报告 success 1, solution cost 4.5. 它是统计输出, 不是 API MotionPlan.
MAWPF 输入为 5-by-1 空地图, 起点 `(0,0)`, 终点 `(4,0)`, 一台机器人,
LaCAM, seed 0, 时间限制 5 s, path length 2, max speed 1, rotation steps 1.
日志位于 `/tmp/tapf-chain-native-smoke/`; 未生成成功的 MAWPF 路径.
未验证包含物理动作的原生链路, 连续几何, 拼接安全, 停车或 TAPF 替换.

## 网页, review 与下一步

持续维护网页已区分 fixture 组合和缺失的原生阶段.
现有导入图为 6 节点和 6 条依赖; 目标流程保留 14 节点和 15 条虚线目标连接.
6 个模块已有实现; 原生适配器集成仍为 0.
浏览器检查通过两种语言和图, 28 次模块选择, 键盘操作, 手机溢出和 JS 错误检查. 已检查桌面和手机截图. 私有发布成功. 未对托管登录流程做浏览器测试. 源码保留在本仓库;
Sites 使用独立 checkout, 保留既有项目和仅所有者访问范围.

相对 origin/main: 代码 +306/-23 = 329 行, 包括测试和网页; 配置 0.
文档单独计入 PR 说明. gpt-6-luna / low 双语复核通过技术事实, 相对链接, doc-sync
和英文标点检查. 等待用户 review 和合并.
合并后, 用可行分配与固定版本原生适配器替换 fixture 阶段, 保留同一组合入口.
合并前不提前开发后续 PR.

[私有网页](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site).
Sites 源码 commit: `69456164727f18ac4085eef0c978c3320eea6228`.
版本: `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_f20650b374ec8191bf4832b034aa39e4`.
原生发布结果为 `succeeded`; 仅所有者访问范围和主仓库 remote 不变.
