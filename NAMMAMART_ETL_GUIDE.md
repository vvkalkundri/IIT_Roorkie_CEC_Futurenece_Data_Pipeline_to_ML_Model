# Run the NammaMart ETL in Airflow

## What was created

- `dags/nammamart_etl_vijayc5.py`: Airflow 3 TaskFlow DAG.
- `include/nammamart_etl_helpers.py`: reusable extraction, validation, transformation, loading, and audit code. Imports schema constants and decimal parsing from `include/profile_nammamart.py` without running the profiler.
- Six assignment CSVs copied into `include/data/nammamart/`. An earlier, different customer file was preserved in `include/data/nammamart/before_assignment_setup/`.
- `tests/test_nammamart_etl.py`: local verification independent of Airflow.

Airflow discovers Python DAG definitions in `dags/`. Astro makes the project available to its Airflow containers. No separate connection to Astro is needed in the DAG. DuckDB is a local file, so this version does not need an Airflow database connection or password.

## 1. Open the project directory

```bash
cd /Users/user/Documents/personal/iitfde/pipeline/IIT_Roorkie_CEC_Futurenece_Data_Pipeline_to_ML_Model
```

Keep Docker Desktop running. The repository already lists `pandas` and `duckdb` in `requirements.txt`.

## 2. Start Airflow

```bash
astro dev start
```

If the environment was already started before its dependencies changed, run `astro dev restart`. Python packages installed only in the Mac's `.venv` are not automatically installed inside the containers.

## 3. Check that Airflow discovers the DAG

```bash
astro dev run dags list-import-errors
astro dev run dags list
```

Look for `nammamart_etl_vijayc5`. Fix import errors before triggering it. The trainer's DAG is unchanged; unrelated errors in another DAG should be investigated separately. DAG edits are normally picked up automatically after the next scan.

## 4. Trigger a manual run

Open http://localhost:8080 and use the credentials shown by your Astro environment (the class setup uses admin/admin).

1. Find `nammamart_etl_vijayc5`.
2. Open the DAG and view its graph.
3. Unpause it when ready, then select Trigger.
4. For a reproducible historical-data check, supply this run configuration if the UI offers a JSON configuration field:

```json
{"as_of": "2026-10-25"}
```

Without configuration, validation uses today's date in Asia/Kolkata. A historical file may therefore produce freshness warnings. Future-date checks and accepted counts may change with the reference date.

The five `extract_*` tasks have no dependencies on one another and can run in parallel, subject to Airflow's available capacity. Then `validate_and_quarantine`, `transform_orders`, and `load_and_report` run in order. `audit_run` waits for every task to finish, including failures.

## 5. Inspect the results

- Extraction logs: file names and row counts only.
- Validation logs: extracted, accepted, and quarantined counts per file.
- Load logs: daily zone revenue and category margin.
- Quarantine: `include/quarantine/vijayc5/<file>_failed_<run-token>.csv`.
- Warehouse: `include/warehouse_vijayc5.duckdb`.
- Private task intermediates: `include/etl_runs/vijayc5/<run-token>/`.

The run token is a stable hash of Airflow's run ID. Full run IDs are recorded in `pipeline_runs` and `dq_results`. Do not commit private intermediates or quarantine files; they contain original source personal data and are ignored by Git. Reporting names, email addresses, and phone numbers are fully redacted. Do not replace the application-generated pickle intermediates with files from an untrusted source.

After the run completes, these SQL queries can be run against the warehouse in a DuckDB-capable editor:

```sql
SELECT * FROM pipeline_runs ORDER BY end_time DESC;
SELECT * FROM dq_results WHERE rows_failed > 0;
SELECT * FROM etl_payment_reconciliation;
SELECT count(*) AS orders, round(sum(net_revenue), 2) AS revenue FROM etl_fact_orders;
SELECT * FROM etl_daily_zone_revenue ORDER BY order_date, zone;
SELECT * FROM etl_category_margin ORDER BY category;
```

