-- ELT warehouse: warehouse_elt_vijayc5.duckdb
-- Selected run: scheduled__2026-10-29T03:30:00+00:00
-- Revenue period: September 2026. Q4b is full current snapshot.

-- Q1 — Daily net revenue by zone and store
SELECT order_date, zone,
 CASE WHEN grouping(store_id)=1 THEN 'ZONE TOTAL' ELSE 'STORE' END AS level,
 store_id, round(sum(net_revenue),2) AS net_revenue
FROM mart_fact_orders
WHERE order_status='DELIVERED' AND order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'
GROUP BY GROUPING SETS ((order_date,zone),(order_date,zone,store_id))
ORDER BY order_date,zone,level,store_id;

-- Q2 — Revenue and gross margin by category
SELECT category, round(sum(net_revenue),2) AS net_revenue,
 round(sum(gross_margin),2) AS gross_margin
FROM mart_fact_orders WHERE order_status='DELIVERED' AND order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'
GROUP BY category ORDER BY category;

-- Q3 — Delivery time and percentage within 15 minutes
SELECT store_id, count(*) AS delivered_orders,
 round(avg(delivery_minutes),2) AS avg_delivery_minutes,
 round(100.0*count(*) FILTER(WHERE within_15_min)/nullif(count(*),0),2) AS pct_within_15_min
FROM mart_fact_orders WHERE order_status='DELIVERED' AND order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'
GROUP BY store_id ORDER BY store_id;

-- Q4a — Revenue by payment mode
SELECT payment_mode,round(sum(net_revenue),2) AS net_revenue
FROM mart_fact_orders WHERE order_status='DELIVERED' AND order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'
GROUP BY payment_mode ORDER BY payment_mode;

-- Q4b — Reconciliation amounts and unresolved exceptions
SELECT count(*) AS exception_rows,
 count(*) FILTER(WHERE order_amount IS NOT NULL AND amount_paid IS NOT NULL) AS quantifiable_rows,
 count(*) FILTER(WHERE order_amount IS NULL OR amount_paid IS NULL) AS unknown_amount_rows,
 round(sum(abs(amount_paid-order_amount)),2) AS known_absolute_difference,
 round(sum(amount_paid-order_amount),2) AS known_signed_difference
FROM mart_payment_reconciliation;

-- Q5 — Top ten customers by delivered-order spend
SELECT customer_id,loyalty_tier,round(sum(net_revenue),2) AS total_spend
FROM mart_fact_orders WHERE order_status='DELIVERED' AND order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'
GROUP BY customer_id,loyalty_tier
ORDER BY total_spend DESC,customer_id LIMIT 10;

-- Q6 — Rejected rows by file and reason for the selected run
WITH rejected AS (
SELECT source_file, failure_reason FROM quality_records WHERE evaluated_run_id='scheduled__2026-10-29T03:30:00+00:00' AND dq_status='FAIL'
), result AS (
 SELECT source_file,'FILE TOTAL (unique records)' AS reason,count(*) AS rejected_records
 FROM rejected GROUP BY source_file
 UNION ALL
 SELECT source_file,trim(reason) AS reason,count(*) AS rejected_records
 FROM rejected,unnest(string_split(failure_reason,';')) AS reasons(reason)
 WHERE trim(reason)<>'' GROUP BY source_file,trim(reason)
)
SELECT 'scheduled__2026-10-29T03:30:00+00:00' AS run_id,* FROM result ORDER BY source_file,reason;

