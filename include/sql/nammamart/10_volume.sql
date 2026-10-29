-- File-level check: compare source batches, not the ever-growing raw tables.
WITH previous AS (
 SELECT b.*, row_number() OVER(PARTITION BY b.source_file ORDER BY b.batch_id DESC) rn
 FROM ingestion_batches b WHERE b.run_id <> (SELECT run_id FROM run_context)
), current AS (
 SELECT * FROM ingestion_batches WHERE run_id=(SELECT run_id FROM run_context)
)
INSERT INTO dq_results
SELECT (SELECT run_id FROM run_context),(SELECT dag_id FROM run_context),
 c.source_file || ':volume:drop_over_90pct','Completeness','Warning',1,
 CASE WHEN p.row_count>0 AND c.row_count < .1*p.row_count THEN 1 ELSE 0 END,
 CASE WHEN p.row_count>0 AND c.row_count < .1*p.row_count THEN 'FAIL' ELSE 'PASS' END,current_timestamp
FROM current c LEFT JOIN previous p ON c.source_file=p.source_file AND p.rn=1;
