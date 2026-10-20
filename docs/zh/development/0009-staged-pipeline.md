# 真实订单到 TPG 规划链路

[中文](../../zh/development/0009-staged-pipeline.md) | [English](../../en/development/0009-staged-pipeline.md)

<!-- doc-sync: staged-pipeline / 2026-10-20-r2 -->

## 范围与状态

原生规划链已在本地跑通: 订单发布 -> 可行分配 -> 共享编译 -> 上游 MAWPF -> 上游 WinkTPG -> 候选 MotionPlan. `tests/native/replay.py` 不使用求解器测试替身.

支持范围为一台机器人, 一个落地货架, 一行需求/库存, 向东的单位间距直线车道. 机器人从节点 0 出发, 依次到取架位, 工作站和更靠后的空归还位. 朝向均为零, 起步静止, 无障碍. 不能表达的约束返回 `UNSUPPORTED`; 库存不足返回 `NO_PLAN`. 这是受限的真实集成, 不是通用仓库求解器或执行闭环.

[PR #9](https://github.com/Requora/TAPF_MAPF_TPG/pull/9) 之前只完成 fixture 串联便提前提交. 用户指出后已转为草稿. 用户在收到 500 行例外请求后授权继续同一个 PR. 本次修正纳入原生实现; 后续 PR 仍遵守原限制. 未新建其他 PR, 未合并.

验证源码快照为基线 `a0e14f7` 加本地代码. 源码 SHA256 为 `1f8a35d1c83eedd502342d7f4d7aba3f82335b846752cea5fdf584e9267c170a`. 计算范围为 src, tests, integrations 下排序后的 `.py`, `.cpp`, `.html`, `.txt`, 排除 __pycache__; 每个相对路径和空字节后追加文件字节. 源码哈希独立标识已测试的原生实现, 不受后续文档提交影响.

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

实际结果: 启用真实二进制后, 源码 79 项与干净安装包 79 项测试全部通过. Ruff, pip check 和 diff 检查通过. 未配置 WAREHOUSE_NATIVE_BIN 时明确跳过三项原生链路测试. 原生二进制仍是可选包依赖. 独立原生 CI job 构建固定版本上游并上传真实 JSON/HTML 重放. 本提交的远端运行待检查.

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

## 未验证边界与交付

多机器人冲突/先后关系, 转弯, 障碍, 运动中拼接, 已接受任务进度, 重分配, 联合 TAPF, Runtime 事务, 连续几何, 无限期停车占用, 中央执行和物理后端仍未验证或未实现. 适配器明确拒绝不支持的输入. MotionPlan 是候选, 不是 Accepted.

PR #9 在远端原生 CI 检查期间保持草稿. 用户已同意本 PR 行数例外. 提交时有效代码变更为 1,192 行 (+1,143/-49); 文档和配置在交付时单独披露. 先前私有网页版本描述早期 fixture 快照, 不代表本次新运行. 上述本地 HTML/JSON 是当前原生证据.
