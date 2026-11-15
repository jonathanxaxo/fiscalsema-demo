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
  const read = () => { try { return localStorage.getItem(KEY) || 'vivo'; } catch (e) { return 'vivo'; } };
  const apply = (mode) => {
    if (mode === 'vivo') delete root.dataset.motion; else root.dataset.motion = mode;
    document.querySelectorAll('[data-motion-choice]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.motionChoice === mode)));
  };
  apply(read());
  document.querySelectorAll('[data-motion-choice]').forEach((button) => button.addEventListener('click', () => {
    try { localStorage.setItem(KEY, button.dataset.motionChoice); } catch (e) { /* sem armazenamento */ }
    apply(button.dataset.motionChoice);
  }));
  const still = () => root.dataset.motion === 'sem' || window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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
