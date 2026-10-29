# Part F: executed observability evidence

Suite `obs_20261026_03`, executed on 26 October 2026 in the local Astro scheduler. Validation reference date: `2026-10-25`. Both unscheduled experiment DAGs use the same task factories as the main DAGs. Each destructive scenario used a separate prepared copy of the baseline workspace. Original fixture hashes were unchanged; case input files were restored after observation. Experiment DAGs were paused afterward.

[Machine-readable task states, timings and SQL metrics](../include/observability_reports/observability_obs_20261026_03.json). This report contains aggregate counts and synthetic test IDs, not customer fields.

## Run inventory

| Experiment | ETL run / state | ELT run / state |
|---|---|---|
| happy | `obs_20261026_03_happy_etl` / success | `obs_20261026_03_happy_elt` / success |
| rerun | `obs_20261026_03_rerun_etl` / success | `obs_20261026_03_rerun_elt` / success |
| increment | `obs_20261026_03_increment_etl` / success | `obs_20261026_03_increment_elt` / success |
| missing | `obs_20261026_03_missing_etl` / failed | `obs_20261026_03_missing_elt` / failed |
| bad_rows | `obs_20261026_03_bad_rows_etl` / success | `obs_20261026_03_bad_rows_elt` / success |
| schema | `obs_20261026_03_schema_etl` / failed | `obs_20261026_03_schema_elt` / failed |
| volume | `obs_20261026_03_volume_etl` / success | `obs_20261026_03_volume_elt` / success |
| drift | `obs_20261026_03_drift_etl` / success | `obs_20261026_03_drift_elt` / success |
| freshness | `obs_20261026_03_freshness_etl` / success | `obs_20261026_03_freshness_elt` / success |
| recovery | `obs_20261026_03_recovery_etl` / failed | `obs_20261026_03_recovery_elt` / failed |
| recovered | `obs_20261026_03_recovery_etl` / success | `obs_20261026_03_recovery_elt` / success |

`recovered` is the same run ID after Clear, not a newly triggered run. The evidence preserves its failed state before recovery even though the run audit is updated to SUCCESS.

## Happy-path counts and task timing

| Pipeline | Source | Received | Accepted (including warnings) | Quarantined |
|---|---|---:|---:|---:|
| ETL | orders.csv | 2412 | 1777 | 635 |
| ETL | payments.csv | 2228 | 2202 | 26 |
| ETL | customers.csv | 405 | 392 | 13 |
| ETL | products.csv | 152 | 140 | 12 |
| ETL | stores.csv | 15 | 13 | 2 |
| ELT | customers.csv | 405 | 392 | 13 |
| ELT | orders.csv | 2412 | 1777 | 635 |
| ELT | payments.csv | 2228 | 2202 | 26 |
| ELT | products.csv | 152 | 140 | 12 |
| ELT | stores.csv | 15 | 13 | 2 |

Accepted source rows are not all published order facts. Audit `rows_loaded` counts order facts only; quality-rule failure counts can overlap and must not be summed as rejected records.

| Pipeline | Task | Duration (seconds) |
|---|---|---:|
| ETL | `extract_products` | 8.083 |
| ETL | `extract_customers` | 8.134 |
| ETL | `extract_payments` | 8.169 |
| ETL | `extract_stores` | 8.072 |
| ETL | `extract_orders` | 8.231 |
| ETL | `validate_and_quarantine` | 2.225 |
| ETL | `transform_orders` | 0.939 |
| ETL | `load_and_report` | 1.004 |
| ETL | `audit_run` | 0.647 |
| ELT | `load_raw` | 8.876 |
| ELT | `transform_staging` | 1.882 |
| ELT | `build_marts` | 0.581 |
| ELT | `audit_run` | 0.665 |

Observed overlapping ETL extract task intervals: 10 pairs. `extract_products` / `extract_customers`; `extract_products` / `extract_payments`; `extract_products` / `extract_stores`; `extract_products` / `extract_orders`; `extract_customers` / `extract_payments`; `extract_customers` / `extract_stores`; `extract_customers` / `extract_orders`; `extract_payments` / `extract_stores`; `extract_payments` / `extract_orders`; `extract_stores` / `extract_orders`. ELT has a serial raw → staging → mart dependency.

## Ten experiments

