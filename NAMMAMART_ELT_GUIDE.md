# NammaMart ELT — run and inspect

## What the DAG does

`dags/nammamart_elt_vijayc5.py` runs four tasks:

1. **load_raw:** ingest the five baseline CSVs, optionally followed by the increment. All source fields are VARCHAR and retain their received values, including blanks, casing, bad values and duplicates. Python performs CSV/schema reading only; it does not clean rows.
2. **transform_staging:** execute SQL files to cast, standardise, deduplicate, mask personal details, validate, reconcile and upsert orders.
3. **build_marts:** publish business tables together in a transaction.
4. **audit_run:** run after all tasks, record SUCCESS/FAILED, and fail visibly if mart publication failed.

The warehouse is `include/warehouse_elt_vijayc5.duckdb`, separate from ETL's `include/warehouse_vijayc5.duckdb`. This avoids concurrent DuckDB writers across the two DAGs. The ELT file contains unmasked raw data and is ignored by Git. Local file storage does not implement role-based access controls; document those separately for the governance assignment.

## Start with the baseline

From the repository root, with Docker Desktop running:

```bash
astro dev start
astro dev run dags list-import-errors
```

Open http://localhost:8080, find `nammamart_elt_vijayc5`, and trigger it. It is initially paused to avoid unintended scheduled runs. Unpause when ready to use its Monday–Saturday, 9 AM IST schedule.

Use this JSON configuration for the baseline run:

```json
{"as_of": "2026-10-25", "include_increment": false}
```

The JSON boolean must be `true` or `false`, not a quoted string. Without an `as_of` override, checks use the current date in Asia/Kolkata. Use the same reference date for comparisons with ETL.

A terminal smoke test is also available:

```bash
astro dev run dags test nammamart_elt_vijayc5
```

Schedule: `0 9 * * 1-6` with an explicit IST start date. `catchup=False` avoids historical repeated loads of fixed fixture files. Two retries, a 30-second retry delay, a ten-minute timeout, and one active run are configured. No paid service, secret, or Airflow database connection is required. The current project's dependencies are sufficient; SQL MERGE requires DuckDB 1.4 or newer.

## Inspect the three layers

| Layer | Tables | Contents |
| --- | --- | --- |
| Raw | `raw_orders`, `raw_payments`, `raw_customers`, `raw_products`, `raw_stores` | Every received record plus `_loaded_at`, `_source_file`, `_run_id`, `_batch_id`, `_row_number` |
| Staging | `stg_orders`, `stg_payments`, `stg_customers`, `stg_products`, `stg_stores` | One current row per key; typed fields, masked personal details, `dq_status`, `failure_reason`, `warning_reason` and lineage |
| Mart | `mart_daily_store_kpis`, `mart_category_margin`, `mart_delivery_sla`, `mart_payment_reconciliation`, `mart_top_customers` | Business reporting |
| Supporting marts | `mart_fact_orders`, `mart_payment_mode_revenue`, `mart_rejections`, `mart_publication` | Comparable fact rows, payment-mode totals, rejection counts and published run/reference date |
| Audit | `ingestion_batches`, `dq_results`, `quality_records`, `elt_quarantine`, `incremental_results`, `pipeline_runs` | Source hashes/counts, quality history, rejected-record lineage, upsert counts and run outcomes |

`FAIL` is a critical rejection. `WARN` rows remain eligible unless another critical rule fails. Full names, email, phone and store manager names are fully redacted in staging; raw remains unchanged. `quality_records` records all evaluated source rows, including duplicate copies that are not retained in the one-row-per-key staging tables. It contains keys/reasons/lineage, not raw contact details.

## Compare with ETL before the increment

The baseline tests compare all accepted order IDs, revenue and margin against the Python ETL, using the same input fixtures and date. Expected baseline: **5,212 raw rows across five files; 2,400 unique order keys in staging; 1,777 approved order facts**. These are different counts: staging retains failed orders, whereas marts exclude them.

