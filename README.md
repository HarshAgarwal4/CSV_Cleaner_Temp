# CSV Cleaner Application

An automated data cleaning pipeline and interactive web interface built with Python, Pandas, and Streamlit to sanitize, deduplicate, and validate tabular CSV datasets.

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
   - Generates detailed cleaning statistics (initial row count, duplicates dropped, nulls removed, and cleaned row count).
   - Exports sanitized dataset and tracked removal reasons.

---

## 🗂️ Project Structure

```text
week1-again/
├── Data/
│   ├── sample_review.csv        # Sample input dataset
│   └── cleaned_review.csv       # Output cleaned dataset
├── src/
│   └── week1_again/
│       └── __init__.py          # Package initialization
├── test/
│   └── test_cleaner.py          # Unit & integration tests with logging
├── app.py                       # Streamlit web interface
├── main.py                      # Standalone CLI cleaning pipeline with retry mechanism
├── pyproject.toml               # Project metadata and dependencies
├── requirements.txt             # Pip dependencies
└── README.md                    # Project documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python **3.12+**
- Recommended: virtual environment (`venv` or `uv`)

### 2. Setup Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 💻 Usage

### Standalone CLI Cleaning Script (`main.py`)
Run the standalone pipeline directly from the terminal to clean `Data/sample_review.csv` into `Data/cleaned_review.csv` and display a comparison summary:

```bash
python main.py
```

### Streamlit Web Application (`app.py`)
Launch the interactive web interface:

```bash
streamlit run app.py
```
- Open your browser at `http://localhost:8501`.
- Upload any `.csv` file.
- Adjust pipeline settings (whitespace normalization, HTML stripping, duplicate removal, null handling rule).
- Click **Clean CSV Now** to view data previews, row metrics, and download cleaned files.

---

## 🧪 Testing with Logging

Unit and integration tests are located in `test/test_cleaner.py` and utilize Python's standard `logging` and `unittest` modules.

### Run Tests:

```bash
python test/test_cleaner.py
```

Or via unittest runner:

```bash
python -m unittest test/test_cleaner.py -v
```

### What is Tested:
- **`clean_csv` Pipeline**:
  - Full end-to-end cleaning (header trimming, HTML removal, deduplication, null removal).
  - Exception handling when input and output file paths are identical.
  - Automatic retry decorator handling transient I/O issues.
- **`clean_dataframe` Logic**:
  - Whitespace trimming and multi-space normalization.
  - Duplicate detection and tracking in the removed records DataFrame.
  - Null removal modes (`any`, `all`, and `required` column).
  - Common text placeholder conversion (`NULL`, `None`, `NA`, empty strings).
- **Execution Logging**:
  - Each test logs setup, input states, transformation metrics, and assertion results.
