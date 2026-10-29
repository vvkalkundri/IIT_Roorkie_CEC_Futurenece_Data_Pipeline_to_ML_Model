"""Local, snapshot-based ETL helpers. No Airflow dependency, so logic is testable."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from include.profile_nammamart import SCHEMAS, NUMERIC, DATES, ALLOWED, money

FILES = [name for name in SCHEMAS if 'increment' not in name]
DAG_ID = 'nammamart_etl_vijayc5'


def run_folder(root, run_id):
    return Path(root) / 'include' / 'etl_runs' / 'vijayc5' / hashlib.sha256(run_id.encode()).hexdigest()[:20]


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, default=str))
    temporary.replace(path)


def extract(root, run_id, name, include_increment=False):
    frame = pd.read_csv(Path(root) / 'include/data/nammamart' / name, dtype=str, keep_default_na=False)
    if list(frame.columns) != SCHEMAS[name]:
        raise ValueError(f'{name}: source schema differs from expected columns')
    folder = run_folder(root, run_id)
    folder.mkdir(parents=True, exist_ok=True)
    received = len(frame)
    if name == 'orders.csv':
        if type(include_increment) is not bool:
            raise ValueError('include_increment must be a boolean')
        state = Path(root) / 'include/etl_state/vijayc5/order_corrections.csv'
        prior = pd.read_csv(state, dtype=str, keep_default_na=False) if state.exists() else frame.iloc[:0].copy()
        effective = pd.concat([frame[~frame.order_id.str.strip().isin(prior.order_id.str.strip())], prior], ignore_index=True)
        inserted = changed = 0
        if include_increment:
            increment = pd.read_csv(Path(root) / 'include/data/nammamart/orders_2026-10-01_increment.csv', dtype=str, keep_default_na=False)
            if list(increment.columns) != SCHEMAS['orders.csv']:
                raise ValueError('Increment: source schema differs from expected columns')
            received += len(increment)
            for key, group in increment.groupby(increment.order_id.str.strip(), sort=False):
                old = effective[effective.order_id.str.strip().eq(key)]
                if old.empty:
                    inserted += 1
                elif old.reset_index(drop=True).to_dict('records') != group.reset_index(drop=True).to_dict('records'):
                    changed += 1
            prior = pd.concat([prior[~prior.order_id.str.strip().isin(increment.order_id.str.strip())], increment], ignore_index=True)
            effective = pd.concat([frame[~frame.order_id.str.strip().isin(prior.order_id.str.strip())], prior], ignore_index=True)
        prior.to_csv(folder / 'pending_corrections.csv', index=False)
        frame.to_csv(folder / 'orders_baseline_received.csv', index=False)
        frame = effective
        save_json(folder / 'increment.json', {'inserted': inserted, 'changed': changed})
    frame.to_csv(folder / name, index=False)
    save_json(folder / f'{name}.count.json', {'rows': received})
    print(f'{name}: extracted {len(frame)} rows')
    return {'file': name, 'rows': len(frame)}


def validate(root, run_id, as_of, dag_id=DAG_ID):
    """Normalise copies, quarantine critical failures, and retain raw failed rows."""
    from decimal import Decimal, ROUND_HALF_UP
    folder = run_folder(root, run_id)
    quarantine = Path(root) / 'include/quarantine/vijayc5'
    quarantine.mkdir(parents=True, exist_ok=True)
    frames = {name: pd.read_csv(folder / name, dtype=str, keep_default_na=False) for name in FILES}
    accepted, masks, reasons, checks = {}, {}, {}, []
    reference = pd.Timestamp(as_of).normalize()

    def check(name, label, dimension, bad, severity='Critical'):
        bad = pd.Series(bad, index=frames[name].index).fillna(False).astype(bool)
        checks.append({'run_id': run_id, 'dag_id': dag_id, 'check_name': f'{name}:{label}',
                       'dimension': dimension, 'severity': severity, 'rows_checked': len(bad),
                       'rows_failed': int(bad.sum()), 'status': 'FAIL' if bad.any() else 'PASS',
                       'checked_at': datetime.now(timezone.utc).isoformat()})
        if severity == 'Critical':
            masks[name] |= bad
            for index in bad.index[bad]:
                reasons[name][index].append(label)

    # Masters must be accepted before validating dependent order references.
    for name in ['customers.csv', 'products.csv', 'stores.csv', 'orders.csv', 'payments.csv']:
        raw = frames[name]
        data = raw.apply(lambda col: col.str.strip())
        masks[name] = pd.Series(False, index=raw.index)
        reasons[name] = {index: [] for index in raw.index}
        # A file-level volume check uses its last committed source count.
        history = Path(root) / 'include/etl_state/vijayc5/source_counts.json'
        previous = json.loads(history.read_text()).get(name) if history.exists() else None
        drop = previous is not None and len(raw) < previous * .1
        checks.append({'run_id': run_id, 'dag_id': dag_id, 'check_name': f'{name}:volume:drop_over_90pct',
                       'dimension': 'Completeness', 'severity': 'Warning', 'rows_checked': 1,
                       'rows_failed': int(drop), 'status': 'FAIL' if drop else 'PASS',
                       'checked_at': datetime.now(timezone.utc).isoformat()})
        for column in data:
            check(name, f'{column}:whitespace', 'Consistency', raw[column].ne(data[column]), 'Warning')
        for column in ['order_status', 'payment_status', 'loyalty_tier']:
            if column in data:
                check(name, f'{column}:casing', 'Consistency', data[column].ne(data[column].str.upper()), 'Warning')
                data[column] = data[column].str.upper()
        if 'payment_mode' in data:
            modes = {'UPI': 'UPI', 'CARD': 'Card', 'CASH ON DELIVERY': 'Cash on Delivery', 'WALLET': 'Wallet'}
            data['payment_mode'] = data.payment_mode.str.upper().map(modes).fillna(data.payment_mode)
        if 'zone' in data:
            data['zone'] = data.zone.str.title()
        key = data.columns[0]
        exact = data.duplicated(keep='first')
        unique_rows = data.drop_duplicates()
        conflicting = set(unique_rows.loc[unique_rows[key].duplicated(keep=False), key])
        check(name, 'exact_duplicate', 'Uniqueness', exact)
        check(name, 'conflicting_key', 'Uniqueness', data[key].isin(conflicting))
        for column in data:
            missing = data[column].eq('')
            if column not in {'delivery_minutes', 'gateway_ref'}:
                severity = 'Warning' if column in {'email', 'phone', 'full_name', 'manager_name', 'city', 'area', 'pincode'} else 'Critical'
                check(name, f'{column}:missing', 'Completeness', missing, severity)
            if column in NUMERIC:
                values = pd.to_numeric(data[column], errors='coerce')
                finite = values.notna() & values.ne(float('inf')) & values.ne(float('-inf'))
                check(name, f'{column}:invalid_number', 'Validity', ~missing & ~finite)
                if column in {'quantity', 'unit_price', 'mrp', 'capacity_orders_per_day'}:
                    check(name, f'{column}:nonpositive', 'Accuracy', finite & values.le(0))
                if column in {'cost_price', 'order_amount', 'amount_paid', 'delivery_minutes'}:
                    check(name, f'{column}:negative', 'Accuracy', finite & values.lt(0))
                if column in {'quantity', 'capacity_orders_per_day'}:
                    check(name, f'{column}:not_integer', 'Validity', finite & values.mod(1).ne(0))
                if column == 'discount_pct':
                    check(name, 'discount:range', 'Validity', finite & ~values.between(0, 100))
                if column == 'delivery_minutes':
                    check(name, 'delivery:impossible', 'Accuracy', finite & values.ge(120))
                    check(name, 'delivery:unusual', 'Accuracy', finite & ~values.between(8, 35), 'Warning')
            if column in DATES:
                fmt = '%Y-%m-%d %H:%M:%S' if column.endswith('_ts') else '%Y-%m-%d'
                dates = pd.to_datetime(data[column], format=fmt, errors='coerce')
                check(name, f'{column}:invalid_date', 'Validity', ~missing & dates.isna())
                check(name, f'{column}:future', 'Timeliness', dates.dt.normalize().gt(reference))
                if column == 'order_ts':
                    valid_dates = dates[dates.dt.normalize().le(reference)]
                    stale = valid_dates.empty or (reference - valid_dates.max().normalize()).days > 1
                    check(name, 'orders:stale', 'Timeliness', pd.Series(stale, index=data.index), 'Warning')
            if column in ALLOWED:
                check(name, f'{column}:unknown', 'Validity', ~data[column].str.upper().isin(ALLOWED[column]))
            if column in {'email', 'phone', 'pincode'}:
                pattern = {'email': r'[^\s@]+@[^\s@]+\.[^\s@]+', 'phone': r'[0-9]{10}', 'pincode': r'[0-9]{6}'}[column]
                check(name, f'{column}:format', 'Validity', ~missing & ~data[column].str.fullmatch(pattern), 'Warning')
        if name == 'products.csv':
            check(name, 'cost:above_mrp', 'Accuracy', pd.to_numeric(data.cost_price, errors='coerce').gt(pd.to_numeric(data.mrp, errors='coerce')))
        if name == 'orders.csv':
            check(name, 'delivery:missing', 'Completeness', data.order_status.eq('DELIVERED') & data.delivery_minutes.eq(''))
            for column, master in [('customer_id', 'customers.csv'), ('product_id', 'products.csv'), ('store_id', 'stores.csv')]:
                check(name, f'{column}:invalid_reference', 'Consistency', ~data[column].isin(accepted[master][column]))
            mismatch = []
            for row in data.itertuples(index=False):
                q, price, discount, amount = map(money, [row.quantity, row.unit_price, row.discount_pct, row.order_amount])
                mismatch.append(False if None in (q, price, discount, amount) else
                                (q * price * (1 - discount / 100)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP) != amount)
            check(name, 'order_amount:formula', 'Accuracy', mismatch)
        if name == 'payments.csv':
            check(name, 'order_id:orphan', 'Consistency', ~data.order_id.isin(frames['orders.csv'].order_id.str.strip()))
        accepted[name] = data.loc[~masks[name]].copy()

    # Strict initial finance policy: require exactly one accepted SUCCESS payment
    # for delivered orders. Missing/ambiguous settlement is held pending review.
    orders = accepted['orders.csv']
    payments = accepted['payments.csv']
    successes = payments[payments.payment_status.eq('SUCCESS')]
    reconciliation = []
    held = pd.Series(False, index=frames['orders.csv'].index)
    for index, order in orders.iterrows():
        group = successes[successes.order_id.eq(order.order_id)]
        reason = None
        if order.order_status == 'DELIVERED' and len(group) != 1:
            reason = 'Delivered order requires exactly one accepted successful payment'
        elif len(group) and any(money(v) != money(order.order_amount) for v in group.amount_paid):
            reason = 'Successful payment amount differs from order amount'
        if reason:
            held.loc[index] = True
            reconciliation.append({'order_id': order.order_id, 'payment_id': ','.join(group.payment_id),
                                   'reason': reason, 'order_amount': float(order.order_amount),
                                   'amount_paid': float(pd.to_numeric(group.amount_paid).sum())})
    check('orders.csv', 'payment:unreconciled', 'Consistency', held)
    for index in frames['payments.csv'].index[masks['payments.csv']]:
        row = frames['payments.csv'].loc[index]
        reconciliation.append({'order_id': row.order_id, 'payment_id': row.payment_id,
                               'reason': '; '.join(reasons['payments.csv'][index]), 'order_amount': None,
                               'amount_paid': None})
    for _, payment in successes.iterrows():
        if payment.order_id not in set(orders.order_id):
            reconciliation.append({'order_id': payment.order_id, 'payment_id': payment.payment_id,
                                   'reason': 'Payment has no quality-approved order', 'order_amount': None,
                                   'amount_paid': float(payment.amount_paid)})
    totals = {}
    for name in FILES:
        raw = frames[name]
        failed = raw.loc[masks[name]].copy()
        failed['failure_reason'] = ['; '.join(reasons[name][i]) for i in failed.index]
        failed.to_csv(quarantine / f'{Path(name).stem}_failed_{folder.name}.csv', index=False)
        good = accepted[name].loc[~masks[name].reindex(accepted[name].index)].copy()
        good.to_csv(folder / f'accepted_{name}', index=False)
        totals[name] = {'extracted': len(raw), 'accepted': len(good), 'quarantined': len(failed)}
        assert len(good) + len(failed) == len(raw)
        print(f'{name}: {totals[name]}')
    save_json(folder / 'counts.json', totals)
    save_json(folder / 'dq.json', checks)
    pd.DataFrame(reconciliation, columns=['order_id', 'payment_id', 'reason', 'order_amount', 'amount_paid']).to_csv(folder / 'reconciliation.csv', index=False)
    return totals


def transform(root, run_id):
    folder = run_folder(root, run_id)
    tables = {name: pd.read_csv(folder / f'accepted_{name}', dtype=str, keep_default_na=False) for name in FILES}
    for frame in tables.values():
        for column in set(frame.columns) & NUMERIC:
            frame[column] = pd.to_numeric(frame[column], errors='coerce')
        for column in set(frame.columns) & DATES:
            frame[column] = pd.to_datetime(frame[column], errors='coerce')
    customers = tables['customers.csv']
    # Full redaction is safe even for malformed personal values.
    for column in ['full_name', 'email', 'phone']:
        customers[column] = '[REDACTED]'
    stores = tables['stores.csv']
    stores['manager_name'] = '[REDACTED]'
    orders = tables['orders.csv'].merge(customers[['customer_id', 'loyalty_tier']], on='customer_id', validate='many_to_one')
    orders = orders.merge(tables['products.csv'][['product_id', 'category', 'cost_price']], on='product_id', validate='many_to_one')
    orders = orders.merge(stores[['store_id', 'zone']], on='store_id', validate='many_to_one')
    orders['order_date'] = orders.order_ts.dt.date
    orders['net_revenue'] = orders.order_amount.where(orders.order_status.eq('DELIVERED'), 0).round(2)
    orders['gross_margin'] = (orders.net_revenue - orders.quantity * orders.cost_price).where(orders.order_status.eq('DELIVERED'), 0).round(2)
    orders['within_15_min'] = orders.order_status.eq('DELIVERED') & orders.delivery_minutes.le(15)
    outputs = {'etl_fact_orders': orders, 'etl_dim_customer': customers,
               'etl_dim_product': tables['products.csv'], 'etl_dim_store': stores}
    # Pickles are private task intermediates produced only by this application.
    for name, frame in outputs.items():
        frame.to_pickle(folder / f'{name}.pkl')
    return {'fact_rows': len(orders)}


def load(root, run_id):
    folder = run_folder(root, run_id)
    with duckdb.connect(str(Path(root) / 'include/warehouse_vijayc5.duckdb')) as db:
        db.execute('BEGIN')
        for name in ['etl_dim_customer', 'etl_dim_product', 'etl_dim_store', 'etl_fact_orders']:
            frame = pd.read_pickle(folder / f'{name}.pkl')
            db.register('batch', frame)
            db.execute(f'CREATE OR REPLACE TABLE {name} AS SELECT * FROM batch')
        frame = pd.read_csv(folder / 'reconciliation.csv', dtype={'order_id': str, 'payment_id': str, 'reason': str})
        db.register('batch', frame)
        db.execute('CREATE OR REPLACE TABLE etl_payment_reconciliation AS SELECT * FROM batch')
        db.execute('CREATE OR REPLACE TABLE etl_daily_zone_revenue AS SELECT order_date, zone, round(sum(net_revenue), 2) AS net_revenue FROM etl_fact_orders GROUP BY ALL')
        db.execute('CREATE OR REPLACE TABLE etl_category_margin AS SELECT category, round(sum(net_revenue), 2) AS net_revenue, round(sum(gross_margin), 2) AS gross_margin FROM etl_fact_orders GROUP BY ALL')
        db.execute('COMMIT')
        stats = json.loads((folder / 'increment.json').read_text()) if (folder / 'increment.json').exists() else {'inserted': 0, 'changed': 0}
        db.execute('CREATE TABLE IF NOT EXISTS incremental_results (run_id VARCHAR PRIMARY KEY, inserted_orders BIGINT, changed_orders BIGINT)')
        db.execute('INSERT OR REPLACE INTO incremental_results VALUES (?, ?, ?)', [run_id, stats['inserted'], stats['changed']])
        for name in ['etl_daily_zone_revenue', 'etl_category_margin']:
            print(name, db.sql(f'SELECT * FROM {name}').df().to_string(index=False))
    state = Path(root) / 'include/etl_state/vijayc5'
    state.mkdir(parents=True, exist_ok=True)
    if (folder / 'pending_corrections.csv').exists():
        temporary = state / 'order_corrections.tmp'
        temporary.write_bytes((folder / 'pending_corrections.csv').read_bytes())
        temporary.replace(state / 'order_corrections.csv')
    counts = json.loads((folder / 'counts.json').read_text())
    save_json(state / 'source_counts.json', {name: count['extracted'] for name, count in counts.items()})
    save_json(folder / 'loaded.json', {'success': True})


def audit(root, run_id, started_at, success, dag_id=DAG_ID):
    folder = run_folder(root, run_id)
    counts = json.loads((folder / 'counts.json').read_text()) if (folder / 'counts.json').exists() else {}
    extracted = sum(json.loads(p.read_text())['rows'] for p in folder.glob('*.count.json'))
    row = pd.DataFrame([{'run_id': run_id, 'dag_id': dag_id, 'start_time': str(started_at),
                         'end_time': datetime.now(timezone.utc).isoformat(), 'rows_extracted': extracted,
                         'rows_loaded': counts.get('orders.csv', {}).get('accepted', 0) if success else 0,
                         'rows_quarantined': sum(c['quarantined'] for c in counts.values()),
                         'status': 'SUCCESS' if success else 'FAILED'}])
    with duckdb.connect(str(Path(root) / 'include/warehouse_vijayc5.duckdb')) as db:
        db.register('audit_row', row)
        db.execute('CREATE TABLE IF NOT EXISTS pipeline_runs AS SELECT * FROM audit_row WHERE false')
        db.execute('DELETE FROM pipeline_runs WHERE run_id = ? AND dag_id = ?', [run_id, dag_id])
        db.execute('INSERT INTO pipeline_runs SELECT * FROM audit_row')
        if (folder / 'dq.json').exists():
            checks = pd.DataFrame(json.loads((folder / 'dq.json').read_text()))
            db.register('checks', checks)
            db.execute('CREATE TABLE IF NOT EXISTS dq_results AS SELECT * FROM checks WHERE false')
            db.execute('DELETE FROM dq_results WHERE run_id = ? AND dag_id = ?', [run_id, dag_id])
            db.execute('INSERT INTO dq_results SELECT * FROM checks')
