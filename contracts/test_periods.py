from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase

from .periods import annual_context, calendar_year_periods, contract_year_periods


class AnnualPeriodTests(SimpleTestCase):
    def contract(self, start, end):
        return SimpleNamespace(validity_start=start, validity_end=end)

    def test_two_year_contract_has_two_contract_years_and_three_civil_closings(self):
        contract = self.contract(date(2026, 7, 1), date(2028, 6, 30))
        contract_years = contract_year_periods(contract)
        calendar_years = calendar_year_periods(contract)

        self.assertEqual(
            [(item.start_date, item.end_date) for item in contract_years],
            [
                (date(2026, 7, 1), date(2027, 6, 30)),
                (date(2027, 7, 1), date(2028, 6, 30)),
            ],
        )
        self.assertEqual(
            [(item.start_date, item.end_date) for item in calendar_years],
            [
                (date(2026, 1, 1), date(2026, 12, 31)),
                (date(2027, 1, 1), date(2027, 12, 31)),
                (date(2028, 1, 1), date(2028, 12, 31)),
            ],
        )

    def test_civil_closing_does_not_end_when_contract_ends_midyear(self):
        contract = self.contract(date(2026, 7, 23), date(2027, 7, 22))
        last = calendar_year_periods(contract)[-1]
        self.assertEqual(last.start_date, date(2027, 1, 1))
        self.assertEqual(last.end_date, date(2027, 12, 31))

    def test_contract_up_to_one_year_has_only_one_contract_year(self):
        contract = self.contract(date(2026, 7, 1), date(2027, 6, 30))
        self.assertEqual(len(contract_year_periods(contract)), 1)

    def test_same_date_receives_both_independent_classifications(self):
        contract = self.contract(date(2026, 7, 1), date(2028, 6, 30))
        context = annual_context(contract, date(2027, 8, 10))
        self.assertEqual(context["calendar"].label, "Fechamento 2027")
        self.assertEqual(context["contract"].label, "Ano contratual 2")

    def test_leap_day_start_keeps_periods_contiguous(self):
        contract = self.contract(date(2024, 2, 29), date(2026, 2, 28))
        periods = contract_year_periods(contract)
        self.assertEqual(len(periods), 2)
        self.assertEqual(periods[0].end_date, date(2025, 2, 28))
        self.assertEqual(periods[1].start_date, date(2025, 3, 1))
        self.assertEqual(periods[-1].end_date, date(2026, 2, 28))
