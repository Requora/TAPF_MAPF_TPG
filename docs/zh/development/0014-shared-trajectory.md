# 共享轨迹求值与精确切片

[中文](../../zh/development/0014-shared-trajectory.md) | [English](../../en/development/0014-shared-trajectory.md)

<!-- doc-sync: shared-trajectory / 2026-10-23-r4 -->

## 当前实现: C++ 核心

用户要求正式使用 C++. 求值, 切片和结构校验现由包内 `_native.cpp` / `_validation.hpp` 执行. Python `_curve.py` 仅转换统一契约. `PreparedTrajectory(knots)` 创建独立只读原生快照, 一次转换并校验; `evaluate(snapshot, t)` 和 `slice_curve(snapshot, a, b)` 复用快照. 原有 tuple 输入仍兼容, 但每次调用都会转换和校验. 返回值仍为 Knot 或 tuple[Knot, ...], 不暴露原生类作为公共 API.

这不是重新规划, 不包含连续碰撞验收或执行器. 不缓存实时账本. 节点仍顺序查找, 当前绑定保持 GIL; 未声称并行加速. 旧 Python 插值/校验实现及临时 C++ 对照程序已删除, 避免保留两套运行核心. 下方旧验证数字与无绑定对照属于历史记录, 以本节和末尾新证据为当前状态.

## 范围与决策

PR #13 已确认合并于 `cabdac3572290707cbf3405d850031632ea62b1f`. 分支: `feat/shared-trajectory`. 本 PR 新增 `warehouse_api.trajectory.evaluate` 和 `slice_curve`, 使用已有 Knot/Pose2/Twist2 契约. 唯一新增生产依赖为 trajectory -> contracts. 不修改求解器, 执行器, Runtime 或后端行为.

API 0.7 第 8 和 10 节规定三次 Hermite 曲线和精确切片. 适配器已经定义曲线; 该工具读取已有曲线, 不再规划另一条曲线. 来源为保持原样的用户参考 `warehouse_api_v0_7/package/warehouse_api/trajectory.py`, SHA256 为 `13bb45ebb55468bd0af2c6f51f87df7ea359df1be51b0e97f4c566835d8eec62`. 不新增运行时库或改变规划器上游版本; 当前新增的构建依赖 pybind11 见下文. 不移植 ReferenceExecutor.

两个 API 返回不可变契约对象, 非法曲线或范围抛出 ValueError. 包内校验检查有限值, 正且有限的时间间隔及覆盖范围. 位置和速度使用参考 Hermite 公式, 朝向不折返. 切片保留两端及全部内部节点, 包括加速度切换点, 允许浮点运算误差.

与参考的有意差异: 不在节点附近用 EPS 吸附; 仅精确零终速允许无限期保持. 移动单节点可读取其精确瞬间, 对齐 PR #13 的立即制动前缀, 但不能延伸. 校验规则放在插值逻辑之外. 消费者需先将立即切换前缀与合法尾段拼接, 再跨该边界截取正时长区间.

## 验证与失败记录

TDD: 新增解析行为测试先因 warehouse_api.trajectory 不存在而报 ModuleNotFoundError (`/tmp/trajectory-red.log`). 实现后六项全部通过: 独立三次位置/导数, 未折返朝向, 嵌套切片/输入不变, 加速度切换/终点保持, 移动终点拒绝, 非法输入及亚纳秒区间.

```bash
PYTHONPATH=src python -m unittest discover -s tests/trajectory -v
WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src:tests python -m trajectory.replay /tmp/tapf-chain-bridges --output /tmp/trajectory-native.json
/tmp/warehouse-ci-check/bin/ruff check src tests web/progress/check.py
git diff --check
```

完整测试: 103 项, 102 通过, 1 项可选 CBS-TA 测试跳过. 原生重放运行 MAWPF/WinkTPG, 对原曲线与切片比较 36 组 x 位置和 x 速度状态, 最大绝对误差 1.67e-15. JSON 保留请求, 原生原始输出, 二进制哈希, 阶段 trace 和成对状态. x 与 vx 的误差最大值合并了不同单位, 只作数值回归摘要, 不是物理安全指标. 日志: `/tmp/trajectory-tests.log`. 复用既有固定版本二进制, 未重新构建: MAWPF `0cdb8e4`, WinkTPG `dd96946`; 见 [原生集成](0009-staged-pipeline.md).

