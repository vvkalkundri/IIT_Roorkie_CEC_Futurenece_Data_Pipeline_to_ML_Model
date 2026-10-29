"""Part 0: read-only profiling of all six NammaMart assignment exports.

Run from the project root:
    python include/profile_nammamart.py
    python include/profile_nammamart.py --as-of 2026-10-02
    python include/profile_nammamart.py --data-dir include/data/nammamart

Outputs: profile_summary.json, data_issues.csv, and PROFILE_REPORT.md.
Issue counts count findings, not rejected rows. This script does not clean,
quarantine, or load data. Proposed rules/severities need client agreement.
"""

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ORDER_COLUMNS = "order_id order_ts customer_id store_id product_id quantity unit_price discount_pct order_amount payment_mode order_status channel delivery_minutes"
SCHEMAS = {
    "orders.csv": ORDER_COLUMNS.split(),
    "payments.csv": "payment_id order_id payment_ts payment_mode amount_paid payment_status gateway_ref".split(),
    "customers.csv": "customer_id full_name email phone city area pincode signup_date loyalty_tier is_active".split(),
    "products.csv": "product_id product_name category sub_category brand mrp cost_price unit is_perishable launch_date".split(),
    "stores.csv": "store_id store_name zone area pincode open_date manager_name capacity_orders_per_day".split(),
    "orders_2026-10-01_increment.csv": ORDER_COLUMNS.split(),
}
NUMERIC = {
    "quantity", "unit_price", "discount_pct", "order_amount", "delivery_minutes",
    "amount_paid", "mrp", "cost_price", "capacity_orders_per_day",
}
DATES = {"order_ts", "payment_ts", "signup_date", "launch_date", "open_date"}
CATEGORIES = {
    "payment_mode", "order_status", "channel", "payment_status", "loyalty_tier",
    "is_active", "category", "sub_category", "unit", "is_perishable", "zone",
}
ALLOWED = {
    "order_status": {"DELIVERED", "CANCELLED", "RETURNED"},
    "payment_mode": {"UPI", "CARD", "CASH ON DELIVERY", "WALLET"},
    "zone": {"NORTH", "SOUTH", "EAST", "WEST"},
}
ISSUE_COLUMNS = ["file", "record_number", "row_key", "column", "problem",
                 "quality_dimension", "proposed_rule", "severity"]


def money(value):
    """Decimal arithmetic avoids binary floating-point rounding surprises."""
    try:
        number = Decimal(str(value).strip())
        return number if number.is_finite() else None
    except InvalidOperation:
        return None


