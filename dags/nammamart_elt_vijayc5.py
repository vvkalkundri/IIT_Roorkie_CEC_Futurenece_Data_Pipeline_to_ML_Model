"""Airflow ELT DAG. Task definitions live in include/nammamart_dag_factories.py."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from include.nammamart_dag_factories import create_elt_dag

dag_instance = create_elt_dag('nammamart_elt_vijayc5', '0 9 * * 1-6')
