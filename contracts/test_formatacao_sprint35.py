"""Formatação e CPF/CNPJ trazidos do FiscalSema Light (Sprint 35). Dados fictícios."""

from django.contrib.staticfiles import finders
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase

from contracts.forms import ContractForm, clean_tax_id, format_tax_id
from contracts.models import Contract
from contracts.tests import contract_data


class CpfCnpjTests(TestCase):
    def form_data(self, tax_id):
        data = contract_data(supplier_tax_id=tax_id)
        for key in ("signature_date", "validity_start", "validity_end"):
            data[key] = data[key].isoformat()
        data["original_value"] = "100000,00"
        return data

    def test_accepts_with_or_without_punctuation_and_keeps_digits(self):
        for typed in ("12.345.678/0001-99", "12345678000199", " 12 345 678 0001 99 "):
            form = ContractForm(data=self.form_data(typed))
            form.is_valid()
            self.assertNotIn("supplier_tax_id", form.errors, typed)
            self.assertEqual(form.cleaned_data["supplier_tax_id"], "12345678000199")
        form = ContractForm(data=self.form_data("123.456.789-01"))
        form.is_valid()
        self.assertEqual(form.cleaned_data["supplier_tax_id"], "12345678901")

    def test_wrong_length_is_refused_with_clear_message(self):
        form = ContractForm(data=self.form_data("12.345.678/0001"))
        self.assertFalse(form.is_valid())
        self.assertIn("CPF com 11 dígitos ou CNPJ com 14", str(form.errors["supplier_tax_id"]))

    def test_mask_attributes_and_formatted_initial(self):
        form = ContractForm(instance=Contract(pk=1, supplier_tax_id="12345678000199"))
        self.assertEqual(form.initial["supplier_tax_id"], "12.345.678/0001-99")
        html = str(form["supplier_tax_id"])
        self.assertIn("data-tax-id", html)
        self.assertIn('inputmode="numeric"', html)
        self.assertEqual(format_tax_id("12345678901"), "123.456.789-01")
        self.assertEqual(clean_tax_id("123.456.789-01"), "12345678901")

    def test_screen_script_has_mask_hash_and_autosubmit(self):
        script = open(finders.find("core/js/app.js"), encoding="utf-8").read()
        for piece in ("[data-tax-id]", "revealHashTarget", "select[data-autosubmit]"):
            self.assertIn(piece, script)


class BarraTests(SimpleTestCase):
    def render(self, value):
        return Template("{% load formatacao %}{{ v|barra }}").render(Context({"v": value}))

    def test_bar_width_is_clamped_between_0_and_100(self):
        self.assertEqual(self.render(35), "35")
        self.assertEqual(self.render("12,6"), "13")
        self.assertEqual(self.render(130), "100")
        self.assertEqual(self.render(-5), "0")
        self.assertEqual(self.render(None), "0")
        self.assertEqual(self.render("texto"), "0")