## PR 与下一步

[PR #14](https://github.com/Requora/TAPF_MAPF_TPG/pull/14) 等待 review. 网页与路线图区分已实现的共享工具和仍仅接口的 CentralExecutor 及连续 Validator. 提交后等待 review, 不启动下一 PR.

连续碰撞, 资源容量, 运动限制校验, 无限期停车安全, Runtime 提交, 动作分发, 事件去重, 联合仓库适配和后端执行仍未验证或未实现. 曲线一致性测试不证明安全.

最终本地检查: 干净源码目录构建并安装 wheel 后, 103 项测试中 102 通过, 1 跳过, pip check 通过. 环境: `/tmp/trajectory-wheel-kt1j73tx/venv`; 日志: `/tmp/trajectory-wheel-tests.log`. Ruff, JS 语法及 diff 检查通过. 网页检查通过双语, 两张图, 32 次模块选择, 键盘和手机布局, 无 JS 错误; 桌面和手机截图已人工检查. gpt-6-luna/low 独立审查通过双语事实及本地链接, 已按建议将路线图阶段 11 明确为执行器接入共享切片. 未检查托管登录或本 PR 远端 CI.

私有发布成功: [进展页](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site). Sites 源码 `d8d144d24535054714802de812f49510840a71ad`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_298c14963dd481919fd1aacd4f712ddc`. 使用独立临时 checkout, 仓库 remote 未改变, 仅所有者访问不变. 托管登录未验证.

过程失败记录: Sites helper 首次初始化返回通用失败, 后续独立目录打开成功; 未修改业务代码规避. 会话重启后预览服务停止, 浏览器报连接拒绝; 重启本地服务后全部网页检查通过. 原始 TDD 失败记录见上文.

最终相对 `cabdac3` 的代码含测试/网页变更为 295 行, 文档为 134 行, 配置无变化. 用户已有 .gitignore 改动, helloworld.md 和参考包未加入. 最终提交远端 CI 待确认.

## 性能基准补充

按用户要求在同一 PR 补充 [性能基准与全部原始样本](0014-trajectory-performance.md). 36 组合成案例覆盖 1/100/1000 台, 每车 16/128/1024 节点, 10/50 Hz 的求值和切片. 1000 台, 128 节点, 50 Hz 的全车队求值中位数 80.406 ms, 超过 20 ms 周期. 独立 cProfile 显示主要耗时来自重复节点校验. 本次未修改生产代码, 不宣称加速.

新增工作量测试先因模块缺失而失败后通过. 源码和既有干净安装 wheel 都为 104 项, 103 通过, 1 跳过; 未重建 wheel. `/tmp/trajectory-benchmark.json` 和 `/tmp/trajectory-benchmark.log` 保留基准, `/tmp/trajectory-profile.log` 保留独立热点分析. 基准是串行合成测量, 不含完整系统, 共享主机负载未隔离. 上文 295/134 行是初次交付统计.

补充验证: Ruff, JS 语法, diff 和双语/键盘/手机网页检查通过, 桌面和手机截图已检查. gpt-6-luna/low 独立审查确认数值, 双语事实及链接一致; 已补 stdout 重定向让命令复现基准日志.

性能快照私有发布成功: Sites 源码 `8654dfb66516ce6a4fbd84551751253e6f2eb443`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_ad011024774c81918acc26bd0515ad57`. 继续使用上文地址和仅所有者访问, 独立 checkout 未改变仓库 remote; 托管登录未验证.

本次更新后整个 PR 相对 `cabdac3` 的代码含测试/网页为 416 行, 文档为 412 行, 配置无变化. 原始测量样本作为文档表格保留, 未通过生成代码规避限制. 最终远端 CI 待确认, 提交后等待 review.

## C++ 对照补充

按用户要求增加 82 行 C++ 段内求值实验. 相同车队和节点数, 每次仍全量校验并顺序查找; 不做缓存或索引优化. 4 组新鲜对照显示约 117-172 倍差异, 1000 台/1024 节点为 Python 649.473 ms 对 C++ 4.903 ms. 三轴三次解析状态及全部匀速输出检查通过. 结果包含语言和数据布局影响, 未测切片, 绑定, 数据转换或完整执行链. 详见 [原始样本与命令](0014-trajectory-performance.md#c-求值对照).

C++ 使用 g++ 的 C++17/O3 编译并通过解析检查. 另以 `-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer` 构建, 在 1000 台/1024 节点/50 Hz 案例运行通过, 无 sanitizer 诊断. 源码测试 104 项, 103 通过, 1 跳过. JS 语法, diff, 双语/键盘/手机网页检查通过, 截图已检查; gpt-6-luna/low 确认双语与样本一致. 全 PR 相对 `cabdac3` 为代码 498 行, 文档 514 行, 配置无变化. 最终远端 CI 待确认.

C++ 快照私有发布成功: Sites 源码 `23ce8e4b93365ba0041f037670a8a845ad1b57b5`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_93e9783413048191b9c06c887a6989ef`. 继续使用上文地址, 保持仅所有者访问. 独立 checkout 未改变仓库 remote; 托管登录未验证. 提交后等待当前 PR review.

## C++ 绑定与安装验证

TDD: 新增快照复用测试先因 PreparedTrajectory 不存在而失败 (`/tmp/trajectory-cpp-binding-red.log`), 实现后通过. 全部已有曲线边界与切片测试现在经过 C++ 核心. 源码与干净 sdist -> wheel 安装均为 105 项, 104 通过, 1 项 CBS-TA 跳过. pip check 通过. `/tmp/trajectory-native-wheel-tests.log` 与 `/tmp/trajectory-native-wheel-build.log` 保留安装证据. 真实 MAWPF/WinkTPG 输出经 C++ 核心的 36 次切片比较最大 x/vx 误差仍为 1.67e-15.

构建依赖固定为 [pybind11 v3.0.1](https://github.com/pybind/pybind11/tree/v3.0.1), commit `f5fbe867d2d26e4a0a9177a51f6e568868ad3dc8`, BSD-3-Clause; 包内保留原始许可证. 按 [官方构建方法](https://pybind11.readthedocs.io/en/stable/compiling.html) 用 setuptools/Pybind11Extension 和 C++17 构建. pybind11 仅为构建依赖; wheel 为平台/CPython ABI 专用, Linux x86_64/CPython 3.14.7 已验证, 其他平台与 Python 版本尚未验证. 本机实际编译使用 g++ 和 Python 工具链的 `-O2`, 并非前述独立对照的 `-O3`.

```bash
python -m pip install -e .
WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges python -m unittest discover -s tests -v
PYTHONPATH=tests python -m trajectory.replay /tmp/tapf-chain-bridges --output /tmp/trajectory-bound-native-replay.json
PYTHONPATH=tests python -m trajectory.benchmark --prepared --robots 100 1000 --knots 128 1024 --hz 50 --output /tmp/trajectory-bound-prepared.json
```

开发时先安装扩展, 不能只设置 PYTHONPATH 就使用未编译的源码. 安装 wheel 后不需要本地编译器. 原生求解器仍为可选外部依赖; 轨迹模块自身现需编译扩展.

最终绑定检查: Ruff 和 JS 语法通过. 首次页面语法检查发现缺失右括号; 修复后双语, 键盘和手机浏览器检查通过. 已检查桌面和手机截图. 最终 wheel 包含扩展, 校验头文件和上游许可证. 整个 PR 相对 `cabdac3`: 472 行代码, 658 行文档, 29 行许可证和 5 行配置 (新增 + 删除). 远端 CI 尚未确认; 不宣称完整系统实时性或连续安全已验证.

绑定快照已私有发布: Sites 源码 `ec92f51bfe65bd8a83aac9bbe5cc3b49cebde10d`, 版本 `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_321aaf3740e88191b13fceac536af1a3`, 部署成功. 上述 URL 和仅所有者访问权限不变; 托管登录尚未验证. 独立 checkout 保持本仓库 remote 不变. 推送后等待 PR #14 review.
