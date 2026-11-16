# Power BI dashboard guide

Step-by-step instructions for building the dashboard in Power BI Desktop from
the four CSV files in `data/processed/`.

> **Not tested in Power BI.** This guide was written without access to Power BI
> Desktop. The data facts and check values below come from the CSV files, but
> the DAX has not been executed and menu names change between versions. Where
> a menu is named differently on your version, look for the closest match, and
> use the check values in section 7 to confirm each page.

## 1. The tables

| File | One row per | Rows | Key column(s) |
|---|---|---|---|
| `fact_measurements.csv` | run and feature | 15,628 | `feature`, `date` |
| `dim_feature.csv` | feature | 10 | `feature` |
| `feature_stage_summary.csv` | feature and stage | 20 | `feature` |
| `daily_pass_rate.csv` | production day | 86 | `date` |

Column notes:

- `feature` is an anonymised sensor name such as `f059`. It is the column
  position in the raw file, not a physical quantity.
- `stage` is 1 for runs 1 to 500 and 2 for runs 501 to 1567. The split is an
  assumption made after seeing a level shift on the control charts.
- `center`, `ucl`, `lcl` in the fact table are the control limits of that
  row's stage. They are the same on every row of a feature and stage.
- `lsl_assumed`, `usl_assumed`, `cp`, `cpk`, `pp`, `ppk` rest on **assumed**
  spec limits (passing-run mean ± 3 sigma). SECOM has no published specs.

## 2. Load the data

1. **Home > Get data > Text/CSV**, pick `fact_measurements.csv`, then
   **Transform Data** (not Load) so you can check the column types.
2. Repeat for the other three files.
3. In Power Query, set these types:

| Table | Column(s) | Type |
|---|---|---|
| all tables that have it | `stage` | Text |
| fact_measurements | `timestamp` | Date/Time |
| fact_measurements, daily_pass_rate | `date` | Date |
| fact_measurements | `run_id` | Whole number |
| fact_measurements | `ooc_flag`, `in_baseline`, `mr_ooc` | True/False |
| dim_feature | `significant`, `has_control_chart` | True/False |
| dim_feature | `rank` | Whole number |
| all | measurement and statistic columns | Decimal number |

   `stage` is set to Text so Power BI treats it as a label and never sums it.

4. If your Windows region uses a decimal comma, numbers such as `0.7222` may
   load as text. Fix it with **Change Type > Using Locale > English (United
   States)**.
5. **Close & Apply**.

## 3. Data model

Open **Model view** and create three relationships. Power BI may detect some
automatically; check each one and delete any others.

| From (one side) | To (many side) | Cardinality | Cross-filter |
|---|---|---|---|
| `dim_feature[feature]` | `fact_measurements[feature]` | One to many | Single |
| `dim_feature[feature]` | `feature_stage_summary[feature]` | One to many | Single |
| `daily_pass_rate[date]` | `fact_measurements[date]` | One to many | Single |

Why this shape:

- `dim_feature` has one row per feature, so a single feature slicer built on
  it filters both the fact table and the summary table.
- The summary is separate from `dim_feature` because limits and Cpk exist per
  stage, while rank and p-value exist once per feature.
- `daily_pass_rate[date]` only lists the 86 days that had production. Do not
  mark it as a date table and do not use time-intelligence functions on it.

Then set the feature sort order: select `dim_feature[feature]`, and under
**Column tools > Sort by column** choose `rank`. Features now appear in rank
order everywhere.

## 4. DAX measures

Create each with **Modeling > New measure**. The home table is a suggestion.

### Pass rate (home table: daily_pass_rate)

```DAX
Total Runs = SUM ( daily_pass_rate[n_runs] )

Passing Runs = SUM ( daily_pass_rate[n_pass] )

Failing Runs = SUM ( daily_pass_rate[n_fail] )

Pass Rate = DIVIDE ( [Passing Runs], [Total Runs] )
```

Format `Pass Rate` as a percentage with one decimal.

These use the daily table on purpose. The fact table repeats every run once
per feature (and skips missing readings), so counting passes there is wrong.
`DIVIDE` also weights each day by its number of runs, which averaging the
`pass_rate` column would not.

