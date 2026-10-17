# RestroDine — Exact Build Sequence

## 0. Do not change the data model yet
Use the supplied dataset as the project baseline. Do not regenerate random values manually inside notebooks.

Historical period: **2025-01-01 to 2025-12-31**.

The dataset is synthetic. Be explicit about that in the README and presentation.

---

## 1. Create the project structure

```text
RestroDine/
├── data/
│   ├── *.csv
│   └── schema.sql
├── load_database.py
├── notebooks/
├── src/
├── app/
├── models/
├── outputs/
├── tests/
├── requirements.txt
└── README.md
```

Use the supplied `data/` directory and CSV files. `load_database.py` creates and fills the MySQL database. The existing `restrodine.db` is an older SQLite snapshot and is not used by the MySQL workflow.

Recommended source modules later:

```text
src/
├── database.py
├── data_validation.py
├── feature_engineering.py
├── forecasting.py
├── workforce.py
├── sentiment.py
└── simulation.py
```

---

# PHASE 1 — REVENUE INTELLIGENCE

## 2. Create and inspect the MySQL database

Start your local MySQL Server. Create and activate a Python 3.11 environment with `conda create -n restrodine-mysql python=3.11 -y` and `conda activate restrodine-mysql`, install requirements with `python -m pip install -r requirements.txt`, then run `python load_database.py`. The loader prompts for the MySQL password, creates the dedicated `restrodine` database, imports the CSVs, and runs integrity checks. Each run drops and recreates the project tables, so use this only with the dedicated `restrodine` database.

Refresh the Schemas panel in MySQL Workbench and confirm these tables:

- customers
- products
- employees
- employee_availability
- shifts
- orders
- order_items
- payments
- promotions
- calendar
- weather
- reviews
- daily_revenue

Do not start modelling before the database passes validation.

---

## 3. Run data-integrity checks

Check:

1. Primary IDs are unique.
2. Every `order_items.order_id` exists in `orders`.
3. Every `order_items.product_id` exists in `products`.
4. Every payment belongs to an order.
5. Sum of order-item `line_total` equals `orders.order_total`.
6. Payment amount equals order total.
7. Customer registration date is on/before first order date.
8. Calendar contains all 365 historical dates.
9. Weather contains all 365 historical dates.
10. Employee labour cost equals hours × hourly cost.

The supplied dataset already passes these automated checks.

---

## 4. Build the daily revenue table yourself once

For the actual analysis, demonstrate the SQL aggregation instead of relying only on the precomputed `daily_revenue.csv`.

Conceptually:

```sql
SELECT
    DATE(order_datetime) AS date,
    SUM(order_total) AS revenue,
    COUNT(DISTINCT order_id) AS orders,
    AVG(order_total) AS average_order_value
FROM orders
GROUP BY DATE(order_datetime)
ORDER BY date;
```

Then join the result with `calendar` and `weather`.

---

## 5. Perform EDA

Create at least:

- Revenue by month
- Revenue by weekday
- Orders by weekday
- Friday/Saturday vs Monday demand
- Revenue by meal period
- Average order value over time
- Revenue vs temperature
- Revenue on rainy vs non-rainy days
- Revenue on holidays vs normal days
- Promotion-period revenue
- Top-selling products
- Revenue and gross-margin proxy by product

Important project observation to investigate:

> Friday and Saturday are restaurant-specific peak days even though only Saturday/Sunday are standard calendar weekends.

Do not redefine `is_weekend`. Use `restaurant_peak_day` for this business-specific feature.

---

## 6. Define the Phase-1 target

Primary target:

```text
Daily Revenue (€)
```

Use daily revenue rather than individual orders for the first forecasting experiment.

Later, workforce planning can forecast **orders/customer demand** separately.

---

## 7. Create a chronological train/test split

Example:

```text
Training: 2025-01-01 → 2025-10-31
Test:     2025-11-01 → 2025-12-31
```

Never randomly shuffle the time series.

---

## 8. Build a baseline

Start with simple forecasting methods:

- Previous-day revenue
- 7-day moving average / recent mean
- Same weekday historical mean

The baseline answers:

> Does a sophisticated forecasting model actually improve on a simple historical approach?

---

## 9. Build Prophet

First model:

```text
Revenue → Prophet
```

Then investigate whether adding external regressors improves performance:

```text
Revenue
 + temperature
 + precipitation
 + rainy flag
 + holiday flag
 + restaurant peak-day flag
```

For future forecasts, external regressors must also be available for the future dates. This is where the weather API becomes important.

---

## 10. Build SARIMAX

Use SARIMAX when external variables are included:

```text
SARIMAX
  target: daily revenue
  exogenous variables:
      temperature
      precipitation
      holiday
      restaurant_peak_day
```

Compare it against the baseline and Prophet.

Do not add random ML models simply to make the project look more advanced. The instructor-approved Phase 1 does not require ML.

---

## 11. Evaluate the models

Use:

- MAE
- RMSE
- MAPE

Create one comparison table:

