# NammaMart assignment submission

## Part 0 — Discovery and data profiling

### Scope and evidence

All six supplied files were profiled using `include/profile_nammamart.py`, with an IST reference date of **2026-10-24**. The source files were not modified. This section preserves the original discovery findings and proposed handling. Implemented operational rules and evidence are documented in Part D below.

- [Profiling report](include/profiling_output/PROFILE_REPORT.md)
- [Complete record-level Data Issues Log](include/profiling_output/data_issues.csv)
- [Column statistics, date/numeric ranges, and categorical frequencies](include/profiling_output/profile_summary.json)

### Profiling summary

| File | Input rows | Rows with duplicate keys | Findings | Distinct records with findings |
| --- | ---: | ---: | ---: | ---: |
| orders.csv | 2412 | 24 | 203 | 187 |
| payments.csv | 2228 | 8 | 46 | 44 |
| customers.csv | 405 | 10 | 441 | 400 |
| products.csv | 152 | 4 | 13 | 12 |
| stores.csv | 15 | 0 | 2 | 2 |
| orders_2026-10-01_increment.csv | 160 | 0 | 1 | 0 |

**Total: 5,372 input rows and 706 findings.** Findings are not rejected-row counts: one record may have several findings. Duplicate-key counts include all members of a duplicate group, not just excess copies. The increment's freshness finding applies to the file, so its count of individual records with findings is zero.

The increment contains **150 new-order rows and 10 existing-order rows**. Cross-file overlap is an expected update candidate, not automatically a duplicate error. These counts do not prove that an upsert has been implemented.

### Data Issues Log — grouped findings

Each row below groups one detected rule and provides a real example key. The linked CSV contains every affected record and its 1-based data-record number (excluding the header). No raw customer contact details are reproduced here.

