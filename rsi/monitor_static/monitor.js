"use strict";
const $ = (id) => document.getElementById(id);
let lastSnapshot = null;
let selectedKey = null;

function percent(value) { return typeof value === "number" ? `${Math.round(value * 100)}%` : "—"; }
function element(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = String(value);
  return node;
}
function renderDecision(decision, snapshot) {
  const context = decision?.context || {};
  $("run-id").textContent = snapshot.game_run_id || context.run_id || "—";
  $("position").textContent = `${context.floor ?? "—"} / ${context.turn ?? "—"}`;
  $("hp").textContent = context.is_victory ? "胜利" : context.hp == null ? "—" : `${context.hp}${context.max_hp == null ? "" : "/" + context.max_hp}`;
  const source = decision?.source || "等待决策";
  $("source").textContent = source;
  $("source").className = `source ${source.startsWith("Astra") ? "astra" : source === "Jev" ? "" : "auto"}`;
  const states = {proposed:"待执行",accepted:"已执行",rejected:"被拒绝",discarded:"状态已过期",delivery_unknown:"交付待确认",awaiting_astra:"等待 Astra",result_received:"收到结果"};
  $("state").textContent = states[decision?.state] || "—";
  $("action").textContent = decision?.label || "等待 trace…";
  $("screen").textContent = decision ? `${context.screen || "未知场景"}${decision.model ? " · " + decision.model : ""}${decision.reason ? " · " + decision.reason : ""}` : "窗口只读取本地记录，不控制游戏。";
  $("confidence").textContent = percent(decision?.confidence);
  $("confidence-fill").style.width = decision?.confidence == null ? "0%" : percent(decision.confidence);
  $("option-count").textContent = decision ? `${decision.option_count || 0} 个` : "—";
  const container = $("options"); container.replaceChildren();
  if (!decision?.options?.length) container.append(element("p", "empty", "本次没有候选分布记录"));
  else for (const option of decision.options) {
    const row = element("div", `option${option.selected ? " selected" : ""}`);
    const top = element("div", "option-top");
    top.append(element("span", "option-label", option.label), element("span", "option-prob", percent(option.probability)));
    row.append(top);
    if (option.probability != null) {
      const meter = element("div", "prob-meter"), fill = element("span");
      fill.style.width = percent(option.probability); meter.append(fill); row.append(meter);
    }
    container.append(row);
  }
  const plan = decision?.plan || snapshot.plan;
  $("plan-section").hidden = !plan;
  if (plan) {
    $("plan-scope").textContent = `${plan.kind === "room_plan" ? "房间" : "楼层"} ${plan.floor ?? ""}`;
    $("plan-text").textContent = plan.guidance || "—";
  }
}
function render(snapshot) {
  lastSnapshot = snapshot;
  $("mode").textContent = snapshot.mode === "replay" ? "TRACE 回放" : snapshot.last_time && Date.now() / 1000 - snapshot.last_time > 60 ? "等待新决策" : "LIVE · 只读";
  $("connection").textContent = snapshot.error || (snapshot.mode === "replay" ? `回放 ${snapshot.replay_progress?.join(" / ") || "—"}` : `状态：${snapshot.status}`);
  $("segment").textContent = snapshot.segment || "无 trace";
  const history = snapshot.history || [];
  if (selectedKey != null && !history.some(item => item.key === selectedKey)) selectedKey = null;
  const decision = selectedKey == null ? (snapshot.current || snapshot.latest) : history.find(item => item.key === selectedKey);
  renderDecision(decision, snapshot);
  $("live-button").hidden = selectedKey == null;
  const container = $("history"); container.replaceChildren();
  for (const item of history) {
    const button = element("button", item.key === selectedKey ? "active" : "");
    button.type = "button";
    button.append(element("span", "", `#${item.seq ?? "—"}`), element("span", "", `${item.source}: ${item.label}`));
    button.addEventListener("click", () => { selectedKey = item.key; render(lastSnapshot); });
    container.append(button);
  }
}
$("live-button").addEventListener("click", () => { selectedKey = null; render(lastSnapshot); });
async function poll() {
  try {
    const response = await fetch("/api/state", {cache:"no-store"});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch (error) { $("connection").textContent = `连接失败：${error.message}`; }
}
poll(); setInterval(poll, 500);
