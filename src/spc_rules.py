"""Reusable SPC functions: I-MR control limits and Western Electric rules.

These functions know nothing about SECOM. They take plain lists or arrays of
numbers in time order, with no missing values, so they can be tested with
small hand-made examples (see tests/test_spc_rules.py).
"""

import numpy as np
import pandas as pd

# Constants for a moving range of 2 consecutive points (standard SPC tables).
D2 = 1.128  # average moving range / D2 estimates sigma
D4 = 3.267  # average moving range * D4 is the upper limit of the MR chart


def moving_range(values):
    """Absolute change from each point to the next.

    The first point has no previous point, so its moving range is NaN.
    Example: [1, 3, 2] -> [NaN, 2, 1]
    """
    values = np.asarray(values, dtype=float)
    return np.abs(np.diff(values, prepend=np.nan))


def imr_limits(baseline_values):
    """Control limits for an I-MR chart, computed from a baseline period.

    Sigma is estimated from the average moving range, not the ordinary
    standard deviation. The moving range only sees run-to-run noise, so a
    slow drift inside the baseline does not inflate the limits.
    """
    values = np.asarray(baseline_values, dtype=float)
    if len(values) < 2:
        raise ValueError("Need at least 2 baseline points")

    center = values.mean()
    mr_bar = np.abs(np.diff(values)).mean()  # average moving range
    sigma = mr_bar / D2

    return {
        "center": center,
        "sigma": sigma,
        "ucl": center + 3 * sigma,  # upper control limit, Individuals chart
        "lcl": center - 3 * sigma,  # lower control limit, Individuals chart
        "mr_center": mr_bar,
        "mr_ucl": D4 * mr_bar,      # upper limit, Moving Range chart
    }


def k_of_n_beyond(z, k, n, threshold):
    """Flag points that complete a 'k of the last n beyond threshold' pattern.

    z holds each point's distance from the centre line in sigma units.
    A point is flagged when:
      - it is itself beyond the threshold, and
      - at least k of the last n points (including it) are beyond the
        threshold on the SAME side of the centre line.
    All four Western Electric rules are this pattern with different numbers.
    """
    z = np.asarray(z, dtype=float)
    flags = np.zeros(len(z), dtype=bool)

    for side in (+1, -1):  # check above the centre line, then below
        beyond = side * z > threshold
        for i in range(len(z)):
            start = max(0, i - n + 1)  # first point of the window ending at i
            if beyond[i] and beyond[start : i + 1].sum() >= k:
                flags[i] = True

    return flags


def check_rules(values, center, sigma):
    """Apply the four Western Electric rules to a series of values.

    Returns a table with one row per point and one True/False column per rule.
    """
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    # Distance of every point from the centre line, in sigma units.
    z = (np.asarray(values, dtype=float) - center) / sigma

    return pd.DataFrame(
        {
            # Rule 1: one point beyond 3 sigma.
            "rule_1": k_of_n_beyond(z, k=1, n=1, threshold=3),
            # Rule 2: 2 of 3 consecutive points beyond 2 sigma, same side.
            "rule_2": k_of_n_beyond(z, k=2, n=3, threshold=2),
            # Rule 3: 4 of 5 consecutive points beyond 1 sigma, same side.
            "rule_3": k_of_n_beyond(z, k=4, n=5, threshold=1),
            # Rule 4: 8 consecutive points on the same side of the centre.
            "rule_4": k_of_n_beyond(z, k=8, n=8, threshold=0),
        }
    )


def summarise_rules(rule_table):
    """Turn the four rule columns into the two columns Power BI needs.

    ooc_flag:       True if the point broke any rule (out of control).
    rule_violated:  text such as "Rule 1" or "Rule 1; Rule 4", or "" if none.
    """
    names = {
        "rule_1": "Rule 1",
        "rule_2": "Rule 2",
        "rule_3": "Rule 3",
        "rule_4": "Rule 4",
    }

    texts = []
    for _, row in rule_table.iterrows():
        broken = [names[column] for column in names if row[column]]
        texts.append("; ".join(broken))

    return pd.DataFrame(
        {
            "ooc_flag": rule_table[list(names)].any(axis=1).to_numpy(),
            "rule_violated": texts,
        }
    )
