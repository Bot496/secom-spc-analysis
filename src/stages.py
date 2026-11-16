"""Split the runs into two stages (before and after the process change).

Used by the control charts and by the per-stage feature comparison, so both
use exactly the same definition.
"""

import numpy as np

from config import BASELINE_RUNS, STAGE_2_START


def add_stage_columns(table, stage_2_start=STAGE_2_START, baseline_runs=BASELINE_RUNS):
    """Return a copy of the table with 'stage' and 'in_baseline' columns.

    stage        1 for runs before stage_2_start, 2 from stage_2_start on
    in_baseline  True for the first baseline_runs runs of each stage
    """
    table = table.copy()
    run_id = table["run_id"]

    table["stage"] = np.where(run_id < stage_2_start, 1, 2)

    # First run number of the stage each row belongs to: 1 or stage_2_start.
    stage_first_run = np.where(table["stage"] == 1, 1, stage_2_start)
    table["in_baseline"] = run_id < stage_first_run + baseline_runs
    return table