| File | Example row key | Column | Problem | Quality dimension | Count | Suggested handling | Severity |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| customers.csv | C00355 | city | Missing value | Completeness | 6 | Retain as missing; log warning; do not invent values | Warning |
| customers.csv | C00103 | customer_id | Repeated key within this file | Uniqueness | 10 | Keep one exact copy and log excess copies; quarantine conflicting versions until a precedence rule is agreed | Critical |
| customers.csv | C00337 | email | Invalid format | Validity | 12 | Log warning; mask email/phone or use a redacted placeholder if malformed; review pincode without inventing it | Warning |
| customers.csv | C00182 | loyalty_tier | Noncanonical casing | Consistency | 400 | Standardise to uppercase | Warning |
| customers.csv | C00151 | phone | Invalid format | Validity | 7 | Log warning; mask email/phone or use a redacted placeholder if malformed; review pincode without inventing it | Warning |
| customers.csv | C00132 | pincode | Invalid format | Validity | 3 | Log warning; mask email/phone or use a redacted placeholder if malformed; review pincode without inventing it | Warning |
| customers.csv | C00400 | signup_date | Date after reference date | Timeliness | 3 | Quarantine; verify reference date | Critical |
| orders.csv | ORD002255 | customer_id | Missing value | Completeness | 18 | Quarantine missing required fields | Critical |
| orders.csv | ORD001554 | delivery_minutes | Delivered order missing delivery time | Completeness | 8 | Quarantine | Critical |
| orders.csv | ORD001037 | delivery_minutes | Delivery at least 120 minutes | Accuracy | 6 | Quarantine; confirm limit with client | Critical |
| orders.csv | ORD002103 | discount_pct | Discount outside 0–100 | Validity | 3 | Quarantine | Critical |
| orders.csv | ORD002103 | order_amount | Amount differs from rounded quantity × price × (1 − discount/100) | Accuracy | 18 | Quarantine; confirm half-up rounding | Critical |
| orders.csv | ORD001296 | order_amount | Negative value | Accuracy | 6 | Quarantine | Critical |
| orders.csv | ORD000398 | order_id | Delivered order has no successful payment | Consistency | 72 | Log reconciliation warning; confirm settlement/COD policy before finance inclusion | Warning |
| orders.csv | ORD001462 | order_id | Repeated key within this file | Uniqueness | 24 | Keep one exact copy and log excess copies; quarantine conflicting versions until a precedence rule is agreed | Critical |
| orders.csv | ORD001066 | order_status | Noncanonical casing | Consistency | 5 | Standardise to uppercase | Warning |
| orders.csv | ORD000500 | order_status | Unrecognised category | Validity | 3 | Quarantine | Critical |
| orders.csv | ORD002119 | order_ts | Date after reference date | Timeliness | 5 | Quarantine; verify reference date | Critical |
| orders.csv | ORD000362 | order_ts | Missing value | Completeness | 1 | Quarantine missing required fields | Critical |
| orders.csv | ORD000403 | order_ts | Unparseable date/timestamp | Validity | 5 | Quarantine | Critical |
| orders.csv | ORD002356 | payment_mode | Surrounding whitespace | Consistency | 2 | Trim in transformed data; preserve raw | Warning |
| orders.csv | ORD001812 | payment_mode | Unrecognised category | Validity | 3 | Quarantine | Critical |
| orders.csv | ORD000986 | product_id | Reference missing from master | Consistency | 9 | Quarantine | Critical |
| orders.csv | ORD000469 | quantity | Must be positive | Accuracy | 10 | Quarantine | Critical |
| orders.csv | ORD001799 | store_id | Reference missing from master | Consistency | 5 | Quarantine | Critical |
| orders_2026-10-01_increment.csv | <file> | order_ts | Latest order is older than one day | Timeliness | 1 | Warn; historical fixtures are expected to be stale | Warning |
| payments.csv | PAY0001568 | amount_paid | Negative value | Accuracy | 6 | Quarantine | Critical |
| payments.csv | PAY0002219 | order_id/amount_paid | Payment references missing order | Consistency | 8 | Quarantine orphan payment and record reconciliation mismatch | Critical |
| payments.csv | PAY0001568 | order_id/amount_paid | Successful payment differs from order amount | Consistency | 14 | Record mismatch; quarantine payment from reconciled outputs; hold associated finance revenue pending resolution (proposed) | Critical |
| payments.csv | PAY0001651 | payment_id | Repeated key within this file | Uniqueness | 8 | Keep one exact copy and log excess copies; quarantine conflicting versions until a precedence rule is agreed | Critical |
| payments.csv | PAY0002113 | payment_mode | Surrounding whitespace | Consistency | 2 | Trim in transformed data; preserve raw | Warning |
| payments.csv | PAY0001954 | payment_mode | Unrecognised category | Validity | 3 | Quarantine | Critical |
| payments.csv | PAY0000396 | payment_ts | Date after reference date | Timeliness | 5 | Quarantine; verify reference date | Critical |
| products.csv | P0051 | category | Missing value | Completeness | 3 | Quarantine missing required fields | Critical |
| products.csv | P0019 | cost_price | Cost exceeds MRP | Accuracy | 5 | Quarantine; confirm business rule | Critical |
| products.csv | P0109 | mrp | Must be positive | Accuracy | 1 | Quarantine | Critical |
| products.csv | P0030 | product_id | Repeated key within this file | Uniqueness | 4 | Keep one exact copy and log excess copies; quarantine conflicting versions until a precedence rule is agreed | Critical |
| stores.csv | S12 | capacity_orders_per_day | Must be positive | Accuracy | 1 | Quarantine | Critical |
| stores.csv | S07 | zone | Missing value | Completeness | 1 | Quarantine missing required fields | Critical |

### Suggested handling — pipeline policy

These are proposed implementation decisions. Open business questions below still require client clarification. Apply the same rules in Python for ETL and SQL for ELT.

| Issue type | Suggested handling |
| --- | --- |
| Whitespace and casing | Trim and map recognised values to canonical spellings, for example `upi` to `UPI`. Log normalisation. Validate allowed values after normalisation; retain untouched raw values. |
| Missing required IDs, dates, category, or zone | Quarantine with a specific failure reason. Do not infer IDs or replace missing dates with the run date. |
| Unknown customer, product, or store | Quarantine the order. Validate against accepted, deduplicated dimensions, not merely the presence of a key in a raw master. |
| Invalid numeric values or incorrect order amount | Quarantine; preserve the source amount and record the failed rule. Do not silently replace an incorrect financial amount. |
| Exact duplicate | Keep one deterministic survivor, such as the first source record, and account for every excess copy in the duplicate/quarantine log. |
| Conflicting duplicate key | Quarantine conflicting versions pending an agreed precedence rule; do not arbitrarily select financial values. |
| Invalid email/phone or missing optional location | Log a warning. Mask valid contact fields; use a redacted placeholder when malformed values cannot be safely masked. Leave unknown location values missing. |
| Missing delivered-order delivery time, negative time, or time at least 120 minutes | Quarantine. Confirm the 120-minute threshold with the client. Values outside the usual 8–35 range but below the critical threshold warrant review rather than automatic rejection. |
| Future or unparseable date | Quarantine against the documented reference date; retain the original value for audit. |
| Historical data failing freshness | Record a file-level warning using the explicit reference date. Do not misrepresent supplied historical fixtures as current daily exports. |
| Payment amount mismatch or orphan payment | Write a reconciliation entry and exclude the invalid payment from reconciled outputs. Proposed finance policy: hold revenue associated with a known amount mismatch until resolved. |
| Delivered order without a successful payment | Record a warning and reconciliation exception; determine settlement delay and Cash on Delivery treatment with finance before final reporting. |
| Increment matching an existing order ID | Treat as an update candidate, validate, then upsert. Preserve the source/version history; do not treat it as a within-file duplicate. |

