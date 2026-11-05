"""RestroDine - create the MySQL database, load all CSVs, run integrity checks.

Usage:  python load_database.py [--host localhost] [--port 3306] [--user root] [--database restrodine]
WARNING: every run DROPS and recreates the project tables in the given database.
The data is SYNTHETIC (generated for a project) - it is not real restaurant data.
"""
import argparse, getpass, re, sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pymysql

DATA = Path(__file__).parent / "data"
# parents before children (foreign keys)
LOAD_ORDER = ["categories", "calendar", "promotions", "customers", "products", "employees",
              "employee_availability", "shifts", "orders", "order_items", "payments", "weather",
              "reviews", "review_aspect_labels", "daily_revenue"]
BATCH = 5000


def run_script(cur, text):
    text = re.sub(r"--[^\n]*", "", text)                 # strip line comments
    for stmt in (s.strip() for s in text.split(";")):
        if stmt:
            cur.execute(stmt)


def load_table(cur, table):
    df = pd.read_csv(DATA / f"{table}.csv", dtype=str, keep_default_na=False, encoding="utf-8")
    df = df.astype(object).where(df != "", None)         # '' -> NULL
    cols = ", ".join(f"`{c}`" for c in df.columns)
    sql = f"INSERT INTO `{table}` ({cols}) VALUES ({', '.join(['%s'] * len(df.columns))})"
    rows = list(df.itertuples(index=False, name=None))
    for i in range(0, len(rows), BATCH):
        cur.executemany(sql, rows[i:i + BATCH])
    return len(rows)


def scalar(cur, sql):
    cur.execute(sql)
    return cur.fetchone()[0]


def run_checks(cur):
    """The 14 README integrity checks. Portable SQL, no parameters. Returns list of (name, ok, detail)."""
    res = []
    def add(name, bad, detail=""):
        res.append((name, bad == 0, detail or f"{bad} violations"))

    # 1 unique primary IDs (enforced by PK, verified anyway)
    dup = sum(scalar(cur, f"SELECT COUNT(*) - COUNT(DISTINCT {k}) FROM {t}") for t, k in
              [("customers", "customer_id"), ("products", "product_id"), ("employees", "employee_id"),
               ("orders", "order_id"), ("order_items", "order_item_id"), ("payments", "payment_id"),
               ("shifts", "shift_id"), ("reviews", "review_id")])
    add("1. Primary IDs unique", dup)
    # 2 / 3 / 4 referential integrity
    add("2. order_items.order_id exists in orders", scalar(cur,
        "SELECT COUNT(*) FROM order_items i LEFT JOIN orders o ON o.order_id=i.order_id WHERE o.order_id IS NULL"))
    add("3. order_items.product_id exists in products", scalar(cur,
        "SELECT COUNT(*) FROM order_items i LEFT JOIN products p ON p.product_id=i.product_id WHERE p.product_id IS NULL"))
    add("4. every payment belongs to an order", scalar(cur,
        "SELECT COUNT(*) FROM payments p LEFT JOIN orders o ON o.order_id=p.order_id WHERE o.order_id IS NULL"))
    # 5 sum(line_total) = order_total
    add("5. SUM(line_total) = orders.order_total", scalar(cur,
        "SELECT COUNT(*) FROM orders o JOIN (SELECT order_id, SUM(line_total) s FROM order_items GROUP BY order_id) i "
        "ON i.order_id=o.order_id WHERE ABS(i.s-o.order_total) > 0.011"))
    # 6 payment = order_total
    add("6. payments.amount = orders.order_total", scalar(cur,
        "SELECT COUNT(*) FROM orders o JOIN (SELECT order_id, SUM(amount) s FROM payments GROUP BY order_id) p "
        "ON p.order_id=o.order_id WHERE ABS(p.s-o.order_total) > 0.011"))
    # 7 registration <= first order
    add("7. registration_date <= first_order_date", scalar(cur,
        "SELECT COUNT(*) FROM customers WHERE first_order_date IS NOT NULL AND registration_date > first_order_date"))
    # 8 / 9 calendar & weather cover every day of the order history
    d0, d1 = (date.fromisoformat(str(x)[:10]) for x in
              (scalar(cur, "SELECT MIN(DATE(order_datetime)) FROM orders"),
               scalar(cur, "SELECT MAX(DATE(order_datetime)) FROM orders")))
    n = (d1 - d0).days + 1
    for k, t in ((8, "calendar"), (9, "weather")):
        have = scalar(cur, f"SELECT COUNT(DISTINCT `date`) FROM {t} WHERE `date` BETWEEN '{d0}' AND '{d1}'")
        add(f"{k}. {t} has all {n} dates ({d0} .. {d1})", n - have, f"{have}/{n} dates")
    # 10 labour cost = hours x hourly cost
    add("10. labour_cost = hours_worked x hourly_cost", scalar(cur,
        "SELECT COUNT(*) FROM shifts s JOIN employees e ON e.employee_id=s.employee_id "
        "WHERE ABS(s.hours_worked*e.hourly_cost - s.labour_cost) > 0.011"))
    # extras that matter for Phase 2 / Phase 1
    add("11. no shift outside employment period / by inactive staff", scalar(cur,
        "SELECT COUNT(*) FROM shifts s JOIN employees e ON e.employee_id=s.employee_id "
        "WHERE s.shift_date < e.employment_start OR (e.employment_end IS NOT NULL AND s.shift_date > e.employment_end)"))
    add("12. daily_revenue = SUM(orders) per day", scalar(cur,
        "SELECT COUNT(*) FROM daily_revenue d JOIN (SELECT DATE(order_datetime) dt, SUM(order_total) r, COUNT(*) n "
        "FROM orders GROUP BY DATE(order_datetime)) o ON o.dt=d.`date` WHERE ABS(o.r-d.revenue) > 0.011 OR o.n<>d.orders"))
    add("13. orders.order_date = DATE(order_datetime)", scalar(cur,
        "SELECT COUNT(*) FROM orders WHERE order_date <> DATE(order_datetime)"))
    add("14. discounted lines carry a promotion_id (and only those)", scalar(cur,
        "SELECT COUNT(*) FROM order_items WHERE (discount_pct > 0 AND promotion_id IS NULL) "
        "OR (discount_pct = 0 AND promotion_id IS NOT NULL)"))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost"); ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--user", default="root"); ap.add_argument("--database", default="restrodine")
    a = ap.parse_args()
    pwd = getpass.getpass(f"MySQL password for {a.user}@{a.host}: ")
    con = pymysql.connect(host=a.host, port=a.port, user=a.user, password=pwd, charset="utf8mb4", autocommit=False)
    cur = con.cursor()
    schema = (DATA / "schema.sql").read_text(encoding="utf-8")
    if a.database != "restrodine":
        schema = schema.replace("restrodine", a.database)
    print("Creating schema ...")
    run_script(cur, schema)
    cur.execute(f"USE `{a.database}`")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    for t in LOAD_ORDER:
        print(f"  loading {t:<22}", end="", flush=True)
        print(f"{load_table(cur, t):>9,} rows")
    con.commit()
    print("\nIntegrity checks")
    ok_all = True
    for name, ok, detail in run_checks(cur):
        ok_all &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  ({detail})")
    con.close()
    print("\nDatabase validated - safe to start modelling." if ok_all else "\nValidation FAILED - fix before modelling.")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
