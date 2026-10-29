-- orders: normalise only inside SQL; raw fields remain untouched.
CREATE OR REPLACE TEMP TABLE n_orders AS
SELECT trim(r."order_id") AS "order_id",
 trim(r."order_ts") AS "order_ts",
 trim(r."customer_id") AS "customer_id",
 trim(r."store_id") AS "store_id",
 trim(r."product_id") AS "product_id",
 trim(r."quantity") AS "quantity",
 trim(r."unit_price") AS "unit_price",
 trim(r."discount_pct") AS "discount_pct",
 trim(r."order_amount") AS "order_amount",
 CASE upper(trim(r."payment_mode")) WHEN 'UPI' THEN 'UPI' WHEN 'CARD' THEN 'Card' WHEN 'CASH ON DELIVERY' THEN 'Cash on Delivery' WHEN 'WALLET' THEN 'Wallet' ELSE trim(r."payment_mode") END AS "payment_mode",
 upper(trim(r."order_status")) AS "order_status",
 trim(r."channel") AS "channel",
 trim(r."delivery_minutes") AS "delivery_minutes", r."order_id" AS "_original_order_id", r."order_ts" AS "_original_order_ts", r."customer_id" AS "_original_customer_id", r."store_id" AS "_original_store_id", r."product_id" AS "_original_product_id", r."quantity" AS "_original_quantity", r."unit_price" AS "_original_unit_price", r."discount_pct" AS "_original_discount_pct", r."order_amount" AS "_original_order_amount", r."payment_mode" AS "_original_payment_mode", r."order_status" AS "_original_order_status", r."channel" AS "_original_channel", r."delivery_minutes" AS "_original_delivery_minutes", r._loaded_at, r._source_file, r._run_id, r._batch_id, r._row_number
FROM raw_orders r JOIN latest_batches b ON r._batch_id=b.batch_id;
CREATE OR REPLACE TEMP TABLE v_orders AS
SELECT *, row_number() OVER(PARTITION BY _batch_id, "order_id", "order_ts", "customer_id", "store_id", "product_id", "quantity", "unit_price", "discount_pct", "order_amount", "payment_mode", "order_status", "channel", "delivery_minutes" ORDER BY _row_number) AS exact_rank,
 count(DISTINCT row("order_id", "order_ts", "customer_id", "store_id", "product_id", "quantity", "unit_price", "discount_pct", "order_amount", "payment_mode", "order_status", "channel", "delivery_minutes")) OVER(PARTITION BY _batch_id, "order_id") AS key_versions
