"""ELT orchestration only: raw ingestion and execution of checked-in SQL files.

All cleaning, quality checks, deduplication, upserts and marts run in DuckDB SQL.
The separate warehouse avoids concurrent writers with the existing ETL DAG.
"""
import csv
import hashlib
from datetime import date
from pathlib import Path

import duckdb

from include.profile_nammamart import SCHEMAS

DAG_ID = 'nammamart_elt_vijayc5'
BASE_FILES = [name for name in SCHEMAS if 'increment' not in name]
INCREMENT = 'orders_2026-10-01_increment.csv'


def connect(root):
    return duckdb.connect(str(Path(root) / 'include/warehouse_elt_vijayc5.duckdb'))


def sql_file(db, root, name):
    db.execute((Path(root) / 'include/sql/nammamart' / name).read_text())


def context(db, run_id, as_of, dag_id=DAG_ID):
    reference = date.fromisoformat(as_of)
    db.execute('CREATE OR REPLACE TEMP TABLE run_context AS SELECT ?::VARCHAR run_id, ?::DATE as_of, ?::VARCHAR dag_id', [run_id, reference, dag_id])


def load_raw(root, run_id, include_increment=False):
    """Append source strings without cleaning; retries reuse this run's batch.

    A new run appends another auditable copy. Same-run retries neither append
    again nor accept a silently changed source. A transaction covers all files.
    """
    if type(include_increment) is not bool:
        raise ValueError('include_increment must be a JSON boolean, not a string')
    names = BASE_FILES + ([INCREMENT] if include_increment else [])
    # Validate/read every file before committing any rows for this run.
    sources = []
    for name in names:
        path = Path(root) / 'include/data/nammamart' / name
        source_bytes = path.read_bytes()
        from io import StringIO
        rows = list(csv.reader(StringIO(source_bytes.decode('utf-8-sig'), newline='')))
        if not rows or rows[0] != SCHEMAS[name]:
            raise ValueError(f'{name}: unexpected CSV schema')
        if any(len(row) != len(rows[0]) for row in rows[1:]):
            raise ValueError(f'{name}: wrong CSV field count')
        sources.append((name, rows[1:], hashlib.sha256(source_bytes).hexdigest()))
    with connect(root) as db:
        sql_file(db, root, '00_metadata.sql')
        db.execute('BEGIN')
        try:
            old_files = {row[0] for row in db.execute('SELECT source_file FROM ingestion_batches WHERE run_id=?', [run_id]).fetchall()}
            if old_files and old_files != set(names):
                raise ValueError('Retry changed input selection; use a new run ID')
            counts = {}
            for name, rows, digest in sources:
                table = 'orders' if name == INCREMENT else Path(name).stem
                columns = SCHEMAS[name]
                schema = ', '.join(f'"{column}" VARCHAR' for column in columns)
                db.execute(f'CREATE TABLE IF NOT EXISTS raw_{table} ({schema}, _loaded_at TIMESTAMPTZ, _source_file VARCHAR, _run_id VARCHAR, _batch_id BIGINT, _row_number BIGINT)')
                previous = db.execute('SELECT sha256, row_count FROM ingestion_batches WHERE run_id=? AND source_file=?', [run_id, name]).fetchone()
                if previous:
                    if previous[0] != digest:
                        raise ValueError(f'{name}: source changed during retry; start a new run')
                    counts[name] = previous[1]
                    continue
                batch_id = db.execute("SELECT nextval('ingestion_sequence')").fetchone()[0]
                values = ','.join('?' for _ in columns)
                if rows:
                    db.executemany(f'INSERT INTO raw_{table} VALUES ({values}, current_timestamp, ?, ?, ?, ?)',
                                   [row + [name, run_id, batch_id, index] for index, row in enumerate(rows, 1)])
                db.execute('INSERT INTO ingestion_batches VALUES (?, ?, ?, ?, ?, current_timestamp)',
                           [batch_id, run_id, name, digest, len(rows)])
                counts[name] = len(rows)
            db.execute('COMMIT')
        except Exception:
            db.execute('ROLLBACK')
            raise
    print(f'Raw rows received: {counts}')
    return counts


