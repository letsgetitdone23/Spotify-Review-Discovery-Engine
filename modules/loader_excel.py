"""
modules/loader_excel.py
-----------------------
Loads and normalizes the preloaded Spotify reviews Excel file into a clean
Pandas DataFrame ready for relevance filtering and AI analysis.

Expected file: data/reviews_preloaded.xlsx
Sheet layout  : The workbook contains multiple sheets (e.g. Reddit, Google
                Playstore, App Store, Twitter, Community n Social). All sheets
                are read and combined into one DataFrame automatically.

Required column in every sheet: review_text
Optional columns               : source, date, rating, language
"""

import os
import pandas as pd

# Resolve path relative to this module's location so it works regardless
# of which directory Streamlit is launched from.
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(_MODULE_DIR, "..", "data", "reviews_preloaded.xlsx")

# Columns that are optional — added with None if absent in a sheet
OPTIONAL_COLUMNS = ["source", "date", "rating", "language"]


def _normalize_sheet(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """
    Normalize a single sheet's DataFrame:
      - lowercase snake_case column names
      - fill missing optional columns
      - default source to sheet_name when blank
      - clean review_text (strip, min-length filter)
    """
    # Normalize column names
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    # Skip sheets that don't have review_text at all
    if "review_text" not in df.columns:
        return pd.DataFrame()

    # Fill missing optional columns
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Use the sheet name as the source fallback (more descriptive than 'Unknown')
    df["source"] = df["source"].fillna(sheet_name)

    # Clean review_text
    df = df.dropna(subset=["review_text"])
    df["review_text"] = df["review_text"].astype(str).str.strip()
    df = df[df["review_text"].str.len() >= 2]

    return df


def load_preloaded_reviews() -> pd.DataFrame:
    """
    Load ALL sheets from the preloaded Excel file and return a single
    combined, normalized, deduplicated DataFrame.

    Process:
      1. Open the workbook and iterate over every sheet.
      2. Normalize each sheet via _normalize_sheet().
      3. Concatenate all sheets into one DataFrame.
      4. Drop cross-sheet duplicate review texts.
      5. Reset the index.

    Returns:
        pd.DataFrame with columns: review_text, source, date, rating, language
        (plus any extra columns present in any sheet)

    Raises:
        FileNotFoundError : if 'data/reviews_preloaded.xlsx' does not exist.
        ValueError        : if no sheet contains a 'review_text' column.
    """
    # --- Step 1: Open workbook ---
    try:
        xl = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Reviews file not found at '{EXCEL_PATH}'. "
            "Please ensure 'data/reviews_preloaded.xlsx' exists in the project root."
        )

    # --- Step 2: Read and normalize every sheet ---
    frames = []
    skipped_sheets = []

    for sheet_name in xl.sheet_names:
        raw_df = xl.parse(sheet_name)
        normalized = _normalize_sheet(raw_df, sheet_name)
        if normalized.empty:
            skipped_sheets.append(sheet_name)
        else:
            frames.append(normalized)

    if not frames:
        raise ValueError(
            "No sheet in the Excel file contains a 'review_text' column. "
            f"Sheets checked: {xl.sheet_names}"
        )

    # --- Step 3: Combine all sheets ---
    df = pd.concat(frames, ignore_index=True)

    # --- Step 4: Drop cross-sheet duplicates ---
    df = df.drop_duplicates(subset=["review_text"])

    # --- Step 5: Reset index ---
    df = df.reset_index(drop=True)

    return df


def summarize_dataframe(df: pd.DataFrame) -> dict:
    """
    Return a quick summary dict of the loaded DataFrame for diagnostics.
    Useful for displaying stats in the UI without re-computing.

    Returns:
        dict with keys: total_reviews, sources, has_rating, has_date, has_language
    """
    return {
        "total_reviews": len(df),
        "sources": df["source"].value_counts().to_dict(),
        "has_rating": df["rating"].notna().any(),
        "has_date": df["date"].notna().any(),
        "has_language": df["language"].notna().any(),
    }
