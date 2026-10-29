-- Published together in a single transaction. Raw/staging PII never enters marts.
CREATE OR REPLACE TABLE mart_payment_reconciliation AS
SELECT * FROM stg_payment_reconciliation;

CREATE OR REPLACE TABLE mart_fact_orders AS
SELECT o.*, cast(o.order_ts AS DATE) order_date, c.loyalty_tier,
 p.category, p.cost_price, s.zone,
 CASE WHEN o.order_status='DELIVERED' THEN o.order_amount ELSE 0 END net_revenue,
 CASE WHEN o.order_status='DELIVERED'
      THEN round(o.order_amount - o.quantity*p.cost_price,2) ELSE 0 END gross_margin,
 (o.order_status='DELIVERED' AND o.delivery_minutes<=15) within_15_min
FROM stg_orders o
JOIN stg_customers c USING(customer_id)
JOIN stg_products p USING(product_id)
JOIN stg_stores s USING(store_id)
WHERE o.dq_status <> 'FAIL' AND c.dq_status <> 'FAIL'
 AND p.dq_status <> 'FAIL' AND s.dq_status <> 'FAIL';

CREATE OR REPLACE TABLE mart_daily_store_kpis AS
SELECT order_date, store_id, zone, count(*) order_count,
 count(*) FILTER(WHERE order_status='DELIVERED') delivered_orders,
 round(sum(net_revenue),2) net_revenue, round(sum(gross_margin),2) gross_margin,
 avg(delivery_minutes) FILTER(WHERE order_status='DELIVERED') avg_delivery_minutes,
 100.0 * count(*) FILTER(WHERE within_15_min) /
 nullif(count(*) FILTER(WHERE order_status='DELIVERED'),0) pct_within_15_min
FROM mart_fact_orders GROUP BY order_date, store_id, zone;

CREATE OR REPLACE TABLE mart_category_margin AS
SELECT category, round(sum(net_revenue),2) net_revenue,
 round(sum(gross_margin),2) gross_margin FROM mart_fact_orders GROUP BY category;

CREATE OR REPLACE TABLE mart_delivery_sla AS
SELECT store_id, count(*) delivered_orders, avg(delivery_minutes) avg_delivery_minutes,
 100.0 * count(*) FILTER(WHERE within_15_min) / nullif(count(*),0) pct_within_15_min
FROM mart_fact_orders WHERE order_status='DELIVERED' GROUP BY store_id;

CREATE OR REPLACE TABLE mart_top_customers AS
SELECT customer_id, loyalty_tier, round(sum(net_revenue),2) total_spend
FROM mart_fact_orders WHERE order_status='DELIVERED'
GROUP BY customer_id, loyalty_tier ORDER BY total_spend DESC, customer_id LIMIT 10;

CREATE OR REPLACE TABLE mart_payment_mode_revenue AS
SELECT payment_mode, round(sum(net_revenue),2) net_revenue
FROM mart_fact_orders GROUP BY payment_mode;

-- Per-run rejection reasons; one record can contribute to several reasons.
CREATE OR REPLACE TABLE mart_rejections AS
SELECT evaluated_run_id, source_file, reason, count(*) rejected_records
FROM elt_quarantine, unnest(string_split(failure_reason,'; ')) reasons(reason)
GROUP BY evaluated_run_id, source_file, reason;

CREATE OR REPLACE TABLE mart_publication AS
SELECT (SELECT run_id FROM run_context) run_id, current_timestamp published_at,
 (SELECT as_of FROM run_context) reference_date;
