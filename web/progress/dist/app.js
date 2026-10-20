const project = window.PROJECT;
let lang = new URLSearchParams(location.search).get("lang") === "en" ? 1 : 0;
let view = "flow";
let selected = "task_compiler";
// 中文: 按当前语言选择成对文案, 让所有界面文字遵循同一语言状态.
// English: Select one bilingual entry using the shared language state.
const text = pair => pair[lang];
// 中文: 通过文案键查找翻译, 集中界面词汇, 避免组件各自保存不同译文.
// English: Resolve a copy key centrally so components share consistent translations.
const copy = key => text(project.copy[key]);
// 中文: 外层函数转义显示值, 内层回调逐字符映射实体, 防止说明文字成为 HTML.
// English: Escape display values with a per-character entity callback so text is not interpreted as HTML.
const escape = value => String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
// 中文: 按当前视图选择边集合, 将目标流程和现有依赖分开呈现, 避免混淆实现状态.
// English: Select edges for the current view so target workflow is distinct from implemented imports.
const edges = () => view === "flow" ? project.flowEdges : project.importEdges;
// 中文: 绘制架构节点, 连接和详情, 集中选择状态的显示, 让用户可追查模块职责与未完成边界.
// English: Render nodes, connections and details from one selection so responsibilities and limits remain traceable.
function renderMap() {
  // 中文: 筛选当前视图应显示的模块, 避免把尚无代码的目标组件画进实际依赖图.
  // English: Filter modules by view so planned components are not shown as existing code dependencies.
  const rows = project.modules.filter(row => view === "flow" || project.importPositions[row[0]]);
  // 中文: 将每条边转换为 SVG并标记当前关联, 明确计划连接, 帮助追踪数据流而不暗示链路全实现.
  // English: Convert edges to SVG with selection and planned-state markers so the diagram does not imply full integration.
  const lines = edges().map(([from, to, label, path, x, y]) => {
    const active = from === selected || to === selected ? "active" : "";
    return `<path class="edge ${view === "flow" && !project.verifiedFlow.includes(from + ":" + to) ? "future" : ""} ${active}" d="${path}" marker-end="url(#arrow)"/><text class="edge-label ${active}" style="display:${view === 'imports' && !active ? 'none' : 'block'}" x="${x}" y="${y}" text-anchor="middle">${escape(label)}</text>`;
  }).join("");
  // 中文: 把模块转成可键盘选择的节点, 同步显示状态与职责, 保证架构图既可读也可操作.
  // English: Render modules as keyboard-selectable nodes with status so the architecture is readable and operable.
  const nodes = rows.map(([id, status, title, api, done, missing, flowX, flowY]) => {
    const [x, y] = view === "flow" ? [flowX, flowY] : project.importPositions[id];
    const state = copy(status) + (project.current.includes(id) ? copy("focusTag") : "");
    return `<g class="node ${id === selected ? "selected" : ""}" data-id="${id}" transform="translate(${x},${y})" role="button" tabindex="0" aria-pressed="${id === selected}" aria-label="${escape(id + ': ' + text(title) + ', ' + state)}"><rect width="250" height="110" rx="14"/><text class="name" x="20" y="32">${id}</text><text class="title" x="20" y="56">${escape(text(title))}</text><text class="status ${status}" x="20" y="87">${escape(state)}</text></g>`;
  }).join("");
  document.querySelector("#map").innerHTML = `<defs><marker id="arrow" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L8 4L0 8" fill="none" stroke="#a68b71"/></marker></defs>${lines}${nodes}`;
  // 中文: 查找当前选中模块的详情, 让说明面板始终对应用户操作的节点.
  // English: Find the selected module so the detail panel always matches the chosen node.
  const [id, status, title, api, done, missing, x, y, path] = project.modules.find(row => row[0] === selected);
  // 中文: 筛选当前模块的入出边并转成列表, 让用户直接看到接口关系, 不必从全图猜测.
  // English: Filter incident edges and render their labels so users can inspect local interfaces without tracing the whole graph.
  const connections = edges().filter(edge => edge[0] === id || edge[1] === id).map(([from, to, label]) => `<li>${escape(from)} → ${escape(to)}<br>${escape(label)}</li>`).join("");
  const source = path.replace("docs/zh/", lang ? "docs/en/" : "docs/zh/");
  document.querySelector("#inspector").innerHTML = `<div><span class="status-tag">${copy(status)}</span><h3>${escape(text(title))}</h3><p>${escape(api)}</p><a href="${project.repo}/blob/${project.branch}/${source}" target="_blank" rel="noreferrer">${copy("source")}</a></div><div><small>${copy("responsibility")}</small><p>${escape(text(done))}</p><small>${copy("missing")}</small><p>${escape(text(missing))}</p></div><div><small>${copy("connections")}</small>${connections ? `<ul>${connections}</ul>` : `<p>${copy("noEdges")}</p>`}</div>`;
}
// 中文: 刷新语言, 状态, 证据和架构显示, 作为交互的统一刷新入口, 防止局部切换留下旧文案.
// English: Refresh language, status, evidence and diagram together so interactions cannot leave stale translated content.
function render() {
  document.documentElement.lang = lang ? "en" : "zh-CN";
  // 中文: 逐个应用翻译键, 使静态页面元素也跟随语言切换, 避免双语混杂.
  // English: Apply translation keys to static elements so language switching does not leave mixed copy.
  document.querySelectorAll("[data-i]").forEach(element => { element.textContent = copy(element.dataset.i); });
  document.querySelector("#language").textContent = lang ? "中文 ↗" : "EN ↗";
  document.querySelector("#mapNote").textContent = copy(view === "flow" ? "flowNote" : "importsNote");
  document.querySelector(".line-key").textContent = view === "flow" ? copy("edges") : text(["实线 = 现有导入", "Solid = existing import"]);
  // 中文: 同步视图按钮的按下状态, 让键盘和辅助技术知道当前显示哪张图.
  // English: Update pressed states so keyboard and assistive users can identify the active diagram.
  document.querySelectorAll("[data-view]").forEach(button => button.setAttribute("aria-pressed", button.dataset.view === view));
  document.querySelector("#stamp").textContent = `${text(["人工同步快照", "Curated snapshot"])} / ${project.date} UTC / ${project.evidenceCommit}`;
  const work = [
    [["NOW / 正在做", "NOW"], ["真实最小链已通过 CI", "Real minimal chain passes CI"], ["PR #9 待 review. 一车一架直线场景中, 六次原生调用得到 2.0/5.2/8.4 s 的动作开始时间, 8.7 s 完成. 原生实现已推送, 远端 CI 构建和 79 项原生测试通过.", "PR #9 awaits review. Six native calls for one robot/shelf on a straight lane produce action starts at 2.0/5.2/8.4 s and completion at 8.7 s. Native code is pushed; remote builds and 79 tests with native binaries pass."]],
    [["NEXT / 待审查", "NEXT / REVIEW"], ["按真实结果审查", "Review the real result"], ["用户已授权本次行数例外. 远端原生 CI 已通过, 等待 review, 不自行合并. 原始输出与可单步重放保留在 CI artifacts.", "The user authorized this line-limit exception. Native CI passed; review is pending, with no automatic merge. Raw output and stepwise replay are retained in CI artifacts."]],
    [["NOT YET / 尚未完成", "NOT YET"], ["通用仓库与执行闭环", "General warehouse & execution loop"], ["多车, 转弯, 障碍, 联合 TAPF, Runtime, 连续几何, 无限期停车和中央执行器未验证或未实现. 当前证据只覆盖受支持子集.", "Multiple robots, turns, obstacles, joint TAPF, Runtime, continuous geometry, indefinite parking, and central execution remain unverified or absent. Evidence covers only the supported subset."]],
  ];
  // 中文: 把状态条目渲染为卡片, 分开当前工作与未实现范围, 防止读者把计划当成果.
  // English: Render status cards that separate current work from missing scope so plans are not mistaken for results.
  document.querySelector("#workItems").innerHTML = work.map(([tag, title, detail]) => `<article><small>${text(tag)}</small><h3>${text(title)}</h3><p>${text(detail)}</p></article>`).join("");
  const locale = lang ? "en" : "zh";
  const evidence = [
    [text(["真实原生 CI · HTML/JSON 重放", "Real native CI · HTML/JSON replay"]), `${project.repo}/actions/runs/39366365034`],
    [text(["当前 PR · 变更与 review", "Current PR · changes & review"]), `${project.repo}/pull/9`],
    [text(["原生实现验证基线", "Native implementation baseline"]), `${project.repo}/commit/${project.evidenceCommit}`],
    [text(["开发日志 · 实际重放与边界", "Development log · replay & limits"]), `${project.repo}/blob/${project.branch}/docs/${locale}/development/0009-staged-pipeline.md`],
    [text(["路线图 · 阶段 1—11", "Roadmap · stages 1–11"]), `${project.repo}/blob/${project.branch}/docs/${locale}/development/ROADMAP.md`],
  ];
  // 中文: 把证据条目渲染成可访问链接, 让每项进展能追溯到代码, CI或日志.
  // English: Render evidence links so progress claims can be traced to code, CI or logs.
  document.querySelector("#evidenceLinks").innerHTML = evidence.map(([label, url]) => `<a href="${url}" target="_blank" rel="noreferrer">${label}<span>↗</span></a>`).join("");
  renderMap();
}
// 中文: 统一处理鼠标和键盘选中模块, 刷新详情后恢复焦点, 保证非鼠标用户也能检查架构.
// English: Handle mouse and keyboard selection and restore focus after rendering so inspection is not mouse-only.
function selectNode(event) {
  const node = event.target.closest("[data-id]");
  if (!node || (event.type === "keydown" && !["Enter", " "].includes(event.key))) return;
  event.preventDefault();
  selected = node.dataset.id;
  renderMap();
  document.querySelector(`[data-id="${selected}"]`).focus({ preventScroll: true });
}
document.querySelector("#map").addEventListener("click", selectNode);
document.querySelector("#map").addEventListener("keydown", selectNode);
// 中文: 切换共享语言并更新 URL, 让当前阅读语言可复制分享, 同步刷新全部内容.
// English: Toggle language and update the URL so the selected reading language can be shared consistently.
document.querySelector("#language").addEventListener("click", () => {
  lang = 1 - lang;
  const url = new URL(location.href);
  url.searchParams.set("lang", lang ? "en" : "zh");
  history.replaceState(null, "", url);
  render();
});
// 中文: 外层为每个视图绑定点击回调, 内层切换图并校正选中节点, 防止依赖图引用不存在的模块.
// English: Bind a click handler per view; each handler switches diagrams and repairs selection if that node is absent.
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => {
  view = button.dataset.view;
  if (view === "imports" && !project.importPositions[selected]) selected = "task_compiler";
  render();
}));
render();
