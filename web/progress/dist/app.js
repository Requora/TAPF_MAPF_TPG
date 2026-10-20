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
    [["NOW / 正在做", "NOW"], ["分阶段组合入口", "Staged composition"], ["基线 PR #8 已合并. 当前 PR #9 新增 StagedPipeline 与 JSON 重放. 订单源和编译器为真实实现; 分配, MAPF, TPG 为明确标注的 fixture 替身. 本 PR 待 review.", "Baseline PR #8 merged. Current PR #9 adds StagedPipeline and JSON replay. Order source and compiler are real implementations; allocation, MAPF, and TPG are labeled fixture doubles. This PR awaits review."]],
    [["NEXT / 待合并后", "NEXT / AFTER MERGE"], ["替换 fixture, 跑通原生链路", "Replace fixtures with native stages"], ["确认本 PR 合并后, 接入可行分配与固定版本 MAPF/TPG 适配器. 保留同一组合入口与逐阶段失败证据. 不提前开发后续 PR.", "After this PR merges, integrate feasible allocation and pinned MAPF/TPG adapters. Retain this composition entry point and stage failure evidence. Do not start later PRs early."]],
    [["NOT YET / 尚未完成", "NOT YET"], ["真实链路与执行闭环", "Native chain and execution loop"], ["真实订单到 TPG 链路尚未跑通. Runtime, 连续几何, 停车验证与中央执行器均未完成. 两个上游已本地构建; 构建成功不等于适配器集成.", "The native order-to-TPG chain is not running. Runtime, continuous geometry, parking validation, and central execution remain absent. Both upstreams built locally; builds do not prove adapter integration."]],
  ];
  document.querySelector("#workItems").innerHTML = work.map(([tag, title, detail]) => `<article><small>${text(tag)}</small><h3>${text(title)}</h3><p>${text(detail)}</p></article>`).join("");
  const locale = lang ? "en" : "zh";
  const evidence = [
    [text(["当前 PR · 变更与 review", "Current PR · changes & review"]), `${project.repo}/pull/9`],
    [text(["验证基线 · 4277591", "Validation baseline · 4277591"]), `${project.repo}/commit/4277591`],
    [text(["开发日志 · 实际重放与边界", "Development log · replay & limits"]), `${project.repo}/blob/${project.branch}/docs/${locale}/development/0009-staged-pipeline.md`],
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
