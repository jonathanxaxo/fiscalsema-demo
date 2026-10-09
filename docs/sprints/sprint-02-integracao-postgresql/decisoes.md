# Decisões da Sprint 02

1. O autor do commit local foi obtido do último commit do projeto original; não
   foi inventada uma identidade.
2. O PostgreSQL 9.6 presente no Windows foi rejeitado por incompatibilidade com
   Django 5.2 e para evitar interferência em serviço preexistente.
3. O PostgreSQL de testes será 17 Alpine, temporário, com banco e usuário que
   contenham `demo`, senha aleatória e porta vinculada somente ao loopback.
4. O contêiner será removido após os testes, inclusive quando houver falha.
5. Nenhuma proteção de `settings_demo.py` será desativada para facilitar o teste.
