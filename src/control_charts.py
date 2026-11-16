"""Step 4: I-MR control charts for the features most associated with failures.

Run:  python src/control_charts.py   (after src/feature_ranking.py)

Outputs:
  reports/figures/imr_<feature>.png   one chart per feature
  reports/control_limits.csv          limits and out-of-control counts
"""

import matplotlib.pyplot as plt
import pandas as pd

from config import (
    BASELINE_RUNS,
    CLEAN_FILE,
    CONTROL_LIMITS_FILE,
    CORRELATION_LIMIT,
    FEATURE_RANKING_FILE,
    FIGURES_DIR,
    TOP_N_CHARTS,
)
from spc_rules import check_rules, imr_limits, moving_range, summarise_rules

# Chart colours (checked for colour-blind separation).
COLOR_DATA = "#2a78d6"     # blue: measurements
COLOR_OOC = "#d03b3b"      # red: out-of-control points
COLOR_LIMIT = "#52514e"    # dark grey: centre line and control limits
COLOR_GRID = "#e1e0d9"
COLOR_BASELINE = "#f0efec" # light grey band behind the baseline period
COLOR_TEXT = "#52514e"


def select_chart_features(ranking, data, n=TOP_N_CHARTS, limit=CORRELATION_LIMIT):
    """Pick the top-ranked features, skipping near-duplicates.

    Walk down the ranking. Keep a feature only if its rank correlation with
    every feature already kept is at or below the limit.
    """
    chosen = []
    for feature in ranking["feature"]:
        is_duplicate = False
        for kept in chosen:
            correlation = data[feature].corr(data[kept], method="spearman")
            if abs(correlation) > limit:
                print(f"  skipped {feature}: correlation {correlation:.2f} with {kept}")
                is_duplicate = True
                break
        if not is_duplicate:
            chosen.append(feature)
        if len(chosen) == n:
            break
    return chosen


def spc_for_feature(data, feature, baseline_runs=BASELINE_RUNS):
    """Compute control limits and rule violations for one feature.

    Returns (points, limits):
      points  one row per run that has a reading, in time order
      limits  dictionary from imr_limits()
    """
    # Runs with no reading for this feature are left out. We do not fill
    # them in, because an invented value would look like a measurement.
    points = data[["run_id", "timestamp", "pass_fail", feature]].dropna(subset=[feature])
    points = points.rename(columns={feature: "value"}).reset_index(drop=True)
    points.insert(3, "feature", feature)

    # Limits come from the baseline runs only, then apply to every run.
    points["in_baseline"] = points["run_id"] <= baseline_runs
    limits = imr_limits(points.loc[points["in_baseline"], "value"])

    points["moving_range"] = moving_range(points["value"])
    points["mr_ooc"] = points["moving_range"] > limits["mr_ucl"]

    rules = check_rules(points["value"], limits["center"], limits["sigma"])
    points = pd.concat([points, rules, summarise_rules(rules)], axis=1)
    return points, limits


def summarise_feature(points, limits, feature):
    """One row of numbers describing the chart for a feature."""
    monitored = points[~points["in_baseline"]]
    ooc = points[points["ooc_flag"]]
    in_control = points[~points["ooc_flag"]]

    return {
        "feature": feature,
        "center": limits["center"],
        "sigma": limits["sigma"],
        "ucl": limits["ucl"],
        "lcl": limits["lcl"],
        "mr_center": limits["mr_center"],
        "mr_ucl": limits["mr_ucl"],
        "n_points": len(points),
        "n_baseline": int(points["in_baseline"].sum()),
        "n_ooc": len(ooc),
        "ooc_rate": len(ooc) / len(points),
        "ooc_rate_baseline": points.loc[points["in_baseline"], "ooc_flag"].mean(),
        "ooc_rate_monitoring": monitored["ooc_flag"].mean(),
        "n_rule_1": int(points["rule_1"].sum()),
        "n_rule_2": int(points["rule_2"].sum()),
        "n_rule_3": int(points["rule_3"].sum()),
        "n_rule_4": int(points["rule_4"].sum()),
        "n_mr_ooc": int(points["mr_ooc"].sum()),
        # Do flagged runs fail more often than unflagged runs?
        "fail_rate_ooc": (ooc["pass_fail"] == "Fail").mean(),
        "fail_rate_in_control": (in_control["pass_fail"] == "Fail").mean(),
    }