For ETL, failed records must be retained in quarantine with `failure_reason`. For ELT, every raw record remains untouched; staging records carry quality status and reasons, and reporting excludes critical failures. Warning-only records may load unless another critical rule fails. Audit counts must distinguish records from individual findings.

### Assumptions and limitations

- Currency checks use decimal arithmetic with `ROUND_HALF_UP` to two decimal places. Confirm this rounding convention with finance.
- Future-date checks compare calendar dates against the reference date. Source timestamps are interpreted as local business time for this profiling exercise.
- Freshness currently uses the latest parsable timestamp, including future-dated records. Invalid future timestamps can hide stale valid data; pipeline freshness should use valid, non-future timestamps. The original orders file therefore must not be assumed fresh just because it has no freshness warning.
- The 400 loyalty-tier casing warnings reflect the proposed uppercase convention; they are normalisation findings, not 400 unusable customers.
- Empty or whitespace-only fields count as missing. Literal text such as `NULL` is not automatically treated as missing.
- Payments are compared individually against September order amounts. This does not yet resolve split payments, refunds, multiple successful payments, settlement windows, or Cash on Delivery exceptions.
- Duplicate records have been detected, but this report does not establish how many groups contain conflicting values versus identical copies. Inspect each group before implementing survivor selection.
- An order can reference a key present in a raw master whose own record fails validation. Pipeline validation must account for these downstream dependencies.
- Suggested handling includes preventive rules, even where this run found no affected records. Reported counts describe this profiling run only.
- The script generates the three profiling outputs; it does not automatically refresh this submission. After rerunning with changed inputs or dates, review and update this section.

### Three questions for the client

1. When duplicate keys have conflicting values, which source/version takes precedence, and what evidence determines that precedence?
2. Should a return received in October restate September revenue or be an October adjustment, and do finance users need both historical and current views?
3. Which payment exceptions must block finance reporting, and how should pending settlements, split payments, refunds, and Cash on Delivery be reconciled?

## Part C — Scheduling and failure handling

Both main DAGs, `nammamart_etl_vijayc5` and `nammamart_elt_vijayc5`, use the settings below. Their [ETL](dags/nammamart_etl_vijayc5.py) and [ELT](dags/nammamart_elt_vijayc5.py) entry points supply the cron; the [shared DAG factories](include/nammamart_dag_factories.py) define timezone and failure handling. The observability aliases are deliberately unscheduled.

| Setting | Implemented value | Reason |
| --- | --- | --- |
| Schedule | `0 9 * * 1-6` | Minute 0, hour 9, every month, Monday–Saturday; no Sunday run |
| Start date / timezone | `pendulum.datetime(2026, 9, 1, tz='Asia/Kolkata')` | Explicit business timezone and a fixed scheduling start boundary |
| Catchup | `False` | These DAGs read the current CSV snapshots, not date-partitioned historical inputs; replaying every missed interval would repeatedly process the same files |
| Retries | `2` | Initial attempt plus two retries for transient failures |
| Retry delay | `timedelta(seconds=30)` | Short recovery window suitable for this local demonstration |
| Execution timeout | `timedelta(minutes=10)` | Limits each task attempt; it is not a ten-minute limit for the entire DAG |
| Concurrent runs | `max_active_runs=1` | Prevents overlapping runs of the same DAG from writing its warehouse/state concurrently |

The final `audit_run` task overrides retries to `0` and uses `trigger_rule='all_done'` so it attempts to record upstream failure too. DAGs are paused upon first creation and must be unpaused for scheduling. Part F demonstrated three attempts on the failed extraction/load tasks and successful selective recovery.

### Answers to the four scheduling questions

