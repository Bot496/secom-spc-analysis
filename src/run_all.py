"""Run the whole analysis from start to finish, in the right order.

Run:  python src/run_all.py

Downloads the raw data first if it is not already in data/raw/.
"""

import subprocess
import sys
from pathlib import Path

from config import SENSOR_FILE

SRC_DIR = Path(__file__).resolve().parent

# Each step reads the files written by the steps before it.
STEPS = [
    "load_clean.py",        # join, sort, drop unusable features
    "feature_ranking.py",   # pass vs fail test per feature
    "stage_comparison.py",  # the same test inside each stage
    "control_charts.py",    # I-MR charts and rule violations
    "capability.py",        # Cp, Cpk against assumed spec limits
    "export_powerbi.py",    # CSV tables for Power BI
]


def run_step(script):
    print(f"\n=== {script} ===")
    # sys.executable is the Python that is running this file, so every step
    # uses the same virtual environment. check=True stops at the first error.
    subprocess.run([sys.executable, str(SRC_DIR / script)], check=True)


def main():
    if not SENSOR_FILE.exists():
        run_step("download_data.py")
    for script in STEPS:
        run_step(script)
    print("\nAll steps finished.")


if __name__ == "__main__":
    main()
