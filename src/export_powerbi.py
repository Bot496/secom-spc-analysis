"""Step 6: write tidy CSV tables for Power BI into data/processed/.

Run:  python src/export_powerbi.py
      (after feature_ranking.py and stage_comparison.py)

Tables (the key column that links tables is marked with *):

  fact_measurements.csv      one row per run and feature (top features only)
      run_id, timestamp, date*, stage, feature*, value, pass_fail,
      ooc_flag, rule_violated, plus the control limits of that row's stage

  dim_feature.csv            one row per feature
      feature*, rank, p-values, effect size, significance per stage

  feature_stage_summary.csv  one row per feature and stage
      feature*, stage, mean, sigma, UCL, LCL, Cp, Cpk, OOC counts

  daily_pass_rate.csv        one row per production day
      date*, n_runs, n_pass, n_fail, pass_rate
"""

import pandas as pd

from capability import capability_table
from config import (
    CLEAN_FILE,
    DAILY_FILE,
    DIM_FEATURE_FILE,
    FACT_FILE,
    FEATURE_RANKING_FILE,
    FEATURE_STAGE_FILE,
    PROCESSED_DIR,
    STAGE_RANKING_FILE,
    TOP_N_FEATURES,
)
from control_charts import select_chart_features, spc_for_feature, summarise_stage


def build_fact_table(data, features):
    """Long format: one row per run and feature, with flags and limits."""
    tables = [spc_for_feature(data, feature) for feature in features]
    fact = pd.concat(tables, ignore_index=True)

    # A date without the time links each row to the daily table.
    fact["date"] = fact["timestamp"].dt.date

    # Text reads better than an empty cell in a Power BI slicer or legend.
    fact["rule_violated"] = fact["rule_violated"].replace("", "No violation")

    columns = [
        "run_id", "timestamp", "date", "stage", "feature", "value",
        "pass_fail", "ooc_flag", "rule_violated", "in_baseline",
        "center", "ucl", "lcl", "moving_range", "mr_center", "mr_ucl", "mr_ooc",
    ]
    return fact[columns]


def build_dim_feature(ranking, stage_ranking, features, chart_features):
    """One row per feature: how strongly it is associated with failure."""
    dim = ranking[ranking["feature"].isin(features)][
        ["feature", "rank", "prob_fail_higher", "median_pass", "median_fail",
         "p_value", "p_adjusted", "significant"]
    ]

    # Add the per-stage test results from stage_comparison.py.
    stage_columns = [
        "feature", "prob_fail_higher_stage1", "p_adjusted_stage1",
        "prob_fail_higher_stage2", "p_adjusted_stage2",
    ]
    dim = dim.merge(stage_ranking[stage_columns], on="feature", how="left")

    dim["has_control_chart"] = dim["feature"].isin(chart_features)
    return dim.sort_values("rank").reset_index(drop=True)


def build_feature_stage_summary(data, features):
    """One row per feature and stage: control limits and capability."""
    # Control chart numbers (limits come from each stage's baseline runs).
    chart_rows = []
    for feature in features:
        points = spc_for_feature(data, feature)
        for _, stage_points in points.groupby("stage"):
            chart_rows.append(summarise_stage(stage_points))
    chart = pd.DataFrame(chart_rows)[
        ["feature", "stage", "first_run", "last_run", "center", "sigma",
         "ucl", "lcl", "n_points", "n_ooc", "ooc_rate"]
    ].rename(columns={"sigma": "sigma_chart", "n_points": "n_runs"})

    # Capability numbers (mean and sigma come from all runs of the stage).
    capability = capability_table(data, features)[
        ["feature", "stage", "mean", "sigma_within", "sigma_overall",
         "lsl_assumed", "usl_assumed", "cp", "cpk", "pp", "ppk",
         "fraction_outside_spec"]
    ]

    return chart.merge(capability, on=["feature", "stage"])


def build_daily_pass_rate(data):
    """One row per production day."""
    is_pass = data["pass_fail"] == "Pass"
    daily = (
        pd.DataFrame({"date": data["timestamp"].dt.date, "is_pass": is_pass})
        .groupby("date")["is_pass"]
        .agg(n_runs="count", n_pass="sum")
        .reset_index()
    )
    daily["n_fail"] = daily["n_runs"] - daily["n_pass"]
    daily["pass_rate"] = daily["n_pass"] / daily["n_runs"]
    return daily


def check_tables(fact, dim, summary, daily):
    """Stop if the tables would not link up correctly in Power BI."""
    # Key columns on the "one" side of a relationship must be unique.
    assert dim["feature"].is_unique, "dim_feature: duplicate feature"
    assert daily["date"].is_unique, "daily_pass_rate: duplicate date"
    assert not summary.duplicated(["feature", "stage"]).any()
    assert not fact.duplicated(["run_id", "feature"]).any()

    # Every fact row must find its feature and its date in the other tables.
    assert set(fact["feature"]) == set(dim["feature"])
    assert set(summary["feature"]) == set(dim["feature"])
    assert set(fact["date"]) <= set(daily["date"])


def main():
    data = pd.read_csv(CLEAN_FILE, parse_dates=["timestamp"])
    ranking = pd.read_csv(FEATURE_RANKING_FILE)
    stage_ranking = pd.read_csv(STAGE_RANKING_FILE)

    features = ranking["feature"].head(TOP_N_FEATURES).tolist()
    chart_features = select_chart_features(ranking, data)

    fact = build_fact_table(data, features)
    dim = build_dim_feature(ranking, stage_ranking, features, chart_features)
    summary = build_feature_stage_summary(data, features)
    daily = build_daily_pass_rate(data)

    check_tables(fact, dim, summary, daily)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for table, path in [(fact, FACT_FILE), (dim, DIM_FEATURE_FILE),
                        (summary, FEATURE_STAGE_FILE), (daily, DAILY_FILE)]:
        table.to_csv(path, index=False)
        print(f"Saved {path.name}: {len(table)} rows x {table.shape[1]} columns")


if __name__ == "__main__":
    main()
