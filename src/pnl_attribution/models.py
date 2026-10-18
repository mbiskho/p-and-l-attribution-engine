from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Mapping


def _finite_number(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")
    return number


def _component_amounts(values: Mapping[str, float]) -> Mapping[str, float]:
    if not isinstance(values, Mapping) or not values:
        raise ValueError("attribution must be a non-empty object of components and amounts")
    cleaned: dict[str, float] = {}
    for component, amount in values.items():
        if not isinstance(component, str) or not component.strip():
            raise ValueError("attribution contains an empty or invalid component name")
        name = component.strip()
        if name in cleaned:
            raise ValueError(f"duplicate attribution component: {name}")
        cleaned[name] = _finite_number(amount, f"attribution[{name!r}]")
    return MappingProxyType(cleaned)


@dataclass(frozen=True)
class DailyObservation:
    date: str
    opening_nav: float
    external_flows: float
    closing_nav: float
    attribution: Mapping[str, float]

    def __post_init__(self) -> None:
        if not isinstance(self.date, str):
            raise ValueError("date must be an ISO date string")
        try:
            parsed_date = date.fromisoformat(self.date)
        except ValueError as error:
            raise ValueError(f"date must be an ISO date (YYYY-MM-DD): {self.date!r}") from error
        if parsed_date.isoformat() != self.date:
            raise ValueError(f"date must use YYYY-MM-DD format: {self.date!r}")
        object.__setattr__(self, "opening_nav", _finite_number(self.opening_nav, "opening_nav"))
        object.__setattr__(self, "external_flows", _finite_number(self.external_flows, "external_flows"))
        object.__setattr__(self, "closing_nav", _finite_number(self.closing_nav, "closing_nav"))
        if self.opening_nav < 0 or self.closing_nav < 0:
            raise ValueError("opening_nav and closing_nav cannot be negative")
        object.__setattr__(self, "attribution", _component_amounts(self.attribution))


@dataclass(frozen=True)
class DailyResult:
    date: str
    opening_nav: float
    external_flows: float
    closing_nav: float
    portfolio_pnl: float
    component_pnl: Mapping[str, float]
    reconciliation_residual: float
    cumulative_pnl: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_pnl", MappingProxyType(dict(self.component_pnl)))


@dataclass(frozen=True)
class PeriodReport:
    currency: str
    start_date: str
    end_date: str
    opening_nav: float
    closing_nav: float
    external_flows: float
    total_pnl: float
    component_pnl: Mapping[str, float]
    reconciliation_residual: float
    observations: tuple[DailyResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_pnl", MappingProxyType(dict(self.component_pnl)))

