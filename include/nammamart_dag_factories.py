"""NammaMart five-file snapshot ETL. See NAMMAMART_ETL_GUIDE.md."""
from datetime import timedelta
from pathlib import Path
import sys

import pendulum
from airflow.sdk import dag, task, get_current_context

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_root():
    from include.nammamart_observability import workspace
    context = get_current_context()
    conf = context['dag_run'].conf or {}
    if 'observability' in context['dag'].dag_id and not conf.get('observability_workspace'):
        raise ValueError('Experiment DAG requires a prepared observability_workspace')
    return workspace(ROOT, conf)


def settings():
    context = get_current_context()
    conf = context['dag_run'].conf or {}
    return context['run_id'], conf.get('as_of') or pendulum.now('Asia/Kolkata').to_date_string(), conf.get('include_increment', False)


def create_etl_dag(dag_id, schedule):
    @dag(
        dag_id=dag_id,
        schedule=schedule,
        start_date=pendulum.datetime(2026, 9, 1, tz='Asia/Kolkata'),
        catchup=False,
        max_active_runs=1,
        is_paused_upon_creation=True,
        default_args={'owner': 'vijayc5', 'retries': 2, 'retry_delay': timedelta(seconds=30),
                      'execution_timeout': timedelta(minutes=10)},
        tags=['nammamart', 'etl', 'assignment'],
        doc_md='Five parallel extracts → validation/quarantine → transformation → snapshot publication → audit. include_increment=true applies and retains order corrections.',
    )
    def nammamart_etl_vijayc5():
        @task
        def extract_file(name):
            from include.nammamart_etl_helpers import extract
            context = get_current_context()
            return extract(run_root(), context['run_id'], name, (context['dag_run'].conf or {}).get('include_increment', False))

        @task
        def validate_and_quarantine(extracted):
            from include.nammamart_etl_helpers import validate
            context = get_current_context()
            reference = (context['dag_run'].conf or {}).get('as_of') or pendulum.now('Asia/Kolkata').to_date_string()
            return validate(run_root(), context['run_id'], reference, context['dag'].dag_id)

        @task
        def transform_orders(counts):
            from include.nammamart_etl_helpers import transform
            return transform(run_root(), get_current_context()['run_id'])

        @task
        def load_and_report(transformed):
            from include.nammamart_etl_helpers import load
            load(run_root(), get_current_context()['run_id'])
            return True

        @task(trigger_rule='all_done', retries=0)
        def audit_run():
            from include.nammamart_etl_helpers import audit
            context = get_current_context()
            # Read this run's task result rather than trusting a leftover disk marker.
            success = context['ti'].xcom_pull(task_ids='load_and_report') is True
            audit(run_root(), context['run_id'], context['dag_run'].start_date, success, context['dag'].dag_id)
            if not success:
                raise RuntimeError('ETL failed; audit recorded FAILED. Inspect upstream task logs.')

        extracted = [extract_file.override(task_id=f'extract_{name}') (f'{name}.csv')
                     for name in ['orders', 'payments', 'customers', 'products', 'stores']]
        validated = validate_and_quarantine(extracted)
        transformed = transform_orders(validated)
        loaded = load_and_report(transformed)
        audit_task = audit_run()
        for upstream in [*extracted, validated, transformed, loaded]:
            upstream >> audit_task

    return nammamart_etl_vijayc5()



def create_elt_dag(dag_id, schedule):
    @dag(dag_id=dag_id, schedule=schedule,
         start_date=pendulum.datetime(2026, 9, 1, tz='Asia/Kolkata'), catchup=False,
         max_active_runs=1, is_paused_upon_creation=True,
         default_args={'owner': 'vijayc5', 'retries': 2, 'retry_delay': timedelta(seconds=30),
                       'execution_timeout': timedelta(minutes=10)},
         tags=['nammamart', 'elt', 'assignment'],
         doc_md='Raw inputs are append-only. All transformations use include/sql/nammamart/*.sql. Trigger with include_increment=true to ingest the correction feed.')
    def nammamart_elt_vijayc5():
        @task
        def load_raw():
            from include.nammamart_elt_helpers import load_raw as run
            run_id, _, incremental = settings()
            return run(run_root(), run_id, incremental)

        @task
        def transform_staging(raw_counts):
            from include.nammamart_elt_helpers import build_staging
            run_id, as_of, _ = settings()
            return build_staging(run_root(), run_id, as_of, get_current_context()['dag'].dag_id)

        @task
        def build_marts(staging_counts):
            from include.nammamart_elt_helpers import build_marts as run
            run_id, as_of, _ = settings()
            return run(run_root(), run_id, as_of)

        @task(trigger_rule='all_done', retries=0)
        def audit_run():
            from include.nammamart_elt_helpers import audit
            context = get_current_context()
            success = context['ti'].xcom_pull(task_ids='build_marts') is True
            audit(run_root(), context['run_id'], context['dag_run'].start_date, success, context['dag'].dag_id)
            if not success:
                raise RuntimeError('ELT failed. Audit recorded FAILED; inspect upstream logs.')

        raw = load_raw()
        staging = transform_staging(raw)
        marts = build_marts(staging)
        audit_task = audit_run()
        for upstream in [raw, staging, marts]:
            upstream >> audit_task

    return nammamart_elt_vijayc5()

