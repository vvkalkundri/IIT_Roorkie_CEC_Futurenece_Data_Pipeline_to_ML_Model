-- customers: normalise only inside SQL; raw fields remain untouched.
CREATE OR REPLACE TEMP TABLE n_customers AS
SELECT trim(r."customer_id") AS "customer_id",
 trim(r."full_name") AS "full_name",
 trim(r."email") AS "email",
 trim(r."phone") AS "phone",
 trim(r."city") AS "city",
 trim(r."area") AS "area",
 trim(r."pincode") AS "pincode",
 trim(r."signup_date") AS "signup_date",
 upper(trim(r."loyalty_tier")) AS "loyalty_tier",
 trim(r."is_active") AS "is_active", r."customer_id" AS "_original_customer_id", r."full_name" AS "_original_full_name", r."email" AS "_original_email", r."phone" AS "_original_phone", r."city" AS "_original_city", r."area" AS "_original_area", r."pincode" AS "_original_pincode", r."signup_date" AS "_original_signup_date", r."loyalty_tier" AS "_original_loyalty_tier", r."is_active" AS "_original_is_active", r._loaded_at, r._source_file, r._run_id, r._batch_id, r._row_number
FROM raw_customers r JOIN latest_batches b ON r._batch_id=b.batch_id;
CREATE OR REPLACE TEMP TABLE v_customers AS
SELECT *, row_number() OVER(PARTITION BY _batch_id, "customer_id", "full_name", "email", "phone", "city", "area", "pincode", "signup_date", "loyalty_tier", "is_active" ORDER BY _row_number) AS exact_rank,
 count(DISTINCT row("customer_id", "full_name", "email", "phone", "city", "area", "pincode", "signup_date", "loyalty_tier", "is_active")) OVER(PARTITION BY _batch_id, "customer_id") AS key_versions
FROM n_customers;
CREATE OR REPLACE TEMP TABLE checks_customers AS
SELECT _batch_id, _row_number, rule_name, dimension, severity, failed
FROM v_customers, LATERAL (VALUES
 ('customer_id:whitespace', 'Consistency', 'Warning', coalesce(("_original_customer_id" <> trim("_original_customer_id")),false)),
 ('full_name:whitespace', 'Consistency', 'Warning', coalesce(("_original_full_name" <> trim("_original_full_name")),false)),
 ('email:whitespace', 'Consistency', 'Warning', coalesce(("_original_email" <> trim("_original_email")),false)),
 ('phone:whitespace', 'Consistency', 'Warning', coalesce(("_original_phone" <> trim("_original_phone")),false)),
 ('city:whitespace', 'Consistency', 'Warning', coalesce(("_original_city" <> trim("_original_city")),false)),
 ('area:whitespace', 'Consistency', 'Warning', coalesce(("_original_area" <> trim("_original_area")),false)),
 ('pincode:whitespace', 'Consistency', 'Warning', coalesce(("_original_pincode" <> trim("_original_pincode")),false)),
 ('signup_date:whitespace', 'Consistency', 'Warning', coalesce(("_original_signup_date" <> trim("_original_signup_date")),false)),
 ('loyalty_tier:whitespace', 'Consistency', 'Warning', coalesce(("_original_loyalty_tier" <> trim("_original_loyalty_tier")),false)),
 ('loyalty_tier:casing', 'Consistency', 'Warning', coalesce((trim("_original_loyalty_tier") <> upper(trim("_original_loyalty_tier"))),false)),
 ('is_active:whitespace', 'Consistency', 'Warning', coalesce(("_original_is_active" <> trim("_original_is_active")),false)),
 ('exact_duplicate', 'Uniqueness', 'Critical', coalesce((exact_rank > 1),false)),
 ('conflicting_key', 'Uniqueness', 'Critical', coalesce((key_versions > 1),false)),
 ('customer_id:missing', 'Completeness', 'Critical', coalesce(("customer_id" = ''),false)),
 ('full_name:missing', 'Completeness', 'Warning', coalesce(("full_name" = ''),false)),
 ('email:missing', 'Completeness', 'Warning', coalesce(("email" = ''),false)),
 ('email:format', 'Validity', 'Warning', coalesce(("email" <> '' AND NOT regexp_full_match("email", '[^\s@]+@[^\s@]+\.[^\s@]+')),false)),
 ('phone:missing', 'Completeness', 'Warning', coalesce(("phone" = ''),false)),
 ('phone:format', 'Validity', 'Warning', coalesce(("phone" <> '' AND NOT regexp_full_match("phone", '[0-9]{10}')),false)),
 ('city:missing', 'Completeness', 'Warning', coalesce(("city" = ''),false)),
 ('area:missing', 'Completeness', 'Warning', coalesce(("area" = ''),false)),
 ('pincode:missing', 'Completeness', 'Warning', coalesce(("pincode" = ''),false)),
 ('pincode:format', 'Validity', 'Warning', coalesce(("pincode" <> '' AND NOT regexp_full_match("pincode", '[0-9]{6}')),false)),
 ('signup_date:missing', 'Completeness', 'Critical', coalesce(("signup_date" = ''),false)),
 ('signup_date:invalid_date', 'Validity', 'Critical', coalesce(("signup_date" <> '' AND try_strptime("signup_date", '%Y-%m-%d') IS NULL),false)),
 ('signup_date:future', 'Timeliness', 'Critical', coalesce((cast(try_strptime("signup_date", '%Y-%m-%d') AS DATE) > (SELECT as_of FROM run_context)),false)),
 ('loyalty_tier:missing', 'Completeness', 'Critical', coalesce(("loyalty_tier" = ''),false)),
 ('is_active:missing', 'Completeness', 'Critical', coalesce(("is_active" = ''),false))
) c(rule_name, dimension, severity, failed);
INSERT INTO dq_results
SELECT (SELECT run_id FROM run_context), (SELECT dag_id FROM run_context), 'customers.csv:' || rule_name,
 dimension, severity, count(*), count(*) FILTER(WHERE failed),
 CASE WHEN bool_or(failed) THEN 'FAIL' ELSE 'PASS' END, current_timestamp
