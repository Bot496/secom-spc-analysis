"""Step 4: I-MR control charts for the features most associated with failures.

Run:  python src/control_charts.py   (after src/feature_ranking.py)

The charts use two stages (see STAGE_2_START in config.py). Each stage has
its own control limits, computed from the first runs of that stage.

Outputs:
  reports/figures/imr_<feature>.png   one chart per feature
  reports/control_limits.csv          limits and out-of-control counts,
                                      one row per feature and stage
"""

import matplotlib.pyplot as plt
import pandas as pd

from config import (
    CLEAN_FILE,
    CONTROL_LIMITS_FILE,
    CORRELATION_LIMIT,
    FEATURE_RANKING_FILE,
    FIGURES_DIR,
    TOP_N_CHARTS,
)
from spc_rules import check_rules, imr_limits, moving_range, summarise_rules
from stages import add_stage_columns

# Chart colours (checked for colour-blind separation).
COLOR_DATA = "#2a78d6"      # blue: measurements
COLOR_OOC = "#d03b3b"       # red: out-of-control points
COLOR_LIMIT = "#52514e"     # dark grey: centre line and control limits
COLOR_GRID = "#e1e0d9"
COLOR_BASELINE = "#f0efec"  # light grey band behind each baseline period
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


def spc_for_feature(data, feature):
    """Compute staged control limits and rule violations for one feature.

    Returns one row per run that has a reading, in time order. Each row
    carries the limits of its own stage, so a chart can draw them directly.
    """
    # Runs with no reading for this feature are left out. We do not fill
    # them in, because an invented value would look like a measurement.
    points = data[["run_id", "timestamp", "pass_fail", feature]].dropna(subset=[feature])
    points = points.rename(columns={feature: "value"}).reset_index(drop=True)
    points.insert(3, "feature", feature)

    points = add_stage_columns(points)
    points["moving_range"] = moving_range(points["value"])

    stage_tables = []
    for _, stage_points in points.groupby("stage"):
        stage_points = stage_points.reset_index(drop=True)

        # Limits come from this stage's baseline runs only.
        baseline = stage_points.loc[stage_points["in_baseline"], "value"]
        limits = imr_limits(baseline)

        # Write the limits on every row of the stage.
        for name, value in limits.items():
            stage_points[name] = value

        stage_points["mr_ooc"] = stage_points["moving_range"] > limits["mr_ucl"]

        # The rules run inside the stage, so a pattern such as "8 in a row"
        # never mixes points judged against different centre lines.
        rules = check_rules(stage_points["value"], limits["center"], limits["sigma"])
        stage_tables.append(
            pd.concat([stage_points, rules, summarise_rules(rules)], axis=1)
        )

    return pd.concat(stage_tables, ignore_index=True)


