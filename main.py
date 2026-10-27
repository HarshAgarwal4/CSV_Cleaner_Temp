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


def export_cleaned_data(data, output_path, export_format="csv"):
    """
    Simple function to export cleaned data (DataFrame or CSV file) to CSV, JSON, or both.
    
    Parameters:
      data: pd.DataFrame or path to a CSV file.
      output_path: Target file path.
      export_format: 'csv', 'json', or 'both'.
    """
    # 1. Get DataFrame (load from file if path given)
    if isinstance(data, (str, Path)):
        df = pd.read_csv(data)
    else:
        df = data

    # 2. Prepare output path and folder
    output_path = Path(output_path)
    base_path = output_path.with_suffix("")
    base_path.parent.mkdir(parents=True, exist_ok=True)

    # 3. Handle export format
    fmt = export_format.lower().strip()

    if fmt == "csv":
        csv_file = base_path.with_suffix(".csv")
        df.to_csv(csv_file, index=False)
        return csv_file

    elif fmt == "json":
        json_file = base_path.with_suffix(".json")
        df.to_json(json_file, orient="records", indent=2)
        return json_file

    elif fmt == "both":
        csv_file = base_path.with_suffix(".csv")
        json_file = base_path.with_suffix(".json")
        df.to_csv(csv_file, index=False)
        df.to_json(json_file, orient="records", indent=2)
        return {"csv": csv_file, "json": json_file}

    else:
        raise ValueError("export_format must be 'csv', 'json', or 'both'")


@retry(max_attempts=3, delay=1)
def clean_csv(input_file, output_file, export_format="csv"):
    """
    Cleans a CSV file in 4 clear, sequential steps:
      1. Trim and strip whitespace
      2. Remove duplicate rows
      3. Remove null / empty rows
      4. Export cleaned data to CSV, JSON, or both
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
    df.columns = df.columns.str.strip()

    def clean_text(value):
        if isinstance(value, str):
            # Remove HTML tags (e.g. <b>text</b> -> text)
            value = re.sub(r"<[^>]+>", "", value)
            # Collapse multiple spaces into one and strip leading/trailing spaces
            return re.sub(r"\s+", " ", value).strip()
        return value

    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        df[col] = df[col].map(clean_text)

    # -----------------------------------------------------
    # STEP 2: Remove Duplicates
    # -----------------------------------------------------
    rows_before_dedup = len(df)
    df = df.drop_duplicates()
    duplicates_removed = rows_before_dedup - len(df)

    # -----------------------------------------------------
    # STEP 3: Remove Nulls
    # -----------------------------------------------------
    null_markers = ["", "NULL", "null", "None", "none", "nan", "NaN", "NA", "N/A"]
    df = df.replace(null_markers, np.nan)
    df = df.replace(r"^\s*$", np.nan, regex=True)

    rows_before_null = len(df)
    df = df.dropna()
    null_rows_removed = rows_before_null - len(df)

    # -----------------------------------------------------
    # STEP 4: Save / Export Cleaned Data
    # -----------------------------------------------------
    exported = export_cleaned_data(df, output_path=output_path, export_format=export_format)

    return {
        "original_rows": original_rows,
        "duplicates_removed": duplicates_removed,
        "null_rows_removed": null_rows_removed,
        "cleaned_rows": len(df),
        "total_removed_rows": original_rows - len(df),
        "output_file": str(output_path),
        "exported_files": exported,
        "remaining_nulls": df.isna().sum().to_dict(),
    }


# =========================================================
# 3. COMPARISON & REPORTING
# =========================================================
def compare_csv(original_file, cleaned_file):
    """
    Compares the original and cleaned files (CSV or JSON) and displays a summary.
    """
    original_path = Path(original_file)
    cleaned_path = Path(cleaned_file)

    original = pd.read_csv(original_path, skip_blank_lines=False)
    if cleaned_path.suffix.lower() == ".json":
        cleaned = pd.read_json(cleaned_path)
    else:
        cleaned = pd.read_csv(cleaned_path, skip_blank_lines=False)

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
        # Clean and export to both CSV and JSON formats
        summary = clean_csv(
            input_file="Data/sample_review.csv",
            output_file="Data/cleaned_review.csv",
            export_format="both",
        )
        compare_csv(
            original_file="Data/sample_review.csv",
            cleaned_file="Data/cleaned_review.csv",
        )
        print("\nSummary Result Dictionary:")
        print(summary)
    except Exception as e:
        print("Error during CSV cleaning:", e)
