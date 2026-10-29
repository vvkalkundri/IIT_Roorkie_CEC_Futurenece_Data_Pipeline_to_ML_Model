# ELT: business SQL and actual results

Warehouse: `include/warehouse_elt_vijayc5.duckdb`. Selected successful run: `scheduled__2026-10-29T03:30:00+00:00`. Audit end time: `2026-10-29 09:00:38.098361+05:30`.

Q1–Q5 revenue/delivery/spend cover September 2026 and only approved DELIVERED orders. Q4b covers all exceptions in the current reconciliation snapshot, including undated/orphan records; it is not a September-only ledger or a proven total loss. Unknown amounts remain unknown. Q6 means records rejected in the selected processing run, not orders whose business date is today. Reason counts overlap; use FILE TOTAL for distinct source records per file. Q1 includes zone subtotals and store rows: do not add both levels together.

## Q1 — Daily net revenue by zone and store

```sql
SELECT order_date, zone,
 CASE WHEN grouping(store_id)=1 THEN 'ZONE TOTAL' ELSE 'STORE' END AS level,
 store_id, round(sum(net_revenue),2) AS net_revenue
FROM mart_fact_orders
WHERE order_status='DELIVERED' AND order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'
GROUP BY GROUPING SETS ((order_date,zone),(order_date,zone,store_id))
ORDER BY order_date,zone,level,store_id;
```

Result: 500 rows.

