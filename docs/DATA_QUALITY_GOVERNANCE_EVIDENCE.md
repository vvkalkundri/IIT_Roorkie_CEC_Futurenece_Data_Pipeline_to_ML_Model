# Data quality and governance — verified evidence

This file is regenerated from the current local warehouses. It contains identifiers, counts and lineage metadata, not raw names, emails or phone numbers.

## Data quality scorecard

Each check may evaluate the same record; failed-check evaluations are not rejected-row counts. A successful pipeline can have critical findings because those records were quarantined. A run without checks is NOT_EVALUATED, not PASS.

### ETL

Run: `manual__2026-10-24T18:57:18.583391+00:00`. Recorded pipeline status: **SUCCESS**. End time: `2026-10-24T18:57:26.672935+00:00`.

| Dimension | Checks | Critical checks with failures | Warning checks with failures | Failed check evaluations | Result |
| --- | --- | --- | --- | --- | --- |
| Accuracy | 12 | 8 | 1 | 59 | CRITICAL_FINDINGS |
| Completeness | 47 | 5 | 1 | 37 | CRITICAL_FINDINGS |
| Consistency | 56 | 5 | 4 | 1038 | CRITICAL_FINDINGS |
| Timeliness | 6 | 3 | 1 | 2425 | CRITICAL_FINDINGS |
| Uniqueness | 10 | 4 | 0 | 30 | CRITICAL_FINDINGS |
| Validity | 25 | 6 | 3 | 40 | CRITICAL_FINDINGS |

### ELT

Run: `manual__2026-10-24T19:24:32.554723+00:00`. Recorded pipeline status: **SUCCESS**. End time: `2026-10-25 00:54:43.868805+05:30`.

| Dimension | Checks | Critical checks with failures | Warning checks with failures | Failed check evaluations | Result |
| --- | --- | --- | --- | --- | --- |
| Accuracy | 12 | 8 | 1 | 59 | CRITICAL_FINDINGS |
| Completeness | 47 | 5 | 1 | 37 | CRITICAL_FINDINGS |
| Consistency | 56 | 5 | 4 | 1192 | CRITICAL_FINDINGS |
| Timeliness | 6 | 3 | 1 | 2585 | CRITICAL_FINDINGS |
| Uniqueness | 10 | 4 | 0 | 30 | CRITICAL_FINDINGS |
| Validity | 25 | 6 | 3 | 40 | CRITICAL_FINDINGS |

## One number traced to source rows

ELT `mart_daily_store_kpis`: date **2026-09-03**, store **S04**, zone **South**, net revenue **138.60**. The source rows below sum exactly to that number. ETL reports **138.60** for the same date/store in its current snapshot.

| Order | Status | Revenue | Source file | Batch | Data record | Quantity | Unit price | Discount % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ORD000159 | DELIVERED | 138.6000 | orders.csv | 16 | 885 | 2 | 77.0 | 10 |
| ORD000198 | CANCELLED | 0.0000 | orders.csv | 16 | 2333 | 4 | 819.0 | 0 |

Record numbers exclude the CSV header. ELT links directly through `_batch_id` and `_row_number`; join to `ingestion_batches` for file hash and source run. ETL must reconstruct the same link through its saved run snapshot and order ID because its fact has no source-record metadata.

ETL snapshot: `include/etl_runs/vijayc5/238b6861daa806b5bf53/orders.csv`.

| Order ID | ETL source data record |
| --- | --- |
| ORD000159 | 885 |
| ORD000198 | 2333 |

## Rejected order audit

Order `ORD000099`: ELT reason `quantity:nonpositive`; exact raw source `orders.csv`, batch `16`, data record `1428`. ETL reason `quantity:nonpositive` in `include/quarantine/vijayc5/orders_failed_238b6861daa806b5bf53.csv`.

Verified fact-table presence: **ETL 0 rows; ELT 0 rows**. Therefore this order contributes no finance revenue. Inspect exact private raw values using the SQL in SUBMISSION.md; this public-facing document does not duplicate the source record.
