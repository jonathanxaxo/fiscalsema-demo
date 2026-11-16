(() => {
  const body = document.body;
  const menuButton = document.querySelector('.menu-toggle');
  const closeMenu = () => {
    body.classList.remove('menu-open');
    menuButton?.setAttribute('aria-expanded', 'false');
  };

  const topbar = document.querySelector('.topbar');
  const updateMenuTop = () => {
    if (!topbar) return;
    const bottom = Math.max(0, Math.round(topbar.getBoundingClientRect().bottom));
    document.documentElement.style.setProperty('--menu-top', `${bottom}px`);
  };
  window.addEventListener('scroll', () => { if (body.classList.contains('menu-open')) updateMenuTop(); }, { passive: true });
  window.addEventListener('resize', updateMenuTop);

  menuButton?.addEventListener('click', () => {
    updateMenuTop();
    const opening = !body.classList.contains('menu-open');
    body.classList.toggle('menu-open', opening);
    menuButton.setAttribute('aria-expanded', String(opening));
  });
  document.querySelector('[data-menu-close]')?.addEventListener('click', closeMenu);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeMenu();
  });

  // Sprint 35: links internos (#...) abrem a seção recolhida correspondente.
  const revealHashTarget = () => {
    if (!window.location.hash) return;
    let target = null;
    try { target = document.querySelector(window.location.hash); } catch (error) { return; }
    let parent = target?.parentElement;
    while (parent) {
      if (parent.tagName === 'DETAILS') parent.open = true;
      parent = parent.parentElement;
    }
    target?.scrollIntoView({ block: 'start' });
  };
  revealHashTarget();
  window.addEventListener('hashchange', revealHashTarget);

  // Sprint 35: seletores marcados trocam o conteúdo assim que a opção é escolhida.
  document.querySelectorAll('select[data-autosubmit]').forEach((select) => {
    select.addEventListener('change', () => select.form?.submit());
  });

  // Sprint 35: máscara de CPF/CNPJ enquanto digita (o servidor guarda só os dígitos).
  const formatTaxId = (value) => {
    const digits = value.replace(/\D/g, '').slice(0, 14);
    if (digits.length <= 11) {
      return digits
        .replace(/^(\d{3})(\d)/, '$1.$2')
        .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
        .replace(/\.(\d{3})(\d{1,2})$/, '.$1-$2');
    }
    return digits
      .replace(/^(\d{2})(\d)/, '$1.$2')
      .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
      .replace(/\.(\d{3})(\d)/, '.$1/$2')
      .replace(/(\d{4})(\d{1,2})$/, '$1-$2');
  };
  document.querySelectorAll('[data-tax-id]').forEach((field) => {
    const applyMask = () => { field.value = formatTaxId(field.value); };
    applyMask();
    field.addEventListener('input', applyMask);
  });

  document.querySelectorAll('table').forEach((table) => {
    if (table.parentElement?.classList.contains('table-responsive') || table.closest('.table-scroll')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'table-responsive';
    wrapper.setAttribute('tabindex', '0');
    wrapper.setAttribute('role', 'region');
    const sectionTitle = table.closest('section')?.querySelector('h2')?.textContent?.trim();
    wrapper.setAttribute('aria-label', sectionTitle ? `Tabela: ${sectionTitle}` : 'Tabela com rolagem horizontal');
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
  });

  const notifications = document.querySelector('[data-notifications]');
  if (notifications) {
    notifications.addEventListener('toggle', () => { if (notifications.open) updateMenuTop(); });
    document.addEventListener('click', (event) => {
      if (notifications.open && !notifications.contains(event.target)) notifications.open = false;
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && notifications.open) {
        notifications.open = false;
        notifications.querySelector('summary')?.focus();
      }
    });
  }

  const scrollHints = [];
  document.querySelectorAll('.table-responsive').forEach((wrapper) => {
    const hint = document.createElement('p');
    hint.className = 'table-scroll-hint';
    hint.textContent = 'Deslize a tabela para o lado para ver todas as colunas →';
    wrapper.parentNode.insertBefore(hint, wrapper);
    scrollHints.push([wrapper, hint]);
  });
  const updateScrollHints = () => {
    scrollHints.forEach(([wrapper, hint]) => {
      hint.classList.toggle('is-visible', wrapper.scrollWidth > wrapper.clientWidth + 1);
    });
  };
  updateScrollHints();
  window.addEventListener('resize', updateScrollHints);

  document.querySelectorAll('.notice').forEach((notice) => {
    if (!notice.hasAttribute('role')) notice.setAttribute('role', 'status');
    if (!notice.hasAttribute('aria-live')) notice.setAttribute('aria-live', 'polite');
  });

  document.querySelectorAll('form[method="post"]:not([data-no-submit-lock])').forEach((form) => {
    let dirty = false;
    form.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach((field) => {
      field.addEventListener('input', () => { dirty = true; });
      field.addEventListener('change', () => { dirty = true; });
    });
    window.addEventListener('beforeunload', (event) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = '';
    });
    form.addEventListener('submit', (event) => {
      if (event.defaultPrevented) return;
      dirty = false;
      const button = form.querySelector('button[type="submit"]');
      if (!button) return;
      button.disabled = true;
      button.dataset.originalText = button.textContent;
      button.textContent = 'Processando…';
    });
  });
})();

