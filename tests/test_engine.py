import unittest
from xml.etree import ElementTree

from pnl_attribution import DailyObservation, PnLAttributionEngine
from pnl_attribution.visualization import render_component_chart, render_cumulative_chart
from pnl_attribution.visualization import render_flow_screenshot, render_project_screenshot


class PnLAttributionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.observations = [
            DailyObservation(
                "2026-01-05",
                1000,
                100,
                1120,
                {"Equity": 90, "Income": 20, "Fees": -5},
            ),
            DailyObservation(
                "2026-01-06",
                1120,
                -20,
                1100,
                {"Equity": -15, "Income": 3, "Fees": -2},
            ),
        ]

    def test_excludes_external_flows_from_daily_and_period_pnl(self) -> None:
        report = PnLAttributionEngine("USD", self.observations).run()

        self.assertEqual(report.observations[0].portfolio_pnl, 20)
        self.assertEqual(report.observations[1].portfolio_pnl, 0)
        self.assertEqual(report.total_pnl, 20)
        self.assertEqual(report.external_flows, 80)
        self.assertEqual(report.closing_nav - report.opening_nav - report.external_flows, 20)

    def test_exposes_daily_and_period_reconciliation_residual(self) -> None:
        report = PnLAttributionEngine("USD", self.observations).run()

        self.assertEqual(report.observations[0].reconciliation_residual, -85)
        self.assertEqual(report.observations[1].reconciliation_residual, 14)
        self.assertEqual(report.reconciliation_residual, -71)
        self.assertAlmostEqual(sum(report.component_pnl.values()), report.total_pnl)

    def test_aggregates_component_amounts_and_cumulative_pnl(self) -> None:
        report = PnLAttributionEngine("USD", self.observations).run()

        self.assertEqual(report.component_pnl["Equity"], 75)
        self.assertEqual(report.component_pnl["Income"], 23)
        self.assertEqual(report.component_pnl["Fees"], -7)
        self.assertEqual(report.observations[1].cumulative_pnl, 20)

    def test_rejects_duplicate_or_unsorted_dates(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            PnLAttributionEngine("USD", [self.observations[0], self.observations[0]])
        with self.assertRaisesRegex(ValueError, "sorted"):
            PnLAttributionEngine("USD", list(reversed(self.observations)))

    def test_rejects_nav_continuity_break(self) -> None:
        broken = DailyObservation("2026-01-06", 1121, 0, 1120, {"Equity": -1})
        with self.assertRaisesRegex(ValueError, "does not match closing NAV"):
            PnLAttributionEngine("USD", [self.observations[0], broken])

    def test_reserves_reconciliation_residual_component_name(self) -> None:
        observation = DailyObservation(
            "2026-01-05",
            100,
            0,
            100,
            {"Reconciliation residual": 0},
        )
        with self.assertRaisesRegex(ValueError, "is reserved"):
            PnLAttributionEngine("USD", [observation])

    def test_rejects_invalid_dates_and_non_finite_amounts(self) -> None:
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            DailyObservation("2026-1-5", 100, 0, 100, {"Equity": 0})
        with self.assertRaisesRegex(ValueError, "finite"):
            DailyObservation("2026-01-05", 100, 0, 100, {"Equity": float("inf")})

    def test_renders_both_standalone_charts(self) -> None:
        report = PnLAttributionEngine("USD", self.observations).run()

        components = render_component_chart(report)
        cumulative = render_cumulative_chart(report)

        self.assertIn("Where did P&amp;L come from?", components)
        self.assertIn("Reconciliation residual", components)
        self.assertTrue(components.endswith("</svg>"))
        self.assertIn("2026-01-05 to 2026-01-06", components)
        self.assertIn("P&amp;L through the period", cumulative)
        self.assertIn("2026-01-06", cumulative)
        self.assertTrue(cumulative.endswith("</svg>"))
        ElementTree.fromstring(components)
        ElementTree.fromstring(cumulative)

    def test_renders_white_project_and_flow_screenshots_with_charts(self) -> None:
        report = PnLAttributionEngine("USD", self.observations).run()

        project = render_project_screenshot(report)
        flow = render_flow_screenshot(report)

        self.assertIn('fill="#ffffff"', project)
        self.assertIn("P&amp;L Attribution Engine", project)
        self.assertIn("Period attribution by component", project)
        self.assertIn('fill="#ffffff"', flow)
        self.assertIn("From portfolio ledger to explainable P&amp;L", flow)
        self.assertIn("Cumulative P&amp;L output", flow)
        self.assertIn("external flows", flow)
        self.assertIn("daily", flow)
        self.assertIn("trail, JSON and charts", flow)
        ElementTree.fromstring(project)
        ElementTree.fromstring(flow)


if __name__ == "__main__":
    unittest.main()
