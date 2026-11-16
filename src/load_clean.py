"""Step 2: load the raw SECOM files, join them, and drop unusable features.

Run:  python src/load_clean.py

Outputs:
  data/processed/secom_clean.csv   one row per run, usable features only
  reports/feature_quality.csv      missing values and the keep/drop decision
                                   for every one of the original features
"""

import pandas as pd

from config import (
    CLEAN_FILE,
    FEATURE_QUALITY_FILE,
    ID_COLUMNS,
    LABEL_FILE,
    LABEL_MEANING,
    MAX_MISSING_FRACTION,
    SENSOR_FILE,
    TIMESTAMP_FORMAT,
)


def load_raw():
    """Read both raw files and join them into one table, one row per run."""
    # Sensor readings: numbers separated by spaces, no header row.
    # pandas reads the text "NaN" as a missing value automatically.
    sensors = pd.read_csv(SENSOR_FILE, sep=" ", header=None)

    # The features are anonymised, so we name them by column position:
    # f000 is the first column in the file, f589 the last.
    sensors.columns = [f"f{i:03d}" for i in range(sensors.shape[1])]

    # Labels: one line per run, e.g.  -1 "19/07/2008 11:55:00"
    labels = pd.read_csv(
        LABEL_FILE, sep=" ", header=None, names=["label", "timestamp"]
    )

    # The two files share no key column. Line N of one file belongs to line N
    # of the other, so they must have the same number of lines.
    if len(sensors) != len(labels):
        raise ValueError(
            f"{len(sensors)} sensor rows but {len(labels)} label rows"
        )

    # Stop if the labels are not coded the way we believe they are.
    unexpected = set(labels["label"]) - set(LABEL_MEANING)
    if unexpected:
        raise ValueError(f"Unexpected label values: {unexpected}")

    runs = pd.DataFrame(
        {
            # Timestamps are not unique, so we need our own run identifier:
            # the line number in the raw files, starting at 1.
            "run_id": range(1, len(labels) + 1),
            "timestamp": pd.to_datetime(
                labels["timestamp"], format=TIMESTAMP_FORMAT
            ),
            "pass_fail": labels["label"].map(LABEL_MEANING),
        }
    )

    # Put the two tables side by side (axis=1), matching row by row.
    data = pd.concat([runs, sensors], axis=1)

    # Sort by time. "stable" keeps runs with identical timestamps in their
    # original file order instead of shuffling them.
    data = data.sort_values("timestamp", kind="stable").reset_index(drop=True)
    return data


def assess_features(data):
    """Count missing values per feature and decide which features to keep."""
    features = data.drop(columns=ID_COLUMNS)

    quality = pd.DataFrame(
        {
            "feature": features.columns,
            "n_missing": features.isna().sum().to_numpy(),
            "missing_fraction": features.isna().mean().to_numpy(),
            # Number of different values, not counting missing ones.
            "n_unique": features.nunique().to_numpy(),
        }
    )

    quality["decision"] = "keep"

    # Rule 1: mostly missing. Too few readings to chart or test.
    mostly_missing = quality["missing_fraction"] > MAX_MISSING_FRACTION
    quality.loc[mostly_missing, "decision"] = "drop: mostly missing"

    # Rule 2: constant. A feature that never changes cannot tell a pass
    # from a fail, and its sigma is zero so control limits are meaningless.
    constant = quality["n_unique"] <= 1
    quality.loc[constant, "decision"] = "drop: constant"

    return quality


def drop_unusable(data, quality):
    """Return the data with only the features marked 'keep'."""
    kept = quality.loc[quality["decision"] == "keep", "feature"].tolist()
    return data[ID_COLUMNS + kept]


def main():
    data = load_raw()
    features = data.drop(columns=ID_COLUMNS)

    print("--- Raw data ---")
    print(f"Runs: {len(data)}   Features: {features.shape[1]}")
    print(f"Pass/fail counts: {data['pass_fail'].value_counts().to_dict()}")
    print(f"Time range: {data['timestamp'].min()} to {data['timestamp'].max()}")
    print(f"Raw file already in time order: {data['run_id'].is_monotonic_increasing}")
    print(f"Runs sharing a timestamp with an earlier run: {data['timestamp'].duplicated().sum()}")

    quality = assess_features(data)

    print("\n--- Missing values ---")
    n_cells = features.size
    n_missing = int(quality["n_missing"].sum())
    print(f"Missing cells: {n_missing} of {n_cells} ({n_missing / n_cells:.2%})")
    print(f"Features with no missing values: {(quality['n_missing'] == 0).sum()}")
    print("Ten features with the most missing values:")
    worst = quality.sort_values("missing_fraction", ascending=False).head(10)
    print(worst.to_string(index=False))

    print("\n--- Keep/drop decisions ---")
    print(f"Missing threshold: more than {MAX_MISSING_FRACTION:.0%} missing")
    print(quality["decision"].value_counts().to_string())

    clean = drop_unusable(data, quality)
    print(f"\nClean table: {clean.shape[0]} runs x {clean.shape[1] - len(ID_COLUMNS)} features")

    CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEATURE_QUALITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(CLEAN_FILE, index=False)
    quality.to_csv(FEATURE_QUALITY_FILE, index=False)
    print(f"Saved {CLEAN_FILE}")
    print(f"Saved {FEATURE_QUALITY_FILE}")


if __name__ == "__main__":
    main()
