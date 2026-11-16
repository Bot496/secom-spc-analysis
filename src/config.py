"""Project settings in one place: file locations and analysis choices.

Every script imports from here, so a threshold is changed once, not in
several files.
"""

from pathlib import Path

# --- Folders -----------------------------------------------------------
# __file__ is this file (src/config.py); its parent's parent is the project.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"

# --- Raw data ----------------------------------------------------------
DATA_URL = "https://archive.ics.uci.edu/static/public/179/secom.zip"
SENSOR_FILE = RAW_DIR / "secom.data"
LABEL_FILE = RAW_DIR / "secom_labels.data"

# Label coding in secom_labels.data, checked against the file:
# -1 = pass (1,463 runs), 1 = fail (104 runs).
LABEL_MEANING = {-1: "Pass", 1: "Fail"}

# Timestamps are day first, e.g. "19/07/2008 11:55:00".
TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M:%S"

# --- Cleaning ----------------------------------------------------------
# Drop a feature when more than this fraction of its values is missing.
# Why 0.40: in this dataset no feature has between 18% and 45% missing, so
# any threshold in that gap removes the same 32 features. The features above
# the gap are too sparse to draw a control chart on.
MAX_MISSING_FRACTION = 0.40

# --- Outputs of the cleaning step ---------------------------------------
CLEAN_FILE = PROCESSED_DIR / "secom_clean.csv"
FEATURE_QUALITY_FILE = REPORTS_DIR / "feature_quality.csv"

# Columns that describe a run. Every other column is a sensor feature.
ID_COLUMNS = ["run_id", "timestamp", "pass_fail"]
