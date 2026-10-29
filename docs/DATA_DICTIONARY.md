# NammaMart data dictionary

Types are read from the actual ETL warehouse; pandas inference may change them with different inputs. Allowed values below are pipeline rules, not SQL constraints. PII=Yes includes linkable personal/transaction data, even when direct contact fields are redacted.

## ETL fact and dimensions

### etl_fact_orders

One current row per business key; ETL tables contain only accepted records.

| Column | Actual type | Meaning | Source | Allowed values / rule | PII |
| --- | --- | --- | --- | --- | --- |
| order_id | VARCHAR | Order business key | orders.order_id | One accepted fact per key | Yes — linkable |
| order_ts | TIMESTAMP_NS | Order timestamp in local business time | orders.order_ts | Parseable; not future-dated at reference date | Yes — linkable |
| customer_id | VARCHAR | Linkable customer business key | customers/orders.customer_id | References accepted customer for facts | Yes — linkable |
| store_id | VARCHAR | Store business key | stores/orders.store_id | References accepted store for facts | Yes — linkable |
| product_id | VARCHAR | Product business key | products/orders.product_id | References accepted product for facts | Yes — linkable |
| quantity | BIGINT | Units ordered | orders.quantity | Positive whole number | Yes — linkable |
| unit_price | DOUBLE | Sale price per unit | orders.unit_price | > 0 | Yes — linkable |
| discount_pct | BIGINT | Percentage discount | orders.discount_pct | 0–100 | Yes — linkable |
| order_amount | DOUBLE | Net order value | orders.order_amount | Rounded quantity × unit_price × (1 − discount_pct/100) | Yes — linkable |
| payment_mode | VARCHAR | Payment method | orders.payment_mode | UPI / Card / Cash on Delivery / Wallet | Yes — linkable |
| order_status | VARCHAR | Current order state | orders.order_status | DELIVERED / CANCELLED / RETURNED | Yes — linkable |
| channel | VARCHAR | Ordering channel | orders.channel | Required text; enumeration not enforced | Yes — linkable |
| delivery_minutes | DOUBLE | Time to deliver | orders.delivery_minutes | Required when DELIVERED; 0 ≤ value < 120; unusual range warning | Yes — linkable |
| loyalty_tier | VARCHAR | Customer loyalty segment | customers.loyalty_tier | Uppercase; required; enumeration not enforced | Yes — linkable |
| category | VARCHAR | Product reporting category | products.category | Required text | Yes — linkable |
| cost_price | DOUBLE | Unit procurement cost | products.cost_price | 0 ≤ cost_price ≤ mrp | Yes — linkable |
| zone | VARCHAR | Store operational zone | stores.zone | North / South / East / West | Yes — linkable |
| order_date | DATE | Business date for revenue attribution | DATE(order_ts) | Date of the original order | Yes — linkable |
| net_revenue | DOUBLE | Revenue eligible for reporting | order_amount and order_status | Order amount if DELIVERED; otherwise 0 | Yes — linkable |
| gross_margin | DOUBLE | Revenue less cost of delivered goods | net_revenue − quantity × cost_price | Rounded to 2 decimals if DELIVERED; otherwise 0 | Yes — linkable |
| within_15_min | BOOLEAN | Delivered within 15 minutes | order_status and delivery_minutes | true / false | Yes — linkable |

### etl_dim_customer

One current row per business key; ETL tables contain only accepted records.

| Column | Actual type | Meaning | Source | Allowed values / rule | PII |
| --- | --- | --- | --- | --- | --- |
| customer_id | VARCHAR | Linkable customer business key | customers/orders.customer_id | References accepted customer for facts | Yes — linkable |
| full_name | VARCHAR | Customer name, redacted in reporting | customers.full_name | [REDACTED] | Yes — redacted |
| email | VARCHAR | Customer email, redacted in reporting | customers.email | [REDACTED] | Yes — redacted |
| phone | VARCHAR | Customer phone, redacted in reporting | customers.phone | [REDACTED] | Yes — redacted |
| city | VARCHAR | Customer city | customers.city | Optional text; missing-value warning | Yes — linkable |
| area | VARCHAR | Customer locality or store locality | customers.area / stores.area | Optional text; missing-value warning | Yes — linkable |
| pincode | VARCHAR | Postal code; stored as text | customers.pincode / stores.pincode | 6 digits expected; invalid format is Warning | Yes — linkable |
| signup_date | TIMESTAMP_NS | Customer registration date | customers.signup_date | Parseable; not future-dated | Yes — linkable |
| loyalty_tier | VARCHAR | Customer loyalty segment | customers.loyalty_tier | Uppercase; required; enumeration not enforced | Yes — linkable |
| is_active | VARCHAR | Customer activity flag | customers.is_active | Required text; enumeration not enforced | Yes — linkable |

