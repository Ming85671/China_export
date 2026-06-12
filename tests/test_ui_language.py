import re
import unittest
from pathlib import Path


class UiLanguageTests(unittest.TestCase):
    def test_app_static_ui_copy_contains_no_chinese_characters(self):
        app_source = Path("app.py").read_text(encoding="utf-8")

        self.assertIsNone(re.search(r"[\u4e00-\u9fff]", app_source))

    def test_app_includes_dashboard_visual_system(self):
        app_source = Path("app.py").read_text(encoding="utf-8")

        for expected_token in (
            "--color-primary",
            "--color-background",
            "dashboard-eyebrow",
            "dashboard-hero",
            "section-kicker",
            "prefers-reduced-motion",
        ):
            with self.subTest(expected_token=expected_token):
                self.assertIn(expected_token, app_source)

    def test_shipment_trend_reserves_space_for_legend_and_y_axis_headroom(self):
        app_source = Path("app.py").read_text(encoding="utf-8")

        for expected_token in (
            "def apply_trend_chart_style",
            'orientation="h"',
            'xanchor="right"',
            "nice_axis_upper_bound(max_volume)",
            'tickmode="linear"',
            "dtick=nice_axis_tick_step(y_axis_upper_bound)",
            "figure.add_hline(",
            "y=y_axis_upper_bound",
            'line_color="#E8EEF7"',
            "apply_trend_chart_style(trend_chart, trend)",
        ):
            with self.subTest(expected_token=expected_token):
                self.assertIn(expected_token, app_source)

        self.assertNotIn("margin=dict(l=18, r=18, t=70, b=18)", app_source)


if __name__ == "__main__":
    unittest.main()