def style_axis(ax):
    """Quiet axes: light grid, no box, grey tick labels."""
    ax.grid(axis="y", color=COLOR_GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.tick_params(colors=COLOR_TEXT, length=0)


def plot_imr(points, limits, feature, path, baseline_runs=BASELINE_RUNS):
    """Draw the Individuals chart (top) and Moving Range chart (bottom)."""
    fig, (ax_i, ax_mr) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True, height_ratios=[2, 1]
    )
    x = points["run_id"]
    last_x = x.max()

    # --- Individuals chart ---
    ax_i.axvspan(0, baseline_runs, color=COLOR_BASELINE, zorder=0)
    ax_i.plot(x, points["value"], color=COLOR_DATA, linewidth=0.8, label="Measurement")

    ooc = points[points["ooc_flag"]]
    ax_i.scatter(
        ooc["run_id"], ooc["value"], s=12, color=COLOR_OOC, edgecolor="white",
        linewidth=0.4, zorder=3, label="Out of control (any rule)",
    )

    # The three horizontal lines: upper limit, centre line, lower limit.
    # Their values go in the title, where they cannot overlap each other.
    for key in ["ucl", "center", "lcl"]:
        ax_i.axhline(limits[key], color=COLOR_LIMIT, linewidth=1)

    ax_i.set_title(
        f"{feature}: Individuals chart  "
        f"({len(ooc)} of {len(points)} runs out of control)\n"
        f"UCL {limits['ucl']:.4g}   CL {limits['center']:.4g}   "
        f"LCL {limits['lcl']:.4g}",
        loc="left", fontsize=11, color="#0b0b0b",
    )
    ax_i.set_ylabel("Value", color=COLOR_TEXT)
    ax_i.legend(loc="upper right", frameon=False, fontsize=9)
    ax_i.text(
        baseline_runs / 2, 0.97, f"Baseline: first {baseline_runs} runs",
        transform=ax_i.get_xaxis_transform(), ha="center", va="top",
        fontsize=9, color=COLOR_TEXT,
    )
    style_axis(ax_i)

    # --- Moving Range chart ---
    ax_mr.axvspan(0, baseline_runs, color=COLOR_BASELINE, zorder=0)
    ax_mr.plot(x, points["moving_range"], color=COLOR_DATA, linewidth=0.8)

    mr_ooc = points[points["mr_ooc"]]
    ax_mr.scatter(
        mr_ooc["run_id"], mr_ooc["moving_range"], s=12, color=COLOR_OOC,
        edgecolor="white", linewidth=0.4, zorder=3,
    )

    for key in ["mr_ucl", "mr_center"]:
        ax_mr.axhline(limits[key], color=COLOR_LIMIT, linewidth=1)

    ax_mr.set_title(
        f"Moving Range chart  ({len(mr_ooc)} above UCL)\n"
        f"UCL {limits['mr_ucl']:.4g}   CL {limits['mr_center']:.4g}",
        loc="left", fontsize=11, color="#0b0b0b",
    )
    ax_mr.set_ylabel("Moving range", color=COLOR_TEXT)
    ax_mr.set_xlabel("Run number (time order)", color=COLOR_TEXT)
    ax_mr.set_xlim(0, last_x)
    style_axis(ax_mr)

    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def main():
    data = pd.read_csv(CLEAN_FILE, parse_dates=["timestamp"])
    ranking = pd.read_csv(FEATURE_RANKING_FILE)

    print("Selecting chart features:")
    features = select_chart_features(ranking, data)
    print(f"  chosen: {features}")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for feature in features:
        points, limits = spc_for_feature(data, feature)
        plot_imr(points, limits, feature, FIGURES_DIR / f"imr_{feature}.png")
        summaries.append(summarise_feature(points, limits, feature))

    summary = pd.DataFrame(summaries)
    summary.to_csv(CONTROL_LIMITS_FILE, index=False)

    print(f"\nBaseline: first {BASELINE_RUNS} runs")
    columns = ["feature", "center", "sigma", "lcl", "ucl", "n_ooc", "ooc_rate",
               "ooc_rate_baseline", "ooc_rate_monitoring"]
    print(summary[columns].round(4).to_string(index=False))
    print("\nViolations by rule, and fail rate of flagged vs unflagged runs:")
    columns = ["feature", "n_rule_1", "n_rule_2", "n_rule_3", "n_rule_4",
               "n_mr_ooc", "fail_rate_ooc", "fail_rate_in_control"]
    print(summary[columns].round(4).to_string(index=False))
    print(f"\nSaved charts to {FIGURES_DIR}")
    print(f"Saved {CONTROL_LIMITS_FILE}")


if __name__ == "__main__":
    main()
