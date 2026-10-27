/* Vanilla JS. Remote strings are rendered with textContent, never HTML. */
"use strict";
const $ = (id) => document.getElementById(id);
const apiBase = (window.APP_CONFIG?.API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const state = { market: "KRW-BTC", markets: [], records: [], summary: null, conversations: [],
  messages: [], conversationId: null, editingId: null, visibleRows: 20, busy: false, refreshId: 0 };
let clientId;
try {
  clientId = localStorage.getItem("coincontext-client");
  if (!/^[a-f0-9-]{36}$/.test(clientId || "")) {
    clientId = crypto.randomUUID();
    localStorage.setItem("coincontext-client", clientId);
  }
} catch { clientId = crypto.randomUUID(); }

const number = (value, digits = 0) => value == null ? "—" : Number(value).toLocaleString("ko-KR", { maximumFractionDigits: digits });
const price = (value) => value == null ? "—" : `${number(value, value < 100 ? 4 : 0)}원`;
const shortDate = (value) => value ? new Date(value).toLocaleString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
const element = (tag, className, text) => {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text != null) item.textContent = text;
  return item;
};

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90000);
  try {
    const response = await fetch(apiBase + path, {
      ...options, signal: controller.signal,
      headers: { "Content-Type": "application/json", "X-Client-Id": clientId, ...options.headers },
    });
    if (response.status === 204) return null;
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = body.detail;
      throw new Error(Array.isArray(detail) ? detail.map((error) => `${error.loc.at(-1)}: ${error.msg}`).join(" / ")
        : detail || `요청을 처리하지 못했습니다 (${response.status}).`);
    }
    return body;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("응답 시간이 길어지고 있습니다. 잠시 후 새로고침해 저장 결과를 확인하세요.");
    if (error instanceof TypeError) throw new Error("서버에 연결할 수 없습니다. 서버 주소·실행 상태·CORS 설정을 확인하세요. 첫 접속은 잠시 걸릴 수 있습니다.");
    throw error;
  } finally { clearTimeout(timeout); }
}

function feedback(message, success = false) {
  $("feedback").textContent = message;
  $("feedback").classList.toggle("success", success);
  $("feedback").hidden = false;
}
function clearFeedback() { $("feedback").hidden = true; }
function confirmDelete(message) {
  const dialog = $("delete-dialog");
  $("delete-description").textContent = message;
  dialog.returnValue = "cancel";
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "delete"), { once: true });
    dialog.showModal();
  });
}
function setBusy(value) {
  state.busy = value;
  for (const id of ["import", "refresh", "market", "market-search", "send", "new-chat", "save-record", "add-record"]) $(id).disabled = value;
  for (const button of document.querySelectorAll("[data-mutation], [data-conversation]")) button.disabled = value;
  $("chat-form").setAttribute("aria-busy", String(value));
}
async function action(fn) {
  if (state.busy) return;
  clearFeedback();
  setBusy(true);
  try { await fn(); } catch (error) { feedback(error.message); } finally { setBusy(false); }
}
function setView(view) {
  for (const name of ["analysis", "data", "history"]) $(`${name}-view`).hidden = name !== view;
  const labels = { analysis: "분석 & AI 대화", data: "데이터 관리", history: "대화 기록" };
  $("view-label").textContent = labels[view];
  for (const button of document.querySelectorAll("[data-view]")) {
    const active = button.dataset.view === view;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
  }
}
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));

function renderMarkets(filter = "") {
  const query = filter.trim().toLowerCase();
  const markets = state.markets.filter((row) => row.market === state.market ||
    `${row.market} ${row.korean_name} ${row.english_name}`.toLowerCase().includes(query));
  if (!markets.some((row) => row.market === state.market)) markets.unshift({ market: state.market, korean_name: state.market });
  $("market").replaceChildren(...markets.map((row) => {
    const option = element("option", "", `${row.korean_name} · ${row.market.replace("KRW-", "")} / KRW`);
    option.value = row.market;
    return option;
  }));
  $("market").value = state.market;
}
$("market-search").addEventListener("input", (event) => renderMarkets(event.target.value));

