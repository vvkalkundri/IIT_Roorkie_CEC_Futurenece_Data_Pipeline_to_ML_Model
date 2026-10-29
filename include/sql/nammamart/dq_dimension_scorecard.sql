-- Read-only scorecard, usable in EITHER warehouse. One row per run/dimension.
-- A failed rule is not the same as a failed pipeline or a rejected record.
WITH dimensions(dimension) AS (VALUES
 ('Completeness'), ('Uniqueness'), ('Validity'),
 ('Accuracy'), ('Consistency'), ('Timeliness')
)
SELECT p.run_id, p.dag_id, p.status AS pipeline_status, cast(p.end_time AS VARCHAR) AS end_time,
 d.dimension, count(q.check_name) AS checks_recorded,
 count(q.check_name) FILTER (WHERE q.severity='Critical' AND q.rows_failed>0) AS critical_checks_with_failures,
 count(q.check_name) FILTER (WHERE q.severity='Warning' AND q.rows_failed>0) AS warning_checks_with_failures,
 coalesce(sum(q.rows_checked),0) AS check_evaluations,
 coalesce(sum(q.rows_failed),0) AS failed_check_evaluations,
 CASE WHEN count(q.check_name)=0 THEN 'NOT_EVALUATED'
      WHEN count(q.check_name) FILTER(WHERE q.severity='Critical' AND q.rows_failed>0)>0 THEN 'CRITICAL_FINDINGS'
      WHEN count(q.check_name) FILTER(WHERE q.rows_failed>0)>0 THEN 'WARNINGS'
      ELSE 'PASS' END AS quality_result
FROM pipeline_runs p CROSS JOIN dimensions d
LEFT JOIN dq_results q ON q.run_id=p.run_id AND q.dag_id=p.dag_id AND q.dimension=d.dimension
GROUP BY p.run_id,p.dag_id,p.status,p.end_time,d.dimension
ORDER BY p.end_time DESC,d.dimension;