1. **What is the cron expression?** `0 9 * * 1-6`, interpreted in `Asia/Kolkata`: 9:00 AM IST, Monday–Saturday. The start date establishes eligibility; it does not itself mean a task starts at midnight on that date.
2. **What time appears in UTC?** The 09:00 IST schedule corresponds to **03:30 UTC on the same day**. With the UI set to UTC, inspect the next scheduled run at 03:30; a local-time display shows 09:00. Actual task starts can be later because of scheduler/worker availability. A run's logical date or data-interval label is not necessarily its wall-clock start time. [Airflow timezone documentation](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/timezone.html).
3. **What if the start date were left in UTC?** With this same cron and a UTC DAG timezone, the scheduled time would be **09:00 UTC = 14:30 IST**. No run would be due at 09:00 IST, and the morning review would miss its report. A naive start date also risks this result when the configured default timezone is UTC.
4. **What if the laptop or Docker is off at 9 AM?** No local task executes while the scheduler/workers are unavailable, so the deadline is missed. Restart the environment, confirm the DAG is unpaused, inspect its run history, and trigger the missing report if needed. `catchup=False` does not recreate every missed day. Whether a latest missed boundary runs after restart depends on the timetable and existing run state; a trigger timetable can skip missed boundaries, while an interval timetable can schedule the latest eligible interval. Do not rely on restart as guaranteed recovery. [Airflow timetable behaviour](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/timetable.html).

### Deadline interpretation

The brief asks both for data ready **before 09:00** and for DAGs scheduled **at 09:00**, while Part C names the **09:30** meeting deadline. I implemented the explicitly requested 09:00 schedule. Starting then does not prove either completion deadline. For production, agree a publication deadline with Operations, measure end-to-end duration including retries, and start sufficiently earlier if 09:00 readiness is mandatory. Use an always-on host and an alert when the expected successful publication is missing. Schedule/next-run screenshots remain separate submission evidence to capture.

## Part D — Data quality dimensions

Both pipelines implement the six dimensions below: Python/pandas in ETL and DuckDB SQL in ELT. The Part D evidence snapshot records **156 rule results** per run; the later Part F implementation adds five baseline file-volume checks (161 results per baseline run). [Executed rule catalogue](docs/DATA_QUALITY_RULES.md) and [verified scorecards](docs/DATA_QUALITY_GOVERNANCE_EVIDENCE.md) provide the run IDs and evidence. These operational rules supersede the proposed handling in Part 0 where explicitly noted below.

| Dimension | Implemented checks and examples | Severity and handling | Implementation |
| --- | --- | --- | --- |
| Completeness | Required keys, timestamps and product category; delivery time required for DELIVERED orders | Critical: quarantine or FAIL staging. Missing optional customer location is Warning. | ETL `check(..., 'Completeness', ...)`; ELT `*:missing` rules |
| Uniqueness | Exact duplicate copies and conflicting versions of each file's business key | Critical: keep the first normalised exact copy; quarantine excess copies. Conflicting key versions are ineligible. | ETL `duplicated` and conflicting-key set; SQL `exact_rank` and `key_versions` |
| Validity | Allowed order status/payment mode/zone; parseable dates; finite numbers; integer quantities; discount 0–100; email/phone/pincode formats | Critical for financial fields/statuses; contact-format issues are Warning and reporting values are redacted. | ETL parsing and allowed-value checks; SQL TRY casts, regular expressions and allowed lists |
| Accuracy | Positive quantity, price and capacity; nonnegative amounts; cost ≤ MRP; recomputed order amount; delivery below 120 minutes | Critical for invalid values/formula mismatches. Delivery outside 8–35 minutes also logs a Warning. | ETL decimal formula and numeric checks; SQL decimal formula and numeric predicates |
| Consistency | Orders reference accepted master records; payments reference orders; delivered orders have one accepted SUCCESS payment of the same amount; whitespace/casing normalisation | Critical for invalid references and reconciliation; normalisation is Warning. | ETL accepted-key sets/payment matching; SQL accepted staging joins and `payment_holds` |
| Timeliness | Future dates prohibited; newest parsable, non-future order date must be within one day of the reference date | Future dates Critical; stale source Warning. Historical fixtures are expected to warn. | Both use explicit `as_of`, defaulting to the current IST date |

**Operational finance decision:** both implementations currently hold delivered orders without exactly one valid matching SUCCESS payment out of finance facts. This is stricter than Part 0's proposed missing-payment warning; COD, delayed settlement, split-payment and refund policies still need client approval. ETL checks accepted masters before orders, so downstream rejections may exceed the profiler's direct findings.

**Quality result versus pipeline result:** a successful run can contain critical findings because rejected records are correctly excluded. Critical findings do not automatically mean the entire DAG failed. WARN-only records can load; a row with any Critical failure cannot enter the finance mart. ELT stores rejected originals in raw and reasons/lineage in `quality_records` and `elt_quarantine`; ETL writes original failed rows with `failure_reason` to its private quarantine folder.