### Out of control (home table: fact_measurements)

```DAX
Readings = COUNTROWS ( fact_measurements )

OOC Count =
CALCULATE (
    COUNTROWS ( fact_measurements ),
    fact_measurements[ooc_flag] = TRUE ()
)

OOC Rate = DIVIDE ( [OOC Count], [Readings] )

Rule 1 Count =
COUNTROWS (
    FILTER (
        fact_measurements,
        CONTAINSSTRING ( fact_measurements[rule_violated], "Rule 1" )
    )
)
```

Copy `Rule 1 Count` for rules 2, 3 and 4. `CONTAINSSTRING` is needed because
one point can break several rules, e.g. `Rule 1; Rule 2`.

Format `OOC Rate` as a percentage.

### Control chart lines (home table: fact_measurements)

```DAX
Value = AVERAGE ( fact_measurements[value] )

UCL = AVERAGE ( fact_measurements[ucl] )

Centre Line = AVERAGE ( fact_measurements[center] )

LCL = AVERAGE ( fact_measurements[lcl] )

OOC Value =
CALCULATE (
    AVERAGE ( fact_measurements[value] ),
    fact_measurements[ooc_flag] = TRUE ()
)

Moving Range = AVERAGE ( fact_measurements[moving_range] )

MR UCL = AVERAGE ( fact_measurements[mr_ucl] )
```

With one feature selected there is one row per run, so the average of one
row is simply that row's value. `OOC Value` is blank for in-control runs,
which lets it be drawn as a separate series of markers.

### Capability (home table: feature_stage_summary)

```DAX
Cp = MIN ( feature_stage_summary[cp] )

Cpk = MIN ( feature_stage_summary[cpk] )

Pp = MIN ( feature_stage_summary[pp] )

Ppk = MIN ( feature_stage_summary[ppk] )
```

Each feature and stage has one row, so `MIN` returns that row's value. If
the stages are not split out, it returns the worse of the two stages, which
is the cautious choice.

## 5. Pages

Use the same colours on every page: blue for measurements, red for
out-of-control points, dark grey for limits.

### Page 1: Pass-rate trend

1. Three **Card** visuals: `Total Runs`, `Failing Runs`, `Pass Rate`.
2. **Line chart**: X-axis `daily_pass_rate[date]`, Y-axis `Pass Rate`.
   If the X-axis shows a Year/Quarter/Month hierarchy, open the field's
   dropdown in the X-axis well and choose `date` instead of
   `Date Hierarchy`.
3. Add `Total Runs` to the chart's **Tooltips**.
4. Under it, a **Clustered column chart**: X-axis `daily_pass_rate[date]`,
   Y-axis `Total Runs`. Days with one or two runs explain the spikes to 0%
   or 100% above. Use two separate charts, not a combined chart with two
   Y-axes.
5. Optional: in the **Analytics** pane of the line chart, add an **X-axis
   constant line** at 29 Aug 2008 and label it "Stage 2". Run 501 is the
   last run of 28 Aug (23:42), so 29 Aug is the first full day of stage 2.
   This option only appears when the X-axis is a continuous date.

### Page 2: Top failing features

1. **Clustered bar chart**: Y-axis `dim_feature[feature]`, X-axis
   `dim_feature[prob_fail_higher]`. Sort the Y-axis by feature, ascending;
   because of the sort-by-column setting this is rank order.
2. In **Analytics**, add a constant line at 0.5 labelled "No difference".
   Bars right of the line mean fail runs tend to read higher; bars left of
   it mean lower.
3. **Table** visual with `rank`, `feature`, `median_pass`, `median_fail`,
   `prob_fail_higher`, `p_adjusted`, `p_adjusted_stage1`,
   `p_adjusted_stage2`. Set each numeric column to **Don't summarize**.
4. Add a **Text box** with this caveat:
   "Ranked over all runs. Tested inside each stage, only one group of
   near-duplicate features (f477, f205, f341) stays significant, and only
   in stage 1. Much of the overall ranking reflects early runs differing
   from late runs. Association is not causation."

