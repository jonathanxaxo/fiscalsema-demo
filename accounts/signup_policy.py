"""Política de quem pode criar conta nova (Sprint 27).

Configurada só por variáveis de ambiente (sem dados pessoais no código):

- ``ALLOWED_SIGNUP_DOMAINS``: domínios institucionais inteiros;
- ``ALLOWED_SIGNUP_EMAILS``: exceções individuais, endereço exato
  (não libera o domínio do endereço);
- ``GOOGLE_REQUIRE_HOSTED_DOMAIN``: quando ligado, contas do domínio
  institucional precisam vir do Google Workspace desse domínio (``hd``).

Sem nenhuma das listas, ninguém cria conta nova. A política vale apenas para
contas novas; cadastros existentes não são afetados.
"""

from django.conf import settings

from .managers import UserManager


def _domains():
    return {item.strip().casefold().lstrip("@") for item in settings.ALLOWED_SIGNUP_DOMAINS if item.strip()}


def _emails():
    return {UserManager.normalize_login_email(item) for item in settings.ALLOWED_SIGNUP_EMAILS if item.strip()}


def is_configured():
    return bool(_domains() or _emails())


def is_signup_allowed(email, *, hosted_domain=None):
    """``hosted_domain`` é o ``hd`` do Google (``None`` fora do login Google)."""
    email = UserManager.normalize_login_email(email or "")
    if "@" not in email:
        return False
    if email in _emails():
        return True
    domain = email.rsplit("@", 1)[1]
    if domain not in _domains():
        return False
    if hosted_domain is not None and settings.GOOGLE_REQUIRE_HOSTED_DOMAIN:
        return (hosted_domain or "").casefold() == domain
    return True
