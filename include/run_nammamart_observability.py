"""Run all ten experiments on unscheduled aliases of the production DAGs.

Run INSIDE the project's Airflow scheduler container, from /usr/local/airflow:
    python include/run_nammamart_observability.py --suite obs_20261026_01
Uses Airflow's CLI for trigger/clear and read-only ORM queries for evidence.
Only prepared private workspaces are mutated; original inputs stay unchanged.
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AS_OF = '2026-10-25'
KINDS = ('etl', 'elt')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str))


def cli(args, log):
    result = subprocess.run(['airflow', *args], capture_output=True, text=True, timeout=90)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'Airflow CLI failed: {args[:3]}; inspect {log}')


def snapshot(kind, run_id):
    from airflow.models.dagrun import DagRun
    from airflow.models.taskinstance import TaskInstance
    from airflow.utils.session import create_session
    value = lambda x: getattr(x, 'value', x)
    dag_id = f'nammamart_{kind}_observability_vijayc5'
    with create_session() as session:
        run = session.query(DagRun).filter_by(dag_id=dag_id, run_id=run_id).one_or_none()
        if run is None:
            return {'state': 'not_created', 'tasks': []}
        tasks = session.query(TaskInstance).filter_by(dag_id=dag_id, run_id=run_id).all()
        return {'state': value(run.state), 'logical_date': str(run.logical_date), 'tasks': [
            {'task_id': t.task_id, 'state': value(t.state), 'try_number': t.try_number,
             'start': str(t.start_date) if t.start_date else None, 'end': str(t.end_date) if t.end_date else None,
             'duration': t.duration} for t in tasks]}


def await_runs(runs, evidence, force_transition=False):
    deadline = time.monotonic() + 600
    last = {}
    seen_active = {kind: not force_transition for kind in runs}
    while time.monotonic() < deadline:
        done = True
        for kind, run_id in runs.items():
            status = snapshot(kind, run_id)
            signature = (status['state'], tuple(sorted((t['task_id'], t['state'], t['try_number']) for t in status['tasks'])))
            if signature != last.get(kind):
                evidence[kind].setdefault('events', []).append({'observed_at': datetime.now(timezone.utc).isoformat(), **status})
                last[kind] = signature
            if status['state'] not in ('success', 'failed'):
                seen_active[kind] = True
            if status['state'] not in ('success', 'failed') or not seen_active[kind]:
                done = False
            evidence[kind]['final'] = status
        if done:
            return
        time.sleep(2)
    raise TimeoutError('Airflow experiment timed out; workspaces and logs preserved')


def prepare(suite, case, seed=None):
    path = ROOT / f'include/observability_workspaces/{suite}_{case}'
    if path.exists():
        raise FileExistsError(f'Use a new suite name; {path} already exists')
    if seed:
        shutil.copytree(seed, path)
    else:
        (path / 'include/data').mkdir(parents=True)
        shutil.copytree(ROOT / 'assignment/nammamart_dataset', path / 'include/data/nammamart')
        shutil.copytree(ROOT / 'include/sql', path / 'include/sql')
    (path / '.prepared').write_text('Isolated NammaMart assignment experiments\n')
    return path


def mutate(path, case):
    data = path / 'include/data/nammamart'
    orders = data / 'orders.csv'
    with orders.open(newline='') as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames, list(reader)
    if case in ('missing', 'recovery'):
        (data / 'products.csv').rename(data / 'products.csv.hidden')
        return
    if case == 'bad_rows':
        template = next(row for row in rows if row['order_id']=='ORD000159')
        for label, column, value in [('NULL','customer_id',''), ('NEGATIVE','quantity','-1'),
                                     ('STORE','store_id','UNKNOWN'), ('STATUS','order_status','SHIPPED'),
                                     ('FUTURE','order_ts','2027-01-01 12:00:00')]:
            row = dict(template, order_id=f'TEST_{label}')
            row[column] = value
            rows.append(row)
    elif case == 'schema':
        fields = ['total' if c=='order_amount' else c for c in fields]
        rows = [{('total' if k=='order_amount' else k): v for k,v in row.items()} for row in rows]
    elif case == 'volume':
        rows = rows[:50]
    elif case == 'drift':
        for row in rows:
            if row['store_id']=='S04':
                row['unit_price'] = str(float(row['unit_price']) * 100)
    elif case == 'freshness':
        for row in rows:
            row['order_ts'] = '2026-09-25 12:00:00'
    with orders.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def metrics(path, kind, run_id):
    filename = 'warehouse_vijayc5.duckdb' if kind=='etl' else 'warehouse_elt_vijayc5.duckdb'
    fact = 'etl_fact_orders' if kind=='etl' else 'mart_fact_orders'
    with duckdb.connect(str(path / 'include' / filename), read_only=True) as db:
        tables = {r[0] for r in db.execute('SHOW TABLES').fetchall()}
        result = {'audit': db.execute('SELECT status,rows_extracted,rows_loaded,rows_quarantined FROM pipeline_runs WHERE run_id=?', [run_id]).fetchone()}
        if fact in tables:
            result['facts'] = db.execute(f'SELECT count(*),round(sum(net_revenue),2),count(distinct order_id) FROM {fact}').fetchone()
            result['store_s04_revenue'] = db.execute(f"SELECT coalesce(round(sum(net_revenue),2),0) FROM {fact} WHERE store_id='S04'").fetchone()[0]
        if 'dq_results' in tables:
            result['failed_checks'] = db.execute('SELECT check_name,rows_failed FROM dq_results WHERE run_id=? AND rows_failed>0 ORDER BY check_name', [run_id]).fetchall()
        if 'incremental_results' in tables:
            result['increment'] = db.execute('SELECT inserted_orders,changed_orders FROM incremental_results WHERE run_id=?', [run_id]).fetchone()
        if kind=='elt':
            result['raw_orders'] = db.execute('SELECT count(*) FROM raw_orders').fetchone()[0] if 'raw_orders' in tables else 0
            if 'stg_orders' in tables:
                result['staging_keys'] = db.execute('SELECT count(*),count(distinct order_id) FROM stg_orders').fetchone()
                result['corrections_returned'] = db.execute("SELECT count(*) FROM stg_orders WHERE order_status='RETURNED' AND _source_file='orders_2026-10-01_increment.csv' AND order_id IN (SELECT order_id FROM raw_orders WHERE _source_file='orders.csv')").fetchone()[0]
            if 'quality_records' in tables:
                result['injected_reasons'] = db.execute("SELECT row_key,failure_reason FROM quality_records WHERE evaluated_run_id=? AND row_key LIKE 'TEST_%'", [run_id]).fetchall()
        else:
            token = hashlib.sha256(run_id.encode()).hexdigest()[:20]
            quarantine = path / f'include/quarantine/vijayc5/orders_failed_{token}.csv'
            if quarantine.exists():
                with quarantine.open(newline='') as handle:
                    result['injected_reasons'] = [(r['order_id'], r['failure_reason']) for r in csv.DictReader(handle) if r['order_id'].startswith('TEST_')]
            corrections = path / 'include/etl_state/vijayc5/order_corrections.csv'
            if corrections.exists():
                with corrections.open(newline='') as handle:
                    result['corrections_returned'] = sum(r['order_status']=='RETURNED' for r in csv.DictReader(handle))
        return result


def pair(suite, case, path, output, increment=False):
    runs = {kind: f'{suite}_{case}_{kind}' for kind in KINDS}
    evidence = {kind: {'dag_id': f'nammamart_{kind}_observability_vijayc5', 'run_id': run_id, 'workspace': path.name} for kind,run_id in runs.items()}
    for kind, run_id in runs.items():
        config = {'as_of': AS_OF, 'include_increment': increment, 'observability_workspace': path.name}
        cli(['dags','trigger',evidence[kind]['dag_id'],'--run-id',run_id,'--logical-date',datetime.now(timezone.utc).isoformat(),'--conf',json.dumps(config)], path / f'private_trigger_{case}_{kind}.log')
    print(f'Triggered {case}: both DAGs', flush=True)
    await_runs(runs, evidence)
    for kind, run_id in runs.items():
        evidence[kind]['metrics'] = metrics(path, kind, run_id)
    output[case] = evidence
    save(ROOT / f'include/observability_reports/observability_{suite}.json', output)
    print(f'{case}: '+', '.join(f"{k}={v['final']['state']}" for k,v in evidence.items()), flush=True)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', required=True)
    args = parser.parse_args()
    suite = args.suite
    if not re.fullmatch(r'obs_[a-z0-9_]{1,40}', suite):
        parser.error('suite must match obs_[a-z0-9_]{1,40}')
    source = ROOT / 'assignment/nammamart_dataset'
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.csv')}
    output = {'suite': suite, 'as_of': AS_OF, 'cases': {}}
    cases = output['cases']
    # Keep checkpoint JSON flat while running; final manifest also includes hashes.
    base = prepare(suite,'base')
    from airflow.models.dag import DagModel
    from airflow.utils.session import create_session
    deadline = time.monotonic() + 240
    while True:
        with create_session() as session:
            found = session.query(DagModel).filter(DagModel.dag_id.in_([f'nammamart_{kind}_observability_vijayc5' for kind in KINDS])).count()
        if found == 2:
            break
        if time.monotonic() > deadline:
            raise TimeoutError('Experiment DAGs not discovered; inspect import errors')
        time.sleep(3)
    try:
        for kind in KINDS:
            cli(['dags','unpause',f'nammamart_{kind}_observability_vijayc5'], base / f'private_unpause_{kind}.log')
        pair(suite,'happy',base,cases)
        seed = prepare(suite,'seed',base)
        pair(suite,'rerun',base,cases)
        pair(suite,'increment',base,cases,True)
        for case in ['missing','bad_rows','schema','volume','drift','freshness','recovery']:
            path = prepare(suite,case,seed)
            mutate(path,case)
            evidence = pair(suite,case,path,cases)
            if case == 'recovery':
                (path / 'include/data/nammamart/products.csv.hidden').rename(path / 'include/data/nammamart/products.csv')
                recovered = {}
                runs = {}
                for kind in KINDS:
                    previous = evidence[kind]
                    root_task = 'extract_products' if kind=='etl' else 'load_raw'
                    logical = previous['final']['logical_date']
                    cli(['tasks','clear',previous['dag_id'],'--task-regex',root_task,'--downstream',
                         '--start-date',logical,'--end-date',logical,'--yes'],path / f'private_clear_{kind}.log')
                    recovered[kind] = {'dag_id':previous['dag_id'],'run_id':previous['run_id'],'workspace':path.name,'before':previous['final']}
                    runs[kind] = previous['run_id']
                    after_clear = snapshot(kind, previous['run_id'])
                    if after_clear['state'] == 'failed':
                        raise RuntimeError('Clear did not reset the failed run; inspect private_clear log')
                await_runs(runs,recovered)
                for kind in KINDS:
                    recovered[kind]['metrics'] = metrics(path,kind,runs[kind])
                cases['recovered'] = recovered
                print('Recovery after Clear: '+str({k:v['final']['state'] for k,v in recovered.items()}),flush=True)
            # Restore each test source after observation, retaining warehouse/log evidence.
            for original in source.glob('*.csv'):
                shutil.copy2(original,path / 'include/data/nammamart' / original.name)
        assert all(hashlib.sha256((source/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items())
        output['source_hashes_unchanged'] = True
        save(ROOT / f'include/observability_reports/observability_{suite}.json',output)
        print('All experiment runs collected; original source hashes unchanged.',flush=True)
    finally:
        for kind in KINDS:
            cli(['dags','pause',f'nammamart_{kind}_observability_vijayc5'],base / f'private_pause_{kind}.log')


if __name__ == '__main__':
    main()
