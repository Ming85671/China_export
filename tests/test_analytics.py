import unittest

import pandas as pd

from src.analytics import (
    aggregate_by_period,
    apply_filters,
    calculate_metrics,
    nice_axis_tick_step,
    nice_axis_upper_bound,
    normalize_shipments,
    prepare_weekly_average_comparison,
    weekly_historical_stats,
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

    def test_nice_axis_upper_bound_is_a_clean_tick_above_the_maximum(self):
        self.assertEqual(nice_axis_upper_bound(2_340_791), 2_500_000)
        self.assertEqual(nice_axis_upper_bound(2_500_000), 3_000_000)

    def test_nice_axis_tick_step_places_a_tick_at_the_upper_bound(self):
        upper_bound = nice_axis_upper_bound(2_340_791)

        self.assertEqual(nice_axis_tick_step(upper_bound), 500_000)
        self.assertEqual(upper_bound % nice_axis_tick_step(upper_bound), 0)

    def test_top_commodities_returns_only_ranked_commodities_without_other(self):
        normalized = normalize_shipments(self.raw)

        result = top_commodities(normalized, limit=2)

        self.assertEqual(set(result["COMMODITY"]), {"Steel", "Coal"})
        self.assertEqual(result["voy_intake_mt"].tolist(), [400, 400])
        self.assertNotIn("Other", result["COMMODITY"].tolist())

    def test_prepare_weekly_average_comparison_aligns_five_year_history_to_selected_window(self):
        normalized = normalize_shipments(
            pd.DataFrame(
                {
                    "load_start_date": [
                        "2020-01-06",
                        "2021-01-04",
                        "2022-01-03",
                        "2023-01-02",
                        "2024-01-01",
                        "2025-01-06",
                        "2026-01-05",
                        "2026-01-12",
                        "2026-06-08",
                    ],
                    "voy_intake_mt": [70, 140, 210, 280, 350, 420, 490, 560, 700],
                    "COMMODITY": ["Coal"] * 9,
                    "discharge_country": ["Japan"] * 9,
                }
            )
        )

        result = prepare_weekly_average_comparison(
            normalized,
            start_date="2025-06-13",
            end_date="2026-01-18",
            as_of="2026-06-13",
        )

        self.assertEqual(sorted(result["year"].unique()), [2021, 2022, 2023, 2024, 2025, 2026])
        self.assertEqual(result[result["year"] == 2026]["daily_average_mt"].tolist(), [70.0, 80.0])
        self.assertNotIn(2020, result["year"].tolist())
        self.assertNotIn(700 / 7, result["daily_average_mt"].tolist())

    def test_prepare_weekly_average_comparison_excludes_incomplete_current_week(self):
        normalized = normalize_shipments(
            pd.DataFrame(
                {
                    "load_start_date": ["2026-06-01", "2026-06-08"],
                    "voy_intake_mt": [700, 1400],
                    "COMMODITY": ["Coal", "Coal"],
                    "discharge_country": ["Japan", "Japan"],
                }
            )
        )

        result = prepare_weekly_average_comparison(
            normalized,
            start_date="2026-06-01",
            end_date="2026-06-13",
            as_of="2026-06-13",
        )

        self.assertEqual(result["week_start"].tolist(), [pd.Timestamp("2026-06-01")])
        self.assertEqual(result["daily_average_mt"].tolist(), [100.0])

    def test_prepare_weekly_average_comparison_calculates_four_week_average(self):
        normalized = normalize_shipments(
            pd.DataFrame(
                {
                    "load_start_date": pd.date_range("2026-01-05", periods=4, freq="7D"),
                    "voy_intake_mt": [70, 140, 210, 280],
                    "COMMODITY": ["Coal"] * 4,
                    "discharge_country": ["Japan"] * 4,
                }
            )
        )

        result = prepare_weekly_average_comparison(
            normalized,
            start_date="2026-01-01",
            end_date="2026-02-01",
            as_of="2026-06-13",
        )

        self.assertEqual(result["four_week_average_mt"].tolist(), [10.0, 15.0, 20.0, 25.0])

    def test_weekly_historical_stats_uses_prior_years_only(self):
        weekly = pd.DataFrame(
            {
                "year": [2024, 2025, 2026],
                "week_seq": [0, 0, 0],
                "x_date": pd.to_datetime(["2026-01-05"] * 3),
                "daily_average_mt": [10.0, 30.0, 100.0],
            }
        )

        result = weekly_historical_stats(weekly, comparison_year=2026)

        self.assertEqual(result.iloc[0]["min"], 10.0)
        self.assertEqual(result.iloc[0]["median"], 20.0)
        self.assertEqual(result.iloc[0]["max"], 30.0)

if __name__ == "__main__":
    unittest.main()
