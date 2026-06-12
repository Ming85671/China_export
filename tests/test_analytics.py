import unittest

import pandas as pd

from src.analytics import (
    aggregate_by_period,
    apply_filters,
    calculate_metrics,
    normalize_shipments,
    top_commodities,
)


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame(
            {
                "load_start_date": [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-08",
                    "2026-02-01",
                    None,
                ],
                "voy_intake_mt": [100, 200, 300, 400, 500],
                "COMMODITY": ["Coal", "Grain", "Coal", "Steel", "Coal"],
                "discharge_country": ["Japan", "Korea", "Japan", "Korea", "Japan"],
            }
        )

    def test_normalize_shipments_removes_invalid_rows(self):
        result = normalize_shipments(self.raw)

        self.assertEqual(len(result), 4)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["load_start_date"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(result["voy_intake_mt"]))

    def test_apply_filters_uses_selected_commodities_and_destinations(self):
        normalized = normalize_shipments(self.raw)

        result = apply_filters(
            normalized,
            start_date="2026-01-01",
            end_date="2026-01-31",
            commodities=["Coal"],
            destinations=["Japan"],
        )

        self.assertEqual(result["voy_intake_mt"].sum(), 400)
        self.assertEqual(result["COMMODITY"].unique().tolist(), ["Coal"])

    def test_aggregate_by_period_supports_daily_weekly_and_monthly(self):
        normalized = normalize_shipments(self.raw)

        daily = aggregate_by_period(normalized, "Daily")
        weekly = aggregate_by_period(normalized, "Weekly")
        monthly = aggregate_by_period(normalized, "Monthly")

        self.assertEqual(daily["voy_intake_mt"].sum(), 1000)
        self.assertEqual(len(daily), 4)
        self.assertEqual(len(weekly), 3)
        self.assertEqual(monthly["voy_intake_mt"].tolist(), [600, 400])

    def test_aggregate_by_period_keeps_selected_commodities_separate(self):
        normalized = normalize_shipments(self.raw)

        result = aggregate_by_period(
            normalized,
            "Monthly",
            group_columns=["COMMODITY"],
        )

        january = result[result["period"] == pd.Timestamp("2026-01-01")]
        self.assertEqual(
            dict(zip(january["COMMODITY"], january["voy_intake_mt"])),
            {"Coal": 400, "Grain": 200},
        )

    def test_weekly_aggregation_excludes_the_current_incomplete_week(self):
        normalized = normalize_shipments(
            pd.DataFrame(
                {
                    "load_start_date": [
                        "2026-05-25",
                        "2026-06-01",
                        "2026-06-08",
                    ],
                    "voy_intake_mt": [100, 200, 50],
                    "COMMODITY": ["Coal", "Coal", "Coal"],
                    "discharge_country": ["Japan", "Japan", "Japan"],
                }
            )
        )

        result = aggregate_by_period(normalized, "Weekly", as_of="2026-06-12")

        self.assertEqual(
            result["period"].tolist(),
            [pd.Timestamp("2026-05-25"), pd.Timestamp("2026-06-01")],
        )
        self.assertEqual(result["voy_intake_mt"].tolist(), [100, 200])

    def test_calculate_metrics_follows_current_filter(self):
        normalized = normalize_shipments(self.raw)
        coal_only = normalized[normalized["COMMODITY"] == "Coal"]

        metrics = calculate_metrics(coal_only, "Monthly")

        self.assertEqual(metrics["total_volume"], 400)
        self.assertEqual(metrics["commodity_count"], 1)
        self.assertEqual(metrics["largest_commodity"], "Coal")

    def test_weekly_period_change_uses_the_latest_two_completed_weeks(self):
        normalized = normalize_shipments(
            pd.DataFrame(
                {
                    "load_start_date": [
                        "2026-05-25",
                        "2026-06-01",
                        "2026-06-08",
                    ],
                    "voy_intake_mt": [100, 200, 50],
                    "COMMODITY": ["Coal", "Coal", "Coal"],
                    "discharge_country": ["Japan", "Japan", "Japan"],
                }
            )
        )

        metrics = calculate_metrics(normalized, "Weekly", as_of="2026-06-12")

        self.assertEqual(metrics["period_change_pct"], 100)
        self.assertEqual(metrics["total_volume"], 350)

    def test_top_commodities_returns_only_ranked_commodities_without_other(self):
        normalized = normalize_shipments(self.raw)

        result = top_commodities(normalized, limit=2)

        self.assertEqual(set(result["COMMODITY"]), {"Steel", "Coal"})
        self.assertEqual(result["voy_intake_mt"].tolist(), [400, 400])
        self.assertNotIn("Other", result["COMMODITY"].tolist())

if __name__ == "__main__":
    unittest.main()
