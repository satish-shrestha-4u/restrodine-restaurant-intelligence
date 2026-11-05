# RestroDine — Restaurant Intelligence & Weather-Aware Revenue Forecasting

An end-to-end Data Science and Business Intelligence project that transforms synthetic restaurant point-of-sale, workforce, customer review and weather data into actionable management insights.

RestroDine combines revenue intelligence, demand forecasting, workforce planning, customer sentiment analysis and menu engineering in an interactive Streamlit application.

> **Important — Synthetic Dataset:** All customers, transactions, products, employees, shifts, reviews and weather observations in this project are synthetic. They were generated for educational and portfolio purposes. The results demonstrate analytical methods and application functionality; they are not findings from a real restaurant.

---

## 1. Business Problem

Restaurant managers need to make decisions across several interconnected areas:

- How much revenue might the restaurant generate over the next two weeks?
- How many employees may be required to meet expected demand?
- Are scheduled employees sufficient for forecast demand?
- What do customer reviews reveal about food, service and other restaurant aspects?
- Which products generate the most revenue and gross profit?
- Which menu items may require pricing, promotion or menu-placement decisions?

These questions are often investigated separately. RestroDine brings them together in one analytical application.

The project demonstrates how data engineering, statistical analysis, forecasting and business intelligence can support restaurant management decisions.

## 2. Project Dataset

The project uses a synthetic restaurant dataset covering two complete calendar years.

| Dataset characteristic | Coverage |
|---|---:|
| Historical period | 1 January 2024 – 31 December 2025 |
| Calendar days | 731 |
| Orders | 56,088 |
| Order items | 220,112 |
| Customers | 5,000 |
| Products | 30 |
| Employees | 30 |
| Shifts | 8,696 |
| Customer reviews | 4,306 |

The dataset includes:

- Point-of-sale transactions and order items
- Customers and customer registration information
- Product catalogue, categories and product costs
- Promotions and discounts
- Employee records and availability
- Employee shifts and labour costs
- Calendar and holiday information
- Historical weather observations
- Customer reviews and aspect-level sentiment labels
- Daily revenue data

The synthetic weather observations are calibrated to western German climate patterns. They should not be interpreted as actual historical weather measurements.

## 3. Application Modules

RestroDine currently provides five analytical modules.

### 3.1 Executive Overview

A management-level overview of restaurant performance, bringing important operational and financial indicators together.

### 3.2 Revenue Intelligence

Analyses historical revenue and order performance and presents the saved 14-day revenue forecast.

Key capabilities:
- Revenue trends and performance indicators
- Forecast revenue for the next 14 days
- Forecast uncertainty intervals where available
- Calendar and weather-aware forecasting outputs

The forecasting model is based on Prophet. The saved model and its metadata are stored in the repository.

### 3.3 Workforce Intelligence

Connects expected demand with workforce requirements.

Key capabilities:
- Forecast expected orders
- Estimate required staffing
- Compare required and scheduled employees
- Identify staffing shortfalls
- Review labour hours and labour costs
- Monitor labour cost as a percentage of forecast revenue

The staffing and labour calculations are intended as operational planning tools, not a substitute for a validated workforce scheduling policy.

### 3.4 Customer Intelligence

Turns customer feedback into structured information for management.

Key capabilities:
- Customer review and rating analysis
- Aspect-level sentiment summaries
- Positive, neutral and negative feedback distributions
- Customer segmentation using RFM analysis
- Identification of customer feedback and improvement areas

The supplied `review_aspect_labels` dataset is ground truth for evaluating aspect-level NLP results. It must not be presented as independent real-world sentiment evidence.

### 3.5 Menu Performance

Evaluates menu products and their financial and operational contribution.

Key capabilities:
- Product sales volume
- Product revenue
- Product cost and gross profit
- Gross margin
- Revenue and profit contribution
- Menu engineering classifications

Menu engineering uses four categories:

