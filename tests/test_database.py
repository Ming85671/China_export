import unittest

from src.database import build_export_query


class DatabaseQueryTests(unittest.TestCase):
    def test_query_uses_axs_table_required_columns_and_country_scope(self):
        query = " ".join(build_export_query().split())

        self.assertIn("FROM axs", query)
        self.assertIn("load_start_date", query)
        self.assertIn("voy_intake_mt", query)
        self.assertIn("COMMODITY", query)
        self.assertIn("discharge_country", query)
        self.assertIn("load_country = 'China'", query)
        self.assertIn("discharge_country <> 'China'", query)
        self.assertIn("ORDER BY load_start_date DESC", query)


if __name__ == "__main__":
    unittest.main()
