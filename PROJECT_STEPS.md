🍽️ RestroDine — Project Development & Implementation Steps
📌 Project Overview
RestroDine is an end-to-end restaurant intelligence and weather-aware revenue forecasting project built around synthetic point-of-sale, customer, workforce, menu and weather datasets.

The project demonstrates how restaurant data can be transformed into structured analytical outputs, revenue forecasts, workforce recommendations, customer insights and menu performance analysis.

The final application brings these capabilities together through an interactive Streamlit dashboard.
🎯 Project objectives
The project combines:
1. Data engineering and data quality
2. Business performance analytics
3. Revenue forecasting and model evaluation
4. Weather API integration
5. Workforce planning and optimization
6. Customer segmentation and experience analytics
7. Menu performance and engineering
8. Streamlit application development
9. Automated analytical validation
10. Documentation and reproducibility
Dataset coverage: 1 January 2024 – 31 December 2025 (731 days).

Data disclosure: All project datasets are synthetic. They must not be presented as actual restaurant operating data.
🧱 PHASE 1 — DATA FOUNDATION AND ENGINEERING
1. 📁 Establish the project structure
The project repository contains the following main components:
RestroDine/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── app.py
├── forecast_pipeline.py
├── load_database.py
│
├── data/
│   ├── *.csv
│   └── schema.sql
│
├── data_clean/
│   └── *_clean.csv
│
├── notebooks/
│   ├── 01a_data_cleaning.ipynb
│   ├── 01b_revenue_eda_and_feature_engineering.ipynb
│   ├── 02_revenue_intelligence.ipynb
│   ├── 03_workforce_intelligence.ipynb
│   ├── 04_customer_intelligence.ipynb
│   └── 05_menu_intelligence.ipynb
│
├── outputs/
│   └── *.csv
│
├── models/
│   └── restrodine_prophet_calendar_weather.json
│
├── metadata/
│   ├── customer_intelligence_summary.json
│   ├── forecast_refresh_metadata.json
│   └── restrodine_prophet_calendar_weather_metadata.json
│
├── tests/
│   └── test_project_validation.py
│
├── requirements.txt
├── PROJECT_STEPS.md
├── EER_Diagram.png
└── README.md
The Streamlit application is located in the project root as app.py.

The forecasting and workforce output generation logic is maintained in forecast_pipeline.py.
2. 🗂️ Establish the synthetic dataset
Original data is stored in data/.

The project covers:
Dataset characteristic	Records
Orders	56,088
Order items	220,112
Customers	5,000
Products	30
Employees	30
Shifts	8,696
Customer reviews	4,306
Calendar days	731


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
All datasets are synthetic. Weather data is calibrated to western German climate patterns and must not be represented as actual historical weather measurements.
3. 🛢️ Build the relational database
The project includes:
- data/schema.sql
- load_database.py
- Original CSV datasets
The database workflow creates the relational database, loads the CSV data and performs integrity checks.

The database structure is documented through EER_Diagram.png.

Important: The database loader drops and recreates project tables. It must only be executed against a dedicated RestroDine database.
4. 🧹 Clean and validate the data
The cleaned datasets are stored in data_clean/.

Main preparation notebook:

notebooks/01a_data_cleaning.ipynb

The cleaning and preparation workflow includes:
- Handling missing values
- Correcting data types
- Validating identifiers
- Checking duplicate records
- Checking foreign-key relationships
- Validating dates and numeric fields
- Preparing datasets for analytical workflows
✅ Data quality requirements
- Primary identifiers must be unique.
- Foreign-key references must be valid.
- Numeric values must be within appropriate ranges.
- Revenue must reconcile with order-item totals.
- Product costs and selling prices must be non-negative.
- Dates must be valid and consistent.
- Missing values must be handled appropriately.
- Analytical datasets must contain the required columns.
5. 🧩 Establish database and data documentation
Database documentation includes:
- data/schema.sql
- EER_Diagram.png
The EER diagram describes the relational structure and relationships between the main operational entities.
📊 PHASE 2 — BUSINESS PERFORMANCE AND REVENUE INTELLIGENCE
6. 🔎 Perform revenue EDA and feature engineering
Notebook:

notebooks/01b_revenue_eda_and_feature_engineering.ipynb

The exploratory analysis examines:
- Monthly revenue
- Weekday revenue
- Order volume
- Average order value
- Meal-period performance
- Temperature and precipitation relationships
- Holiday and calendar effects
- Promotion activity
- Product revenue and profitability
Feature engineering prepares the historical data for forecasting and subsequent business analysis.

Business-specific peak days are represented through the appropriate restaurant features rather than changing the meaning of standard calendar weekends.
7. 🎯 Define the forecasting targets
The main revenue forecasting target is:

