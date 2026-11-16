"""Step 3: rank features by how differently they behave on pass vs fail runs.

Run:  python src/feature_ranking.py   (after src/load_clean.py)

Output:
  reports/feature_ranking.csv   one row per feature, strongest first
"""

import pandas as pd
from scipy import stats

from config import (
    CLEAN_FILE,
    FDR_LEVEL,
    FEATURE_RANKING_FILE,
    ID_COLUMNS,
    TOP_N_FEATURES,
)


def compare_pass_fail(data):
    """Run one Mann-Whitney U test per feature: pass runs vs fail runs."""
    is_fail = data["pass_fail"] == "Fail"
    feature_names = [c for c in data.columns if c not in ID_COLUMNS]

    rows = []
    for feature in feature_names:
        # A feature with a single value in this data cannot be tested (every
        # pair is a tie), so skip it. This happens when the test is run on
        # part of the runs, where a feature may not vary at all.
        if data[feature].nunique() <= 1:
            continue

        # Split the feature's values into the two groups. Missing values
        # are simply left out of the test for this feature.
        pass_values = data.loc[~is_fail, feature].dropna()
        fail_values = data.loc[is_fail, feature].dropna()

        # Mann-Whitney U asks: if I pick one fail run and one pass run at
        # random, is the fail value higher more (or less) often than 50%?
        # It compares ranks, not raw values, so it does not assume a bell
        # curve and is not thrown off by a few extreme readings.
        result = stats.mannwhitneyu(
            fail_values, pass_values, alternative="two-sided"
        )

        # U counts the (fail, pass) pairs where the fail value is higher.
        # Dividing by the number of pairs gives a probability:
        # 0.5 = no difference, near 0 or 1 = strong separation.
        n_pairs = len(fail_values) * len(pass_values)
        prob_fail_higher = result.statistic / n_pairs

        rows.append(
            {
                "feature": feature,
                "n_pass": len(pass_values),
                "n_fail": len(fail_values),
                "median_pass": pass_values.median(),
                "median_fail": fail_values.median(),
                "prob_fail_higher": prob_fail_higher,
                "p_value": result.pvalue,
            }
        )

    return pd.DataFrame(rows)


def adjust_and_rank(results, fdr_level=FDR_LEVEL):
    """Correct the p-values for multiple testing, then rank the features."""
    results = results.copy()

    # Benjamini-Hochberg: sort the p-values, multiply the k-th smallest by
    # (number of tests / k), and make sure the result never decreases as
    # k grows. The adjusted value is compared with the FDR level.
    results["p_adjusted"] = stats.false_discovery_control(
        results["p_value"], method="bh"
    )
    results["significant"] = results["p_adjusted"] < fdr_level

    # Rank 1 = smallest p-value = strongest evidence of a difference.
    results = results.sort_values("p_value").reset_index(drop=True)
    results.insert(0, "rank", range(1, len(results) + 1))
    return results


def main():
    data = pd.read_csv(CLEAN_FILE, parse_dates=["timestamp"])

    ranking = adjust_and_rank(compare_pass_fail(data))

    n_tests = len(ranking)
    print(f"Features tested: {n_tests}")
    print(f"Raw p < 0.05 (no correction): {(ranking['p_value'] < 0.05).sum()}")
    print(f"Expected by chance alone at 0.05: about {0.05 * n_tests:.0f}")
    print(f"Significant after Benjamini-Hochberg at {FDR_LEVEL:.0%}: {ranking['significant'].sum()}")

    print(f"\nTop {TOP_N_FEATURES} features:")
    print(ranking.head(TOP_N_FEATURES).to_string(index=False))

    FEATURE_RANKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    ranking.to_csv(FEATURE_RANKING_FILE, index=False)
    print(f"\nSaved {FEATURE_RANKING_FILE}")


if __name__ == "__main__":
    main()