| order_date | zone | level | store_id | net_revenue |
| --- | --- | --- | --- | --- |
| 2026-09-01 | East | STORE | S08 | 2984.70 |
| 2026-09-01 | East | STORE | S09 | 2089.60 |
| 2026-09-01 | East | STORE | S10 | 2141.60 |
| 2026-09-01 | East | STORE | S11 | 1757.15 |
| 2026-09-01 | East | ZONE TOTAL | NULL | 8973.05 |
| 2026-09-01 | North | STORE | S01 | 1410.80 |
| 2026-09-01 | North | STORE | S02 | 2385.55 |
| 2026-09-01 | North | STORE | S03 | 4178.80 |
| 2026-09-01 | North | ZONE TOTAL | NULL | 7975.15 |
| 2026-09-01 | South | STORE | S05 | 803.00 |
| 2026-09-01 | South | STORE | S06 | 2812.00 |
| 2026-09-01 | South | ZONE TOTAL | NULL | 3615.00 |
| 2026-09-01 | West | STORE | S13 | 1469.10 |
| 2026-09-01 | West | STORE | S14 | 1749.45 |
| 2026-09-01 | West | STORE | S15 | 925.20 |
| 2026-09-01 | West | ZONE TOTAL | NULL | 4143.75 |
| 2026-09-02 | East | STORE | S08 | 1019.60 |
| 2026-09-02 | East | STORE | S09 | 2944.90 |
| 2026-09-02 | East | STORE | S10 | 2996.90 |
| 2026-09-02 | East | STORE | S11 | 859.20 |
| 2026-09-02 | East | ZONE TOTAL | NULL | 7820.60 |
| 2026-09-02 | North | STORE | S01 | 1125.00 |
| 2026-09-02 | North | STORE | S02 | 889.20 |
| 2026-09-02 | North | STORE | S03 | 1559.60 |
| 2026-09-02 | North | ZONE TOTAL | NULL | 3573.80 |
| 2026-09-02 | South | STORE | S04 | 3867.10 |
| 2026-09-02 | South | STORE | S05 | 3759.50 |
| 2026-09-02 | South | STORE | S06 | 2038.80 |
| 2026-09-02 | South | ZONE TOTAL | NULL | 9665.40 |
| 2026-09-02 | West | STORE | S13 | 755.15 |
| 2026-09-02 | West | STORE | S14 | 3762.90 |
| 2026-09-02 | West | STORE | S15 | 3581.30 |
| 2026-09-02 | West | ZONE TOTAL | NULL | 8099.35 |
| 2026-09-03 | East | STORE | S08 | 1660.45 |
| 2026-09-03 | East | STORE | S09 | 2858.75 |
| 2026-09-03 | East | STORE | S10 | 1842.50 |
| 2026-09-03 | East | STORE | S11 | 5000.70 |
| 2026-09-03 | East | ZONE TOTAL | NULL | 11362.40 |
| 2026-09-03 | North | STORE | S01 | 2655.00 |
| 2026-09-03 | North | STORE | S02 | 6597.85 |
| 2026-09-03 | North | STORE | S03 | 4328.30 |
| 2026-09-03 | North | ZONE TOTAL | NULL | 13581.15 |
| 2026-09-03 | South | STORE | S04 | 138.60 |
| 2026-09-03 | South | STORE | S05 | 2693.00 |
| 2026-09-03 | South | STORE | S06 | 4646.80 |
| 2026-09-03 | South | ZONE TOTAL | NULL | 7478.40 |
| 2026-09-03 | West | STORE | S13 | 519.30 |
| 2026-09-03 | West | STORE | S14 | 4695.30 |
| 2026-09-03 | West | STORE | S15 | 3316.65 |
| 2026-09-03 | West | ZONE TOTAL | NULL | 8531.25 |
| 2026-09-04 | East | STORE | S08 | 1772.10 |
| 2026-09-04 | East | STORE | S09 | 1368.70 |
| 2026-09-04 | East | STORE | S10 | 2743.80 |
| 2026-09-04 | East | STORE | S11 | 3453.40 |
| 2026-09-04 | East | ZONE TOTAL | NULL | 9338.00 |
| 2026-09-04 | North | STORE | S01 | 427.00 |
| 2026-09-04 | North | STORE | S02 | 1026.40 |
| 2026-09-04 | North | STORE | S03 | 1094.40 |
| 2026-09-04 | North | ZONE TOTAL | NULL | 2547.80 |
| 2026-09-04 | South | STORE | S04 | 3335.30 |
| 2026-09-04 | South | STORE | S05 | 681.95 |
| 2026-09-04 | South | STORE | S06 | 298.80 |
| 2026-09-04 | South | ZONE TOTAL | NULL | 4316.05 |
| 2026-09-04 | West | STORE | S13 | 984.00 |
| 2026-09-04 | West | STORE | S14 | 4294.30 |
| 2026-09-04 | West | STORE | S15 | 1087.40 |
| 2026-09-04 | West | ZONE TOTAL | NULL | 6365.70 |
| 2026-09-05 | East | STORE | S08 | 1460.70 |
| 2026-09-05 | East | STORE | S09 | 3297.55 |
| 2026-09-05 | East | STORE | S10 | 416.00 |
| 2026-09-05 | East | STORE | S11 | 228.00 |
| 2026-09-05 | East | ZONE TOTAL | NULL | 5402.25 |
| 2026-09-05 | North | STORE | S01 | 1419.55 |
| 2026-09-05 | North | STORE | S02 | 184.45 |
| 2026-09-05 | North | STORE | S03 | 1123.05 |
| 2026-09-05 | North | ZONE TOTAL | NULL | 2727.05 |
| 2026-09-05 | South | STORE | S04 | 1286.40 |
| 2026-09-05 | South | STORE | S05 | 3292.00 |
| 2026-09-05 | South | STORE | S06 | 1211.00 |
| 2026-09-05 | South | ZONE TOTAL | NULL | 5789.40 |
| 2026-09-05 | West | STORE | S13 | 1973.20 |
| 2026-09-05 | West | STORE | S14 | 1239.10 |
| 2026-09-05 | West | STORE | S15 | 2093.05 |
| 2026-09-05 | West | ZONE TOTAL | NULL | 5305.35 |
| 2026-09-06 | East | STORE | S08 | 2418.20 |
| 2026-09-06 | East | STORE | S09 | 3148.40 |
| 2026-09-06 | East | STORE | S10 | 1650.15 |
| 2026-09-06 | East | STORE | S11 | 3322.40 |
| 2026-09-06 | East | ZONE TOTAL | NULL | 10539.15 |
| 2026-09-06 | North | STORE | S01 | 2333.80 |
| 2026-09-06 | North | STORE | S02 | 1013.70 |
| 2026-09-06 | North | STORE | S03 | 5448.40 |
| 2026-09-06 | North | ZONE TOTAL | NULL | 8795.90 |
| 2026-09-06 | South | STORE | S04 | 3080.65 |
| 2026-09-06 | South | STORE | S05 | 3585.00 |
| 2026-09-06 | South | STORE | S06 | 2630.40 |
| 2026-09-06 | South | ZONE TOTAL | NULL | 9296.05 |
| 2026-09-06 | West | STORE | S13 | 3087.00 |
| 2026-09-06 | West | STORE | S14 | 307.45 |
| 2026-09-06 | West | STORE | S15 | 8227.70 |
| 2026-09-06 | West | ZONE TOTAL | NULL | 11622.15 |
| 2026-09-07 | East | STORE | S08 | 1846.40 |
| 2026-09-07 | East | STORE | S10 | 2433.45 |
| 2026-09-07 | East | STORE | S11 | 824.00 |
| 2026-09-07 | East | ZONE TOTAL | NULL | 5103.85 |
| 2026-09-07 | North | STORE | S01 | 355.50 |
| 2026-09-07 | North | STORE | S02 | 492.00 |
| 2026-09-07 | North | STORE | S03 | 4380.40 |
| 2026-09-07 | North | ZONE TOTAL | NULL | 5227.90 |
| 2026-09-07 | South | STORE | S04 | 2169.20 |
| 2026-09-07 | South | STORE | S05 | 3542.55 |
| 2026-09-07 | South | STORE | S06 | 4557.65 |
| 2026-09-07 | South | ZONE TOTAL | NULL | 10269.40 |
| 2026-09-07 | West | STORE | S13 | 4869.10 |
| 2026-09-07 | West | STORE | S14 | 1632.55 |
| 2026-09-07 | West | STORE | S15 | 1750.90 |
| 2026-09-07 | West | ZONE TOTAL | NULL | 8252.55 |
| 2026-09-08 | East | STORE | S08 | 1187.85 |
| 2026-09-08 | East | STORE | S09 | 643.15 |
| 2026-09-08 | East | STORE | S10 | 358.40 |
| 2026-09-08 | East | STORE | S11 | 1378.35 |
| 2026-09-08 | East | ZONE TOTAL | NULL | 3567.75 |
| 2026-09-08 | North | STORE | S01 | 2062.20 |
| 2026-09-08 | North | STORE | S02 | 2816.65 |
| 2026-09-08 | North | STORE | S03 | 1327.80 |
| 2026-09-08 | North | ZONE TOTAL | NULL | 6206.65 |
| 2026-09-08 | South | STORE | S04 | 900.00 |
| 2026-09-08 | South | STORE | S05 | 2877.10 |
| 2026-09-08 | South | STORE | S06 | 3136.70 |
| 2026-09-08 | South | ZONE TOTAL | NULL | 6913.80 |
| 2026-09-08 | West | STORE | S13 | 825.65 |
| 2026-09-08 | West | STORE | S14 | 2000.30 |
| 2026-09-08 | West | STORE | S15 | 1906.05 |
| 2026-09-08 | West | ZONE TOTAL | NULL | 4732.00 |
| 2026-09-09 | East | STORE | S08 | 2912.50 |
| 2026-09-09 | East | STORE | S09 | 1569.85 |
| 2026-09-09 | East | STORE | S10 | 1818.20 |
| 2026-09-09 | East | STORE | S11 | 1452.45 |
| 2026-09-09 | East | ZONE TOTAL | NULL | 7753.00 |
| 2026-09-09 | North | STORE | S01 | 2014.00 |
| 2026-09-09 | North | STORE | S02 | 3922.95 |
| 2026-09-09 | North | ZONE TOTAL | NULL | 5936.95 |
| 2026-09-09 | South | STORE | S04 | 1204.70 |
| 2026-09-09 | South | STORE | S05 | 2035.45 |
| 2026-09-09 | South | STORE | S06 | 4084.80 |
| 2026-09-09 | South | ZONE TOTAL | NULL | 7324.95 |
| 2026-09-09 | West | STORE | S13 | 414.40 |
| 2026-09-09 | West | STORE | S14 | 2153.80 |
| 2026-09-09 | West | STORE | S15 | 3411.60 |
| 2026-09-09 | West | ZONE TOTAL | NULL | 5979.80 |
| 2026-09-10 | East | STORE | S08 | 3589.80 |
| 2026-09-10 | East | STORE | S09 | 1917.60 |
| 2026-09-10 | East | STORE | S10 | 2026.05 |
| 2026-09-10 | East | STORE | S11 | 2466.15 |
| 2026-09-10 | East | ZONE TOTAL | NULL | 9999.60 |
| 2026-09-10 | North | STORE | S01 | 4023.95 |
| 2026-09-10 | North | STORE | S02 | 3511.10 |
| 2026-09-10 | North | STORE | S03 | 6143.70 |
| 2026-09-10 | North | ZONE TOTAL | NULL | 13678.75 |
| 2026-09-10 | South | STORE | S04 | 856.60 |
| 2026-09-10 | South | STORE | S05 | 1015.80 |
| 2026-09-10 | South | ZONE TOTAL | NULL | 1872.40 |
| 2026-09-10 | West | STORE | S13 | 1750.40 |
| 2026-09-10 | West | STORE | S15 | 1519.60 |
| 2026-09-10 | West | ZONE TOTAL | NULL | 3270.00 |
| 2026-09-11 | East | STORE | S08 | 3830.95 |
| 2026-09-11 | East | STORE | S09 | 3679.90 |
| 2026-09-11 | East | STORE | S10 | 3619.15 |
| 2026-09-11 | East | STORE | S11 | 262.40 |
| 2026-09-11 | East | ZONE TOTAL | NULL | 11392.40 |
| 2026-09-11 | North | STORE | S01 | 688.00 |
| 2026-09-11 | North | STORE | S02 | 1772.70 |
| 2026-09-11 | North | STORE | S03 | 4035.75 |
| 2026-09-11 | North | ZONE TOTAL | NULL | 6496.45 |
| 2026-09-11 | South | STORE | S04 | 1127.65 |
| 2026-09-11 | South | STORE | S06 | 1392.50 |
| 2026-09-11 | South | ZONE TOTAL | NULL | 2520.15 |
| 2026-09-11 | West | STORE | S13 | 2404.00 |
| 2026-09-11 | West | STORE | S14 | 67.00 |
| 2026-09-11 | West | STORE | S15 | 2918.35 |
| 2026-09-11 | West | ZONE TOTAL | NULL | 5389.35 |
| 2026-09-12 | East | STORE | S08 | 1137.15 |
| 2026-09-12 | East | STORE | S09 | 4337.05 |
| 2026-09-12 | East | STORE | S10 | 394.00 |
| 2026-09-12 | East | STORE | S11 | 2494.20 |
| 2026-09-12 | East | ZONE TOTAL | NULL | 8362.40 |
| 2026-09-12 | North | STORE | S01 | 2037.50 |
| 2026-09-12 | North | STORE | S02 | 339.60 |
| 2026-09-12 | North | STORE | S03 | 2095.80 |
| 2026-09-12 | North | ZONE TOTAL | NULL | 4472.90 |
| 2026-09-12 | South | STORE | S04 | 2780.05 |
| 2026-09-12 | South | STORE | S05 | 1483.00 |
| 2026-09-12 | South | STORE | S06 | 1080.00 |
| 2026-09-12 | South | ZONE TOTAL | NULL | 5343.05 |
| 2026-09-12 | West | STORE | S13 | 5736.30 |
| 2026-09-12 | West | STORE | S14 | 2916.95 |
| 2026-09-12 | West | STORE | S15 | 5380.95 |
| 2026-09-12 | West | ZONE TOTAL | NULL | 14034.20 |
| 2026-09-13 | East | STORE | S08 | 5568.15 |
| 2026-09-13 | East | STORE | S09 | 2163.80 |
| 2026-09-13 | East | STORE | S10 | 1084.80 |
| 2026-09-13 | East | STORE | S11 | 4176.70 |
| 2026-09-13 | East | ZONE TOTAL | NULL | 12993.45 |
| 2026-09-13 | North | STORE | S01 | 2625.00 |
| 2026-09-13 | North | STORE | S02 | 1245.40 |
| 2026-09-13 | North | STORE | S03 | 1648.50 |
| 2026-09-13 | North | ZONE TOTAL | NULL | 5518.90 |
| 2026-09-13 | South | STORE | S04 | 3371.35 |
| 2026-09-13 | South | STORE | S05 | 3416.80 |
| 2026-09-13 | South | STORE | S06 | 341.00 |
| 2026-09-13 | South | ZONE TOTAL | NULL | 7129.15 |
| 2026-09-13 | West | STORE | S13 | 2486.00 |
| 2026-09-13 | West | STORE | S14 | 2737.00 |
| 2026-09-13 | West | STORE | S15 | 944.75 |
| 2026-09-13 | West | ZONE TOTAL | NULL | 6167.75 |
| 2026-09-14 | East | STORE | S08 | 836.40 |
| 2026-09-14 | East | STORE | S09 | 5531.70 |
| 2026-09-14 | East | STORE | S10 | 6544.90 |
| 2026-09-14 | East | STORE | S11 | 938.45 |
| 2026-09-14 | East | ZONE TOTAL | NULL | 13851.45 |
| 2026-09-14 | North | STORE | S01 | 3276.25 |
| 2026-09-14 | North | STORE | S02 | 2203.60 |
| 2026-09-14 | North | STORE | S03 | 2232.10 |
| 2026-09-14 | North | ZONE TOTAL | NULL | 7711.95 |
| 2026-09-14 | South | STORE | S04 | 1239.00 |
| 2026-09-14 | South | STORE | S05 | 1172.00 |
| 2026-09-14 | South | STORE | S06 | 1329.00 |
| 2026-09-14 | South | ZONE TOTAL | NULL | 3740.00 |
| 2026-09-14 | West | STORE | S13 | 3203.40 |
| 2026-09-14 | West | STORE | S14 | 645.20 |
| 2026-09-14 | West | STORE | S15 | 1605.00 |
| 2026-09-14 | West | ZONE TOTAL | NULL | 5453.60 |
| 2026-09-15 | East | STORE | S08 | 9.90 |
| 2026-09-15 | East | STORE | S09 | 3549.00 |
| 2026-09-15 | East | STORE | S10 | 984.30 |
| 2026-09-15 | East | STORE | S11 | 2470.80 |
| 2026-09-15 | East | ZONE TOTAL | NULL | 7014.00 |
| 2026-09-15 | North | STORE | S01 | 4583.05 |
| 2026-09-15 | North | STORE | S02 | 1630.30 |
| 2026-09-15 | North | STORE | S03 | 1787.80 |
| 2026-09-15 | North | ZONE TOTAL | NULL | 8001.15 |
| 2026-09-15 | South | STORE | S04 | 1882.00 |
| 2026-09-15 | South | STORE | S05 | 411.00 |
| 2026-09-15 | South | STORE | S06 | 1345.20 |
| 2026-09-15 | South | ZONE TOTAL | NULL | 3638.20 |
| 2026-09-15 | West | STORE | S13 | 1131.80 |
| 2026-09-15 | West | STORE | S14 | 3378.40 |
| 2026-09-15 | West | STORE | S15 | 1845.70 |
| 2026-09-15 | West | ZONE TOTAL | NULL | 6355.90 |
| 2026-09-16 | East | STORE | S08 | 2494.55 |
| 2026-09-16 | East | STORE | S09 | 2256.55 |
| 2026-09-16 | East | STORE | S10 | 3714.00 |
| 2026-09-16 | East | STORE | S11 | 2403.20 |
| 2026-09-16 | East | ZONE TOTAL | NULL | 10868.30 |
| 2026-09-16 | North | STORE | S01 | 1805.05 |
| 2026-09-16 | North | STORE | S02 | 2698.00 |
| 2026-09-16 | North | STORE | S03 | 2674.85 |
| 2026-09-16 | North | ZONE TOTAL | NULL | 7177.90 |
| 2026-09-16 | South | STORE | S04 | 1231.30 |
| 2026-09-16 | South | STORE | S05 | 2857.55 |
| 2026-09-16 | South | STORE | S06 | 6657.20 |
| 2026-09-16 | South | ZONE TOTAL | NULL | 10746.05 |
| 2026-09-16 | West | STORE | S13 | 1530.00 |
| 2026-09-16 | West | STORE | S14 | 2000.05 |
| 2026-09-16 | West | STORE | S15 | 873.90 |
| 2026-09-16 | West | ZONE TOTAL | NULL | 4403.95 |
| 2026-09-17 | East | STORE | S08 | 2178.20 |
| 2026-09-17 | East | STORE | S09 | 1686.90 |
| 2026-09-17 | East | STORE | S10 | 1584.90 |
| 2026-09-17 | East | STORE | S11 | 1550.25 |
| 2026-09-17 | East | ZONE TOTAL | NULL | 7000.25 |
| 2026-09-17 | North | STORE | S01 | 3614.60 |
| 2026-09-17 | North | STORE | S02 | 558.00 |
| 2026-09-17 | North | STORE | S03 | 2497.00 |
| 2026-09-17 | North | ZONE TOTAL | NULL | 6669.60 |
| 2026-09-17 | South | STORE | S04 | 2283.20 |
| 2026-09-17 | South | STORE | S05 | 1344.60 |
| 2026-09-17 | South | STORE | S06 | 5989.15 |
| 2026-09-17 | South | ZONE TOTAL | NULL | 9616.95 |
| 2026-09-17 | West | STORE | S13 | 3202.30 |
| 2026-09-17 | West | STORE | S14 | 3680.00 |
| 2026-09-17 | West | STORE | S15 | 3326.00 |
| 2026-09-17 | West | ZONE TOTAL | NULL | 10208.30 |
| 2026-09-18 | East | STORE | S08 | 2670.80 |
| 2026-09-18 | East | STORE | S09 | 9.00 |
| 2026-09-18 | East | STORE | S10 | 6683.00 |
| 2026-09-18 | East | STORE | S11 | 1973.80 |
| 2026-09-18 | East | ZONE TOTAL | NULL | 11336.60 |
| 2026-09-18 | North | STORE | S01 | 1684.60 |
| 2026-09-18 | North | STORE | S02 | 1559.70 |
| 2026-09-18 | North | STORE | S03 | 666.00 |
| 2026-09-18 | North | ZONE TOTAL | NULL | 3910.30 |
| 2026-09-18 | South | STORE | S04 | 896.00 |
| 2026-09-18 | South | STORE | S05 | 3661.20 |
| 2026-09-18 | South | STORE | S06 | 217.00 |
| 2026-09-18 | South | ZONE TOTAL | NULL | 4774.20 |
| 2026-09-18 | West | STORE | S13 | 2700.80 |
| 2026-09-18 | West | STORE | S14 | 2469.00 |
| 2026-09-18 | West | STORE | S15 | 1317.10 |
| 2026-09-18 | West | ZONE TOTAL | NULL | 6486.90 |
| 2026-09-19 | East | STORE | S08 | 1253.50 |
| 2026-09-19 | East | STORE | S09 | 1374.85 |
| 2026-09-19 | East | STORE | S10 | 1606.25 |
| 2026-09-19 | East | STORE | S11 | 2986.80 |
| 2026-09-19 | East | ZONE TOTAL | NULL | 7221.40 |
| 2026-09-19 | North | STORE | S01 | 4641.05 |
| 2026-09-19 | North | STORE | S02 | 9732.00 |
| 2026-09-19 | North | STORE | S03 | 2647.40 |
| 2026-09-19 | North | ZONE TOTAL | NULL | 17020.45 |
| 2026-09-19 | South | STORE | S04 | 1572.20 |
| 2026-09-19 | South | STORE | S05 | 2950.80 |
| 2026-09-19 | South | STORE | S06 | 2936.10 |
| 2026-09-19 | South | ZONE TOTAL | NULL | 7459.10 |
| 2026-09-19 | West | STORE | S13 | 7889.70 |
| 2026-09-19 | West | STORE | S14 | 5163.90 |
| 2026-09-19 | West | STORE | S15 | 3824.00 |
| 2026-09-19 | West | ZONE TOTAL | NULL | 16877.60 |
| 2026-09-20 | East | STORE | S08 | 2346.45 |
| 2026-09-20 | East | STORE | S09 | 933.25 |
| 2026-09-20 | East | STORE | S10 | 4258.60 |
| 2026-09-20 | East | STORE | S11 | 1882.65 |
| 2026-09-20 | East | ZONE TOTAL | NULL | 9420.95 |
| 2026-09-20 | North | STORE | S01 | 6060.40 |
| 2026-09-20 | North | STORE | S02 | 1357.20 |
| 2026-09-20 | North | STORE | S03 | 98.80 |
| 2026-09-20 | North | ZONE TOTAL | NULL | 7516.40 |
| 2026-09-20 | South | STORE | S04 | 2911.80 |
| 2026-09-20 | South | STORE | S05 | 4013.10 |
| 2026-09-20 | South | STORE | S06 | 578.00 |
| 2026-09-20 | South | ZONE TOTAL | NULL | 7502.90 |
| 2026-09-20 | West | STORE | S13 | 2535.00 |
| 2026-09-20 | West | STORE | S14 | 571.95 |
| 2026-09-20 | West | STORE | S15 | 1929.80 |
| 2026-09-20 | West | ZONE TOTAL | NULL | 5036.75 |
| 2026-09-21 | East | STORE | S08 | 2931.20 |
| 2026-09-21 | East | STORE | S09 | 1919.75 |
| 2026-09-21 | East | STORE | S10 | 3664.50 |
| 2026-09-21 | East | STORE | S11 | 230.00 |
| 2026-09-21 | East | ZONE TOTAL | NULL | 8745.45 |
| 2026-09-21 | North | STORE | S01 | 629.85 |
| 2026-09-21 | North | STORE | S02 | 1686.10 |
| 2026-09-21 | North | STORE | S03 | 1172.20 |
| 2026-09-21 | North | ZONE TOTAL | NULL | 3488.15 |
| 2026-09-21 | South | STORE | S04 | 2122.30 |
| 2026-09-21 | South | STORE | S05 | 1022.20 |
| 2026-09-21 | South | STORE | S06 | 2690.10 |
| 2026-09-21 | South | ZONE TOTAL | NULL | 5834.60 |
| 2026-09-21 | West | STORE | S13 | 1170.70 |
| 2026-09-21 | West | STORE | S14 | 799.50 |
| 2026-09-21 | West | STORE | S15 | 3578.05 |
| 2026-09-21 | West | ZONE TOTAL | NULL | 5548.25 |
| 2026-09-22 | East | STORE | S08 | 1896.55 |
| 2026-09-22 | East | STORE | S09 | 1509.60 |
| 2026-09-22 | East | STORE | S10 | 1646.45 |
| 2026-09-22 | East | STORE | S11 | 2095.85 |
| 2026-09-22 | East | ZONE TOTAL | NULL | 7148.45 |
| 2026-09-22 | North | STORE | S02 | 2942.75 |
| 2026-09-22 | North | STORE | S03 | 966.70 |
| 2026-09-22 | North | ZONE TOTAL | NULL | 3909.45 |
| 2026-09-22 | South | STORE | S04 | 759.80 |
| 2026-09-22 | South | STORE | S05 | 541.70 |
| 2026-09-22 | South | STORE | S06 | 1761.80 |
| 2026-09-22 | South | ZONE TOTAL | NULL | 3063.30 |
| 2026-09-22 | West | STORE | S13 | 1343.90 |
| 2026-09-22 | West | STORE | S14 | 2600.40 |
| 2026-09-22 | West | STORE | S15 | 413.70 |
| 2026-09-22 | West | ZONE TOTAL | NULL | 4358.00 |
| 2026-09-23 | East | STORE | S08 | 3685.40 |
| 2026-09-23 | East | STORE | S09 | 1037.20 |
| 2026-09-23 | East | STORE | S10 | 411.00 |
| 2026-09-23 | East | STORE | S11 | 672.30 |
| 2026-09-23 | East | ZONE TOTAL | NULL | 5805.90 |
| 2026-09-23 | North | STORE | S01 | 2255.40 |
| 2026-09-23 | North | STORE | S02 | 391.90 |
| 2026-09-23 | North | STORE | S03 | 1625.65 |
| 2026-09-23 | North | ZONE TOTAL | NULL | 4272.95 |
| 2026-09-23 | South | STORE | S04 | 2737.00 |
| 2026-09-23 | South | STORE | S05 | 2447.45 |
| 2026-09-23 | South | STORE | S06 | 2327.80 |
| 2026-09-23 | South | ZONE TOTAL | NULL | 7512.25 |
| 2026-09-23 | West | STORE | S13 | 2725.45 |
| 2026-09-23 | West | STORE | S14 | 3924.60 |
| 2026-09-23 | West | STORE | S15 | 733.30 |
| 2026-09-23 | West | ZONE TOTAL | NULL | 7383.35 |
| 2026-09-24 | East | STORE | S08 | 1185.00 |
| 2026-09-24 | East | STORE | S09 | 696.35 |
| 2026-09-24 | East | STORE | S10 | 2114.30 |
| 2026-09-24 | East | STORE | S11 | 1204.80 |
| 2026-09-24 | East | ZONE TOTAL | NULL | 5200.45 |
| 2026-09-24 | North | STORE | S01 | 2636.00 |
| 2026-09-24 | North | STORE | S02 | 3552.45 |
| 2026-09-24 | North | STORE | S03 | 675.75 |
| 2026-09-24 | North | ZONE TOTAL | NULL | 6864.20 |
| 2026-09-24 | South | STORE | S05 | 5233.70 |
| 2026-09-24 | South | STORE | S06 | 1817.00 |
| 2026-09-24 | South | ZONE TOTAL | NULL | 7050.70 |
| 2026-09-24 | West | STORE | S13 | 2085.85 |
| 2026-09-24 | West | STORE | S14 | 2599.80 |
| 2026-09-24 | West | STORE | S15 | 274.30 |
| 2026-09-24 | West | ZONE TOTAL | NULL | 4959.95 |
| 2026-09-25 | East | STORE | S08 | 1918.30 |
| 2026-09-25 | East | STORE | S09 | 1102.20 |
| 2026-09-25 | East | STORE | S10 | 3030.80 |
| 2026-09-25 | East | STORE | S11 | 633.15 |
| 2026-09-25 | East | ZONE TOTAL | NULL | 6684.45 |
| 2026-09-25 | North | STORE | S01 | 1040.15 |
| 2026-09-25 | North | STORE | S02 | 2578.45 |
| 2026-09-25 | North | ZONE TOTAL | NULL | 3618.60 |
| 2026-09-25 | South | STORE | S04 | 2920.00 |
| 2026-09-25 | South | STORE | S05 | 1076.00 |
| 2026-09-25 | South | STORE | S06 | 4602.65 |
| 2026-09-25 | South | ZONE TOTAL | NULL | 8598.65 |
| 2026-09-25 | West | STORE | S13 | 3164.20 |
| 2026-09-25 | West | STORE | S14 | 1922.95 |
| 2026-09-25 | West | STORE | S15 | 1197.00 |
| 2026-09-25 | West | ZONE TOTAL | NULL | 6284.15 |
| 2026-09-26 | East | STORE | S08 | 2621.55 |
| 2026-09-26 | East | STORE | S09 | 1018.15 |
| 2026-09-26 | East | STORE | S10 | 2908.40 |
| 2026-09-26 | East | STORE | S11 | 6688.10 |
| 2026-09-26 | East | ZONE TOTAL | NULL | 13236.20 |
| 2026-09-26 | North | STORE | S01 | 2495.40 |
| 2026-09-26 | North | STORE | S02 | 2358.15 |
| 2026-09-26 | North | STORE | S03 | 3854.75 |
| 2026-09-26 | North | ZONE TOTAL | NULL | 8708.30 |
| 2026-09-26 | South | STORE | S04 | 2081.10 |
| 2026-09-26 | South | STORE | S05 | 7751.20 |
| 2026-09-26 | South | STORE | S06 | 5680.40 |
| 2026-09-26 | South | ZONE TOTAL | NULL | 15512.70 |
| 2026-09-26 | West | STORE | S13 | 841.25 |
| 2026-09-26 | West | STORE | S14 | 923.30 |
| 2026-09-26 | West | STORE | S15 | 901.00 |
| 2026-09-26 | West | ZONE TOTAL | NULL | 2665.55 |
| 2026-09-27 | East | STORE | S08 | 4433.60 |
| 2026-09-27 | East | STORE | S09 | 1812.20 |
| 2026-09-27 | East | STORE | S10 | 2405.20 |
| 2026-09-27 | East | STORE | S11 | 1627.20 |
| 2026-09-27 | East | ZONE TOTAL | NULL | 10278.20 |
| 2026-09-27 | North | STORE | S01 | 865.55 |
| 2026-09-27 | North | STORE | S03 | 2189.20 |
| 2026-09-27 | North | ZONE TOTAL | NULL | 3054.75 |
| 2026-09-27 | South | STORE | S04 | 3110.30 |
| 2026-09-27 | South | STORE | S05 | 532.40 |
| 2026-09-27 | South | STORE | S06 | 2772.20 |
| 2026-09-27 | South | ZONE TOTAL | NULL | 6414.90 |
| 2026-09-27 | West | STORE | S13 | 2549.25 |
| 2026-09-27 | West | STORE | S14 | 2034.45 |
| 2026-09-27 | West | STORE | S15 | 3638.60 |
| 2026-09-27 | West | ZONE TOTAL | NULL | 8222.30 |
| 2026-09-28 | East | STORE | S08 | 1134.30 |
| 2026-09-28 | East | STORE | S09 | 727.20 |
| 2026-09-28 | East | STORE | S10 | 4400.00 |
| 2026-09-28 | East | STORE | S11 | 352.00 |
| 2026-09-28 | East | ZONE TOTAL | NULL | 6613.50 |
| 2026-09-28 | North | STORE | S01 | 4294.90 |
| 2026-09-28 | North | STORE | S02 | 1189.20 |
| 2026-09-28 | North | STORE | S03 | 1541.65 |
| 2026-09-28 | North | ZONE TOTAL | NULL | 7025.75 |
| 2026-09-28 | South | STORE | S04 | 1302.00 |
| 2026-09-28 | South | STORE | S05 | 575.60 |
| 2026-09-28 | South | STORE | S06 | 1054.90 |
| 2026-09-28 | South | ZONE TOTAL | NULL | 2932.50 |
| 2026-09-28 | West | STORE | S13 | 1108.20 |
| 2026-09-28 | West | STORE | S14 | 1768.60 |
| 2026-09-28 | West | STORE | S15 | 1127.25 |
| 2026-09-28 | West | ZONE TOTAL | NULL | 4004.05 |
| 2026-09-29 | East | STORE | S08 | 288.15 |
| 2026-09-29 | East | STORE | S09 | 4182.55 |
| 2026-09-29 | East | STORE | S10 | 1136.00 |
| 2026-09-29 | East | STORE | S11 | 2426.85 |
| 2026-09-29 | East | ZONE TOTAL | NULL | 8033.55 |
| 2026-09-29 | North | STORE | S01 | 3793.40 |
| 2026-09-29 | North | STORE | S02 | 3520.90 |
| 2026-09-29 | North | STORE | S03 | 3491.65 |
| 2026-09-29 | North | ZONE TOTAL | NULL | 10805.95 |
| 2026-09-29 | South | STORE | S04 | 6159.60 |
| 2026-09-29 | South | STORE | S05 | 3652.75 |
| 2026-09-29 | South | STORE | S06 | 992.00 |
| 2026-09-29 | South | ZONE TOTAL | NULL | 10804.35 |
| 2026-09-29 | West | STORE | S13 | 315.00 |
| 2026-09-29 | West | STORE | S14 | 637.30 |
| 2026-09-29 | West | STORE | S15 | 4746.45 |
| 2026-09-29 | West | ZONE TOTAL | NULL | 5698.75 |
| 2026-09-30 | East | STORE | S08 | 557.80 |
| 2026-09-30 | East | STORE | S09 | 52.25 |
| 2026-09-30 | East | STORE | S10 | 3073.70 |
| 2026-09-30 | East | STORE | S11 | 4858.80 |
| 2026-09-30 | East | ZONE TOTAL | NULL | 8542.55 |
| 2026-09-30 | North | STORE | S01 | 1976.00 |
| 2026-09-30 | North | STORE | S02 | 2206.40 |
| 2026-09-30 | North | STORE | S03 | 214.00 |
| 2026-09-30 | North | ZONE TOTAL | NULL | 4396.40 |
| 2026-09-30 | South | STORE | S04 | 1673.10 |
| 2026-09-30 | South | STORE | S05 | 3571.60 |
| 2026-09-30 | South | STORE | S06 | 2493.50 |
| 2026-09-30 | South | ZONE TOTAL | NULL | 7738.20 |
| 2026-09-30 | West | STORE | S13 | 1301.60 |
| 2026-09-30 | West | STORE | S14 | 582.45 |
| 2026-09-30 | West | STORE | S15 | 357.00 |
| 2026-09-30 | West | ZONE TOTAL | NULL | 2241.05 |