- **Star:** High popularity and high profitability
- **Plowhorse:** High popularity and lower profitability
- **Puzzle:** Lower popularity and high profitability
- **Dog:** Lower popularity and lower profitability

These classifications are based on project-specific thresholds. They are analytical guidelines rather than universal restaurant industry standards.

## 4. Technical Architecture

The project follows a structured analytical workflow:

```text
Synthetic Restaurant Data
          |
          v
    Original CSV Files
          |
          v
    Data Cleaning
          |
          v
    Cleaned Datasets
          |
          v
 Feature Engineering
          |
          v
  Analytical Workflows
          |
    +-----+------------------+
    |          |             |
    v          v             v
 Revenue   Workforce      Customer
Forecast   Intelligence  Intelligence
    |          |             |
    +----------+-------------+
               |
               v
        Menu Intelligence
               |
               v
      Precomputed Outputs
               |
               v
       Streamlit Application
               |
               v
       Management Insights
```

The project also includes a MySQL database schema and a database-loading script for the relational data workflow.

The Streamlit application reads precomputed analytical outputs. It does not retrain the Prophet model every time a user changes pages or interacts with the dashboard.

## 5. Technology Stack

| Area | Technologies |
|---|---|
| Programming | Python |
| Data manipulation | Pandas, NumPy |
| Database | MySQL, SQL |
| Forecasting | Prophet |
| Statistical analysis | Statistical methods and time-series evaluation |
| Machine learning | Scikit-learn |
| Visualization | Matplotlib, Seaborn, Plotly |
| Application | Streamlit |
| Testing | Pytest |
| Version control | Git, GitHub |
| Development | Jupyter Notebook, VS Code |

The project uses Python for data processing and analysis, SQL for relational data management, and Streamlit for presenting the results through an interactive interface.

## 6. Repository Structure

```text
RestroDine/
│
├── app.py
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
│   └── restrodine_prophet_calendar_weather_metadata.json
│
├── tests/
│   └── test_project_validation.py
│
├── load_database.py
├── requirements.txt
├── PROJECT_STEPS.md
├── EER_Diagram.png
└── README.md
```

### Directory descriptions

- `data/`: Original synthetic CSV files and SQL schema.
- `data_clean/`: Cleaned and processed datasets.
- `notebooks/`: Analytical development and experimentation.
- `outputs/`: Precomputed analytical results used by the application.
- `models/`: Saved forecasting model.
- `metadata/`: Model and analytical metadata.
- `tests/`: Automated analytical and data-integrity tests.
- `app.py`: Streamlit application entry point.
- `load_database.py`: MySQL database creation and CSV-loading utility.

## 7. Installation and Setup

### Prerequisites

- Python 3.11 (recommended)
- Git
- Conda or Python virtual environment
- A compatible operating system
- MySQL Server and MySQL Workbench (optional, for the database workflow)

### Clone the repository

```bash
git clone https://github.com/satish-shrestha-4u/restrodine-project.git

cd restrodine-project
```

### Create and activate the environment

Using Conda:

```bash
conda create -n restrodine-env python=3.11 -y

conda activate restrodine-env
```

Alternatively, using Python's built-in virtual environment:

```bash
python -m venv .venv

source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### Install dependencies

```bash
python -m pip install --upgrade pip

