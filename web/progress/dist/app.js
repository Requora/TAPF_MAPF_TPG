const project = window.PROJECT;
let lang = new URLSearchParams(location.search).get("lang") === "en" ? 1 : 0;
let view = "flow";
let selected = "task_compiler";
const text = pair => pair[lang];
const copy = key => text(project.copy[key]);
const escape = value => String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
const edges = () => view === "flow" ? project.flowEdges : project.importEdges;
function renderMap() {
  const rows = project.modules.filter(row => view === "flow" || project.importPositions[row[0]]);
  const lines = edges().map(([from, to, label, path, x, y]) => {
    const active = from === selected || to === selected ? "active" : "";
    return `<path class="edge ${view === "flow" ? "future" : ""} ${active}" d="${path}" marker-end="url(#arrow)"/><text class="edge-label ${active}" x="${x}" y="${y}" text-anchor="middle">${escape(label)}</text>`;
  }).join("");
  const nodes = rows.map(([id, status, title, api, done, missing, flowX, flowY]) => {
    const [x, y] = view === "flow" ? [flowX, flowY] : project.importPositions[id];
    const state = copy(status) + (project.current.includes(id) ? copy("focusTag") : "");
    return `<g class="node ${id === selected ? "selected" : ""}" data-id="${id}" transform="translate(${x},${y})" role="button" tabindex="0" aria-pressed="${id === selected}" aria-label="${escape(id + ': ' + text(title) + ', ' + state)}"><rect width="250" height="110" rx="14"/><text class="name" x="20" y="32">${id}</text><text class="title" x="20" y="56">${escape(text(title))}</text><text class="status ${status}" x="20" y="87">${escape(state)}</text></g>`;
  }).join("");
  document.querySelector("#map").innerHTML = `<defs><marker id="arrow" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L8 4L0 8" fill="none" stroke="#a68b71"/></marker></defs>${lines}${nodes}`;
  const [id, status, title, api, done, missing, x, y, path] = project.modules.find(row => row[0] === selected);
  const connections = edges().filter(edge => edge[0] === id || edge[1] === id).map(([from, to, label]) => `<li>${escape(from)} → ${escape(to)}<br>${escape(label)}</li>`).join("");
  const source = path.replace("docs/zh/", lang ? "docs/en/" : "docs/zh/");
  document.querySelector("#inspector").innerHTML = `<div><span class="status-tag">${copy(status)}</span><h3>${escape(text(title))}</h3><p>${escape(api)}</p><a href="${project.repo}/blob/${project.branch}/${source}" target="_blank" rel="noreferrer">${copy("source")}</a></div><div><small>${copy("responsibility")}</small><p>${escape(text(done))}</p><small>${copy("missing")}</small><p>${escape(text(missing))}</p></div><div><small>${copy("connections")}</small>${connections ? `<ul>${connections}</ul>` : `<p>${copy("noEdges")}</p>`}</div>`;
}
function render() {
  document.documentElement.lang = lang ? "en" : "zh-CN";
  document.querySelectorAll("[data-i]").forEach(element => { element.textContent = copy(element.dataset.i); });
  document.querySelector("#language").textContent = lang ? "中文 ↗" : "EN ↗";
  document.querySelector("#mapNote").textContent = copy(view === "flow" ? "flowNote" : "importsNote");
  document.querySelector(".line-key").textContent = view === "flow" ? copy("edges") : text(["实线 = 现有导入", "Solid = existing import"]);
  document.querySelectorAll("[data-view]").forEach(button => button.setAttribute("aria-pressed", button.dataset.view === view));
  document.querySelector("#stamp").textContent = `${text(["人工同步快照", "Curated snapshot"])} / ${project.date} UTC / ${project.evidenceCommit}`;
  const work = [
    [["NOW / 正在做", "NOW"], ["模块边界与可观察性", "Boundaries & observability"], ["PR #8 未合并. 明确四个包的职责和公开 API, 加入依赖门禁与导出检查, 建立双语进展网页. 3 条 review 已处理: 1 条修正, 2 条回复证据.", "PR #8 is unmerged. Clarify four packages and public APIs, add import and export checks, and establish this bilingual dashboard. Three findings triaged: one corrected, two answered with evidence."]],
    [["NEXT / 待合并后", "NEXT / AFTER MERGE"], ["库存与需求可行的分配", "Feasible task allocation"], ["确认当前 PR 合并后, 再开始 allocation 的最小增量. 要求输入快照不变, 任务 ID 稳定, 不重复使用可用库存和需求.", "After confirming this PR is merged, start the smallest allocation increment: immutable input snapshots, stable task IDs, and no double use of available stock or demand."]],
    [["NOT YET / 尚未完成", "NOT YET"], ["真正接通执行闭环", "The complete execution loop"], ["MAPF/TPG/TAPF 原生集成, Runtime 事务, 连续几何, 停车验证与中央执行器均未完成. 重分配和多任务队列仍不支持.", "Native MAPF/TPG/TAPF integration, Runtime transactions, continuous geometry, parking validation, and central execution remain unimplemented. Reassignment and multi-task queues remain unsupported."]],
  ];
  document.querySelector("#workItems").innerHTML = work.map(([tag, title, detail]) => `<article><small>${text(tag)}</small><h3>${text(title)}</h3><p>${text(detail)}</p></article>`).join("");
  const locale = lang ? "en" : "zh";
  const evidence = [
    [text(["当前 PR · 变更与 review", "Current PR · changes & review"]), `${project.repo}/pull/8`],
    [text(["已通过 CI · a785121", "Passed CI · a785121"]), `${project.repo}/actions/runs/39355507531`],
    [text(["开发日志 · 实际重放与边界", "Development log · replay & limits"]), `${project.repo}/blob/${project.branch}/docs/${locale}/development/0008-module-boundaries.md`],
    [text(["路线图 · 阶段 1—11", "Roadmap · stages 1–11"]), `${project.repo}/blob/${project.branch}/docs/${locale}/development/ROADMAP.md`],
  ];
  document.querySelector("#evidenceLinks").innerHTML = evidence.map(([label, url]) => `<a href="${url}" target="_blank" rel="noreferrer">${label}<span>↗</span></a>`).join("");
  renderMap();
}
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
document.querySelector("#language").addEventListener("click", () => {
  lang = 1 - lang;
  const url = new URL(location.href);
  url.searchParams.set("lang", lang ? "en" : "zh");
  history.replaceState(null, "", url);
  render();
});
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => {
  view = button.dataset.view;
  if (view === "imports" && !project.importPositions[selected]) selected = "task_compiler";
  render();
}));
render();
