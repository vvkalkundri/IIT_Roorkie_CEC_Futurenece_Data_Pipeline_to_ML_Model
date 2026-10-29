-- products: normalise only inside SQL; raw fields remain untouched.
CREATE OR REPLACE TEMP TABLE n_products AS
SELECT trim(r."product_id") AS "product_id",
 trim(r."product_name") AS "product_name",
 trim(r."category") AS "category",
 trim(r."sub_category") AS "sub_category",
 trim(r."brand") AS "brand",
 trim(r."mrp") AS "mrp",
 trim(r."cost_price") AS "cost_price",
 trim(r."unit") AS "unit",
 trim(r."is_perishable") AS "is_perishable",
 trim(r."launch_date") AS "launch_date", r."product_id" AS "_original_product_id", r."product_name" AS "_original_product_name", r."category" AS "_original_category", r."sub_category" AS "_original_sub_category", r."brand" AS "_original_brand", r."mrp" AS "_original_mrp", r."cost_price" AS "_original_cost_price", r."unit" AS "_original_unit", r."is_perishable" AS "_original_is_perishable", r."launch_date" AS "_original_launch_date", r._loaded_at, r._source_file, r._run_id, r._batch_id, r._row_number
FROM raw_products r JOIN latest_batches b ON r._batch_id=b.batch_id;
CREATE OR REPLACE TEMP TABLE v_products AS
SELECT *, row_number() OVER(PARTITION BY _batch_id, "product_id", "product_name", "category", "sub_category", "brand", "mrp", "cost_price", "unit", "is_perishable", "launch_date" ORDER BY _row_number) AS exact_rank,
 count(DISTINCT row("product_id", "product_name", "category", "sub_category", "brand", "mrp", "cost_price", "unit", "is_perishable", "launch_date")) OVER(PARTITION BY _batch_id, "product_id") AS key_versions
FROM n_products;
CREATE OR REPLACE TEMP TABLE checks_products AS
SELECT _batch_id, _row_number, rule_name, dimension, severity, failed
FROM v_products, LATERAL (VALUES
 ('product_id:whitespace', 'Consistency', 'Warning', coalesce(("_original_product_id" <> trim("_original_product_id")),false)),
 ('product_name:whitespace', 'Consistency', 'Warning', coalesce(("_original_product_name" <> trim("_original_product_name")),false)),
 ('category:whitespace', 'Consistency', 'Warning', coalesce(("_original_category" <> trim("_original_category")),false)),
 ('sub_category:whitespace', 'Consistency', 'Warning', coalesce(("_original_sub_category" <> trim("_original_sub_category")),false)),
 ('brand:whitespace', 'Consistency', 'Warning', coalesce(("_original_brand" <> trim("_original_brand")),false)),
 ('mrp:whitespace', 'Consistency', 'Warning', coalesce(("_original_mrp" <> trim("_original_mrp")),false)),
 ('cost_price:whitespace', 'Consistency', 'Warning', coalesce(("_original_cost_price" <> trim("_original_cost_price")),false)),
 ('unit:whitespace', 'Consistency', 'Warning', coalesce(("_original_unit" <> trim("_original_unit")),false)),
 ('is_perishable:whitespace', 'Consistency', 'Warning', coalesce(("_original_is_perishable" <> trim("_original_is_perishable")),false)),
 ('launch_date:whitespace', 'Consistency', 'Warning', coalesce(("_original_launch_date" <> trim("_original_launch_date")),false)),
 ('exact_duplicate', 'Uniqueness', 'Critical', coalesce((exact_rank > 1),false)),
 ('conflicting_key', 'Uniqueness', 'Critical', coalesce((key_versions > 1),false)),
 ('product_id:missing', 'Completeness', 'Critical', coalesce(("product_id" = ''),false)),
 ('product_name:missing', 'Completeness', 'Critical', coalesce(("product_name" = ''),false)),
 ('category:missing', 'Completeness', 'Critical', coalesce(("category" = ''),false)),
 ('sub_category:missing', 'Completeness', 'Critical', coalesce(("sub_category" = ''),false)),
 ('brand:missing', 'Completeness', 'Critical', coalesce(("brand" = ''),false)),
 ('mrp:missing', 'Completeness', 'Critical', coalesce(("mrp" = ''),false)),
 ('mrp:invalid_number', 'Validity', 'Critical', coalesce(("mrp" <> '' AND (try_cast("mrp" AS DOUBLE) IS NULL OR NOT isfinite(try_cast("mrp" AS DOUBLE)))),false)),
 ('mrp:nonpositive', 'Accuracy', 'Critical', coalesce((isfinite(try_cast("mrp" AS DOUBLE)) AND try_cast("mrp" AS DOUBLE) <= 0),false)),
 ('cost_price:missing', 'Completeness', 'Critical', coalesce(("cost_price" = ''),false)),
 ('cost_price:invalid_number', 'Validity', 'Critical', coalesce(("cost_price" <> '' AND (try_cast("cost_price" AS DOUBLE) IS NULL OR NOT isfinite(try_cast("cost_price" AS DOUBLE)))),false)),
 ('cost_price:negative', 'Accuracy', 'Critical', coalesce((isfinite(try_cast("cost_price" AS DOUBLE)) AND try_cast("cost_price" AS DOUBLE) < 0),false)),
 ('unit:missing', 'Completeness', 'Critical', coalesce(("unit" = ''),false)),
 ('is_perishable:missing', 'Completeness', 'Critical', coalesce(("is_perishable" = ''),false)),
 ('launch_date:missing', 'Completeness', 'Critical', coalesce(("launch_date" = ''),false)),
 ('launch_date:invalid_date', 'Validity', 'Critical', coalesce(("launch_date" <> '' AND try_strptime("launch_date", '%Y-%m-%d') IS NULL),false)),
 ('launch_date:future', 'Timeliness', 'Critical', coalesce((cast(try_strptime("launch_date", '%Y-%m-%d') AS DATE) > (SELECT as_of FROM run_context)),false)),
 ('cost:above_mrp', 'Accuracy', 'Critical', coalesce((try_cast(cost_price AS DOUBLE) > try_cast(mrp AS DOUBLE)),false))
) c(rule_name, dimension, severity, failed);
INSERT INTO dq_results
SELECT (SELECT run_id FROM run_context), (SELECT dag_id FROM run_context), 'products.csv:' || rule_name,
 dimension, severity, count(*), count(*) FILTER(WHERE failed),
 CASE WHEN bool_or(failed) THEN 'FAIL' ELSE 'PASS' END, current_timestamp
