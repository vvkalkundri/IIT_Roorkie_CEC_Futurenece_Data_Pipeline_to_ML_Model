"""Export reviewed-schema metadata and quality/lineage evidence without raw PII.

Run: .venv/bin/python include/export_nammamart_governance.py
Reads the two warehouses without changing them. Refreshes documents only;
policy decisions in SUBMISSION.md are intentionally not generated.
"""
import csv
import hashlib
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'

# Meaning, source, allowed values/rule. Policy rules are not DB constraints.
FIELDS = {
 'order_id': ('Order business key', 'orders.order_id', 'One accepted fact per key'),
 'order_ts': ('Order timestamp in local business time', 'orders.order_ts', 'Parseable; not future-dated at reference date'),
 'customer_id': ('Linkable customer business key', 'customers/orders.customer_id', 'References accepted customer for facts'),
 'store_id': ('Store business key', 'stores/orders.store_id', 'References accepted store for facts'),
 'product_id': ('Product business key', 'products/orders.product_id', 'References accepted product for facts'),
 'quantity': ('Units ordered', 'orders.quantity', 'Positive whole number'),
 'unit_price': ('Sale price per unit', 'orders.unit_price', '> 0'),
 'discount_pct': ('Percentage discount', 'orders.discount_pct', '0–100'),
 'order_amount': ('Net order value', 'orders.order_amount', 'Rounded quantity × unit_price × (1 − discount_pct/100)'),
 'payment_mode': ('Payment method', 'orders.payment_mode', 'UPI / Card / Cash on Delivery / Wallet'),
 'order_status': ('Current order state', 'orders.order_status', 'DELIVERED / CANCELLED / RETURNED'),
 'channel': ('Ordering channel', 'orders.channel', 'Required text; enumeration not enforced'),
 'delivery_minutes': ('Time to deliver', 'orders.delivery_minutes', 'Required when DELIVERED; 0 ≤ value < 120; unusual range warning'),
 'loyalty_tier': ('Customer loyalty segment', 'customers.loyalty_tier', 'Uppercase; required; enumeration not enforced'),
 'category': ('Product reporting category', 'products.category', 'Required text'),
 'cost_price': ('Unit procurement cost', 'products.cost_price', '0 ≤ cost_price ≤ mrp'),
 'zone': ('Store operational zone', 'stores.zone', 'North / South / East / West'),
 'order_date': ('Business date for revenue attribution', 'DATE(order_ts)', 'Date of the original order'),
 'net_revenue': ('Revenue eligible for reporting', 'order_amount and order_status', 'Order amount if DELIVERED; otherwise 0'),
 'gross_margin': ('Revenue less cost of delivered goods', 'net_revenue − quantity × cost_price', 'Rounded to 2 decimals if DELIVERED; otherwise 0'),
 'within_15_min': ('Delivered within 15 minutes', 'order_status and delivery_minutes', 'true / false'),
 'full_name': ('Customer name, redacted in reporting', 'customers.full_name', '[REDACTED]'),
 'email': ('Customer email, redacted in reporting', 'customers.email', '[REDACTED]'),
 'phone': ('Customer phone, redacted in reporting', 'customers.phone', '[REDACTED]'),
 'city': ('Customer city', 'customers.city', 'Optional text; missing-value warning'),
 'area': ('Customer locality or store locality', 'customers.area / stores.area', 'Optional text; missing-value warning'),
 'pincode': ('Postal code; stored as text', 'customers.pincode / stores.pincode', '6 digits expected; invalid format is Warning'),
 'signup_date': ('Customer registration date', 'customers.signup_date', 'Parseable; not future-dated'),
 'is_active': ('Customer activity flag', 'customers.is_active', 'Required text; enumeration not enforced'),
 'product_name': ('Product display name', 'products.product_name', 'Required text'),
 'sub_category': ('Product subcategory', 'products.sub_category', 'Required text'),
 'brand': ('Product brand', 'products.brand', 'Required text'),
 'mrp': ('Maximum retail price', 'products.mrp', '> 0'),
 'unit': ('Product unit of sale', 'products.unit', 'Required text'),
 'is_perishable': ('Product perishability flag', 'products.is_perishable', 'Required text; not cast to Boolean currently'),
 'launch_date': ('Product launch date', 'products.launch_date', 'Parseable; not future-dated'),
 'store_name': ('Dark-store name', 'stores.store_name', 'Required text'),
 'open_date': ('Store opening date', 'stores.open_date', 'Parseable; not future-dated'),
 'manager_name': ('Employee name, redacted in reporting', 'stores.manager_name', '[REDACTED]'),
 'capacity_orders_per_day': ('Nominal store daily capacity', 'stores.capacity_orders_per_day', 'Positive whole number; volume comparison not yet implemented'),
}