## Q2 — Revenue and gross margin by category

```sql
SELECT category, round(sum(net_revenue),2) AS net_revenue,
 round(sum(gross_margin),2) AS gross_margin
FROM mart_fact_orders WHERE order_status='DELIVERED' AND order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'
GROUP BY category ORDER BY category;
```

Result: 6 rows.

| category | net_revenue | gross_margin |
| --- | --- | --- |
| Dairy & Bakery | 136814.60 | 36645.32 |
| Fruits & Vegetables | 69231.60 | 16449.94 |
| Household | 153530.90 | 38284.44 |
| Personal Care | 165663.40 | 37572.18 |
| Snacks & Beverages | 141028.15 | 32531.22 |
| Staples | 196786.85 | 50745.39 |

## Q3 — Delivery time and percentage within 15 minutes

```sql
SELECT store_id, count(*) AS delivered_orders,
 round(avg(delivery_minutes),2) AS avg_delivery_minutes,
 round(100.0*count(*) FILTER(WHERE within_15_min)/nullif(count(*),0),2) AS pct_within_15_min
FROM mart_fact_orders WHERE order_status='DELIVERED' AND order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'
GROUP BY store_id ORDER BY store_id;
```

Result: 13 rows.

| store_id | delivered_orders | avg_delivery_minutes | pct_within_15_min |
| --- | --- | --- | --- |
| S01 | 125 | 20.7 | 30.4 |
| S02 | 120 | 21.37 | 28.33 |
| S03 | 119 | 21.29 | 27.73 |
| S04 | 111 | 21.66 | 26.13 |
| S05 | 117 | 21.41 | 29.91 |
| S06 | 123 | 22.05 | 24.39 |
| S08 | 130 | 20.55 | 36.15 |
| S09 | 116 | 21.22 | 29.31 |
| S10 | 123 | 21.82 | 27.64 |
| S11 | 119 | 21.51 | 26.05 |
| S13 | 120 | 21.75 | 28.33 |
| S14 | 141 | 21.72 | 30.5 |
| S15 | 131 | 22.47 | 20.61 |

