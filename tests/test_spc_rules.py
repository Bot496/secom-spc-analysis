"""Tests for the SPC functions, using small examples worked out by hand.

Most tests use center=0 and sigma=1, so each value IS its distance from the
centre line in sigma units. That makes the expected answer easy to read.
"""

import numpy as np
import pytest

from spc_rules import (
    check_rules,
    imr_limits,
    k_of_n_beyond,
    moving_range,
    summarise_rules,
)


def rules_for(values):
    """Shortcut: check the rules with centre 0 and sigma 1."""
    return check_rules(values, center=0, sigma=1)


# --- Moving range and control limits ---------------------------------------

def test_moving_range():
    result = moving_range([1, 3, 2])
    assert np.isnan(result[0])              # no previous point
    assert result[1:].tolist() == [2, 1]    # |3-1| = 2, |2-3| = 1


def test_imr_limits_by_hand():
    # Values alternate 10, 12: mean = 54 / 5 = 10.8.
    # Every moving range is 2, so the average moving range is 2.
    # sigma = 2 / 1.128 = 1.773
    limits = imr_limits([10, 12, 10, 12, 10])

    assert limits["center"] == pytest.approx(10.8)
    assert limits["mr_center"] == pytest.approx(2.0)
    assert limits["sigma"] == pytest.approx(2 / 1.128)
    assert limits["ucl"] == pytest.approx(10.8 + 3 * 2 / 1.128)
    assert limits["lcl"] == pytest.approx(10.8 - 3 * 2 / 1.128)
    assert limits["mr_ucl"] == pytest.approx(3.267 * 2)


def test_imr_limits_needs_two_points():
    with pytest.raises(ValueError):
        imr_limits([5.0])


# --- Rule 1: one point beyond 3 sigma ---------------------------------------

def test_rule_1_flags_points_beyond_3_sigma_on_either_side():
    flags = rules_for([0, 3.1, -3.5, 2.9])["rule_1"]
    assert flags.tolist() == [False, True, True, False]


def test_rule_1_exactly_3_sigma_is_not_beyond():
    flags = rules_for([3.0, -3.0])["rule_1"]
    assert flags.tolist() == [False, False]


# --- Rule 2: 2 of 3 beyond 2 sigma, same side -------------------------------

def test_rule_2_flags_second_point_beyond_2_sigma():
    # Points 1 and 3 are beyond 2 sigma: point 3 completes "2 of 3".
    flags = rules_for([2.5, 0, 2.5])["rule_2"]
    assert flags.tolist() == [False, False, True]


def test_rule_2_ignores_points_on_opposite_sides():
    flags = rules_for([2.5, -2.5, 0])["rule_2"]
    assert flags.tolist() == [False, False, False]


def test_rule_2_needs_points_within_a_window_of_3():
    # Two points beyond 2 sigma, but 4 apart: not "2 of 3 consecutive".
    flags = rules_for([2.5, 0, 0, 2.5])["rule_2"]
    assert flags.tolist() == [False, False, False, False]


def test_rule_2_does_not_flag_a_normal_point_after_the_pattern():
    # The pattern completes at the second point. The third point is close
    # to the centre line and must not be flagged.
    flags = rules_for([2.5, 2.5, 0])["rule_2"]
    assert flags.tolist() == [False, True, False]


# --- Rule 3: 4 of 5 beyond 1 sigma, same side -------------------------------

def test_rule_3_flags_fourth_point_beyond_1_sigma():
    flags = rules_for([1.5, 1.5, 0, 1.5, 1.5])["rule_3"]
    assert flags.tolist() == [False, False, False, False, True]


def test_rule_3_three_of_five_is_not_enough():
    flags = rules_for([1.5, 0, 1.5, 0, 1.5])["rule_3"]
    assert flags.tolist() == [False] * 5


def test_rule_3_works_below_the_centre_line():
    flags = rules_for([-1.5, -1.5, -1.5, -1.5])["rule_3"]
    assert flags.tolist() == [False, False, False, True]


# --- Rule 4: 8 in a row on one side -----------------------------------------

def test_rule_4_seven_in_a_row_is_not_enough():
    flags = rules_for([0.1] * 7)["rule_4"]
    assert flags.tolist() == [False] * 7


def test_rule_4_flags_the_eighth_point_and_every_point_after():
    flags = rules_for([0.1] * 9)["rule_4"]
    assert flags.tolist() == [False] * 7 + [True, True]


def test_rule_4_run_is_broken_by_a_point_on_the_other_side():
    values = [0.1] * 7 + [-0.1] + [0.1] * 7
    flags = rules_for(values)["rule_4"]
    assert flags.tolist() == [False] * 15


def test_rule_4_works_below_the_centre_line():
    flags = rules_for([-0.1] * 8)["rule_4"]
    assert flags.tolist() == [False] * 7 + [True]


# --- All rules together ------------------------------------------------------

def test_in_control_series_breaks_no_rule():
    # Small values that keep crossing the centre line.
    values = [0.5, -0.5, 0.8, -0.2, 0.1, -0.9, 0.4, -0.6, 0.3, -0.1]
    table = rules_for(values)
    assert not table.to_numpy().any()


def test_rules_use_the_given_center_and_sigma():
    # Centre 100, sigma 2: 107 is 3.5 sigma above, 105 is 2.5 sigma above.
    table = check_rules([100, 107, 105], center=100, sigma=2)
    assert table["rule_1"].tolist() == [False, True, False]
    # 107 and 105 are both beyond 2 sigma (104): rule 2 at the third point.
    assert table["rule_2"].tolist() == [False, False, True]


def test_check_rules_rejects_zero_sigma():
    with pytest.raises(ValueError):
        check_rules([1, 2, 3], center=2, sigma=0)


def test_summarise_rules_lists_every_broken_rule():
    # Two points at 3.5 sigma: the second breaks rule 1 and rule 2.
    summary = summarise_rules(rules_for([3.5, 3.5, 0]))
    assert summary["ooc_flag"].tolist() == [True, True, False]
    assert summary["rule_violated"].tolist() == ["Rule 1", "Rule 1; Rule 2", ""]


def test_k_of_n_beyond_handles_the_start_of_the_series():
    # Only two points exist, both beyond: "2 of the last 3" is satisfied.
    flags = k_of_n_beyond([2.5, 2.5], k=2, n=3, threshold=2)
    assert flags.tolist() == [False, True]
