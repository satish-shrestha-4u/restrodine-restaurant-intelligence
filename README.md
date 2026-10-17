# RestroDine Synthetic Dataset

Historical synthetic restaurant dataset for 2025-01-01 to 2025-12-31.

## Design rules

- `is_weekend` = standard Saturday/Sunday calendar definition.
- `restaurant_peak_day` = Friday/Saturday restaurant-specific peak demand.
- Customer registration dates can precede 2025 because the restaurant already has an existing customer base.
- For every customer who ordered, `registration_date <= first_order_date`.
- Employees include names, roles, employment type, hourly cost and employment status.
- Weather is synthetic historical data; the project can later integrate real API observations/forecasts.
- Demand includes weekday effects, Friday/Saturday peaks, meal periods, holidays, promotions and weather effects.

## Database setup

This project uses **MySQL**. Use Python 3.11 for this project (the same version used by GitHub Actions). Start your local MySQL Server; the Workbench connection should show as connected. Then run these commands from a terminal in the project folder:

```bash
conda create -n restrodine-mysql python=3.11 -y
conda activate restrodine-mysql
python -m pip install -r requirements.txt
python load_database.py
```

The loader uses MySQL on `127.0.0.1:3306`, connects as `root` by default, and prompts for the MySQL password. To use another local MySQL username, set `MYSQL_USER` before running it. Optional connection settings are `MYSQL_HOST` and `MYSQL_PORT`.

The loader creates the `restrodine` database, creates the tables from `data/schema.sql`, imports the CSV files from `data/`, and runs integrity checks. **Running it again drops and rebuilds the project's RestroDine tables and reloads the CSVs.** Use a dedicated `restrodine` database; do not point it at a database containing other work.

After it finishes, refresh the Schemas panel in MySQL Workbench and expand `restrodine`.

The existing `restrodine.db` file is an older SQLite snapshot. The MySQL loader does not read or modify it.

## Core workflow

Data Sources -> MySQL -> Cleaning/Validation -> Feature Engineering -> Revenue Intelligence -> Workforce Intelligence -> Customer Intelligence -> Streamlit -> Management Decisions

## Forecasting

Target: daily revenue. Compare a baseline with Prophet and SARIMAX. Use a chronological train/test split.

Metrics: MAE, RMSE, MAPE.

## Tables

customers, products, employees, employee_availability, shifts, orders, order_items, payments, promotions, calendar, weather, reviews, daily_revenue