def md_table(headers, rows):
    clean = lambda value: str(value).replace('|', '\\|').replace('\n', ' ')
    return ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] + [
        '| ' + ' | '.join(clean(value) for value in row) + ' |' for row in rows]


def export():
    DOCS.mkdir(exist_ok=True)
    connections = {}
    try:
        for label, name in [('ETL', 'warehouse_vijayc5.duckdb'), ('ELT', 'warehouse_elt_vijayc5.duckdb')]:
            connections[label] = duckdb.connect(str(ROOT / 'include' / name), read_only=True)
        evidence = ['# Data quality and governance — verified evidence', '',
                    'This file is regenerated from the current local warehouses. It contains identifiers, counts and lineage metadata, not raw names, emails or phone numbers.', '',
                    '## Data quality scorecard', '',
                    'Each check may evaluate the same record; failed-check evaluations are not rejected-row counts. A successful pipeline can have critical findings because those records were quarantined. A run without checks is NOT_EVALUATED, not PASS.', '']
        query = (ROOT / 'include/sql/nammamart/dq_dimension_scorecard.sql').read_text()
        catalog = ['# Recorded quality-rule catalogue', '',
                   'Rules below are taken from each latest recorded run. Rule names and severities identify the implemented checks; row counts live in dq_results. This is evidence of executed rules, not a promise that every conceivable defect is covered.', '']
        latest = {}
        for label, db in connections.items():
            run = db.execute('SELECT run_id,status,cast(end_time AS VARCHAR) FROM pipeline_runs ORDER BY end_time DESC LIMIT 1').fetchone()
            if run is None:
                raise ValueError(f'{label}: no pipeline runs available')
            latest[label] = run[0]
            rows = [row for row in db.execute(query).fetchall() if row[0] == run[0]]
            if len(rows) != 6:
                raise AssertionError(f'{label}: expected six scorecard dimensions')
            evidence += [f'### {label}', '', f'Run: `{run[0]}`. Recorded pipeline status: **{run[1]}**. End time: `{run[2]}`.', '']
            evidence += md_table(['Dimension', 'Checks', 'Critical checks with failures', 'Warning checks with failures', 'Failed check evaluations', 'Result'],
                                 [(r[4],r[5],r[6],r[7],r[9],r[10]) for r in rows]) + ['']
            rules = db.execute('SELECT check_name,dimension,severity FROM dq_results WHERE run_id=? ORDER BY dimension,check_name', [run[0]]).fetchall()
            catalog += [f'## {label}', '', f'Run: `{run[0]}`. {len(rules)} recorded checks.', '']
            catalog += md_table(['Check', 'Dimension', 'Severity'], rules) + ['']

        elt, etl = connections['ELT'], connections['ETL']
        group = elt.execute("SELECT order_date,store_id,zone,sum(net_revenue),count(*) FROM mart_fact_orders WHERE order_status='DELIVERED' GROUP BY ALL ORDER BY count(*),order_date,store_id LIMIT 1").fetchone()
        if not group:
            raise ValueError('No delivered order available for lineage evidence')
        day, store, zone, amount, _ = group
        trace = elt.execute('''SELECT f.order_id,f.order_status,f.net_revenue,f._source_file,f._batch_id,f._row_number,
                              r.quantity,r.unit_price,r.discount_pct
                              FROM mart_fact_orders f JOIN raw_orders r ON f._batch_id=r._batch_id AND f._row_number=r._row_number
                              WHERE f.order_date=? AND f.store_id=? ORDER BY f.order_id''', [day,store]).fetchall()
        kpi = elt.execute('SELECT net_revenue FROM mart_daily_store_kpis WHERE order_date=? AND store_id=?', [day,store]).fetchone()[0]
        assert sum(row[2] for row in trace) == kpi == amount
        etl_value = etl.execute('SELECT coalesce(sum(net_revenue),0) FROM etl_fact_orders WHERE order_date=? AND store_id=?', [day,store]).fetchone()[0]
        evidence += ['## One number traced to source rows', '',
                     f'ELT `mart_daily_store_kpis`: date **{day}**, store **{store}**, zone **{zone}**, net revenue **{amount:.2f}**. The source rows below sum exactly to that number. ETL reports **{etl_value:.2f}** for the same date/store in its current snapshot.', '']
        evidence += md_table(['Order', 'Status', 'Revenue', 'Source file', 'Batch', 'Data record', 'Quantity', 'Unit price', 'Discount %'], trace) + ['']
        evidence += ['Record numbers exclude the CSV header. ELT links directly through `_batch_id` and `_row_number`; join to `ingestion_batches` for file hash and source run. ETL must reconstruct the same link through its saved run snapshot and order ID because its fact has no source-record metadata.', '']
        etl_token = hashlib.sha256(latest['ETL'].encode()).hexdigest()[:20]
        snapshot = ROOT / f'include/etl_runs/vijayc5/{etl_token}/orders.csv'
        if snapshot.exists():
            with snapshot.open(newline='') as handle:
                source = list(csv.DictReader(handle))
            order_ids = {row[0] for row in trace}
            records = [(r['order_id'], index) for index,r in enumerate(source,1) if r['order_id'].strip() in order_ids]
            evidence += [f'ETL snapshot: `include/etl_runs/vijayc5/{etl_token}/orders.csv`.', '']
            evidence += md_table(['Order ID', 'ETL source data record'], records) + ['']
        else:
            evidence += ['ETL run snapshot is unavailable locally; exact source-row evidence cannot be reconstructed from its fact table alone.', '']

        # Example verified against both current finance facts and the ETL quarantine.
        rejected_key = 'ORD000099'
        rejected = elt.execute("SELECT row_key,source_file,batch_id,row_number,failure_reason FROM elt_quarantine WHERE row_key=? AND source_file='orders.csv' LIMIT 1", [rejected_key]).fetchone()
        quarantine = ROOT / f'include/quarantine/vijayc5/orders_failed_{etl_token}.csv'
        if rejected and quarantine.exists():
            with quarantine.open(newline='') as handle:
                rejected_etl = next((r for r in csv.DictReader(handle) if r['order_id']==rejected_key), None)
            etl_count = etl.execute('SELECT count(*) FROM etl_fact_orders WHERE order_id=?', [rejected_key]).fetchone()[0]
            elt_count = elt.execute('SELECT count(*) FROM mart_fact_orders WHERE order_id=?', [rejected_key]).fetchone()[0]
            assert rejected_etl is not None and etl_count == elt_count == 0
            evidence += ['## Rejected order audit', '',
                f'Order `{rejected_key}`: ELT reason `{rejected[4]}`; exact raw source `{rejected[1]}`, batch `{rejected[2]}`, data record `{rejected[3]}`. ETL reason `{rejected_etl["failure_reason"]}` in `include/quarantine/vijayc5/orders_failed_{etl_token}.csv`.', '',
                f'Verified fact-table presence: **ETL {etl_count} rows; ELT {elt_count} rows**. Therefore this order contributes no finance revenue. Inspect exact private raw values using the SQL in SUBMISSION.md; this public-facing document does not duplicate the source record.', '']
        else:
            evidence += ['## Rejected order audit', '', 'The example order or ETL quarantine snapshot is unavailable in the current run; select another rejected order and verify its absence before claiming evidence.', '']

        dictionary = ['# NammaMart data dictionary', '',
            'Types are read from the actual ETL warehouse; pandas inference may change them with different inputs. Allowed values below are pipeline rules, not SQL constraints. PII=Yes includes linkable personal/transaction data, even when direct contact fields are redacted.', '',
            '## ETL fact and dimensions', '']
        for table in ['etl_fact_orders','etl_dim_customer','etl_dim_product','etl_dim_store']:
            dictionary += [f'### {table}', '', 'One current row per business key; ETL tables contain only accepted records.', '']
            rows=[]
            for column, dtype, *_ in etl.execute(f'DESCRIBE {table}').fetchall():
                meaning, origin, values = FIELDS[column]
                personal = table in {'etl_fact_orders','etl_dim_customer'} or column=='manager_name'
                pii = 'Yes — redacted' if column in {'full_name','email','phone','manager_name'} else ('Yes — linkable' if personal else 'No')
                rows.append((column,dtype,meaning,origin,values,pii))
            dictionary += md_table(['Column', 'Actual type', 'Meaning', 'Source', 'Allowed values / rule', 'PII'],rows)+['']
        dictionary += ['## ELT mapping and differences', '',
            '`stg_customers`, `stg_products`, `stg_stores` correspond to the ETL customer/product/store dimensions; `stg_orders` corresponds to the order source, and `mart_fact_orders` adds the derived fields described above. Staging retains FAIL records; the mart excludes them. Personal-data classifications are the same.', '',
            'ELT numeric source fields are DECIMAL(18,4), parsed dates are TIMESTAMP, order_date is DATE and within_15_min is BOOLEAN. Direct personal fields are VARCHAR with `[REDACTED]`. All raw source fields are VARCHAR without masking. Reconciliation, quality and lineage fields are described below.', '']
        metadata = [
            ('_loaded_at','TIMESTAMPTZ','Raw ingestion time','Ingestion metadata','Timestamp','No'),
            ('_source_file','VARCHAR','Originating CSV filename','Ingestion metadata','Known assignment filename','No'),
            ('_run_id','VARCHAR','Source ingestion run','Airflow run ID','Run identifier','No'),
            ('_batch_id','BIGINT','Unique source batch','ingestion_sequence','Join to ingestion_batches','No'),
            ('_row_number','BIGINT','1-based CSV data record','CSV read order','Positive integer','No'),
            ('dq_status','VARCHAR','Current quality outcome','SQL rules','PASS / WARN / FAIL','No'),
            ('failure_reason','VARCHAR','Critical rule names','SQL validation','Semicolon-separated; empty if none','No'),
            ('warning_reason','VARCHAR','Warning rule names','SQL validation','Semicolon-separated; empty if none','No'),
            ('_payload_hash','VARCHAR','Change-detection fingerprint','Normalised source row','MD5; not encryption or anonymisation','Yes — linkable for personal records'),
            ('payment_id / order_id','VARCHAR','Payment and order references','payments/orders CSV','Source business identifiers','Yes — linkable'),
            ('amount_paid / order_amount','DECIMAL(18,4)','Reconciliation amounts','payments/orders','Nullable if invalid or unavailable','Yes — linkable'),
            ('amount_difference','DECIMAL(18,4)','Paid minus order amount','Reconciliation calculation','Nullable when not quantifiable','Yes — linkable'),
        ]
        dictionary += md_table(['Column', 'Type', 'Meaning', 'Source', 'Allowed values / rule', 'PII'],metadata)+['',
            'Customer city/area/pincode and behaviour remain linkable through customer_id. Redaction reduces exposure but does not anonymise these tables. Product and store attributes become personal-context data when attached to an identifiable customer transaction.', '']
        for name, lines in [('DATA_QUALITY_GOVERNANCE_EVIDENCE.md',evidence),('DATA_QUALITY_RULES.md',catalog),('DATA_DICTIONARY.md',dictionary)]:
            (DOCS/name).write_text('\n'.join(lines),encoding='utf-8')
            print(f'Wrote docs/{name}')
    finally:
        for db in connections.values():
            db.close()


if __name__ == '__main__':
    export()