Daily Revenue (€)

The forecasting workflow also supports the demand information required for workforce planning.

Expected order demand is used to translate forecast business activity into operational staffing requirements.
8. 📈 Develop and evaluate revenue forecasting models
Notebook:

notebooks/02_revenue_intelligence.ipynb

The revenue forecasting work includes the development and evaluation of forecasting approaches.

The model evaluation process includes historical baseline comparisons and statistical forecasting models, including SARIMAX and Prophet.

Forecasting evaluation uses chronological validation rather than random train/test shuffling.

Relevant evaluation metrics include:
- MAE
- RMSE
- MAPE, where appropriate and where actual values are non-zero
The comparison of forecasting approaches is intended to assess predictive performance using a consistent evaluation period and methodology.
🤖 Forecasting model artifact
models/restrodine_prophet_calendar_weather.json
📝 Model metadata
metadata/restrodine_prophet_calendar_weather_metadata.json
📅 Main forecast output
outputs/revenue_forecast_next_14_days.csv
The application uses the saved model artifact and precomputed analytical outputs rather than retraining the model during every Streamlit interaction.
9. 🌦️ Integrate weather information into forecasting
Weather information is incorporated into the forecasting workflow through weather-related data and API integration.

The purpose is to make weather information available as an input to revenue forecasting and to investigate its relationship with restaurant demand and revenue.

The forecasting workflow combines relevant calendar and weather information with historical restaurant performance.

Weather-related associations must be interpreted carefully. They do not establish that weather causes changes in revenue.
👥 PHASE 3 — WORKFORCE INTELLIGENCE AND OPTIMIZATION
10. 🔗 Convert forecast demand into staffing requirements
Notebook:

notebooks/03_workforce_intelligence.ipynb

The workforce workflow consumes revenue forecasting outputs and translates expected demand into staffing requirements.
Analytical dependency
Revenue Forecast
       |
       v
Expected Order Demand
       |
       v
Required Staffing
       |
       v
Employee Allocation
       |
       v
Recommended Workforce Roster
       |
       v
Staffing Coverage and Gaps
Workforce planning is connected to revenue forecasting rather than operating as an independent forecasting workflow.

Staffing rules are based on project-specific assumptions and synthetic demand distributions.
11. 🧮 Calculate workforce and labour indicators
The workforce analysis includes:
- Expected orders
- Required employees
- Scheduled employees
- Labour hours
- Labour costs
- Labour cost as a percentage of forecast revenue
- Staffing coverage
- Staffing gaps
- Employee capacity utilisation
- Recommended shift allocations
📂 Main workforce outputs
outputs/workforce_forecast_next_14_days.csv

outputs/recommended_roster.csv

outputs/staffing_coverage.csv

outputs/staffing_gaps.csv
Output	Purpose
workforce_forecast_next_14_days.csv	Daily demand, workforce requirements and projected labour metrics
recommended_roster.csv	Individual employee shift recommendations
staffing_coverage.csv	Required versus assigned staffing by role and shift
staffing_gaps.csv	Unfilled staffing positions and associated reasons


12. 🗓️ Implement workforce planning and roster recommendations
The workforce planning implementation considers:
- Employee status
- Employee role
- Availability
- Existing shifts
- Working-hour constraints
- Labour costs
The application provides a weekly roster view based on the rolling 14-day forecast period, together with staffing coverage and gap information.

The recommended roster is an operational decision-support output based on the project's scheduling rules and synthetic workforce data.

It should not be interpreted as a legally validated real-world employee schedule.
🧑‍🤝‍🧑 PHASE 4 — CUSTOMER INTELLIGENCE
13. 💬 Analyse customer reviews and purchasing behaviour
Notebook:

notebooks/04_customer_intelligence.ipynb

Customer intelligence combines review analysis with customer purchasing behaviour.

The analysis includes:
- Review rating distribution
- Review trends
- Positive, neutral and negative sentiment
- Aspect-level sentiment summaries
- Customer feedback categories
- Customer RFM segmentation
- Customer value analysis
- Customer improvement areas
- High-value customer feedback risks
14. 🗣️ Perform aspect-level customer experience analysis
Restaurant experience aspects include:
- Food
- Service
- Staff
- Price
- Atmosphere
- Waiting Time
- Drinks
- Cleanliness
Illustrative example:
Review:

"The food was excellent and the waiter was friendly,
but we waited almost 40 minutes."
Illustrative aspect interpretation:
Food          -> Positive
Service       -> Positive
Waiting Time  -> Negative
The supplied review_aspect_labels.csv contains synthetic pre-labelled aspect-level sentiment annotations.

