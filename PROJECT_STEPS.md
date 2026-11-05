# RestroDine — Project Development Steps

## Project Overview

RestroDine is a restaurant intelligence and forecasting project built around synthetic point-of-sale, customer, workforce, menu and weather datasets.

The project combines:

1. Data engineering and data quality
2. Revenue intelligence and forecasting
3. Workforce intelligence
4. Customer intelligence
5. Menu performance and engineering
6. Streamlit application development
7. Automated analytical validation

**Dataset coverage:** 2024-01-01 to 2025-12-31 (731 days).

**Data disclosure:** All project datasets are synthetic. They must not be presented as actual restaurant operating data.

---

# PHASE 1 — DATA FOUNDATION AND ENGINEERING

## 1. Establish the project structure

The current repository contains:

```text
RestroDine/
│
├── app.py
├── data/
├── data_clean/
├── notebooks/
├── outputs/
├── models/
├── metadata/
├── tests/
├── load_database.py
├── requirements.txt
├── README.md
└── PROJECT_STEPS.md
```

The Streamlit application is located in the project root as `app.py`.

Reusable application modules have not been separated into a `src/` package. Do not create empty folders simply to make the architecture appear more complex.

## 2. Establish the synthetic dataset

Original data is stored in `data/`.

The project covers:

- 56,088 orders
- 220,112 order items
- 5,000 customers
- 30 products
- 30 employees
- 8,696 shifts
- 4,306 reviews
- 731 calendar days

The source datasets include:

- Categories
- Calendar
- Customers
- Daily revenue
- Employee availability
- Employees
- Order items
- Orders
- Payments
- Products
- Promotions
- Review aspect labels
- Reviews
- Shifts
- Weather

Keep the synthetic data disclosure in all project documentation.

## 3. Build the relational database

The project includes:

- `data/schema.sql`
- `load_database.py`
- Original CSV datasets

The loader creates the project database, loads the CSV data and performs integrity checks.

Important: the loader drops and recreates project tables. Run it only against a dedicated RestroDine database.

## 4. Clean and validate the data

The cleaned datasets are stored in `data_clean/`.

Main cleaning and preparation notebook:

```text
notebooks/01a_data_cleaning.ipynb
```

The cleaned data is used for subsequent analytical workflows.

Validation requirements:

- Primary identifiers are unique.
- Foreign-key references are valid.
- Numeric values are valid.
- Revenue reconciles with order-item totals.
- Product costs and selling prices are non-negative.
- Dates are valid and consistent.
- Missing values are handled appropriately.
- Analytical datasets have the required columns.

## 5. Establish the database and data documentation

Current database documentation:

- `data/schema.sql`
- `EER_Diagram.png`

The EER diagram describes the relational structure.

The original editable workflow diagram was not present in the inspected repository and should only be added if it is recovered or recreated.

---

# PHASE 2 — REVENUE INTELLIGENCE

## 6. Perform revenue EDA and feature engineering

Notebook:

```text
notebooks/01b_revenue_eda_and_feature_engineering.ipynb
```

Areas of analysis include:

- Monthly revenue
- Weekday revenue
- Order volume
- Average order value
- Meal-period performance
- Temperature and precipitation relationships
- Holiday and calendar effects
- Promotion activity
- Product revenue and profitability

Business-specific peak days should be represented through the appropriate restaurant feature rather than changing the meaning of a standard calendar weekend.

## 7. Define the forecasting target

The primary revenue target is:

```text
Daily Revenue (€)
```

Daily revenue is appropriate for the first revenue forecasting experiment.

Workforce planning also requires a separate view of expected order demand.

## 8. Develop revenue intelligence

Notebook:

```text
notebooks/02_revenue_intelligence.ipynb
```

The revenue intelligence workflow covers historical performance analysis and forecasting.

The saved forecasting artifact is:

```text
models/restrodine_prophet_calendar_weather.json
```

Associated metadata:

```text
metadata/restrodine_prophet_calendar_weather_metadata.json
```

The project includes a 14-day revenue forecast:

```text
outputs/revenue_forecast_next_14_days.csv
```

The model and its outputs should be evaluated using chronological validation rather than random train/test shuffling.

## 9. Evaluate forecasting performance

Forecast evaluation should use appropriate time-series metrics:

- MAE
- RMSE
- MAPE, where appropriate and where actual values are non-zero

A useful model comparison should include:

- Previous-day baseline
- Historical mean or weekday baseline
- Prophet
- SARIMAX, if implemented and evaluated

Do not publish placeholder values as actual results.

The research question is:

> Does incorporating weather and calendar information improve revenue forecasting compared with historical sales information alone?

Answer this only after a controlled comparison using the same test period and evaluation procedure.

