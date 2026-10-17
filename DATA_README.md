# RestroDine Data Layer

Synthetic educational restaurant data for RestroDine.

Period: 2025-01-01 to 2025-12-31.

The CSV files in `data/` load into the MySQL database `restrodine` using `load_database.py` and the MySQL table definitions in `data/schema.sql`.

Tables:
categories, customers, products, employees, employee_availability, shifts,
calendar, weather, promotions, orders, order_items, payments, reviews,
daily_revenue.

Relationships are enforced with MySQL foreign keys. `calendar` links dated
records, including orders, shifts, reviews, promotions, weather, and daily
revenue. `daily_revenue.date` links to both `calendar.date` and `weather.date`.
`categories` links products to the categories targeted by promotions. Customer,
employee, order, and product relationships connect the operational tables.
The loader derives `orders.order_date` from the existing `order_datetime` CSV
column. The MySQL `daily_revenue` table stores only date and revenue measures;
calendar and weather details are joined from their respective tables. The
source CSV files remain unchanged.

The transactions use business rules rather than independent random values:
weekends/holidays increase demand, rainy days reduce demand, lunch/dinner
peaks are represented, and realistic product combinations are simulated.

The initial weather table is synthetic. Later it can be augmented/replaced
with historical weather API data for the forecasting experiment.
