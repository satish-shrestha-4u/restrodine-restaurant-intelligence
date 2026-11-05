# ============================================================
# RESTRODINE — ANALYTICAL VALIDATION TESTS
# ============================================================
# Run from the project root:
# python tests/validate_project.py
#
# These tests validate data integrity and analytical logic.
# All project data is synthetic.
# ============================================================

from pathlib import Path
import json
import sys
import re

import numpy as np
import pandas as pd


# ============================================================
# PROJECT PATHS AND TEST UTILITIES
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data_clean"
OUTPUTS = ROOT / "outputs"
MODELS = ROOT / "models"
METADATA = ROOT / "metadata"

passed = 0
failed = 0


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def check(condition, message):
    """Record a test result and stop only when a check fails."""
    global passed, failed

    if condition:
        passed += 1
        print(f"PASS: {message}")
    else:
        failed += 1
        print(f"FAIL: {message}")


def load_csv(folder, filename, required=True):
    path = folder / filename

    if not path.exists():
        if required:
            check(False, f"File exists: {path.relative_to(ROOT)}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(path)
        check(True, f"CSV readable: {path.relative_to(ROOT)}")
        return df
    except Exception as exc:
        check(False, f"CSV readable: {path.relative_to(ROOT)} ({exc})")
        return pd.DataFrame()


def require_columns(df, columns, label):
    missing = [column for column in columns if column not in df.columns]

    check(
        not missing,
        f"{label} contains required columns: {columns}",
    )

    return not missing


def numeric(df, column):
    return pd.to_numeric(df[column], errors="coerce")


def find_column(df, candidates):
    for column in candidates:
        if column in df.columns:
            return column
    return None


def close_enough(left, right, atol=0.02, rtol=0.0001):
    return np.allclose(
        np.asarray(left, dtype=float),
        np.asarray(right, dtype=float),
        atol=atol,
        rtol=rtol,
        equal_nan=False,
    )


# ============================================================
# MAIN VALIDATION FUNCTION
# ============================================================

def run_validation():
    global passed, failed

    passed = 0
    failed = 0


    # ============================================================
    # 1. LOAD CLEANED DATA
    # ============================================================

    print("\n" + "=" * 65)
    print("RESTRODINE — DATA AND ANALYTICS VALIDATION")
    print("=" * 65)

    orders = load_csv(DATA, "orders_clean.csv")
    items = load_csv(DATA, "order_items_clean.csv")
    products = load_csv(DATA, "products_clean.csv")
    reviews = load_csv(DATA, "reviews_clean.csv")

    employees = load_csv(DATA, "employees_clean.csv")
    shifts = load_csv(DATA, "shifts_clean.csv")

    # Required output files

    forecast = load_csv(
        OUTPUTS,
        "revenue_forecast_next_14_days.csv",
    )

    workforce = load_csv(
        OUTPUTS,
        "workforce_forecast_next_14_days.csv",
    )

    coverage = load_csv(
        OUTPUTS,
        "staffing_coverage.csv",
    )

    gaps = load_csv(
        OUTPUTS,
        "staffing_gaps.csv",
    )

    menu_products = load_csv(
        OUTPUTS,
        "menu_product_performance.csv",
    )

    menu_engineering = load_csv(
        OUTPUTS,
        "menu_engineering.csv",
    )

    aspect_summary = load_csv(
        OUTPUTS,
        "customer_aspect_sentiment_summary.csv",
    )

    rfm_segments = load_csv(
        OUTPUTS,
        "customer_rfm_segments.csv",
    )


    # ============================================================
    # 2. REVENUE DATA VALIDATION
    # ============================================================

    print("\n--- REVENUE VALIDATION ---")

    if require_columns(
        orders,
        ["order_id", "order_total"],
        "Orders dataset",
    ) and require_columns(
        items,
        ["order_id", "quantity", "line_total"],
        "Order items dataset",
    ):

        order_totals = numeric(orders, "order_total")
        line_totals = numeric(items, "line_total")

        check(
            order_totals.notna().all(),
            "Order totals contain valid numeric values",
        )

        check(
            line_totals.notna().all(),
            "Order line totals contain valid numeric values",
        )

        check(
            (order_totals >= 0).all(),
            "Order totals are non-negative",
        )

        check(
            (line_totals >= 0).all(),
            "Order line totals are non-negative",
        )

        # Every order item should reference an existing order.

        unknown_orders = set(items["order_id"]) - set(orders["order_id"])

        check(
            len(unknown_orders) == 0,
            "Every order item references an existing order",
        )

        # Compare order totals with the sum of their line totals.

        item_totals = (
            items.assign(_line_total=line_totals)
            .groupby("order_id")["_line_total"]
            .sum()
        )

        order_total_map = (
            orders.assign(_order_total=order_totals)
            .groupby("order_id")["_order_total"]
            .sum()
        )

        common_ids = item_totals.index.intersection(
            order_total_map.index
        )

        if len(common_ids) > 0:

            differences = (
                item_totals.loc[common_ids]
                - order_total_map.loc[common_ids]
            ).abs()

            check(
                (differences <= 0.02).all(),
                "Order totals reconcile with order-item line totals",
            )

        else:
            check(False, "Orders and order items have matching IDs")

        # Quantity validation

        quantities = numeric(items, "quantity")

        check(
            quantities.notna().all() and (quantities > 0).all(),
            "Order-item quantities are positive",
        )

    else:
        check(False, "Revenue reconciliation could not run")


    # ============================================================
    # 3. PRODUCT COST AND GROSS PROFIT VALIDATION
    # ============================================================

    print("\n--- PRODUCT PROFITABILITY VALIDATION ---")

    if require_columns(
        products,
        ["product_id", "selling_price", "product_cost"],
        "Products dataset",
    ) and require_columns(
        items,
        ["product_id", "quantity", "line_total"],
        "Order items dataset",
    ):

        product_costs = numeric(products, "product_cost")
        selling_prices = numeric(products, "selling_price")

        check(
            product_costs.notna().all()
            and (product_costs >= 0).all(),
            "Product costs are valid and non-negative",
        )

        check(
            selling_prices.notna().all()
            and (selling_prices >= 0).all(),
            "Selling prices are valid and non-negative",
        )

        check(
            products["product_id"].is_unique,
            "Product catalogue has unique product IDs",
        )

        item_product_ids = set(items["product_id"])
        catalogue_product_ids = set(products["product_id"])

        check(
            item_product_ids.issubset(catalogue_product_ids),
            "Every sold product exists in the product catalogue",
        )

        joined = items.merge(
            products[["product_id", "product_cost"]],
            on="product_id",
            how="left",
            validate="many_to_one",
        )

        joined["quantity"] = numeric(joined, "quantity")
        joined["line_total"] = numeric(joined, "line_total")
        joined["product_cost"] = numeric(joined, "product_cost")

        joined["expected_cost"] = (
            joined["quantity"] * joined["product_cost"]
        )

        joined["expected_gross_profit"] = (
            joined["line_total"] - joined["expected_cost"]
        )

        check(
            joined["expected_gross_profit"].notna().all(),
            "Product gross-profit calculations have valid inputs",
        )

        calculated_total_profit = (
            joined["expected_gross_profit"].sum()
        )

        calculated_total_revenue = joined["line_total"].sum()

        check(
            close_enough(
                calculated_total_profit,
                calculated_total_revenue
                - joined["expected_cost"].sum(),
            ),
            "Total gross profit equals revenue minus product costs",
        )

    else:
        check(False, "Product profitability validation could not run")


    # ============================================================
    # 4. REVENUE FORECAST VALIDATION
    # ============================================================

    print("\n--- FORECAST VALIDATION ---")

    if require_columns(
        forecast,
        ["date", "forecast_revenue"],
        "Revenue forecast",
    ):

        forecast["date"] = pd.to_datetime(
            forecast["date"], errors="coerce"
        )

        forecast["forecast_revenue"] = numeric(
            forecast, "forecast_revenue"
        )

        check(
            forecast["date"].notna().all(),
            "Forecast dates are valid",
        )

        check(
            forecast["date"].is_unique,
            "Forecast dates are unique",
        )

        check(
            forecast["forecast_revenue"].notna().all(),
            "Forecast revenue contains valid numeric values",
        )

        check(
            (forecast["forecast_revenue"] >= 0).all(),
            "Forecast revenue is non-negative",
        )

        lower_col = find_column(
            forecast,
            ["lower_bound", "yhat_lower"],
        )

        upper_col = find_column(
            forecast,
            ["upper_bound", "yhat_upper"],
        )

        if lower_col and upper_col:

            forecast[lower_col] = numeric(forecast, lower_col)
            forecast[upper_col] = numeric(forecast, upper_col)

            check(
                forecast[lower_col].notna().all()
                and forecast[upper_col].notna().all(),
                "Forecast interval bounds are numeric",
            )

            check(
                (
                    forecast[lower_col]
                    <= forecast["forecast_revenue"]
                ).all(),
                "Lower forecast bounds do not exceed point forecasts",
            )

            check(
                (
                    forecast["forecast_revenue"]
                    <= forecast[upper_col]
                ).all(),
                "Point forecasts do not exceed upper bounds",
            )

        else:
            check(
                False,
                "Forecast lower and upper interval columns are present",
            )

    else:
        check(False, "Forecast validation could not run")


    # ============================================================
    # 5. WORKFORCE VALIDATION
    # ============================================================

    print("\n--- WORKFORCE VALIDATION ---")

    workforce_required = [
        "date",
        "expected_orders",
        "required_staff",
        "scheduled_employees",
        "labour_hours",
        "labour_cost",
        "forecast_revenue",
        "labour_cost_pct_revenue",
    ]

    if require_columns(
        workforce,
        workforce_required,
        "Workforce forecast",
    ):

        workforce["date"] = pd.to_datetime(
            workforce["date"], errors="coerce"
        )

        check(
            workforce["date"].notna().all(),
            "Workforce forecast dates are valid",
        )

        check(
            workforce["date"].is_unique,
            "Workforce forecast contains one row per date",
        )

        numeric_workforce_cols = [
            "expected_orders",
            "required_staff",
            "scheduled_employees",
            "labour_hours",
            "labour_cost",
            "forecast_revenue",
            "labour_cost_pct_revenue",
        ]

        for column in numeric_workforce_cols:
            workforce[column] = numeric(workforce, column)

        check(
            workforce[numeric_workforce_cols].notna().all().all(),
            "Workforce metrics contain valid numeric values",
        )

        nonnegative_columns = [
            "expected_orders",
            "required_staff",
            "scheduled_employees",
            "labour_hours",
            "labour_cost",
            "forecast_revenue",
        ]

        check(
            (
                workforce[nonnegative_columns] >= 0
            ).all().all(),
            "Workforce counts, hours and costs are non-negative",
        )

        # Verify labour cost percentage.

        valid_revenue = workforce["forecast_revenue"] > 0

        if valid_revenue.any():

            expected_pct = (
                workforce.loc[valid_revenue, "labour_cost"]
                / workforce.loc[valid_revenue, "forecast_revenue"]
                * 100
            )

            actual_pct = workforce.loc[
                valid_revenue, "labour_cost_pct_revenue"
            ]

            check(
                close_enough(
                    expected_pct,
                    actual_pct,
                    atol=0.15,
                    rtol=0.001,
                ),
                "Labour cost percentage reconciles with labour cost / revenue",
            )

        else:
            check(
                False,
                "Workforce forecast contains positive forecast revenue",
            )

        # Scheduled employees should not be negative.

        check(
            (workforce["scheduled_employees"] >= 0).all(),
            "Scheduled employee counts are non-negative",
        )

    else:
        check(False, "Workforce validation could not run")


    # ============================================================
    # 6. STAFFING COVERAGE VALIDATION
    # ============================================================

    print("\n--- STAFFING COVERAGE VALIDATION ---")

    if not coverage.empty:

        if require_columns(
            coverage,
            ["required", "assigned", "shortfall"],
            "Staffing coverage",
        ):

            for column in ["required", "assigned", "shortfall"]:
                coverage[column] = numeric(coverage, column)

            check(
                coverage[
                    ["required", "assigned", "shortfall"]
                ].notna().all().all(),
                "Staffing coverage values are numeric",
            )

            check(
                (
                    coverage["required"] >= 0
                ).all()
                and (
                    coverage["assigned"] >= 0
                ).all()
                and (
                    coverage["shortfall"] >= 0
                ).all(),
                "Staffing coverage counts are non-negative",
            )

            expected_shortfall = (
                coverage["required"] - coverage["assigned"]
            ).clip(lower=0)

            check(
                close_enough(
                    expected_shortfall,
                    coverage["shortfall"],
                    atol=0.001,
                    rtol=0,
                ),
                "Staffing shortfall equals max(required - assigned, 0)",
            )

    else:
        check(False, "Staffing coverage output is not empty")


    # ============================================================
    # 7. STAFFING GAP VALIDATION
    # ============================================================

    print("\n--- STAFFING GAP VALIDATION ---")

    if not gaps.empty:

        gap_col = find_column(gaps, ["unfilled", "shortfall"])

        if gap_col:

            gap_values = numeric(gaps, gap_col)

            check(
                gap_values.notna().all(),
                "Staffing gap values are numeric",
            )

            check(
                (gap_values >= 0).all(),
                "Unfilled staffing requirements are non-negative",
            )

        else:
            check(
                False,
                "Staffing gaps contain an unfilled or shortfall column",
            )

    else:
        check(False, "Staffing gaps output is not empty")


    # ============================================================
    # 8. CUSTOMER SENTIMENT VALIDATION
    # ============================================================

    print("\n--- CUSTOMER SENTIMENT VALIDATION ---")

    if not aspect_summary.empty:

        sentiment_columns = [
            "Positive (%)",
            "Neutral (%)",
            "Negative (%)",
        ]

        if require_columns(
            aspect_summary,
            sentiment_columns,
            "Customer sentiment percentages",
        ):

            for column in sentiment_columns:
                aspect_summary[column] = numeric(
                    aspect_summary, column
                )

            check(
                aspect_summary[sentiment_columns].notna().all().all(),
                "Sentiment percentages are numeric",
            )

            check(
                (
                    aspect_summary[sentiment_columns] >= 0
                ).all().all()
                and (
                    aspect_summary[sentiment_columns] <= 100
                ).all().all(),
                "Sentiment percentages are between 0 and 100",
            )

            sentiment_totals = aspect_summary[
                sentiment_columns
            ].sum(axis=1)

            check(
                np.allclose(
                    sentiment_totals,
                    100,
                    atol=0.01,
                ),
                "Sentiment percentages sum to approximately 100 per aspect",
            )

    else:
        check(False, "Customer sentiment output is not empty")


    # ============================================================
    # 9. RFM SEGMENT VALIDATION
    # ============================================================

    print("\n--- RFM SEGMENT VALIDATION ---")

    if not rfm_segments.empty:

        segment_col = find_column(
            rfm_segments,
            ["RFM_Segment", "segment"],
        )

        if segment_col:

            valid_segments = {
                "Champions",
                "Loyal Customers",
                "Potential Loyalists",
                "At Risk",
                "Needs Attention",
                "Regular Customers",
            }

            actual_segments = set(
                rfm_segments[segment_col]
                .dropna()
                .astype(str)
                .unique()
            )

            unexpected = actual_segments - valid_segments

            check(
                len(unexpected) == 0,
                "RFM labels belong to the defined project segments",
            )

        else:
            check(
                False,
                "RFM output contains a segment column",
            )

    else:
        check(False, "RFM segment output is available")


    # ============================================================
    # 10. MENU PERFORMANCE VALIDATION
    # ============================================================

    print("\n--- MENU PERFORMANCE VALIDATION ---")

    if require_columns(
        menu_products,
        ["product_id", "quantity_sold", "total_revenue"],
        "Menu product performance",
    ):

        menu_products["quantity_sold"] = numeric(
            menu_products, "quantity_sold"
        )

        menu_products["total_revenue"] = numeric(
            menu_products, "total_revenue"
        )

        check(
            menu_products["product_id"].is_unique,
            "Menu performance has one row per product",
        )

        check(
            menu_products[
                ["quantity_sold", "total_revenue"]
            ].notna().all().all(),
            "Menu quantities and revenue are numeric",
        )

        check(
            (
                menu_products["quantity_sold"] >= 0
            ).all()
            and (
                menu_products["total_revenue"] >= 0
            ).all(),
            "Menu quantities and revenue are non-negative",
        )

        menu_profit_col = find_column(
            menu_products,
            ["total_gross_profit", "gross_profit"],
        )

        if menu_profit_col:

            menu_products[menu_profit_col] = numeric(
                menu_products, menu_profit_col
            )

            check(
                menu_products[menu_profit_col].notna().all(),
                "Menu gross profit contains numeric values",
            )

    else:
        check(False, "Menu product performance validation could not run")


    # ============================================================
    # 11. MENU ENGINEERING CLASS VALIDATION
    # ============================================================

    print("\n--- MENU ENGINEERING VALIDATION ---")

    if not menu_engineering.empty:

        class_col = find_column(
            menu_engineering,
            [
                "menu_class",
                "Menu_Class",
                "classification",
                "class",
            ],
        )

        if class_col:

            valid_classes = {
                "Star",
                "Plowhorse",
                "Puzzle",
                "Dog",
            }

            actual_classes = set(
                menu_engineering[class_col]
                .dropna()
                .astype(str)
                .str.title()
                .unique()
            )

            check(
                actual_classes.issubset(valid_classes),
                "Menu engineering uses only the four defined classes",
            )

            check(
                menu_engineering[class_col].notna().all(),
                "Every classified product has a menu class",
            )

        else:
            check(
                False,
                "Menu engineering export contains a classification column",
            )

    else:
        check(False, "Menu engineering output is available")


    # ============================================================
    # 12. MODEL METADATA VALIDATION
    # ============================================================

    print("\n--- MODEL ARTIFACT VALIDATION ---")

    model_path = (
        MODELS / "restrodine_prophet_calendar_weather.json"
    )

    metadata_path = (
        METADATA / "restrodine_prophet_calendar_weather_metadata.json"
    )

    check(
        model_path.is_file() and model_path.stat().st_size > 0,
        "Prophet model file exists and is not empty",
    )

    check(
        metadata_path.is_file() and metadata_path.stat().st_size > 0,
        "Prophet metadata file exists and is not empty",
    )

    if metadata_path.exists():

        try:
            with metadata_path.open(encoding="utf-8") as file:
                model_metadata = json.load(file)

            check(
                isinstance(model_metadata, dict),
                "Prophet metadata contains a JSON object",
            )

        except Exception as exc:
            check(False, f"Prophet metadata JSON is valid ({exc})")

    
    # ============================================================
    # 13. SQL SCHEMA AND FOREIGN KEY VALIDATION
    # ============================================================

    print("\n--- SQL SCHEMA VALIDATION ---")

    schema_path = ROOT / "data" / "schema.sql"

    check(
        schema_path.is_file(),
        "SQL schema file exists",
    )

    if schema_path.is_file():

        schema_text = schema_path.read_text(encoding="utf-8")

        # Extract CREATE TABLE definitions.
        table_pattern = re.compile(
            r"CREATE\s+TABLE\s+`?(\w+)`?\s*\((.*?)\)\s*"
            r"(?:ENGINE\b[^;]*;|;)",
            re.IGNORECASE | re.DOTALL,
        )

        schema_tables = {}

        for match in table_pattern.finditer(schema_text):

            table_name = match.group(1)
            table_body = match.group(2)

            columns = []

            for line in table_body.splitlines():

                line = line.split("--")[0].strip()

                if not line:
                    continue

                column_match = re.match(
                    r"`?(\w+)`?\s+"
                    r"(VARCHAR|CHAR|TEXT|INT|INTEGER|BIGINT|"
                    r"TINYINT|DECIMAL|NUMERIC|FLOAT|DOUBLE|"
                    r"DATE|DATETIME|TIME|BOOLEAN|JSON|ENUM)\b",
                    line,
                    re.IGNORECASE,
                )

                if column_match:
                    columns.append(column_match.group(1))

            schema_tables[table_name] = {
                "columns": columns,
                "body": table_body,
            }

        check(
            len(schema_tables) > 0,
            "SQL schema contains CREATE TABLE definitions",
        )

        # Check source CSV columns against SQL schema.
        # daily_model_table is derived and has no source CSV.

        schema_errors = []

        for table_name, definition in schema_tables.items():

            csv_path = ROOT / "data" / f"{table_name}.csv"

            if not csv_path.exists():

                if table_name == "daily_model_table":
                    continue

                schema_errors.append(
                    f"Missing source CSV: {table_name}.csv"
                )
                continue

            try:
                df = pd.read_csv(
                    csv_path,
                    dtype=str,
                    keep_default_na=False,
                )

                expected_columns = definition["columns"]
                actual_columns = df.columns.tolist()

                if actual_columns != expected_columns:
                    schema_errors.append(
                        f"{table_name}: expected {expected_columns}, "
                        f"found {actual_columns}"
                    )

            except Exception as exc:

                schema_errors.append(
                    f"{table_name}: {exc}"
                )

        check(
            len(schema_errors) == 0,
            "Source CSV columns match SQL schema definitions",
        )

        for error in schema_errors:
            print(f"SCHEMA DETAIL: {error}")

        # Check foreign-key references between source CSV files.

        print("\n--- FOREIGN KEY VALIDATION ---")

        foreign_key_errors = []
        foreign_key_count = 0

        for table_name, definition in schema_tables.items():

            child_path = ROOT / "data" / f"{table_name}.csv"

            if not child_path.exists():
                continue

            child_df = pd.read_csv(
                child_path,
                dtype=str,
                keep_default_na=False,
            )

            fk_pattern = re.compile(
                r"FOREIGN\s+KEY\s*\(\s*`?(\w+)`?\s*\)"
                r"\s*REFERENCES\s+`?(\w+)`?"
                r"\s*\(\s*`?(\w+)`?\s*\)",
                re.IGNORECASE,
            )

            for fk_match in fk_pattern.finditer(
                definition["body"]
            ):

                child_column = fk_match.group(1)
                parent_table = fk_match.group(2)
                parent_column = fk_match.group(3)

                parent_path = (
                    ROOT / "data" / f"{parent_table}.csv"
                    )

                foreign_key_count += 1

                if not parent_path.exists():
                    foreign_key_errors.append(
                        f"{table_name}.{child_column}: "
                        f"parent CSV {parent_table}.csv is missing"
                    )
                    continue

                parent_df = pd.read_csv(
                    parent_path,
                    dtype=str,
                    keep_default_na=False,
                )

                if child_column not in child_df.columns:
                    foreign_key_errors.append(
                        f"{table_name}: missing column {child_column}"
                    )
                    continue

                if parent_column not in parent_df.columns:
                    foreign_key_errors.append(
                        f"{parent_table}: missing column {parent_column}"
                    )
                    continue

                child_values = set(
                    child_df[child_column].astype(str)
                )

                parent_values = set(
                    parent_df[parent_column].astype(str)
                )

                # Empty values are allowed for nullable foreign keys.
                child_values.discard("")

                invalid_values = child_values - parent_values

                if invalid_values:
                    foreign_key_errors.append(
                        f"{table_name}.{child_column}: "
                        f"{len(invalid_values)} unmatched values "
                        f"referencing {parent_table}.{parent_column}"
                    )

        check(
            foreign_key_count > 0,
            "SQL schema contains foreign-key definitions",
        )

        check(
            len(foreign_key_errors) == 0,
            "All source CSV foreign-key references are valid",
        )

        for error in foreign_key_errors:
            print(f"FOREIGN KEY DETAIL: {error}")


    # ============================================================
    # 14. FINAL REPORT
    # ============================================================

        print("\n" + "=" * 65)
        print("RESTRODINE VALIDATION SUMMARY")
        print("=" * 65)

        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total:  {passed + failed}")

        if failed:
            print("\nRESULT: VALIDATION FAILED")
        else:
            print("\nRESULT: ALL ANALYTICAL CHECKS PASSED")

        return failed == 0


# ============================================================
# PYTEST FUNCTION
# ============================================================

def test_project_validation():
    assert run_validation(), "RestroDine analytical validation failed"


if __name__ == "__main__":
    sys.exit(0 if run_validation() else 1)