## Q4a — Revenue by payment mode

```sql
SELECT payment_mode,round(sum(net_revenue),2) AS net_revenue
FROM mart_fact_orders WHERE order_status='DELIVERED' AND order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'
GROUP BY payment_mode ORDER BY payment_mode;
```

Result: 4 rows.

| payment_mode | net_revenue |
| --- | --- |
| Card | 175599.00 |
| Cash on Delivery | 113306.00 |
| UPI | 476538.55 |
| Wallet | 97611.95 |

## Q4b — Reconciliation amounts and unresolved exceptions

```sql
SELECT count(*) AS exception_rows,
 count(*) FILTER(WHERE order_amount IS NOT NULL AND amount_paid IS NOT NULL) AS quantifiable_rows,
 count(*) FILTER(WHERE order_amount IS NULL OR amount_paid IS NULL) AS unknown_amount_rows,
 round(sum(abs(amount_paid-order_amount)),2) AS known_absolute_difference,
 round(sum(amount_paid-order_amount),2) AS known_signed_difference
FROM mart_payment_reconciliation;
```

Result: 1 rows.

| exception_rows | quantifiable_rows | unknown_amount_rows | known_absolute_difference | known_signed_difference |
| --- | --- | --- | --- | --- |
| 696 | 192 | 504 | 100816.10 | -100816.10 |

