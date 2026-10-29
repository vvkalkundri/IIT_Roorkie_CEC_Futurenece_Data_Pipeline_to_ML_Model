-- Match the current ETL's strict initial finance policy. Payment quality and
-- order quality are evaluated before reconciliation, without circular joins.
CREATE OR REPLACE TEMP TABLE approved_orders AS
SELECT * FROM stg_orders WHERE dq_status <> 'FAIL';
CREATE OR REPLACE TEMP TABLE successful_payments AS
SELECT * FROM stg_payments WHERE dq_status <> 'FAIL' AND payment_status='SUCCESS';
CREATE OR REPLACE TEMP TABLE payment_holds AS
SELECT o.order_id, o._batch_id, o._row_number, o.order_amount,
 coalesce(string_agg(p.payment_id, ',' ORDER BY p.payment_id),'') payment_id,
 coalesce(sum(p.amount_paid),0) amount_paid,
 CASE WHEN o.order_status='DELIVERED' AND count(p.payment_id) <> 1
      THEN 'Delivered order requires exactly one accepted successful payment'
      WHEN bool_or(p.amount_paid <> o.order_amount)
      THEN 'Successful payment amount differs from order amount'
      ELSE '' END reason
FROM approved_orders o LEFT JOIN successful_payments p USING(order_id)
GROUP BY o.order_id, o._batch_id, o._row_number, o.order_amount, o.order_status
HAVING reason <> '';

CREATE OR REPLACE TABLE stg_payment_reconciliation AS
SELECT order_id, payment_id, reason, order_amount, amount_paid,
 amount_paid - order_amount AS amount_difference, _batch_id, _row_number
FROM payment_holds
UNION ALL
SELECT e.order_id, e.payment_id, e.failure_reason,
 NULL::DECIMAL(18,4), NULL::DECIMAL(18,4), NULL::DECIMAL(18,4), e._batch_id, e._row_number
FROM evaluated_payments e WHERE e.dq_status='FAIL'
UNION ALL
SELECT p.order_id, p.payment_id, 'Payment has no quality-approved order',
 NULL::DECIMAL(18,4), p.amount_paid, NULL::DECIMAL(18,4), p._batch_id, p._row_number
FROM successful_payments p WHERE p.order_id NOT IN (SELECT order_id FROM approved_orders);

INSERT INTO dq_results
SELECT (SELECT run_id FROM run_context), (SELECT dag_id FROM run_context),
 'orders.csv:payment:unreconciled', 'Consistency', 'Critical',
 (SELECT count(*) FROM evaluated_orders), count(*),
 CASE WHEN count(*)>0 THEN 'FAIL' ELSE 'PASS' END, current_timestamp
FROM payment_holds;

UPDATE stg_orders SET dq_status='FAIL',
 failure_reason=concat_ws('; ', nullif(stg_orders.failure_reason,''), 'payment:unreconciled')
FROM payment_holds h WHERE stg_orders.order_id=h.order_id;
UPDATE quality_records SET dq_status='FAIL',
 failure_reason=concat_ws('; ', nullif(quality_records.failure_reason,''), 'payment:unreconciled')
FROM payment_holds h
WHERE quality_records.evaluated_run_id=(SELECT run_id FROM run_context)
 AND quality_records.batch_id=h._batch_id AND quality_records.row_number=h._row_number;

-- Lineage metadata only: exact received values can be retrieved from raw using
-- batch_id and row_number, under the raw-layer access policy.
CREATE OR REPLACE TABLE elt_quarantine AS
SELECT * FROM quality_records
WHERE evaluated_run_id=(SELECT run_id FROM run_context) AND dq_status='FAIL';
