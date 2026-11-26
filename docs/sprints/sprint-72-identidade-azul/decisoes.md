# Decisões — Sprint 72

1. **Variáveis com nomes históricos.** O CSS já usava variáveis (`--green-950`,
   `--green-800`...). Os valores passaram a ser azuis e os nomes foram mantidos
   para evitar uma refatoração ampla em centenas de regras. Um comentário no
   `app.css` registra isso.
2. **Verde só para sucesso.** Foram criadas `--success`, `--success-bg` e
   `--success-ink`, usadas por `badge-success`, `status-success`,
   `attention-success`, `attention-ok`, `notice` e `countdown-success`. A
   situação "Homologado" também continua verde. Erro, perigo e atenção não
   mudaram.
3. **Logotipo sem perder a geometria.** A lupa, o círculo, a verificação e o
   cabo mantêm as mesmas coordenadas da Sprint 46 (testes existentes). Foram
   acrescentados a folha de documento com canto dobrado e as linhas de texto
   vistas através da lente. O amarelo do cabo deu lugar ao branco.
4. **Imagem institucional.** Foi usada a imagem enviada pelo responsável
   (SEMA, brasão e Governo de Mato Grosso), em 1698 × 543 px. A pedido dele, o
   fundo branco atrás de "Governo de Mato Grosso" foi tornado transparente
   (inclusive o miolo das letras) e as bordas das letras foram suavizadas.
   Nada foi recortado, separado, redesenhado ou recolorido; o quadrado do
   brasão ficou intacto. Na tela, a imagem só é redimensionada
   proporcionalmente (`height: auto`).
5. **Rodapé fora da impressão.** O rodapé fica oculto em `@media print` para
   não alterar os PDFs dos relatórios corrigidos na Sprint 70.
6. **Sem carregamento tardio.** A imagem tem 67 KB; o carregamento imediato
   evita espaço vazio no rodapé.
7. **Sem nova dependência.** O teste confere largura, altura e transparência
   pelo cabeçalho do PNG, com a biblioteca padrão do Python.
8. **Aviso de dados fictícios fora das telas.** Por decisão expressa do
   responsável em 26/11/2026, a faixa amarela "AMBIENTE DE DEMONSTRAÇÃO", a
   nota do menu lateral, o aviso do rodapé e a frase abaixo do login foram
   removidos. O aviso passa a ser dado na apresentação e no início do vídeo,
   na voz do autor. A regra do `CLAUDE.md` e do `AGENTS.md` foi atualizada.
   Continuam: uso exclusivo de dados fictícios, a faixa de homologação (em
   outro ambiente) e os avisos de privacidade do Arise sobre não enviar dados
   reais ao serviço de IA externo.
9. **Selo de perfil em azul claro.** O nome do perfil ("Fiscal Titular" e
   demais) e os rótulos de alcance ("Somente leitura", "Visão geral") usam a
   nova classe `badge-profile`; o selo de situação do contrato continua verde
   (sucesso).