### Quality scorecard and persistence

Both warehouse files contain `dq_results` with `run_id`, `dag_id`, `check_name`, `dimension`, `severity`, `rows_checked`, `rows_failed`, `status` and `checked_at`. ETL persists its check results during the final audit; ELT persists them in the staging transaction. Results are replaced for the same run on retry, while different-run history remains. An extraction/schema failure before validation has no completed rule results: it must appear as **NOT_EVALUATED**, never an invented quality pass. Database failure can prevent audit persistence; Airflow logs remain necessary evidence.

Use [dq_dimension_scorecard.sql](include/sql/nammamart/dq_dimension_scorecard.sql) against either warehouse. It returns all six dimensions for every audited run, including runs without checks. Failed-check evaluations are not unique rejected records, since a row can fail several rules. The current freshness check is file-level but attributes its warning to every evaluated order; a large timeliness count is not thousands of distinct freshness incidents.

```sql
SELECT run_id, dag_id, dimension, severity, count(*) AS checks,
       sum(rows_checked) AS check_evaluations,
       sum(rows_failed) AS failed_check_evaluations
FROM dq_results
GROUP BY run_id, dag_id, dimension, severity
ORDER BY run_id, dimension, severity;
```

The latest ELT run includes the incremental feed while the latest ETL run is still a baseline snapshot. Therefore consistency and freshness counts differ; this is not a like-for-like quality comparison. Baseline parity was verified separately during ELT implementation. Existing validation excludes future-dated timestamps before calculating freshness, unlike the initial discovery profiler.

To regenerate the evidence, executed-rule catalogue and data dictionary without changing warehouse data:

```bash
.venv/bin/python include/export_nammamart_governance.py
```

This evidence covers the six Part D dimensions. Part F below separately records the completed volume, drift and recovery experiments. Quality checks detect the stated rules, not every possible business error; for example, some nonfinancial category fields are required but do not yet have an approved enumeration.

## Part E — Data governance

### 1. Ownership and rule changes

Orders: Operations; payments: Finance; customers: CRM/customer operations with privacy oversight; products: Merchandising; stores: Store Operations. Engineering owns pipeline reliability and warehouse implementation, while Finance approves revenue definitions and Operations approves delivery KPIs. A 120-minute limit change needs Operations approval, Finance review of reporting impact, and an engineering change with tests and a recorded effective date.

### 2. Data dictionary

The [data dictionary](docs/DATA_DICTIONARY.md) lists every current ETL fact/dimension column, actual type, meaning, source, allowed rule and PII classification, with ELT mappings and metadata differences. It documents inferred ETL types versus explicit ELT types, redaction and fields whose enumerations are not yet enforced. “Allowed” denotes pipeline policy; these are not all warehouse constraints.

### 3. Lineage

Verified example: `mart_daily_store_kpis` reports **138.60** for **2026-09-03 / S04 / South**. Delivered order `ORD000159`, source `orders.csv` data record **885**, contributes `2 × 77 × (1 − 10/100) = 138.60`; cancelled `ORD000198` contributes zero. ELT carries batch/record lineage directly; ETL produces the same total but needs its retained source snapshot and order-ID lookup. [Exact lineage evidence](docs/DATA_QUALITY_GOVERNANCE_EVIDENCE.md).

```sql
-- ELT: exact contributing source records for the verified KPI.
SELECT f.order_id, f.order_status, f.net_revenue,
       r._source_file, r._run_id, r._batch_id, r._row_number,
       r.quantity, r.unit_price, r.discount_pct, r.order_amount
FROM mart_fact_orders f JOIN raw_orders r
  ON f._batch_id=r._batch_id AND f._row_number=r._row_number
WHERE f.order_date=DATE '2026-09-03' AND f.store_id='S04';
```

### 4. Personal data and Indian law

Both pipelines replace customer `full_name`, `email`, `phone` and store `manager_name` with `[REDACTED]` in reporting/staging. Raw originals are retained for controlled audit/replay, rather than being destroyed during transformation. This is redaction, not anonymisation: customer keys, locations and transaction history remain linkable personal data and still require protection.

