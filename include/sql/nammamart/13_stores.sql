-- stores: normalise only inside SQL; raw fields remain untouched.
CREATE OR REPLACE TEMP TABLE n_stores AS
SELECT trim(r."store_id") AS "store_id",
 trim(r."store_name") AS "store_name",
 upper(left(trim(r."zone"),1)) || lower(substr(trim(r."zone"),2)) AS "zone",
 trim(r."area") AS "area",
 trim(r."pincode") AS "pincode",
 trim(r."open_date") AS "open_date",
 trim(r."manager_name") AS "manager_name",
 trim(r."capacity_orders_per_day") AS "capacity_orders_per_day", r."store_id" AS "_original_store_id", r."store_name" AS "_original_store_name", r."zone" AS "_original_zone", r."area" AS "_original_area", r."pincode" AS "_original_pincode", r."open_date" AS "_original_open_date", r."manager_name" AS "_original_manager_name", r."capacity_orders_per_day" AS "_original_capacity_orders_per_day", r._loaded_at, r._source_file, r._run_id, r._batch_id, r._row_number
FROM raw_stores r JOIN latest_batches b ON r._batch_id=b.batch_id;
CREATE OR REPLACE TEMP TABLE v_stores AS
SELECT *, row_number() OVER(PARTITION BY _batch_id, "store_id", "store_name", "zone", "area", "pincode", "open_date", "manager_name", "capacity_orders_per_day" ORDER BY _row_number) AS exact_rank,
 count(DISTINCT row("store_id", "store_name", "zone", "area", "pincode", "open_date", "manager_name", "capacity_orders_per_day")) OVER(PARTITION BY _batch_id, "store_id") AS key_versions
FROM n_stores;
CREATE OR REPLACE TEMP TABLE checks_stores AS
SELECT _batch_id, _row_number, rule_name, dimension, severity, failed
FROM v_stores, LATERAL (VALUES
 ('store_id:whitespace', 'Consistency', 'Warning', coalesce(("_original_store_id" <> trim("_original_store_id")),false)),
 ('store_name:whitespace', 'Consistency', 'Warning', coalesce(("_original_store_name" <> trim("_original_store_name")),false)),
 ('zone:whitespace', 'Consistency', 'Warning', coalesce(("_original_zone" <> trim("_original_zone")),false)),
 ('area:whitespace', 'Consistency', 'Warning', coalesce(("_original_area" <> trim("_original_area")),false)),
 ('pincode:whitespace', 'Consistency', 'Warning', coalesce(("_original_pincode" <> trim("_original_pincode")),false)),
 ('open_date:whitespace', 'Consistency', 'Warning', coalesce(("_original_open_date" <> trim("_original_open_date")),false)),
 ('manager_name:whitespace', 'Consistency', 'Warning', coalesce(("_original_manager_name" <> trim("_original_manager_name")),false)),
 ('capacity_orders_per_day:whitespace', 'Consistency', 'Warning', coalesce(("_original_capacity_orders_per_day" <> trim("_original_capacity_orders_per_day")),false)),
 ('exact_duplicate', 'Uniqueness', 'Critical', coalesce((exact_rank > 1),false)),
 ('conflicting_key', 'Uniqueness', 'Critical', coalesce((key_versions > 1),false)),
 ('store_id:missing', 'Completeness', 'Critical', coalesce(("store_id" = ''),false)),
 ('store_name:missing', 'Completeness', 'Critical', coalesce(("store_name" = ''),false)),
 ('zone:missing', 'Completeness', 'Critical', coalesce(("zone" = ''),false)),
 ('zone:unknown', 'Validity', 'Critical', coalesce((upper("zone") NOT IN ('EAST', 'NORTH', 'SOUTH', 'WEST')),false)),
 ('area:missing', 'Completeness', 'Warning', coalesce(("area" = ''),false)),
 ('pincode:missing', 'Completeness', 'Warning', coalesce(("pincode" = ''),false)),
 ('pincode:format', 'Validity', 'Warning', coalesce(("pincode" <> '' AND NOT regexp_full_match("pincode", '[0-9]{6}')),false)),
 ('open_date:missing', 'Completeness', 'Critical', coalesce(("open_date" = ''),false)),
 ('open_date:invalid_date', 'Validity', 'Critical', coalesce(("open_date" <> '' AND try_strptime("open_date", '%Y-%m-%d') IS NULL),false)),
 ('open_date:future', 'Timeliness', 'Critical', coalesce((cast(try_strptime("open_date", '%Y-%m-%d') AS DATE) > (SELECT as_of FROM run_context)),false)),
 ('manager_name:missing', 'Completeness', 'Warning', coalesce(("manager_name" = ''),false)),
 ('capacity_orders_per_day:missing', 'Completeness', 'Critical', coalesce(("capacity_orders_per_day" = ''),false)),
 ('capacity_orders_per_day:invalid_number', 'Validity', 'Critical', coalesce(("capacity_orders_per_day" <> '' AND (try_cast("capacity_orders_per_day" AS DOUBLE) IS NULL OR NOT isfinite(try_cast("capacity_orders_per_day" AS DOUBLE)))),false)),
 ('capacity_orders_per_day:nonpositive', 'Accuracy', 'Critical', coalesce((isfinite(try_cast("capacity_orders_per_day" AS DOUBLE)) AND try_cast("capacity_orders_per_day" AS DOUBLE) <= 0),false)),
 ('capacity_orders_per_day:not_integer', 'Validity', 'Critical', coalesce((isfinite(try_cast("capacity_orders_per_day" AS DOUBLE)) AND try_cast("capacity_orders_per_day" AS DOUBLE) % 1 <> 0),false))
) c(rule_name, dimension, severity, failed);
INSERT INTO dq_results
SELECT (SELECT run_id FROM run_context), (SELECT dag_id FROM run_context), 'stores.csv:' || rule_name,
 dimension, severity, count(*), count(*) FILTER(WHERE failed),
 CASE WHEN bool_or(failed) THEN 'FAIL' ELSE 'PASS' END, current_timestamp
