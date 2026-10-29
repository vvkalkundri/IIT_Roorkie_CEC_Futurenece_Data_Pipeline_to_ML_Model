-- payments: normalise only inside SQL; raw fields remain untouched.
CREATE OR REPLACE TEMP TABLE n_payments AS
SELECT trim(r."payment_id") AS "payment_id",
 trim(r."order_id") AS "order_id",
 trim(r."payment_ts") AS "payment_ts",
 CASE upper(trim(r."payment_mode")) WHEN 'UPI' THEN 'UPI' WHEN 'CARD' THEN 'Card' WHEN 'CASH ON DELIVERY' THEN 'Cash on Delivery' WHEN 'WALLET' THEN 'Wallet' ELSE trim(r."payment_mode") END AS "payment_mode",
 trim(r."amount_paid") AS "amount_paid",
 upper(trim(r."payment_status")) AS "payment_status",
 trim(r."gateway_ref") AS "gateway_ref", r."payment_id" AS "_original_payment_id", r."order_id" AS "_original_order_id", r."payment_ts" AS "_original_payment_ts", r."payment_mode" AS "_original_payment_mode", r."amount_paid" AS "_original_amount_paid", r."payment_status" AS "_original_payment_status", r."gateway_ref" AS "_original_gateway_ref", r._loaded_at, r._source_file, r._run_id, r._batch_id, r._row_number
FROM raw_payments r JOIN latest_batches b ON r._batch_id=b.batch_id;
CREATE OR REPLACE TEMP TABLE v_payments AS
SELECT *, row_number() OVER(PARTITION BY _batch_id, "payment_id", "order_id", "payment_ts", "payment_mode", "amount_paid", "payment_status", "gateway_ref" ORDER BY _row_number) AS exact_rank,
 count(DISTINCT row("payment_id", "order_id", "payment_ts", "payment_mode", "amount_paid", "payment_status", "gateway_ref")) OVER(PARTITION BY _batch_id, "payment_id") AS key_versions
FROM n_payments;
CREATE OR REPLACE TEMP TABLE checks_payments AS
SELECT _batch_id, _row_number, rule_name, dimension, severity, failed
FROM v_payments, LATERAL (VALUES
 ('payment_id:whitespace', 'Consistency', 'Warning', coalesce(("_original_payment_id" <> trim("_original_payment_id")),false)),
 ('order_id:whitespace', 'Consistency', 'Warning', coalesce(("_original_order_id" <> trim("_original_order_id")),false)),
 ('payment_ts:whitespace', 'Consistency', 'Warning', coalesce(("_original_payment_ts" <> trim("_original_payment_ts")),false)),
 ('payment_mode:whitespace', 'Consistency', 'Warning', coalesce(("_original_payment_mode" <> trim("_original_payment_mode")),false)),
 ('amount_paid:whitespace', 'Consistency', 'Warning', coalesce(("_original_amount_paid" <> trim("_original_amount_paid")),false)),
 ('payment_status:whitespace', 'Consistency', 'Warning', coalesce(("_original_payment_status" <> trim("_original_payment_status")),false)),
 ('payment_status:casing', 'Consistency', 'Warning', coalesce((trim("_original_payment_status") <> upper(trim("_original_payment_status"))),false)),
 ('gateway_ref:whitespace', 'Consistency', 'Warning', coalesce(("_original_gateway_ref" <> trim("_original_gateway_ref")),false)),
 ('exact_duplicate', 'Uniqueness', 'Critical', coalesce((exact_rank > 1),false)),
 ('conflicting_key', 'Uniqueness', 'Critical', coalesce((key_versions > 1),false)),
 ('payment_id:missing', 'Completeness', 'Critical', coalesce(("payment_id" = ''),false)),
 ('order_id:missing', 'Completeness', 'Critical', coalesce(("order_id" = ''),false)),
 ('payment_ts:missing', 'Completeness', 'Critical', coalesce(("payment_ts" = ''),false)),
 ('payment_ts:invalid_date', 'Validity', 'Critical', coalesce(("payment_ts" <> '' AND try_strptime("payment_ts", '%Y-%m-%d %H:%M:%S') IS NULL),false)),
 ('payment_ts:future', 'Timeliness', 'Critical', coalesce((cast(try_strptime("payment_ts", '%Y-%m-%d %H:%M:%S') AS DATE) > (SELECT as_of FROM run_context)),false)),
 ('payment_mode:missing', 'Completeness', 'Critical', coalesce(("payment_mode" = ''),false)),
 ('payment_mode:unknown', 'Validity', 'Critical', coalesce((upper("payment_mode") NOT IN ('CARD', 'CASH ON DELIVERY', 'UPI', 'WALLET')),false)),
 ('amount_paid:missing', 'Completeness', 'Critical', coalesce(("amount_paid" = ''),false)),
 ('amount_paid:invalid_number', 'Validity', 'Critical', coalesce(("amount_paid" <> '' AND (try_cast("amount_paid" AS DOUBLE) IS NULL OR NOT isfinite(try_cast("amount_paid" AS DOUBLE)))),false)),
 ('amount_paid:negative', 'Accuracy', 'Critical', coalesce((isfinite(try_cast("amount_paid" AS DOUBLE)) AND try_cast("amount_paid" AS DOUBLE) < 0),false)),
 ('payment_status:missing', 'Completeness', 'Critical', coalesce(("payment_status" = ''),false)),
 ('order_id:orphan', 'Consistency', 'Critical', coalesce((order_id NOT IN (SELECT trim(order_id) FROM raw_orders)),false))
) c(rule_name, dimension, severity, failed);
INSERT INTO dq_results
SELECT (SELECT run_id FROM run_context), (SELECT dag_id FROM run_context), 'payments.csv:' || rule_name,
 dimension, severity, count(*), count(*) FILTER(WHERE failed),
 CASE WHEN bool_or(failed) THEN 'FAIL' ELSE 'PASS' END, current_timestamp