| Dataset | Personal-data inventory and treatment |
| --- | --- |
| customers.csv | All columns relate to a customer: `customer_id`, `full_name`, `email`, `phone`, `city`, `area`, `pincode`, `signup_date`, `loyalty_tier`, `is_active`. Name/email/phone redacted downstream; remaining attributes retained for defined analytics purposes. |
| orders.csv and incremental orders | `order_id`, `order_ts`, `customer_id`, `store_id`, `product_id`, `quantity`, `unit_price`, `discount_pct`, `order_amount`, `payment_mode`, `order_status`, `channel`, `delivery_minutes` form linkable purchase/behaviour records. IDs are not anonymised; reporting remains restricted. |
| payments.csv | `payment_id`, `order_id`, `payment_ts`, `payment_mode`, `amount_paid`, `payment_status`, `gateway_ref` are linkable payment information. Reconciliation needs restricted access even without a customer name. |
| stores.csv | `manager_name` directly identifies an employee and is redacted downstream. The manager's association with a store/location is also personal context; store business attributes alone are not customer PII. |
| products.csv | No direct personal data in the standalone product catalogue. Product purchases become personal context when joined to identifiable customer orders. |

The relevant framework is India's **Digital Personal Data Protection Act, 2023**, with the **DPDP Rules, 2025**: plan for lawful, purpose-specific processing, clear notices/consent where required, minimisation, safeguards, individual rights, breach handling and justified retention. As of **25 October 2026**, commencement is phased; do not claim that all substantive duties are already in force. The official notification places major processing provisions eighteen months after publication. [Government overview](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2190014) and [commencement notification](https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf).

### 5. Access control

Proposed access: engineering service identities write raw/staging; designated engineers, data stewards and authorised auditors get purpose-limited raw/quarantine access. Analysts read masked staging where necessary; Finance/Operations read approved marts, with customer/payment-level access narrower than aggregate access. Raw customer phone/email access is for authorised incident, support or audit work only—not routine reporting.

**Current limitation:** local DuckDB files and Git ignores do not enforce table-level roles, encryption or access logging. Production requires separate protected storage or an authenticated query service with least-privilege roles, audited access and controlled exports. The assignment's local demonstration must not be described as deployed access control.

### 6. Retention

Proposed policy: keep canonical raw transaction/audit records for **one year from processing**, subject to applicable longer legal holds; remove redundant debugging/quarantine copies **30 days after resolution**, retaining canonical evidence and reasons. Review masked customer-level analytics at **12 months** and erase or irreversibly aggregate when no approved purpose or legal requirement remains. These are proposed policies, not configured deletion jobs.

The final Rules include one-year retention provisions for specified personal-data/log purposes once applicable; legal review must reconcile this with other recordkeeping duties before enabling purge. Archive/backup copies and downstream exports must follow the approved schedule, with a deletion manifest and hold checks. [Official Rules, rules 6 and 8](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf). The assignment's “never deleted” raw rule means no deletion during ordinary cleaning/reruns; production lifecycle erasure must be a separately approved process. No source or raw records were deleted for this submission.

### 7. Secrets

The NammaMart DAGs use local CSV/DuckDB files and currently require no external credentials. If alerts are added, store `SLACK_WEBHOOK_URL` in an Airflow Variable or an approved secrets backend and retrieve it at task runtime using `Variable.get()`; do not place its value in DAGs, logs or GitHub. This is a configuration policy, not evidence that an alert secret has already been configured.

### 8. Rejected-order audit

Verified order **ORD000099** has quantity zero and fails `quantity:nonpositive`. ETL retains its original fields plus the reason in the run's quarantine CSV; ELT retains the received record in `raw_orders` and identifies it through `elt_quarantine` batch/record metadata. Both current finance fact tables contain **zero rows** for this order, proving it contributes no reported revenue. [Run-specific evidence and paths](docs/DATA_QUALITY_GOVERNANCE_EVIDENCE.md).

```sql
-- ELT: inspect original fields only in an authorised private session.
SELECT r.*, q.failure_reason
FROM elt_quarantine q JOIN raw_orders r
  ON q.batch_id=r._batch_id AND q.row_number=r._row_number
WHERE q.row_key='ORD000099' AND q.source_file='orders.csv';
SELECT count(*) AS finance_rows FROM mart_fact_orders WHERE order_id='ORD000099';
-- ETL warehouse: inspect the CSV named in the evidence document separately.
SELECT count(*) AS finance_rows FROM etl_fact_orders WHERE order_id='ORD000099';
```

### 9. Change history

For a delivered September order returned in October, ELT's latest-state upsert makes its original September revenue zero; raw retains the earlier delivered version. ETL now also supports the supplied increment and retains corrections across subsequent baseline runs. The isolated Part F run verified both pipelines recorded 150 inserted keys, 10 changed keys and ten RETURNED corrections; both published 1,777 facts with total revenue 864,042.35. This does not imply the main ETL warehouse has already been rerun with the increment. Confirm Finance's restatement policy; preserve both “as originally reported” and “latest corrected” views using versioned facts or dated reporting snapshots, which are not yet implemented.