| # | Expected | Observed on both pipelines | Where I saw it | What I would change |
|---|---|---|---|---|
| 1 | Happy path: green tasks, audited counts and measurable durations | 1,777 facts and revenue 865,874.05 in each pipeline; 5,212 received rows; timing and per-file counts above. ETL overlap: 10 pairs. | Airflow task start/end/duration; pipeline_runs; per-file validation counts | Record duration baselines and alert on slow runs. |
| 2 | Re-run: unchanged facts; append-only ELT raw grows | Facts and revenue unchanged. ELT raw_orders grew 2,412 → 4,824; a new run preserves a new source snapshot, while same-run retries deduplicate batches. | Fact counts, raw_orders and ingestion_batches | Apply retention to historical raw batches; distinguish retries from new runs. |
| 3 | Increment: 150 new keys, 10 corrected keys, no duplicate facts | Both recorded 150 inserts / 10 changes; all ten corrections are RETURNED. Facts have unique order IDs. ELT has 2,550 unique staging keys. Missing new payments prevent all 150 new keys becoming finance facts. | incremental_results; stg_orders; ETL retained corrections; distinct fact IDs | Use source version ordering for multiple future incremental files; confirm Finance restatement rules. |
| 4 | Missing products: retries, loud failure, blocked downstream | ETL extract_products and ELT load_raw exhausted three attempts (initial + two retries). Both runs and audits FAILED; downstream tasks upstream_failed. Previous committed facts remain available. | Airflow retry/state timeline below; pipeline_runs | Add an external failure notification and a dashboard showing publication age. |
| 5 | Five new bad rows: quarantine each with its reason | All five synthetic IDs have the required reason: missing customer, nonpositive quantity, unknown store reference, invalid status and future timestamp. Relevant dq_results checks failed. | ETL rejected CSV; ELT quality_records/elt_quarantine; dq_results; synthetic-ID table below | Keep these examples as regression fixtures and monitor rejection rate. |
| 6 | Renamed order_amount: fail before publishing wrong data | ETL extract_orders failed with `ValueError: orders.csv: source schema differs from expected columns`; ELT load_raw failed with `ValueError: orders.csv: unexpected CSV schema`. Both exhausted three attempts and retained prior facts. | Task failures and schema error messages; FAILED audit | Use versioned schema contracts and avoid retrying deterministic schema errors. |
| 7 | 50 orders: warn on a drop above 90% | 2,412 → 50 orders (97.93% drop); orders.csv:volume:drop_over_90pct failed with one file-level warning in each pipeline. Runs succeeded; warning does not block publication. | dq_results and current source counts compared with prior successful/batched source | Make severe volume drops a publication gate after agreeing thresholds. |
| 8 | 100× S04 prices: detect corruption and measure impact | ETL: S04 revenue 58,998.30 → 0.00 (change -58,998.30); ELT: S04 revenue 58,998.30 → 0.00 (change -58,998.30). The order-amount formula check caught unchanged amounts; affected orders were rejected. | dq_results formula failures; S04 sum(net_revenue) in fact tables | Add price quantile/median drift checks by store/product; formula checks miss coherent changes to price and amount. |
| 9 | Latest order timestamp 30 days old: freshness warning | Latest timestamp 2026-09-25 versus reference 2026-10-25; orders:stale failed in both pipelines. Runs succeeded because stale fixtures are warnings. | dq_results Timeliness checks | Set a production freshness SLA and gate stale publication or label it clearly. |
| 10 | Fix missing products, Clear failed task + downstream only | Same run IDs recovered to SUCCESS. ETL’s other four extracts retained their original attempt/start/end. extract_products ran attempt 4; validation, transform, load and audit executed. ELT load_raw ran attempt 4 and its downstream chain executed. | Before/after task metadata below; same-run SUCCESS audit | Document selective recovery and retain failed-attempt history outside the one-row-per-run audit. |

## Failure and recovery evidence

Retry delay is configured as 30 seconds. Observed times below are polling observations (2-second polling), so they include scheduler delay and are not exact worker retry-start timestamps.

| Case / pipeline | Failed task | Observed up_for_retry (UTC) | Final attempt / state |
|---|---|---|---|
| missing / ETL | `extract_products` | 2026-10-26T15:09:27.236481+00:00; 2026-10-26T15:09:57.514001+00:00 | 3 / failed |
| missing / ELT | `load_raw` | 2026-10-26T15:09:29.259036+00:00; 2026-10-26T15:09:59.545718+00:00 | 3 / failed |
| schema / ETL | `extract_orders` | 2026-10-26T15:11:07.768862+00:00; 2026-10-26T15:11:38.009429+00:00 | 3 / failed |
| schema / ELT | `load_raw` | 2026-10-26T15:11:09.795531+00:00; 2026-10-26T15:11:40.032362+00:00 | 3 / failed |
| recovery / ETL | `extract_products` | 2026-10-26T15:13:08.372314+00:00; 2026-10-26T15:13:38.604897+00:00 | 3 / failed |
| recovery / ELT | `load_raw` | 2026-10-26T15:13:10.394026+00:00; 2026-10-26T15:13:40.620143+00:00 | 3 / failed |

