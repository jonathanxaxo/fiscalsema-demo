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
