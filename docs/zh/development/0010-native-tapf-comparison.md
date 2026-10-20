# 真实目标分配与 CBS-TA 对照

[中文](../../zh/development/0010-native-tapf-comparison.md) | [English](../../en/development/0010-native-tapf-comparison.md)

<!-- doc-sync: native-tapf-comparison / 2026-10-20-r1 -->

## 范围与来源

已确认 PR #9 由用户合并, 远端基线为 `04d4cda44f3ad9a78bed2f53946c5524702239c6`.
本轮分支 `feat/native-tapf-comparison`, 实现验证基线 `b2a3f77`. PR 链接待创建后补齐.
状态为真实上游目标分配实验已验证, 不是仓库联合流水线已实现.
仓库规划 API, DTO, 依赖图和单车道支持范围不变. 进程工具增加可选 cwd 参数以隔离原生辅助文件. 本轮继续遵守 500 行限制.

上游 [libMultiRobotPlanning](https://github.com/whoenig/libMultiRobotPlanning/tree/4c75fa20c435c440d8b6bd6dc81668ddc7296ba0)
固定 commit `4c75fa20c435c440d8b6bd6dc81668ddc7296ba0`, MIT 许可证.
`integrations/tapf/CMakeLists.txt` 直接构建未改动的 assignment, cbs, cbs_ta 示例.
构建检查 commit 和已跟踪文件差异, 不复制上游代码或二进制到仓库.
C++14, Boost program_options 和 yaml-cpp 为构建依赖. PyYAML 6.0.3 仅用于读取研究输出, 不是包运行依赖.

## 决策与真实轨迹

样例有两个点机器人, 单位格移动与等待均耗时一个 tick. 主通道为 `(0,0)` 到 `(4,0)`,
只有 `(2,1)` 可用于会车. 起点为 `(0,0)` 和 `(1,0)`, 两台机器人都可选择 `(3,0)` 或 `(4,0)`.
独立距离矩阵为 `[[3,4],[2,3]]`, 两个完整匹配的代价均为 6.

| 方案 | agent0 目标 | agent1 目标 | 原生总路径代价 |
| --- | --- | --- | --- |
| 固定分配 0 + CBS | (3,0) | (4,0) | 6 |
| 固定分配 1 + CBS | (4,0) | (3,0) | 8 |
| CBS-TA 联合搜索 | (3,0) | (4,0) | 6 |

本地原生 assignment 选择固定分配 1. 平局顺序可能随实现/环境变化, 测试不要求固定平局选择.
两种分配全部运行 CBS, CBS-TA 与其中最小代价比较. 这验证本样例的最优结果, 不是普遍性能优势.
固定分配 1 的实际路径如下, 可以在 HTML 中逐步查看:

| tick | agent0 | agent1 |
| --- | --- | --- |
| 0 | (0,0) | (1,0) |
| 1 | (1,0) | (2,0) |
| 2 | (2,0) | (2,1) |
| 3 | (3,0) | (2,0) |
| 4 | (4,0) | (3,0) |

研究校验模块独立检查初态, 目标资格, 相邻移动/等待, 障碍, 时间连续性, 顶点冲突,
对向边交换, 到达后持续占用及统计代价. 终点在最大到达时间后均保持不动, 因此无需无限循环检查离散静止终态.
这不验证机器人形状, 连续采样间碰撞或物理停车.
实验只调用已公开的 `native_process.run_native`, 仅扩展进程工具的可选 cwd 参数, 不引入仓库规划 API 或不兼容 DTO.

## 验证与重放

先安装 CMake, C++ 编译器, Boost program_options, yaml-cpp 和 PyYAML 6.0.3.
本地使用 GCC 13.3.0, Boost 1.85.0, yaml-cpp 0.8.0.
本地 CMake 在 `/home/yimin/miniconda3/envs/lacam-tapf/bin`, 配置时额外传入
`-DCMAKE_PREFIX_PATH=/home/yimin/miniconda3/envs/lacam-tapf`.

```bash
git clone https://github.com/whoenig/libMultiRobotPlanning.git /tmp/warehouse-tapf-upstream
git -C /tmp/warehouse-tapf-upstream checkout 4c75fa20c435c440d8b6bd6dc81668ddc7296ba0
cmake -S integrations/tapf -B /tmp/warehouse-tapf-pinned \
  -DLMRP_SOURCE_DIR=/tmp/warehouse-tapf-upstream -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/warehouse-tapf-pinned -j 2
WAREHOUSE_TAPF_BIN=/tmp/warehouse-tapf-pinned PYTHONPATH=src:tests \
  python -m unittest tapf.test_comparison -v
PYTHONPATH=src:tests python -m tapf.replay /tmp/warehouse-tapf-pinned \
  --output /tmp/warehouse-tapf-evidence-new
```

每次重放要求新的或空的输出目录. 目录保存输入, 4 次调用的 YAML/stdout/stderr/run.json 和各调用子目录中的辅助输出,
汇总 comparison.json 和离线 replay.html. 汇总保留上游 commit, 许可证, 二进制 SHA256,
每次调用预算 10 s 和 `seed: null` (无随机生成). 所有错误保留 traceback.
本地结果: 6/8/6, 4 次退出码均为 0, 86 项源码测试通过.
没有原生二进制时共运行 86 项, 其中 82 项通过, 4 项跳过; 普通测试不要求 PyYAML.
CI 新增独立原生实验 job, 纳入 CI gate 并上传完整证据目录.
桌面和手机重放检查通过: tick 2 的真实会车口位置, 三个面板, 单步按钮, 键盘及无溢出. 进展网页 check.py 检查通过, 两种页面的桌面/手机截图已检查. 干净源码构建的 wheel 在 Python 3.14 隔离模式中通过 86 项测试, pip check 通过. Ruff, JavaScript 语法及 diff 检查通过. 远端 CI 结果待提交后补充.

## 失败记录与边界

TDD Red: 新增测试先因 `tapf.replay` 尚未存在而失败. 实现后真实原生测试和四项离散检查通过.
额外回归先证明非空目录会继续调用不存在的二进制, 抛出 FileNotFoundError;
修正后在任何调用前返回 FileExistsError, 保留旧证据, 第六项测试通过.
系统默认 Python 缺少 PyYAML 的首次回归尝试暴露依赖错误, 随后用已配置环境重现目标行为.
首次本地构建因使用非命名空间 yaml-cpp 链接名而失败, 改为导出的 `yaml-cpp::yaml-cpp` 目标后通过.
真实运行发现上游 CBS-TA 在工作目录输出 searchGraph.dot. 新回归先因 cwd 参数缺失而失败, 再扩展进程工具并记录子进程目录. 第七项新增测试通过, 原生辅助输出位于证据目录, 调用者目录不变.
系统 PATH 无 CMake/Node; 使用已有工具绝对路径, 未修改上游源码.

仓库 SKU, 货架选择, Lift/Serve/Drop, 锁, 共享编译, TPG, Runtime, 执行和连续安全未接入此实验.
两个目标的完全枚举只作为本样例的对照, 不新增通用求解器或宣称大规模最优性验证.
下一步在用户 review 并合并本 PR 后, 才设计联合目标结果到统一仓库契约的受限适配.

## 网页, 行数与交付

进展网页同步 PR #9 合并状态与实验边界, 联合业务连接仍为虚线.
仓库原生适配器集成数保持为 2, 独立目标实验不冒充第三个仓库适配器.
网页源码在本 PR 审查, 通过独立 Sites checkout 更新同一私有站点.
发布结果, 最终行数与 PR 链接待完成后记录.
