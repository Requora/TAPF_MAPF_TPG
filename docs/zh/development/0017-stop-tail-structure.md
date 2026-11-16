# 停车尾段结构检查

[中文](../../zh/development/0017-stop-tail-structure.md) | [English](../../en/development/0017-stop-tail-structure.md)

<!-- doc-sync: stop-tail-structure / 2026-11-16-r2 -->

## 范围与决策

基线为已合并 PR #16, `19565310d116c2a4fbe763fe4ccd04e07b92c745`. 当前分支 `feat/stop-tail-validation`. 本次只新增共享结构检查, 不改统一契约, 不新增模块依赖或上游版本.

`check_stop_tail_structure(model, start, motion)` 返回统一 Failure 元组. 输入覆盖全车队, 节点有限且时间严格递增. 前缀精确匹配 join_state, 全车队前缀在同一时间结束, 各尾段精确衔接对应前缀, 最终线速度与角速度均为零. 静止单节点尾段有效, 各车可在不同时间停车. 输入不变.

检查集中在 validation 模块, 避免在后续 Runtime 中散落规则. 本函数只检查结构, 不创建第二套 Hermite 插值实现. 前缀不能缺省. 动作, 碰撞, 资源, 制动能力和无限期终点占用必须另行验证. 返回空元组不授权提交, 不实现完整 Validator Protocol.

## 验证与失败记录

TDD: 新接口导入失败, 确认 Red. 实现后 6 项新测试通过. 完整测试 113 项, 112 通过, 1 项可选 CBS-TA 跳过. 失败用例包括漏车, 重复 ID, 未知 ID, 空节点, NaN, 重复时间, 起点跳变, 前缀结束时间不一致, 尾段跳变与非零角终速.

明确反例: 两车尾段停在同一点仍可通过结构检查. 该用例证明结构结果不能作为碰撞安全证据. 这是 fixture 验证, 不是新增真实上游运行证据.

```bash
PYTHONPATH=src:tests /tmp/trajectory-cpp-dev/bin/python -m unittest validation.test_stop_tail -v
PYTHONPATH=src WAREHOUSE_NATIVE_BIN=/tmp/tapf-chain-bridges /tmp/trajectory-cpp-dev/bin/python -m unittest discover -s tests -q
```

## PR 与下一步

历史状态: [PR #17](https://github.com/Requora/TAPF_MAPF_TPG/pull/17) 提交时等待 review, 当时不自行合并. 最新合并状态见下文. 后续连续几何, 制动与停车占用检查仍为计划. 用户本地 .gitignore, helloworld.md 和参考包保持原状.

最终检查: Ruff, git diff --check 和双语网页检查通过. 已检查桌面和手机截图. gpt-6-luna/low 独立双语检查通过. 新接口实际调用: 完整车队返回 `()`, 漏车返回 `BAD_INPUT: stop tail must cover each model robot exactly once`.

私有进展页通过 Sites skill 同步发布成功, 仅所有者访问保持不变. 源码 `8fa1529f4e006e2815275fbe973dd16e7fe0c223`, version `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_7a665c34b5f081919b140f18ecd997ed`. 首次发布辅助程序在主仓库目录失败, 改用独立临时 checkout 后成功; 首次网页检查的 Python 环境缺少 Playwright, 改用已有浏览器环境后通过. 端口 8765 被占用, 本次检查使用 8793. 未验证托管登录, 干净 wheel 安装或完整连续安全.

目标优先级更新: 用户更重视尽快展示端到端运行. 后续开发选择应优先接通最小可运行链路并提供真实轨迹与重放. 连续几何不再作为默认紧接的开发项; 受支持子集, 替身和未验证安全边界必须明确, 现有安全门禁与 PR review 规则保持有效. 本次仅记录偏好, 不启动下一项实现.

合并状态更新: PR #17 已在远端确认合并于 `08da31c442a79fa1d377c7b69cebeb72f992e67a`. 后续执行器工作见 [0018](0018-executor-replay.md).
