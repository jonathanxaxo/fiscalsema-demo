# Decisões — Sprint 43

- **Não mudar regra de negócio.** O problema era de tela (o botão não era
  encontrado), não de permissão; por isso a correção só deixa o caminho
  visível e explicado.
- **`?servico=` só pré-marca.** O valor é ignorado se não for número ou se
  não for um serviço homologado da própria OS (o formulário só oferece esses);
  a validação no serviço continua sendo a proteção real.