These labels provide structured descriptive inputs for customer experience analysis. They are not predictions generated by a trained NLP model and must not be presented as independent evidence of real-world customer sentiment.
15. 📊 Perform RFM customer segmentation
Customer segmentation uses three dimensions:
Metric	Meaning
Recency	How recently a customer made a purchase
Frequency	How often a customer purchased
Monetary	How much a customer spent


The RFM analysis supports:
- Customer value segmentation
- Purchasing behaviour analysis
- Revenue concentration analysis
- Customer segment profiling
- Identification of high-value customers
RFM results are based on qualifying transaction activity within the project's reference period.
16. 📂 Generate customer intelligence outputs
Important outputs include:
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
Customer intelligence translates synthetic purchasing and review data into structured management information.
🍽️ PHASE 5 — MENU INTELLIGENCE AND ENGINEERING
17. 🔍 Analyse menu performance
Notebook:

notebooks/05_menu_intelligence.ipynb

The menu analysis examines:
- Product sales volume
- Revenue by product
- Revenue by category
- Product costs
- Gross profit
- Gross margin
- Discount performance
- Weekday performance
- Monthly performance
- Promotion trends
18. 🏷️ Apply menu engineering
Menu engineering classifies products into four categories:
Classification	Popularity	Profitability
Star	High	High
Plowhorse	High	Low
Puzzle	Low	High
Dog	Low	Low


The classifications use project-specific popularity and profitability thresholds.

Gross profit is calculated as:

Revenue - Product Costs

It excludes operating expenses such as labour, rent, utilities and other overheads. It must not be interpreted as net profit.
19. 📈 Generate menu intelligence outputs
Important outputs include:
outputs/menu_product_performance.csv

outputs/menu_category_performance.csv

outputs/menu_class_summary.csv

outputs/menu_discount_performance.csv

outputs/menu_engineering.csv

outputs/menu_intelligence_kpis.csv

outputs/menu_monthly_performance.csv

outputs/menu_recommendations.csv

outputs/menu_weekday_performance.csv
The results support product and category performance analysis, profitability comparisons and menu engineering decisions.
🖥️ PHASE 6 — STREAMLIT APPLICATION
20. 🚀 Build the interactive application
Application entry point:

app.py

The Streamlit application brings the analytical outputs together in five main modules:
1. Executive Overview
2. Revenue & Forecast
3. Workforce Planning
4. Customer Intelligence
5. Menu Performance
The application also provides a separate Data & Methodology view documenting the dataset, analytical methods, reconciliation checks, model metadata, customer analytics metadata and project limitations.
🏗️ Application architecture
The Streamlit application consumes:
- Cleaned operational datasets
- Precomputed analytical outputs
- Saved forecasting model artifacts
- Model and customer analytics metadata
The forecasting and workforce output generation logic is maintained separately in forecast_pipeline.py.

The application does not need to retrain Prophet every time Streamlit reruns.
21. 🧪 Validate each application module
Executive Overview
Check:
- Key performance indicators
- Historical business performance
- Metric definitions
- Data coverage
Revenue & Forecast
Check:
- Historical revenue
- Forecast dates
- Forecast values
- Forecast uncertainty intervals
- Forecast visualisations
- Weather-related forecasting information
Workforce Planning
Check:
- Expected orders
- Required employees
- Scheduled employees
- Staffing shortfalls
- Labour cost indicators
- Employee capacity
- Weekly workforce roster
- Staffing gap explanations
Customer Intelligence
Check:
- Review ratings
- Sentiment distributions
- Aspect summaries
- RFM segments
- Customer feedback indicators
- Period filtering where applicable
Menu Performance
Check:
- Product performance
- Category performance
- Gross profit
- Gross margin
- Discount performance
- Menu engineering classifications
Data & Methodology
Check:
- Analytical workflow sequence
- Data quality and reconciliation
- Dataset inventory
- Forecasting model metadata
- Customer analytics metadata
- Automated validation documentation
- Project limitations
General application checks
- No missing required input files.
- No broken page navigation.
- No misleading metric labels.
- No unhandled empty-data cases.
- Clear disclosure of synthetic data.
- Consistent formatting of monetary values and percentages.
- Forecast and workforce date ranges are aligned.
🧪 PHASE 7 — TESTING AND QUALITY ASSURANCE
22. ✅ Maintain the consolidated Pytest validation suite
Main test file:
tests/test_project_validation.py
Run locally:
python -m pytest tests/test_project_validation.py -v -s
The consolidated validation suite contains 72 analytical validation checks, according to the latest documented local test result.
Validation coverage
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
Latest documented local result
Passed: 72
Failed: 0
Total:  72

