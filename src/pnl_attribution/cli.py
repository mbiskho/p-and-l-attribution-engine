from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .engine import PnLAttributionEngine
from .models import DailyObservation, PeriodReport
from .visualization import (
    render_component_chart,
    render_cumulative_chart,
    render_flow_screenshot,
    render_project_screenshot,
)


def _object(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


def _number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def load_engine(path: Path) -> PnLAttributionEngine:
    with path.open(encoding="utf-8") as source:
        document = _object(json.load(source), "input")

    currency = document.get("currency")
    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("input.currency must be a non-empty string")
    records = document.get("observations")
    if not isinstance(records, list):
        raise ValueError("input.observations must be a JSON array")
    observations = []
    for index, raw_record in enumerate(records):
        record = _object(raw_record, f"observations[{index}]")
        attribution = _object(record.get("attribution"), f"observations[{index}].attribution")
        observations.append(
            DailyObservation(
                date=record.get("date"),
                opening_nav=_number(record.get("opening_nav"), f"observations[{index}].opening_nav"),
                external_flows=_number(
                    record.get("external_flows"),
                    f"observations[{index}].external_flows",
                ),
                closing_nav=_number(record.get("closing_nav"), f"observations[{index}].closing_nav"),
                attribution={
                    component: _number(amount, f"observations[{index}].attribution.{component}")
                    for component, amount in attribution.items()
                },
            )
        )
    return PnLAttributionEngine(
        currency=currency,
        observations=observations,
        continuity_tolerance=_number(document.get("continuity_tolerance", 0.01), "continuity_tolerance"),
    )


def _report_document(report: PeriodReport) -> dict[str, Any]:
    return {
        "currency": report.currency,
        "period": {"start": report.start_date, "end": report.end_date},
        "opening_nav": report.opening_nav,
        "closing_nav": report.closing_nav,
        "external_flows": report.external_flows,
        "total_pnl": report.total_pnl,
        "component_pnl": dict(report.component_pnl),
        "reconciliation_residual": report.reconciliation_residual,
        "observations": [
            {
                "date": item.date,
                "opening_nav": item.opening_nav,
                "external_flows": item.external_flows,
                "closing_nav": item.closing_nav,
                "portfolio_pnl": item.portfolio_pnl,
                "component_pnl": dict(item.component_pnl),
                "reconciliation_residual": item.reconciliation_residual,
                "cumulative_pnl": item.cumulative_pnl,
            }
            for item in report.observations
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile daily portfolio NAV changes to P&L attribution."
    )
    parser.add_argument("input", type=Path, help="path to a daily attribution JSON file")
    parser.add_argument(
        "--format",
        choices=("text", "json", "svg"),
        default="text",
        help="output format: text, JSON, or SVG chart (default: text)",
    )
    parser.add_argument(
        "--chart",
        choices=("components", "cumulative", "project", "flow"),
        default="components",
        help="SVG report: component chart, cumulative chart, project overview, or flow",
    )
    args = parser.parse_args(argv)

    try:
        report = load_engine(args.input).run()
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    if args.format == "json":
        print(json.dumps(_report_document(report), indent=2, sort_keys=True))
    elif args.format == "svg":
        chart_renderers = {
            "components": render_component_chart,
            "cumulative": render_cumulative_chart,
            "project": render_project_screenshot,
            "flow": render_flow_screenshot,
        }
        chart = chart_renderers[args.chart](report)
        print(chart)
    else:
        print(f"Period: {report.start_date} to {report.end_date} ({report.currency})")
        print(f"Opening NAV:          {report.opening_nav:>16,.2f}")
        print(f"External flows:       {report.external_flows:>16,.2f}")
        print(f"Closing NAV:          {report.closing_nav:>16,.2f}")
        print(f"Total portfolio P&L:  {report.total_pnl:>16,.2f}")
        print("\nAttribution")
        for component, amount in sorted(
            report.component_pnl.items(),
            key=lambda item: item[1],
        ):
            print(f"  {component:<28} {amount:>16,.2f}")
        print(f"\nReconciliation residual: {report.reconciliation_residual:,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