For an actual feed example, `ORD000271` was ordered on 4 September and is RETURNED in current ELT staging. The assignment's 3 September example is illustrative, not a claim that this exact date occurs among the ten supplied corrections. A version-history feature must retain effective and ingestion times so later corrections can be distinguished from what was known at the original report time.

## Part F: Observability tests — completed

Executed all ten experiments on **both ETL and ELT** in the local Astro scheduler on **26 October 2026**, suite `obs_20261026_03`. The experiment DAGs share the main DAGs' task factories and use isolated private input copies and warehouses. Validation used the fixed reference date **2026-10-25**. Original dataset hashes remained unchanged; case inputs were restored and the unscheduled experiment DAGs were paused afterward.

[Detailed evidence: per-file counts, task durations, run IDs, retry timings and Clear recovery](docs/OBSERVABILITY_obs_20261026_03.md). [Machine-readable Airflow states and SQL measurements](include/observability_reports/observability_obs_20261026_03.json).

Both DAGs have an `all_done` audit task with one `pipeline_runs` row per run containing `run_id`, `dag_id`, `start_time`, `end_time`, `rows_extracted`, `rows_loaded`, `rows_quarantined` and `status`. An upstream failure produces a FAILED audit and a red DAG. Clear updates that run's audit to SUCCESS after recovery; the evidence preserves the earlier failed attempt states.

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


Baseline per-file received / accepted / quarantined counts were identical in both: orders **2,412 / 1,777 / 635**, payments **2,228 / 2,202 / 26**, customers **405 / 392 / 13**, products **152 / 140 / 12**, stores **15 / 13 / 2**. The five ETL extract task intervals overlapped; ELT's raw, staging and mart tasks were sequential. Exact task durations and timestamps are in the detailed report.

The volume experiment also exposed a policy difference: ETL quarantined **2,220** records versus **64** in ELT. ETL checks payment references against the current orders; ELT checks all retained raw order history. Both produced **39 facts / 17,865.00 revenue**, but rejection counts are not interchangeable. This reference policy should be aligned before production. Increment rejection totals differ too (**838 ETL / 842 ELT**) because ETL evaluates the merged effective orders, while ELT evaluates baseline and increment records before selecting the winning version.

### Five pillars of data observability

| Pillar | Implemented evidence | Limitation |
|---|---|---|
| Freshness | Latest nonfuture order date versus reference date; stale warning | No production publication gate or notification |
| Volume | Previous-versus-current row count; >90% drop warning | No seasonality; ETL uses last committed counts, ELT previous received batches |
| Schema | Exact required columns; loud failure before publication | No schema evolution workflow |
| Distribution | Formula, range and reconciliation checks catch this price mutation | Weakest: no learned/statistical drift baseline; coherent price/amount changes can pass |
| Lineage | Run IDs, raw batch/source/row references in ELT, ETL run snapshots, quarantine reasons and publication audit | Strongest, especially ELT; no external lineage catalogue or historical mart snapshots |


The exploratory run caught a decimal overflow in the ELT formula under 100× prices; widening the intermediate calculation fixed it. It also exposed an Airflow Clear selector mismatch, now fixed and verified with same-run recovery. **Twelve local integration tests passed**, including price-drift and retained-increment regression tests. The final scheduler suite and its evidence assertions passed. These results complete Part F; they do not claim external notifications, statistical drift monitoring or the entire assignment submission is finished.

## Part G — Recommendation to the client

**To: Sameer, CTO, NammaMart**  
**Subject: Adopt ELT with restricted raw access and validated finance marts**  
**Date: 29 October 2026**

I recommend **ELT** as NammaMart's primary pipeline, with Finance and Operations consuming only approved marts. Retain the ETL implementation as a regression reference during adoption. ELT best supports your need to explain reported numbers, investigate payment exceptions and apply late returns, while its staging checks can enforce the same finance inclusion rules as ETL.

**Evidence and quality guarantees.** In our baseline experiment, both pipelines received 5,212 rows and published the same 1,777 approved order facts with total net revenue of 865,874.05 across the supplied snapshot. Re-running preserved those facts and revenue. Both rejected all five injected bad orders with the expected reasons, failed loudly on missing files and schema changes, and recovered through selective Clear. These tests demonstrate the implemented checks, not protection against every possible business error. Freshness and volume currently warn without stopping publication; production should block or explicitly label incomplete reports using thresholds agreed with Operations and Finance. [Executed comparison and experiments](docs/OBSERVABILITY_obs_20261026_03.md).

