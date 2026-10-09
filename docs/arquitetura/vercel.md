# Arquitetura da demonstração

```text
Navegador
  -> HTTPS da Vercel
  -> Python Function / Django WSGI
  -> PostgreSQL demo com TLS e pooler
```

Arquivos estáticos são servidos pelo WhiteNoise. Logs técnicos seguem para a
saída padrão da função e eventos de auditoria ficam no PostgreSQL demo.

Não fazem parte desta arquitetura: VM, Docker, Nginx, Gunicorn, volumes locais,
PostgreSQL real ou diretórios `/opt/fiscalsema-light`.
