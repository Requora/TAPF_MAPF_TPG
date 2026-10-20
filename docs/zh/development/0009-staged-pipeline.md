# 真实订单到 TPG 规划链路

[中文](../../zh/development/0009-staged-pipeline.md) | [English](../../en/development/0009-staged-pipeline.md)

<!-- doc-sync: staged-pipeline / 2026-10-20-r6 -->

## 范围与状态

原生规划链已在本地跑通: 订单发布 -> 可行分配 -> 共享编译 -> 上游 MAWPF -> 上游 WinkTPG -> 候选 MotionPlan. `tests/native/replay.py` 不使用求解器测试替身.

支持范围为一台机器人, 一个落地货架, 一行需求/库存, 向东的单位间距直线车道. 机器人从节点 0 出发, 依次到取架位, 工作站和更靠后的空归还位. 朝向均为零, 起步静止, 无障碍. 不能表达的约束返回 `UNSUPPORTED`; 库存不足返回 `NO_PLAN`. 这是受限的真实集成, 不是通用仓库求解器或执行闭环.

[PR #9](https://github.com/Requora/TAPF_MAPF_TPG/pull/9) 之前只完成 fixture 串联便提前提交. 用户指出后已转为草稿. 用户在收到 500 行例外请求后授权继续同一个 PR. 本次修正纳入原生实现; 后续 PR 仍遵守原限制. 未新建其他 PR, 未合并.

验证源码快照为 `a1d0d03b9e1fb7ee711c8ca8b783fa9b1d0885dd`. 该 CI 快照的历史 SHA256 (不是后续 review 工作树哈希) 为 `1f8a35d1c83eedd502342d7f4d7aba3f82335b846752cea5fdf584e9267c170a`. 计算范围为 src, tests, integrations 下排序后的 `.py`, `.cpp`, `.html`, `.txt`, 排除 __pycache__; 每个相对路径和空字节后追加文件字节. 源码哈希独立标识已测试的原生实现, 不受后续文档提交影响.

## 实现与决策

```mermaid
flowchart LR
    O[ReplayOrderSource] -->|Order -> Demand: 重放驱动| A[SingleShelfAllocator]
    A -->|TaskDelta| C[CurrentTaskCompiler]
    C -->|RobotJobs / PathRequest| M[NativeMawpfPlanner / LaCAM]
    M -->|FleetPlan / MotionRequest| T[NativeWinkTpgPlanner / speedSolver]
    T -->|精确节点 + 动作静止段| P[候选 MotionPlan]
```

全部公开规划消息继续使用 contracts.py. StagedPipeline 注入独立阶段, 共用截止时间, 检查路径/动作身份, 并在 `last_trace` 保留真实阶段输入和结果. 只有 Runtime 可以接受候选; Runtime 尚未实现.

SingleShelfAllocator 选择当前支持范围内唯一可行的机器人/货架, 检查可用 SKU 数量, 从已发布需求生成 Pick. 任务 ID 派生自请求 ID. 它不预留库存, 不优化匹配. 此分配器不支持已有任务, 锁定队列或通用分配.

每个动作目标调用一次 MAWPF. 真实上游状态转换成相邻 Move 和编译后的 Do 引用. WinkTPG 消费这些已经选定的移动, 返回每段真实速度原语. 每段终点静止, 然后执行编译动作. 适配器保留加速度切换点为 Hermite 节点, 包括零速到零速三角速度原语的中点. 每个动作前增加静止等待以对齐仿真 tick. 编译耗时和 StepRef 保持不变. 已静止的单机器人收到明确的保持尾段.

`validation` 当前负责支持范围的输入/业务检查, 不是连续 Validator 实现. MAPF 和 TPG 各自校验原生输出. `native_process` 保留命令, 请求 ID, 预算, 实际耗时, 退出码, stdout, stderr 和原始输出. 仅捕获预期的进程 TimeoutExpired: subprocess.run 杀死子进程后映射为 TIMEOUT; 意外错误保留 traceback. 旧输出不能满足新调用.

## 验证与重放

先克隆下表上游 URL, 检出精确 commit. CMake 检查 commit 并拒绝已跟踪源码改动. 本环境 CMake 位于 `/home/yimin/miniconda3/envs/lacam-tapf/bin`, 使用 Boost 1.85.0 和 GCC 13.3.0. 上游源码保持在仓库外.

```bash
cmake -S integrations/native -B /tmp/tapf-chain-bridges \
  -DMAWPF_SOURCE_DIR=/tmp/tapf-chain-mawpf \
  -DWINKTPG_SOURCE_DIR=/tmp/tapf-chain-winktpg \
  -DCMAKE_PREFIX_PATH=/home/yimin/miniconda3/envs/lacam-tapf
cmake --build /tmp/tapf-chain-bridges -j 4
WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src:tests python -m native.replay /tmp/tapf-chain-bridges \
  --output /tmp/tapf-real-chain.json --html /tmp/tapf-real-chain.html
PYTHONPATH=src:tests python -m native.replay /tmp/tapf-chain-bridges \
  --quantity 3 --stock 3 --station 4 --destination 8 \
  --output /tmp/tapf-real-chain-changed.json --html /tmp/tapf-real-chain-changed.html
PYTHONPATH=src:tests python -m native.replay /tmp/tapf-chain-bridges --stock 0 \
  --output /tmp/tapf-real-chain-rejected.json --html /tmp/tapf-real-chain-rejected.html
ruff check src tests web/progress/check.py
```

实际结果: 启用真实二进制后, 源码 79 项与干净安装包 79 项测试全部通过. Ruff, pip check 和 diff 检查通过. 未配置 WAREHOUSE_NATIVE_BIN 时明确跳过三项原生链路测试. 原生二进制仍是可选包依赖. 独立原生 CI job 构建固定版本上游并上传真实 JSON/HTML 重放. [远端 CI 39366365034](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39366365034) 的原生构建, 启用二进制的全部 79 项测试和重放命令均通过. [Artifact 12239575773](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39366365034/artifacts/12239575773) 含 HTML/JSON; zip SHA256 为 `d9e55990ca524a89cb324086568380069c9d855226f35a9365a2b8de308b983b`.

| 重放 | 实际结果 |
| --- | --- |
| 一件商品, 取架 1, 工作站 3, 归还 5 | 六次原生进程调用成功; Lift 2.0 s, Serve 5.2 s, Drop 8.4 s; 8.7 s 完成; 终点速度为零 |
| 三件商品, 工作站 4, 归还 8 | 真实上游路径改变; 服务耗时从 0.3 s 变为 0.7 s; 开始时间 2.0/5.9/10.7 s; 11.0 s 完成 |
| 库存为零 | 分配阶段 NO_PLAN; 没有原生调用 |
| 第二台机器人 | UNSUPPORTED |
| 真实休眠子进程 | 记录 TIMEOUT; 不消费成功结果 |
| 退出为零但无输出 | BACKEND_ERROR; 旧输出已删除 |

测试对默认重放的每个区间解析检查 Hermite 速度和加速度极值, 精确动作静止段, 引用顺序, tick 对齐, 终点位姿, 零终速和尾段拼接. 这些检查不等于连续碰撞或无限期停车验证. 输入快照不变. JSON 证据包含可执行文件 SHA256, 真实阶段输出和完整原生记录.

独立 HTML 重放使用返回的 Hermite 节点, 不虚构采样路径. 可拖动时间, 切换前后节点, 播放, 检查动作/资源, 展开原生输出并查看拒绝案例. 浏览器检查通过六次调用和动作表, 节点切换, 终速, 手机溢出与拒绝展示. 已检查桌面/手机截图. 货架动画根据已规划动作完成时间推导, 不是后端观测.

## 上游来源与失败记录

| 来源 | Commit | 许可证 / 集成 |
| --- | --- | --- |
| [MAWPF](https://github.com/HirokiNagai-39/mawpf) | `0cdb8e43797aff3781e4cd3ddb2c6d7d36f3df17` | MIT; 薄封装导出真实 LaCAM 路径 |
| [WinkTPG](https://github.com/JingtianYan/WinkTPG-IEEE-TASE) | `dd96946f225e206de35b041320786eab43210658` | 未发现许可证文件; 不再分发上游源码/二进制; 导出真实 speedSolver 原语 |

MAWPF 原场景读取返回 `invalid N`, 因为其 U 索引遗漏 omega 维度. 封装用显式属性选取正确的零速/朝东节点, 并设置上游构造函数未初始化的借用图所有权标志. 没有改写搜索算法.

WinkTPG 最初因 simulator.h 缺少 unordered_map 而构建失败, 构建参数增加 `-include unordered_map`. 原 CLI CSV 只有统计结果, 因此封装直接调用 speedSolver, 导出开始时间, 耗时和起止速度. 首次无限规划窗口造成上游整数边界溢出, 现使用有限路径长度. 上游 simEnv 仅作为初始状态容器: 没有运行模拟器 step, 没有新增模拟器/后端实现.

历史 fixture 验证在 `4277591` 通过 73 项测试. 更早的脏工作区 wheel 混入旧平铺模块, 干净导出 `c47f4a7` 后通过当时的 72 项测试. 原生 wheel 从新的纯源码目录构建. 历史数量与当前 79 项原生运行分开记录.

自动 review 已对照源码核实: run_native 在 subprocess.run 前拒绝非正剩余预算. 所指的零速到零速等待实际是上游加速/减速原语: [sipp_ip.cpp 第 334-338 行](https://github.com/JingtianYan/WinkTPG-IEEE-TASE/blob/dd96946f225e206de35b041320786eab43210658/src/sipp_ip.cpp#L334-L338) 用 `2*sqrt(1/a_max)` 表达跨一格运动; 在支持的加速度下, 中点为 x+0.5, 速度为 1. 适配器保留该切换点以精确进行 Hermite 插值. 零需求为 BAD_INPUT; 正需求但库存不足为 NO_PLAN.

## 未验证边界与交付

多机器人冲突/先后关系, 转弯, 障碍, 运动中拼接, 已接受任务进度, 重分配, 联合 TAPF, Runtime 事务, 连续几何, 无限期停车占用, 中央执行和物理后端仍未验证或未实现. 适配器明确拒绝不支持的输入. MotionPlan 是候选, 不是 Accepted.

PR #9 在远端原生 CI 通过后进入待 review 状态; 未合并. 用户已同意本 PR 行数例外. 最终交付在下方分别记录代码, 文档和配置行数. 私有进展网页已更新为 `a1d0d03` 原生证据及远端 CI. 独立重放既保留在本地, 也包含在上述 CI artifact 中.

发布: Sites 返回成功, 保留仅所有者可访问的现有权限. 源码 checkout 为 `/tmp/tapf-chain-site`, 源码 commit 为 `b2bfcbaa6b79cae15f5134d3a3966a8c5b2be6fc`, 版本为 `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_5bb6b11a3b488191bef27287333d8e58`. [私有网页](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site). 架构页浏览器检查通过双语, 双图, 键盘, 手机布局与无 JS 错误; 已检查桌面/手机截图.

相对 `576e25d` 的变更: 代码 1,193 (+1,144/-49); 文档 429 (+378/-51); 配置 58 (+57/-1). 生产源码和上游构建配置未偏离已通过的原生 CI 基线; 下述 review 跟进仅修改测试时钟. 未 vendoring 上游或加入参考包. 下一步: 用户 review PR #9; 合并前不开展后续模块.

## Review 跟进, 2026-10-20

已对照当前源码和固定版本上游核实七条行内意见. 本次新增一项测试修正: 截止时间测试改为 `chain(repeat(0, expired_call), repeat(10))`. 到期后额外读取时钟仍返回到期时间, 不再触发 StopIteration. 保留阶段数量与 TIMEOUT 断言. 相对 `d612355` 仅修改测试 +2/-2 行, 未改变生产行为或原生证据. 已发布架构快照仍适用.

| 意见 | 处理 |
| --- | --- |
| [编译后截止时间](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321133366) | 不改: solve 已在编译之后, MAPF 之前检查截止时间. |
| [路径与任务一致性](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321133367) | 4277591 已修复: 检查机器人覆盖和有序 Do 引用; 回归案例阻止进入运动阶段. |
| [共享预算时钟](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321133372) | 4277591 已改为无限 count(). |
| [截止时间测试时钟](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321153328) | 本次改为无限到期尾段. |
| [原生负预算](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321287871) | 不改: run_native 在启动任何进程前返回 TIMEOUT. |
| [零速到零速运动](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321287874) | 不改: 上游定义跨一格加速/减速; 删除中点会破坏精确插值. |
| [零需求/库存](https://github.com/Requora/TAPF_MAPF_TPG/pull/9#discussion_r4321287876) | 不改: 零需求是非法输入; 正需求且零库存是不可行. 两种失败码有意区分. |

验证: `PYTHONPATH=src:tests python3 -m unittest planning.test_staged -v` 的 9 项测试全部通过. Ruff 和 diff 检查通过. 直接检查确认预算 0/-1 返回 TIMEOUT, 不启动不存在的可执行文件且不创建文件; 零库存为 NO_PLAN, 零需求为 BAD_INPUT. 原生范围, 连续安全边界, PR 状态及网页证据基线不变.

用户追加约定已写入根目录 AGENTS.md: 每个函数使用中英文注释或 docstring, 说明用途, 函数存在的必要性和执行这项工作的原因; 函数变化时同步注释. 根目录 AGENTS.md 仍仅保留中文规则文件.

[Review 修正 CI, 990b3f1](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39372553744) 的静态检查, 安装包测试, 真实原生测试和 CI gate 全部通过.

用户追加 TDD 开发要求: Red -> Green -> Refactor; 先确认测试因缺少目标行为而失败, 再最小实现, 最后保持测试通过进行重构. 修复 bug 先增加复现问题的回归测试. 本次仅修改规则和双语记录, diff 检查通过, 未重跑代码测试.
