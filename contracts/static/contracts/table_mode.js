(() => {
  const grid = document.querySelector('[data-table-mode]');
  if (!grid) return;
  const feedback = document.getElementById('table-feedback');
  const search = document.getElementById('table-search');
  const cells = () => Array.from(grid.querySelectorAll('tbody td'));

  cells().forEach((cell) => cell.tabIndex = 0);

  grid.addEventListener('keydown', (event) => {
    const cell = event.target.closest('td');
    if (!cell) return;
    const row = cell.parentElement;
    const rows = Array.from(row.parentElement.rows);
    const column = cell.cellIndex;
    const rowIndex = rows.indexOf(row);
    let target = null;
    if (event.key === 'ArrowLeft') target = row.cells[column - 1];
    if (event.key === 'ArrowRight') target = row.cells[column + 1];
    if (event.key === 'ArrowUp' && rows[rowIndex - 1]) target = rows[rowIndex - 1].cells[column];
    if (event.key === 'ArrowDown' && rows[rowIndex + 1]) target = rows[rowIndex + 1].cells[column];
    if (event.key === 'Enter') {
      const action = row.querySelector('[data-primary-action]');
      if (action) action.click();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'c') {
      event.preventDefault();
      navigator.clipboard?.writeText(cell.innerText.trim());
      feedback.textContent = 'Conteúdo da célula copiado.';
      return;
    }
    if (target) { event.preventDefault(); target.focus(); }
  });

  grid.addEventListener('paste', (event) => {
    const text = event.clipboardData?.getData('text')?.trim();
    if (!text || !search) return;
    event.preventDefault();
    search.value = text.replace(/[\r\n\t]+/g, ' ').slice(0, 200);
    search.focus();
    feedback.textContent = 'Texto colado no filtro. Pressione Enter para pesquisar. Nenhum dado foi alterado.';
  });

  grid.querySelectorAll('thead th').forEach((header) => {
    header.style.position = 'sticky';
    const handle = document.createElement('span');
    handle.className = 'column-resizer';
    handle.setAttribute('aria-hidden', 'true');
    header.appendChild(handle);
    handle.addEventListener('pointerdown', (event) => {
      event.preventDefault();
      const startX = event.clientX;
      const startWidth = header.offsetWidth;
      const move = (moveEvent) => {
        header.style.width = `${Math.max(80, startWidth + moveEvent.clientX - startX)}px`;
        header.style.minWidth = header.style.width;
      };
      const stop = () => {
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', stop);
      };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', stop);
    });
  });
})();
