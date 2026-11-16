"""Tests for the feature ranking, using tiny tables worked out by hand."""

import pandas as pd
import pytest

from feature_ranking import adjust_and_rank, compare_pass_fail


def make_data():
    """Six runs: 3 pass, 3 fail, and two features.

    'separated': every fail value is above every pass value.
    'mixed':     pass and fail values are interleaved.
    """
    return pd.DataFrame(
        {
            "run_id": [1, 2, 3, 4, 5, 6],
            "timestamp": pd.date_range("2008-01-01", periods=6, freq="h"),
            "pass_fail": ["Pass", "Pass", "Pass", "Fail", "Fail", "Fail"],
            "separated": [1.0, 2.0, 3.0, 10.0, 11.0, 12.0],
            "mixed": [1.0, 3.0, 5.0, 2.0, 4.0, 6.0],
        }
    )


def test_fully_separated_feature_has_probability_one():
    results = compare_pass_fail(make_data()).set_index("feature")
    # All 9 (fail, pass) pairs have the fail value higher: 9 / 9 = 1.
    assert results.loc["separated", "prob_fail_higher"] == 1.0
    assert results.loc["separated", "median_pass"] == 2.0
    assert results.loc["separated", "median_fail"] == 11.0


def test_mixed_feature_is_counted_by_hand():
    results = compare_pass_fail(make_data()).set_index("feature")
    # Fail 2 beats pass 1 (1 pair); fail 4 beats 1 and 3 (2 pairs);
    # fail 6 beats 1, 3 and 5 (3 pairs). Total 6 of 9 pairs.
    assert results.loc["mixed", "prob_fail_higher"] == pytest.approx(6 / 9)


def test_missing_values_are_left_out():
    data = make_data()
    data.loc[0, "separated"] = None  # one pass run has no reading
    results = compare_pass_fail(data).set_index("feature")
    assert results.loc["separated", "n_pass"] == 2
    assert results.loc["separated", "n_fail"] == 3


def test_constant_feature_is_skipped():
    data = make_data()
    data["flat"] = 7.0  # same value on every run: nothing to test
    results = compare_pass_fail(data)
    assert results["feature"].tolist() == ["separated", "mixed"]


def test_benjamini_hochberg_by_hand():
    # Four tests. Adjusted p = p * 4 / position when sorted:
    #   0.01 * 4/1 = 0.04
    #   0.02 * 4/2 = 0.04
    #   0.03 * 4/3 = 0.04
    #   0.20 * 4/4 = 0.20
    results = pd.DataFrame(
        {"feature": ["a", "b", "c", "d"], "p_value": [0.20, 0.03, 0.01, 0.02]}
    )
    ranked = adjust_and_rank(results, fdr_level=0.05)

    assert ranked["feature"].tolist() == ["c", "d", "b", "a"]
    assert ranked["rank"].tolist() == [1, 2, 3, 4]
    assert ranked["p_adjusted"].tolist() == pytest.approx([0.04, 0.04, 0.04, 0.20])
    assert ranked["significant"].tolist() == [True, True, True, False]