RESULT: ALL ANALYTICAL CHECKS PASSED
Passing tests confirms that the current outputs satisfy the implemented validation rules. It does not prove that every forecasting assumption or business rule is statistically or operationally optimal.
23. ⚙️ Configure GitHub Actions
Workflow:
.github/workflows/ci.yml
The GitHub Actions workflow performs automated project checks, including:
1. Repository checkout
2. Python environment setup
3. Dependency installation
4. Python syntax checks
5. SQL schema file validation
6. Forecasting model artifact checks
7. Source CSV readability checks
8. Consolidated Pytest validation
The CI environment uses Python 3.11.

After pushing changes, verify the workflow result in the GitHub repository under the Actions tab.
📚 PHASE 8 — DOCUMENTATION AND REPRODUCIBILITY
24. 📝 Maintain project documentation
Important documentation files:
README.md

PROJECT_STEPS.md

EER_Diagram.png

data/schema.sql
The README documents:
- Business problem
- Synthetic dataset
- Application modules
- Technical architecture
- Technology stack
- Repository structure
- Installation and setup
- Application launch
- Optional MySQL database setup
- Automated testing
- Analytical definitions and limitations
- Future improvements
Documentation must describe implemented functionality accurately and distinguish future ideas from completed features.
25. 🔁 Maintain project reproducibility
A new user should be able to:
1. Clone the repository.
2. Create a Python environment.
3. Install dependencies.
4. Run the Streamlit application.
5. Explore the analytical modules.
6. Run the Pytest validation suite.
7. Understand the synthetic data and analytical limitations.
8. Optionally configure MySQL and load the source datasets.
🚢 PHASE 9 — FINAL RELEASE AND DEPLOYMENT
The analytical development and main application workflows are documented in the preceding phases. The remaining release work should focus on making the completed project accessible, reproducible and presentable as a portfolio project.
26. 📦 Prepare the GitHub repository
Before release:
- Confirm that all required source files are committed.
- Confirm that the notebooks, cleaned datasets, model artifacts, metadata and analytical outputs required by the application are included.
- Confirm that requirements.txt contains the necessary dependencies.
- Confirm that no unnecessary temporary files or local environment files are committed.
- Confirm that the README and PROJECT_STEPS.md accurately describe the implementation.
- Verify that the GitHub Actions workflow runs successfully.
27. ☁️ Deploy the Streamlit application
Deployment target:

Streamlit Community Cloud

Deployment configuration:
- GitHub repository: satish-shrestha-4u/restrodine-project
- Branch: main
- Application entry point: app.py
After deployment:
- Confirm that the application starts successfully.
- Verify that all five dashboard modules load.
- Check that charts, tables and KPIs display correctly.
- Verify that forecast and workforce outputs load.
- Check that the Data & Methodology page is accessible.
- Confirm that the application does not depend on local absolute file paths.
- Add the public application URL to the GitHub README.
28. 🖼️ Complete the portfolio presentation
Prepare the repository for professional presentation:
- Add clear dashboard screenshots to the README.
- Include the public Streamlit application link.
- Keep the project description consistent across GitHub and the application.
- Ensure that the synthetic-data disclosure is visible.
- Explain the forecasting, workforce and business intelligence workflows clearly.
- Keep the repository structure understandable to reviewers and recruiters.
29. 🔍 Perform the final release verification
The final release should satisfy the following criteria:
- [ ] GitHub repository is accessible.
- [ ] README is complete and accurate.
- [ ] PROJECT_STEPS.md reflects the actual implementation.
- [ ] Required project files are committed.
- [ ] GitHub Actions checks pass.
- [ ] Pytest validation suite passes.
- [ ] Streamlit application is deployed.
- [ ] All dashboard modules work in the deployed application.
- [ ] Public application link is included in the README.
- [ ] Synthetic data and methodological limitations are disclosed.
🏆 PROJECT COMPLETION PRINCIPLES
RestroDine should be evaluated on more than the number of models or features.

A strong final project should demonstrate:
- Reproducible data processing
- Correct financial calculations
- Appropriate forecasting evaluation
- Integration of weather information into forecasting
- Transparent workforce planning assumptions
- Meaningful customer and menu insights
- Reliable application behaviour
- Automated testing
- Clear technical documentation
- Honest disclosure of synthetic data and project limitations
The central objective is to demonstrate how restaurant data can be transformed into understandable, testable and actionable management intelligence.

Project: RestroDine — Restaurant Intelligence & Weather-Aware Revenue Forecasting

Author: [Satish](https://github.com/satish-shrestha-4u)

Context: Data Science and AI portfolio project developed during training at WBS Coding School as a final project. 