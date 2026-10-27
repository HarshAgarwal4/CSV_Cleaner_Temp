import re
from io import BytesIO
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st


# =========================================================
# 1. CORE CSV CLEANING FUNCTION
# =========================================================
def clean_dataframe(
    original_df,
    trim_spaces=True,
    normalize_spaces=True,
    strip_html=False,
    remove_duplicates=True,
    remove_nulls=True,
    null_mode="any",  # "any", "all", or "required"
    required_column=None,
    treat_text_nulls=True,
):
    """
    Cleans a DataFrame following the exact 4-step pipeline:
      1. Trim and strip whitespace
      2. Remove duplicate rows
      3. Remove null / empty values
      4. Prepare cleaned results
    """
    df = original_df.copy()
    removed_records = []
    original_rows = len(df)

    # -----------------------------------------------------
    # STEP 1: Trim & Strip Whitespace
    # -----------------------------------------------------
    if trim_spaces or normalize_spaces:
        # Strip spaces from column headers (e.g. ' name ' -> 'name')
        df.columns = df.columns.str.strip()

    def clean_cell(value):
        if isinstance(value, str):
            if strip_html:
                value = re.sub(r"<[^>]+>", "", value)
            if normalize_spaces:
                value = re.sub(r"\s+", " ", value).strip()
            elif trim_spaces:
                value = value.strip()
            return value
        return value

    # Apply text cleaning across all text columns
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        df[col] = df[col].map(clean_cell)

    # -----------------------------------------------------
    # STEP 2: Remove Duplicates
    # -----------------------------------------------------
    duplicates_removed = 0
    if remove_duplicates:
        dup_mask = df.duplicated(keep="first")
        if dup_mask.any():
            dup_df = df[dup_mask].copy()
            dup_df["Removal Reason"] = "Duplicate row (after whitespace trimming)"
            removed_records.append(dup_df)
            duplicates_removed = int(dup_mask.sum())
            df = df[~dup_mask].copy()

    # -----------------------------------------------------
    # STEP 3: Remove Null Values
    # -----------------------------------------------------
    null_rows_removed = 0
    # Convert blank strings and placeholder words into real NaN
    df = df.replace(r"^\s*$", np.nan, regex=True)
    if treat_text_nulls:
        null_markers = ["", "NULL", "null", "None", "none", "nan", "NaN", "NA", "N/A"]
        df = df.replace(null_markers, np.nan)

    if remove_nulls:
        if null_mode == "required" and required_column:
            null_mask = df[required_column].isna()
            reason = f"Missing required column: {required_column}"
        elif null_mode == "all":
            null_mask = df.isna().all(axis=1)
            reason = "Fully empty row (all values null)"
        else:  # "any"
            null_mask = df.isna().any(axis=1)
            reason = "Contains null / missing values"

        if null_mask.any():
            null_df = df[null_mask].copy()
            null_df["Removal Reason"] = reason
            removed_records.append(null_df)
            null_rows_removed = int(null_mask.sum())
            df = df[~null_mask].copy()

    # -----------------------------------------------------
    # STEP 4: Build Results & Summary
    # -----------------------------------------------------
    cleaned_df = df.reset_index(drop=True)

    if removed_records:
        removed_df = pd.concat(removed_records, ignore_index=True)
    else:
        removed_df = pd.DataFrame(columns=list(original_df.columns) + ["Removal Reason"])

    summary = {
        "original_rows": original_rows,
        "cleaned_rows": len(cleaned_df),
        "duplicates_removed": duplicates_removed,
        "null_rows_removed": null_rows_removed,
        "total_removed": original_rows - len(cleaned_df),
    }

    return cleaned_df, removed_df, summary


# =========================================================
# 2. CORE EXPORT FUNCTION (CSV, JSON, BOTH)
# =========================================================
def export_cleaned_data(df, export_format="csv"):
    """
    Simple function to export cleaned DataFrame to CSV or JSON format for download.
    
    Parameters:
      df: Cleaned pandas DataFrame.
      export_format: 'csv', 'json', or 'both'.

    Returns:
      Bytes of CSV/JSON data or a dict {'csv': bytes, 'json': bytes} if 'both'.
    """
    fmt = export_format.lower().strip()

    if fmt == "csv":
        return df.to_csv(index=False).encode("utf-8")
    elif fmt == "json":
        return df.to_json(orient="records", indent=2).encode("utf-8")
    elif fmt == "both":
        return {
            "csv": df.to_csv(index=False).encode("utf-8"),
            "json": df.to_json(orient="records", indent=2).encode("utf-8"),
        }
    else:
        raise ValueError("export_format must be 'csv', 'json', or 'both'")


# =========================================================
# 3. STREAMLIT USER INTERFACE
# =========================================================
st.set_page_config(page_title="CSV Cleaner Pro", page_icon="🧹", layout="wide")

st.title("🧹 CSV Cleaner Pro")
st.markdown("A simple, clean pipeline: **1. Trim & Strip** ➔ **2. Remove Duplicates** ➔ **3. Remove Nulls** ➔ **4. Save / Download**")

# Upload CSV
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is None:
    st.info("👆 Please upload a CSV file to get started.")