// Sprint 47: linhas marcadas com data-row-link abrem o registro ao clicar em qualquer parte da linha
// (links, botões e formulários da linha continuam funcionando normalmente).
(() => {
  // Sprint 48: no sistema inteiro, a linha cujo primeiro campo já é um link (número da OS, do empenho,
  // da NF, do pagamento...) abre esse mesmo link. Tabelas marcadas com data-no-row-link ficam de fora.
  document.querySelectorAll('tbody tr:not([data-row-link])').forEach((row) => {
    if (row.closest('[data-no-row-link], .assistant-messages, .arise-panel') || !row.cells.length) return;
    const link = row.cells[0].querySelector('a[href]:not([download]):not([target]):not([href^="#"]):not([href^="javascript"])');
    if (link) row.dataset.rowLink = link.getAttribute('href');
  });
  document.querySelectorAll('tr[data-row-link]').forEach((row) => {
    row.classList.add('row-link');
    row.addEventListener('click', (event) => {
      if (event.target.closest('a, button, input, select, textarea, label, form, summary')) return;
      if (window.getSelection && String(window.getSelection()).trim()) return;
      if (event.ctrlKey || event.metaKey) { window.open(row.dataset.rowLink, '_blank', 'noopener'); return; }
      window.location.href = row.dataset.rowLink;
    });
  });
})();

// Sprint 36: prazo sugerido (ex.: OS: abertura + 6 meses). Só preenche se o campo
// estiver vazio ou ainda tiver o último valor sugerido; a pessoa pode alterar.
(() => {
  document.querySelectorAll('input[data-suggest-from][data-suggest-months]').forEach((target) => {
    const form = target.form;
    if (!form) return;
    const source = form.elements.namedItem(target.dataset.suggestFrom);
    const months = Number(target.dataset.suggestMonths);
    if (!source || !Number.isInteger(months)) return;
    let lastSuggested = '';
    const suggest = () => {
      const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(source.value || '');
      if (!match) return;
      if (target.value && target.value !== lastSuggested) return;
      const year = Number(match[1]);
      const monthIndex = Number(match[2]) - 1 + months;
      const day = Number(match[3]);
      const targetYear = year + Math.floor(monthIndex / 12);
      const targetMonth = monthIndex % 12;
      const lastDay = new Date(Date.UTC(targetYear, targetMonth + 1, 0)).getUTCDate();
      const value = [
        String(targetYear).padStart(4, '0'),
        String(targetMonth + 1).padStart(2, '0'),
        String(Math.min(day, lastDay)).padStart(2, '0'),
      ].join('-');
      target.value = value;
      lastSuggested = value;
    };
    source.addEventListener('change', suggest);
    if (!target.value) suggest();
  });
})();