**Current implementation note:** The repository contains a saved Prophet model with calendar and weather-related metadata. A complete, independently verified baseline-versus-Prophet-versus-SARIMAX comparison is not established by the existence of the model file alone.

---

# PHASE 3 — WORKFORCE INTELLIGENCE

## 10. Convert forecast demand into staffing requirements

Notebook:

```text
notebooks/03_workforce_intelligence.ipynb
```

The workforce workflow connects expected demand with staffing requirements.

Conceptual process:

```text
Revenue and Order Forecast
          |
          v
Expected Customer Demand
          |
          v
Required Staffing
          |
          v
Scheduled Workforce
          |
          v
Staffing Coverage and Gaps
```

Staffing rules should be transparent and based on the synthetic demand distribution.

Any order thresholds and staffing ratios are project assumptions, not universal industry standards.

## 11. Calculate workforce and labour indicators

The workforce analysis includes:

- Expected orders
- Required staff
- Scheduled employees
- Labour hours
- Labour costs
- Labour cost as a percentage of forecast revenue
- Staffing coverage
- Staffing gaps

Key outputs:

```text
outputs/workforce_forecast_next_14_days.csv
outputs/staffing_coverage.csv
outputs/staffing_gaps.csv
outputs/recommended_roster.csv
```

The calculations should reconcile with the underlying data and use consistent definitions.

## 12. Review roster recommendations

A roster recommendation should account for:

- Employee status
- Employee role
- Availability
- Existing shifts
- Working-hour constraints
- Labour costs

Do not describe a roster as fully optimized unless the scheduling logic has been tested against the relevant operational and employment constraints.

---

# PHASE 4 — CUSTOMER INTELLIGENCE

## 13. Analyse customer reviews

Notebook:

```text
notebooks/04_customer_intelligence.ipynb
```

Customer intelligence examines review ratings, feedback and customer segments.

Relevant analytical areas:

- Review rating distribution
- Review trends
- Positive, neutral and negative sentiment
- Aspect-level sentiment
- Customer feedback categories
- Customer RFM segmentation
- Customer improvement areas

## 14. Perform aspect-level analysis

Restaurant aspects include:

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
Review:
"The food was excellent and the waiter was friendly,
but we waited almost 40 minutes."
```

Illustrative aspect interpretation:

```text
Food          -> Positive
Service       -> Positive
Waiting Time  -> Negative
```

The supplied `review_aspect_labels.csv` provides ground-truth labels for evaluation.

Do not use the ground-truth labels as independent evidence of real-world customer sentiment.

## 15. Review customer intelligence outputs

Important outputs include:

```text
outputs/customer_aspect_sentiment_summary.csv
outputs/customer_rfm_segments.csv
outputs/customer_feedback_by_segment.csv
outputs/customer_feedback_by_type.csv
outputs/customer_improvement_areas.csv
outputs/customer_monthly_sentiment.csv
outputs/customer_ratings_by_type.csv
outputs/customer_review_aspect_detail.csv
outputs/customer_segment_profile.csv
outputs/high_value_negative_feedback.csv
outputs/customer_intelligence_kpis.csv
```

Customer intelligence should translate analytical findings into useful management information.

---

# PHASE 5 — MENU INTELLIGENCE

## 16. Analyse menu performance

Notebook:

```text
notebooks/05_menu_intelligence.ipynb
```

Analyse:

- Product sales volume
- Revenue by product
- Revenue by category
- Product costs
- Gross profit
- Gross margin
- Discount performance
- Weekday performance
- Monthly performance

## 17. Apply menu engineering

Menu engineering classifies products into four groups:

| Class | Popularity | Profitability |
|---|---|---|
| Star | High | High |
| Plowhorse | High | Low |
| Puzzle | Low | High |
| Dog | Low | Low |

The classifications use project-specific thresholds.

Gross profit is calculated as revenue less product costs. It excludes operating expenses such as labour, rent and utilities.

## 18. Review menu intelligence outputs

Important outputs include:

```text
outputs/menu_product_performance.csv
outputs/menu_category_performance.csv
outputs/menu_class_summary.csv
outputs/menu_discount_performance.csv
outputs/menu_engineering.csv
outputs/menu_intelligence_kpis.csv
outputs/menu_monthly_performance.csv
outputs/menu_recommendations.csv
outputs/menu_weekday_performance.csv
```

---

# PHASE 6 — STREAMLIT APPLICATION

## 19. Build and maintain the application

Application entry point:

```text
app.py
```

The current application has five main modules:

1. Executive Overview
2. Revenue Intelligence
3. Workforce Intelligence
4. Customer Intelligence
5. Menu Performance

The application consumes precomputed outputs and saved model artifacts.

It should not retrain Prophet every time the Streamlit application reruns.

## 20. Validate each application module

### Executive Overview

Check that key performance indicators load and display correctly.

### Revenue Intelligence

Check:

- Historical revenue
- Forecast dates
- Forecast values
- Forecast intervals
- Revenue visualizations

### Workforce Intelligence

Check:

- Expected orders
- Required staff
- Scheduled employees
- Staffing shortfalls
- Labour cost indicators

### Customer Intelligence

Check:

- Ratings
- Sentiment
- Aspect summaries
- RFM segments
- Customer feedback indicators

### Menu Performance

Check:

- Product performance
- Category performance
- Gross profit
- Gross margin
- Menu engineering classifications

### General application checks

- No missing input files.
- No broken page navigation.
- No misleading metric labels.
- No unhandled empty-data cases.
- Clear disclosure of synthetic data.
- Consistent formatting of monetary values and percentages.

---

# PHASE 7 — TESTING AND QUALITY ASSURANCE

## 21. Maintain the consolidated pytest suite

Main test file:

```text
tests/test_project_validation.py
```

Run locally:

```bash
python -m pytest tests/test_project_validation.py -v -s
```

The current suite contains 72 passing validation checks.

Coverage includes:

1. CSV readability
2. Revenue reconciliation
3. Product profitability
4. Revenue forecast validation
5. Workforce forecast validation
6. Staffing coverage
7. Staffing gaps
8. Customer sentiment percentages
9. RFM segment labels
10. Menu performance
11. Menu engineering
12. Model and metadata artifacts
13. SQL schema validation
14. Foreign-key integrity

Latest verified local result:

```text
Passed: 72
Failed: 0
Total:  72