FROM checks_payments GROUP BY rule_name, dimension, severity;
CREATE OR REPLACE TEMP TABLE evaluated_payments AS
SELECT v.*, q.failure_reason, q.warning_reason,
 CASE WHEN q.failure_reason <> '' THEN 'FAIL' WHEN q.warning_reason <> '' THEN 'WARN' ELSE 'PASS' END AS dq_status
FROM v_payments v JOIN (
 SELECT _batch_id, _row_number,
 coalesce(string_agg(rule_name, '; ' ORDER BY rule_name) FILTER(WHERE failed AND severity='Critical'),'') failure_reason,
 coalesce(string_agg(rule_name, '; ' ORDER BY rule_name) FILTER(WHERE failed AND severity='Warning'),'') warning_reason
 FROM checks_payments GROUP BY _batch_id, _row_number
) q USING(_batch_id,_row_number);
INSERT INTO quality_records
SELECT (SELECT run_id FROM run_context), _source_file, _run_id, _batch_id, _row_number,
 payment_id, dq_status, failure_reason FROM evaluated_payments;
CREATE OR REPLACE TEMP TABLE candidate_payments AS
SELECT "payment_id" AS "payment_id",
 "order_id" AS "order_id",
 try_strptime("payment_ts", '%Y-%m-%d %H:%M:%S') AS "payment_ts",
 "payment_mode" AS "payment_mode",
 try_cast("amount_paid" AS DECIMAL(18,4)) AS "amount_paid",
 "payment_status" AS "payment_status",
 "gateway_ref" AS "gateway_ref", _loaded_at, _source_file, _run_id, _batch_id, _row_number,
 dq_status, failure_reason, warning_reason,
 md5(cast(row("payment_id", "order_id", "payment_ts", "payment_mode", "amount_paid", "payment_status", "gateway_ref") AS VARCHAR)) AS _payload_hash
FROM evaluated_payments
QUALIFY row_number() OVER(PARTITION BY payment_id ORDER BY  _batch_id DESC, exact_rank, _row_number)=1;
CREATE OR REPLACE TABLE stg_payments AS SELECT * FROM candidate_payments;
