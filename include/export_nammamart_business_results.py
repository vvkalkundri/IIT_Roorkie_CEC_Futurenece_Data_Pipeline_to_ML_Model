"""Export read-only SQL and complete result tables for the six business questions.

Run from the project root: .venv/bin/python include/export_nammamart_business_results.py
Never triggers DAGs or changes warehouse/source data. Replaces generated reports.
"""
import hashlib
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/business_results'


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def table(columns, rows):
    def cell(value):
        return ('NULL' if value is None else str(value)).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(columns) + ' |',
                      '| ' + ' | '.join(['---'] * len(columns)) + ' |',
                      *['| ' + ' | '.join(map(cell, row)) + ' |' for row in rows]])


def export(kind):
    filename = 'warehouse_vijayc5.duckdb' if kind == 'etl' else 'warehouse_elt_vijayc5.duckdb'
    fact = 'etl_fact_orders' if kind == 'etl' else 'mart_fact_orders'
    recon = 'etl_payment_reconciliation' if kind == 'etl' else 'mart_payment_reconciliation'
    with duckdb.connect(str(ROOT / 'include' / filename), read_only=True) as db:
        run_id, end_time = db.execute("SELECT run_id,cast(end_time AS VARCHAR) FROM pipeline_runs WHERE status='SUCCESS' ORDER BY end_time DESC LIMIT 1").fetchone()
        if kind == 'elt':
            assert db.execute('SELECT run_id FROM mart_publication').fetchone()[0] == run_id
        selected_run = literal(run_id)
        token = hashlib.sha256(run_id.encode()).hexdigest()[:20]
        # Exact-run files, never a wildcard over every historical quarantine.
        quarantine = ROOT / 'include/quarantine/vijayc5'
        paths = [quarantine / f'{name}_failed_{token}.csv' for name in ('orders','payments','customers','products','stores')]
        if kind == 'etl':
            assert all(p.exists() for p in paths), 'Missing selected-run quarantine files'
            rejected = '\nUNION ALL\n'.join(
                f"SELECT {literal(p.name.split('_failed_')[0]+'.csv')} AS source_file, failure_reason FROM read_csv({literal(p)}, header=true, all_varchar=true)" for p in paths)
        else:
            rejected = f"SELECT source_file, failure_reason FROM quality_records WHERE evaluated_run_id={selected_run} AND dq_status='FAIL'"
        period = "order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'"
        queries = [
            ('Q1 — Daily net revenue by zone and store', f"""SELECT order_date, zone,
 CASE WHEN grouping(store_id)=1 THEN 'ZONE TOTAL' ELSE 'STORE' END AS level,
 store_id, round(sum(net_revenue),2) AS net_revenue
FROM {fact}
WHERE order_status='DELIVERED' AND {period}
GROUP BY GROUPING SETS ((order_date,zone),(order_date,zone,store_id))
ORDER BY order_date,zone,level,store_id;"""),
            ('Q2 — Revenue and gross margin by category', f"""SELECT category, round(sum(net_revenue),2) AS net_revenue,
 round(sum(gross_margin),2) AS gross_margin
FROM {fact} WHERE order_status='DELIVERED' AND {period}
GROUP BY category ORDER BY category;"""),
            ('Q3 — Delivery time and percentage within 15 minutes', f"""SELECT store_id, count(*) AS delivered_orders,
 round(avg(delivery_minutes),2) AS avg_delivery_minutes,
 round(100.0*count(*) FILTER(WHERE within_15_min)/nullif(count(*),0),2) AS pct_within_15_min
FROM {fact} WHERE order_status='DELIVERED' AND {period}
GROUP BY store_id ORDER BY store_id;"""),
            ('Q4a — Revenue by payment mode', f"""SELECT payment_mode,round(sum(net_revenue),2) AS net_revenue
FROM {fact} WHERE order_status='DELIVERED' AND {period}
GROUP BY payment_mode ORDER BY payment_mode;"""),
            ('Q4b — Reconciliation amounts and unresolved exceptions', f"""SELECT count(*) AS exception_rows,
 count(*) FILTER(WHERE order_amount IS NOT NULL AND amount_paid IS NOT NULL) AS quantifiable_rows,
 count(*) FILTER(WHERE order_amount IS NULL OR amount_paid IS NULL) AS unknown_amount_rows,
 round(sum(abs(amount_paid-order_amount)),2) AS known_absolute_difference,
 round(sum(amount_paid-order_amount),2) AS known_signed_difference
FROM {recon};"""),
            ('Q5 — Top ten customers by delivered-order spend', f"""SELECT customer_id,loyalty_tier,round(sum(net_revenue),2) AS total_spend
FROM {fact} WHERE order_status='DELIVERED' AND {period}
GROUP BY customer_id,loyalty_tier
ORDER BY total_spend DESC,customer_id LIMIT 10;"""),
            ('Q6 — Rejected rows by file and reason for the selected run', f"""WITH rejected AS (
{rejected}
), result AS (
 SELECT source_file,'FILE TOTAL (unique records)' AS reason,count(*) AS rejected_records
 FROM rejected GROUP BY source_file
 UNION ALL
 SELECT source_file,trim(reason) AS reason,count(*) AS rejected_records
 FROM rejected,unnest(string_split(failure_reason,';')) AS reasons(reason)
 WHERE trim(reason)<>'' GROUP BY source_file,trim(reason)
)
SELECT {selected_run} AS run_id,* FROM result ORDER BY source_file,reason;"""),
        ]
        notes = (f'# {kind.upper()}: business SQL and actual results\n\n'
                 f'Warehouse: `include/{filename}`. Selected successful run: `{run_id}`. '
                 f'Audit end time: `{end_time}`.\n\n'
                 'Q1–Q5 revenue/delivery/spend cover September 2026 and only approved DELIVERED orders. '
                 'Q4b covers all exceptions in the current reconciliation snapshot, including undated/orphan records; '
                 'it is not a September-only ledger or a proven total loss. Unknown amounts remain unknown. '
                 'Q6 means records rejected in the selected processing run, not orders whose business date is today. '
                 'Reason counts overlap; use FILE TOTAL for distinct source records per file. '
                 'Q1 includes zone subtotals and store rows: do not add both levels together.\n\n')
        sql_text = f'-- {kind.upper()} warehouse: {filename}\n-- Selected run: {run_id}\n-- Revenue period: September 2026. Q4b is full current snapshot.\n\n'
        for title, sql in queries:
            cursor = db.execute(sql)
            columns, rows = [c[0] for c in cursor.description], cursor.fetchall()
            notes += f'## {title}\n\n```sql\n{sql}\n```\n\nResult: {len(rows)} rows.\n\n{table(columns, rows)}\n\n'
            sql_text += f'-- {title}\n{sql}\n\n'
        safe_quarantine = (f"SELECT order_id,quantity,failure_reason FROM read_csv({literal(paths[0])},header=true,all_varchar=true) WHERE order_id='ORD000099';" if kind=='etl' else
                           f"SELECT source_file,row_key,failure_reason FROM quality_records WHERE evaluated_run_id={selected_run} AND row_key='ORD000099' AND dq_status='FAIL';")
        screenshot_sql = f"""-- Run each SELECT separately and capture SQL plus its result grid.
-- Database: {filename}; run: {run_id}
SELECT run_id,dag_id,cast(start_time AS VARCHAR) AS start_time,
 cast(end_time AS VARCHAR) AS end_time,rows_extracted,rows_loaded,rows_quarantined,status
FROM pipeline_runs WHERE run_id={selected_run};

SELECT run_id,dimension,severity,count(*) AS checks,
 sum(rows_checked) AS check_evaluations,sum(rows_failed) AS failed_check_evaluations
FROM dq_results WHERE run_id={selected_run}
GROUP BY run_id,dimension,severity ORDER BY dimension,severity;

SELECT check_name,dimension,severity,rows_checked,rows_failed,status
FROM dq_results WHERE run_id={selected_run} AND rows_failed>0
ORDER BY dimension,check_name;

SELECT order_id,payment_id,reason,order_amount,amount_paid,
 round(amount_paid-order_amount,2) AS amount_difference
FROM {recon} ORDER BY reason,order_id,payment_id LIMIT 20;

-- Privacy-limited quarantine view; originals remain private.
{safe_quarantine}
"""
        # Validate every screenshot statement before handing it to the user.
        for statement in db.extract_statements(screenshot_sql):
            db.execute(statement).fetchall()
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f'{kind}_business.sql').write_text(sql_text)
        (OUT / f'{kind}_results.md').write_text(notes)
        (OUT / f'{kind}_screenshots.sql').write_text(screenshot_sql)
        print(f'{kind.upper()}: exported and verified SQL, full results and screenshot queries for {run_id}')


if __name__ == '__main__':
    for pipeline in ('etl','elt'):
        export(pipeline)
