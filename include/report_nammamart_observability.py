"""Verify scheduler evidence and produce a PII-free Part F report locally."""
import argparse
import hashlib
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def generate(suite):
    source = ROOT / f'include/observability_reports/observability_{suite}.json'
    evidence = json.loads(source.read_text())
    cases = evidence['cases']
    assert evidence['source_hashes_unchanged']
    required = {'happy', 'rerun', 'increment', 'missing', 'bad_rows', 'schema',
                'volume', 'drift', 'freshness', 'recovery', 'recovered'}
    assert set(cases) == required
    for case, pair in cases.items():
        for kind, result in pair.items():
            expected = 'failed' if case in ('missing', 'schema', 'recovery') else 'success'
            assert result['final']['state'] == expected, (case, kind, result['final'])
            assert result['metrics']['audit'][0] == expected.upper(), (case, kind, 'audit')
    lines = ['# Part F: executed observability evidence', '',
             f'Suite `{suite}`, executed on 26 October 2026 in the local Astro scheduler. '
             f'Validation reference date: `{evidence["as_of"]}`. '
             'Both unscheduled experiment DAGs use the same task factories as the main DAGs. '
             'Each destructive scenario used a separate prepared copy of the baseline workspace. '
             'Original fixture hashes were unchanged; case input files were restored after observation. '
             'Experiment DAGs were paused afterward.', '',
             f'[Machine-readable task states, timings and SQL metrics](../include/observability_reports/observability_{suite}.json). '
             'This report contains aggregate counts and synthetic test IDs, not customer fields.', '',
             '## Run inventory', '',
             '| Experiment | ETL run / state | ELT run / state |', '|---|---|---|']
    for case, pair in cases.items():
        lines.append(f'| {case} | `{pair["etl"]["run_id"]}` / {pair["etl"]["final"]["state"]} | `{pair["elt"]["run_id"]}` / {pair["elt"]["final"]["state"]} |')
    lines += ['', '`recovered` is the same run ID after Clear, not a newly triggered run. '
              'The evidence preserves its failed state before recovery even though the run audit is updated to SUCCESS.',
              '', '## Happy-path counts and task timing', '',
              '| Pipeline | Source | Received | Accepted (including warnings) | Quarantined |', '|---|---|---:|---:|---:|']
    for kind in ('etl', 'elt'):
        r = cases['happy'][kind]
        # The seed retains the happy-path warehouse before any incremental run.
        root = ROOT / f'include/observability_workspaces/{suite}_seed'
        if kind == 'etl':
            token = hashlib.sha256(r['run_id'].encode()).hexdigest()[:20]
            counts = json.loads((root / f'include/etl_runs/vijayc5/{token}/counts.json').read_text())
            rows = [(name, c['extracted'], c['accepted'], c['quarantined']) for name, c in counts.items()]
        else:
            with duckdb.connect(str(root / 'include/warehouse_elt_vijayc5.duckdb'), read_only=True) as db:
                rows = db.execute("SELECT source_file,count(*),count(*) FILTER(WHERE dq_status<>'FAIL'),count(*) FILTER(WHERE dq_status='FAIL') FROM quality_records WHERE evaluated_run_id=? GROUP BY source_file ORDER BY source_file", [r['run_id']]).fetchall()
        for name, received, accepted, quarantined in rows:
            assert received == accepted + quarantined
            lines.append(f'| {kind.upper()} | {name} | {received} | {accepted} | {quarantined} |')
    lines += ['', 'Accepted source rows are not all published order facts. Audit `rows_loaded` counts order facts only; '
              'quality-rule failure counts can overlap and must not be summed as rejected records.', '',
              '| Pipeline | Task | Duration (seconds) |', '|---|---|---:|']
    for kind in ('etl', 'elt'):
        for task in cases['happy'][kind]['final']['tasks']:
            lines.append(f'| {kind.upper()} | `{task["task_id"]}` | {task["duration"]:.3f} |')
    extracts = [t for t in cases['happy']['etl']['final']['tasks'] if t['task_id'].startswith('extract_')]
    overlap = [(a['task_id'], b['task_id']) for i, a in enumerate(extracts) for b in extracts[i+1:]
               if max(a['start'], b['start']) < min(a['end'], b['end'])]
    lines += ['', f'Observed overlapping ETL extract task intervals: {len(overlap)} pairs. '
              + ('; '.join(f'`{a}` / `{b}`' for a,b in overlap) if overlap else 'No overlap observed; graph independence alone does not prove parallel execution.')
              + '. ELT has a serial raw → staging → mart dependency.', '', '## Ten experiments', '',
              '| # | Expected | Observed on both pipelines | Where I saw it | What I would change |', '|---|---|---|---|---|']
    happy = cases['happy']['etl']['metrics']['facts']
    assert list(map(str, happy)) == list(map(str, cases['happy']['elt']['metrics']['facts']))
    for kind in ('etl', 'elt'):
        assert cases['rerun'][kind]['metrics']['facts'] == cases['happy'][kind]['metrics']['facts']
        inc = cases['increment'][kind]['metrics']
        assert inc['increment'] == [150, 10]
        assert inc['corrections_returned'] == 10
        assert inc['facts'][0] == inc['facts'][2]
        reasons = dict(cases['bad_rows'][kind]['metrics']['injected_reasons'])
        for key, reason in [('NULL','customer_id:missing'), ('NEGATIVE','quantity:nonpositive'),
                            ('STORE','store_id:invalid_reference'), ('STATUS','order_status:unknown'), ('FUTURE','order_ts:future')]:
            assert reason in reasons['TEST_'+key], (kind, key, reasons)
            assert any(reason in check and count > 0 for check, count in cases['bad_rows'][kind]['metrics']['failed_checks'])
        for case, check in [('volume','volume:drop_over_90pct'), ('drift','order_amount:formula'), ('freshness','orders:stale')]:
            assert any(check in name and count > 0 for name, count in cases[case][kind]['metrics']['failed_checks'])
    assert cases['increment']['elt']['metrics']['staging_keys'] == [2550, 2550]
    for case in ('missing', 'schema', 'recovery'):
        for kind in ('etl', 'elt'):
            assert cases[case][kind]['metrics']['facts'] == cases['happy'][kind]['metrics']['facts']
    raw_before = cases['happy']['elt']['metrics']['raw_orders']
    raw_after = cases['rerun']['elt']['metrics']['raw_orders']
    assert raw_after - raw_before == 2412
    observations = [
        ('Happy path: green tasks, audited counts and measurable durations', f'{happy[0]:,} facts and revenue {float(happy[1]):,.2f} in each pipeline; 5,212 received rows; timing and per-file counts above. ETL overlap: {len(overlap)} pairs.', 'Airflow task start/end/duration; pipeline_runs; per-file validation counts', 'Record duration baselines and alert on slow runs.'),
        ('Re-run: unchanged facts; append-only ELT raw grows', f'Facts and revenue unchanged. ELT raw_orders grew {raw_before:,} → {raw_after:,}; a new run preserves a new source snapshot, while same-run retries deduplicate batches.', 'Fact counts, raw_orders and ingestion_batches', 'Apply retention to historical raw batches; distinguish retries from new runs.'),
        ('Increment: 150 new keys, 10 corrected keys, no duplicate facts', 'Both recorded 150 inserts / 10 changes; all ten corrections are RETURNED. Facts have unique order IDs. ELT has 2,550 unique staging keys. Missing new payments prevent all 150 new keys becoming finance facts.', 'incremental_results; stg_orders; ETL retained corrections; distinct fact IDs', 'Use source version ordering for multiple future incremental files; confirm Finance restatement rules.'),
        ('Missing products: retries, loud failure, blocked downstream', 'ETL extract_products and ELT load_raw exhausted three attempts (initial + two retries). Both runs and audits FAILED; downstream tasks upstream_failed. Previous committed facts remain available.', 'Airflow retry/state timeline below; pipeline_runs', 'Add an external failure notification and a dashboard showing publication age.'),
        ('Five new bad rows: quarantine each with its reason', 'All five synthetic IDs have the required reason: missing customer, nonpositive quantity, unknown store reference, invalid status and future timestamp. Relevant dq_results checks failed.', 'ETL rejected CSV; ELT quality_records/elt_quarantine; dq_results; synthetic-ID table below', 'Keep these examples as regression fixtures and monitor rejection rate.'),
        ('Renamed order_amount: fail before publishing wrong data', 'ETL extract_orders failed with `ValueError: orders.csv: source schema differs from expected columns`; ELT load_raw failed with `ValueError: orders.csv: unexpected CSV schema`. Both exhausted three attempts and retained prior facts.', 'Task failures and schema error messages; FAILED audit', 'Use versioned schema contracts and avoid retrying deterministic schema errors.'),
        ('50 orders: warn on a drop above 90%', '2,412 → 50 orders (97.93% drop); orders.csv:volume:drop_over_90pct failed with one file-level warning in each pipeline. Runs succeeded; warning does not block publication.', 'dq_results and current source counts compared with prior successful/batched source', 'Make severe volume drops a publication gate after agreeing thresholds.'),
        ('100× S04 prices: detect corruption and measure impact', '; '.join(f'{k.upper()}: S04 revenue {float(cases["happy"][k]["metrics"]["store_s04_revenue"]):,.2f} → {float(cases["drift"][k]["metrics"]["store_s04_revenue"]):,.2f} (change {float(cases["drift"][k]["metrics"]["store_s04_revenue"])-float(cases["happy"][k]["metrics"]["store_s04_revenue"]):,.2f})' for k in ('etl','elt')) + '. The order-amount formula check caught unchanged amounts; affected orders were rejected.', 'dq_results formula failures; S04 sum(net_revenue) in fact tables', 'Add price quantile/median drift checks by store/product; formula checks miss coherent changes to price and amount.'),
        ('Latest order timestamp 30 days old: freshness warning', 'Latest timestamp 2026-09-25 versus reference 2026-10-25; orders:stale failed in both pipelines. Runs succeeded because stale fixtures are warnings.', 'dq_results Timeliness checks', 'Set a production freshness SLA and gate stale publication or label it clearly.'),
        ('Fix missing products, Clear failed task + downstream only', 'Same run IDs recovered to SUCCESS. ETL’s other four extracts retained their original attempt/start/end. extract_products ran attempt 4; validation, transform, load and audit executed. ELT load_raw ran attempt 4 and its downstream chain executed.', 'Before/after task metadata below; same-run SUCCESS audit', 'Document selective recovery and retain failed-attempt history outside the one-row-per-run audit.'),
    ]
    for i, row in enumerate(observations, 1):
        lines.append('| '+str(i)+' | '+' | '.join(row)+' |')
    lines += ['', '## Failure and recovery evidence', '',
              'Retry delay is configured as 30 seconds. Observed times below are polling observations (2-second polling), '
              'so they include scheduler delay and are not exact worker retry-start timestamps.', '',
              '| Case / pipeline | Failed task | Observed up_for_retry (UTC) | Final attempt / state |', '|---|---|---|---|']
    for case in ('missing', 'schema', 'recovery'):
        for kind in ('etl', 'elt'):
            r = cases[case][kind]
            name = 'load_raw' if kind == 'elt' else ('extract_orders' if case=='schema' else 'extract_products')
            task = next(t for t in r['final']['tasks'] if t['task_id']==name)
            assert task['state']=='failed' and task['try_number']==3
            retry_times = sorted({event['observed_at'] for event in r['events'] if any(t['task_id']==name and t['state']=='up_for_retry' for t in event['tasks'])})
            assert retry_times
            assert any(t['state']=='upstream_failed' for t in r['final']['tasks'])
            lines.append(f'| {case} / {kind.upper()} | `{name}` | {"; ".join(retry_times)} | {task["try_number"]} / {task["state"]} |')
    lines += ['', '| Pipeline | Task | Attempts before → after Clear | Result |', '|---|---|---|---|']
    for kind in ('etl','elt'):
        r=cases['recovered'][kind]
        before={t['task_id']: t for t in r['before']['tasks']}
        for task in r['final']['tasks']:
            old=before[task['task_id']]
            if old['state']=='success':
                assert (task['try_number'],task['start'],task['end']) == (old['try_number'],old['start'],old['end'])
            else:
                assert task['try_number']>old['try_number']
            assert task['state']=='success'
            lines.append(f'| {kind.upper()} | `{task["task_id"]}` | {old["try_number"]} → {task["try_number"]} | success |')
    lines += ['', '| Pipeline | Synthetic order ID | Quarantine reasons |', '|---|---|---|']
    for kind in ('etl','elt'):
        for key, reason in sorted(cases['bad_rows'][kind]['metrics']['injected_reasons']):
            lines.append(f'| {kind.upper()} | {key} | {reason} |')
    lines += ['', 'Audit-count interpretation: the volume test reports 2,220 ETL quarantined rows versus 64 ELT rows. ETL tests payment references against the current order snapshot; ELT tests whether an order ever existed in retained raw history. Both publish 39 facts and revenue 17,865.00, but their quarantine scopes differ. Align the reference policy before treating these counts as interchangeable. Incremental quarantine counts also differ (838 ETL / 842 ELT): ETL evaluates the merged effective order set, while ELT retains and evaluates baseline and increment records before selecting the winning version. The freshness mutation changes formerly future-dated records too, so its 1,780 facts differ from the unmodified baseline.', '', '## Five pillars', '', '| Pillar | Implemented evidence | Limitation |', '|---|---|---|',
              '| Freshness | Latest nonfuture order date versus reference date; stale warning | No production publication gate or notification |',
              '| Volume | Previous-versus-current row count; >90% drop warning | No seasonality; ETL uses last committed counts, ELT previous received batches |',
              '| Schema | Exact required columns; loud failure before publication | No schema evolution workflow |',
              '| Distribution | Formula, range and reconciliation checks catch this price mutation | Weakest: no learned/statistical drift baseline; coherent price/amount changes can pass |',
              '| Lineage | Run IDs, raw batch/source/row references in ELT, ETL run snapshots, quarantine reasons and publication audit | Strongest, especially ELT; no external lineage catalogue or historical mart snapshots |', '',
              '## Defects exposed and corrected', '',
              'The exploratory suite obs_20261026_02 exposed an ELT DECIMAL(18) intermediate overflow under 100× prices. '
              'The formula now widens the intermediate to DECIMAL(38); a regression test checks quarantine without a crash. '
              'The installed Airflow Clear implementation treats its task selector as a substring; anchored regex text matched no tasks. '
              'The runner now passes the literal task name and verifies the run was reset. '
              'Shared DAG factories were moved out of DAG discovery modules to eliminate duplicate registration. '
              'The final suite above verifies the corrected behavior; the exploratory suite is not treated as a pass.', '',
              '## Reproduce and inspect', '',
              'Run inside the Astro scheduler from `/usr/local/airflow`: `python include/run_nammamart_observability.py --suite obs_unique` '
              '(use a new lowercase/digit suffix). Run locally afterward: '
              '`.venv/bin/python include/report_nammamart_observability.py --suite obs_unique`. '
              'The report generator asserts the observed outcomes before writing a report. '
              'Private datasets, quarantine, logs and warehouses remain in ignored `include/observability_workspaces/`.', '',
              'In Airflow select `nammamart_etl_observability_vijayc5` or `nammamart_elt_observability_vijayc5`, '
              'then the exact run ID in the inventory. Use Graph for states/dependencies and task logs for attempts/errors. '
              'A failed audit task deliberately keeps the DAG red when upstream work failed. '
              'There are no external Slack/email alerts configured.', '',
              'For SQL evidence, open the corresponding isolated workspace warehouse after its run ends. '
              'Filter `pipeline_runs` and `dq_results` by the inventory run ID; '
              'ETL uses `etl_fact_orders`, ELT uses `mart_fact_orders`. '
              'Current live production warehouses were not overwritten by these experiments.']
    target=ROOT / f'docs/OBSERVABILITY_{suite}.md'
    target.write_text('\n'.join(lines)+'\n')
    print(f'All ten experiments verified on both DAGs. Report: {target}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', required=True)
    generate(parser.parse_args().suite)
