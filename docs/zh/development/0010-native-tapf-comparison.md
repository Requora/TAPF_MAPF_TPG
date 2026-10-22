# 真实目标分配与 CBS-TA 对照

[中文](../../zh/development/0010-native-tapf-comparison.md) | [English](../../en/development/0010-native-tapf-comparison.md)

<!-- doc-sync: native-tapf-comparison / 2026-10-22-r7 -->

## 范围与来源

已确认 PR #9 由用户合并, 远端基线为 `04d4cda44f3ad9a78bed2f53946c5524702239c6`.
本轮分支 `feat/native-tapf-comparison`, 实现验证基线 `b2a3f77`. [PR #10](https://github.com/Requora/TAPF_MAPF_TPG/pull/10) 已提交, 等待 review.
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
桌面和手机重放检查通过: tick 2 的真实会车口位置, 三个面板, 单步按钮, 键盘及无溢出. 进展网页 check.py 检查通过, 两种页面的桌面/手机截图已检查. 干净源码构建的 wheel 在 Python 3.14 隔离模式中通过 86 项测试, pip check 通过. Ruff, JavaScript 语法及 diff 检查通过. [远端 CI 39379639913](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39379639913) 全部通过, 验证 commit 为 `1d2ffe8`. 已下载 [实验 artifact 12244991832](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39379639913/artifacts/12244991832), 核对 4 次成功调用, 固定代价 6/8, 独立选择为 8, 联合为 6. Artifact SHA256: `75cda758e375efeb8ce012ed76dce1ceb67d05ee43ea5363ced02d5995479225`.

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
已发布到同一[私有网页](https://warehouse-planning-observatory.gain-salvo-0t.chatgpt.site), 返回 succeeded. Sites 源码 commit 为 `254ac62db093f3759c91ec331b7843cd2982d725`, version_id 为 `appgprj_6ad6c9324f348191aab84e8bfffe6102~appgver_dfdebc47895881918bb2701928b2379e`. 页面包含 PR #10 和真实实验 CI artifact 链接. 访问范围保持仅所有者; 未运行托管登录浏览器测试. 本仓库 remote 未改变.

目标实验交付时相对 `04d4cda` 的差异: 代码 381 (+361/-20), 文档 293 (+254/-39), 配置 52 (+51/-1). HTML/JS, 测试和注释均计入代码. 本轮无行数例外, 未加入参考包或上游代码. 提交后仅等待 review, 不自行合并或开展后续 PR.

## 自动 review 核对

本轮五条自动意见未发现新缺陷: compare 已在任何调用前拒绝非空目录; 子目录失败保留符合证据隔离约定; mapping 的键和值已限定为 agent0/agent1 与 goal0/goal1; 联合结果不应被强制等于独立分配, 否则本例会拒绝代价 6 的正确方案; Python -I discover 已在远端原生 job 实际通过. 双语复核由 gpt-6-luna / low 执行, 已采纳测试总数表达建议并通过再次复核.

## OpenRouter review 迁移, 2026-10-21

用户要求将自动 review 改走 OpenRouter. 本次在同一 PR #10 修改 review 工作流, 不开启后续规划模块开发.
根据 [OpenRouter 官方接口说明](https://openrouter.ai/docs/quickstart)和实时 [模型列表](https://openrouter.ai/api/v1/models), 使用 `https://openrouter.ai/api/v1` 与 `deepseek/deepseek-v4.1-flash-1017`. PR-Agent 的 LiteLLM 兼容路由为 `openai/deepseek/deepseek-v4.1-flash-1017`; `openai/` 只是协议前缀.
密钥经隐藏输入写入仓库 Actions Secret `OPENROUTER_API_KEY`, 由工作流的 OPENAI_KEY 读取. 密钥未写入仓库或日志. 按用户后续要求改为 `reasoning_effort=medium`. 保持固定 PR-Agent 镜像, 中文行内 review, 无模型 fallback 和原重试策略. 最终模型 token 上限为 81920, 其中输出含推理保留 65536, 输入仍保留 16384; AI 超时为 300 s, 迁移时工作流超时设为 8 min, 后按下节 review 核对恢复为 6 min.
验证先后: LiteLLM 1.105.0 的离线 HTTP 拦截先因请求仍发往 api.deepseek.com 而失败; 修改后确认请求为 `https://openrouter.ai/api/v1/chat/completions`, 实际 model 为 `deepseek/deepseek-v4.1-flash-1017`, reasoning_effort 为 medium, 最终 max_tokens 为 65536. 先前 reasoning_effort=none 的真实 OpenRouter 小请求返回 OK, finish_reason=stop; 首次 medium 完整 [run 39544133063](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39544133063) 在原 16384 输出预算下返回空正文和 finish_reason=length. 依据 [OpenRouter 推理预算说明](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens), 增加输出预算并保留 medium, 不降低推理强度; 新预算的 [run 39544399291](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39544399291) 已在 `a822172` 成功完成, 日志确认 reasoning_effort=medium, 并发布 4 条行内意见和[中文摘要](https://github.com/Requora/TAPF_MAPF_TPG/pull/10#issuecomment-6284755464). 实际模型用时 60.6 s, 输入 16121 token, 输出 13317 token. 输入预算限制仍会裁剪部分 diff, 本次成功不表示覆盖全部 PR 文件. YAML 与 diff 检查通过. 未增加只复述配置的永久测试.
本次改变审查服务路由和推理强度; 规划 API, 原生实验和架构证据不变. 工作区已有的 .gitignore 修改和 helloworld.md 未纳入提交. [同一提交的 CI](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39544399105) 全部通过. 上述运行证据固定于 `a822172`; 后续提交仅补充文档证据.

## PR 评论复核, 2026-10-22

[人工评论](https://github.com/Requora/TAPF_MAPF_TPG/pull/10#discussion_r4333078654)询问为何将 job 超时从 6 min 改为 8 min. 原因只是给 300 s 模型请求和周边操作增加余量, 不是修复已观察到的超时. 两次成功 job 耗时分别为 108 s 和 117 s; [最新运行](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39544812671)及同一提交的 [CI](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39544812778)均通过. 因没有证据需要扩大 job 上限, 本次恢复为 6 min. OpenRouter, medium, 65536 输出预算和 300 s AI 超时保持不变. 6 min 是整个 job 的硬上限, 周边操作也占用该预算, 不保证模型总能用满 300 s.
五条机器人意见仍不需要修改算法: 非空目录在 compare 入口被拒绝; 失败目录保留证据; 目标名已经限定, 两种分配均被枚举; 联合结果必须允许改变独立分配; 隔离模式的测试发现可成功导入. 本次再次执行 `WAREHOUSE_TAPF_BIN=/tmp/warehouse-tapf-pinned /tmp/warehouse-tapf-wheel-venv/bin/python -I -m unittest discover -s tests -p test_comparison.py -v`, 6 项全部通过, 包含真实上游调用. 首次误将 wheel 安装目录当作虚拟环境导致命令未启动, 更正为已有虚拟环境后通过. YAML 和 diff 检查通过; [恢复 6 min 后的 CI](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39852122416)通过, 但 [review 39852122481](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39852122481)被取消. GitHub annotation 明确为 job 超过 6 min; 最后模型请求日志为 20:50:00 UTC, 取消为 20:55:46 UTC, 未记录模型返回. 因此此前两次快速成功不能证明 6 min 对所有请求足够, 300 s AI 配置也未在本次提供可观察的请求终止. 保留 6 min 作为总运行上限, 如实记录审查未完成, 不宣称本次 review 验证通过或 8 min 必定成功.
本次只调整配置 1 行并同步双语日志, 不改变规划模块, 实验结论或进展网页. 6 条评论已分别回复核对依据, [超时回复](https://github.com/Requora/TAPF_MAPF_TPG/pull/10#discussion_r4353378181)已补充本次取消结果. 未关闭审查线程或合并 PR.

## High 推理配置, 2026-10-22

用户要求 review 使用 high. 工作流将 `CONFIG.REASONING_EFFORT` 从 medium 改为 high, 并同步双语预算注释. 保留 OpenRouter, DeepSeek V4.1 Flash1017, 65536 输出预算, 16384 输入预算, 300 s AI 超时和 6 min job 上限.
本次读取 [OpenRouter 模型列表](https://openrouter.ai/api/v1/models), 该模型列出的 supported_efforts 为 max/high/low/none, 未列 medium. 之前仅验证参数传出, 不能证明模型原生支持 medium. [最新 medium review](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39853238713)记录约 322 s 后返回空正文和 finish_reason=length, 并触及 job 上限; [同提交 CI](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39853238750)通过. 不将推理档位不匹配认定为已证明的空输出根因, 也不保证改成 high 就不会耗尽输出或超时.
离线 HTTP 拦截先要求 high 并因实际 medium 失败, 修改后确认真实客户端发往 OpenRouter 的请求为 reasoning_effort=high, 模型和 max_tokens=65536 不变. YAML 和 diff 检查通过, 无业务代码修改. 远端 review 与 CI 在推送后运行, 结果记录于 PR 说明, 不以离线请求验证代替服务实际成功. 双语日志同步, 进展网页和规划架构不变.

## Review 输入预算与超时修正, 2026-10-22

[high review 39855330148](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39855330148)在 6 min job 上限下被取消. 最后模型调用日志为 21:13:04 UTC, 取消为 21:18:52 UTC, 没有模型返回记录. [同提交 CI](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39855329923)通过. 这是 high 已触及时间上限的实际证据, 因此本次将 job 上限改为 8 min, 而非沿用之前没有超时证据时的推测. AI_TIMEOUT=300 不等同于已验证的整个请求墙钟硬截止; job 仍提供总运行上限.
该运行记录输入约 37706 token, 但 81920 总预算扣除 65536 输出预留后只有 16384 输入空间, 导致 diff 被裁剪. 本次同时将 CUSTOM_MODEL_MAX_TOKENS 和 MAX_MODEL_TOKENS 改为 131072, 输出预留仍为 65536, 输入空间增至 65536. 模型目录公布的上下文为 1048576, 本地预算未超出该上限. high, 模型, 路由, 密钥映射, 300 s AI 设置和无重试策略不变. 输入空间增大可能增加单次费用和延迟; 本次保留有界预算, 不保证任意 PR 全部装入.
可选 .secrets.toml 缺失无需创建密钥文件. Actions token 查询 /user 的 403 在上游代码中回退为 github-actions[bot], 无需增加权限或使用个人 token. 本次不修改或屏蔽上游警告.
预算复现先因 16384 无法容纳已观察的 37706 加 4096 余量而失败; 修改后 65536 可容纳相同输入. 实际客户端 HTTP 拦截确认 high, OpenRouter 和 max_tokens=65536 不变; YAML 与 diff 检查通过. 这只验证预算与请求参数, 不等同于服务审查成功. 推送后的真实 diff 覆盖和模型结果记录于 PR 说明. 本次没有业务代码或网页变更, 双语日志同步.

## 输出上限与时间估算, 2026-10-22

[预算修正后的 review 39856505842](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39856505842)确认 `Tokens: 38758` 且 `returning full diff`, 因此该提交的 diff 裁剪问题已验证消除. 但模型调用从 21:21:38 到 21:27:32 后返回空正文和 finish_reason=length, 审查失败, 不再只是 job 超时. 用户随后明确要求继续增大输出上限并据此计算时间.
用户提供 generation ID `gen-1792703584-tN4b4ljB9eB9KKym0mMO`. 经 [OpenRouter generation API](https://openrouter.ai/docs/api/api-reference/generations/get-request-&-usage-metadata-for-a-generation)查询, 这是 21:13:04 UTC 的前一次 high 请求: provider=InferenceNet, generation_time=362093 ms, native_tokens_completion=51685, native_tokens_reasoning=51685, cancelled=true, 上游状态 499, finish_reason=null. 该记录不是 39856505842 的请求. 全部已生成 token 均计为推理, 未产生正文; 这与客户端取消相符, 不将 499 解读为模型供应商主动故障.
实测平均速度为 `51685 / 362.093 = 142.74 token/s`. 新输出上限为 131072, 同速跑满约 `131072 / 142.74 = 918.26 s = 15.30 min`. 增加 25% 余量后约 1147.82 s, 向上取整为 1200 s AI 超时. job 再留 2 min 启动和发布余量, 因此设为 22 min. 这是单次中途取消请求的速度估算, 不是服务 SLA 或模型必定完成的保证; 实际速度, 首 token 延迟, 路由和输入处理时间会变化, AI 超时也不被宣称为整个流式请求的墙钟硬截止.
工作流将 MAX_OUTPUT_TOKENS 改为 131072, CUSTOM_MODEL_MAX_TOKENS 和 MAX_MODEL_TOKENS 同步改为 196608, 为输入保留 65536. high, 模型, OpenRouter, 密钥和无重试策略不变. 新预算不保证正文一定出现. 密钥仅通过隐藏输入用于本次只读查询, 未写入仓库或日志; 原始账户元数据未提交.
离线客户端检查先因 max_tokens 仍为 65536 失败, 修改后确认发送 high 和 max_tokens=131072; 预算检查确认输入仍为 65536 且时间公式得到 AI=1200 s/job=22 min. YAML 与 diff 检查通过. 远端结果在推送后记录于 PR 说明, 不以参数验证代替真实审查成功. 本次仅修改配置及双语日志, 不改业务代码或网页.

## CI 软件源修正, 2026-10-22

用户要求将原生集成任务换源. [旧 CI 39856505754](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39856505754)记录 Azure 源下载 25.3 MB 用时 9 min 32 s, 另一个 job 下载 26.6 MB 用时 9 min 24 s. [后续 CI 39857834152](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39857834152)中 TAPF job 被取消, CI gate 失败; Python, 静态检查和另一个原生 job 通过. 这不是 review 仍在等待: [review 39857834193](https://github.com/Requora/TAPF_MAPF_TPG/actions/runs/39857834193)已在 118 s 内成功, 确认 high 和完整 diff, 模型用时 75.9 s, 输入 40250/输出 5684 token, 发布 5 条行内意见.
两个原生 job 固定使用 ubuntu-24.04, 与上述日志实际运行系统相同. 依据 [runner 官方软件源配置](https://github.com/actions/runner-images/blob/main/images/ubuntu/scripts/build/configure-apt-sources.sh), 在临时 runner 中重写 /etc/apt/apt-mirrors.txt, 使用 https://archive.ubuntu.com/ubuntu/ 为首选, https://security.ubuntu.com/ubuntu/ 为备用, 移除 Azure 下载源. 包列表, APT 签名验证, 原生构建, 测试和门禁保持不变. 不改本机软件源, 不加入自动测速或缓存实现.
YAML 解析, 两个安装步骤的 bash 语法和实际 printf 输出检查通过, diff 检查通过. 镜像速度依赖运行网络, 本机下载探测不能证明 GitHub runner 会更快; 换源后的安装耗时和完整 CI 结果以推送后的真实运行及 PR 说明为准. 本次仅修改工作流配置和双语日志, 不改规划架构或网页.
