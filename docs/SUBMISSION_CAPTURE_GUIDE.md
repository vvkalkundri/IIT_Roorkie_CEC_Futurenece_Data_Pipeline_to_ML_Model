# Submission screenshots and SQL/results guide

The SQL has already been executed read-only against both local warehouses. Full results are in [ETL results](business_results/etl_results.md) and [ELT results](business_results/elt_results.md). No source data or warehouse was changed. The selected run in each is `scheduled__2026-10-29T03:30:00+00:00`; these are captured results, not a promise that later runs will be identical.

## 1. Capture the Airflow evidence

Open your existing Astro Airflow browser tab. Select the main `nammamart_etl_vijayc5` or `nammamart_elt_vijayc5` DAG, rather than the unscheduled observability aliases. Use the successful 29 October scheduled run where available.

For each DAG, select the successful run, open **Graph**, close the task detail panel if it obscures nodes, and use fit-to-screen. Keep the DAG name, run ID and every green task visible. Then return to the DAG overview/details and capture its schedule and next run. Your existing UI uses a clock control at bottom left: choose IST/local time and keep `+05:30` visible. The cron should be `0 9 * * 1-6` and the next run should be 09:00 on a Monday–Saturday. If the UI is in UTC, 03:30 is equivalent; label that explicitly.

Save captures under `docs/screenshots/` using the names below. On macOS, Shift–Command–4 lets you capture a selected area. Include the relevant application context and avoid unrelated browser tabs/bookmarks.

| Suggested filename | Required visible evidence | Existing image coverage |
| --- | --- | --- |
| `01_etl_graph.png` | Main ETL DAG, successful run ID, all nine green tasks | The 25 October 12:41:07 AM image already shows this; a current-run capture is preferable |
| `02_elt_graph.png` | Main ELT DAG, successful run ID, all four green tasks | The 12:57:34 AM image shows success but clips the graph; retake using fit-to-screen |
| `03_etl_schedule.png` | ETL DAG name, cron, next run and timezone | Still needed |
| `04_elt_schedule.png` | ELT DAG name, cron, next run and timezone | The 12:57:46 AM image already shows the cron, next run at 09:00 and +05:30 |

The 12:42:15 AM image is useful extra evidence of ETL per-file counts. It does not replace a quarantine example or `dq_results` query output. Existing October 25 captures are valid historical evidence when captioned with their original dates; do not relabel them as October 29 runs.

## 2. Capture database and quarantine evidence

In your SQL editor, create/select separate DuckDB connections to these files:

- ETL: `include/warehouse_vijayc5.duckdb`
- ELT: `include/warehouse_elt_vijayc5.duckdb`

Use the [ETL screenshot SQL](business_results/etl_screenshots.sql) with the ETL connection and [ELT screenshot SQL](business_results/elt_screenshots.sql) with the ELT connection. Select and execute one statement at a time. Capture the database/connection name, the SQL and a readable result grid. These queries are pinned to the captured run ID; the reconciliation tables themselves hold the current snapshot.

| Suggested filename | Statement/result to capture |
| --- | --- |
| `05_etl_quarantine.png` | Last ETL statement: selected fields from the exact-run orders quarantine CSV, showing `ORD000099`, quantity 0 and `quantity:nonpositive` |
| `06_etl_dq.png` | Quality summary showing all six dimensions; optionally a second image of individual failed checks |
| `07_elt_dq.png` | Same quality evidence from ELT |
| `08_etl_audit.png` | `pipeline_runs`: run ID, DAG ID, start/end, received/loaded/quarantined counts and SUCCESS |
| `09_elt_audit.png` | Same run-audit evidence from ELT |
| `10_etl_reconciliation.png` | Reconciliation exceptions with IDs, reason and amounts |
| `11_elt_reconciliation.png` | Equivalent ELT exception rows |

Eleven images are a suggested organisation, not an assignment-mandated count. You may combine evidence if every item remains readable. For the quarantine requirement, the last ETL query explicitly reads the actual CSV; a CSV editor view showing just the relevant columns is also suitable. Preserve the original quarantine file. Do not capture raw customer names, emails, phone numbers or manager names; the prepared queries avoid these fields.