def summarise_stage(stage_points):
    """One row of numbers describing one feature in one stage."""
    first = stage_points.iloc[0]
    after_baseline = stage_points[~stage_points["in_baseline"]]
    ooc = stage_points[stage_points["ooc_flag"]]
    in_control = stage_points[~stage_points["ooc_flag"]]

    return {
        "feature": first["feature"],
        "stage": first["stage"],
        "first_run": stage_points["run_id"].min(),
        "last_run": stage_points["run_id"].max(),
        "center": first["center"],
        "sigma": first["sigma"],
        "ucl": first["ucl"],
        "lcl": first["lcl"],
        "mr_center": first["mr_center"],
        "mr_ucl": first["mr_ucl"],
        "n_points": len(stage_points),
        "n_baseline": int(stage_points["in_baseline"].sum()),
        "n_ooc": len(ooc),
        "ooc_rate": len(ooc) / len(stage_points),
        "ooc_rate_baseline": stage_points.loc[stage_points["in_baseline"], "ooc_flag"].mean(),
        "ooc_rate_after_baseline": after_baseline["ooc_flag"].mean(),
        "n_rule_1": int(stage_points["rule_1"].sum()),
        "n_rule_2": int(stage_points["rule_2"].sum()),
        "n_rule_3": int(stage_points["rule_3"].sum()),
        "n_rule_4": int(stage_points["rule_4"].sum()),
        "n_mr_ooc": int(stage_points["mr_ooc"].sum()),
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


def draw_stage_lines(ax, points, columns):
    """Shade each stage's baseline and draw its limit lines."""
    for stage, stage_points in points.groupby("stage"):
        first_run = stage_points["run_id"].min()
        last_run = stage_points["run_id"].max()
        baseline_end = stage_points.loc[stage_points["in_baseline"], "run_id"].max()

        # Only the first band gets a legend entry, so it is listed once.
        label = "Baseline period" if stage == 1 else None
        ax.axvspan(first_run, baseline_end, color=COLOR_BASELINE, zorder=0, label=label)
        for column in columns:
            ax.hlines(
                stage_points[column].iloc[0], first_run, last_run,
                color=COLOR_LIMIT, linewidth=1,
            )


def limits_text(points, columns, separator):
    """Text such as 'Stage 1: UCL 43.95  CL 11.65  LCL -20.66' per stage."""
    labels = {"ucl": "UCL", "center": "CL", "lcl": "LCL",
              "mr_ucl": "UCL", "mr_center": "CL"}
    parts = []
    for stage, stage_points in points.groupby("stage"):
        values = "  ".join(
            f"{labels[column]} {stage_points[column].iloc[0]:.4g}" for column in columns
        )
        parts.append(f"Stage {stage}: {values}")
    return separator.join(parts)


def plot_imr(points, feature, path):
    """Draw the Individuals chart (top) and Moving Range chart (bottom)."""
    fig, (ax_i, ax_mr) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True, height_ratios=[2, 1]
    )
    x = points["run_id"]

    # --- Individuals chart ---
    i_columns = ["ucl", "center", "lcl"]
    draw_stage_lines(ax_i, points, i_columns)
    ax_i.plot(x, points["value"], color=COLOR_DATA, linewidth=0.8, label="Measurement")

    ooc = points[points["ooc_flag"]]
    ax_i.scatter(
        ooc["run_id"], ooc["value"], s=12, color=COLOR_OOC, edgecolor="white",
        linewidth=0.4, zorder=3, label="Out of control (any rule)",
    )

    ax_i.set_title(
        f"{feature}: Individuals chart  "
        f"({len(ooc)} of {len(points)} runs out of control)\n"
        f"{limits_text(points, i_columns, separator='\n')}",
        loc="left", fontsize=11, color="#0b0b0b",
    )
    ax_i.set_ylabel("Value", color=COLOR_TEXT)
    # Legend sits above the plot, on the right, so it never covers data.
    ax_i.legend(
        loc="lower right", bbox_to_anchor=(1, 1), ncol=3, frameon=False, fontsize=9
    )
    style_axis(ax_i)

    # --- Moving Range chart ---
    mr_columns = ["mr_ucl", "mr_center"]
    draw_stage_lines(ax_mr, points, mr_columns)
    ax_mr.plot(x, points["moving_range"], color=COLOR_DATA, linewidth=0.8)

    mr_ooc = points[points["mr_ooc"]]
    ax_mr.scatter(
        mr_ooc["run_id"], mr_ooc["moving_range"], s=12, color=COLOR_OOC,
        edgecolor="white", linewidth=0.4, zorder=3,
    )

    ax_mr.set_title(
        f"Moving Range chart  ({len(mr_ooc)} above UCL)\n"
        f"{limits_text(points, mr_columns, separator='      ')}",
        loc="left", fontsize=11, color="#0b0b0b",
    )
    ax_mr.set_ylabel("Moving range", color=COLOR_TEXT)
    ax_mr.set_xlabel("Run number (time order)", color=COLOR_TEXT)
    ax_mr.set_xlim(0, x.max())
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
        points = spc_for_feature(data, feature)
        plot_imr(points, feature, FIGURES_DIR / f"imr_{feature}.png")
        for _, stage_points in points.groupby("stage"):
            summaries.append(summarise_stage(stage_points))

    summary = pd.DataFrame(summaries)
    summary.to_csv(CONTROL_LIMITS_FILE, index=False)

    print("\nLimits and out-of-control (OOC) rates per stage:")
    columns = ["feature", "stage", "first_run", "last_run", "center", "sigma",
               "lcl", "ucl", "n_ooc", "ooc_rate_baseline", "ooc_rate_after_baseline"]
    print(summary[columns].round(4).to_string(index=False))
    print("\nViolations by rule, and fail rate of flagged vs unflagged runs:")
    columns = ["feature", "stage", "n_rule_1", "n_rule_2", "n_rule_3", "n_rule_4",
               "n_mr_ooc", "fail_rate_ooc", "fail_rate_in_control"]
    print(summary[columns].round(4).to_string(index=False))
    print(f"\nSaved charts to {FIGURES_DIR}")
    print(f"Saved {CONTROL_LIMITS_FILE}")


if __name__ == "__main__":
    main()
