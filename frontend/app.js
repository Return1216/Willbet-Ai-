// 这个文件只负责浏览器交互，不包含任何服务端密钥或模型配置。
const launcher = document.querySelector("#launcher");
const panel = document.querySelector("#chat-panel");
const closeButton = document.querySelector("#close-button");
const clearButton = document.querySelector("#clear-button");
const form = document.querySelector("#chat-form");
const questionInput = document.querySelector("#question");
const sendButton = document.querySelector("#send-button");
const messages = document.querySelector("#messages");
const errorMessage = document.querySelector("#error-message");

const sessionId = globalThis.crypto?.randomUUID?.() || `web-${Date.now()}`;
let busy = false;

function setOpen(isOpen) {
  panel.hidden = !isOpen;
  launcher.setAttribute("aria-expanded", String(isOpen));
  if (isOpen) questionInput.focus();
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

function clearError() {
  errorMessage.textContent = "";
  errorMessage.hidden = true;
}

function appendMessage(role, content = "") {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;
  item.appendChild(bubble);
  messages.appendChild(item);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

function resetMessages() {
  messages.innerHTML = `
    <div class="welcome-card">
      <span class="welcome-mark" aria-hidden="true">✦</span>
      <div><strong>你好，我是 WillBet AI</strong><p>可以问我提现、投注、赛事和游戏相关的问题。</p></div>
    </div>`;
  clearError();
}

function setBusy(value) {
  busy = value;
  sendButton.disabled = value;
  questionInput.disabled = value;
  sendButton.setAttribute("aria-busy", String(value));
}

function readEvent(frame) {
  const data = frame.split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!data) return null;
  if (data === "[DONE]") return "done-marker";
  try { return JSON.parse(data); } catch { return null; }
}

async function sendQuestion(question) {
  clearError();
  const answerBubble = appendMessage("assistant");
  answerBubble.parentElement.classList.add("pending");
  try {
    let receivedToken = false;
    const response = await fetch("/api/assistant/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ question, session_id: sessionId, stream: true }),
    });
    if (!response.ok) throw new Error(`服务暂时不可用（${response.status}）`);
    if (!response.body) throw new Error("浏览器不支持流式响应");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let completed = false;
    while (!completed) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() || "";
      for (const frame of frames) {
        const event = readEvent(frame);
        if (!event) continue;
        if (event === "done-marker") { completed = true; break; }
        if (event.type === "token") { answerBubble.textContent += event.content || ""; receivedToken = true; }
        if (event.type === "clarification") { answerBubble.textContent = event.content || ""; receivedToken = true; }
        if (event.type === "error") throw new Error(event.message || "助手暂时无法回答");
        if (event.type === "done") {
          if (!receivedToken && event.answer) answerBubble.textContent = event.answer;
          completed = true;
          break;
        }
      }
      messages.scrollTop = messages.scrollHeight;
      if (done) break;
    }
    if (!answerBubble.textContent.trim()) answerBubble.textContent = "暂时没有得到回答，请稍后再试。";
  } finally {
    answerBubble.parentElement.classList.remove("pending");
  }
}

launcher.addEventListener("click", () => setOpen(panel.hidden));
closeButton.addEventListener("click", () => setOpen(false));
clearButton.addEventListener("click", resetMessages);

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question || busy) return;
  appendMessage("user", question);
  questionInput.value = "";
  setBusy(true);
  try {
    await sendQuestion(question);
  } catch (error) {
    showError(error instanceof Error ? error.message : "请求失败，请稍后再试");
  } finally {
    setBusy(false);
    questionInput.focus();
  }
});
