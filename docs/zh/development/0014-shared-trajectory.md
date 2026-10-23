# 共享轨迹求值与精确切片

[中文](../../zh/development/0014-shared-trajectory.md) | [English](../../en/development/0014-shared-trajectory.md)

<!-- doc-sync: shared-trajectory / 2026-10-23-r1 -->

## 范围与决策

PR #13 已确认合并于 `cabdac3572290707cbf3405d850031632ea62b1f`. 分支: `feat/shared-trajectory`. 本 PR 新增 `warehouse_api.trajectory.evaluate` 和 `slice_curve`, 使用已有 Knot/Pose2/Twist2 契约. 唯一新增生产依赖为 trajectory -> contracts. 不修改求解器, 执行器, Runtime 或后端行为.

API 0.7 第 8 和 10 节规定三次 Hermite 曲线和精确切片. 适配器已经定义曲线; 该工具读取已有曲线, 不再规划另一条曲线. 来源为保持原样的用户参考 `warehouse_api_v0_7/package/warehouse_api/trajectory.py`, SHA256 为 `13bb45ebb55468bd0af2c6f51f87df7ea359df1be51b0e97f4c566835d8eec62`. 不新增外部库或改变上游版本. 不移植 ReferenceExecutor.

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

交付前补充 PR 链接以及最终安装, 浏览器, 文档审查和发布证据. 网页与路线图区分已实现的共享工具和仍仅接口的 CentralExecutor 及连续 Validator. 提交后等待 review, 不启动下一 PR.

连续碰撞, 资源容量, 运动限制校验, 无限期停车安全, Runtime 提交, 动作分发, 事件去重, 联合仓库适配和后端执行仍未验证或未实现. 曲线一致性测试不证明安全.

最终本地检查: 干净源码目录构建并安装 wheel 后, 103 项测试中 102 通过, 1 跳过, pip check 通过. 环境: `/tmp/trajectory-wheel-kt1j73tx/venv`; 日志: `/tmp/trajectory-wheel-tests.log`. Ruff, JS 语法及 diff 检查通过. 网页检查通过双语, 两张图, 32 次模块选择, 键盘和手机布局, 无 JS 错误; 桌面和手机截图已人工检查. gpt-6-luna/low 独立审查通过双语事实及本地链接, 已按建议将路线图阶段 11 明确为执行器接入共享切片. 未检查托管登录或本 PR 远端 CI.
