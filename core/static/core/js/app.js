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
