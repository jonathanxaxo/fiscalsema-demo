(() => {
  const body = document.body;
  const menuButton = document.querySelector('.menu-toggle');
  const closeMenu = () => {
    body.classList.remove('menu-open');
    menuButton?.setAttribute('aria-expanded', 'false');
  };

  menuButton?.addEventListener('click', () => {
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