**Auditability and ease of change.** ELT preserves source values and links records to file, batch, row and run metadata. We traced the S04 daily revenue of 138.60 directly to its contributing source record; ETL required a separate snapshot lookup. Both applied 150 new order keys and ten RETURNED corrections without duplicate facts. ELT's retained raw history makes revised SQL rules and investigations easier to replay, whereas ETL requires its source snapshots and another transformation run. Version SQL changes, rerun regression checks and obtain business-owner approval before changing finance definitions. Current marts show the latest corrected state; keeping both original and restated reports still requires versioned reporting snapshots. [Lineage evidence](docs/DATA_QUALITY_GOVERNANCE_EVIDENCE.md).

**Performance at 1,000× volume.** Roughly 5.2 million rows per equivalent five-file batch is a sizing scenario, not a tested capacity claim. The small local run showed parallel ETL extracts and sequential ELT layers; it does not establish a scaling winner. Benchmark both on representative larger data, measuring memory, disk, elapsed time and concurrent readers. For ELT, avoid repeatedly appending full unchanged exports and recomputing all history: adopt versioned incremental batches and process affected records while retaining canonical raw evidence. Move beyond a single local warehouse if measured contention or recovery requirements demand it.

**Cost and rollout.** The demonstrated Airflow, pandas and DuckDB stack needs no paid data-platform service. Production still incurs hosting, storage, backup, monitoring and engineering costs; ELT's growing raw history makes retention especially important. Begin with an always-on deployment, restricted raw/quarantine storage, masked marts, publication alerts and a Finance sign-off on reconciliation and return treatment. Current local file access does not enforce these production controls.

**Top three risks:**

1. **Misleading finance results:** unresolved settlement/return rules, differing orphan-payment policies and warning-only publication checks can produce incomplete totals. Agree one rule set, align reference checks and require publication gates.
2. **Personal-data exposure:** raw and quarantine retain identifiable data without enforced database roles. Restrict and audit access, protect storage/backups and implement approved retention.
3. **Missed deadlines as data grows:** laptop outages, full-batch processing and unbounded raw growth threaten delivery. Use an always-on host, benchmark 1,000× volume, implement incremental processing and test restore procedures.

## Business questions — SQL and executed results

Read-only exports captured from both local warehouses for successful run `scheduled__2026-10-29T03:30:00+00:00`:

| Pipeline | Executable SQL | Complete results, including SQL |
| --- | --- | --- |
| ETL | [Six business questions](docs/business_results/etl_business.sql) | [ETL results](docs/business_results/etl_results.md) |
| ELT | [Six business questions](docs/business_results/elt_business.sql) | [ELT results](docs/business_results/elt_results.md) |

Revenue, margin, delivery and customer-spend queries cover September 2026 and approved DELIVERED orders. Q4 includes both payment-mode revenue and a separate full-snapshot reconciliation summary; unknown amounts are counted separately, not treated as zero. Q6 counts rejections in the selected processing run, with unique file totals separated from overlapping reason counts. The files contain full results rather than screenshot-sized samples.

**Comparison:** the main ETL warehouse currently reflects the baseline, while ELT retains the supplied incremental corrections. September revenue is **864,887.20 ETL / 863,055.50 ELT**, with 1,776 approved fact rows in each (including non-delivered statuses). Six approved orders changed from DELIVERED to RETURNED, explaining the complete **1,831.70** revenue difference. ELT's other four returned corrections are not in the approved September fact set. The [capture guide](docs/SUBMISSION_CAPTURE_GUIDE.md) lists the six contributing order IDs and amounts. Equal-input parity was demonstrated separately in Part F; the current main-warehouse exports intentionally report their actual input histories.

**Screenshots:** follow the [capture checklist](docs/SUBMISSION_CAPTURE_GUIDE.md) and the verified [ETL](docs/business_results/etl_screenshots.sql) / [ELT](docs/business_results/elt_screenshots.sql) screenshot queries. Existing images cover ETL success, a partly clipped ELT success graph and the ELT schedule; the complete screenshot evidence still needs to be assembled and linked here.

## Remaining assignment work

Both pipelines, their supplied-feed incremental handling and all ten Part F observability experiments have been implemented and tested; Parts C, D, E, F and G are documented here. SQL plus actual results for all six business questions from both pipelines are linked above. Remaining submission work: capture/verify and link the required screenshots. Access roles, retention enforcement, historical reporting snapshots and client approval of unresolved finance rules remain proposed work; they are not claimed as implemented controls.
