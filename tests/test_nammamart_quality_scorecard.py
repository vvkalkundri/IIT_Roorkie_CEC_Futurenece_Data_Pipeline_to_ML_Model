"""Read-only scorecard must distinguish pipeline failure from quality findings."""
import unittest
from pathlib import Path

import duckdb


class QualityScorecardTests(unittest.TestCase):
    def test_unevaluated_failed_run_is_not_a_quality_pass(self):
        with duckdb.connect(':memory:') as db:
            db.execute('CREATE TABLE pipeline_runs(run_id VARCHAR, dag_id VARCHAR, status VARCHAR, end_time VARCHAR)')
            db.execute('CREATE TABLE dq_results(run_id VARCHAR, dag_id VARCHAR, check_name VARCHAR, dimension VARCHAR, severity VARCHAR, rows_checked BIGINT, rows_failed BIGINT)')
            db.execute("INSERT INTO pipeline_runs VALUES ('failed','etl','FAILED','2026-10-25'), ('complete','etl','SUCCESS','2026-10-24')")
            db.execute("INSERT INTO dq_results VALUES ('complete','etl','quantity','Accuracy','Critical',10,2), ('complete','etl','amount','Accuracy','Critical',10,1), ('complete','etl','casing','Consistency','Warning',10,3)")
            sql = (Path(__file__).resolve().parents[1] / 'include/sql/nammamart/dq_dimension_scorecard.sql').read_text()
            rows = db.execute(sql).fetchall()
        failed = [r for r in rows if r[0]=='failed']
        self.assertEqual(len(failed), 6)
        self.assertTrue(all(r[5]==0 and r[-1]=='NOT_EVALUATED' for r in failed))
        accuracy = next(r for r in rows if r[0]=='complete' and r[4]=='Accuracy')
        self.assertEqual(accuracy[2], 'SUCCESS')
        self.assertEqual(accuracy[5:10], (2,2,0,20,3))
        self.assertEqual(accuracy[-1], 'CRITICAL_FINDINGS')
        consistency = next(r for r in rows if r[0]=='complete' and r[4]=='Consistency')
        self.assertEqual(consistency[-1], 'WARNINGS')


if __name__ == '__main__':
    unittest.main()