function renderSummary() {
  const summary = state.summary;
  const metrics = summary?.metrics || {};
  $("metric-latest").textContent = price(metrics.latest);
  $("metric-average").textContent = price(metrics.average);
  $("metric-date").textContent = summary?.period ? `${summary.period.end} · 완료 일봉` : "완료된 일봉 기준";
  $("metric-period").textContent = summary?.period ? `${summary.period.start} — ${summary.period.end}` : "저장된 전체 기간";
  const trend = summary?.trend || {};
  const names = { increase: "상승", decrease: "하락", stable: "유지", insufficient_data: "데이터 부족" };
  $("metric-trend").textContent = trend.change_pct == null ? "—" : `${trend.change_pct > 0 ? "+" : ""}${number(trend.change_pct, 2)}%`;
  $("metric-trend").classList.toggle("positive", trend.direction === "increase");
  $("metric-trend").classList.toggle("negative", trend.direction === "decrease");
  $("metric-trend").title = names[trend.direction] || "";
  $("metric-count").replaceChildren(document.createTextNode(`${number(summary?.count || 0)} `), element("small", "", "개"));
  $("metric-coverage").textContent = summary?.count >= 100 ? "100개 이상 데이터 준비 완료" : "최소 100개 데이터 권장";
  $("context-market").textContent = state.market;
  $("context-max").textContent = price(metrics.max);
  $("context-min").textContent = price(metrics.min);
  $("coin-avatar").textContent = state.market === "KRW-BTC" ? "₿" : state.market.replace("KRW-", "").slice(0, 2);
  const indicators = summary?.latest_indicators || {};
  for (const [key, id] of [["bb_upper", "bb-upper"], ["bb_middle", "bb-middle"], ["bb_lower", "bb-lower"]]) $(id).textContent = price(indicators[key]);
  $("rsi").textContent = number(indicators.rsi, 2);
  $("rsi-meter").hidden = indicators.rsi == null;
  $("rsi-meter").value = indicators.rsi ?? 50;
  $("rsi-description").textContent = indicators.rsi == null ? "15개 이상 필요" : indicators.rsi >= 70 ? "70 이상 · 통상 과매수 구간" : indicators.rsi <= 30 ? "30 이하 · 통상 과매도 구간" : "30–70 · 중간 구간";
  $("macd").textContent = number(indicators.macd, 4);
  $("macd-signal").textContent = indicators.macd_signal == null ? "시그널 계산에 34개 이상 필요" : `시그널 ${number(indicators.macd_signal, 4)}`;
  $("macd-histogram").textContent = `히스토그램 ${number(indicators.macd_histogram, 4)}`;
  $("volume-ratio").textContent = indicators.volume_ratio == null ? "—" : `${number(indicators.volume_ratio, 2)}×`;
  $("volume").textContent = `최신 거래량 ${number(indicators.volume, 4)}`;
  const warnings = [...(summary?.warnings || [])];
  if (summary?.has_date_gaps) warnings.push("누락 날짜가 있습니다. 지표는 달력 날짜가 아닌 관측된 일봉 수 기준입니다.");
  $("summary-warning").textContent = warnings.length ? warnings.join(" ") : "완료된 일봉만 분석합니다. 거래 없는 날짜는 보간하지 않으며, 종가·거래량을 서버에서 계산합니다.";
}

function renderData() {
  const visible = state.records.slice(0, state.visibleRows);
  $("data-rows").replaceChildren(...visible.map((row) => {
    const tr = element("tr");
    for (const value of [row.date, number(row.value, 4), number(row.open, 4), number(row.high, 4), number(row.low, 4), number(row.volume, 4)]) tr.append(element("td", "", value));
    const note = element("td", "note-cell", `${row.memo || "메모 없음"} · ${row.source === "upbit" ? "업비트" : "직접 입력"}`);
    note.title = row.memo;
    tr.append(note);
    const controls = element("td");
    const edit = element("button", "button quiet", "수정");
    edit.dataset.mutation = "edit";
    edit.setAttribute("aria-label", `${row.date} 데이터 수정`);
    edit.addEventListener("click", () => openRecord(row));
    const remove = element("button", "button danger", "삭제");
    remove.dataset.mutation = "delete";
    remove.setAttribute("aria-label", `${row.date} 데이터 삭제`);
    remove.addEventListener("click", async () => {
      if (state.busy || !await confirmDelete(`${row.date} ${row.market} 데이터가 영구 삭제됩니다.`)) return;
      action(async () => {
        await api(`/api/data/${encodeURIComponent(row.id)}`, { method: "DELETE" });
        await refreshData();
        feedback("데이터를 삭제하고 요약을 갱신했습니다.", true);
      });
    });
    edit.disabled = remove.disabled = state.busy;
    controls.append(edit, remove);
    tr.append(controls);
    return tr;
  }));
  $("data-empty").hidden = state.records.length > 0;
  $("table-count").textContent = `${number(state.records.length)}개 중 ${number(visible.length)}개 표시`;
  $("show-more").hidden = visible.length >= state.records.length;
}
$("show-more").addEventListener("click", () => { state.visibleRows += 50; renderData(); });

