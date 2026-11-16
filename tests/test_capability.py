"""Tests for the capability functions, using examples worked out by hand."""

import pytest

from capability import assumed_spec_limits, capability_indices

# Values that alternate 10, 12:
#   mean = 11
#   every moving range = 2, so sigma_within = 2 / 1.128 = 1.773
ALTERNATING = [10.0, 12.0] * 5
SIGMA_WITHIN = 2 / 1.128


def test_assumed_spec_limits_by_hand():
    # Values 1, 2, 3: mean 2, sample standard deviation 1.
    lsl, usl = assumed_spec_limits([1.0, 2.0, 3.0], k=3)
    assert lsl == pytest.approx(-1.0)   # 2 - 3 * 1
    assert usl == pytest.approx(5.0)    # 2 + 3 * 1


def test_wider_multiplier_gives_wider_limits():
    lsl, usl = assumed_spec_limits([1.0, 2.0, 3.0], k=4)
    assert (lsl, usl) == pytest.approx((-2.0, 6.0))


def test_centred_process_has_cp_equal_to_cpk():
    # Spec 5 to 17: the mean (11) is exactly in the middle.
    result = capability_indices(ALTERNATING, lsl=5, usl=17)

    assert result["mean"] == pytest.approx(11.0)
    assert result["sigma_within"] == pytest.approx(SIGMA_WITHIN)
    assert result["cp"] == pytest.approx(12 / (6 * SIGMA_WITHIN))   # 1.128
    assert result["cpk"] == pytest.approx(result["cp"])


def test_off_centre_process_has_high_cp_but_low_cpk():
    # Same spread and same spec width (12), but the window is 9 to 21,
    # so the mean (11) sits only 2 units above the lower limit.
    result = capability_indices(ALTERNATING, lsl=9, usl=21)

    assert result["cp"] == pytest.approx(12 / (6 * SIGMA_WITHIN))   # unchanged
    assert result["cpk"] == pytest.approx(2 / (3 * SIGMA_WITHIN))   # 0.376
    assert result["cpk"] < result["cp"]


def test_drifting_process_has_ppk_below_cpk():
    # A steady climb: each step is small (moving range 1), but the values
    # travel a long way overall. Short-term sigma is small, overall is large.
    climbing = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    result = capability_indices(climbing, lsl=-10, usl=21)

    assert result["sigma_within"] == pytest.approx(1 / 1.128)
    assert result["sigma_overall"] > result["sigma_within"]
    assert result["ppk"] < result["cpk"]


def test_fraction_outside_spec_is_counted():
    # Values 1 to 10 with limits 2.5 to 8.5: 1, 2, 9 and 10 are outside,
    # which is 4 of 10.
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    result = capability_indices(values, lsl=2.5, usl=8.5)
    assert result["fraction_outside_spec"] == pytest.approx(0.4)


def test_constant_values_are_rejected():
    with pytest.raises(ValueError):
        capability_indices([5.0, 5.0, 5.0], lsl=0, usl=10)