FROM n_orders;
CREATE OR REPLACE TEMP TABLE checks_orders AS
SELECT _batch_id, _row_number, rule_name, dimension, severity, failed
FROM v_orders, LATERAL (VALUES
 ('order_id:whitespace', 'Consistency', 'Warning', coalesce(("_original_order_id" <> trim("_original_order_id")),false)),
 ('order_ts:whitespace', 'Consistency', 'Warning', coalesce(("_original_order_ts" <> trim("_original_order_ts")),false)),
 ('customer_id:whitespace', 'Consistency', 'Warning', coalesce(("_original_customer_id" <> trim("_original_customer_id")),false)),
 ('store_id:whitespace', 'Consistency', 'Warning', coalesce(("_original_store_id" <> trim("_original_store_id")),false)),
 ('product_id:whitespace', 'Consistency', 'Warning', coalesce(("_original_product_id" <> trim("_original_product_id")),false)),
 ('quantity:whitespace', 'Consistency', 'Warning', coalesce(("_original_quantity" <> trim("_original_quantity")),false)),
 ('unit_price:whitespace', 'Consistency', 'Warning', coalesce(("_original_unit_price" <> trim("_original_unit_price")),false)),
 ('discount_pct:whitespace', 'Consistency', 'Warning', coalesce(("_original_discount_pct" <> trim("_original_discount_pct")),false)),
 ('order_amount:whitespace', 'Consistency', 'Warning', coalesce(("_original_order_amount" <> trim("_original_order_amount")),false)),
 ('payment_mode:whitespace', 'Consistency', 'Warning', coalesce(("_original_payment_mode" <> trim("_original_payment_mode")),false)),
 ('order_status:whitespace', 'Consistency', 'Warning', coalesce(("_original_order_status" <> trim("_original_order_status")),false)),
 ('order_status:casing', 'Consistency', 'Warning', coalesce((trim("_original_order_status") <> upper(trim("_original_order_status"))),false)),
 ('channel:whitespace', 'Consistency', 'Warning', coalesce(("_original_channel" <> trim("_original_channel")),false)),
 ('delivery_minutes:whitespace', 'Consistency', 'Warning', coalesce(("_original_delivery_minutes" <> trim("_original_delivery_minutes")),false)),
 ('exact_duplicate', 'Uniqueness', 'Critical', coalesce((exact_rank > 1),false)),
 ('conflicting_key', 'Uniqueness', 'Critical', coalesce((key_versions > 1),false)),
 ('order_id:missing', 'Completeness', 'Critical', coalesce(("order_id" = ''),false)),
 ('order_ts:missing', 'Completeness', 'Critical', coalesce(("order_ts" = ''),false)),
 ('order_ts:invalid_date', 'Validity', 'Critical', coalesce(("order_ts" <> '' AND try_strptime("order_ts", '%Y-%m-%d %H:%M:%S') IS NULL),false)),
 ('order_ts:future', 'Timeliness', 'Critical', coalesce((cast(try_strptime("order_ts", '%Y-%m-%d %H:%M:%S') AS DATE) > (SELECT as_of FROM run_context)),false)),
 ('orders:stale', 'Timeliness', 'Warning', coalesce((coalesce((SELECT as_of FROM run_context) - (SELECT max(try_cast(order_ts AS DATE)) FROM v_orders WHERE try_cast(order_ts AS DATE) <= (SELECT as_of FROM run_context)) > 1, true)),false)),
 ('customer_id:missing', 'Completeness', 'Critical', coalesce(("customer_id" = ''),false)),
 ('store_id:missing', 'Completeness', 'Critical', coalesce(("store_id" = ''),false)),
 ('product_id:missing', 'Completeness', 'Critical', coalesce(("product_id" = ''),false)),
 ('quantity:missing', 'Completeness', 'Critical', coalesce(("quantity" = ''),false)),
 ('quantity:invalid_number', 'Validity', 'Critical', coalesce(("quantity" <> '' AND (try_cast("quantity" AS DOUBLE) IS NULL OR NOT isfinite(try_cast("quantity" AS DOUBLE)))),false)),
 ('quantity:nonpositive', 'Accuracy', 'Critical', coalesce((isfinite(try_cast("quantity" AS DOUBLE)) AND try_cast("quantity" AS DOUBLE) <= 0),false)),
 ('quantity:not_integer', 'Validity', 'Critical', coalesce((isfinite(try_cast("quantity" AS DOUBLE)) AND try_cast("quantity" AS DOUBLE) % 1 <> 0),false)),
 ('unit_price:missing', 'Completeness', 'Critical', coalesce(("unit_price" = ''),false)),
 ('unit_price:invalid_number', 'Validity', 'Critical', coalesce(("unit_price" <> '' AND (try_cast("unit_price" AS DOUBLE) IS NULL OR NOT isfinite(try_cast("unit_price" AS DOUBLE)))),false)),
 ('unit_price:nonpositive', 'Accuracy', 'Critical', coalesce((isfinite(try_cast("unit_price" AS DOUBLE)) AND try_cast("unit_price" AS DOUBLE) <= 0),false)),
 ('discount_pct:missing', 'Completeness', 'Critical', coalesce(("discount_pct" = ''),false)),
 ('discount_pct:invalid_number', 'Validity', 'Critical', coalesce(("discount_pct" <> '' AND (try_cast("discount_pct" AS DOUBLE) IS NULL OR NOT isfinite(try_cast("discount_pct" AS DOUBLE)))),false)),
 ('discount:range', 'Validity', 'Critical', coalesce((isfinite(try_cast("discount_pct" AS DOUBLE)) AND try_cast("discount_pct" AS DOUBLE) NOT BETWEEN 0 AND 100),false)),
 ('order_amount:missing', 'Completeness', 'Critical', coalesce(("order_amount" = ''),false)),
 ('order_amount:invalid_number', 'Validity', 'Critical', coalesce(("order_amount" <> '' AND (try_cast("order_amount" AS DOUBLE) IS NULL OR NOT isfinite(try_cast("order_amount" AS DOUBLE)))),false)),
 ('order_amount:negative', 'Accuracy', 'Critical', coalesce((isfinite(try_cast("order_amount" AS DOUBLE)) AND try_cast("order_amount" AS DOUBLE) < 0),false)),
 ('payment_mode:missing', 'Completeness', 'Critical', coalesce(("payment_mode" = ''),false)),
 ('payment_mode:unknown', 'Validity', 'Critical', coalesce((upper("payment_mode") NOT IN ('CARD', 'CASH ON DELIVERY', 'UPI', 'WALLET')),false)),
 ('order_status:missing', 'Completeness', 'Critical', coalesce(("order_status" = ''),false)),
 ('order_status:unknown', 'Validity', 'Critical', coalesce((upper("order_status") NOT IN ('CANCELLED', 'DELIVERED', 'RETURNED')),false)),
 ('channel:missing', 'Completeness', 'Critical', coalesce(("channel" = ''),false)),
 ('delivery_minutes:invalid_number', 'Validity', 'Critical', coalesce(("delivery_minutes" <> '' AND (try_cast("delivery_minutes" AS DOUBLE) IS NULL OR NOT isfinite(try_cast("delivery_minutes" AS DOUBLE)))),false)),
 ('delivery_minutes:negative', 'Accuracy', 'Critical', coalesce((isfinite(try_cast("delivery_minutes" AS DOUBLE)) AND try_cast("delivery_minutes" AS DOUBLE) < 0),false)),
 ('delivery:impossible', 'Accuracy', 'Critical', coalesce((isfinite(try_cast("delivery_minutes" AS DOUBLE)) AND try_cast("delivery_minutes" AS DOUBLE) >= 120),false)),
 ('delivery:unusual', 'Accuracy', 'Warning', coalesce((isfinite(try_cast("delivery_minutes" AS DOUBLE)) AND try_cast("delivery_minutes" AS DOUBLE) NOT BETWEEN 8 AND 35),false)),
 ('delivery:missing', 'Completeness', 'Critical', coalesce((order_status='DELIVERED' AND delivery_minutes=''),false)),
 ('customer_id:invalid_reference', 'Consistency', 'Critical', coalesce((customer_id NOT IN (SELECT customer_id FROM stg_customers WHERE dq_status <> 'FAIL')),false)),
 ('product_id:invalid_reference', 'Consistency', 'Critical', coalesce((product_id NOT IN (SELECT product_id FROM stg_products WHERE dq_status <> 'FAIL')),false)),
 ('store_id:invalid_reference', 'Consistency', 'Critical', coalesce((store_id NOT IN (SELECT store_id FROM stg_stores WHERE dq_status <> 'FAIL')),false)),
 ('order_amount:formula', 'Accuracy', 'Critical', coalesce((round(try_cast(quantity AS DECIMAL(38,4)) * try_cast(unit_price AS DECIMAL(18,4)) * (100 - try_cast(discount_pct AS DECIMAL(9,4))) * 0.01, 2) <> try_cast(order_amount AS DECIMAL(18,4))),false))
) c(rule_name, dimension, severity, failed);
INSERT INTO dq_results
SELECT (SELECT run_id FROM run_context), (SELECT dag_id FROM run_context), 'orders.csv:' || rule_name,
 dimension, severity, count(*), count(*) FILTER(WHERE failed),
 CASE WHEN bool_or(failed) THEN 'FAIL' ELSE 'PASS' END, current_timestamp