To compare the September aggregate of the local ETL and ELT warehouses after both have run:

```bash
.venv/bin/python -c 'from pathlib import Path; from include.nammamart_elt_helpers import compare_etl; print(compare_etl(Path.cwd()))'
```

Close other applications' write connections to either database before this read. The comparator reports MATCH/DIFFERENT and both counts/revenue/margin; it never overwrites ETL. Equal reference dates and inputs are necessary. Apply the same increment to both pipelines before comparing; ETL now retains corrections too.

## Apply the incremental file

Trigger a new run with:

```json
{"as_of": "2026-10-25", "include_increment": true}
```

The existing `orders_2026-10-01_increment.csv` is appended to `raw_orders`. SQL MERGE on `order_id` inserts **150 new keys** and changes **10 existing keys** after a baseline run. The ten corrections become RETURNED in staging. The test verifies 2,550 unique order keys afterward.

```sql
SELECT * FROM incremental_results ORDER BY checked_at;
SELECT order_id, order_status, dq_status, failure_reason
FROM stg_orders
WHERE _source_file = 'orders_2026-10-01_increment.csv';
```

The supplied increment has no corresponding new payment export. Under the current ETL-matching strict finance policy, delivered new orders without one valid matching SUCCESS payment remain rejected from finance marts. All 150 new keys still enter staging, with reasons where applicable. Thus **150 staging inserts do not imply 150 additional revenue-producing facts**.

Corrections restate the original order date's revenue: a returned September order no longer contributes September revenue. Original history remains raw. A rejected newer correction suppresses the older good record; it cannot accidentally leave old DELIVERED revenue active.

After a correction has been ingested, `include_increment=false` skips re-ingesting that file but **does not undo existing corrections**. SQL selects the latest received batch of each source, and this named October increment has precedence over the baseline. This rule is specific to the supplied assignment feed; a production feed with multiple dates needs an explicit source-version ordering contract.

## Re-run behaviour

- A **new Airflow run** appends another copy of its source rows to raw for audit. A five-file baseline adds 5,212 rows; a run including the increment adds 5,372.
- A **retry of the same raw task/run** reuses the already committed batches. The `(run_id, source_file)` uniqueness rule prevents retry duplicates. Changed bytes or a changed input selection on the same run are rejected; trigger a new run instead.
- Staging uses the latest batch per source rather than treating every raw copy as a new business record. Within-file exact duplicates retain the first normalised copy; conflicting versions of a key are marked FAIL.
- A repeated baseline after increment does not roll returned orders back. Repeated unchanged runs report zero new/changed order keys. These counts track normalised business payload changes, not changed load metadata or reference-date quality outcomes.
- Raw records are never deleted. The SHA-256 hash records the original file bytes; raw fields preserve parsed CSV values, not the CSV's quoting/line-ending encoding.

## SQL for the six business questions

Run these against the ELT warehouse in a DuckDB-capable editor. Apply an explicit month filter when comparing September rather than the whole export.

```sql
-- 1. Daily revenue by store and zone; remove store_id for zone-only totals.
SELECT order_date, zone, store_id, sum(net_revenue) AS net_revenue
FROM mart_daily_store_kpis GROUP BY order_date, zone, store_id
ORDER BY order_date, zone, store_id;

-- 2. Category revenue and gross margin.
SELECT * FROM mart_category_margin ORDER BY category;

-- 3. Delivery time and percentage within 15 minutes.
SELECT * FROM mart_delivery_sla ORDER BY store_id;

-- 4. Revenue by payment mode and quantifiable payment discrepancies.
SELECT * FROM mart_payment_mode_revenue ORDER BY payment_mode;
SELECT sum(abs(amount_difference)) AS total_absolute_amount_difference,
       count(*) FILTER (WHERE amount_difference IS NULL) AS exceptions_needing_investigation
FROM mart_payment_reconciliation;

-- 5. Top customers by spend, with loyalty tier and no raw contact details.
SELECT * FROM mart_top_customers ORDER BY total_spend DESC, customer_id;

-- 6. Rejected records by source and reason for the current evaluation.
SELECT * FROM mart_rejections ORDER BY source_file, reason;
```

