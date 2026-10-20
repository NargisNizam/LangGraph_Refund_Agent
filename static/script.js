const $ = (id) => document.getElementById(id);
const form = $("requestForm");
const threadInput = $("threadInput");
const orderInput = $("orderInput");
const messageInput = $("messageInput");
const submitBtn = $("submitBtn");
const resultPanel = $("resultPanel");
let activeThreadId = null;

function createThreadId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return `support-${window.crypto.randomUUID()}`;
  }
  return `support-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
function prepareNewRequest() {
  activeThreadId = createThreadId();
  threadInput.value = activeThreadId;
}
function setBusy(busy) {
  submitBtn.disabled = busy;
  submitBtn.innerHTML = busy ? "Processing…" : "<span>✦</span> Process Request";
}
function showResult(data, isError = false) {
  resultPanel.hidden = false;
  $("resultStatus").textContent = isError ? "Request failed" :
    data.status === "awaiting_approval" ? "Awaiting approval" : (data.decision || "Completed").replaceAll("_", " ");
  $("resultStatus").className = "status-pill" + (isError ? " error" : data.status === "awaiting_approval" ? " pending" : "");
  $("resultMessage").textContent = data.response || data.detail ||
    (data.interrupts?.[0] ? JSON.stringify(data.interrupts[0], null, 2) : "Request processed.");
  $("resultReference").textContent = data.thread_id ? `Reference: ${data.thread_id}` : "";
  const pending = !isError && data.status === "awaiting_approval";
  $("reviewControls").hidden = !pending;
  if (pending) {
    const info = data.interrupts?.[0] || {};
    $("reviewSummary").textContent = `Order ${info.order_id || orderInput.value || "unknown"} · Amount $${Number(info.amount || 0).toFixed(2)}. Please review before continuing.`;
  }
  resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
async function apiRequest(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
  } catch (error) {
    throw new Error("Cannot connect to the API. Confirm that the FastAPI server is running.");
  }
  const raw = await response.text();
  let data;
  try { data = raw ? JSON.parse(raw) : {}; }
  catch { data = { detail: raw || `Server returned HTTP ${response.status}` }; }
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data);
    throw new Error(detail || `Request failed with HTTP ${response.status}`);
  }
  return data;
}
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!messageInput.value.trim()) {
    messageInput.focus();
    return;
  }
  setBusy(true);
  try {
    const data = await apiRequest("/support", {
      method: "POST",
      body: JSON.stringify({
        thread_id: threadInput.value,
        message: messageInput.value.trim(),
        order_id: orderInput.value.trim() || null,
      }),
    });
    showResult(data);
  } catch (error) {
    showResult({ thread_id: threadInput.value, response: error.message }, true);
  } finally {
    setBusy(false);
  }
});
async function review(approved) {
  $("approveBtn").disabled = true;
  $("rejectBtn").disabled = true;
  try {
    const data = await apiRequest(`/review/${encodeURIComponent(activeThreadId || threadInput.value)}`, {
      method: "POST",
      body: JSON.stringify({ approved }),
    });
    showResult(data);
  } catch (error) {
    showResult({ thread_id: activeThreadId || threadInput.value, response: error.message }, true);
  } finally {
    $("approveBtn").disabled = false;
    $("rejectBtn").disabled = false;
  }
}
$("approveBtn").addEventListener("click", () => review(true));
$("rejectBtn").addEventListener("click", () => review(false));
$("newRefBtn").addEventListener("click", prepareNewRequest);
$("resetBtn").addEventListener("click", () => {
  form.reset();
  prepareNewRequest();
  resultPanel.hidden = true;
  messageInput.focus();
});
async function checkHealth() {
  try {
    const data = await apiRequest("/health");
    $("healthText").textContent = data.status === "ok" ? "Online · Ready" : "Status unknown";
  } catch {
    $("healthText").textContent = "Offline · Check server";
  }
}
prepareNewRequest();
checkHealth();