### Page 3: Control chart per feature

1. **Slicer** on `dim_feature[feature]`. In the slicer's format options set
   **Selection > Single select** on. The chart measures only make sense for
   one feature at a time.
2. **Line chart** (Individuals chart): X-axis `fact_measurements[run_id]`,
   Y-axis `Value`, `UCL`, `Centre Line`, `LCL`, `OOC Value`. Check that the
   X-axis type is **Continuous**.
3. Format the series:
   - `Value`: blue, thin line.
   - `UCL`, `Centre Line`, `LCL`: dark grey.
   - `OOC Value`: red, markers on, and line stroke width 0 so only the
     markers show. This setting is per series and sits under **Lines** or
     **Shapes** depending on the version.
   - Turn markers off for the other four series.
4. Add `fact_measurements[timestamp]`, `pass_fail` and `rule_violated` to
   **Tooltips** (as First or Don't summarize).
5. Optional: an **X-axis constant line** at 501 labelled "Stage 2".
6. Second **Line chart** (Moving Range chart) below it: X-axis `run_id`,
   Y-axis `Moving Range` and `MR UCL`.
7. **Cards**: `OOC Count`, `OOC Rate`.
8. **Clustered column chart**: X-axis `fact_measurements[rule_violated]`,
   Y-axis `Readings`, with a visual-level filter excluding `No violation`.
   Add `fact_measurements[stage]` as the legend to compare the stages.

The step in the limit lines at run 501 is the stage change, not an error.

### Page 4: Capability table

1. Page title: "Process capability against ASSUMED spec limits
   (passing-run mean ± 3 sigma). Not engineering specs."
2. **Matrix**: Rows `dim_feature[feature]`, Columns
   `feature_stage_summary[stage]`, Values `Cp`, `Cpk`, `Pp`, `Ppk`.
3. Conditional formatting on `Cpk`: in the Values well open the dropdown on
   `Cpk` > **Conditional formatting > Background color**. Set **Format
   style** to **Rules**, base it on `Cpk`, and switch each rule from
   Percent to **Number**:

| Rule | Colour | Meaning |
|---|---|---|
| value >= 0 and < 1 | red | spread or centring does not fit the assumed window |
| value >= 1 and < 1.33 | amber | fits with little margin |
| value >= 1.33 | green | fits with margin |

   Add the same thresholds as text in a legend near the matrix, so the
   colour is never the only cue.
4. **Table** visual with `feature`, `stage`, `mean`, `lsl_assumed`,
   `usl_assumed`, `fraction_outside_spec`, each set to Don't summarize.
5. Text box: "Cp and Cpk use short-term sigma. Pp and Ppk use overall
   sigma. Cpk well above Ppk means the feature drifts or spikes over time."

## 6. Finishing touches

- Give every visual a plain title that says what it shows.
- Put the stage definition and the assumed-spec note where a reader will
  see them, not only in this guide.
- Turn off **Auto date/time** (File > Options > Data Load) if you want a
  smaller model; nothing here depends on it.

## 7. Check values

Use these to confirm each page before trusting the dashboard. All come from
the CSV files.

| What | Expected |
|---|---|
| `Total Runs`, no filters | 1,567 |
| `Failing Runs`, no filters | 104 |
| `Pass Rate`, no filters | 93.4% |
| `Readings`, no filters | 15,628 |
| `OOC Count`, no filters | 3,922 |
| `OOC Count`, feature f059 | 233 |
| `OOC Count`, feature f103 | 418 |
| `OOC Count`, feature f129 | 730 |
| `Cpk`, f059 stage 1 | 0.71 |
| `Cpk`, f059 stage 2 | 2.64 |
| f059 `UCL`, stage 1 / stage 2 | 43.95 / 10.71 |

If `Total Runs` changes when you pick a feature, a relationship is wrong:
the feature slicer must not filter the daily table.

## References

- Microsoft Learn, conditional formatting in tables and matrices:
  https://learn.microsoft.com/power-bi/create-reports/desktop-conditional-table-formatting
