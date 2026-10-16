import sqlite3
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "restrodine.db"
SCHEMA_PATH = PROJECT_ROOT / "schema.sql"

TABLES = [
    ("customers", "customers.csv"),
    ("products", "products.csv"),
    ("employees", "employees.csv"),
    ("calendar", "calendar.csv"),
    ("weather", "weather.csv"),
    ("promotions", "promotions.csv"),
    ("employee_availability", "employee_availability.csv"),
    ("shifts", "shifts.csv"),
    ("orders", "orders.csv"),
    ("order_items", "order_items.csv"),
    ("payments", "payments.csv"),
    ("reviews", "reviews.csv"),
    ("daily_revenue", "daily_revenue.csv"),
]


def read_csv(filename):
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV file: {path}")
    return pd.read_csv(path)


def clean_for_sqlite(df):
    return df.astype(object).where(pd.notna(df), None)


def main():
    print("=" * 60)
    print("RESTRODINE DATABASE LOADER")
    print("=" * 60)

    if DB_PATH.exists():
        DB_PATH.unlink()

    con = sqlite3.connect(DB_PATH)

    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        for table_name, filename in TABLES:
            print(f"Loading {filename} -> {table_name} ...")
            df = clean_for_sqlite(read_csv(filename))
            df.to_sql(table_name, con, if_exists="append", index=False, chunksize=1000)
            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"  {count:,} rows loaded")

        con.commit()

        print("\n" + "=" * 60)
        print("VALIDATION")
        print("=" * 60)

        failed = 0

        def check(name, passed, detail):
            nonlocal failed
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {name}: {detail}")
            if not passed:
                failed += 1

        fk = con.execute("PRAGMA foreign_key_check").fetchall()
        check("foreign key integrity", len(fk) == 0, f"{len(fk)} violations")

        for table, column in [
            ("customers", "customer_id"),
            ("products", "product_id"),
            ("employees", "employee_id"),
            ("orders", "order_id"),
            ("order_items", "order_item_id"),
            ("payments", "payment_id"),
            ("reviews", "review_id"),
        ]:
            total = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            unique = con.execute(f"SELECT COUNT(DISTINCT {column}) FROM {table}").fetchone()[0]
            check(f"{table} unique IDs", total == unique, f"{total:,} rows / {unique:,} unique")

        missing = con.execute("""
            SELECT COUNT(*)
            FROM orders o
            LEFT JOIN payments p ON p.order_id = o.order_id
            WHERE p.order_id IS NULL
        """).fetchone()[0]
        check("every order has payment", missing == 0, f"{missing} missing")

        mismatch = con.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT o.order_id
                FROM orders o
                JOIN order_items i ON i.order_id = o.order_id
                GROUP BY o.order_id, o.order_total
                HAVING ABS(ROUND(o.order_total, 2) - ROUND(SUM(i.line_total), 2)) > 0.02
            )
        """).fetchone()[0]
        check("order totals reconcile with items", mismatch == 0, f"{mismatch} mismatches")

        mismatch = con.execute("""
            SELECT COUNT(*)
            FROM orders o
            JOIN payments p ON p.order_id = o.order_id
            WHERE ABS(ROUND(o.order_total, 2) - ROUND(p.amount, 2)) > 0.01
        """).fetchone()[0]
        check("payments reconcile with orders", mismatch == 0, f"{mismatch} mismatches")

        for table in ["calendar", "weather", "daily_revenue"]:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            check(f"{table} has 365 rows", count == 365, f"{count} rows")

        if failed:
            raise RuntimeError(f"Database validation failed: {failed} check(s) failed.")

        print("\nALL VALIDATION CHECKS PASSED")
        print(f"SQLite database: {DB_PATH}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