FROM checks_customers GROUP BY rule_name, dimension, severity;
CREATE OR REPLACE TEMP TABLE evaluated_customers AS
SELECT v.*, q.failure_reason, q.warning_reason,
 CASE WHEN q.failure_reason <> '' THEN 'FAIL' WHEN q.warning_reason <> '' THEN 'WARN' ELSE 'PASS' END AS dq_status
FROM v_customers v JOIN (
 SELECT _batch_id, _row_number,
 coalesce(string_agg(rule_name, '; ' ORDER BY rule_name) FILTER(WHERE failed AND severity='Critical'),'') failure_reason,
 coalesce(string_agg(rule_name, '; ' ORDER BY rule_name) FILTER(WHERE failed AND severity='Warning'),'') warning_reason
 FROM checks_customers GROUP BY _batch_id, _row_number
) q USING(_batch_id,_row_number);
INSERT INTO quality_records
SELECT (SELECT run_id FROM run_context), _source_file, _run_id, _batch_id, _row_number,
 customer_id, dq_status, failure_reason FROM evaluated_customers;
CREATE OR REPLACE TEMP TABLE candidate_customers AS
SELECT "customer_id" AS "customer_id",
 '[REDACTED]' AS "full_name",
 '[REDACTED]' AS "email",
 '[REDACTED]' AS "phone",
 "city" AS "city",
 "area" AS "area",
 "pincode" AS "pincode",
 try_strptime("signup_date", '%Y-%m-%d') AS "signup_date",
 "loyalty_tier" AS "loyalty_tier",
 "is_active" AS "is_active", _loaded_at, _source_file, _run_id, _batch_id, _row_number,
 dq_status, failure_reason, warning_reason,
 md5(cast(row("customer_id", "full_name", "email", "phone", "city", "area", "pincode", "signup_date", "loyalty_tier", "is_active") AS VARCHAR)) AS _payload_hash
FROM evaluated_customers
QUALIFY row_number() OVER(PARTITION BY customer_id ORDER BY  _batch_id DESC, exact_rank, _row_number)=1;
CREATE OR REPLACE TABLE stg_customers AS SELECT * FROM candidate_customers;