## Q5 — Top ten customers by delivered-order spend

```sql
SELECT customer_id,loyalty_tier,round(sum(net_revenue),2) AS total_spend
FROM mart_fact_orders WHERE order_status='DELIVERED' AND order_date >= DATE '2026-09-01' AND order_date < DATE '2026-10-01'
GROUP BY customer_id,loyalty_tier
ORDER BY total_spend DESC,customer_id LIMIT 10;
```

Result: 10 rows.

| customer_id | loyalty_tier | total_spend |
| --- | --- | --- |
| C00310 | BRONZE | 7258.95 |
| C00072 | SILVER | 6393.95 |
| C00265 | GOLD | 6119.50 |
| C00236 | PLATINUM | 6105.80 |
| C00115 | BRONZE | 5783.70 |
| C00105 | GOLD | 5702.85 |
| C00135 | BRONZE | 5693.20 |
| C00163 | PLATINUM | 5671.50 |
| C00064 | BRONZE | 5609.25 |
| C00209 | PLATINUM | 5315.40 |

## Q6 — Rejected rows by file and reason for the selected run

```sql
WITH rejected AS (
SELECT source_file, failure_reason FROM quality_records WHERE evaluated_run_id='scheduled__2026-10-29T03:30:00+00:00' AND dq_status='FAIL'
), result AS (
 SELECT source_file,'FILE TOTAL (unique records)' AS reason,count(*) AS rejected_records
 FROM rejected GROUP BY source_file
 UNION ALL
 SELECT source_file,trim(reason) AS reason,count(*) AS rejected_records
 FROM rejected,unnest(string_split(failure_reason,';')) AS reasons(reason)
 WHERE trim(reason)<>'' GROUP BY source_file,trim(reason)
)
SELECT 'scheduled__2026-10-29T03:30:00+00:00' AS run_id,* FROM result ORDER BY source_file,reason;
```

