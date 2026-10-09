import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class MaximumLengthValidator:
    def __init__(self, max_length=24):
        self.max_length = max_length

    def validate(self, password, user=None):
        if len(password) > self.max_length:
            raise ValidationError(
                _("A senha deve ter no máximo %(max_length)d caracteres."),
                code="password_too_long",
                params={"max_length": self.max_length},
            )

    def get_help_text(self):
        return _("Sua senha deve ter no máximo %(max_length)d caracteres.") % {
            "max_length": self.max_length
        }


class PasswordComplexityValidator:
    requirements = (
        (r"[A-Z]", _("Inclua pelo menos uma letra maiúscula."), "password_missing_uppercase"),
        (r"[a-z]", _("Inclua pelo menos uma letra minúscula."), "password_missing_lowercase"),
        (r"[0-9]", _("Inclua pelo menos um número."), "password_missing_number"),
        (
            r"[^A-Za-z0-9]",
            _("Inclua pelo menos um caractere especial, como !, @, # ou $."),
            "password_missing_special",
        ),
    )

    def validate(self, password, user=None):
        errors = [
            ValidationError(message, code=code)
            for pattern, message, code in self.requirements
            if not re.search(pattern, password)
        ]
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Sua senha deve conter letra maiúscula, letra minúscula, número e "
            "caractere especial."
        )


class PasswordDifferentFromEmailValidator:
    message = _("A senha deve ser diferente do e-mail.")

    def validate(self, password, user=None):
        if user and user.email and password.casefold() == user.email.casefold():
            raise ValidationError(self.message, code="password_same_as_email")

    def get_help_text(self):
        return self.message
