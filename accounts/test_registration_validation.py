from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .forms import (
    AccountPasswordChangeForm,
    AccountSetPasswordForm,
    AdministrativeFiscalCreationForm,
    FiscalRegistrationForm,
)
from .models import AccountStatus, User
from .tests import VALID_PASSWORD


class ClearRegistrationValidationTests(TestCase):
    def registration_data(self, **overrides):
        data = {
            "full_name": "Pessoa de Teste",
            "email": "pessoa.teste@example.local",
            "organization_name": "DEMO",
            "sector_name": "CSTI",
            "phone": "",
            "password1": VALID_PASSWORD,
            "password2": VALID_PASSWORD,
        }
        data.update(overrides)
        return data

    def test_invalid_email_explains_expected_format_without_creating_account(self):
        response = self.client.post(
            reverse("accounts:register"), self.registration_data(email="email-invalido")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Informe um e-mail válido, como nome@dominio.gov.br."
        )
        self.assertFalse(User.objects.exists())

    def test_missing_email_has_specific_message(self):
        response = self.client.post(
            reverse("accounts:register"), self.registration_data(email="")
        )
        self.assertContains(response, "Informe o e-mail.")
        self.assertFalse(User.objects.exists())

    def test_email_is_trimmed_normalized_and_duplicate_is_rejected(self):
        User.objects.create_user(
            email="pessoa.teste@example.local",
            full_name="Conta existente",
            password=VALID_PASSWORD,
        )
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(email="  PESSOA.TESTE@EXAMPLE.LOCAL "),
        )
        self.assertContains(response, "Já existe uma conta com este e-mail.")
        self.assertEqual(User.objects.count(), 1)

    def test_password_form_reports_every_missing_complexity_requirement(self):
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(password1="abcdef", password2="abcdef"),
        )
        self.assertContains(response, "Inclua pelo menos uma letra maiúscula.")
        self.assertContains(response, "Inclua pelo menos um número.")
        self.assertContains(
            response,
            "Inclua pelo menos um caractere especial, como !, @, # ou $.",
        )
        self.assertNotContains(response, "Inclua pelo menos uma letra minúscula.")

    def test_password_validator_reports_only_the_missing_case_requirement(self):
        user = User(email="validacao@example.local", full_name="Validação")
        with self.assertRaises(ValidationError) as raised:
            validate_password("senha1!", user=user)
        self.assertIn("Inclua pelo menos uma letra maiúscula.", raised.exception.messages)
        self.assertNotIn("Inclua pelo menos uma letra minúscula.", raised.exception.messages)
        self.assertNotIn("Inclua pelo menos um número.", raised.exception.messages)
        self.assertNotIn(
            "Inclua pelo menos um caractere especial, como !, @, # ou $.",
            raised.exception.messages,
        )

    def test_registration_password_inputs_expose_six_to_twenty_four_limits(self):
        form = FiscalRegistrationForm()
        for field_name in ("password1", "password2"):
            self.assertEqual(form.fields[field_name].widget.attrs["minlength"], 6)
            self.assertEqual(form.fields[field_name].widget.attrs["maxlength"], 24)

    def test_administrative_creation_uses_same_email_and_password_rules(self):
        form = AdministrativeFiscalCreationForm(
            data=self.registration_data(email="invalido", organization="")
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            list(form.errors["email"]),
            ["Informe um e-mail válido, como nome@dominio.gov.br."],
        )
        self.assertEqual(form.fields["password1"].widget.attrs["maxlength"], 24)

    def test_change_and_reset_forms_expose_the_same_password_limits(self):
        user = User.objects.create_user(
            email="troca@example.local",
            full_name="Troca de Senha",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
        )
        forms = (AccountPasswordChangeForm(user), AccountSetPasswordForm(user))
        for form in forms:
            for field_name in ("new_password1", "new_password2"):
                self.assertEqual(form.fields[field_name].widget.attrs["minlength"], 6)
                self.assertEqual(form.fields[field_name].widget.attrs["maxlength"], 24)
