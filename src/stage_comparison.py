"""Check whether the pass/fail ranking is partly a time effect.

Run:  python src/stage_comparison.py   (after src/feature_ranking.py)

The fail rate and several features changed level at about the same time.
A feature can then look "associated with failure" over the whole dataset
only because early runs had both higher readings and more failures.

To check, this script repeats the step 3 test inside each stage. If a
feature still separates pass from fail inside a stage, the association is
not explained by the change between stages alone.

Output:
  reports/ranking_by_stage.csv   the overall top features, tested per stage
"""

import pandas as pd

from config import (
    CLEAN_FILE,
    FDR_LEVEL,
    FEATURE_RANKING_FILE,
    STAGE_RANKING_FILE,
    TOP_N_FEATURES,
)
from feature_ranking import adjust_and_rank, compare_pass_fail
from stages import add_stage_columns


def main():
    data = pd.read_csv(CLEAN_FILE, parse_dates=["timestamp"])
    data = add_stage_columns(data)
    overall = pd.read_csv(FEATURE_RANKING_FILE)

    # Start from the overall top features and add per-stage columns to them.
    columns = ["feature", "rank", "prob_fail_higher", "p_adjusted"]
    table = overall.head(TOP_N_FEATURES)[columns].rename(
        columns={
            "rank": "rank_all",
            "prob_fail_higher": "prob_fail_higher_all",
            "p_adjusted": "p_adjusted_all",
        }
    )

    print("Fail rate per stage:")
    for stage, stage_data in data.groupby("stage"):
        n_fail = (stage_data["pass_fail"] == "Fail").sum()
        print(f"  Stage {stage}: runs {stage_data['run_id'].min()}-"
              f"{stage_data['run_id'].max()}, {n_fail} fails of "
              f"{len(stage_data)} ({n_fail / len(stage_data):.1%})")

        # Same test and correction as step 3, on this stage's runs only.
        features_only = stage_data.drop(columns=["stage", "in_baseline"])
        ranking = adjust_and_rank(compare_pass_fail(features_only))
        print(f"    significant features after correction at "
              f"{FDR_LEVEL:.0%}: {ranking['significant'].sum()} of {len(ranking)}")

        ranking = ranking[columns].rename(
            columns={
                "rank": f"rank_stage{stage}",
                "prob_fail_higher": f"prob_fail_higher_stage{stage}",
                "p_adjusted": f"p_adjusted_stage{stage}",
            }
        )
        table = table.merge(ranking, on="feature", how="left")

    print(f"\nOverall top {TOP_N_FEATURES} features, tested inside each stage:")
    print(table.round(4).to_string(index=False))

    table.to_csv(STAGE_RANKING_FILE, index=False)
    print(f"\nSaved {STAGE_RANKING_FILE}")


if __name__ == "__main__":
    main()