// Sprint 41: visual vivo. Tudo é apresentação; respeita "Movimento" e prefers-reduced-motion.
(() => {
  const root = document.documentElement;
  const KEY = 'fiscalsema-movimento';
  // Sprint 45: sem escolha salva, o pedido de "reduzir movimento" do sistema operacional vira "Calmo"
  // (continua pulsando, mais devagar). "Vivo" e "Sem" escolhidos pela pessoa sempre valem.
  const fallback = () => (window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'calmo' : 'vivo');
  const read = () => { try { return localStorage.getItem(KEY) || fallback(); } catch (e) { return fallback(); } };
  const apply = (mode) => {
    root.dataset.motion = mode;
    // Sprint 46: no modo "Sem", o logotipo usa a versão parada (a animação fica dentro do SVG).
    document.querySelectorAll('.brand-picture').forEach((picture) => {
      const img = picture.querySelector('img');
      const still = img?.dataset.stillSrc;
      if (!img || !still) return;
      if (!img.dataset.liveSrc) img.dataset.liveSrc = img.getAttribute('src');
      img.setAttribute('src', mode === 'sem' ? still : img.dataset.liveSrc);
    });
    document.querySelectorAll('[data-motion-choice]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.motionChoice === mode)));
  };
  apply(read());
  document.querySelectorAll('[data-motion-choice]').forEach((button) => button.addEventListener('click', () => {
    try { localStorage.setItem(KEY, button.dataset.motionChoice); } catch (e) { /* sem armazenamento */ }
    apply(button.dataset.motionChoice);
  }));
  const still = () => root.dataset.motion === 'sem';

  // Ordem de entrada (sequência) das seções, campos, linhas, itens de menu e avisos.
  const stagger = (selector, variable = '--fs-i') => {
    document.querySelectorAll(selector).forEach((group) => {
      [...group.children].forEach((child, index) => child.style.setProperty(variable, Math.min(index, 20)));
    });
  };
  stagger('.content');
  stagger('.dashboard-columns');
  stagger('.form-card');
  stagger('form.form-grid');
  stagger('.sidebar nav');
  stagger('.notifications-list');
  stagger('.method-grid');
  stagger('.method-steps');
  stagger('.account-methods');
  // Sprint 45: barras do gráfico mensal respiram em sequência.
  document.querySelectorAll('.exec-chart-bars span').forEach((bar, index) => bar.style.setProperty('--fs-b', index % 12));
  // Sprint 44: números das sprints da Metodologia acendem em onda.
  document.querySelectorAll('.method-timeline li b').forEach((b, index) => b.style.setProperty('--fs-w', index));
  // Sprint 42: telas sem cabeçalho de página, formulários simples, detalhes e login.
  stagger('.auth-card');
  document.querySelectorAll('.content form:not(.form-grid):not(.inline-form):not(.assistant-form), .auth-card form, .content dl').forEach((group) => {
    [...group.children].forEach((child, index) => child.style.setProperty('--fs-i', Math.min(index, 20)));
  });
  stagger('tbody', '--fs-r');

  // Barras de progresso: enchem a partir do zero, com ponto pulsante na ponta.
  const bars = [];
  document.querySelectorAll('.progress > span').forEach((span) => {
    const target = parseFloat(span.style.width) || 0;
    const progress = span.parentElement;
    if (progress.closest('.col-progress') && target >= 90) progress.classList.add('is-critical');
    if (target > 0 && !progress.querySelector('.fs-tip')) {
      const tip = document.createElement('i');
      tip.className = 'fs-tip';
      tip.setAttribute('aria-hidden', 'true');
      progress.appendChild(tip);
    }
    bars.push([span, target]);
  });
  const tracks = [...document.querySelectorAll('.exec-track > span')].map((span) => [span, parseFloat(span.style.width) || 0]);
  const columns = [...document.querySelectorAll('.exec-chart-bars span')].map((span) => [span, span.style.height]);
  if (!still()) {
    bars.forEach(([span]) => { span.style.width = '0%'; });
    tracks.forEach(([span]) => { span.style.width = '0%'; });
    columns.forEach(([span]) => { span.style.height = '0%'; });
    document.querySelectorAll('.progress .fs-tip').forEach((tip) => { tip.style.left = '0%'; });
  }
  requestAnimationFrame(() => requestAnimationFrame(() => {
    bars.forEach(([span, target]) => {
      const width = Math.min(Math.max(target, 0), 100);
      span.style.width = `${width}%`;
      const tip = span.parentElement.querySelector('.fs-tip');
      if (tip) tip.style.left = `${width}%`;
    });
    tracks.forEach(([span, target]) => { span.style.width = `${target}%`; });
    columns.forEach(([span, height], index) => { setTimeout(() => { span.style.height = height; }, still() ? 0 : index * 25); });
  }));

  // Valores em R$ dos indicadores contam até o número final.
  const parse = (text) => Number(text.replace(/[^\d,]/g, '').replace(',', '.'));
  const format = (value) => value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (!still()) {
    document.querySelectorAll('.kpi-card strong, .exec-mini-kpis strong').forEach((el) => {
      const text = el.textContent.trim();
      if (!/^R\$\s?[\d.]+(,\d{1,2})?$/.test(text.replace(/ /g, ' '))) return;
      const target = parse(text);
      if (!target) return;
      const start = performance.now();
      const step = (now) => {
        const t = Math.min(1, (now - start) / 1200);
        el.textContent = `R$ ${format(target * (1 - Math.pow(1 - t, 3)))}`;
        if (t < 1) requestAnimationFrame(step); else el.textContent = text;
      };
      requestAnimationFrame(step);
    });
  }

  // Ondulação ao clicar em botões.
  document.addEventListener('pointerdown', (event) => {
    const button = event.target.closest('button, .button-link');
    if (!button || still() || button.closest('.arise-panel, .arise-widget')) return;
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const ripple = document.createElement('span');
    ripple.className = 'fs-ripple';
    Object.assign(ripple.style, { width: `${size}px`, height: `${size}px`, left: `${event.clientX - rect.left - size / 2}px`, top: `${event.clientY - rect.top - size / 2}px` });
    button.appendChild(ripple);
    setTimeout(() => ripple.remove(), 650);
  });

  // Sino balança uma vez por sessão quando há pendências.
  const toggle = document.querySelector('.notifications-toggle');
  if (toggle && toggle.querySelector('.notifications-count') && !still()) {
    let rang = false;
    try { rang = sessionStorage.getItem('fiscalsema-sino') === '1'; sessionStorage.setItem('fiscalsema-sino', '1'); } catch (e) { /* sem armazenamento */ }
    if (!rang) setTimeout(() => toggle.classList.add('fs-ring'), 600);
  }
})();

// Sprint 49: depois de 1 hora sem mexer no sistema, a tela volta para a entrada (o servidor
// encerra a sessão). Enquanto a pessoa digita ou rola a tela sem salvar, o navegador avisa o
// servidor a cada 5 minutos de uso, para não perder o que está sendo preenchido.
(() => {
  const body = document.body;
  const limit = Number(body.dataset.idleTimeout || 0) * 1000;
  const pingUrl = body.dataset.keepaliveUrl;
  if (!limit || !pingUrl) return;
  const KEY = 'fiscalsema-ultima-atividade';
  const PING_EVERY = Math.min(5 * 60 * 1000, limit / 2);
  const read = () => { try { return Number(localStorage.getItem(KEY)) || 0; } catch (e) { return 0; } };
  let local = Date.now();
  let lastPing = Date.now();
  let lastMark = 0;
  const mark = () => {
    const now = Date.now();
    if (now - lastMark < 1000) return;
    lastMark = now; local = now;
    try { localStorage.setItem(KEY, String(now)); } catch (e) { /* sem armazenamento */ }
    if (now - lastPing >= PING_EVERY) {
      lastPing = now;
      fetch(pingUrl, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' }, cache: 'no-store' })
        .then((response) => { if (response.status === 401) window.location.reload(); })
        .catch(() => { /* sem rede: o servidor decide na próxima ação */ });
    }
  };
  mark();
  ['pointerdown', 'keydown', 'wheel', 'touchstart', 'scroll', 'mousemove'].forEach((type) =>
    window.addEventListener(type, mark, { passive: true, capture: true }));
  setInterval(() => {
    const last = Math.max(local, read()); // outra aba aberta também conta como uso
    if (Date.now() - last > limit + 5000) window.location.reload();
  }, 30000);
})();

// Sprint 52: fechou a aba do sistema e abriu de novo → pede a senha.
// Cada aba guarda uma marca que some quando ela é fechada. Ao abrir uma aba sem a marca, o
// sistema pergunta às outras abas dele se alguma está aberta; se nenhuma responder, ele foi
// fechado e reaberto: a sessão é encerrada e a pessoa entra de novo com a senha.
// Atualizar a página e trocar de tela mantêm a marca; Ctrl+clique abre nova aba com outra aberta.
(() => {
  const KEY = 'fiscalsema-aba';
  const root = document.documentElement;
  const body = document.body;
  const reveal = () => root.classList.remove('fs-verificando');
  let storageOk = true;
  try { sessionStorage.getItem(KEY); } catch (e) { storageOk = false; }
  if (!storageOk) { reveal(); return; }
  if (body.classList.contains('auth-page')) { // tela de entrada: o login vai acontecer nesta aba
    sessionStorage.setItem(KEY, '1');
    return;
  }
  const closedUrl = body.dataset.tabClosedUrl;
  const channel = 'BroadcastChannel' in window ? new BroadcastChannel('fiscalsema-abas') : null;
  if (channel) {
    channel.onmessage = (event) => {
      if (event.data === 'alguem-aberto?' && sessionStorage.getItem(KEY)) channel.postMessage('estou-aberto');
    };
  }
  if (!closedUrl || sessionStorage.getItem(KEY)) { reveal(); return; }
  if (!channel) { sessionStorage.setItem(KEY, '1'); reveal(); return; } // navegador antigo: não arrisca
  let answered = false;
  const listen = (event) => { if (event.data === 'estou-aberto') answered = true; };
  channel.addEventListener('message', listen);
  channel.postMessage('alguem-aberto?');
  setTimeout(() => {
    channel.removeEventListener('message', listen);
    if (answered) { sessionStorage.setItem(KEY, '1'); reveal(); return; }
    const token = document.querySelector('form[action*="/sair/"] input[name="csrfmiddlewaretoken"]')?.value || '';
    fetch(closedUrl, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': token, 'X-Requested-With': 'fetch' } })
      .then((response) => response.json().catch(() => ({})))
      .then((data) => {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.replace(`${data.login || '/conta/entrar/'}?next=${next}`);
      })
      .catch(() => { sessionStorage.setItem(KEY, '1'); reveal(); });
  }, 700);
  setTimeout(reveal, 4000); // segurança: nunca deixa a tela escondida
})();
