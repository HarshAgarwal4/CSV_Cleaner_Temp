# CSV Cleaner Application

An automated data cleaning pipeline and interactive web interface built with Python, Pandas, and Streamlit to sanitize, deduplicate, validate, and export tabular CSV datasets to CSV and JSON formats.

---

## 📌 Features

### 🔄 4-Step Cleaning Pipeline
1. **Trim & Strip Whitespace**:
   - Strips leading and trailing whitespace from column headers and cell values.
   - Normalizes multiple internal spaces (e.g. `"John   Doe"` &rarr; `"John Doe"`).
   - Optional removal of HTML tags (e.g. `<b>text</b>` &rarr; `text`).
2. **Remove Duplicate Rows**:
   - Drops duplicate rows post-whitespace normalization so subtle spacing differences don't create false duplicates.
3. **Handle Null & Missing Values**:
   - Normalizes blank strings and placeholder markers (`NULL`, `None`, `NA`, `nan`, `N/A`) into real nulls (`NaN`).
   - Supports multiple removal rules:
     - **Strict**: Drop rows with any missing value.
     - **All**: Drop rows where all columns are empty.
     - **Required**: Drop rows only when a designated essential column is missing.
4. **Summary & Export**:
   - Generates cleaning statistics (rows before/after, duplicates removed, nulls removed).
   - Simple export to **CSV**, **JSON**, or **both**.

---

## 🗂️ Project Structure

```text
week1-again/
├── Data/
│   ├── sample_review.csv        # Sample input dataset
│   ├── cleaned_review.csv       # Output cleaned dataset (CSV)
│   └── cleaned_review.json      # Output cleaned dataset (JSON)
├── src/
│   └── week1_again/
│       └── __init__.py          # Package initialization
├── test/
│   └── test_cleaner.py          # Unit & integration tests with logging
├── app.py                       # Streamlit web interface with CSV/JSON/both download
├── main.py                      # Standalone CLI cleaning & export pipeline
├── pyproject.toml               # Project metadata and dependencies
├── requirements.txt             # Pip dependencies
└── README.md                    # Project documentation
```

---

## Setup Instructions

### 1. Clone the repository
```bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_PROJECT_FOLDER>
```

### 2. Install dependencies
Make sure [uv](https://docs.astral.sh/uv/getting-started/installation/) is installed.

```bash
uv sync
```
This creates the virtual environment (.venv) and installs the dependencies defined in pyproject.toml and uv.lock.

### 3. Run the application

For the Python script:
```bash
uv run main.py
```

For the Streamlit application:
```bash
uv run streamlit run app.py
```

---

## 💻 Usage

### Standalone CLI Cleaning & Export (`main.py`)
Run the standalone pipeline directly from the terminal to clean `Data/sample_review.csv` into `Data/cleaned_review.csv` and `Data/cleaned_review.json`:

```bash
uv run main.py
```

#### Simple Export in `main.py`:
```python
from main import export_cleaned_data, clean_csv

# Clean and export to both CSV and JSON
summary = clean_csv(
    input_file="Data/sample_review.csv",
    output_file="Data/cleaned_review.csv",
    export_format="both",  # 'csv', 'json', or 'both'
)

# Or export an existing DataFrame / CSV file directly
export_cleaned_data(
    data="Data/cleaned_review.csv",
    output_path="Data/exported_data",
    export_format="json",  # 'csv', 'json', or 'both'
)
```

### Streamlit Web Application (`app.py`)
Launch the interactive web interface:

```bash
uv run streamlit run app.py
```
- Open your browser at `http://localhost:8501`.
- Upload any `.csv` file.
- Adjust pipeline settings and click **Clean CSV Now**.
- Navigate to the **⬇️ Download Cleaned Data** tab to download your cleaned data in **CSV**, **JSON**, or **Both (CSV & JSON)**.

---

## 🧪 Testing

Run tests with `unittest`:

```bash
uv run python -m unittest test/test_cleaner.py -v
```
