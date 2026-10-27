import contextlib
import io
import json
import logging
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging for test execution
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("TestCleaner")

# Suppress streamlit scriptrunner warning logs during test runs
logging.getLogger("streamlit").setLevel(logging.ERROR)

from main import clean_csv, export_cleaned_data as main_export_cleaned_data, retry

# Import clean_dataframe and export_cleaned_data while silencing top-level Streamlit CLI output in tests
with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
    from app import clean_dataframe, export_cleaned_data as app_export_cleaned_data


class TestCleanerApplication(unittest.TestCase):
    """
    Unit and integration tests for CSV cleaning and export functionality.
    """

    def setUp(self):
        logger.info("Setting up test case: %s", self._testMethodName)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()
        logger.info("Cleaned up test case: %s\n", self._testMethodName)

    # =========================================================
    # Tests for main.py (clean_csv & export_cleaned_data)
    # =========================================================

    def test_clean_csv_full_pipeline(self):
        """Test full clean_csv pipeline: trimming, deduping, and null removal."""
        logger.info("Executing test_clean_csv_full_pipeline...")

        # Create sample dirty CSV
        raw_csv_content = (
            " customer_id , full_name , email , spend \n"
            "CUST-001,<b>Alice Smith</b>,alice@example.com,100.50\n"
            "CUST-001,Alice Smith,alice@example.com,100.50\n"  # Duplicate after HTML/space strip
            "CUST-002,Bob Jones  ,bob@example.com,NULL\n"       # Null placeholder
            "CUST-003,Charlie   Brown,charlie@example.com,50.00\n"
            "CUST-004,David None,none,75.00\n"                  # Text null in email
            "CUST-005,Eva Green,eva@example.com,   \n"          # Blank space null
        )

        input_file = self.temp_dir_path / "raw_input.csv"
        output_file = self.temp_dir_path / "cleaned_output.csv"
        input_file.write_text(raw_csv_content, encoding="utf-8")

        summary = clean_csv(str(input_file), str(output_file))

        # Assertions
        self.assertTrue(output_file.exists(), "Cleaned output file should exist.")
        self.assertEqual(summary["original_rows"], 6)
        self.assertEqual(summary["duplicates_removed"], 1)
        self.assertEqual(summary["null_rows_removed"], 3)
        self.assertEqual(summary["cleaned_rows"], 2)

        cleaned_df = pd.read_csv(output_file)
        self.assertListEqual(
            list(cleaned_df.columns),
            ["customer_id", "full_name", "email", "spend"],
        )
        self.assertEqual(len(cleaned_df), 2)
        logger.info("test_clean_csv_full_pipeline passed successfully.")

    def test_clean_csv_export_format_both(self):
        """Test clean_csv with export_format='both' to export CSV and JSON."""
        logger.info("Executing test_clean_csv_export_format_both...")

        raw_csv_content = (
            "id,name,role\n"
            "1,Alice,Engineer\n"
            "2,Bob,Designer\n"
        )
        input_file = self.temp_dir_path / "simple_input.csv"
        output_file = self.temp_dir_path / "simple_cleaned.csv"
        input_file.write_text(raw_csv_content, encoding="utf-8")

        summary = clean_csv(str(input_file), str(output_file), export_format="both")

        csv_file = self.temp_dir_path / "simple_cleaned.csv"
        json_file = self.temp_dir_path / "simple_cleaned.json"

        self.assertTrue(csv_file.exists(), "Cleaned CSV file must exist.")
        self.assertTrue(json_file.exists(), "Cleaned JSON file must exist.")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["name"], "Alice")
        logger.info("test_clean_csv_export_format_both passed successfully.")

    def test_clean_csv_same_input_output_error(self):
        """Test clean_csv raises ValueError when input and output paths are identical."""
        logger.info("Executing test_clean_csv_same_input_output_error...")

        file_path = self.temp_dir_path / "same_file.csv"
        file_path.write_text("col1,col2\n1,2\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            clean_csv(str(file_path), str(file_path))

    def test_retry_decorator(self):
        """Test that retry decorator retries on failure and succeeds if transient."""
        logger.info("Executing test_retry_decorator...")

        attempts = 0

        @retry(max_attempts=3, delay=0.01)
        def flaky_function():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise IOError("Temporary I/O lock")
            return "SUCCESS"

        result = flaky_function()
        self.assertEqual(result, "SUCCESS")
        self.assertEqual(attempts, 2)

    def test_main_export_cleaned_data_csv_and_json(self):
        """Test main_export_cleaned_data exporting DataFrame to CSV, JSON, and both."""
        logger.info("Executing test_main_export_cleaned_data_csv_and_json...")

        df = pd.DataFrame({
            "product_id": [101, 102],
            "title": ["Widget A", "Widget B"],
        })

        out_csv = self.temp_dir_path / "export_test.csv"
        out_json = self.temp_dir_path / "export_test.json"
        out_both = self.temp_dir_path / "export_both"

        # CSV
        res_csv = main_export_cleaned_data(df, out_csv, export_format="csv")
        self.assertTrue(res_csv.exists())
        self.assertEqual(len(pd.read_csv(res_csv)), 2)

        # JSON
        res_json = main_export_cleaned_data(df, out_json, export_format="json")
        self.assertTrue(res_json.exists())
        with open(res_json, "r", encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)), 2)

        # Both
        res_both = main_export_cleaned_data(df, out_both, export_format="both")
        self.assertTrue(res_both["csv"].exists())
        self.assertTrue(res_both["json"].exists())
        logger.info("test_main_export_cleaned_data_csv_and_json passed.")

    def test_main_export_cleaned_data_from_file_path(self):
        """Test main_export_cleaned_data when passing a CSV file path as input."""
        logger.info("Executing test_main_export_cleaned_data_from_file_path...")

        source_file = self.temp_dir_path / "source.csv"
        source_file.write_text("item,qty\napple,5\nbanana,10\n", encoding="utf-8")

        target_json = self.temp_dir_path / "converted.json"
        res = main_export_cleaned_data(source_file, target_json, export_format="json")

        self.assertTrue(res.exists())
        with open(res, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["item"], "apple")
        logger.info("test_main_export_cleaned_data_from_file_path passed.")

    def test_main_export_cleaned_data_invalid_format(self):
        """Test main_export_cleaned_data raises ValueError on invalid format."""
        logger.info("Executing test_main_export_cleaned_data_invalid_format...")

        df = pd.DataFrame({"a": [1]})
        with self.assertRaises(ValueError):
            main_export_cleaned_data(df, self.temp_dir_path / "test.csv", export_format="unsupported")

    # =========================================================
    # Tests for app.py (clean_dataframe & export_cleaned_data)
    # =========================================================

    def test_clean_dataframe_whitespace_and_html(self):
        """Test clean_dataframe trimming, normalization, and HTML tag removal."""
        logger.info("Executing test_clean_dataframe_whitespace_and_html...")

        df = pd.DataFrame({
            " name ": ["  John   Doe  ", "<b>Jane</b>", "Bob"],
            " city ": [" New   York ", "<i>London</i>", "Paris  "],
        })

        cleaned_df, removed_df, summary = clean_dataframe(
            df,
            trim_spaces=True,
            normalize_spaces=True,
            strip_html=True,
            remove_duplicates=False,
            remove_nulls=False,
        )

        self.assertListEqual(list(cleaned_df.columns), ["name", "city"])
        self.assertEqual(cleaned_df.loc[0, "name"], "John Doe")
        self.assertEqual(cleaned_df.loc[1, "name"], "Jane")
        self.assertEqual(cleaned_df.loc[0, "city"], "New York")
        self.assertEqual(cleaned_df.loc[1, "city"], "London")
        logger.info("test_clean_dataframe_whitespace_and_html passed.")

    def test_clean_dataframe_deduplication(self):
        """Test clean_dataframe deduplication and tracking in removed_df."""
        logger.info("Executing test_clean_dataframe_deduplication...")

        df = pd.DataFrame({
            "id": ["1", "2", "1"],
            "value": ["Alpha", "Beta", "Alpha"],
        })

        cleaned_df, removed_df, summary = clean_dataframe(
            df,
            remove_duplicates=True,
            remove_nulls=False,
        )

        self.assertEqual(len(cleaned_df), 2)
        self.assertEqual(summary["duplicates_removed"], 1)
        self.assertEqual(len(removed_df), 1)
        self.assertIn("Duplicate row", removed_df["Removal Reason"].iloc[0])
        logger.info("test_clean_dataframe_deduplication passed.")

    def test_clean_dataframe_null_modes(self):
        """Test clean_dataframe with null_mode 'any', 'all', and 'required'."""
        logger.info("Executing test_clean_dataframe_null_modes...")

        df = pd.DataFrame({
            "col1": ["Valid", np.nan, np.nan],
            "col2": ["Valid", "Partial", np.nan],
        })

        # Mode: ANY (strict)
        cleaned_any, _, sum_any = clean_dataframe(df, null_mode="any", remove_nulls=True)
        self.assertEqual(len(cleaned_any), 1)

        # Mode: ALL
        cleaned_all, _, sum_all = clean_dataframe(df, null_mode="all", remove_nulls=True)
        self.assertEqual(len(cleaned_all), 2)

        # Mode: REQUIRED column
        cleaned_req, _, sum_req = clean_dataframe(
            df, null_mode="required", required_column="col2", remove_nulls=True
        )
        self.assertEqual(len(cleaned_req), 2)
        logger.info("test_clean_dataframe_null_modes passed.")

    def test_clean_dataframe_placeholder_nulls(self):
        """Test that placeholder values ('NULL', 'None', 'NA', empty string) are treated as nulls."""
        logger.info("Executing test_clean_dataframe_placeholder_nulls...")

        df = pd.DataFrame({
            "id": ["1", "2", "3", "4", "5", "6"],
            "val": ["valid", "NULL", "none", "N/A", "", "   "],
        })

        cleaned_df, removed_df, summary = clean_dataframe(
            df,
            treat_text_nulls=True,
            remove_nulls=True,
            null_mode="any",
        )

        self.assertEqual(len(cleaned_df), 1)
        self.assertEqual(cleaned_df.iloc[0]["val"], "valid")
        self.assertEqual(summary["null_rows_removed"], 5)
        logger.info("test_clean_dataframe_placeholder_nulls passed.")

    def test_app_export_cleaned_data_csv_json_both(self):
        """Test app_export_cleaned_data generates bytes for CSV, JSON, and both."""
        logger.info("Executing test_app_export_cleaned_data_csv_json_both...")

        df = pd.DataFrame({
            "user_id": [1, 2],
            "username": ["alex", "taylor"],
        })

        # CSV export (bytes)
        csv_bytes = app_export_cleaned_data(df, export_format="csv")
        self.assertIsInstance(csv_bytes, bytes)
        self.assertIn(b"user_id,username", csv_bytes)

        # JSON export (bytes)
        json_bytes = app_export_cleaned_data(df, export_format="json")
        self.assertIsInstance(json_bytes, bytes)
        records = json.loads(json_bytes.decode("utf-8"))
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["username"], "alex")

        # Both export (dict of bytes)
        both_bytes = app_export_cleaned_data(df, export_format="both")
        self.assertIn("csv", both_bytes)
        self.assertIn("json", both_bytes)
        self.assertIsInstance(both_bytes["csv"], bytes)
        self.assertIsInstance(both_bytes["json"], bytes)

        # Invalid format
        with self.assertRaises(ValueError):
            app_export_cleaned_data(df, export_format="unknown")

        logger.info("test_app_export_cleaned_data_csv_json_both passed.")


if __name__ == "__main__":
    logger.info("Starting Cleaner Application Test Suite...")
    unittest.main(verbosity=2)
