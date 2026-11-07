(() => {
  "use strict";

  // Versão de impressão do relatório: abre a janela de impressão do navegador
  // automaticamente. Nada é gravado pelo sistema; o PDF fica com o usuário.
  if (!document.body.hasAttribute("data-auto-print")) {
    return;
  }

  window.addEventListener(
    "load",
    () => {
      window.print();
    },
    { once: true },
  );
})();
