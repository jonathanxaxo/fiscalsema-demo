(() => {
  "use strict";

  // Versão de impressão do relatório: abre a janela de impressão do navegador
  // automaticamente. Nada é gravado pelo sistema; o PDF fica com o usuário.
  if (!document.querySelector("[data-auto-print]")) {
    return;
  }

  const openPrintDialog = () => {
    // Aguarda o navegador pintar o conteudo liberado antes de gerar a previa.
    window.requestAnimationFrame(() => window.print());
  };

  const printWhenPageIsVisible = () => {
    const root = document.documentElement;
    if (!root.classList.contains("fs-verificando")) {
      openPrintDialog();
      return;
    }

    // Uma nova aba pode ficar invisivel por alguns milissegundos enquanto o
    // sistema confirma que a aba de origem continua aberta. Imprimir durante
    // essa verificacao gera paginas em branco no Chrome/Edge.
    const observer = new MutationObserver(() => {
      if (root.classList.contains("fs-verificando")) {
        return;
      }
      observer.disconnect();
      openPrintDialog();
    });
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
  };

  window.addEventListener(
    "load",
    printWhenPageIsVisible,
    { once: true },
  );
})();