Not every reconciliation exception has a measurable amount difference: invalid amounts, duplicate source rows and missing valid orders remain explicit investigation entries. Summing the known differences does not resolve those unknown exceptions. One rejected record can have several reasons; do not sum reason counts to claim a unique rejected-row count.

## Audit and lineage

```sql
SELECT * FROM pipeline_runs ORDER BY end_time DESC;
SELECT * FROM dq_results WHERE rows_failed > 0 ORDER BY run_id, check_name;
SELECT * FROM mart_publication;
-- Example: locate exact original order fields for rejected order records.
-- This queries private raw data; restrict access in a real deployment.
SELECT q.row_key, q.failure_reason, r.*
FROM elt_quarantine q JOIN raw_orders r
  ON q.batch_id=r._batch_id AND q.row_number=r._row_number;
```

`pipeline_runs.rows_extracted` counts source rows received for that run; `rows_loaded` counts published approved order facts; `rows_quarantined` counts evaluated source records with critical failures. These counts have different scopes and are not an accounting equation. Audit failure does not imply old marts are empty: `mart_publication` identifies the last successfully published snapshot. If raw/schema loading fails, there may be no quality evaluation for that run; Airflow logs and the run audit still record failure. If the database itself is unavailable, audit persistence can fail too.

Raw ingestion and staging/mart transformations use separate transactions. Failed transformations preserve raw for replay and leave the previous published marts intact. Staging may be newer than marts if mart publication fails. The schedule alone does not prove completion by the client's deadline.

## Files to study

- `include/nammamart_elt_helpers.py`: ingestion, transaction boundaries, SQL execution and auditing; no pandas cleaning.
- `include/sql/nammamart/00_metadata.sql`: ingestion and audit structures.
- `10_quality_setup.sql`, `11_customers.sql`, `12_products.sql`, `13_stores.sql`: source selection and master-data rules.
- `14_orders.sql`: validation plus actual SQL MERGE/upsert.
- `15_payments.sql`, `16_reconciliation.sql`: payment validation and finance eligibility.
- `20_marts.sql`: the business tables.

All transformations are checked-in SQL, independently inspectable and editable. The shared profiler import supplies CSV schemas only. The strict single-payment policy matches the existing ETL but still requires client agreement for split payments, refunds, delayed settlements and Cash on Delivery.

## Tests and remaining assignment work

```bash
.venv/bin/python -m unittest discover -s tests -p test_nammamart_elt.py -v
```

Tests use temporary warehouses and cover exact raw values, ETL parity, redaction, six quality dimensions, 150 inserts/10 corrections, repeat-run stability, same-run retry behaviour, changed source/schema failure and rejected corrections superseding old good rows. These tests are not substitutes for the ten required Airflow experiments and screenshots.

ETL incremental support, Part D/E and the executed Part F observability suite are now documented in `SUBMISSION.md`. Written scheduling answers, the required submission screenshots, six business-query results and the client recommendation remain separate submission work.

## Verification completed

The Airflow import check reported no errors, and a baseline `astro dev run dags test nammamart_elt_vijayc5` finished with all four tasks successful. The live warehouse remains at the baseline; incremental behaviour was exercised in temporary test databases. All four integration tests passed.

Local September comparison: **MATCH**. ETL count/revenue/margin: 1776, 864887.2, 212727.47. ELT count/revenue/margin: 1776, 864887.20, 212727.47.

## Observability updates

The executed Part F report is linked from `SUBMISSION.md`. The file-volume warning compares each current batch against its previous received batch. Order-amount formula arithmetic uses a widened decimal intermediate so the 100× price experiment is rejected by data-quality rules without crashing SQL. All raw values remain unchanged.
