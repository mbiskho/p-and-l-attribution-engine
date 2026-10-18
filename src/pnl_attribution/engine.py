from __future__ import annotations

import math
from collections.abc import Sequence

from .models import DailyObservation, DailyResult, PeriodReport


class PnLAttributionEngine:
    def __init__(
        self,
        currency: str,
        observations: Sequence[DailyObservation],
        continuity_tolerance: float = 0.01,
    ) -> None:
        if not isinstance(currency, str) or not currency.strip():
            raise ValueError("currency must be a non-empty string")
        self.currency = currency.strip()
        self.observations = tuple(observations)
        if not self.observations:
            raise ValueError("at least one daily observation is required")
        if isinstance(continuity_tolerance, bool) or not isinstance(
            continuity_tolerance, (int, float)
        ):
            raise ValueError("continuity_tolerance must be a non-negative number")
        self.continuity_tolerance = float(continuity_tolerance)
        if not math.isfinite(self.continuity_tolerance) or self.continuity_tolerance < 0:
            raise ValueError("continuity_tolerance must be a non-negative finite number")
        self._validate_sequence()

    def _validate_sequence(self) -> None:
        dates = [observation.date for observation in self.observations]
        if any(
            "Reconciliation residual" in observation.attribution
            for observation in self.observations
        ):
            raise ValueError(
                "'Reconciliation residual' is reserved for the engine-calculated difference"
            )
        if len(dates) != len(set(dates)):
            raise ValueError("observation dates must be unique")
        if dates != sorted(dates):
            raise ValueError("observations must be sorted by date")
        for previous, current in zip(self.observations, self.observations[1:]):
            difference = abs(current.opening_nav - previous.closing_nav)
            if difference > self.continuity_tolerance:
                raise ValueError(
                    f"opening NAV on {current.date} does not match closing NAV on "
                    f"{previous.date}: difference {difference:.2f} exceeds "
                    f"tolerance {self.continuity_tolerance:.2f}"
                )

    def run(self) -> PeriodReport:
        daily_results: list[DailyResult] = []
        period_components: dict[str, list[float]] = {}
        total_pnl_values: list[float] = []
        flow_values: list[float] = []
        residual_values: list[float] = []
        cumulative_pnl = 0.0

        for observation in self.observations:
            portfolio_pnl = math.fsum(
                (
                    observation.closing_nav,
                    -observation.opening_nav,
                    -observation.external_flows,
                )
            )
            component_pnl = dict(observation.attribution)
            residual = portfolio_pnl - math.fsum(component_pnl.values())
            cumulative_pnl = math.fsum((cumulative_pnl, portfolio_pnl))

            for component, amount in component_pnl.items():
                period_components.setdefault(component, []).append(amount)
            period_components.setdefault("Reconciliation residual", []).append(residual)
            total_pnl_values.append(portfolio_pnl)
            flow_values.append(observation.external_flows)
            residual_values.append(residual)
            daily_results.append(
                DailyResult(
                    date=observation.date,
                    opening_nav=observation.opening_nav,
                    external_flows=observation.external_flows,
                    closing_nav=observation.closing_nav,
                    portfolio_pnl=portfolio_pnl,
                    component_pnl=component_pnl,
                    reconciliation_residual=residual,
                    cumulative_pnl=cumulative_pnl,
                )
            )

        aggregated_components = {
            component: math.fsum(amounts)
            for component, amounts in period_components.items()
        }
        total_pnl = math.fsum(total_pnl_values)
        if not math.isclose(
            math.fsum(aggregated_components.values()),
            total_pnl,
            rel_tol=1e-12,
            abs_tol=1e-7,
        ):
            raise ArithmeticError("period attribution does not reconcile to total P&L")

        first = self.observations[0]
        last = self.observations[-1]
        return PeriodReport(
            currency=self.currency,
            start_date=first.date,
            end_date=last.date,
            opening_nav=first.opening_nav,
            closing_nav=last.closing_nav,
            external_flows=math.fsum(flow_values),
            total_pnl=total_pnl,
            component_pnl=aggregated_components,
            reconciliation_residual=math.fsum(residual_values),
            observations=tuple(daily_results),
        )