async function refreshData() {
  const requestId = ++state.refreshId;
  const market = state.market;
  const [records, summary] = await Promise.all([
    api(`/api/data?market=${encodeURIComponent(market)}`),
    api(`/api/data/summary?market=${encodeURIComponent(market)}`),
  ]);
  if (requestId !== state.refreshId || market !== state.market) return;
  state.records = records;
  state.summary = summary;
  renderSummary();
  renderData();
}
function newChat() {
  state.messages = [];
  state.conversationId = null;
  $("question").value = "";
  $("chat-subtitle").textContent = `${state.market} · 저장된 데이터에 근거해 답변합니다`;
  renderMessages();
}
$("new-chat").addEventListener("click", () => { if (!state.busy) newChat(); });
$("market").addEventListener("change", () => action(async () => {
  state.market = $("market").value;
  state.visibleRows = 20;
  state.summary = null;
  state.records = [];
  renderSummary(); renderData(); newChat();
  await refreshData();
}));
$("refresh").addEventListener("click", () => action(async () => { await refreshData(); await loadConversations(); feedback("저장 데이터를 새로 불러왔습니다.", true); }));
$("import").addEventListener("click", () => action(async () => {
  $("import").textContent = "수집·저장 중…";
  try {
    const result = await api("/api/data/import", { method: "POST", body: JSON.stringify({ market: state.market }) });
    await refreshData();
    feedback(`${result.message}${result.count < 100 ? " 100개 미만입니다. 더 오래된 이력이 있는 종목을 선택하세요." : ""}`, true);
  } finally { $("import").textContent = "↓ 일봉 데이터 수집"; }
}));

function openRecord(record = null) {
  if (state.busy) return;
  state.editingId = record?.id || null;
  $("record-form").reset();
  $("record-error").hidden = true;
  $("record-title").textContent = record ? "일봉 데이터 수정" : "일봉 데이터 추가";
  $("record-help").textContent = record ? `${state.market} · 종목과 날짜는 고정됩니다. 수정된 기록은 직접 입력으로 표시합니다.` : `${state.market} · UTC 시작일 기준으로 완료된 일봉을 추가하세요.`;
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
  $("record-date").max = yesterday;
  for (const name of ["date", "value", "open", "high", "low", "volume", "memo"]) {
    $("record-form").elements.namedItem(name).value = record?.[name] ?? (name === "date" ? yesterday : "");
  }
  $("record-date").disabled = Boolean(record);
  $("record-dialog").showModal();
}
$("add-record").addEventListener("click", () => openRecord());
for (const id of ["close-dialog", "cancel-dialog"]) $(id).addEventListener("click", () => { if (!state.busy) $("record-dialog").close(); });
$("record-dialog").addEventListener("cancel", (event) => { if (state.busy) event.preventDefault(); });
$("record-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy) return;
  const form = $("record-form");
  const payload = { market: state.market, date: $("record-date").value, memo: form.elements.namedItem("memo").value.trim() };
  for (const name of ["value", "open", "high", "low", "volume"]) payload[name] = Number(form.elements.namedItem(name).value);
  if (payload.low > Math.min(payload.open, payload.value) || payload.high < Math.max(payload.open, payload.value)) {
    $("record-error").textContent = "저가 ≤ 시가/종가 ≤ 고가 관계를 확인하세요.";
    $("record-error").hidden = false;
    return;
  }
  setBusy(true);
  $("record-error").hidden = true;
  try {
    const edit = state.editingId;
    await api(edit ? `/api/data/${encodeURIComponent(edit)}` : "/api/data", { method: edit ? "PUT" : "POST", body: JSON.stringify(payload) });
    $("record-dialog").close();
    try {
      await refreshData();
      feedback("데이터를 저장하고 요약을 갱신했습니다.", true);
    } catch (error) { feedback(`저장은 완료됐지만 화면을 갱신하지 못했습니다. ${error.message}`); }
  } catch (error) { $("record-error").textContent = error.message; $("record-error").hidden = false; }
  finally { setBusy(false); }
});

function messageNode(message) {
  const article = element("article", `message ${message.role}${message.pending ? " pending" : ""}`);
  article.append(element("div", "message-role", message.role === "user" ? "나" : "COIN CONTEXT"), element("div", "message-content", message.content));
  return article;
}
function renderMessages(pending = false) {
  if (!state.messages.length) {
    const welcome = element("div", "chat-welcome");
    welcome.append(element("div", "welcome-icon", "✦"), element("h3", "", "숫자 너머의 맥락이 궁금한가요?"), element("p", "", "가격 흐름부터 지표의 의미까지.\n저장한 데이터를 바탕으로 차근차근 설명해 드릴게요."));
    $("messages").replaceChildren(welcome);
  } else $("messages").replaceChildren(...state.messages.map(messageNode));
  if (pending) $("messages").append(messageNode({ role: "assistant", content: "데이터를 읽고 답변하고 있어요…", pending: true }));
  $("messages").scrollTop = $("messages").scrollHeight;
  $("suggestions").hidden = state.messages.length > 0;
}
$("question").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); $("chat-form").requestSubmit(); }
});
document.querySelectorAll("[data-prompt]").forEach((button) => button.addEventListener("click", () => { $("question").value = button.dataset.prompt; $("question").focus(); }));
$("chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const question = $("question").value.trim();
  if (!question || state.busy) return;
  action(async () => {
    state.messages.push({ role: "user", content: question });
    $("question").value = "";
    $("chat-status").textContent = "답변을 생성하고 대화를 저장합니다…";
    renderMessages(true);
    let response;
    try {
      response = await api("/api/chat", { method: "POST", body: JSON.stringify({ market: state.market, message: question, conversation_id: state.conversationId }) });
    } catch (error) {
      state.messages.pop();
      $("question").value = question;
      throw error;
    } finally { $("chat-status").textContent = "Enter로 전송 · Shift+Enter로 줄바꿈"; renderMessages(); }
    state.conversationId = response.conversation_id;
    state.messages.push({ role: "assistant", content: response.answer });
    state.summary = response.summary;
    renderSummary(); renderMessages();
    await loadConversations();
  });
});