### etl_dim_product

One current row per business key; ETL tables contain only accepted records.

| Column | Actual type | Meaning | Source | Allowed values / rule | PII |
| --- | --- | --- | --- | --- | --- |
| product_id | VARCHAR | Product business key | products/orders.product_id | References accepted product for facts | No |
| product_name | VARCHAR | Product display name | products.product_name | Required text | No |
| category | VARCHAR | Product reporting category | products.category | Required text | No |
| sub_category | VARCHAR | Product subcategory | products.sub_category | Required text | No |
| brand | VARCHAR | Product brand | products.brand | Required text | No |
| mrp | DOUBLE | Maximum retail price | products.mrp | > 0 | No |
| cost_price | DOUBLE | Unit procurement cost | products.cost_price | 0 ≤ cost_price ≤ mrp | No |
| unit | VARCHAR | Product unit of sale | products.unit | Required text | No |
| is_perishable | VARCHAR | Product perishability flag | products.is_perishable | Required text; not cast to Boolean currently | No |
| launch_date | TIMESTAMP_NS | Product launch date | products.launch_date | Parseable; not future-dated | No |

### etl_dim_store

One current row per business key; ETL tables contain only accepted records.

| Column | Actual type | Meaning | Source | Allowed values / rule | PII |
| --- | --- | --- | --- | --- | --- |
| store_id | VARCHAR | Store business key | stores/orders.store_id | References accepted store for facts | No |
| store_name | VARCHAR | Dark-store name | stores.store_name | Required text | No |
| zone | VARCHAR | Store operational zone | stores.zone | North / South / East / West | No |
| area | VARCHAR | Customer locality or store locality | customers.area / stores.area | Optional text; missing-value warning | No |
| pincode | VARCHAR | Postal code; stored as text | customers.pincode / stores.pincode | 6 digits expected; invalid format is Warning | No |
| open_date | TIMESTAMP_NS | Store opening date | stores.open_date | Parseable; not future-dated | No |
| manager_name | VARCHAR | Employee name, redacted in reporting | stores.manager_name | [REDACTED] | Yes — redacted |
| capacity_orders_per_day | BIGINT | Nominal store daily capacity | stores.capacity_orders_per_day | Positive whole number; volume comparison not yet implemented | No |

## ELT mapping and differences

`stg_customers`, `stg_products`, `stg_stores` correspond to the ETL customer/product/store dimensions; `stg_orders` corresponds to the order source, and `mart_fact_orders` adds the derived fields described above. Staging retains FAIL records; the mart excludes them. Personal-data classifications are the same.

ELT numeric source fields are DECIMAL(18,4), parsed dates are TIMESTAMP, order_date is DATE and within_15_min is BOOLEAN. Direct personal fields are VARCHAR with `[REDACTED]`. All raw source fields are VARCHAR without masking. Reconciliation, quality and lineage fields are described below.

| Column | Type | Meaning | Source | Allowed values / rule | PII |
| --- | --- | --- | --- | --- | --- |
| _loaded_at | TIMESTAMPTZ | Raw ingestion time | Ingestion metadata | Timestamp | No |
| _source_file | VARCHAR | Originating CSV filename | Ingestion metadata | Known assignment filename | No |
| _run_id | VARCHAR | Source ingestion run | Airflow run ID | Run identifier | No |
| _batch_id | BIGINT | Unique source batch | ingestion_sequence | Join to ingestion_batches | No |
| _row_number | BIGINT | 1-based CSV data record | CSV read order | Positive integer | No |
| dq_status | VARCHAR | Current quality outcome | SQL rules | PASS / WARN / FAIL | No |
| failure_reason | VARCHAR | Critical rule names | SQL validation | Semicolon-separated; empty if none | No |
| warning_reason | VARCHAR | Warning rule names | SQL validation | Semicolon-separated; empty if none | No |
| _payload_hash | VARCHAR | Change-detection fingerprint | Normalised source row | MD5; not encryption or anonymisation | Yes — linkable for personal records |
| payment_id / order_id | VARCHAR | Payment and order references | payments/orders CSV | Source business identifiers | Yes — linkable |
| amount_paid / order_amount | DECIMAL(18,4) | Reconciliation amounts | payments/orders | Nullable if invalid or unavailable | Yes — linkable |
| amount_difference | DECIMAL(18,4) | Paid minus order amount | Reconciliation calculation | Nullable when not quantifiable | Yes — linkable |

Customer city/area/pincode and behaviour remain linkable through customer_id. Redaction reduces exposure but does not anonymise these tables. Product and store attributes become personal-context data when attached to an identifiable customer transaction.
