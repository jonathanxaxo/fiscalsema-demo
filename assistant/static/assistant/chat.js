"use strict";
// Assistente Arise do FiscalSema (Sprints 21–23): página, painel flutuante, streaming e formatação segura.
(function () {
document.querySelectorAll("[data-assistant]").forEach(init);
setupWidget();

function init(root) {
  const floating = root.hasAttribute("data-floating");
  const storageKey = `arise-conversa-${root.dataset.user || ""}`;
  const store = {
    get() { try { return sessionStorage.getItem(storageKey) || ""; } catch (e) { return ""; } },
    set(v) { try { v ? sessionStorage.setItem(storageKey, v) : sessionStorage.removeItem(storageKey); } catch (e) { /* sem armazenamento */ } },
  };
  const form = root.querySelector("[data-assistant-form]");
  const list = root.querySelector("[data-assistant-messages]");
  const input = form ? form.querySelector("textarea") : null;
  const sendButton = form ? form.querySelector("button[type=submit]") : null;
  const conversationInput = form ? form.querySelector("input[name=conversa]") : null;
  const welcome = root.querySelector("[data-assistant-welcome]");

  function esc(text) {
    return String(text ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function inline(text) {
    return text
      .replace(/`([^`\n]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
      .replace(/(^|[^_])_([^_\n]+)_/g, "$1<em>$2</em>");
  }

  // Markdown simples e seguro: escapa TUDO antes de formatar (listas, títulos, código e tabelas).
  function md(raw) {
    const blocks = [];
    let text = esc(raw).replace(/```[\w-]*\n?([\s\S]*?)(```|$)/g, (_, code) => {
      blocks.push(`<pre><code>${code.replace(/\n$/, "")}</code></pre>`);
      return `\u0000${blocks.length - 1}\u0000`;
    });
    const lines = text.split("\n");
    let html = "", listType = null;
    const closeList = () => { if (listType) { html += `</${listType}>`; listType = null; } };
    const isRow = line => /^\s*\|.*\|\s*$/.test(line);
    const cells = line => line.trim().replace(/^\||\|$/g, "").split("|").map(c => inline(c.trim()));
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      let m;
      if (isRow(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
        closeList();
        let table = `<div class="table-responsive"><table class="table-compact"><thead><tr>${cells(line).map(c => `<th>${c}</th>`).join("")}</tr></thead><tbody>`;
        i += 2;
        while (i < lines.length && isRow(lines[i])) { table += `<tr>${cells(lines[i]).map(c => `<td>${c}</td>`).join("")}</tr>`; i++; }
        i--;
        html += table + "</tbody></table></div>";
      } else if ((m = line.match(/^\s*[-*•]\s+(.*)/))) {
        if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; }
        html += `<li>${inline(m[1])}</li>`;
      } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)/))) {
        if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; }
        html += `<li>${inline(m[1])}</li>`;
      } else if ((m = line.match(/^#{1,4}\s+(.*)/))) {
        closeList(); html += `<h4>${inline(m[1])}</h4>`;
      } else if (line.trim() === "") {
        // mantém a lista aberta
      } else {
        closeList(); html += `<p>${inline(line)}</p>`;
      }
    }
    closeList();
    return html.replace(/\u0000(\d+)\u0000/g, (_, n) => blocks[n]).replace(/<p>(<pre>[\s\S]*?<\/pre>)<\/p>/g, "$1");
  }

  function scrollDown() { list.scrollTop = list.scrollHeight; }

  function addMessage(role, text) {
    const item = document.createElement("div");
    item.className = `assistant-msg assistant-msg-${role}`;
    const label = document.createElement("span");
    label.className = "assistant-msg-label";
    label.textContent = role === "user" ? "Você" : "Assistente Arise";
    const body = document.createElement("div");
    body.className = "assistant-msg-body";
    if (role === "user") body.textContent = text; else body.innerHTML = md(text);
    item.append(label, body);
    list.appendChild(item);
    scrollDown();
    return body;
  }

  // Mensagens já gravadas (renderizadas pelo servidor como texto puro).
  root.querySelectorAll("[data-md]").forEach(el => { el.innerHTML = md(el.textContent); });
  scrollDown();

  async function send(question) {
    question = question.trim();
    if (!question || sendButton.disabled) return;
    if (welcome) welcome.hidden = true;
    addMessage("user", question);
    const body = addMessage("assistant", "");
    body.innerHTML = '<span class="assistant-typing">Assistente está digitando…</span>';
    sendButton.disabled = true;
    const data = new FormData(form);
    data.set("pergunta", question);
    const started = performance.now();
    let first = 0;
    try {
      const response = await fetch(form.action, { method: "POST", body: data, credentials: "same-origin", headers: { "X-Requested-With": "fetch" } });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.erro || (response.status === 403 ? "Sua sessão expirou. Recarregue a página e entre de novo." : `Erro ${response.status}.`));
      }
      const id = response.headers.get("X-Conversa-Id");
      if (id && conversationInput && conversationInput.value !== id) {
        conversationInput.value = id;
        if (floating) {
          store.set(id);
          const full = root.querySelector("[data-assistant-full]");
          if (full) full.href = `${root.dataset.historyUrl}${id}/`;
        } else {
          try { history.replaceState(null, "", `${root.dataset.conversationBase}${id}/`); } catch (e) { /* sem histórico */ }
        }
      }
      const reader = response.body.getReader(), decoder = new TextDecoder();
      let total = "", scheduled = false;
      const draw = () => { scheduled = false; body.innerHTML = md(total); scrollDown(); };
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        if (!first) first = performance.now();
        total += decoder.decode(value, { stream: true });
        if (!scheduled) { scheduled = true; requestAnimationFrame(draw); }
      }
      draw();
      if (!total.trim()) body.innerHTML = '<p class="assistant-error">Não recebi resposta. Tente novamente.</p>';
      console.debug(`[Assistente Arise] 1ª palavra ${((first - started) / 1000).toFixed(1)} s · total ${((performance.now() - started) / 1000).toFixed(1)} s`);
    } catch (error) {
      body.innerHTML = `<p class="assistant-error">${esc(error.message)}</p>`;
    } finally {
      sendButton.disabled = false;
      input.focus({ preventScroll: true });
    }
  }

  if (form) {
    form.addEventListener("submit", event => {
      event.preventDefault();
      const question = input.value;
      input.value = "";
      input.style.height = "";
      send(question);
    });
    input.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
    });
    input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 180) + "px"; });
    root.querySelectorAll("[data-suggestion]").forEach(button => {
      button.addEventListener("click", () => send(button.dataset.suggestion));
    });
  }

  if (floating) {
    const newButton = root.querySelector("[data-assistant-new]");
    const reset = () => {
      store.set("");
      conversationInput.value = "";
      list.querySelectorAll(".assistant-msg").forEach(el => el.remove());
      if (welcome) welcome.hidden = false;
      const full = root.querySelector("[data-assistant-full]");
      if (full) full.href = root.dataset.historyUrl.replace(/conversas\/$/, "");
    };
    if (newButton) newButton.addEventListener("click", () => { reset(); input.focus(); });
    // Continua a última conversa desta aba, buscando as mensagens no servidor (só do próprio usuário).
    root.loadConversation = async () => {
      const id = store.get();
      if (!id || conversationInput.value === id) return;
      try {
        const response = await fetch(`${root.dataset.historyUrl}${id}/mensagens/`, { credentials: "same-origin" });
        if (!response.ok) { reset(); return; }
        const data = await response.json();
        conversationInput.value = String(data.id);
        if (welcome && data.mensagens.length) welcome.hidden = true;
        data.mensagens.forEach(m => addMessage(m.role, m.content));
        const full = root.querySelector("[data-assistant-full]");
        if (full) full.href = `${root.dataset.historyUrl}${data.id}/`;
      } catch (e) { /* sem rede: começa vazia */ }
    };
  }
}

function setupWidget() {
  const widget = document.querySelector("[data-arise-widget]");
  if (!widget) return;
  const toggle = widget.querySelector("[data-arise-toggle]");
  const panel = widget.querySelector(".arise-panel");
  const open = () => {
    panel.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    widget.classList.add("is-open");
    if (panel.loadConversation) panel.loadConversation();
    const box = panel.querySelector("textarea");
    if (box) box.focus({ preventScroll: true });
  };
  const close = () => {
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    widget.classList.remove("is-open");
    toggle.focus({ preventScroll: true });
  };
  toggle.addEventListener("click", () => (panel.hidden ? open() : close()));
  widget.querySelector("[data-arise-close]").addEventListener("click", close);
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !panel.hidden) close(); });
}
})();