Result: 41 rows.

| run_id | source_file | reason | rejected_records |
| --- | --- | --- | --- |
| scheduled__2026-10-29T03:30:00+00:00 | customers.csv | FILE TOTAL (unique records) | 13 |
| scheduled__2026-10-29T03:30:00+00:00 | customers.csv | conflicting_key | 10 |
| scheduled__2026-10-29T03:30:00+00:00 | customers.csv | signup_date:future | 3 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | FILE TOTAL (unique records) | 635 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | customer_id:invalid_reference | 65 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | customer_id:missing | 18 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | delivery:impossible | 6 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | delivery:missing | 8 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | discount:range | 3 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | exact_duplicate | 12 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | order_amount:formula | 18 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | order_amount:negative | 6 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | order_status:unknown | 3 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | order_ts:future | 5 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | order_ts:invalid_date | 5 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | order_ts:missing | 1 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | payment:unreconciled | 70 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | payment_mode:unknown | 3 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | product_id:invalid_reference | 170 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | quantity:nonpositive | 10 |
| scheduled__2026-10-29T03:30:00+00:00 | orders.csv | store_id:invalid_reference | 316 |
| scheduled__2026-10-29T03:30:00+00:00 | orders_2026-10-01_increment.csv | FILE TOTAL (unique records) | 154 |
| scheduled__2026-10-29T03:30:00+00:00 | orders_2026-10-01_increment.csv | customer_id:invalid_reference | 2 |
| scheduled__2026-10-29T03:30:00+00:00 | orders_2026-10-01_increment.csv | payment:unreconciled | 122 |
| scheduled__2026-10-29T03:30:00+00:00 | orders_2026-10-01_increment.csv | product_id:invalid_reference | 17 |
| scheduled__2026-10-29T03:30:00+00:00 | orders_2026-10-01_increment.csv | store_id:invalid_reference | 13 |
| scheduled__2026-10-29T03:30:00+00:00 | payments.csv | FILE TOTAL (unique records) | 26 |
| scheduled__2026-10-29T03:30:00+00:00 | payments.csv | amount_paid:negative | 6 |
| scheduled__2026-10-29T03:30:00+00:00 | payments.csv | exact_duplicate | 4 |
| scheduled__2026-10-29T03:30:00+00:00 | payments.csv | order_id:orphan | 8 |
| scheduled__2026-10-29T03:30:00+00:00 | payments.csv | payment_mode:unknown | 3 |
| scheduled__2026-10-29T03:30:00+00:00 | payments.csv | payment_ts:future | 5 |
| scheduled__2026-10-29T03:30:00+00:00 | products.csv | FILE TOTAL (unique records) | 12 |
| scheduled__2026-10-29T03:30:00+00:00 | products.csv | category:missing | 3 |
| scheduled__2026-10-29T03:30:00+00:00 | products.csv | conflicting_key | 4 |
| scheduled__2026-10-29T03:30:00+00:00 | products.csv | cost:above_mrp | 5 |
| scheduled__2026-10-29T03:30:00+00:00 | products.csv | mrp:nonpositive | 1 |
| scheduled__2026-10-29T03:30:00+00:00 | stores.csv | FILE TOTAL (unique records) | 2 |
| scheduled__2026-10-29T03:30:00+00:00 | stores.csv | capacity_orders_per_day:nonpositive | 1 |
| scheduled__2026-10-29T03:30:00+00:00 | stores.csv | zone:missing | 1 |
| scheduled__2026-10-29T03:30:00+00:00 | stores.csv | zone:unknown | 1 |

