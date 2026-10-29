"""Airflow DAG: unscheduled test aliases of the real DAG factories; isolated roots required."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from include.nammamart_dag_factories import create_etl_dag
from include.nammamart_dag_factories import create_elt_dag

etl_observability = create_etl_dag('nammamart_etl_observability_vijayc5', None)
elt_observability = create_elt_dag('nammamart_elt_observability_vijayc5', None)
