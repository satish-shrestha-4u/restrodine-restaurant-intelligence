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

## Core workflow
Data Sources -> SQLite -> Cleaning/Validation -> Feature Engineering -> Revenue Intelligence -> Workforce Intelligence -> Customer Intelligence -> Streamlit -> Management Decisions

## Forecasting
Target: daily revenue. Compare a baseline with Prophet and SARIMAX. Use a chronological train/test split. Metrics: MAE, RMSE, MAPE.

## Tables
customers, products, employees, employee_availability, shifts, orders, order_items, payments, promotions, calendar, weather, reviews, daily_revenue
