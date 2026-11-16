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

# --- Feature ranking (step 3) --------------------------------------------
# False discovery rate for the Benjamini-Hochberg correction: among the
# features we call significant, about this share may be false alarms.
FDR_LEVEL = 0.05
TOP_N_FEATURES = 10  # features reported in the ranking and exported
TOP_N_CHARTS = 5     # features that get control charts

FEATURE_RANKING_FILE = REPORTS_DIR / "feature_ranking.csv"

# --- Control charts (step 4) ---------------------------------------------
# The process changed level between about run 300 and run 480 (seen on the
# first control charts), and the fail rate dropped at the same time. One set
# of limits cannot describe both periods, so the charts use two stages:
#   Stage 1 = runs 1 to STAGE_2_START - 1
#   Stage 2 = runs STAGE_2_START to the end
# ASSUMPTION: the split at run 501 was chosen by eye, with hindsight, as the
# point where the change had settled. It is not a documented process event.
STAGE_2_START = 501

# Each stage gets its own control limits, computed from the first
# BASELINE_RUNS runs of that stage and then frozen for the rest of the stage.
BASELINE_RUNS = 300

# When picking features to chart, skip a feature whose rank correlation
# with a higher-ranked chart feature is above this (near-duplicate signal).
CORRELATION_LIMIT = 0.9

FIGURES_DIR = REPORTS_DIR / "figures"
CONTROL_LIMITS_FILE = REPORTS_DIR / "control_limits.csv"
STAGE_RANKING_FILE = REPORTS_DIR / "ranking_by_stage.csv"

# --- Process capability (step 5) -------------------------------------------
# ASSUMPTION: SECOM publishes no specification limits. As a stand-in we use
#     LSL, USL = mean of passing runs -/+ SPEC_SIGMA_MULTIPLIER * their sigma
# on the idea that values seen on passing runs are acceptable. These are NOT
# real engineering specs. With a multiplier of 3 the spec window is 6 sigma
# wide by our own choice, so Cp near 1 is expected by construction. Only
# comparisons between features, and Cp versus Cpk, carry meaning.
SPEC_SIGMA_MULTIPLIER = 3.0

CAPABILITY_FILE = REPORTS_DIR / "capability.csv"

# --- Power BI export (step 6) ----------------------------------------------
FACT_FILE = PROCESSED_DIR / "fact_measurements.csv"
DIM_FEATURE_FILE = PROCESSED_DIR / "dim_feature.csv"
FEATURE_STAGE_FILE = PROCESSED_DIR / "feature_stage_summary.csv"
DAILY_FILE = PROCESSED_DIR / "daily_pass_rate.csv"
