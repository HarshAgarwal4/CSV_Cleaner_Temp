import contextlib
import io
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

from main import clean_csv, retry

# Import clean_dataframe while silencing top-level Streamlit CLI output in tests
with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
    from app import clean_dataframe


class TestCleanerApplication(unittest.TestCase):
    """
    Unit and integration tests for CSV cleaning functionality
    with comprehensive logging.
    """

    def setUp(self):
        logger.info("Setting up test case: %s", self._testMethodName)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()
        logger.info("Cleaned up test case: %s\n", self._testMethodName)

    # =========================================================
    # Tests for main.py (clean_csv)
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

        logger.info("Input file created at: %s", input_file)
        logger.info("Calling clean_csv...")

        summary = clean_csv(str(input_file), str(output_file))

        logger.info("Clean CSV summary returned: %s", summary)

        # Assertions
        self.assertTrue(output_file.exists(), "Cleaned output file should exist.")
        self.assertEqual(summary["original_rows"], 6, "Expected 6 original rows.")
        self.assertEqual(summary["duplicates_removed"], 1, "Expected 1 duplicate row removed.")
        self.assertEqual(summary["null_rows_removed"], 3, "Expected 3 rows with nulls removed.")
        self.assertEqual(summary["cleaned_rows"], 2, "Expected 2 cleaned rows remaining.")

        cleaned_df = pd.read_csv(output_file)
        logger.info("Cleaned DataFrame preview:\n%s", cleaned_df)

        # Validate headers stripped
        self.assertListEqual(
            list(cleaned_df.columns),
            ["customer_id", "full_name", "email", "spend"],
            "Column headers should be stripped.",
        )

        # Validate remaining customers (CUST-001 and CUST-003)
        remaining_ids = list(cleaned_df["customer_id"])
        self.assertIn("CUST-001", remaining_ids)
        self.assertIn("CUST-003", remaining_ids)

        # Validate text normalization on CUST-003
        charlie_name = cleaned_df.loc[cleaned_df["customer_id"] == "CUST-003", "full_name"].values[0]
        self.assertEqual(charlie_name, "Charlie Brown", "Multiple spaces should be normalized.")

        logger.info("test_clean_csv_full_pipeline passed successfully.")

    def test_clean_csv_same_input_output_error(self):
        """Test clean_csv raises ValueError when input and output paths are identical."""
        logger.info("Executing test_clean_csv_same_input_output_error...")

        file_path = self.temp_dir_path / "same_file.csv"
        file_path.write_text("col1,col2\n1,2\n", encoding="utf-8")

        with self.assertRaises(ValueError) as context:
            clean_csv(str(file_path), str(file_path))

        logger.info("Successfully caught expected ValueError: %s", context.exception)

    def test_retry_decorator(self):
        """Test that retry decorator retries on failure and succeeds if transient."""
        logger.info("Executing test_retry_decorator...")

        attempts = 0

        @retry(max_attempts=3, delay=0.01)
        def flaky_function():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                logger.warning("Simulating transient failure on attempt %d", attempts)
                raise IOError("Temporary I/O lock")
            return "SUCCESS"

        result = flaky_function()
        logger.info("Flaky function succeeded with result: %s after %d attempts", result, attempts)
        self.assertEqual(result, "SUCCESS")
        self.assertEqual(attempts, 2)

    # =========================================================
    # Tests for app.py (clean_dataframe)
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

        logger.info("Cleaned columns: %s", list(cleaned_df.columns))
        logger.info("Cleaned values in 'name': %s", list(cleaned_df["name"]))

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

        logger.info("Deduplication summary: %s", summary)
        logger.info("Removed records:\n%s", removed_df)

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
        logger.info("Mode 'any' cleaned rows: %d", len(cleaned_any))
        self.assertEqual(len(cleaned_any), 1)
        self.assertEqual(sum_any["null_rows_removed"], 2)

        # Mode: ALL
        cleaned_all, _, sum_all = clean_dataframe(df, null_mode="all", remove_nulls=True)
        logger.info("Mode 'all' cleaned rows: %d", len(cleaned_all))
        self.assertEqual(len(cleaned_all), 2)
        self.assertEqual(sum_all["null_rows_removed"], 1)

        # Mode: REQUIRED column
        cleaned_req, _, sum_req = clean_dataframe(
            df, null_mode="required", required_column="col2", remove_nulls=True
        )
        logger.info("Mode 'required' (col2) cleaned rows: %d", len(cleaned_req))
        self.assertEqual(len(cleaned_req), 2)
        self.assertEqual(sum_req["null_rows_removed"], 1)

        logger.info("test_clean_dataframe_null_modes passed.")

    def test_clean_dataframe_placeholder_nulls(self):
        """Test that placeholder values ('NULL', 'None', 'NA', empty string) are treated as nulls."""
        logger.info("Executing test_clean_dataframe_placeholder_nulls...")

        # Distinct row ids to ensure rows are not dropped as duplicates
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

        logger.info("Placeholder test summary: %s", summary)
        logger.info("Removed records:\n%s", removed_df)
        self.assertEqual(len(cleaned_df), 1)
        self.assertEqual(cleaned_df.iloc[0]["val"], "valid")
        self.assertEqual(summary["null_rows_removed"], 5)
        self.assertEqual(summary["total_removed"], 5)
        logger.info("test_clean_dataframe_placeholder_nulls passed.")


if __name__ == "__main__":
    logger.info("Starting Cleaner Application Test Suite...")
    unittest.main(verbosity=2)