| Pipeline | Task | Attempts before → after Clear | Result |
|---|---|---|---|
| ETL | `load_and_report` | 0 → 1 | success |
| ETL | `audit_run` | 1 → 2 | success |
| ETL | `extract_customers` | 1 → 1 | success |
| ETL | `validate_and_quarantine` | 0 → 1 | success |
| ETL | `transform_orders` | 0 → 1 | success |
| ETL | `extract_products` | 3 → 4 | success |
| ETL | `extract_stores` | 1 → 1 | success |
| ETL | `extract_orders` | 1 → 1 | success |
| ETL | `extract_payments` | 1 → 1 | success |
| ELT | `load_raw` | 3 → 4 | success |
| ELT | `transform_staging` | 0 → 1 | success |
| ELT | `build_marts` | 0 → 1 | success |
| ELT | `audit_run` | 1 → 2 | success |

| Pipeline | Synthetic order ID | Quarantine reasons |
|---|---|---|
| ETL | TEST_FUTURE | order_ts:future |
| ETL | TEST_NEGATIVE | quantity:nonpositive; order_amount:formula |
| ETL | TEST_NULL | customer_id:missing; customer_id:invalid_reference |
| ETL | TEST_STATUS | order_status:unknown |
| ETL | TEST_STORE | store_id:invalid_reference |
| ELT | TEST_FUTURE | order_ts:future |
| ELT | TEST_NEGATIVE | order_amount:formula; quantity:nonpositive |
| ELT | TEST_NULL | customer_id:invalid_reference; customer_id:missing |
| ELT | TEST_STATUS | order_status:unknown |
| ELT | TEST_STORE | store_id:invalid_reference |

Audit-count interpretation: the volume test reports 2,220 ETL quarantined rows versus 64 ELT rows. ETL tests payment references against the current order snapshot; ELT tests whether an order ever existed in retained raw history. Both publish 39 facts and revenue 17,865.00, but their quarantine scopes differ. Align the reference policy before treating these counts as interchangeable. Incremental quarantine counts also differ (838 ETL / 842 ELT): ETL evaluates the merged effective order set, while ELT retains and evaluates baseline and increment records before selecting the winning version. The freshness mutation changes formerly future-dated records too, so its 1,780 facts differ from the unmodified baseline.

## Five pillars

| Pillar | Implemented evidence | Limitation |
|---|---|---|
| Freshness | Latest nonfuture order date versus reference date; stale warning | No production publication gate or notification |
| Volume | Previous-versus-current row count; >90% drop warning | No seasonality; ETL uses last committed counts, ELT previous received batches |
| Schema | Exact required columns; loud failure before publication | No schema evolution workflow |
| Distribution | Formula, range and reconciliation checks catch this price mutation | Weakest: no learned/statistical drift baseline; coherent price/amount changes can pass |
| Lineage | Run IDs, raw batch/source/row references in ELT, ETL run snapshots, quarantine reasons and publication audit | Strongest, especially ELT; no external lineage catalogue or historical mart snapshots |

## Defects exposed and corrected

The exploratory suite obs_20261026_02 exposed an ELT DECIMAL(18) intermediate overflow under 100× prices. The formula now widens the intermediate to DECIMAL(38); a regression test checks quarantine without a crash. The installed Airflow Clear implementation treats its task selector as a substring; anchored regex text matched no tasks. The runner now passes the literal task name and verifies the run was reset. Shared DAG factories were moved out of DAG discovery modules to eliminate duplicate registration. The final suite above verifies the corrected behavior; the exploratory suite is not treated as a pass.

## Reproduce and inspect

Run inside the Astro scheduler from `/usr/local/airflow`: `python include/run_nammamart_observability.py --suite obs_unique` (use a new lowercase/digit suffix). Run locally afterward: `.venv/bin/python include/report_nammamart_observability.py --suite obs_unique`. The report generator asserts the observed outcomes before writing a report. Private datasets, quarantine, logs and warehouses remain in ignored `include/observability_workspaces/`.

In Airflow select `nammamart_etl_observability_vijayc5` or `nammamart_elt_observability_vijayc5`, then the exact run ID in the inventory. Use Graph for states/dependencies and task logs for attempts/errors. A failed audit task deliberately keeps the DAG red when upstream work failed. There are no external Slack/email alerts configured.

For SQL evidence, open the corresponding isolated workspace warehouse after its run ends. Filter `pipeline_runs` and `dq_results` by the inventory run ID; ETL uses `etl_fact_orders`, ELT uses `mart_fact_orders`. Current live production warehouses were not overwritten by these experiments.
