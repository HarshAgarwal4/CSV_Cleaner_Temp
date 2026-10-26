import re
import time
from pathlib import Path
import numpy as np
import pandas as pd

def retry(max_attempts=3, delay=1):
    """
    Automatically retries a function if a temporary error occurs
    (such as a file being temporarily locked by another app).
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as error:
                    if attempt == max_attempts:
                        raise error
                    print(f"Attempt {attempt} failed ({error}). Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator

@retry(max_attempts=3, delay=1)
def clean_csv(input_file, output_file):
    """
    Cleans a CSV file in 4 clear, sequential steps:
      1. Trim and strip whitespace
      2. Remove duplicate rows
      3. Remove null / empty rows
      4. Save the cleaned CSV
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output files must be different.")

    # Step 0: Read the original CSV file
    df = pd.read_csv(input_path, skip_blank_lines=False)
    original_rows = len(df)

    # -----------------------------------------------------
    # STEP 1: Trim & Strip Whitespace
    # -----------------------------------------------------
    # 1a. Strip spaces from column headers (e.g. ' full_name ' -> 'full_name')
    df.columns = df.columns.str.strip()

    # 1b. Helper function to clean text values
    def clean_text(value):
        if isinstance(value, str):
            # Remove HTML tags (e.g. <b>text</b> -> text)
            value = re.sub(r"<[^>]+>", "", value)
            # Collapse multiple spaces into one and strip leading/trailing spaces
            return re.sub(r"\s+", " ", value).strip()
        return value

    # Apply text cleanup to every text/string column
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        df[col] = df[col].map(clean_text)

    # -----------------------------------------------------
    # STEP 2: Remove Duplicates
    # -----------------------------------------------------
    # Since whitespace was stripped in Step 1, rows that only
    # differed by spaces are now exact matches and will be removed.
    rows_before_dedup = len(df)
    df = df.drop_duplicates()
    duplicates_removed = rows_before_dedup - len(df)

    # -----------------------------------------------------
    # STEP 3: Remove Nulls
    # -----------------------------------------------------
    # 3a. Convert empty strings and common placeholder words into real NaN
    null_markers = ["", "NULL", "null", "None", "none", "nan", "NaN", "NA", "N/A"]
    df = df.replace(null_markers, np.nan)
    df = df.replace(r"^\s*$", np.nan, regex=True)

    # 3b. Drop any rows containing missing/null values
    rows_before_null = len(df)
    df = df.dropna()
    null_rows_removed = rows_before_null - len(df)

    # -----------------------------------------------------
    # STEP 4: Save Cleaned CSV
    # -----------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    # Return a simple summary dictionary
    return {
        "original_rows": original_rows,
        "duplicates_removed": duplicates_removed,
        "null_rows_removed": null_rows_removed,
        "cleaned_rows": len(df),
        "total_removed_rows": original_rows - len(df),
        "output_file": str(output_path),
        "remaining_nulls": df.isna().sum().to_dict(),
    }


# =========================================================
# 3. COMPARISON & REPORTING
# =========================================================
def compare_csv(original_file, cleaned_file):
    """
    Compares the original and cleaned CSV files and displays a summary.
    """
    original = pd.read_csv(original_file, skip_blank_lines=False)
    cleaned = pd.read_csv(cleaned_file, skip_blank_lines=False)

    print("\n" + "=" * 50)
    print("           CSV CLEANING REPORT")
    print("=" * 50)
    print(f"Original Rows       : {len(original)}")
    print(f"Cleaned Rows        : {len(cleaned)}")
    print(f"Total Rows Removed  : {len(original) - len(cleaned)}")
    print("=" * 50)

    print("\nRemaining Missing Values in Cleaned File:")
    print(cleaned.isna().sum().to_string())

    print("\nPreview of First 5 Cleaned Rows:")
    print(cleaned.head())
    print("=" * 50)


# =========================================================
# 4. SCRIPT ENTRY POINT
# =========================================================
if __name__ == "__main__":
    try:
        summary = clean_csv(
            input_file="Data/sample_review.csv",
            output_file="Data/cleaned_review.csv",
        )
        compare_csv(
            original_file="Data/sample_review.csv",
            cleaned_file="Data/cleaned_review.csv",
        )
        print("\nSummary Result Dictionary:")
        print(summary)
    except Exception as e:
        print("Error during CSV cleaning:", e)
