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
  // Sprint 32: anexo "ler e descartar" (PDF/DOCX até 4 MB, só para a próxima pergunta).
  const fileInput = form ? form.querySelector("[data-attachment-input]") : null;
  const attachmentBox = form ? form.querySelector("[data-assistant-attachment]") : null;
  const MAX_FILE = 4 * 1024 * 1024;
  function clearAttachment() {
    if (!fileInput) return;
    fileInput.value = "";
    attachmentBox.hidden = true;
  }
  function attachedName() {
    return fileInput && fileInput.files && fileInput.files[0] ? fileInput.files[0].name : "";
  }
  if (fileInput) {
    fileInput.addEventListener("change", () => {
      const file = fileInput.files[0];
      if (!file) { clearAttachment(); return; }
      if (!/\.(pdf|docx)$/i.test(file.name)) { alert("Envie somente PDF ou DOCX."); clearAttachment(); return; }
      if (file.size > MAX_FILE) { alert("O arquivo passa de 4 MB. Envie um arquivo menor."); clearAttachment(); return; }
      attachmentBox.querySelector("[data-attachment-name]").textContent = file.name;
      attachmentBox.hidden = false;
      input.focus({ preventScroll: true });
    });
    attachmentBox.querySelector("[data-attachment-remove]").addEventListener("click", () => { clearAttachment(); input.focus(); });
  }

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
    const fileName = attachedName();
    addMessage("user", fileName ? `${question}\n\n📎 documento anexado: ${fileName} (lido e descartado)` : question);
    const body = addMessage("assistant", "");
    body.innerHTML = `<span class="assistant-typing">${fileName ? "Lendo o documento…" : "Assistente está digitando…"}</span>`;
    sendButton.disabled = true;
    const data = new FormData(form);
    data.set("pergunta", question);
    if (!fileName) data.delete("anexo");
    clearAttachment();
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
    root.resetConversation = reset;
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
  const head = panel.querySelector(".arise-panel-head");
  const MARGIN = 8;
  const isCompact = () => window.matchMedia("(max-width: 640px)").matches;

  // Posição guardada só nesta aba (conveniência; sem servidor).
  const posStore = {
    get(key) { try { return JSON.parse(sessionStorage.getItem(`arise-pos-${key}`) || "null"); } catch (e) { return null; } },
    set(key, value) { try { sessionStorage.setItem(`arise-pos-${key}`, JSON.stringify(value)); } catch (e) { /* sem armazenamento */ } },
  };
  const clamp = (left, top, el) => {
    const w = el.offsetWidth, h = el.offsetHeight;
    return {
      left: Math.min(Math.max(MARGIN, left), Math.max(MARGIN, window.innerWidth - w - MARGIN)),
      top: Math.min(Math.max(MARGIN, top), Math.max(MARGIN, window.innerHeight - h - MARGIN)),
    };
  };

  // Botão redondo: o contêiner fixo passa a usar left/top quando é arrastado.
  const placeFab = pos => {
    if (!pos) return;
    const p = clamp(pos.left, pos.top, toggle);
    Object.assign(widget.style, { left: `${p.left}px`, top: `${p.top}px`, right: "auto", bottom: "auto" });
  };
  // Janela do chat: posição livre no computador; no celular ocupa a tela inteira.
  const placePanel = () => {
    if (panel.hidden) return;
    if (isCompact()) { Object.assign(panel.style, { position: "", left: "", top: "", right: "", bottom: "" }); return; }
    panel.style.position = "fixed";
    panel.style.right = panel.style.bottom = "auto";
    let pos = posStore.get("painel");
    if (!pos) {
      // Abre ao lado do botão: acima, abaixo, à esquerda ou à direita — onde couber.
      const fab = toggle.getBoundingClientRect(), w = panel.offsetWidth, h = panel.offsetHeight, gap = 12;
      const fits = c => c.left >= MARGIN && c.top >= MARGIN
        && c.left + w <= window.innerWidth - MARGIN && c.top + h <= window.innerHeight - MARGIN;
      const sideTop = Math.min(Math.max(MARGIN, fab.top), window.innerHeight - h - MARGIN);
      const options = [
        { left: fab.right - w, top: fab.top - h - gap },
        { left: fab.right - w, top: fab.bottom + gap },
        { left: fab.left, top: fab.top - h - gap },
        { left: fab.left, top: fab.bottom + gap },
        { left: fab.left - w - gap, top: sideTop },
        { left: fab.right + gap, top: sideTop },
      ];
      pos = options.find(fits) || options[0];
    }
    const p = clamp(pos.left, pos.top, panel);
    panel.style.left = `${p.left}px`;
    panel.style.top = `${p.top}px`;
  };

  // Arrastar com mouse, caneta ou dedo. Movimento pequeno conta como clique.
  function draggable(handle, target, key, after) {
    let start = null;
    const move = event => {
      if (!start || event.pointerId !== start.id) return;
      const dx = event.clientX - start.x, dy = event.clientY - start.y;
      if (!start.moved && Math.hypot(dx, dy) < 5) return;
      if (!start.moved) { start.moved = true; widget.classList.add("is-dragging"); }
      const p = clamp(start.left + dx, start.top + dy, target);
      if (target === panel) { panel.style.left = `${p.left}px`; panel.style.top = `${p.top}px`; } else placeFab(p);
      event.preventDefault();
    };
    const finish = event => {
      if (!start || event.pointerId !== start.id) return;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", finish);
      if (start.moved) {
        const rect = target.getBoundingClientRect();
        posStore.set(key, { left: rect.left, top: rect.top });
        handle.dataset.justDragged = "1";
        setTimeout(() => { delete handle.dataset.justDragged; }, 0);
        if (after) after();
      }
      widget.classList.remove("is-dragging");
      start = null;
    };
    handle.addEventListener("pointerdown", event => {
      if (event.button !== 0 || event.target.closest("button:not([data-arise-toggle]), a, input, textarea")) return;
      if (target === panel && isCompact()) return;
      const rect = target.getBoundingClientRect();
      start = { x: event.clientX, y: event.clientY, left: rect.left, top: rect.top, moved: false, id: event.pointerId };
      window.addEventListener("pointermove", move, { passive: false });
      window.addEventListener("pointerup", finish);
      window.addEventListener("pointercancel", finish);
    });
  }

  // Aviso amarelo: aparece a cada abertura do painel e some depois de 35 segundos.
  const notice = panel.querySelector("[data-arise-notice]");
  const NOTICE_MS = 35000;
  let noticeTimer = null, fadeTimer = null;
  const stopNotice = () => { clearTimeout(noticeTimer); clearTimeout(fadeTimer); };
  const showNotice = () => {
    if (!notice) return;
    stopNotice();
    notice.hidden = false;
    notice.classList.remove("is-fading");
    noticeTimer = setTimeout(() => {
      notice.classList.add("is-fading");
      fadeTimer = setTimeout(() => { notice.hidden = true; }, 400);
    }, NOTICE_MS);
  };

  const open = () => {
    panel.hidden = false;
    placePanel();
    showNotice();
    toggle.setAttribute("aria-expanded", "true");
    widget.classList.add("is-open");
    if (panel.loadConversation) panel.loadConversation();
    const box = panel.querySelector("textarea");
    if (box) box.focus({ preventScroll: true });
  };
  // Minimizar: esconde a janela e mantém a conversa para continuar depois.
  const minimize = () => {
    stopNotice();
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    widget.classList.remove("is-open");
    toggle.focus({ preventScroll: true });
  };
  // Fechar: encerra o chat; a próxima abertura começa uma conversa nova
  // (a conversa encerrada continua no histórico da tela cheia).
  const end = () => {
    if (panel.resetConversation) panel.resetConversation();
    minimize();
  };

  placeFab(posStore.get("botao"));
  draggable(toggle, toggle, "botao", () => { if (!panel.hidden && !posStore.get("painel")) placePanel(); });
  draggable(head, panel, "painel");
  toggle.addEventListener("click", () => {
    if (toggle.dataset.justDragged) return;  // foi arrastado, não clicado
    panel.hidden ? open() : minimize();
  });
  widget.querySelector("[data-arise-minimize]").addEventListener("click", minimize);
  widget.querySelector("[data-arise-close]").addEventListener("click", end);
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !panel.hidden) minimize(); });
  window.addEventListener("resize", () => { placeFab(posStore.get("botao")); placePanel(); });
}
})();