FROM checks_stores GROUP BY rule_name, dimension, severity;
CREATE OR REPLACE TEMP TABLE evaluated_stores AS
SELECT v.*, q.failure_reason, q.warning_reason,
 CASE WHEN q.failure_reason <> '' THEN 'FAIL' WHEN q.warning_reason <> '' THEN 'WARN' ELSE 'PASS' END AS dq_status
FROM v_stores v JOIN (
 SELECT _batch_id, _row_number,
 coalesce(string_agg(rule_name, '; ' ORDER BY rule_name) FILTER(WHERE failed AND severity='Critical'),'') failure_reason,
 coalesce(string_agg(rule_name, '; ' ORDER BY rule_name) FILTER(WHERE failed AND severity='Warning'),'') warning_reason
 FROM checks_stores GROUP BY _batch_id, _row_number
) q USING(_batch_id,_row_number);
INSERT INTO quality_records
SELECT (SELECT run_id FROM run_context), _source_file, _run_id, _batch_id, _row_number,
 store_id, dq_status, failure_reason FROM evaluated_stores;
CREATE OR REPLACE TEMP TABLE candidate_stores AS
SELECT "store_id" AS "store_id",
 "store_name" AS "store_name",
 "zone" AS "zone",
 "area" AS "area",
 "pincode" AS "pincode",
 try_strptime("open_date", '%Y-%m-%d') AS "open_date",
 '[REDACTED]' AS "manager_name",
 try_cast("capacity_orders_per_day" AS DECIMAL(18,4)) AS "capacity_orders_per_day", _loaded_at, _source_file, _run_id, _batch_id, _row_number,
 dq_status, failure_reason, warning_reason,
 md5(cast(row("store_id", "store_name", "zone", "area", "pincode", "open_date", "manager_name", "capacity_orders_per_day") AS VARCHAR)) AS _payload_hash
FROM evaluated_stores
QUALIFY row_number() OVER(PARTITION BY store_id ORDER BY  _batch_id DESC, exact_rank, _row_number)=1;
CREATE OR REPLACE TABLE stg_stores AS SELECT * FROM candidate_stores;