def build_staging(root, run_id, as_of, dag_id=DAG_ID):
    with connect(root) as db:
        context(db, run_id, as_of, dag_id)
        db.execute('BEGIN')
        try:
            for name in ['10_quality_setup.sql', '10_volume.sql', '11_customers.sql', '12_products.sql',
                         '13_stores.sql', '14_orders.sql', '15_payments.sql', '16_reconciliation.sql']:
                sql_file(db, root, name)
            db.execute('COMMIT')
        except Exception:
            db.execute('ROLLBACK')
            raise
        result = db.execute('SELECT inserted_orders, changed_orders FROM incremental_results WHERE run_id=?', [run_id]).fetchone()
    print(f'Order staging: inserted={result[0]}, changed={result[1]}')
    return {'inserted': result[0], 'changed': result[1]}


def build_marts(root, run_id, as_of):
    with connect(root) as db:
        context(db, run_id, as_of)
        db.execute('BEGIN')
        try:
            sql_file(db, root, '20_marts.sql')
            db.execute('COMMIT')
        except Exception:
            db.execute('ROLLBACK')
            raise
        rows, revenue = db.execute('SELECT count(*), round(coalesce(sum(net_revenue),0),2) FROM mart_fact_orders').fetchone()
    print(f'Mart: {rows} approved orders; net revenue {revenue}')
    return True


def audit(root, run_id, started_at, success, dag_id=DAG_ID):
    with connect(root) as db:
        sql_file(db, root, '00_metadata.sql')
        extracted = db.execute('SELECT coalesce(sum(row_count),0) FROM ingestion_batches WHERE run_id=?', [run_id]).fetchone()[0]
        tables = {row[0] for row in db.execute('SHOW TABLES').fetchall()}
        loaded = db.execute('SELECT count(*) FROM mart_fact_orders').fetchone()[0] if success else 0
        rejected = 0
        if 'quality_records' in tables:
            rejected = db.execute("SELECT count(*) FROM quality_records WHERE evaluated_run_id=? AND dq_status='FAIL'", [run_id]).fetchone()[0]
        db.execute('INSERT OR REPLACE INTO pipeline_runs VALUES (?, ?, ?::TIMESTAMPTZ, current_timestamp, ?, ?, ?, ?)',
                   [run_id, dag_id, str(started_at), extracted, loaded, rejected, 'SUCCESS' if success else 'FAILED'])


def compare_etl(root):
    """Read-only comparison; no writes or ATTACH to the ETL warehouse."""
    etl_path = Path(root) / 'include/warehouse_vijayc5.duckdb'
    if not etl_path.exists():
        return {'status': 'NOT_CHECKED', 'reason': 'ETL warehouse does not exist'}
    query = "SELECT count(*), round(coalesce(sum(net_revenue),0),2), round(coalesce(sum(gross_margin),0),2) FROM {} WHERE order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'"
    with duckdb.connect(str(etl_path), read_only=True) as db:
        etl = db.execute(query.format('etl_fact_orders')).fetchone()
    with connect(root) as db:
        elt = db.execute(query.format('mart_fact_orders')).fetchone()
        increment = db.execute('SELECT count(*) FROM ingestion_batches WHERE source_file=?', [INCREMENT]).fetchone()[0] > 0
    same = etl[0] == elt[0] and all(abs(float(a) - float(b)) < .005 for a, b in zip(etl[1:], elt[1:]))
    return {'status': 'MATCH' if same else 'DIFFERENT', 'etl': list(map(str, etl)),
            'elt': list(map(str, elt)), 'increment_present': increment,
            'note': 'Compare equal inputs/reference dates. Incremental returns can restate September; apply the same increments to both pipelines before comparing.'}
