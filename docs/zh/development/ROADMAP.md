# 开发计划

[中文](../../zh/development/ROADMAP.md) | [English](../../en/development/ROADMAP.md)

<!-- doc-sync: roadmap / 2026-10-23-r25 -->

状态: PR #13 已合并, 已确认基线 `cabdac3`. 本轮实现共享轨迹求值与精确切片, [PR #14](https://github.com/Requora/TAPF_MAPF_TPG/pull/14) 待 review.
`trajectory.evaluate / slice_curve` 读取已有 Hermite 曲线, 保留全部内部节点.
解析曲线测试和真实原生轨迹 36 次切片比较已通过, 最大位置/速度误差 1.67e-15.
这是共享工具, 尚未接入连续验证器或中央执行器. Runtime, 连续安全和联合仓库适配仍未完成.
性能基准: 1000 台, 128 节点, 50 Hz 的整车队求值中位数 80.406 ms, 超过 20 ms 周期; 重复校验是热点. C++ 段内求值对照约快 117-172 倍, 尚未接绑定或替换生产代码.
见 [共享轨迹](0014-shared-trajectory.md).

## 可替换模块

```mermaid
flowchart TD
    O[订单生成器 / OrderSource] -->|Order| R[Runtime]
    R -->|PlanningRequest| P[DecisionPipeline]
    P --> A[Allocator]
    A -->|TaskDelta| C[SharedCompiler]
    C -->|RobotJobs| M[PathPlanner: MAPF 适配器]
    M -->|FleetPlan: routes + before| T[MotionPlanner: TPG 适配器]
    P --> J[联合 TAPF: 分配 + 路径]
    J -->|TaskDelta + compiled jobs + FleetPlan| T
    T -->|MotionPlan: prefix + stop_tail| P
    P -->|ExecutableProposal| R
    R --> V[共享 Validator]
    V -->|全部接受或全部拒绝| R
    R -->|ExecutionInput| E[CentralExecutor]
    E -->|IdealControlFrame| B[外部后端边界]
    B -->|Observation| R
```

图中描述完整目标设计. 单车道规划子集已本地跑通, 完整闭环尚未完成. 后端位于本次工作范围之外.
测试可提供固定观测和替身. 通过构造函数注入选择实现.
新增算法不应要求改动 Runtime 或公开请求字段. 原生依赖保持可选.

`DecisionPipeline.solve(PlanningRequest)` 是统一替换边界.
分阶段实现组合分配器, 编译器, MAPF 和运动规划器.
联合 TAPF 同时替换分配和路径搜索, 然后使用相同的编译语义,
运动适配器, 验证器和最终提交. 同时优化运动的求解器也可直接实现整个边界.
不要增加强制中间提交, 也不要声称 TAPF 已处理仓库库存.

## 分批阶段与验收证据

| 阶段 | 范围 | 标记为已实现前需要的证据 |
| --- | --- | --- |
| 1 | 共享 API 契约, 包, review 规则 | 独立安装与导入; 原件哈希 |
| 2 | 结构 codec 和选定 fixture | 往返转换; 拒绝未知字段和无效值 |
| 3 | 订单源与带 seed 的订单生成 | 有序发布, 合并 SKU, 不重复发布, 拒绝时间倒退, reset 重放 |
| 4 | 共享任务编译器 | 当前任务剩余动作, D1 锁, 携带归属, 共用量化耗时; 暂缓队列后缀编辑 |
| 5 | 分配适配器 | 库存与需求可行, 稳定任务 ID, 输入快照不变 |
| 6 | MAPF 进程适配器 | 真实固定版本可执行文件, 相邻边, 重复资源访问, 完整先后关系, 超时 |
| 7 | TPG 进程适配器 | 真实速度曲线, 精确拼接, 动作耗时, 全车队停车尾段, 明确不支持的情况 |
| 8 | 分阶段与联合 TAPF 组合 | 在同一受支持 fixture 上用 CBS-TA 替换独立分配/MAPF |
| 9 | 连续验证器 | 采样间交叉, 跟随, 载货转弯, 资源容量, 无限期终点占用 |
| 10 | Runtime 事务与分支 | 不重复预留, 幂等提交, 拒绝过期结果, 保护 Lift, 到期分支优先 |
| 11 | 中央执行器与集成重放 | 接入共享 Hermite 切片, 保留切换节点, 动作只启动一次, 事件去重 |

扩展上游集成前先定义并测试适配器支持的子集.
不支持的边中间起步, 载货交接, 几何, 循环旋转或动作语义必须明确拒绝,
不能默默简化问题. 中间适配器 PR 不必声称所有阶段均可运行.
共享验证器和停车要求满足之前, 不接受任何可执行方案.

## 上游候选

检查日期为 2026-10-20. MAWPF/WinkTPG 的单车道子集已集成验证; libMultiRobotPlanning 的目标分配实验已真实运行, 不代表通用仓库支持.

| 候选 | 证据与建议用途 | 适配工作 / 限制 |
| --- | --- | --- |
| [MAWPF](https://github.com/HirokiNagai-39/mawpf) | C++17; CLI 可选 LaCAM, PIBT, LNS2 或 PP; MIT | 单车道图/状态/任务转换和动作支持检查已本地运行. 多机器人路径, 障碍, 转弯, 跨格移动和资源先后关系仍未完成. |
| [WinkTPG](https://github.com/JingtianYan/WinkTPG-IEEE-TASE) | C++20 和 Boost; 路径文件输入, CSV 输出; 模式 1 为 WinkTPG, 0 为 TPG | 单车道物理动作和精确 Hermite 拼接已本地运行. 多机器人运动和连续全车队停车检查仍未完成. 检查的文件树中未发现许可证文件; 再分发前需明确使用条款. |
| [libMultiRobotPlanning](https://github.com/whoenig/libMultiRobotPlanning) | C++14; CBS/ECBS, CBS-TA/ECBS-TA, 最小费用分配与次优分配枚举; MIT | 目标分配, CBS 和 CBS-TA 对照已真实运行. 目标分配示例不表达 SKU 选择, 货架服务或队列锁. |

检查的 commits (各自的原生构建均已固定):

- MAWPF: `0cdb8e43797aff3781e4cd3ddb2c6d7d36f3df17`.
- WinkTPG: `dd96946f225e206de35b041320786eab43210658`.
- libMultiRobotPlanning: `4c75fa20c435c440d8b6bd6dc81668ddc7296ba0`.

分配先测试具有明确可行边的最小费用机器人/任务匹配.
仓库专用代码仍需选择可行货架, 拣选项, 工作站和归还位置.
匹配本身不解决库存或服务顺序.
每个机器人一个目标的双车受限实验已完成, 包含平局分配和会车口绕行.
后续需适配共享任务语义与多动作仓库任务; CBS-TA 尚不支持完整仓库 API.

阶段 8 已验证单车道分阶段链路与独立目标分配原生实验. 联合仓库流水线和通用原生集成仍为计划.

## 可观察性

每次真实集成运行记录请求 ID, 输入 fixture, 上游 commit, 命令/配置,
seed, 墙钟预算, 退出状态, 诊断和归一化结果.
修复时保留最小失败重放. 追踪分配, 路线访问/先后关系, 运动节点和停车决策.
有真实求解器输出可检查时再增加重放界面.
fixture 通过与原生求解器运行必须分别标注.
