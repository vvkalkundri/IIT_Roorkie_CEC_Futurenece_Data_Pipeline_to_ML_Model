-- Raw batches never get deleted. Run/source uniqueness makes task retries safe.
CREATE SEQUENCE IF NOT EXISTS ingestion_sequence;
CREATE TABLE IF NOT EXISTS ingestion_batches (
 batch_id BIGINT PRIMARY KEY, run_id VARCHAR, source_file VARCHAR, sha256 VARCHAR,
 row_count BIGINT, loaded_at TIMESTAMPTZ, UNIQUE(run_id, source_file));
CREATE TABLE IF NOT EXISTS pipeline_runs (
 run_id VARCHAR, dag_id VARCHAR, start_time TIMESTAMPTZ, end_time TIMESTAMPTZ,
 rows_extracted BIGINT, rows_loaded BIGINT, rows_quarantined BIGINT, status VARCHAR,
 PRIMARY KEY(run_id, dag_id));
CREATE TABLE IF NOT EXISTS incremental_results (
 run_id VARCHAR PRIMARY KEY, inserted_orders BIGINT, changed_orders BIGINT, checked_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS dq_results (
 run_id VARCHAR, dag_id VARCHAR, check_name VARCHAR, dimension VARCHAR, severity VARCHAR,
 rows_checked BIGINT, rows_failed BIGINT, status VARCHAR, checked_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS quality_records (
 evaluated_run_id VARCHAR, source_file VARCHAR, source_run_id VARCHAR,
 batch_id BIGINT, row_number BIGINT, row_key VARCHAR, dq_status VARCHAR, failure_reason VARCHAR);
