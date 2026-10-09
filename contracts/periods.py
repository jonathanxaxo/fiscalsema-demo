from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class AnnualPeriod:
    kind: str
    ordinal: int
    label: str
    start_date: date
    end_date: date

    def contains(self, value):
        return self.start_date <= value <= self.end_date


def _anniversary(value, years):
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        # O ciclo iniciado em 29/02 completa um ano após o fim de fevereiro.
        return date(value.year + years, 3, 1)


def contract_year_periods(contract):
    """Return anniversary-based periods clipped to the contract validity."""
    periods = []
    ordinal = 1
    start = contract.validity_start
    while start <= contract.validity_end:
        next_start = _anniversary(contract.validity_start, ordinal)
        end = min(next_start - timedelta(days=1), contract.validity_end)
        periods.append(
            AnnualPeriod(
                kind="CONTRACT_YEAR",
                ordinal=ordinal,
                label=f"Ano contratual {ordinal}",
                start_date=start,
                end_date=end,
            )
        )
        start = next_start
        ordinal += 1
    return tuple(periods)


def calendar_year_periods(contract):
    """Return full official calendar years touched by the contract."""
    periods = []
    for ordinal, year in enumerate(
        range(contract.validity_start.year, contract.validity_end.year + 1), start=1
    ):
        periods.append(
            AnnualPeriod(
                kind="CALENDAR_YEAR",
                ordinal=ordinal,
                label=f"Fechamento {year}",
                start_date=date(year, 1, 1),
                end_date=date(year, 12, 31),
            )
        )
    return tuple(periods)


def period_for_date(periods, value):
    if not value:
        return None
    return next((period for period in periods if period.contains(value)), None)


def annual_context(contract, value):
    """Expose both official dimensions; neither is inferred from the other."""
    return {
        "calendar": period_for_date(calendar_year_periods(contract), value),
        "contract": period_for_date(contract_year_periods(contract), value),
    }
