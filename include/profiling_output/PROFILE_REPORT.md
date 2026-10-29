# NammaMart profiling report

Reference date (IST): 2026-10-24

Read-only discovery. Sources are never modified. All input fields are read as text;
numeric/date statistics use temporary parsed copies. Blank includes whitespace-only fields.
Reports omit raw personal values. Record numbers are 1-based data records, excluding the header.
Issue counts are findings, not rejected-row counts. A row can have multiple findings.

| File | Rows | Duplicate-key rows | Findings | Rows with findings |
| --- | ---: | ---: | ---: | ---: |
| orders.csv | 2412 | 24 | 203 | 187 |
| payments.csv | 2228 | 8 | 46 | 44 |
| customers.csv | 405 | 10 | 441 | 400 |
| products.csv | 152 | 4 | 13 | 12 |
| stores.csv | 15 | 0 | 2 | 2 |
| orders_2026-10-01_increment.csv | 160 | 0 | 1 | 0 |

## Findings by rule

| File | Column | Problem | Severity | Count |
| --- | --- | --- | --- | ---: |
| customers.csv | city | Missing value | Warning | 6 |
| customers.csv | customer_id | Repeated key within this file | Critical | 10 |
| customers.csv | email | Invalid format | Warning | 12 |
| customers.csv | loyalty_tier | Noncanonical casing | Warning | 400 |
| customers.csv | phone | Invalid format | Warning | 7 |
| customers.csv | pincode | Invalid format | Warning | 3 |
| customers.csv | signup_date | Date after reference date | Critical | 3 |
| orders.csv | customer_id | Missing value | Critical | 18 |
| orders.csv | delivery_minutes | Delivered order missing delivery time | Critical | 8 |
| orders.csv | delivery_minutes | Delivery at least 120 minutes | Critical | 6 |
| orders.csv | discount_pct | Discount outside 0–100 | Critical | 3 |
| orders.csv | order_amount | Amount differs from rounded quantity × price × (1 − discount/100) | Critical | 18 |
| orders.csv | order_amount | Negative value | Critical | 6 |
| orders.csv | order_id | Delivered order has no successful payment | Warning | 72 |
| orders.csv | order_id | Repeated key within this file | Critical | 24 |
| orders.csv | order_status | Noncanonical casing | Warning | 5 |
| orders.csv | order_status | Unrecognised category | Critical | 3 |
| orders.csv | order_ts | Date after reference date | Critical | 5 |
| orders.csv | order_ts | Missing value | Critical | 1 |
| orders.csv | order_ts | Unparseable date/timestamp | Critical | 5 |
| orders.csv | payment_mode | Surrounding whitespace | Warning | 2 |
| orders.csv | payment_mode | Unrecognised category | Critical | 3 |
| orders.csv | product_id | Reference missing from master | Critical | 9 |
| orders.csv | quantity | Must be positive | Critical | 10 |
| orders.csv | store_id | Reference missing from master | Critical | 5 |
| orders_2026-10-01_increment.csv | order_ts | Latest order is older than one day | Warning | 1 |
| payments.csv | amount_paid | Negative value | Critical | 6 |
| payments.csv | order_id/amount_paid | Payment references missing order | Critical | 8 |
| payments.csv | order_id/amount_paid | Successful payment differs from order amount | Critical | 14 |
| payments.csv | payment_id | Repeated key within this file | Critical | 8 |
| payments.csv | payment_mode | Surrounding whitespace | Warning | 2 |
| payments.csv | payment_mode | Unrecognised category | Critical | 3 |
| payments.csv | payment_ts | Date after reference date | Critical | 5 |
| products.csv | category | Missing value | Critical | 3 |
| products.csv | cost_price | Cost exceeds MRP | Critical | 5 |
| products.csv | mrp | Must be positive | Critical | 1 |
| products.csv | product_id | Repeated key within this file | Critical | 4 |
| stores.csv | capacity_orders_per_day | Must be positive | Critical | 1 |
| stores.csv | zone | Missing value | Critical | 1 |

## Assumptions and next steps

- Numeric/date ranges and original categorical frequencies are in profile_summary.json.
- data_issues.csv contains record keys, quality dimensions, proposed rules, and severity.
- Duplicate-key counts include all members, not just excess copies. Keys are trimmed for comparison.
- Money uses decimal arithmetic and ROUND_HALF_UP to two places; confirm this policy with finance.
- Future-date checks compare calendar dates; freshness uses the supplied reference date.
- Payments are compared individually to September orders. Refunds, multiple payments, and settlement timing need client policy.
- Increment overlaps are update candidates; this script does not apply updates.
- Required fields and severity are proposed rules, not an approved rejection policy.

## Questions for the client

1. Which record wins when duplicate keys contain conflicting values?
2. Should October returns restate September revenue or become October adjustments?
3. Should payment mismatches block finance reporting, and how should pending/COD payments be handled?