else:
    # Read uploaded CSV
    original_df = pd.read_csv(uploaded_file, skip_blank_lines=False)

    # Sidebar settings
    with st.sidebar:
        st.header("⚙️ Pipeline Settings")

        st.markdown("### 1️⃣ Trim & Strip")
        trim_spaces = st.checkbox("Trim leading/trailing spaces", value=True)
        normalize_spaces = st.checkbox("Normalize inner extra spaces", value=True)
        strip_html = st.checkbox("Strip HTML tags", value=False)

        st.markdown("### 2️⃣ Remove Duplicates")
        remove_duplicates = st.checkbox("Remove duplicate rows", value=True)

        st.markdown("### 3️⃣ Remove Null Values")
        remove_nulls = st.checkbox("Remove null values", value=True)
        null_mode = "any"
        required_column = None
        treat_text_nulls = True

        if remove_nulls:
            null_choice = st.radio(
                "Null Removal Rule:",
                [
                    "Drop row if ANY value is null (Strict)",
                    "Drop row only if ALL values are null",
                    "Drop row if a specific column is null",
                ],
            )
            if null_choice == "Drop row if ANY value is null (Strict)":
                null_mode = "any"
            elif null_choice == "Drop row only if ALL values are null":
                null_mode = "all"
            else:
                null_mode = "required"
                required_column = st.selectbox("Select required column:", original_df.columns)

            treat_text_nulls = st.checkbox(
                "Treat 'NULL', 'None', 'NA', and empty cells as null",
                value=True,
            )

    # Show original data overview
    st.subheader("📄 Original Dataset")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Rows", f"{len(original_df):,}")
    col2.metric("Total Columns", f"{len(original_df.columns):,}")
    col3.metric("Total Missing Cells", f"{int(original_df.isna().sum().sum()):,}")

    st.dataframe(original_df.head(10), use_container_width=True)

    # Run cleaning button
    if st.button("🧹 Clean CSV Now", type="primary", use_container_width=True):
        cleaned_df, removed_df, summary = clean_dataframe(
            original_df=original_df,
            trim_spaces=trim_spaces,
            normalize_spaces=normalize_spaces,
            strip_html=strip_html,
            remove_duplicates=remove_duplicates,
            remove_nulls=remove_nulls,
            null_mode=null_mode,
            required_column=required_column,
            treat_text_nulls=treat_text_nulls,
        )

        st.session_state["cleaned_df"] = cleaned_df
        st.session_state["removed_df"] = removed_df
        st.session_state["summary"] = summary
        st.success("✅ CSV cleaned successfully!")

    # Display results if available
    if "cleaned_df" in st.session_state:
        cleaned_df = st.session_state["cleaned_df"]
        removed_df = st.session_state["removed_df"]
        summary = st.session_state["summary"]

        st.divider()
        st.subheader("✨ Cleaning Results")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Original Rows", f"{summary['original_rows']:,}")
        m2.metric("Cleaned Rows", f"{summary['cleaned_rows']:,}")
        m3.metric("Duplicates Removed", f"{summary['duplicates_removed']:,}")
        m4.metric("Null Rows Removed", f"{summary['null_rows_removed']:,}")

        # Tabs for details
        tab_preview, tab_removed, tab_quality, tab_download = st.tabs(
            [
                "🔍 Preview Cleaned Data",
                "🗑️ Removed Rows",
                "📊 Missing Values Summary",
                "⬇️ Download Results",
            ]
        )

        with tab_preview:
            col_left, col_right = st.columns(2)
            with col_left:
                st.write("**Original CSV (First 10 rows):**")
                st.dataframe(original_df.head(10), use_container_width=True)
            with col_right:
                st.write("**Cleaned CSV (First 10 rows):**")
                st.dataframe(cleaned_df.head(10), use_container_width=True)

        with tab_removed:
            st.write(f"**Total Removed Rows:** {len(removed_df):,}")
            if removed_df.empty:
                st.info("No rows were removed.")
            else:
                st.dataframe(removed_df, use_container_width=True)

        with tab_quality:
            st.write("**Remaining Missing Values per Column:**")
            st.dataframe(cleaned_df.isna().sum().rename("Missing Count"))

        with tab_download:
            st.write("### ⬇️ Download Cleaned Data")
            st.markdown("Choose whether to export your cleaned data to **CSV**, **JSON**, or **Both**:")

            export_choice = st.radio(
                "Select export format:",
                ["CSV", "JSON", "Both (CSV & JSON)"],
                horizontal=True,
            )

            if export_choice == "CSV":
                csv_bytes = export_cleaned_data(cleaned_df, "csv")
                st.download_button(
                    label="⬇️ Download Cleaned CSV",
                    data=csv_bytes,
                    file_name="cleaned_data.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            elif export_choice == "JSON":
                json_bytes = export_cleaned_data(cleaned_df, "json")
                st.download_button(
                    label="⬇️ Download Cleaned JSON",
                    data=json_bytes,
                    file_name="cleaned_data.json",
                    mime="application/json",
                    use_container_width=True,
                )
            else:  # Both
                both_data = export_cleaned_data(cleaned_df, "both")
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="⬇️ Download Cleaned CSV",
                        data=both_data["csv"],
                        file_name="cleaned_data.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with col2:
                    st.download_button(
                        label="⬇️ Download Cleaned JSON",
                        data=both_data["json"],
                        file_name="cleaned_data.json",
                        mime="application/json",
                        use_container_width=True,
                    )

            if not removed_df.empty:
                st.divider()
                st.write("**Removed Rows Log:**")
                st.download_button(
                    label="⬇️ Download Removed Rows (CSV)",
                    data=export_cleaned_data(removed_df, "csv"),
                    file_name="removed_rows.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
