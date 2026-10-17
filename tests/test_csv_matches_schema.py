"""Offline check (no MySQL needed): every CSV matches data/schema.sql - column names AND order,
types, lengths, NOT NULL, DECIMAL precision, dates, foreign-key values.  Run: python -m pytest tests -q"""
import re
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"


def parse_schema():
    text = re.sub(r"--[^\n]*", "", (DATA / "schema.sql").read_text(encoding="utf-8"))
    tables = {}
    for name, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\) ENGINE", text, flags=re.S):
        cols = []
        for line in re.split(r",\s*\n", body):
            line = line.strip()
            if not line or re.match(r"(PRIMARY|KEY|CONSTRAINT)", line):
                continue
            m = re.match(r"`?(\w+)`?\s+(\w+)(?:\(([\d,]+)\))?(.*)", line)
            cols.append(dict(name=m[1], type=m[2].upper(), arg=m[3], notnull="NOT NULL" in m[4].upper()))
        tables[name] = cols
    return tables


def check_table(name, cols):
    df = pd.read_csv(DATA / f"{name}.csv", dtype=str, keep_default_na=False)
    errs = []
    if list(df.columns) != [c["name"] for c in cols]:
        return [f"{name}: column order/names differ: csv={list(df.columns)}"]
    for c in cols:
        s = df[c["name"]]; nn = s[s != ""]
        if c["notnull"] and len(nn) != len(s):
            errs.append(f"{name}.{c['name']}: NULL in NOT NULL column")
        t = c["type"]
        if t in ("INT", "TINYINT"):
            if not nn.str.fullmatch(r"-?\d+").all(): errs.append(f"{name}.{c['name']}: non-integer")
        elif t == "DECIMAL":
            p, sc = map(int, c["arg"].split(","))
            if not nn.str.fullmatch(r"-?\d+(\.\d+)?").all(): errs.append(f"{name}.{c['name']}: non-numeric")
            else:
                v = nn.astype(float)
                if (v.abs() >= 10 ** (p - sc)).any(): errs.append(f"{name}.{c['name']}: exceeds DECIMAL({p},{sc})")
                if (nn.str.split(".").str[1].fillna("").str.len() > sc).any(): errs.append(f"{name}.{c['name']}: too many decimals")
        elif t == "DATE":
            if pd.to_datetime(nn, format="%Y-%m-%d", errors="coerce").isna().any(): errs.append(f"{name}.{c['name']}: bad date")
        elif t == "DATETIME":
            if pd.to_datetime(nn, format="%Y-%m-%d %H:%M:%S", errors="coerce").isna().any(): errs.append(f"{name}.{c['name']}: bad datetime")
        elif t == "TIME":
            if not nn.str.fullmatch(r"\d{2}:\d{2}(:\d{2})?").all(): errs.append(f"{name}.{c['name']}: bad time")
        elif t == "VARCHAR":
            if (nn.str.len() > int(c["arg"])).any(): errs.append(f"{name}.{c['name']}: longer than VARCHAR({c['arg']})")
    return errs


def test_all_csvs_match_schema():
    schema = parse_schema()
    errs = []
    for t, cols in schema.items():
        errs += check_table(t, cols)
    assert not errs, "\n".join(errs)


def test_foreign_keys():
    rd = lambda t: pd.read_csv(DATA / f"{t}.csv", dtype=str, keep_default_na=False)
    fk = [("orders", "customer_id", "customers", "customer_id"), ("order_items", "order_id", "orders", "order_id"),
          ("order_items", "product_id", "products", "product_id"), ("payments", "order_id", "orders", "order_id"),
          ("shifts", "employee_id", "employees", "employee_id"), ("employee_availability", "employee_id", "employees", "employee_id"),
          ("reviews", "customer_id", "customers", "customer_id"), ("reviews", "order_id", "orders", "order_id"),
          ("review_aspect_labels", "review_id", "reviews", "review_id")]
    for ct, cc, pt, pc in fk:
        child = rd(ct)[cc]; child = child[child != ""]
        assert child.isin(rd(pt)[pc]).all(), f"{ct}.{cc} -> {pt}.{pc} has orphans"


if __name__ == "__main__":
    test_all_csvs_match_schema(); test_foreign_keys(); print("OK: CSVs match schema.sql")
