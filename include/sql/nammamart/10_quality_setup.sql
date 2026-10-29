-- Keep quality history per evaluation; replace only the same run on retry.
DELETE FROM dq_results WHERE run_id = (SELECT run_id FROM run_context);
DELETE FROM quality_records WHERE evaluated_run_id = (SELECT run_id FROM run_context);
CREATE OR REPLACE TEMP VIEW latest_batches AS
SELECT source_file, max(batch_id) batch_id FROM ingestion_batches GROUP BY source_file;
