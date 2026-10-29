"""Run with: python -m unittest discover -s tests -p test_nammamart_etl.py"""
import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

import duckdb
import pandas as pd

from include.nammamart_etl_helpers import FILES, extract, validate, transform, load, audit


class EtlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'include/data/nammamart'
        self.data.mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / 'assignment/nammamart_dataset'
        for name in FILES:
            shutil.copy2(source / name, self.data / name)

    def run_etl(self, run_id):
        with contextlib.redirect_stdout(io.StringIO()):
            for name in FILES:
                extract(self.root, run_id, name)
            counts = validate(self.root, run_id, '2026-10-25')
            transform(self.root, run_id)
            load(self.root, run_id)
            audit(self.root, run_id, '2026-10-25T00:00:00Z', True)
        return counts

    def test_repeat_load_accounting_and_privacy(self):
        totals = []
        for run_id in ['first', 'repeat']:
            counts = self.run_etl(run_id)
            for count in counts.values():
                self.assertEqual(count['extracted'], count['accepted'] + count['quarantined'])
            with duckdb.connect(str(self.root / 'include/warehouse_vijayc5.duckdb')) as db:
                totals.append(db.execute('SELECT count(*), round(sum(net_revenue),2) FROM etl_fact_orders').fetchone())
                self.assertEqual(db.execute('SELECT count(*)-count(distinct order_id) FROM etl_fact_orders').fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM etl_dim_customer WHERE email <> '[REDACTED]' OR phone <> '[REDACTED]'").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM etl_fact_orders WHERE order_status <> 'DELIVERED' AND net_revenue <> 0").fetchone()[0], 0)
                dimensions = {r[0] for r in db.execute('SELECT DISTINCT dimension FROM dq_results').fetchall()}
                self.assertEqual(len(dimensions), 6)
                # No accepted delivered order is among payment-held order keys.
                self.assertEqual(db.execute("SELECT count(*) FROM etl_fact_orders f JOIN etl_payment_reconciliation r USING(order_id) WHERE f.order_status='DELIVERED' AND (r.reason LIKE 'Delivered order requires%' OR r.reason = 'Successful payment amount differs from order amount')").fetchone()[0], 0)
        self.assertEqual(totals[0], totals[1])
        self.assertGreater(totals[0][0], 0)

    def test_missing_source_and_failure_audit(self):
        (self.data / 'products.csv').unlink()
        with self.assertRaises(FileNotFoundError):
            extract(self.root, 'missing', 'products.csv')
        audit(self.root, 'missing', '2026-10-25T00:00:00Z', False)
        with duckdb.connect(str(self.root / 'include/warehouse_vijayc5.duckdb')) as db:
            self.assertEqual(db.execute('SELECT status, rows_loaded FROM pipeline_runs').fetchone(), ('FAILED', 0))

    def test_schema_change_fails_loudly(self):
        path = self.data / 'orders.csv'
        path.write_text(path.read_text().replace('order_amount', 'total', 1))
        with self.assertRaisesRegex(ValueError, 'schema'):
            extract(self.root, 'schema', 'orders.csv')

    def test_injected_critical_order_is_quarantined(self):
        path = self.data / 'orders.csv'
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        row = frame.iloc[0].copy()
        row['order_id'], row['quantity'], row['customer_id'] = 'TEST_BAD_ORDER', '-1', ''
        pd.concat([frame, row.to_frame().T], ignore_index=True).to_csv(path, index=False)
        self.run_etl('bad-row')
        failed = pd.concat([pd.read_csv(p) for p in (self.root / 'include/quarantine/vijayc5').glob('orders_failed_*.csv')])
        reason = failed.loc[failed.order_id.eq('TEST_BAD_ORDER'), 'failure_reason'].iloc[0]
        self.assertIn('quantity:nonpositive', reason)
        self.assertIn('customer_id:missing', reason)

    def test_increment_retains_returns_on_baseline_rerun(self):
        self.run_etl('baseline')
        source = Path(__file__).resolve().parents[1] / 'assignment/nammamart_dataset/orders_2026-10-01_increment.csv'
        shutil.copy2(source, self.data / source.name)
        with contextlib.redirect_stdout(io.StringIO()):
            for name in FILES:
                extract(self.root, 'increment', name, include_increment=True)
            validate(self.root, 'increment', '2026-10-25')
            transform(self.root, 'increment')
            load(self.root, 'increment')
        with duckdb.connect(str(self.root / 'include/warehouse_vijayc5.duckdb')) as db:
            self.assertEqual(db.execute("SELECT inserted_orders,changed_orders FROM incremental_results WHERE run_id='increment'").fetchone(), (150,10))
            before = db.execute('SELECT count(*),round(sum(net_revenue),2) FROM etl_fact_orders').fetchone()
        self.run_etl('repeat-base')
        with duckdb.connect(str(self.root / 'include/warehouse_vijayc5.duckdb')) as db:
            self.assertEqual(before, db.execute('SELECT count(*),round(sum(net_revenue),2) FROM etl_fact_orders').fetchone())
        corrections = pd.read_csv(self.root / 'include/etl_state/vijayc5/order_corrections.csv')
        self.assertEqual(int(corrections.order_status.eq('RETURNED').sum()),10)

    def test_volume_drop_warns(self):
        self.run_etl('baseline')
        path = self.data / 'orders.csv'
        pd.read_csv(path).head(50).to_csv(path,index=False)
        self.run_etl('low-volume')
        with duckdb.connect(str(self.root / 'include/warehouse_vijayc5.duckdb')) as db:
            self.assertEqual(db.execute("SELECT severity,rows_checked,rows_failed FROM dq_results WHERE run_id='low-volume' AND check_name='orders.csv:volume:drop_over_90pct'").fetchone(), ('Warning',1,1))


if __name__ == '__main__':
    unittest.main()
