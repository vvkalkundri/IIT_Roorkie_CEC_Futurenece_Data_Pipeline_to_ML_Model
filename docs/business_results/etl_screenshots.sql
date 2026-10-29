-- Run each SELECT separately and capture SQL plus its result grid.
-- Database: warehouse_vijayc5.duckdb; run: scheduled__2026-10-29T03:30:00+00:00
SELECT run_id,dag_id,cast(start_time AS VARCHAR) AS start_time,
 cast(end_time AS VARCHAR) AS end_time,rows_extracted,rows_loaded,rows_quarantined,status
FROM pipeline_runs WHERE run_id='scheduled__2026-10-29T03:30:00+00:00';

SELECT run_id,dimension,severity,count(*) AS checks,
 sum(rows_checked) AS check_evaluations,sum(rows_failed) AS failed_check_evaluations
FROM dq_results WHERE run_id='scheduled__2026-10-29T03:30:00+00:00'
GROUP BY run_id,dimension,severity ORDER BY dimension,severity;

SELECT check_name,dimension,severity,rows_checked,rows_failed,status
FROM dq_results WHERE run_id='scheduled__2026-10-29T03:30:00+00:00' AND rows_failed>0
ORDER BY dimension,check_name;

SELECT order_id,payment_id,reason,order_amount,amount_paid,
 round(amount_paid-order_amount,2) AS amount_difference
FROM etl_payment_reconciliation ORDER BY reason,order_id,payment_id LIMIT 20;

-- Privacy-limited quarantine view; originals remain private.
SELECT order_id,quantity,failure_reason FROM read_csv('/Users/user/Documents/personal/iitfde/pipeline/IIT_Roorkie_CEC_Futurenece_Data_Pipeline_to_ML_Model/include/quarantine/vijayc5/orders_failed_f6f01b0cccd2e65abc61.csv',header=true,all_varchar=true) WHERE order_id='ORD000099';