RESULT: ALL ANALYTICAL CHECKS PASSED
```

Passing tests confirm that the current outputs satisfy the implemented checks. They do not prove that every forecasting assumption or business rule is statistically or operationally optimal.

## 22. Maintain GitHub Actions

Workflow:

```text
.github/workflows/ci.yml
```

The CI workflow is designed to:

- Check out the repository
- Set up Python
- Install dependencies
- Check Python syntax
- Check the SQL schema
- Check forecasting model artifacts
- Validate source CSV files
- Run the consolidated pytest suite

Verify the workflow on GitHub after pushing changes.

---

# PHASE 8 — DOCUMENTATION AND REPRODUCIBILITY

## 23. Maintain the README

The README should explain:

- Business problem
- Synthetic dataset
- Analytical modules
- Technical architecture
- Repository structure
- Installation
- Application launch
- Optional database setup
- Testing
- Assumptions and limitations
- Future improvements

## 24. Maintain project documentation

Important documentation:

```text
README.md
PROJECT_STEPS.md
EER_Diagram.png
data/schema.sql
```

Documentation must describe implemented features accurately and clearly distinguish future work from completed work.

## 25. Final reproducibility check

A new user should be able to:

1. Clone the repository.
2. Create a Python environment.
3. Install dependencies.
4. Run the Streamlit application.
5. Run the pytest validation suite.
6. Understand the synthetic data and analytical limitations.
7. Optionally configure MySQL and load the source datasets.

---

# PHASE 9 — FUTURE IMPROVEMENTS

These are potential extensions rather than confirmed completed features.

## 26. Forecasting improvements

- Backtest multiple forecasting approaches.
- Compare baseline models with Prophet.
- Implement and evaluate SARIMAX if justified.
- Evaluate weather and calendar feature contributions.
- Improve forecast monitoring and error analysis.

## 27. Weather API integration

Potential future architecture:

```text
Weather API
     |
     v
Future Weather Data
     |
     v
Forecast Model Regressors
     |
     v
Revenue Forecast
     |
     v
Staffing Recommendation
```

Historical synthetic weather should remain consistent with the historical model-development data.

## 28. Workforce optimization

Potential improvements:

- More detailed role-level staffing rules
- Availability-aware roster optimization
- Working-hour constraints
- Scenario analysis
- Improved labour cost optimization

## 29. Customer intelligence improvements

Potential improvements:

- More robust NLP evaluation
- Aspect extraction improvements
- Model comparison
- Review topic discovery
- Customer feedback alerts

## 30. Additional business intelligence

Potential extensions:

- Inventory and waste analysis
- Promotion effectiveness
- Scenario simulation
- Operational alerts
- Menu pricing analysis

Prioritize features based on business value rather than adding complexity for its own sake.

---

# PROJECT COMPLETION PRINCIPLES

RestroDine should be judged on more than the number of models or features.

A strong final project should demonstrate:

- Reproducible data processing
- Correct financial calculations
- Appropriate forecasting evaluation
- Transparent staffing assumptions
- Meaningful customer and menu insights
- Reliable application behaviour
- Automated testing
- Clear technical documentation
- Honest disclosure of synthetic data and project limitations

The central objective is to demonstrate how restaurant data can be transformed into understandable, testable and actionable management intelligence.
