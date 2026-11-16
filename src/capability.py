"""Step 5: process capability (Cp, Cpk) for the top features.

Run:  python src/capability.py   (after src/feature_ranking.py)

IMPORTANT: SECOM has no published spec limits. The limits used here are an
ASSUMPTION derived from the passing runs (see SPEC_SIGMA_MULTIPLIER in
config.py). The indices are for comparison only, not real capability.

Output:
  reports/capability.csv   one row per feature and stage
"""

import numpy as np
import pandas as pd

from config import (
    CAPABILITY_FILE,
    CLEAN_FILE,
    FEATURE_RANKING_FILE,
    SPEC_SIGMA_MULTIPLIER,
    TOP_N_FEATURES,
)
from spc_rules import D2
from stages import add_stage_columns


def assumed_spec_limits(pass_values, k=SPEC_SIGMA_MULTIPLIER):
    """ASSUMED spec limits: mean of the passing runs -/+ k standard deviations.

    Returns (lsl, usl): lower and upper specification limit.
    """
    values = np.asarray(pass_values, dtype=float)
    mean = values.mean()
    sigma = values.std(ddof=1)  # ddof=1: sample standard deviation
    return mean - k * sigma, mean + k * sigma


def capability_indices(values, lsl, usl):
    """Capability indices for values in time order, with no missing values.

    Cp   = spec width / (6 sigma)
           Would the spread fit inside the spec window if it were centred?
    Cpk  = distance from the mean to the NEAREST spec limit / (3 sigma)
           Same idea, but it also penalises being off-centre. Cpk <= Cp.

    Cp and Cpk use the short-term sigma (average moving range / 1.128),
    the same sigma as the control chart. Pp and Ppk are the same formulas
    with the ordinary standard deviation of all the values, which also
    includes drift over time. A process that drifts has Ppk below Cpk.
    """
    values = np.asarray(values, dtype=float)
    mean = values.mean()

    sigma_within = np.abs(np.diff(values)).mean() / D2
    sigma_overall = values.std(ddof=1)
    if sigma_within <= 0 or sigma_overall <= 0:
        raise ValueError("The values do not vary, so capability is undefined")

    # Distance from the mean to the nearest spec limit.
    nearest = min(usl - mean, mean - lsl)

    return {
        "mean": mean,
        "sigma_within": sigma_within,
        "sigma_overall": sigma_overall,
        "cp": (usl - lsl) / (6 * sigma_within),
        "cpk": nearest / (3 * sigma_within),
        "pp": (usl - lsl) / (6 * sigma_overall),
        "ppk": nearest / (3 * sigma_overall),
        # Share of these runs that actually fall outside the assumed limits.
        "fraction_outside_spec": ((values < lsl) | (values > usl)).mean(),
    }


def capability_table(data, features):
    """Capability of each feature in each stage, against one assumed spec."""
    data = add_stage_columns(data)
    is_pass = data["pass_fail"] == "Pass"

    rows = []
    for feature in features:
        # One spec per feature, from the passing runs of the whole dataset.
        # A spec describes what the product needs, so it does not change
        # from stage to stage.
        lsl, usl = assumed_spec_limits(data.loc[is_pass, feature].dropna())

        for stage, stage_data in data.groupby("stage"):
            values = stage_data[feature].dropna()
            row = {"feature": feature, "stage": stage, "n_runs": len(values),
                   "lsl_assumed": lsl, "usl_assumed": usl}
            row.update(capability_indices(values, lsl, usl))
            rows.append(row)

    return pd.DataFrame(rows)


def main():
    data = pd.read_csv(CLEAN_FILE, parse_dates=["timestamp"])
    ranking = pd.read_csv(FEATURE_RANKING_FILE)
    features = ranking["feature"].head(TOP_N_FEATURES).tolist()

    table = capability_table(data, features)

    print("ASSUMED spec limits (not real engineering specs):")
    print(f"  passing-run mean -/+ {SPEC_SIGMA_MULTIPLIER} sigma, per feature\n")
    columns = ["feature", "stage", "lsl_assumed", "usl_assumed", "mean",
               "cp", "cpk", "pp", "ppk", "fraction_outside_spec"]
    print(table[columns].round(3).to_string(index=False))

    CAPABILITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(CAPABILITY_FILE, index=False)
    print(f"\nSaved {CAPABILITY_FILE}")


if __name__ == "__main__":
    main()