FROM checks_orders GROUP BY rule_name, dimension, severity;
CREATE OR REPLACE TEMP TABLE evaluated_orders AS
SELECT v.*, q.failure_reason, q.warning_reason,
 CASE WHEN q.failure_reason <> '' THEN 'FAIL' WHEN q.warning_reason <> '' THEN 'WARN' ELSE 'PASS' END AS dq_status
FROM v_orders v JOIN (
 SELECT _batch_id, _row_number,
 coalesce(string_agg(rule_name, '; ' ORDER BY rule_name) FILTER(WHERE failed AND severity='Critical'),'') failure_reason,
 coalesce(string_agg(rule_name, '; ' ORDER BY rule_name) FILTER(WHERE failed AND severity='Warning'),'') warning_reason
 FROM checks_orders GROUP BY _batch_id, _row_number
) q USING(_batch_id,_row_number);
INSERT INTO quality_records
SELECT (SELECT run_id FROM run_context), _source_file, _run_id, _batch_id, _row_number,
 order_id, dq_status, failure_reason FROM evaluated_orders;
CREATE OR REPLACE TEMP TABLE candidate_orders AS
SELECT "order_id" AS "order_id",
 try_strptime("order_ts", '%Y-%m-%d %H:%M:%S') AS "order_ts",
 "customer_id" AS "customer_id",
 "store_id" AS "store_id",
 "product_id" AS "product_id",
 try_cast("quantity" AS DECIMAL(18,4)) AS "quantity",
 try_cast("unit_price" AS DECIMAL(18,4)) AS "unit_price",
 try_cast("discount_pct" AS DECIMAL(18,4)) AS "discount_pct",
 try_cast("order_amount" AS DECIMAL(18,4)) AS "order_amount",
 "payment_mode" AS "payment_mode",
 "order_status" AS "order_status",
 "channel" AS "channel",
 try_cast("delivery_minutes" AS DECIMAL(18,4)) AS "delivery_minutes", _loaded_at, _source_file, _run_id, _batch_id, _row_number,
 dq_status, failure_reason, warning_reason,
 md5(cast(row("order_id", "order_ts", "customer_id", "store_id", "product_id", "quantity", "unit_price", "discount_pct", "order_amount", "payment_mode", "order_status", "channel", "delivery_minutes") AS VARCHAR)) AS _payload_hash
FROM evaluated_orders
QUALIFY row_number() OVER(PARTITION BY order_id ORDER BY CASE WHEN _source_file='orders_2026-10-01_increment.csv' THEN 1 ELSE 0 END DESC, _batch_id DESC, exact_rank, _row_number)=1;
-- Real upsert. Latest correction wins even when it fails validation: never
-- silently fall back to the old DELIVERED value of a rejected RETURNED update.
CREATE TABLE IF NOT EXISTS stg_orders AS SELECT * FROM candidate_orders WHERE false;
INSERT OR REPLACE INTO incremental_results
SELECT (SELECT run_id FROM run_context),
 count(*) FILTER(WHERE old.order_id IS NULL),
 count(*) FILTER(WHERE old.order_id IS NOT NULL AND old._payload_hash <> new._payload_hash), current_timestamp
FROM candidate_orders new LEFT JOIN stg_orders old USING(order_id);
MERGE INTO stg_orders target USING candidate_orders source ON target.order_id=source.order_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
-- Current sources define the staging snapshot; history remains in raw.
DELETE FROM stg_orders WHERE order_id NOT IN (SELECT order_id FROM candidate_orders);
