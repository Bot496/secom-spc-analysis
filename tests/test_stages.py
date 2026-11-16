"""Tests for the stage split, using eight runs counted by hand."""

import pandas as pd

from control_charts import spc_for_feature
from stages import add_stage_columns


def test_stage_and_baseline_columns():
    table = pd.DataFrame({"run_id": [1, 2, 3, 4, 5, 6, 7, 8]})

    # Stage 2 starts at run 5; each stage's baseline is its first 2 runs.
    result = add_stage_columns(table, stage_2_start=5, baseline_runs=2)

    assert result["stage"].tolist() == [1, 1, 1, 1, 2, 2, 2, 2]
    assert result["in_baseline"].tolist() == [
        True, True, False, False,   # stage 1: runs 1 and 2 are baseline
        True, True, False, False,   # stage 2: runs 5 and 6 are baseline
    ]


def test_original_table_is_not_changed():
    table = pd.DataFrame({"run_id": [1, 2, 3]})
    add_stage_columns(table, stage_2_start=2, baseline_runs=1)
    assert list(table.columns) == ["run_id"]


def test_spc_for_feature_leaves_out_missing_readings():
    # 600 runs, so both real stages (split at run 501) contain data.
    n = 600
    data = pd.DataFrame(
        {
            "run_id": range(1, n + 1),
            "timestamp": pd.date_range("2008-01-01", periods=n, freq="h"),
            "pass_fail": "Pass",
            # Alternating 10, 12 gives a known mean (11) and moving range (2).
            "x": [10.0, 12.0] * (n // 2),
        }
    )
    data.loc[5, "x"] = None  # run 6 has no reading

    points = spc_for_feature(data, "x")

    assert len(points) == n - 1
    assert 6 not in points["run_id"].tolist()
    assert set(points["stage"]) == {1, 2}
    # Stage 2 baseline is clean: mean 11, sigma = 2 / 1.128.
    stage_2 = points[points["stage"] == 2]
    assert stage_2["center"].iloc[0] == 11.0
    assert round(stage_2["sigma"].iloc[0], 4) == round(2 / 1.128, 4)
    # Alternating values never break a rule.
    assert not stage_2["ooc_flag"].any()