A green run does not mean every quality check passes: a successful pipeline can quarantine bad records. Quality failure counts can overlap, so do not add them to infer unique rejected rows.

## 3. Review the six business answers

Open [ETL business SQL](business_results/etl_business.sql) or [ELT business SQL](business_results/elt_business.sql) in the matching database connection. Each query is followed by its complete executed result in the corresponding results document.

| Question | What to submit/verify |
| --- | --- |
| Q1 | Daily September revenue at zone and store levels; `level` distinguishes zone subtotals from store rows. Do not sum both levels together. |
| Q2 | September revenue and gross margin by category, using approved delivered orders |
| Q3 | Store delivery counts, average minutes and percentage within 15 minutes, with delivered orders as the denominator |
| Q4a/Q4b | Revenue by payment mode, plus known absolute reconciliation differences and the count of exceptions with unknown amounts |
| Q5 | Ten customer IDs, loyalty tiers and spend; no names/contact details |
| Q6 | Rejected records by file and reason for the chosen processing run; FILE TOTAL counts each rejected source record once |

The revenue questions use **1–30 September 2026** consistently. “Rejected today” means the selected 29 October processing run, not orders dated 29 October. Reconciliation covers the **entire current source snapshot**, including undated/orphan exceptions. `known_absolute_difference` is the sum of measurable absolute differences; it is not a complete financial loss figure. Both warehouses have 504 exception rows whose difference cannot be calculated. Do not silently turn unknown amounts into zero.

The assignment requires SQL plus results for these questions; it does not explicitly demand a screenshot of every business result. The linked result documents include all rows, including the long daily-revenue output. Optional query screenshots should supplement those tables rather than truncate the submitted results.

## 4. Explain the current ETL/ELT difference

| September measure | ETL baseline | ELT with retained corrections |
| --- | ---: | ---: |
| Approved fact rows, including non-delivered statuses | 1,776 | 1,776 |
| Net revenue | 864,887.20 | 863,055.50 |

ELT retains ten RETURNED corrections from the incremental file. Six are present in the approved September fact set; the remaining corrected orders are outside that approved set. These six account for the full **1,831.70** reduction:

| Order | ETL status / revenue | ELT status / revenue |
| --- | --- | --- |
| ORD000271 | DELIVERED / 445.00 | RETURNED / 0.00 |
| ORD000584 | DELIVERED / 102.60 | RETURNED / 0.00 |
| ORD000708 | DELIVERED / 416.00 | RETURNED / 0.00 |
| ORD001025 | DELIVERED / 150.00 | RETURNED / 0.00 |
| ORD001067 | DELIVERED / 532.80 | RETURNED / 0.00 |
| ORD001990 | DELIVERED / 185.30 | RETURNED / 0.00 |

This is a difference in input history, not evidence of double counting. Part F separately demonstrated parity with equal inputs, including increments. Q4b also includes the extra incremental orders and their missing payments in ELT, so full-snapshot reconciliation amounts differ. State the input scope with the results instead of forcing a match by editing data.

## 5. Refresh results and link your screenshots

To regenerate the SQL and full Markdown results after future runs, execute from the project directory:

```bash
cd /Users/user/Documents/personal/iitfde/pipeline/IIT_Roorkie_CEC_Futurenece_Data_Pipeline_to_ML_Model
.venv/bin/python include/export_nammamart_business_results.py
```

This uses the already installed Python environment, opens both warehouses read-only and exports results under `docs/business_results/`. No DuckDB GUI is required to generate the deliverables. Run it after both DAGs finish. If a database is locked, wait for its writer to finish and close other write connections. Recheck the comparison in this guide and SUBMISSION.md after refreshing; those narrative comparisons are not regenerated by the exporter.

After saving your screenshots, add each image to SUBMISSION.md with a caption stating the DAG/database, run ID, timezone where relevant and what it proves. Example, once that file exists:

```markdown
![ETL successful graph](docs/screenshots/01_etl_graph.png)
ETL scheduled run on 29 October 2026: all nine tasks succeeded.
```

Keep the screenshots readable and check that every Markdown link opens before submitting the repository.
