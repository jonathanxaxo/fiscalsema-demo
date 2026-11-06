from decimal import Decimal

from django.test import SimpleTestCase

from core.templatetags.formatacao import cnpj_cpf, quantidade


class QuantidadeFilterTests(SimpleTestCase):
    def test_removes_insignificant_zeros_keeping_two_places(self):
        self.assertEqual(quantidade(Decimal("20.0000")), "20,00")
        self.assertEqual(quantidade(Decimal("1200.0000")), "1.200,00")
        self.assertEqual(quantidade(Decimal("12.5000")), "12,50")

    def test_never_hides_significant_places(self):
        self.assertEqual(quantidade(Decimal("12.3456")), "12,3456")
        self.assertEqual(quantidade(Decimal("0.0010")), "0,001")

    def test_empty_values_are_preserved(self):
        self.assertIsNone(quantidade(None))
        self.assertEqual(quantidade(""), "")


class CnpjCpfFilterTests(SimpleTestCase):
    def test_formats_cnpj_and_cpf(self):
        self.assertEqual(cnpj_cpf("12345678000199"), "12.345.678/0001-99")
        self.assertEqual(cnpj_cpf("12345678901"), "123.456.789-01")

    def test_unknown_lengths_are_left_unchanged(self):
        self.assertEqual(cnpj_cpf("123"), "123")
        self.assertEqual(cnpj_cpf(""), "")