pip install -r requirements.txt
```

## 8. Run the Streamlit Application

From the project root:

```bash
streamlit run app.py
```

Streamlit will start a local server and provide a browser address, normally:

```text
http://localhost:8501
```

The application uses the analytical CSV outputs, saved model artifacts and metadata included in the repository.

No database connection is required to use the precomputed-output application workflow unless a particular feature explicitly requires it.

Run analytical validation tests:

```bash
python -m pytest tests/test_project_validation.py -v -s
```

## 9. Optional MySQL Database Setup

The repository includes:

- `data/schema.sql`
- `load_database.py`
- Original CSV datasets

The database loader creates and populates the project database and performs integrity checks.

Start your local MySQL Server, then execute:

```bash
python load_database.py
```

The script prompts for the MySQL password.

**Important:** The loader drops and recreates project tables in the specified database. Use it only with a dedicated RestroDine database. Never point it at a database containing unrelated or valuable information.

The loader checks primary-key uniqueness, referential integrity, order and payment reconciliation, calendar and weather coverage, and labour-cost calculations.

## 10. Data Validation and Automated Testing

Data quality is essential when building analytical applications.

RestroDine includes a consolidated Pytest validation suite:

```bash
python -m pytest tests/test_project_validation.py -v -s
```

The current validation suite contains 72 passing checks covering:

| Validation area | Coverage |
|---|---|
| CSV readability | Required project datasets and outputs |
| Revenue | Order totals and order-item reconciliation |
| Product profitability | Product costs and gross-profit calculations |
| Revenue forecasting | Dates, numeric values and forecast intervals |
| Workforce forecasting | Demand, staffing, hours and labour costs |
| Staffing coverage | Required, assigned and shortfall calculations |
| Staffing gaps | Non-negative staffing shortfalls |
| Customer sentiment | Percentage ranges and reconciliation |
| RFM segmentation | Valid project segment labels |
| Menu performance | Product-level revenue and quantity checks |
| Menu engineering | Valid menu classifications |
| Model artifacts | Saved Prophet model and metadata |
| SQL schema | Source CSV column definitions |
| Foreign keys | Source CSV referential integrity |

Latest local result:

```text
Passed: 72
Failed: 0
Total:  72

RESULT: ALL ANALYTICAL CHECKS PASSED
```

GitHub Actions is configured to run the project checks automatically when relevant changes are pushed or submitted through pull requests.

Passing validation tests confirms that the encoded project rules hold for the current data and outputs. It does not independently establish forecasting accuracy or prove that every business assumption is correct.

## 11. Important Analytical Definitions and Limitations

### Synthetic data

All business data is generated for this project. No real restaurant, customer or employee records are represented.

### Gross profit

Gross profit is calculated as:

```text
Revenue - Product Costs
```

It excludes labour, rent, utilities, delivery fees and other operating expenses. It must not be interpreted as net profit.

### Weather data

Historical weather is synthetic and calibrated to western German climate patterns. Replacing it with real weather observations requires rebuilding the relevant analytical datasets and model inputs consistently.

### Customer aspect labels

`review_aspect_labels` is ground truth for NLP evaluation, not an independent source of real-world customer sentiment.

### Forecasts

Forecast outputs are estimates based on the project's synthetic historical data and model assumptions. They should not be interpreted as guaranteed future revenue or staffing requirements.

### Menu engineering

Star, Plowhorse, Puzzle and Dog classifications depend on project-specific popularity and profitability thresholds. Different restaurants may require different thresholds.

### Staffing recommendations

Staffing requirements are based on the project's forecasting and staffing assumptions. They are decision-support estimates rather than legally or operationally validated scheduling instructions.

## 12. Future Improvements

Potential extensions include:

- Backtesting and comparison of forecasting models
- More extensive forecast error analysis
- Real weather API integration for future forecasts
- Improved demand-to-staffing optimization
- Employee availability and working-hour constraint enhancements
- More advanced NLP evaluation
- Inventory and waste analytics
- Promotion effectiveness analysis
- Scenario simulation and management alerts

These are potential extensions, not claims about features already implemented.

## 13. Project Documentation

- `PROJECT_STEPS.md`: Development sequence, implementation status and future work.
- `EER_Diagram.png`: Entity Relationship Diagram of the database.
- `data/schema.sql`: Relational database definitions.

## 14. Author and Project Context

RestroDine was developed as a Data Science and AI portfolio project during Data Science and AI training at WBS Coding School.

The project combines a background in Economics and Finance with practical work in Python, SQL, data analytics, forecasting, machine learning and business intelligence.

**The objective:** demonstrate how a data-driven system can connect restaurant financial performance, workforce planning, customer feedback and menu decisions in one application.