| Model | MAE | RMSE | MAPE |
|---|---:|---:|---:|
| Previous-day baseline | ... | ... | ... |
| Historical mean | ... | ... | ... |
| Prophet | ... | ... | ... |
| SARIMAX | ... | ... | ... |

Then answer:

> Does weather/calendar information improve forecasting compared with historical sales alone?

That is the central Phase-1 research question.

---

# PHASE 2 — WORKFORCE INTELLIGENCE

## 12. Convert demand into staffing requirements

Do not jump directly from revenue to employees.

Use:

```text
Revenue / Order Forecast
        ↓
Expected Customer Demand
        ↓
Required Staffing
```

Start with transparent rule-based staffing.

Example structure:

```text
< 60 orders       → Low staffing
60–100 orders     → Standard staffing
101–150 orders    → High staffing
> 150 orders      → Very high staffing
```

Tune the thresholds after inspecting the synthetic demand distribution.

---

## 13. Add role requirements

Example:

```text
Low:
1 manager
2 kitchen
3 service

Standard:
1 manager
2–3 kitchen
4 service
1 bartender

High:
1 manager
3 kitchen
5–6 service
1–2 bartender

Very High:
1–2 manager
4 kitchen
7–8 service
2 bartender
```

These are starting rules, not final truths. Explain that they are a prototype staffing policy.

---

## 14. Build roster recommendation

For a selected future date:

```text
Forecast demand
      ↓
Required roles
      ↓
Employee availability
      ↓
Employment status
      ↓
Employment type
      ↓
Existing schedule
      ↓
Recommended roster
      ↓
Labour cost
```

Do not schedule inactive employees.

Respect availability and basic working-hour constraints.

---

# PHASE 3 — CUSTOMER INTELLIGENCE

## 15. Start with review sentiment

Input:

```text
review_text
```

Output:

```text
Positive / Neutral / Negative
```

Then add confidence if the selected NLP approach provides it.

---

## 16. Add aspect analysis

Extract restaurant-specific aspects:

- Food
- Service
- Staff
- Price
- Atmosphere
- Waiting Time
- Drinks
- Cleanliness

Example:

```text
“The food was excellent and the waiter was friendly,
but we waited almost 40 minutes.”
```

Expected analytical result:

```text
Food         → Positive
Service      → Positive
Waiting Time → Negative
```

This is much more valuable to management than only assigning one overall sentiment label.

---

# 17. Build the Streamlit application

Recommended pages:

```text
Dashboard
Revenue Forecast
Workforce / Roster
Customer Intelligence
Menu Intelligence
Simulation
```

### Dashboard
Show:

- Today's / selected-period revenue
- Orders
- AOV
- Forecast
- Labour cost
- Customer sentiment
- Important alerts

### Revenue Forecast
Show:

- Historical revenue
- Forecast
- Confidence interval
- Weather
- Model comparison

### Workforce
Show:

- Forecast demand
- Required staff
- Recommended roster
- Labour cost
- Staffing gap

### Customer Intelligence
Show:

- Overall sentiment
- Rating distribution
- Aspect sentiment
- Most common negative issues

### Menu
Show:

- Top-selling products
- Revenue by category
- Product margin proxy
- Potential menu-engineering analysis

### Simulation
Eventually:

```text
Simulate Next Day
        ↓
Generate new transactions
        ↓
Insert into MySQL
        ↓
Update analytics
        ↓
Update forecast input
        ↓
Update staffing recommendation
```

---

# 18. Weather API integration

Only after the historical pipeline works.

Use the synthetic `weather` table for historical model development.

Then connect a real weather API for future dates:

```text
Weather API
     ↓
Future temperature / precipitation
     ↓
Forecast model regressors
     ↓
Revenue forecast
     ↓
Staffing recommendation
```

Do not rebuild historical data every time the API is called.

---

# 19. Final integrated workflow

```text
Historical POS Data
       ↓
MySQL
       ↓
Cleaning + Validation
       ↓
Feature Engineering
       ↓
Revenue Forecast
       ↓
Expected Demand
       ↓
Staffing Requirement
       ↓
Roster Recommendation
       ↓
Restaurant Operations
       ↓
Customer Reviews
       ↓
Sentiment + Aspect Analysis
       ↓
Streamlit Dashboard
       ↓
Management Decisions
```

---

# 20. What to finish before adding optional features

Core project is complete only when these work:

- [ ] Database validated
- [ ] Revenue EDA completed
- [ ] Baseline forecast completed
- [ ] Prophet completed
- [ ] SARIMAX completed
- [ ] Models evaluated with MAE/RMSE/MAPE
- [ ] Weather API integrated
- [ ] Staffing rules implemented
- [ ] Roster recommendation implemented
- [ ] Labour cost calculated
- [ ] Review sentiment implemented
- [ ] Aspect analysis implemented
- [ ] Streamlit pages connected to MySQL
- [ ] End-to-end workflow tested

Only then add one optional extension such as inventory/waste, menu engineering, promotion effectiveness, alerts, or receipt OCR.
'''
# add guide to zip