def profile(data_dir, as_of):
    frames, summary, issues = {}, {}, []

    def add(name, mask, column, problem, dimension, rule, severity="Critical"):
        frame = frames[name]
        for index in frame.index[mask]:
            issues.append(dict(zip(ISSUE_COLUMNS, [
                name, int(index) + 1, frame.iloc[index, 0].strip() or "<missing>",
                column, problem, dimension, rule, severity,
            ])))

    # Read strings without pandas interpreting literal 'NA' or 'NULL' as missing.
    # Only empty/whitespace fields count as missing; other tokens stay inspectable.
    for name, expected in SCHEMAS.items():
        path = data_dir / name
        if not path.is_file():
            raise ValueError(f"Missing input: {path}. Select the assignment dataset with --data-dir.")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            if header != expected:
                raise ValueError(f"Unexpected schema in {name}: expected {expected}; got {header}")
            for record, row in enumerate(reader, 1):
                if len(row) != len(expected):
                    raise ValueError(f"{name}, record {record}: wrong field count")
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        frames[name] = frame

    for name, frame in frames.items():
        key = frame.columns[0]
        clean = frame.apply(lambda column: column.str.strip())
        key_duplicates = clean[key].ne("") & clean[key].duplicated(keep=False)
        file_summary = {
            "rows": len(frame), "columns": len(frame.columns),
            "sha256": hashlib.sha256((data_dir / name).read_bytes()).hexdigest(),
            "duplicate_key_rows": int(key_duplicates.sum()),
            "duplicate_key_values": int(clean.loc[key_duplicates, key].nunique()),
            "exact_duplicate_excess_rows": int(frame.duplicated().sum()),
            "column_profiles": {},
        }
        summary[name] = file_summary
        add(name, key_duplicates, key, "Repeated key within this file", "Uniqueness",
            "Choose a deterministic survivor; quarantine conflicting duplicates")

        for column in frame.columns:
            values = clean[column]
            blank = values.eq("")
            details = {"missing": int(blank.sum()), "distinct_nonblank": int(values[~blank].nunique())}
            file_summary["column_profiles"][column] = details
            # Delivery time is conditional; absent gateway references may be legitimate.
            if column not in {"delivery_minutes", "gateway_ref"}:
                warning = column in {"email", "phone", "full_name", "manager_name", "area", "city", "pincode"}
                add(name, blank, column, "Missing value", "Completeness",
                    "Review requiredness; quarantine missing required fields",
                    "Warning" if warning else "Critical")
            add(name, frame[column].ne(values) & ~blank, column, "Surrounding whitespace",
                "Consistency", "Trim in transformed data; preserve raw", "Warning")

            if column in NUMERIC:
                numbers = pd.to_numeric(values, errors="coerce")
                finite = numbers.notna() & numbers.map(lambda n: math.isfinite(n) if pd.notna(n) else False)
                good = numbers[finite]
                details.update(kind="numeric", minimum=float(good.min()) if len(good) else None,
                               maximum=float(good.max()) if len(good) else None,
                               invalid_nonblank=int((~blank & ~finite).sum()))
                add(name, ~blank & ~finite, column, "Not a finite number", "Validity", "Quarantine")
                if column in {"quantity", "unit_price", "mrp", "capacity_orders_per_day"}:
                    add(name, finite & numbers.le(0), column, "Must be positive", "Accuracy", "Quarantine")
                if column in {"cost_price", "order_amount", "amount_paid", "delivery_minutes"}:
                    add(name, finite & numbers.lt(0), column, "Negative value", "Accuracy", "Quarantine")
                if column in {"quantity", "capacity_orders_per_day"}:
                    add(name, finite & numbers.mod(1).ne(0), column, "Must be a whole number", "Validity", "Quarantine")
                if column == "discount_pct":
                    add(name, finite & ~numbers.between(0, 100), column, "Discount outside 0–100", "Validity", "Quarantine")
                if column == "delivery_minutes":
                    add(name, finite & numbers.ge(120), column, "Delivery at least 120 minutes", "Accuracy", "Quarantine; confirm limit with client")
                    add(name, finite & ~numbers.between(8, 35) & numbers.between(0, 119.999), column,
                        "Outside usual 8–35 minute range", "Accuracy", "Review unusual delivery", "Warning")
            elif column in DATES:
                date_format = "%Y-%m-%d %H:%M:%S" if column.endswith("_ts") else "%Y-%m-%d"
                dates = pd.to_datetime(values, format=date_format, errors="coerce")
                details.update(kind="date", minimum=str(dates.min()) if dates.notna().any() else None,
                               maximum=str(dates.max()) if dates.notna().any() else None,
                               invalid_nonblank=int((~blank & dates.isna()).sum()))
                add(name, ~blank & dates.isna(), column, "Unparseable date/timestamp", "Validity", "Quarantine")
                add(name, dates.dt.date.gt(as_of), column, "Date after reference date", "Timeliness", "Quarantine; verify reference date")
                if column == "order_ts" and dates.notna().any():
                    latest = dates.max().date()
                    file_summary["freshness"] = {"latest_order_date": str(latest), "age_days": (as_of - latest).days}
                    if (as_of - latest).days > 1:
                        issues.append(dict(zip(ISSUE_COLUMNS, [name, "", "<file>", column,
                            "Latest order is older than one day", "Timeliness",
                            "Warn; historical fixtures are expected to be stale", "Warning"])))
            else:
                details["kind"] = "text"
            if column in CATEGORIES:
                details["raw_value_counts"] = frame[column].value_counts(dropna=False).to_dict()
                if column in ALLOWED:
                    add(name, ~blank & ~values.str.upper().isin(ALLOWED[column]), column,
                        "Unrecognised category", "Validity", "Quarantine")
                if column in {"loyalty_tier", "order_status", "payment_status"}:
                    add(name, ~blank & values.ne(values.str.upper()), column,
                        "Noncanonical casing", "Consistency", "Standardise to uppercase", "Warning")
            if column in {"email", "phone", "pincode"}:
                pattern = {"email": r"[^\s@]+@[^\s@]+\.[^\s@]+", "phone": r"[0-9]{10}", "pincode": r"[0-9]{6}"}[column]
                add(name, ~blank & ~values.str.fullmatch(pattern), column, "Invalid format",
                    "Validity", "Review and mask personal details in reporting", "Warning")

        if "order_status" in frame:
            delivered = clean.order_status.str.upper().eq("DELIVERED")
            add(name, delivered & clean.delivery_minutes.eq(""), "delivery_minutes",
                "Delivered order missing delivery time", "Completeness", "Quarantine")
            mismatch = []
            for row in frame.itertuples(index=False):
                q, price, discount, amount = map(money, (row.quantity, row.unit_price, row.discount_pct, row.order_amount))
                mismatch.append(False if None in (q, price, discount, amount) else
                    (q * price * (1 - discount / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) != amount)
            add(name, pd.Series(mismatch, index=frame.index, dtype=bool), "order_amount",
                "Amount differs from rounded quantity × price × (1 − discount/100)", "Accuracy", "Quarantine; confirm half-up rounding")
            for column, master in [("customer_id", "customers.csv"), ("product_id", "products.csv"), ("store_id", "stores.csv")]:
                keys = set(frames[master][column].str.strip()) - {""}
                add(name, clean[column].ne("") & ~clean[column].isin(keys), column,
                    "Reference missing from master", "Consistency", "Quarantine")
        if name == "products.csv":
            add(name, pd.to_numeric(clean.cost_price, errors="coerce").gt(pd.to_numeric(clean.mrp, errors="coerce")),
                "cost_price", "Cost exceeds MRP", "Accuracy", "Quarantine; confirm business rule")

    # Reconcile against the original snapshot, not October corrections. Multiple
    # order versions are reported as ambiguous rather than arbitrarily selected.
    orders = frames["orders.csv"].apply(lambda col: col.str.strip())
    payments = frames["payments.csv"].apply(lambda col: col.str.strip())
    order_groups = {key: group for key, group in orders.groupby("order_id") if key}
    for index, row in payments.iterrows():
        group = order_groups.get(row.order_id)
        problem = None
        if row.order_id and group is None:
            problem = "Payment references missing order"
        elif group is not None and row.payment_status.upper() == "SUCCESS":
            amounts = {money(value) for value in group.order_amount}
            if len(amounts) != 1 or None in amounts:
                problem = "Order amount ambiguous or invalid; cannot reconcile"
            elif money(row.amount_paid) is not None and money(row.amount_paid) not in amounts:
                problem = "Successful payment differs from order amount"
        if problem:
            add("payments.csv", payments.index == index, "order_id/amount_paid", problem,
                "Consistency", "Investigate reconciliation mismatch")
    successful = set(payments.loc[payments.payment_status.str.upper().eq("SUCCESS"), "order_id"])
    add("orders.csv", orders.order_status.str.upper().eq("DELIVERED") & ~orders.order_id.isin(successful),
        "order_id", "Delivered order has no successful payment", "Consistency",
        "Review settlement timing and Cash on Delivery policy", "Warning")

    increment = frames["orders_2026-10-01_increment.csv"]
    existing = increment.order_id.str.strip().isin(set(orders.order_id))
    summary["orders_2026-10-01_increment.csv"]["incremental_comparison"] = {
        "existing_order_rows": int(existing.sum()), "new_order_rows": int((~existing).sum()),
        "note": "Cross-file overlap is an update candidate, not a duplicate error. Validate before upsert.",
    }
    return summary, issues


def write_reports(output_dir, summary, issues, as_of):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "profile_summary.json").write_text(
        json.dumps({"as_of": str(as_of), "files": summary}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (output_dir / "data_issues.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ISSUE_COLUMNS)
        writer.writeheader()
        writer.writerows(issues)
    lines = ["# NammaMart profiling report", "", f"Reference date (IST): {as_of}", "",
        "Read-only discovery. Sources are never modified. All input fields are read as text;",
        "numeric/date statistics use temporary parsed copies. Blank includes whitespace-only fields.",
        "Reports omit raw personal values. Record numbers are 1-based data records, excluding the header.",
        "Issue counts are findings, not rejected-row counts. A row can have multiple findings.", "",
        "| File | Rows | Duplicate-key rows | Findings | Rows with findings |",
        "| --- | ---: | ---: | ---: | ---: |"]
    for name, details in summary.items():
        found = [issue for issue in issues if issue["file"] == name]
        affected = {issue["record_number"] for issue in found if issue["record_number"] != ""}
        lines.append(f"| {name} | {details['rows']} | {details['duplicate_key_rows']} | {len(found)} | {len(affected)} |")
    lines += ["", "## Findings by rule", "", "| File | Column | Problem | Severity | Count |",
              "| --- | --- | --- | --- | ---: |"]
    counts = Counter((i["file"], i["column"], i["problem"], i["severity"]) for i in issues)
    lines += [f"| {' | '.join(key)} | {count} |" for key, count in sorted(counts.items())]
    lines += ["", "## Assumptions and next steps", "",
        "- Numeric/date ranges and original categorical frequencies are in profile_summary.json.",
        "- data_issues.csv contains record keys, quality dimensions, proposed rules, and severity.",
        "- Duplicate-key counts include all members, not just excess copies. Keys are trimmed for comparison.",
        "- Money uses decimal arithmetic and ROUND_HALF_UP to two places; confirm this policy with finance.",
        "- Future-date checks compare calendar dates; freshness uses the supplied reference date.",
        "- Payments are compared individually to September orders. Refunds, multiple payments, and settlement timing need client policy.",
        "- Increment overlaps are update candidates; this script does not apply updates.",
        "- Required fields and severity are proposed rules, not an approved rejection policy.", "",
        "## Questions for the client", "",
        "1. Which record wins when duplicate keys contain conflicting values?",
        "2. Should October returns restate September revenue or become October adjustments?",
        "3. Should payment mismatches block finance reporting, and how should pending/COD payments be handled?", ""]
    (output_dir / "PROFILE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "assignment/nammamart_dataset")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "include/profiling_output")
    parser.add_argument("--as-of", type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
                        default=datetime.now(ZoneInfo("Asia/Kolkata")).date(), help="Reference date YYYY-MM-DD (default: today in IST)")
    args = parser.parse_args()
    try:
        summary, issues = profile(args.data_dir, args.as_of)
    except (ValueError, OSError, pd.errors.ParserError) as error:
        parser.exit(1, f"Profiling failed: {error}\n")
    write_reports(args.output_dir, summary, issues, args.as_of)
    for name, details in summary.items():
        print(f"{name}: {details['rows']} rows; {details['duplicate_key_rows']} rows with duplicate keys")
    print(f"Recorded {len(issues)} findings. Reports: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
