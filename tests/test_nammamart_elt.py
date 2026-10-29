"""Integration checks against real fixtures, isolated from the user's databases."""
import contextlib
import csv
import io
import shutil
import tempfile
import unittest
from pathlib import Path

import duckdb

from include import nammamart_elt_helpers as elt
from include import nammamart_etl_helpers as etl

PROJECT = Path(__file__).resolve().parents[1]


class EltTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'include/data').mkdir(parents=True)
        shutil.copytree(PROJECT / 'assignment/nammamart_dataset', self.root / 'include/data/nammamart')
        shutil.copytree(PROJECT / 'include/sql', self.root / 'include/sql')

    def run_elt(self, run_id, incremental=False):
        with contextlib.redirect_stdout(io.StringIO()):
            elt.load_raw(self.root, run_id, incremental)
            counts = elt.build_staging(self.root, run_id, '2026-10-25')
            elt.build_marts(self.root, run_id, '2026-10-25')
            elt.audit(self.root, run_id, '2026-10-25T00:00:00+00:00', True)
        return counts

    def test_raw_exact_values_and_baseline_matches_etl(self):
        self.run_elt('baseline')
        with contextlib.redirect_stdout(io.StringIO()):
            for name in etl.FILES:
                etl.extract(self.root, 'etl', name)
            etl.validate(self.root, 'etl', '2026-10-25')
            etl.transform(self.root, 'etl')
            etl.load(self.root, 'etl')
        self.assertEqual(elt.compare_etl(self.root)['status'], 'MATCH')
        with elt.connect(self.root) as db:
            for name in elt.BASE_FILES:
                with (self.root / 'include/data/nammamart' / name).open(newline='') as handle:
                    rows = list(csv.reader(handle))
                columns = ','.join('"'+column+'"' for column in rows[0])
                actual = db.execute(f'SELECT {columns} FROM raw_{Path(name).stem} ORDER BY _row_number').fetchall()
                self.assertEqual(actual, [tuple(row) for row in rows[1:]])
            actual = db.execute('SELECT order_id, net_revenue, gross_margin FROM mart_fact_orders ORDER BY order_id').fetchall()
            self.assertEqual(db.execute("SELECT count(*) FROM stg_customers WHERE email <> '[REDACTED]' OR phone <> '[REDACTED]'").fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(distinct dimension) FROM dq_results').fetchone()[0], 6)
            self.assertEqual(db.execute("SELECT rows_extracted, rows_loaded, status FROM pipeline_runs WHERE run_id='baseline'").fetchone(), (5212, 1777, 'SUCCESS'))
        with duckdb.connect(str(self.root / 'include/warehouse_vijayc5.duckdb')) as db:
            expected = db.execute('SELECT order_id, net_revenue, gross_margin FROM etl_fact_orders ORDER BY order_id').fetchall()
        self.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            self.assertEqual(a[0], b[0])
            self.assertAlmostEqual(float(a[1]), float(b[1]), places=2)
            self.assertAlmostEqual(float(a[2]), float(b[2]), places=2)

    def test_increment_and_repeat_do_not_revert_corrections(self):
        self.run_elt('baseline')
        self.assertEqual(self.run_elt('increment', True), {'inserted': 150, 'changed': 10})
        with elt.connect(self.root) as db:
            before = db.execute('SELECT count(*), sum(net_revenue) FROM mart_fact_orders').fetchone()
            self.assertEqual(db.execute('SELECT count(*), count(distinct order_id) FROM stg_orders').fetchone(), (2550, 2550))
            corrections = db.execute("SELECT order_id, order_status FROM stg_orders WHERE _source_file=? AND order_id IN (SELECT trim(order_id) FROM raw_orders WHERE _source_file='orders.csv')", [elt.INCREMENT]).fetchall()
            self.assertEqual(len(corrections), 10)
            self.assertTrue(all(status == 'RETURNED' for _, status in corrections))
            self.assertEqual(db.execute("SELECT count(*) FROM mart_fact_orders WHERE order_id IN (SELECT order_id FROM stg_orders WHERE order_status='RETURNED') AND net_revenue<>0").fetchone()[0], 0)
        self.assertEqual(self.run_elt('repeat-base'), {'inserted': 0, 'changed': 0})
        with elt.connect(self.root) as db:
            self.assertEqual(before, db.execute('SELECT count(*), sum(net_revenue) FROM mart_fact_orders').fetchone())
            # Three baseline snapshots plus one incremental file are kept raw.
            self.assertEqual(db.execute('SELECT count(*) FROM raw_orders').fetchone()[0], 2412*3+160)

    def test_retry_idempotence_changed_source_and_schema_failure(self):
        self.run_elt('baseline')
        elt.load_raw(self.root, 'baseline')
        with elt.connect(self.root) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM raw_orders').fetchone()[0], 2412)
        path = self.root / 'include/data/nammamart/orders.csv'
        original = path.read_text()
        path.write_text(original.replace('ORD001913', 'CHANGED', 1))
        with self.assertRaisesRegex(ValueError, 'changed during retry'):
            elt.load_raw(self.root, 'baseline')
        path.write_text(original.replace('order_amount', 'total', 1))
        with self.assertRaisesRegex(ValueError, 'schema'):
            elt.load_raw(self.root, 'schema-error')
        elt.audit(self.root, 'schema-error', '2026-10-25T00:00:00+00:00', False)
        with elt.connect(self.root) as db:
            self.assertEqual(db.execute("SELECT status, rows_extracted FROM pipeline_runs WHERE run_id='schema-error'").fetchone(), ('FAILED', 0))
            self.assertEqual(db.execute('SELECT count(*) FROM raw_orders').fetchone()[0], 2412)

    def test_price_drift_is_quarantined_without_decimal_overflow(self):
        self.run_elt('baseline')
        source = self.root / 'include/data/nammamart/orders.csv'
        with source.open(newline='') as handle:
            reader = csv.DictReader(handle)
            fields, rows = reader.fieldnames, list(reader)
        for row in rows:
            if row['store_id'] == 'S04':
                row['unit_price'] = str(float(row['unit_price']) * 100)
        with source.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        self.run_elt('drift')
        with elt.connect(self.root) as db:
            self.assertGreater(db.execute("SELECT rows_failed FROM dq_results WHERE run_id='drift' AND check_name='orders.csv:order_amount:formula'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT coalesce(sum(net_revenue),0) FROM mart_fact_orders WHERE store_id='S04'").fetchone()[0], 0)

    def test_rejected_increment_does_not_fall_back_to_old_good_order(self):
        self.run_elt('baseline')
        with elt.connect(self.root) as db:
            key = db.execute("SELECT order_id FROM mart_fact_orders WHERE order_status='DELIVERED' ORDER BY order_id LIMIT 1").fetchone()[0]
        source = self.root / 'include/data/nammamart/orders.csv'
        with source.open(newline='') as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            row = next(row for row in reader if row['order_id'] == key)
        row['customer_id'] = ''
        with (self.root / 'include/data/nammamart' / elt.INCREMENT).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerow(row)
        self.run_elt('bad-update', True)
        with elt.connect(self.root) as db:
            self.assertEqual(db.execute('SELECT dq_status FROM stg_orders WHERE order_id=?', [key]).fetchone()[0], 'FAIL')
            self.assertEqual(db.execute('SELECT count(*) FROM mart_fact_orders WHERE order_id=?', [key]).fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