async function openConversation(id) {
  await action(async () => {
    const conversation = await api(`/api/conversations/${encodeURIComponent(id)}`);
    state.market = conversation.market;
    state.summary = null;
    state.records = [];
    renderSummary(); renderData();
    state.conversationId = conversation.id;
    state.messages = conversation.messages;
    state.visibleRows = 20;
    renderMarkets($("market-search").value);
    $("chat-subtitle").textContent = `${conversation.market} · ${conversation.title}`;
    $("question").value = "";
    setView("analysis"); renderMessages();
    await refreshData();
    $("chat-title").scrollIntoView({ block: "center", behavior: "smooth" });
  });
}
async function loadConversations() {
  state.conversations = await api("/api/conversations");
  renderHistory();
}
function renderHistory() {
  $("recent-list").replaceChildren();
  $("history-list").replaceChildren();
  if (!state.conversations.length) {
    $("recent-list").append(element("p", "muted", "저장된 대화가 여기에 표시됩니다."));
    $("history-list").append(element("p", "empty-state", "아직 저장된 대화가 없습니다. AI에게 첫 질문을 남겨보세요."));
  }
  for (const [index, conversation] of state.conversations.entries()) {
    if (index < 5) {
      const recent = element("button");
      recent.dataset.conversation = conversation.id;
      recent.append(element("span", "", `◷ ${conversation.title}`), element("small", "", `${conversation.market} · ${shortDate(conversation.updated_at)}`));
      recent.addEventListener("click", () => openConversation(conversation.id));
      recent.disabled = state.busy;
      $("recent-list").append(recent);
    }
    const card = element("article", "history-card");
    card.append(element("span", "history-market", conversation.market), element("h3", "", conversation.title), element("p", "", `${shortDate(conversation.updated_at)} · 메시지 ${conversation.message_count}개`));
    const controls = element("div", "history-actions");
    const load = element("button", "button secondary", "대화 불러오기 ↗");
    load.dataset.conversation = conversation.id;
    load.disabled = state.busy;
    load.addEventListener("click", () => openConversation(conversation.id));
    const remove = element("button", "button danger", "삭제");
    remove.dataset.mutation = "conversation";
    remove.disabled = state.busy;
    remove.addEventListener("click", async () => {
      if (state.busy || !await confirmDelete(`‘${conversation.title}’ 대화가 영구 삭제됩니다.`)) return;
      action(async () => {
        await api(`/api/conversations/${encodeURIComponent(conversation.id)}`, { method: "DELETE" });
        if (state.conversationId === conversation.id) newChat();
        await loadConversations(); feedback("대화를 삭제했습니다.", true);
      });
    });
    controls.append(load, remove); card.append(controls); $("history-list").append(card);
  }
}

async function init() {
  $("docs-link").href = apiBase + "/docs";
  renderSummary(); renderMessages(); renderHistory();
  setBusy(true);
  const jobs = await Promise.allSettled([api("/health"), api("/api/markets"), refreshData(), loadConversations()]);
  const health = jobs[0];
  if (health.status === "fulfilled") {
    const status = health.value;
    const notes = [];
    if (status.storage === "sqlite") notes.push("로컬 SQLite 저장 모드");
    if (!status.ai_configured) notes.push("AI 연결 전: 서버에 OpenAI API 키를 설정하면 대화할 수 있습니다.");
    if (status.storage === "firestore" && !status.firebase_configured) notes.push("Firebase 서비스 계정 설정이 필요합니다.");
    $("connection-note").textContent = notes.join(" · ");
    $("connection-note").hidden = !notes.length;
  } else $("connection-note").textContent = health.reason.message;
  if (jobs[1].status === "fulfilled") { state.markets = jobs[1].value; renderMarkets(); }
  const failed = jobs.slice(1).find((job) => job.status === "rejected");
  if (failed) feedback(failed.reason.message);
  setBusy(false);
}
init();