FROM checks_products GROUP BY rule_name, dimension, severity;
CREATE OR REPLACE TEMP TABLE evaluated_products AS
SELECT v.*, q.failure_reason, q.warning_reason,
 CASE WHEN q.failure_reason <> '' THEN 'FAIL' WHEN q.warning_reason <> '' THEN 'WARN' ELSE 'PASS' END AS dq_status
FROM v_products v JOIN (
 SELECT _batch_id, _row_number,
 coalesce(string_agg(rule_name, '; ' ORDER BY rule_name) FILTER(WHERE failed AND severity='Critical'),'') failure_reason,
 coalesce(string_agg(rule_name, '; ' ORDER BY rule_name) FILTER(WHERE failed AND severity='Warning'),'') warning_reason
 FROM checks_products GROUP BY _batch_id, _row_number
) q USING(_batch_id,_row_number);
INSERT INTO quality_records
SELECT (SELECT run_id FROM run_context), _source_file, _run_id, _batch_id, _row_number,
 product_id, dq_status, failure_reason FROM evaluated_products;
CREATE OR REPLACE TEMP TABLE candidate_products AS
SELECT "product_id" AS "product_id",
 "product_name" AS "product_name",
 "category" AS "category",
 "sub_category" AS "sub_category",
 "brand" AS "brand",
 try_cast("mrp" AS DECIMAL(18,4)) AS "mrp",
 try_cast("cost_price" AS DECIMAL(18,4)) AS "cost_price",
 "unit" AS "unit",
 "is_perishable" AS "is_perishable",
 try_strptime("launch_date", '%Y-%m-%d') AS "launch_date", _loaded_at, _source_file, _run_id, _batch_id, _row_number,
 dq_status, failure_reason, warning_reason,
 md5(cast(row("product_id", "product_name", "category", "sub_category", "brand", "mrp", "cost_price", "unit", "is_perishable", "launch_date") AS VARCHAR)) AS _payload_hash
FROM evaluated_products
QUALIFY row_number() OVER(PARTITION BY product_id ORDER BY  _batch_id DESC, exact_rank, _row_number)=1;
CREATE OR REPLACE TABLE stg_products AS SELECT * FROM candidate_products;
