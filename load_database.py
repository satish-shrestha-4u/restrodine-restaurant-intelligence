import getpass
import os
from pathlib import Path

import mysql.connector
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
SCHEMA_PATH = DATA_DIR / "schema.sql"
DATABASE_NAME = "restrodine"

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


def read_csv(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV file: {path}")
    return pd.read_csv(path)


def mysql_value(value):
    """Convert pandas/numpy values into values MySQL Connector can bind."""
    if pd.isna(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return int(value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def execute_schema(cursor) -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Missing MySQL schema file: {SCHEMA_PATH}")

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    for statement in schema.split(";"):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)


def load_table(cursor, table_name: str, filename: str) -> int:
    df = read_csv(filename)
    if table_name == "orders":
        # Keep the source CSV unchanged; this date key links each order to calendar.
        df["order_date"] = pd.to_datetime(df["order_datetime"]).dt.date
    elif table_name == "daily_revenue":
        # Calendar and weather attributes live in their own linked tables.
        df = df[["date", "revenue", "orders", "average_order_value"]]
    columns = list(df.columns)
    column_sql = ", ".join(f"`{column}`" for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = (
        f"INSERT INTO `{table_name}` ({column_sql}) "
        f"VALUES ({placeholders})"
    )

    rows = (
        tuple(mysql_value(value) for value in row)
        for row in df.itertuples(index=False, name=None)
    )

    inserted = 0
    while True:
        batch = []
        try:
            for _ in range(1000):
                batch.append(next(rows))
        except StopIteration:
            pass

        if not batch:
            break

        cursor.executemany(insert_sql, batch)
        inserted += len(batch)

    return inserted


def main() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Missing MySQL schema file: {SCHEMA_PATH}")

    password = os.environ.get("MYSQL_PASSWORD")
    if password is None:
        password = getpass.getpass("MySQL password for the selected user: ")

    connection = mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=password,
        connection_timeout=10,
    )

    cursor = connection.cursor()
    try:
        print("Creating/resetting the RestroDine MySQL tables...")
        execute_schema(cursor)

        products = read_csv("products.csv")
        promotions = read_csv("promotions.csv")
        category_names = sorted(set(products["category"].dropna().astype(str)) |
                                set(promotions["product_category"].dropna().astype(str)))
        cursor.executemany(
            "INSERT INTO categories (category_name) VALUES (%s)",
            [(name,) for name in category_names],
        )
        print(f"Loaded {len(category_names)} product/promotion categories")

        for table_name, filename in TABLES:
            print(f"Loading {filename} -> {table_name} ...")
            count = load_table(cursor, table_name, filename)
            print(f"  {count:,} rows loaded")

        connection.commit()

        print("\nVALIDATION")
        failed = 0

        def check(name: str, passed: bool, detail: str) -> None:
            nonlocal failed
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {name}: {detail}")
            if not passed:
                failed += 1

        for table, column in [
            ("customers", "customer_id"),
            ("products", "product_id"),
            ("employees", "employee_id"),
            ("orders", "order_id"),
            ("order_items", "order_item_id"),
            ("payments", "payment_id"),
            ("reviews", "review_id"),
        ]:
            cursor.execute(
                f"SELECT COUNT(*), COUNT(DISTINCT `{column}`) "
                f"FROM `{table}`"
            )
            total, unique = cursor.fetchone()
            check(f"{table} unique IDs", total == unique,
                  f"{total:,} rows / {unique:,} unique")

        cursor.execute("""
            SELECT COUNT(*)
            FROM orders o
            LEFT JOIN payments p ON p.order_id = o.order_id
            WHERE p.order_id IS NULL
        """)
        missing = cursor.fetchone()[0]
        check("every order has payment", missing == 0, f"{missing} missing")

        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT o.order_id
                FROM orders o
                JOIN order_items i ON i.order_id = o.order_id
                GROUP BY o.order_id, o.order_total
                HAVING ABS(ROUND(o.order_total, 2)
                           - ROUND(SUM(i.line_total), 2)) > 0.02
            ) AS mismatches
        """)
        mismatch = cursor.fetchone()[0]
        check("order totals reconcile with items", mismatch == 0,
              f"{mismatch} mismatches")

        cursor.execute("""
            SELECT COUNT(*)
            FROM orders o
            JOIN payments p ON p.order_id = o.order_id
            WHERE ABS(ROUND(o.order_total, 2) - ROUND(p.amount, 2)) > 0.01
        """)
        mismatch = cursor.fetchone()[0]
        check("payments reconcile with orders", mismatch == 0,
              f"{mismatch} mismatches")

        for table in ("calendar", "weather", "daily_revenue"):
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]
            check(f"{table} has 365 rows", count == 365, f"{count} rows")

        if failed:
            raise RuntimeError(
                f"MySQL database validation failed: {failed} check(s) failed."
            )

        print("\nALL VALIDATION CHECKS PASSED")
        print(f"MySQL database: {DATABASE_NAME}")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
