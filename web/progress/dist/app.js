const project = window.PROJECT;
let lang = new URLSearchParams(location.search).get("lang") === "en" ? 1 : 0;
let view = "flow";
let selected = "task_compiler";
// 中文: text 从一对中英文文字中取出当前语言的内容, 让各个界面组件使用同一个语言设置.
// English: text selects the current language from a Chinese/English pair so all components share one language setting.
const text = pair => pair[lang];
// 中文: copy 按 key(文字条目的名称)查找当前语言的译文, 让组件复用同一份翻译而不会各自使用不同说法.
// English: copy looks up the current translation by key, the text entry's name, so components reuse consistent wording.
const copy = key => text(project.copy[key]);
// 中文: escape 将显示值转为字符串; replace 的回调把特殊字符换成 HTML 实体, 即表示字符本身的编码.
// 浏览器因此把这些字符显示为文字, 而不会将说明内容解释为页面标签.
// English: escape converts a display value to a string; its replace callback encodes special characters as HTML entities.
// These encodings make the browser display the characters as text instead of interpreting them as page markup.
const escape = value => String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
// 中文: edges 根据当前视图返回模块间的连接列表. 流程图的连接表示业务数据流, 依赖图的连接表示代码导入.
// 这个函数分开选择两种连接, 避免界面把计划中的业务联系误画成已经存在的代码依赖.
// English: edges selects module connections for the current view: business data flow or code imports.
// The function keeps these lists separate so planned workflow links are not shown as existing code dependencies.
const edges = () => view === "flow" ? project.flowEdges : project.importEdges;
// 中文: renderMap 根据当前选中的模块绘制架构图和详情面板, 让用户同时检查模块职责, 连接和未完成项.
// 图中的节点代表软件模块, 连线代表模块之间的关系; 这张图不表示机器人运动路线.
// English: renderMap draws the architecture and detail panel for the selected module so users can inspect its role, links and limits.
// Diagram nodes represent software modules and lines represent their relationships; this diagram is not a robot route.
function renderMap() {
  // 中文: filter 的回调决定每个模块是否出现在当前图中, 避免依赖图把尚无代码的计划组件当成现有模块.
  // English: The filter callback selects modules for the current diagram so the import view excludes planned components without code.
  const rows = project.modules.filter(row => view === "flow" || project.importPositions[row[0]]);
  // 中文: map 的回调把每条模块连接转换成 SVG(浏览器中的矢量图形)线条和标签, 并标记相关模块及计划连接.
  // 这些标记让用户能沿连接检查数据流, 而不会把尚未验证的连接误认为已经接通.
  // English: The map callback converts each module connection into SVG vector lines and labels, marking selected and planned links.
  // These marks let users follow the data flow without mistaking unverified connections for completed integration.
  const lines = edges().map(([from, to, label, path, x, y]) => {
    const active = from === selected || to === selected ? "active" : "";
    return `<path class="edge ${view === "flow" && !project.verifiedFlow.includes(from + ":" + to) ? "future" : ""} ${active}" d="${path}" marker-end="url(#arrow)"/><text class="edge-label ${active}" style="display:${view === 'imports' && !active ? 'none' : 'block'}" x="${x}" y="${y}" text-anchor="middle">${escape(label)}</text>`;
  }).join("");
  // 中文: map 的回调为每个模块生成可用键盘选择的图形节点, 并显示模块名称和状态, 让用户能阅读和操作架构图.
  // English: The map callback creates a keyboard-selectable diagram node with each module's name and status so users can read and operate it.
  const nodes = rows.map(([id, status, title, api, done, missing, flowX, flowY]) => {
    const [x, y] = view === "flow" ? [flowX, flowY] : project.importPositions[id];
    const state = copy(status) + (project.current.includes(id) ? copy("focusTag") : "");
    return `<g class="node ${id === selected ? "selected" : ""}" data-id="${id}" transform="translate(${x},${y})" role="button" tabindex="0" aria-pressed="${id === selected}" aria-label="${escape(id + ': ' + text(title) + ', ' + state)}"><rect width="250" height="110" rx="14"/><text class="name" x="20" y="32">${id}</text><text class="title" x="20" y="56">${escape(text(title))}</text><text class="status ${status}" x="20" y="87">${escape(state)}</text></g>`;
  }).join("");
  document.querySelector("#map").innerHTML = `<defs><marker id="arrow" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L8 4L0 8" fill="none" stroke="#a68b71"/></marker></defs>${lines}${nodes}`;
  // 中文: find 的回调将每个模块 ID 与 selected 比较, 让详情面板使用用户当前选中的模块记录.
  // English: The find callback compares each module ID with selected so the detail panel uses the user's chosen module record.
  const [id, status, title, api, done, missing, x, y, path] = project.modules.find(row => row[0] === selected);
  // 中文: filter 的回调选出起点或终点为当前模块的连接, map 的回调再将连接生成列表项.
  // 这个列表让用户直接检查当前模块与其他模块的接口关系, 不必在完整架构图中逐条寻找.
  // English: The filter callback selects connections that start or end at this module, and the map callback turns them into list items.
  // This list lets users inspect the module's interfaces without tracing every connection in the full diagram.
  const connections = edges().filter(edge => edge[0] === id || edge[1] === id).map(([from, to, label]) => `<li>${escape(from)} → ${escape(to)}<br>${escape(label)}</li>`).join("");
  const source = path.replace("docs/zh/", lang ? "docs/en/" : "docs/zh/");
  document.querySelector("#inspector").innerHTML = `<div><span class="status-tag">${copy(status)}</span><h3>${escape(text(title))}</h3><p>${escape(api)}</p><a href="${project.repo}/blob/${project.branch}/${source}" target="_blank" rel="noreferrer">${copy("source")}</a></div><div><small>${copy("responsibility")}</small><p>${escape(text(done))}</p><small>${copy("missing")}</small><p>${escape(text(missing))}</p></div><div><small>${copy("connections")}</small>${connections ? `<ul>${connections}</ul>` : `<p>${copy("noEdges")}</p>`}</div>`;
}
// 中文: render 统一刷新页面语言, 状态卡片, 验证证据链接和架构图, 防止用户切换选项后仍看到部分旧内容.
// English: render refreshes language, status cards, verification links and the diagram together so option changes do not leave stale content.
function render() {
  document.documentElement.lang = lang ? "en" : "zh-CN";
  // 中文: forEach 的回调读取每个元素 data-i 属性中的文字条目名称, 再填入当前译文, 避免语言切换后页面混用两种语言.
  // English: The forEach callback reads each element's text-entry name from data-i and applies its translation to avoid mixed languages.
  document.querySelectorAll("[data-i]").forEach(element => { element.textContent = copy(element.dataset.i); });
  document.querySelector("#language").textContent = lang ? "中文 ↗" : "EN ↗";
  document.querySelector("#mapNote").textContent = copy(view === "flow" ? "flowNote" : "importsNote");
  document.querySelector(".line-key").textContent = view === "flow" ? copy("edges") : text(["实线 = 现有导入", "Solid = existing import"]);
  // 中文: forEach 的回调更新每个视图按钮的 aria-pressed 状态, 即辅助工具读取的选中标记, 让用户知道当前显示哪张图.
  // English: The forEach callback updates each view button's aria-pressed selection state so assistive tools can identify the current diagram.
  document.querySelectorAll("[data-view]").forEach(button => button.setAttribute("aria-pressed", button.dataset.view === view));
  document.querySelector("#stamp").textContent = `${text(["人工同步快照", "Curated snapshot"])} / ${project.date} UTC / ${project.evidenceCommit}`;
  const work = [
    [["NOW / 正在做", "NOW"], ["修复自动审查调用链", "Repair automated review transport"], ["两次 Ionstream 502 共等待 62 分钟且无正文. 新传输层单次调用, 总时限 10 min, 保留供应商错误与用量元数据.", "Two Ionstream 502 failures consumed 62 minutes without visible output. The new transport allows one attempt, a 10-minute deadline and provider error/usage metadata."]],
    [["NEXT / 待审查", "NEXT / REVIEW"], ["验证真实 review", "Verify a real review"], ["PR #14/#15 已各单次完成真实审查并发布意见, 费用约 $0.00833 / $0.0437. 七项本地测试通过; 隔离后的发布 job 待验证. 此图展示已合并业务基线, PR #14 C++ 轨迹仍独立待审查.", "PR #14/#15 each completed and published a real review in one attempt, costing about $0.00833 / $0.0437. Seven local tests pass; the isolated publishing job awaits verification. This diagram shows the merged application baseline; PR #14 C++ trajectory remains separately under review."]],
    [["NOT YET / 尚未完成", "NOT YET"], ["联合仓库与执行闭环", "Joint warehouse & execution loop"], ["目标实验未接 SKU, Lift/Serve/Drop, 共享编译或 TPG. 多车仓库, Runtime, 连续几何, 无限期停车和中央执行器仍未完成.", "The goal experiment has no SKU, Lift/Serve/Drop, shared compiler or TPG connection. Multi-robot warehouse planning, Runtime, continuous geometry, indefinite parking and execution remain incomplete."]],
  ];
  // 中文: map 的回调把每个工作状态条目转换为卡片, 分开显示当前工作和未实现项, 防止读者把计划当成已完成成果.
  // English: The map callback converts each work-status entry into a card, separating current work from missing scope so plans are not mistaken for results.
  document.querySelector("#workItems").innerHTML = work.map(([tag, title, detail]) => `<article><small>${text(tag)}</small><h3>${text(title)}</h3><p>${text(detail)}</p></article>`).join("");
  const locale = lang ? "en" : "zh";
  const evidence = [
    [text(["当前 PR #15 · 审查传输层", "Current PR #15 · review transport"]), `${project.repo}/pull/15`],
    [text(["待审查 PR #14 · C++ 轨迹", "Pending PR #14 · C++ trajectory"]), `${project.repo}/pull/14`],
    [text(["已合并 PR #13 · 运动结果边界", "Merged PR #13 · motion-result boundary"]), `${project.repo}/pull/13`],
    [text(["真实目标实验 CI · 下载单步重放", "Real goal experiment CI · download replay"]), `${project.repo}/actions/runs/39379639913/artifacts/12244991832`],
    [text(["真实原生 CI · HTML/JSON 重放", "Real native CI · HTML/JSON replay"]), `${project.repo}/actions/runs/39366365034`],
    [text(["已合并 PR #12 · 组合测试", "Merged PR #12 · composition tests"]), `${project.repo}/pull/12`],
    [text(["已合并 PR #11 · 路径约束", "Merged PR #11 · path contract"]), `${project.repo}/pull/11`],
    [text(["已合并 PR #10 · 实验证据", "Merged PR #10 · experiment evidence"]), `${project.repo}/pull/10`],
    [text(["已合并验证基线", "Merged verification baseline"]), `${project.repo}/commit/${project.evidenceCommit}`],
    [text(["开发日志 · 实际重放与边界", "Development log · replay & limits"]), `${project.repo}/blob/${project.branch}/docs/${locale}/development/0015-review-transport.md`],
    [text(["路线图 · 阶段 1—11", "Roadmap · stages 1–11"]), `${project.repo}/blob/${project.branch}/docs/${locale}/development/ROADMAP.md`],
  ];
  // 中文: map 的回调把每条验证证据转换成链接, 让用户能从页面追查代码, 自动构建与测试记录(CI), 或开发日志.
  // English: The map callback turns each verification entry into a link to code, automated build/test records (CI), or development logs.
  document.querySelector("#evidenceLinks").innerHTML = evidence.map(([label, url]) => `<a href="${url}" target="_blank" rel="noreferrer">${label}<span>↗</span></a>`).join("");
  renderMap();
}
// 中文: selectNode 根据鼠标点击或键盘事件选择模块, 并在刷新详情后恢复键盘焦点, 让不用鼠标的用户也能检查架构.
// English: selectNode handles mouse or keyboard module selection and restores keyboard focus after rendering so inspection does not require a mouse.
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
// 中文: 语言按钮的点击回调切换页面语言, 将语言选择写入网址参数并刷新页面内容, 让复制的网址保留当前阅读语言.
// English: The language button's click callback switches language, updates the URL parameter and refreshes content so copied links retain the choice.
document.querySelector("#language").addEventListener("click", () => {
  lang = 1 - lang;
  const url = new URL(location.href);
  url.searchParams.set("lang", lang ? "en" : "zh");
  history.replaceState(null, "", url);
  render();
});
// 中文: forEach 的回调为每个视图按钮注册点击回调; 点击回调切换架构图, 并在新图没有原选中模块时选择任务编译器.
// 这项检查让详情面板始终对应当前图中存在的模块.
// English: The forEach callback registers a click callback for each view button; each click switches diagrams and selects
// the task compiler if the previous selection is absent. This check keeps the detail panel tied to a module in the current diagram.
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => {
  view = button.dataset.view;
  if (view === "imports" && !project.importPositions[selected]) selected = "task_compiler";
  render();
}));
render();