`rows_loaded` in the run audit means loaded order-fact rows, not the sum of fact and dimension rows. A failed run leaves the last successfully committed reporting snapshot intact. Do not interpret old warehouse totals as evidence that the newest run succeeded.

## 6. Check repeatability and failure behaviour

Trigger again with the same source files and `as_of` date. Compare order counts and revenue: both should be unchanged. Audit history gains a new run. This is a transactional full-snapshot replacement, not an append.

Run the local helper tests with:

```bash
.venv/bin/python -m unittest discover -s tests -p test_nammamart_etl.py -v
```

These tests use temporary folders and databases. They do not replace the assignment's ten Airflow UI experiments or screenshots.

## Schedule and failure handling

- Cron: `0 9 * * 1-6`, with an Asia/Kolkata start date (09:00 IST / 03:30 UTC, Monday–Saturday).
- `catchup=False`: avoid historical daily runs against these static snapshot files.
- Two retries with a 30-second delay; ten-minute task timeout.
- `max_active_runs=1`: prevents this DAG's runs competing for the same DuckDB file.
- `audit_run` uses `all_done`. It records FAILED and raises an error if loading did not succeed, so the final audit task cannot hide an upstream failure behind a successful DAG status.
- No scheduled task can execute while the local Docker/Airflow environment is stopped. A 9 AM start also does not guarantee completion before 9 AM; the brief's timing inconsistency still needs clarification.

## Business rules and scope

Critical errors are quarantined. Exact duplicates retain the first normalised copy; conflicting versions of a key are quarantined. Orders must reference accepted master records. Warnings do not independently reject rows. Every file's input count equals accepted plus quarantined records.

This initial implementation uses a **strict finance assumption**: each delivered order must have exactly one accepted SUCCESS payment of the same amount. Missing, multiple, and mismatched settlements are held from finance facts and recorded for reconciliation. This is stricter than the profiler's warning for missing successful payments. Confirm Cash on Delivery, refund, and settlement policies before final submission. Fact revenue and margin count only DELIVERED orders.

This DAG implements the five-file snapshot ETL flow and supports the supplied order increment. It does not maintain historical reporting snapshots or send external failure notifications. ELT is implemented in a separate DAG. The executed Part F report is linked from SUBMISSION.md. Its daily task schedule repeatedly processes the provided snapshots; production daily file selection is a later extension. The shared intermediate folder assumes local Astro containers with a shared project filesystem, not remote distributed workers. A future ELT DAG should use a separate warehouse or coordinate writes to avoid DuckDB writer conflicts.

When an extraction fails, the audit records the failure and counts available extracts; quality results exist only if validation completed. A warehouse connection failure can also prevent audit persistence and remains visible in the Airflow task logs.

## Verified during setup

The Airflow import-error check returned no errors, and `astro dev run dags test nammamart_etl_vijayc5` completed successfully, including all nine tasks and the audit. This CLI test does not demonstrate parallel scheduler execution; capture that separately in a UI-triggered run. Four local tests passed: repeat-load accounting/privacy, missing-source failure audit, schema failure, and injected bad-order quarantine.

With the 2026-10-25 reference date, 1,777 of 2,412 source orders were accepted and 635 were quarantined under the strict finance and master-data rules. These counts differ from profiler findings because pipeline validation checks accepted master records and settlement eligibility.

## Incremental orders and observability

Trigger with `{"as_of":"2026-10-25","include_increment":true}` to apply the supplied incremental orders. After a baseline, `incremental_results` records 150 new keys and 10 changed keys. Validated corrections are incorporated into the snapshot; the received correction feed is retained privately under `include/etl_state/vijayc5/` so a subsequent baseline run cannot undo returned statuses. Critical failures are still excluded from finance facts. Those counts describe input key changes, not 150 additional published facts.

The prepared observability aliases use the same task factories as the scheduled DAGs and separate private warehouses. See the Part F evidence linked from `SUBMISSION.md` for actual scheduler parallelism, retries, selective Clear recovery, volume warnings and price-drift results. The volume check warns when source rows fall below 10% of the previous committed count; it does not block publication.
