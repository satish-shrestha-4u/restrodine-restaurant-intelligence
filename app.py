# ============================================================
# RESTRODINE — RESTAURANT INTELLIGENCE PLATFORM
# ============================================================
# All project data is synthetic and created for demonstration.
# This application does not represent a real restaurant.
#
# Run from the project root:
# streamlit run app.py
# ============================================================

from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="RestroDine | Restaurant Intelligence",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data_clean"
OUTPUT_DIR = BASE_DIR / "outputs"

# Optional directories retained for future extensions
MODEL_DIR = BASE_DIR / "models"
METADATA_DIR = BASE_DIR / "metadata"


# ============================================================
# 3. DESIGN SYSTEM
# ============================================================

NAVY = "#17253A"
NAVY_LIGHT = "#243750"
BACKGROUND = "#F5F7FB"
WHITE = "#FFFFFF"
TEXT = "#202B3C"
MUTED = "#7B8798"
GREEN = "#239B68"
BLUE = "#3974D5"
PURPLE = "#8957C8"
ORANGE = "#D99038"
RED = "#D9534F"
BORDER = "#E8ECF2"

CHART_COLORS = [
    "#3974D5",
    "#239B68",
    "#8957C8",
    "#D99038",
    "#D9534F",
    "#49A6A6",
]

st.markdown(
    f"""
    <style>
    @import url(
        'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap'
    );

    html, body, [class*="css"] {{
        font-family: 'DM Sans', sans-serif;
    }}

    .stApp {{
        background-color: {BACKGROUND};
    }}

    [data-testid="stSidebar"] {{
        background: {NAVY};
    }}

    [data-testid="stSidebar"] * {{
        color: #FFFFFF;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label {{
        color: #D9E2EF !important;
        font-weight: 500;
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: #D9E2EF;
    }}

    .brand-title {{
        font-size: 27px;
        font-weight: 800;
        letter-spacing: 1px;
        color: #FFFFFF;
        margin-bottom: 0;
    }}

    .brand-subtitle {{
        color: #AFC0D5;
        font-size: 10px;
        letter-spacing: 2px;
        margin-top: -3px;
    }}

    .page-title {{
        font-size: 30px;
        font-weight: 800;
        color: {TEXT};
        margin-bottom: 2px;
    }}

    .page-subtitle {{
        font-size: 14px;
        color: {MUTED};
        margin-bottom: 22px;
    }}

    .section-title {{
        font-size: 18px;
        font-weight: 700;
        color: {TEXT};
        margin-top: 18px;
        margin-bottom: 10px;
    }}

    .kpi-card {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 17px 18px;
        min-height: 115px;
        box-shadow: 0 2px 8px rgba(25, 42, 70, 0.035);
    }}

    .kpi-label {{
        font-size: 12px;
        font-weight: 600;
        color: {MUTED};
        margin-bottom: 9px;
    }}

    .kpi-value {{
        font-size: 25px;
        font-weight: 800;
        color: {TEXT};
        line-height: 1.2;
    }}

    .kpi-note {{
        font-size: 11px;
        color: {MUTED};
        margin-top: 7px;
    }}

    .panel {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 12px;
    }}

    .synthetic-banner {{
        background: #FFF6E8;
        border: 1px solid #F2D8A8;
        color: #805B24;
        padding: 10px 14px;
        border-radius: 9px;
        font-size: 12px;
        margin-bottom: 18px;
    }}

    .insight-box {{
        background: #EEF4FF;
        border-left: 4px solid {BLUE};
        border-radius: 7px;
        padding: 13px 15px;
        margin: 10px 0 16px 0;
        color: #344E75;
        font-size: 13px;
    }}

    .stButton button {{
        border-radius: 8px;
    }}

    div[data-testid="stDataFrame"] {{
        border: 1px solid {BORDER};
        border-radius: 10px;
        overflow: hidden;
    }}

    footer {{
        visibility: hidden;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 4. DATA LOADING
# ============================================================

@st.cache_data(show_spinner=False)
def load_csv(file_path):
    """Load a CSV safely and cache the result."""
    path = Path(file_path)

    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def get_data(filename):
    return load_csv(str(DATA_DIR / filename))


def get_output(filename):
    return load_csv(str(OUTPUT_DIR / filename))


def parse_date_column(df, column):
    if not df.empty and column in df.columns:
        df = df.copy()
        df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


def first_existing_column(df, candidates):
    """Return the first available column from a list."""
    for column in candidates:
        if column in df.columns:
            return column
    return None


def numeric_series(df, column, default=0):
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)

    return pd.to_numeric(df[column], errors="coerce").fillna(default)


def money(value):
    if pd.isna(value):
        value = 0
    return f"€{value:,.2f}"


def integer(value):
    if pd.isna(value):
        value = 0
    return f"{value:,.0f}"


def percentage(value):
    if pd.isna(value):
        value = 0
    return f"{value:.1f}%"


def safe_divide(numerator, denominator):
    if denominator == 0 or pd.isna(denominator):
        return 0
    return numerator / denominator


# ============================================================
# 5. LOAD PROJECT DATA
# ============================================================

orders = get_data("orders_clean.csv")
order_items = get_data("order_items_clean.csv")
products = get_data("products_clean.csv")
customers = get_data("customers_clean.csv")
employees = get_data("employees_clean.csv")
availability = get_data("employee_availability_clean.csv")
shifts = get_data("shifts_clean.csv")
reviews = get_data("reviews_clean.csv")
weather = get_data("weather_clean.csv")
calendar = get_data("calendar_clean.csv")
daily_revenue = get_data("daily_revenue_clean.csv")
daily_model = get_data("daily_model_table_clean.csv")

forecast = get_output("revenue_forecast_next_14_days.csv")

workforce_forecast = get_output(
    "workforce_forecast_next_14_days.csv"
)
recommended_roster = get_output("recommended_roster.csv")
staffing_coverage = get_output("staffing_coverage.csv")
staffing_gaps = get_output("staffing_gaps.csv")

customer_kpis = get_output("customer_intelligence_kpis.csv")
aspect_summary = get_output("customer_aspect_sentiment_summary.csv")
improvement_areas = get_output("customer_improvement_areas.csv")
monthly_sentiment = get_output("customer_monthly_sentiment.csv")
feedback_by_type = get_output("customer_feedback_by_type.csv")
ratings_by_type = get_output("customer_ratings_by_type.csv")
rfm_segments = get_output("customer_rfm_segments.csv")
segment_profile = get_output("customer_segment_profile.csv")
feedback_by_segment = get_output("customer_feedback_by_segment.csv")
high_value_negative = get_output("high_value_negative_feedback.csv")
review_aspect_detail = get_output("customer_review_aspect_detail.csv")

menu_kpis = get_output("menu_intelligence_kpis.csv")
menu_products = get_output("menu_product_performance.csv")
menu_categories = get_output("menu_category_performance.csv")
menu_monthly = get_output("menu_monthly_performance.csv")
menu_weekday = get_output("menu_weekday_performance.csv")
menu_discounts = get_output("menu_discount_performance.csv")
menu_engineering = get_output("menu_engineering.csv")
menu_recommendations = get_output("menu_recommendations.csv")
menu_class_summary = get_output("menu_class_summary.csv")


# ============================================================
# 6. STANDARDISE DATES
# ============================================================

orders = parse_date_column(orders, "order_datetime")
orders = parse_date_column(orders, "order_date")
reviews = parse_date_column(reviews, "review_date")
daily_revenue = parse_date_column(daily_revenue, "date")
daily_model = parse_date_column(daily_model, "date")
forecast = parse_date_column(forecast, "date")
workforce_forecast = parse_date_column(workforce_forecast, "date")
recommended_roster = parse_date_column(recommended_roster, "date")
staffing_coverage = parse_date_column(staffing_coverage, "date")
staffing_gaps = parse_date_column(staffing_gaps, "date")
monthly_sentiment = parse_date_column(monthly_sentiment, "review_month")
menu_monthly = parse_date_column(menu_monthly, "month")


# ============================================================
# 7. COMMON UI FUNCTIONS
# ============================================================

def page_header(title, subtitle):
    st.markdown(
        f'<div class="page-title">{title}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="page-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def show_kpi(label, value, note=""):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title):
    st.markdown(
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True,
    )


def show_chart(fig, height=350):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=35, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="DM Sans",
            color=TEXT,
            size=11,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        linecolor=BORDER,
    )

    fig.update_yaxes(
        gridcolor="#EDF0F5",
        zeroline=False,
    )

    st.plotly_chart(fig, use_container_width=True)


def show_empty(message):
    st.info(message)


def show_table(df, height=350):
    if df.empty:
        show_empty("No data available for this section.")
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=height,
        )


def add_synthetic_disclosure():
    st.markdown(
        """
        <div class="synthetic-banner">
        <b>DEMONSTRATION DATA:</b>
        All customers, orders, employees, reviews, sales,
        forecasts and business results in RestroDine are synthetic.
        They are not real restaurant records or actual business findings.
        </div>
        """,
        unsafe_allow_html=True,
    )


def filter_by_date(df, date_column, date_range):
    if df.empty or date_column not in df.columns:
        return df

    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        return df

    start_date, end_date = date_range

    if start_date is None or end_date is None:
        return df

    dates = pd.to_datetime(df[date_column], errors="coerce")

    return df.loc[
        dates.dt.date.between(start_date, end_date)
    ].copy()


def make_line_chart(df, x, y, title, y_title=None):
    fig = px.line(
        df,
        x=x,
        y=y,
        title=title,
        markers=True,
        color_discrete_sequence=[BLUE],
    )

    fig.update_traces(line=dict(width=3))

    if y_title:
        fig.update_yaxes(title=y_title)

    return fig


# ============================================================
# 8. MENU PERFORMANCE FALLBACK CALCULATIONS
# ============================================================

def build_menu_performance():
    """
    Calculate product performance from cleaned source tables
    when the Notebook 05 exports are not available.
    """

    required_items = {
        "product_id",
        "order_id",
        "quantity",
        "line_total",
    }

    required_products = {
        "product_id",
        "product_name",
        "category",
        "selling_price",
        "product_cost",
    }

    if (
        order_items.empty
        or products.empty
        or not required_items.issubset(order_items.columns)
        or not required_products.issubset(products.columns)
    ):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    items = order_items.copy()
    catalogue = products.copy()

    items["quantity"] = numeric_series(items, "quantity")
    items["line_total"] = numeric_series(items, "line_total")

    catalogue["selling_price"] = numeric_series(
        catalogue, "selling_price"
    )
    catalogue["product_cost"] = numeric_series(
        catalogue, "product_cost"
    )

    merged = items.merge(
        catalogue[
            [
                "product_id",
                "product_name",
                "category",
                "selling_price",
                "product_cost",
            ]
        ],
        on="product_id",
        how="left",
    )

    merged["total_cost"] = (
        merged["quantity"] * merged["product_cost"]
    )

    merged["gross_profit"] = (
        merged["line_total"] - merged["total_cost"]
    )

    product_summary = (
        merged.groupby(
            ["product_id", "product_name", "category"],
            as_index=False,
        )
        .agg(
            quantity_sold=("quantity", "sum"),
            revenue=("line_total", "sum"),
            product_cost=("total_cost", "sum"),
            gross_profit=("gross_profit", "sum"),
        )
    )

    product_summary["gross_margin_pct"] = (
        product_summary["gross_profit"]
        / product_summary["revenue"].replace(0, np.nan)
        * 100
    ).fillna(0)

    product_summary["contribution_margin_per_unit"] = (
        product_summary["gross_profit"]
        / product_summary["quantity_sold"].replace(0, np.nan)
    ).fillna(0)

    category_summary = (
        product_summary.groupby("category", as_index=False)
        .agg(
            quantity_sold=("quantity_sold", "sum"),
            revenue=("revenue", "sum"),
            gross_profit=("gross_profit", "sum"),
        )
    )

    category_summary["gross_margin_pct"] = (
        category_summary["gross_profit"]
        / category_summary["revenue"].replace(0, np.nan)
        * 100
    ).fillna(0)

    return product_summary, category_summary, merged


if menu_products.empty:
    calculated_products, calculated_categories, menu_detail = (
        build_menu_performance()
    )
else:
    calculated_products = menu_products.copy()
    calculated_categories = menu_categories.copy()
    menu_detail = pd.DataFrame()


# ============================================================
# 9. GLOBAL FILTERS
# ============================================================

date_column = first_existing_column(
    orders,
    ["order_date", "order_datetime"],
)

if date_column and not orders.empty:
    date_values = pd.to_datetime(
        orders[date_column], errors="coerce"
    ).dropna()

    if not date_values.empty:
        min_date = date_values.min().date()
        max_date = date_values.max().date()
    else:
        min_date = None
        max_date = None
else:
    min_date = None
    max_date = None


# ============================================================
# 10. SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div class="brand-title">🍽️ RESTRODINE</div>
        <div class="brand-subtitle">
            RESTAURANT INTELLIGENCE PLATFORM
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    navigation = st.radio(
        "NAVIGATION",
        [
            "Executive Overview",
            "Revenue Intelligence",
            "Workforce Intelligence",
            "Customer Intelligence",
            "Menu Performance",
        ],
        label_visibility="visible",
    )

    st.markdown("---")

    st.markdown("**DATA PERIOD**")

    if min_date and max_date:
        selected_dates = st.date_input(
            "Select historical date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="global_date_range",
        )
    else:
        selected_dates = None
        st.caption("Historical date range unavailable.")

    st.markdown("---")

    st.caption("RESTRODINE · DATA SCIENCE & AI PROJECT")
    st.caption("All data is synthetic.")


# Apply global order date filter

if selected_dates and date_column:
    filtered_orders = filter_by_date(
        orders, date_column, selected_dates
    )
else:
    filtered_orders = orders.copy()


# ============================================================
# 11. EXECUTIVE OVERVIEW
# ============================================================

def executive_overview():

    page_header(
        "Executive Overview",
        "A consolidated view of restaurant performance and operations.",
    )

    add_synthetic_disclosure()

    if filtered_orders.empty:
        show_empty("No order records are available for this date range.")
        return

    order_total_col = first_existing_column(
        filtered_orders,
        ["order_total", "total_amount", "revenue"],
    )

    order_date_col = first_existing_column(
        filtered_orders,
        ["order_date", "order_datetime"],
    )

    if order_total_col:
        revenue_value = numeric_series(
            filtered_orders, order_total_col
        ).sum()
    else:
        revenue_value = 0

    total_orders = len(filtered_orders)

    average_order = safe_divide(
        revenue_value, total_orders
    )

    average_daily_revenue = 0

    if order_date_col:
        temp = filtered_orders.copy()
        temp["_date"] = pd.to_datetime(
            temp[order_date_col], errors="coerce"
        ).dt.date

        daily = temp.groupby("_date")[order_total_col].sum()
        if not daily.empty:
            average_daily_revenue = daily.mean()

    # KPI cards

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        show_kpi(
            "TOTAL REVENUE",
            money(revenue_value),
            "Selected historical period",
        )

    with c2:
        show_kpi(
            "TOTAL ORDERS",
            integer(total_orders),
            "Orders in selected period",
        )

    with c3:
        show_kpi(
            "AVERAGE ORDER VALUE",
            money(average_order),
            "Revenue per order",
        )

    with c4:
        show_kpi(
            "AVG. DAILY REVENUE",
            money(average_daily_revenue),
            "Average revenue per trading day",
        )

    # Revenue trend

    section("Revenue Performance")

    if order_date_col and order_total_col:

        temp = filtered_orders.copy()
        temp["_date"] = pd.to_datetime(
            temp[order_date_col], errors="coerce"
        ).dt.date

        trend = (
            temp.groupby("_date", as_index=False)[order_total_col]
            .sum()
            .rename(
                columns={
                    "_date": "date",
                    order_total_col: "revenue",
                }
            )
        )

        left, right = st.columns([1.65, 1])

        with left:
            fig = make_line_chart(
                trend,
                "date",
                "revenue",
                "Daily Revenue",
                "Revenue (€)",
            )
            show_chart(fig, 360)

        with right:
            temp["_month"] = pd.to_datetime(
                temp["_date"]
            ).dt.to_period("M").astype(str)

            monthly = (
                temp.groupby("_month", as_index=False)[
                    order_total_col
                ]
                .sum()
                .rename(
                    columns={
                        "_month": "month",
                        order_total_col: "revenue",
                    }
                )
            )

            fig = px.bar(
                monthly,
                x="month",
                y="revenue",
                title="Monthly Revenue",
                color_discrete_sequence=[GREEN],
            )
            fig.update_layout(xaxis_title="", yaxis_title="Revenue (€)")
            show_chart(fig, 360)

    # Operational snapshot

    section("Operational Snapshot")

    col1, col2 = st.columns(2)

    with col1:

        if "order_type" in filtered_orders.columns:
            order_mix = (
                filtered_orders["order_type"]
                .fillna("Unknown")
                .value_counts()
                .rename_axis("order_type")
                .reset_index(name="orders")
            )

            fig = px.pie(
                order_mix,
                names="order_type",
                values="orders",
                hole=0.62,
                title="Orders by Type",
                color_discrete_sequence=CHART_COLORS,
            )
            show_chart(fig, 330)
        else:
            show_empty("Order type information is unavailable.")

    with col2:

        if "meal_period" in filtered_orders.columns:
            meal_mix = (
                filtered_orders["meal_period"]
                .fillna("Unknown")
                .value_counts()
                .rename_axis("meal_period")
                .reset_index(name="orders")
            )

            fig = px.bar(
                meal_mix,
                x="meal_period",
                y="orders",
                title="Orders by Meal Period",
                color="meal_period",
                color_discrete_sequence=CHART_COLORS,
            )
            fig.update_layout(showlegend=False)
            show_chart(fig, 330)
        else:
            show_empty("Meal period information is unavailable.")

    # Review and workforce snapshot

    section("Customer and Workforce Snapshot")

    col1, col2, col3 = st.columns(3)

    with col1:
        review_count = len(reviews)
        average_rating = 0

        if not reviews.empty and "rating" in reviews.columns:
            average_rating = numeric_series(
                reviews, "rating"
            ).mean()

        show_kpi(
            "CUSTOMER REVIEWS",
            integer(review_count),
            f"Average rating: {average_rating:.2f}/5",
        )

    with col2:
        labour_cost = 0

        if not workforce_forecast.empty:
            labour_cost = numeric_series(
                workforce_forecast, "labour_cost"
            ).sum()

        show_kpi(
            "FORECAST LABOUR COST",
            money(labour_cost),
            "Saved workforce forecast period",
        )

    with col3:
        forecast_revenue = 0

        if not forecast.empty and "forecast_revenue" in forecast.columns:
            forecast_revenue = numeric_series(
                forecast, "forecast_revenue"
            ).sum()

        show_kpi(
            "NEXT 14-DAY FORECAST",
            money(forecast_revenue),
            "Precomputed revenue forecast",
        )

    # Top menu items

    section("Top Performing Menu Items")

    if not calculated_products.empty:

        product_col = first_existing_column(
            calculated_products,
            ["product_name", "product"],
        )
        revenue_col = first_existing_column(
            calculated_products,
            ["revenue", "total_revenue", "line_total"],
        )

        if product_col and revenue_col:
            top_items = calculated_products.nlargest(
                8, revenue_col
            )

            fig = px.bar(
                top_items.sort_values(revenue_col),
                x=revenue_col,
                y=product_col,
                orientation="h",
                title="Top 8 Products by Revenue",
                color_discrete_sequence=[BLUE],
            )
            fig.update_layout(
                xaxis_title="Revenue (€)",
                yaxis_title="",
            )
            show_chart(fig, 350)
        else:
            show_empty("Product revenue columns are unavailable.")
    else:
        show_empty("Menu performance data is not available.")


# ============================================================
# 12. REVENUE INTELLIGENCE
# ============================================================

def revenue_intelligence():

    page_header(
        "Revenue Intelligence",
        "Understand sales patterns, revenue drivers and expected demand.",
    )

    add_synthetic_disclosure()

    if filtered_orders.empty:
        show_empty("No historical orders are available.")
        return

    order_date_col = first_existing_column(
        filtered_orders,
        ["order_date", "order_datetime"],
    )

    revenue_col = first_existing_column(
        filtered_orders,
        ["order_total", "total_amount", "revenue"],
    )

    if not order_date_col or not revenue_col:
        show_empty("Required order date or revenue columns are missing.")
        return

    temp = filtered_orders.copy()

    temp["_date"] = pd.to_datetime(
        temp[order_date_col], errors="coerce"
    )

    temp["_revenue"] = numeric_series(temp, revenue_col)

    total_revenue = temp["_revenue"].sum()
    total_orders = len(temp)
    aov = safe_divide(total_revenue, total_orders)

    daily = (
        temp.groupby(temp["_date"].dt.date)
        .agg(
            revenue=("_revenue", "sum"),
            orders=("_revenue", "count"),
        )
        .reset_index()
        .rename(columns={"_date": "date"})
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        show_kpi("REVENUE", money(total_revenue), "Selected period")

    with c2:
        show_kpi("ORDERS", integer(total_orders), "Selected period")

    with c3:
        show_kpi("AVERAGE ORDER VALUE", money(aov), "Revenue per order")

    # Daily trend

    section("Historical Revenue Trend")

    fig = make_line_chart(
        daily,
        "date",
        "revenue",
        "Daily Revenue",
        "Revenue (€)",
    )
    show_chart(fig, 380)

    # Monthly and weekday analysis

    col1, col2 = st.columns(2)

    with col1:
        temp["_month"] = temp["_date"].dt.to_period("M").astype(str)

        monthly = (
            temp.groupby("_month", as_index=False)["_revenue"]
            .sum()
            .rename(
                columns={
                    "_month": "month",
                    "_revenue": "revenue",
                }
            )
        )

        fig = px.bar(
            monthly,
            x="month",
            y="revenue",
            title="Monthly Revenue",
            color_discrete_sequence=[BLUE],
        )
        show_chart(fig, 340)

    with col2:
        temp["_weekday"] = temp["_date"].dt.day_name()

        weekday_order = [
            "Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday", "Sunday",
        ]

        weekday = (
            temp.groupby("_weekday")["_revenue"]
            .sum()
            .reindex(weekday_order)
            .reset_index()
            .rename(
                columns={
                    "_weekday": "weekday",
                    "_revenue": "revenue",
                }
            )
        )

        fig = px.bar(
            weekday,
            x="weekday",
            y="revenue",
            title="Revenue by Weekday",
            color_discrete_sequence=[GREEN],
        )
        show_chart(fig, 340)

    # Order type and meal period

    col1, col2 = st.columns(2)

    with col1:
        if "order_type" in temp.columns:
            order_type = (
                temp.groupby("order_type")["_revenue"]
                .sum()
                .reset_index()
            )

            fig = px.pie(
                order_type,
                names="order_type",
                values="_revenue",
                hole=0.55,
                title="Revenue by Order Type",
                color_discrete_sequence=CHART_COLORS,
            )
            show_chart(fig, 330)
        else:
            show_empty("Order type data unavailable.")

    with col2:
        if "meal_period" in temp.columns:
            meal = (
                temp.groupby("meal_period")["_revenue"]
                .sum()
                .reset_index()
            )

            fig = px.bar(
                meal,
                x="meal_period",
                y="_revenue",
                title="Revenue by Meal Period",
                color_discrete_sequence=[PURPLE],
            )
            show_chart(fig, 330)
        else:
            show_empty("Meal period data unavailable.")

    # Weather analysis

    section("Weather and Promotion Analysis")

    if not daily_model.empty:

        weather_columns = [
            "date",
            "temperature_avg_c",
            "precipitation_mm",
            "is_rainy",
            "revenue",
        ]

        available = [
            c for c in weather_columns
            if c in daily_model.columns
        ]

        if "temperature_avg_c" in available and "revenue" in available:

            weather_data = daily_model.copy()

            fig = px.scatter(
                weather_data,
                x="temperature_avg_c",
                y="revenue",
                color=(
                    "is_rainy"
                    if "is_rainy" in weather_data.columns
                    else None
                ),
                title="Temperature and Revenue",
                trendline="ols",
                color_discrete_sequence=CHART_COLORS,
            )
            fig.update_layout(
                xaxis_title="Average Temperature (°C)",
                yaxis_title="Revenue (€)",
            )
            show_chart(fig, 350)
        else:
            show_empty("Weather and revenue fields are unavailable.")

    if "discount_pct" in order_items.columns:
        discount_data = order_items.copy()
        discount_data["discount_pct"] = numeric_series(
            discount_data, "discount_pct"
        )

        discount_data["line_total"] = numeric_series(
            discount_data, "line_total"
        )

        discount_data["discount_group"] = pd.cut(
            discount_data["discount_pct"],
            bins=[-0.01, 0, 5, 10, 20, 100],
            labels=[
                "No discount",
                "0–5%",
                "5–10%",
                "10–20%",
                "20%+",
            ],
        )

        discount_summary = (
            discount_data.groupby(
                "discount_group",
                observed=False,
            )["line_total"]
            .sum()
            .reset_index()
        )

        fig = px.bar(
            discount_summary,
            x="discount_group",
            y="line_total",
            title="Sales Revenue by Discount Band",
            color_discrete_sequence=[ORANGE],
        )
        show_chart(fig, 330)

    # Forecast

    section("Revenue Forecast")

    if not forecast.empty and "forecast_revenue" in forecast.columns:

        forecast_display = forecast.copy()

        forecast_total = numeric_series(
            forecast_display, "forecast_revenue"
        ).sum()

        lower_col = first_existing_column(
            forecast_display,
            ["lower_bound", "yhat_lower"],
        )
        upper_col = first_existing_column(
            forecast_display,
            ["upper_bound", "yhat_upper"],
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            show_kpi(
                "FORECAST REVENUE",
                money(forecast_total),
                "Saved forecast horizon",
            )

        with c2:
            show_kpi(
                "FORECAST DAYS",
                integer(len(forecast_display)),
                "Forecast records",
            )

        with c3:
            average_forecast = safe_divide(
                forecast_total, len(forecast_display)
            )
            show_kpi(
                "AVERAGE DAILY FORECAST",
                money(average_forecast),
                "Expected daily revenue",
            )

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=forecast_display["date"],
                y=forecast_display["forecast_revenue"],
                mode="lines+markers",
                name="Forecast Revenue",
                line=dict(color=BLUE, width=3),
            )
        )

        if lower_col and upper_col:
            fig.add_trace(
                go.Scatter(
                    x=forecast_display["date"],
                    y=forecast_display[upper_col],
                    mode="lines",
                    line=dict(width=0),
                    showlegend=False,
                    name="Upper bound",
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=forecast_display["date"],
                    y=forecast_display[lower_col],
                    mode="lines",
                    fill="tonexty",
                    fillcolor="rgba(57,116,213,0.13)",
                    line=dict(width=0),
                    name="Forecast interval",
                )
            )

        fig.update_layout(title="Next 14 Days Revenue Forecast")
        show_chart(fig, 380)

        show_table(forecast_display, 300)

        st.caption(
            "Forecasts are precomputed model outputs for demonstration. "
            "They are not actual future revenue."
        )

    else:
        show_empty(
            "Forecast CSV not found. Run Notebook 02 to generate it."
        )


# ============================================================
# 13. WORKFORCE INTELLIGENCE
# ============================================================

def workforce_intelligence():

    page_header(
        "Workforce Intelligence",
        "Plan staffing levels, monitor shift coverage and understand labour costs.",
    )

    add_synthetic_disclosure()

    if workforce_forecast.empty:
        show_empty(
            "Workforce forecast not found. Run Notebook 03 first."
        )
        return

    wf = workforce_forecast.copy()

    required_columns = [
        "expected_orders",
        "required_staff",
        "scheduled_employees",
        "labour_hours",
        "labour_cost",
        "forecast_revenue",
        "labour_cost_pct_revenue",
    ]

    for col in required_columns:
        if col in wf.columns:
            wf[col] = numeric_series(wf, col)

    expected_orders = wf["expected_orders"].sum() if "expected_orders" in wf else 0
    labour_cost = wf["labour_cost"].sum() if "labour_cost" in wf else 0
    labour_hours = wf["labour_hours"].sum() if "labour_hours" in wf else 0
    forecast_revenue = wf["forecast_revenue"].sum() if "forecast_revenue" in wf else 0

    labour_pct = safe_divide(
        labour_cost, forecast_revenue
    ) * 100

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        show_kpi(
            "EXPECTED ORDERS",
            integer(expected_orders),
            "Forecast period",
        )

    with c2:
        show_kpi(
            "LABOUR COST",
            money(labour_cost),
            "Recommended roster",
        )

    with c3:
        show_kpi(
            "LABOUR HOURS",
            integer(labour_hours),
            "Total scheduled hours",
        )

    with c4:
        show_kpi(
            "LABOUR COST / REVENUE",
            percentage(labour_pct),
            "Forecast labour cost ratio",
        )

    # Demand and staffing

    section("Demand and Staffing Requirements")

    if "date" in wf.columns:

        fig = go.Figure()

        if "required_staff" in wf.columns:
            fig.add_trace(
                go.Scatter(
                    x=wf["date"],
                    y=wf["required_staff"],
                    name="Required Staff",
                    mode="lines+markers",
                    line=dict(color=BLUE, width=3),
                )
            )

        if "scheduled_employees" in wf.columns:
            fig.add_trace(
                go.Scatter(
                    x=wf["date"],
                    y=wf["scheduled_employees"],
                    name="Scheduled Employees",
                    mode="lines+markers",
                    line=dict(color=GREEN, width=3),
                )
            )

        fig.update_layout(
            title="Required vs Scheduled Employees",
            yaxis_title="Employees",
        )

        show_chart(fig, 370)

    # Labour cost and forecast revenue

    if "date" in wf.columns and "labour_cost" in wf.columns:

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=wf["date"],
                y=wf["labour_cost"],
                name="Labour Cost",
                marker_color=PURPLE,
            )
        )

        if "forecast_revenue" in wf.columns:
            fig.add_trace(
                go.Scatter(
                    x=wf["date"],
                    y=wf["forecast_revenue"],
                    name="Forecast Revenue",
                    yaxis="y2",
                    line=dict(color=GREEN, width=3),
                )
            )

        fig.update_layout(
            title="Labour Cost vs Forecast Revenue",
            yaxis=dict(title="Labour Cost (€)"),
            yaxis2=dict(
                title="Forecast Revenue (€)",
                overlaying="y",
                side="right",
                showgrid=False,
            ),
        )

        show_chart(fig, 370)

    # Labour cost ratio

    if "date" in wf.columns and "labour_cost_pct_revenue" in wf.columns:

        fig = px.line(
            wf,
            x="date",
            y="labour_cost_pct_revenue",
            title="Daily Labour Cost as % of Forecast Revenue",
            markers=True,
            color_discrete_sequence=[ORANGE],
        )

        fig.update_yaxes(title="Labour Cost (%)")
        show_chart(fig, 330)

    # Roster

    section("Recommended Employee Roster")

    if not recommended_roster.empty:

        roster = recommended_roster.copy()

        if "date" in roster.columns:
            roster["date"] = pd.to_datetime(
                roster["date"], errors="coerce"
            )

            if "date" in wf.columns and not wf.empty:
                available_dates = sorted(
                    wf["date"].dropna().dt.date.unique()
                )

                if available_dates:
                    selected_day = st.selectbox(
                        "Select roster date",
                        available_dates,
                    )

                    roster = roster[
                        roster["date"].dt.date == selected_day
                    ]

        show_table(roster, 350)

    else:
        show_empty("Recommended roster CSV is unavailable.")

    # Coverage and staffing gaps

    section("Staffing Coverage")

    col1, col2 = st.columns(2)

    with col1:
        if not staffing_coverage.empty:

            coverage = staffing_coverage.copy()

            if "coverage_status" in coverage.columns:
                status_counts = (
                    coverage["coverage_status"]
                    .value_counts()
                    .reset_index()
                )
                status_counts.columns = [
                    "status",
                    "count",
                ]

                fig = px.pie(
                    status_counts,
                    names="status",
                    values="count",
                    hole=0.58,
                    title="Coverage Status",
                    color_discrete_sequence=[
                        GREEN, ORANGE, RED, BLUE
                    ],
                )
                show_chart(fig, 330)
            else:
                show_table(coverage, 330)

        else:
            show_empty("Staffing coverage data unavailable.")

    with col2:
        if not staffing_gaps.empty:

            gaps = staffing_gaps.copy()

            gap_col = first_existing_column(
                gaps,
                ["unfilled", "shortfall"],
            )

            role_col = first_existing_column(
                gaps,
                ["role"],
            )

            if gap_col and role_col:
                gap_summary = (
                    gaps.groupby(role_col)[gap_col]
                    .sum()
                    .reset_index()
                )

                fig = px.bar(
                    gap_summary,
                    x=role_col,
                    y=gap_col,
                    title="Unfilled Positions by Role",
                    color_discrete_sequence=[RED],
                )
                show_chart(fig, 330)
            else:
                show_table(gaps, 330)

        else:
            show_empty("Staffing gap data unavailable.")

    if not staffing_gaps.empty:
        section("Staffing Gaps — Action Required")
        show_table(staffing_gaps, 300)

    st.caption(
        "The roster and staffing outputs cover the saved forecast horizon. "
        "They are planning recommendations, not confirmed employee shifts."
    )


# ============================================================
# 14. CUSTOMER INTELLIGENCE
# ============================================================

def customer_intelligence():

    page_header(
        "Customer Intelligence",
        "Understand customer feedback, satisfaction patterns and customer value.",
    )

    add_synthetic_disclosure()

    # Customer KPIs

    section("Customer Intelligence KPIs")

    if not customer_kpis.empty:

        if {"Metric", "Value"}.issubset(customer_kpis.columns):

            metrics = customer_kpis.to_dict("records")

            cols = st.columns(min(4, len(metrics)))

            for i, item in enumerate(metrics[:4]):
                with cols[i]:
                    value = item["Value"]

                    if isinstance(value, (float, np.floating)):
                        display_value = f"{value:,.2f}"
                    else:
                        display_value = str(value)

                    show_kpi(
                        str(item["Metric"]).upper(),
                        display_value,
                        "Customer analysis",
                    )

            if len(metrics) > 4:
                cols = st.columns(min(4, len(metrics) - 4))

                for i, item in enumerate(metrics[4:8]):
                    with cols[i]:
                        show_kpi(
                            str(item["Metric"]).upper(),
                            str(item["Value"]),
                            "Customer analysis",
                        )

        else:
            show_table(customer_kpis, 250)

    else:
        review_count = len(reviews)

        average_rating = 0
        if not reviews.empty and "rating" in reviews.columns:
            average_rating = numeric_series(
                reviews, "rating"
            ).mean()

        c1, c2 = st.columns(2)

        with c1:
            show_kpi(
                "TOTAL REVIEWS",
                integer(review_count),
                "Available review records",
            )

        with c2:
            show_kpi(
                "AVERAGE RATING",
                f"{average_rating:.2f}/5",
                "Average review rating",
            )

    # Aspect sentiment

    section("Sentiment by Review Aspect")

    if not aspect_summary.empty:

        aspect_col = first_existing_column(
            aspect_summary,
            ["aspect", "review_aspect"],
        )

        if aspect_col:

            sentiment_cols = [
                c for c in aspect_summary.columns
                if c.lower().startswith(
                    ("positive", "neutral", "negative")
                )
            ]

            if sentiment_cols:

                plot_data = aspect_summary.melt(
                    id_vars=[aspect_col],
                    value_vars=sentiment_cols,
                    var_name="sentiment",
                    value_name="value",
                )

                fig = px.bar(
                    plot_data,
                    x=aspect_col,
                    y="value",
                    color="sentiment",
                    barmode="group",
                    title="Sentiment Distribution by Aspect",
                    color_discrete_map={
                        "Positive (%)": GREEN,
                        "Neutral (%)": ORANGE,
                        "Negative (%)": RED,
                        "Positive": GREEN,
                        "Neutral": ORANGE,
                        "Negative": RED,
                    },
                )

                show_chart(fig, 380)

            else:
                show_table(aspect_summary, 300)

        else:
            show_table(aspect_summary, 300)

    else:
        show_empty(
            "Aspect sentiment export not found. Run Notebook 04."
        )

    # Improvement areas

    section("Customer Improvement Priorities")

    if not improvement_areas.empty:
        show_table(improvement_areas, 280)
    else:
        show_empty("Customer improvement areas are unavailable.")

    # Monthly sentiment

    section("Customer Sentiment Over Time")

    if not monthly_sentiment.empty:

        month_col = first_existing_column(
            monthly_sentiment,
            ["review_month", "month"],
        )

        if month_col:

            sentiment_cols = [
                c for c in monthly_sentiment.columns
                if c.lower().startswith(
                    ("positive", "neutral", "negative")
                )
            ]

            if sentiment_cols:

                monthly_plot = monthly_sentiment.melt(
                    id_vars=[month_col],
                    value_vars=sentiment_cols,
                    var_name="sentiment",
                    value_name="value",
                )

                fig = px.line(
                    monthly_plot,
                    x=month_col,
                    y="value",
                    color="sentiment",
                    markers=True,
                    title="Monthly Sentiment Trend",
                    color_discrete_map={
                        "Positive (%)": GREEN,
                        "Neutral (%)": ORANGE,
                        "Negative (%)": RED,
                        "Positive": GREEN,
                        "Neutral": ORANGE,
                        "Negative": RED,
                    },
                )

                show_chart(fig, 360)

            else:
                show_table(monthly_sentiment, 300)

        else:
            show_table(monthly_sentiment, 300)

    else:
        show_empty("Monthly sentiment data unavailable.")

    # Customer types

    section("Customer Type Analysis")

    col1, col2 = st.columns(2)

    with col1:
        if not ratings_by_type.empty:
            show_table(ratings_by_type, 300)
        else:
            show_empty("Customer ratings by type unavailable.")

    with col2:
        if not feedback_by_type.empty:
            show_table(feedback_by_type, 300)
        else:
            show_empty("Customer feedback by type unavailable.")

    # RFM segmentation

    section("Customer Value and RFM Segmentation")

    col1, col2 = st.columns(2)

    with col1:
        if not rfm_segments.empty:

            segment_col = first_existing_column(
                rfm_segments,
                ["RFM_Segment", "segment"],
            )

            if segment_col:
                segment_counts = (
                    rfm_segments[segment_col]
                    .value_counts()
                    .reset_index()
                )
                segment_counts.columns = [
                    "segment",
                    "customers",
                ]

                fig = px.pie(
                    segment_counts,
                    names="segment",
                    values="customers",
                    hole=0.55,
                    title="Customer Segment Distribution",
                    color_discrete_sequence=CHART_COLORS,
                )

                show_chart(fig, 340)
            else:
                show_table(rfm_segments, 300)

        else:
            show_empty("RFM segmentation data unavailable.")

    with col2:
        if not segment_profile.empty:
            show_table(segment_profile, 340)
        else:
            show_empty("Customer segment profile unavailable.")

    if not feedback_by_segment.empty:
        section("Feedback by Customer Segment")
        show_table(feedback_by_segment, 300)

    # High-value negative feedback

    section("High-Value Customers with Negative Feedback")

    if not high_value_negative.empty:

        st.markdown(
            """
            <div class="insight-box">
            These records help prioritise customer-service follow-up.
            They identify high-spending customers associated with
            negative feedback; they are not a churn prediction.
            </div>
            """,
            unsafe_allow_html=True,
        )

        show_table(high_value_negative, 350)

    else:
        show_empty("No high-value negative feedback records available.")

    # Review explorer

    section("Customer Feedback Explorer")

    if not review_aspect_detail.empty:

        detail = review_aspect_detail.copy()

        if "aspect" in detail.columns:
            aspects = sorted(
                detail["aspect"].dropna().astype(str).unique()
            )

            selected_aspects = st.multiselect(
                "Filter by review aspect",
                aspects,
                default=aspects,
            )

            detail = detail[
                detail["aspect"].astype(str).isin(selected_aspects)
            ]

        if "sentiment" in detail.columns:
            sentiments = sorted(
                detail["sentiment"].dropna().astype(str).unique()
            )

            selected_sentiments = st.multiselect(
                "Filter by sentiment",
                sentiments,
                default=sentiments,
            )

            detail = detail[
                detail["sentiment"].astype(str).isin(
                    selected_sentiments
                )
            ]

        show_table(detail, 400)

    else:
        show_empty("Review aspect detail data unavailable.")

    st.caption(
        "Sentiment labels are synthetic annotations included in the "
        "dataset. They are not live model predictions."
    )


# ============================================================
# 15. MENU PERFORMANCE
# ============================================================

def menu_performance():

    page_header(
        "Menu Performance",
        "Measure product popularity, contribution, category performance and menu opportunities.",
    )

    add_synthetic_disclosure()

    if calculated_products.empty:
        show_empty(
            "Menu performance is unavailable. Check the cleaned product "
            "and order-item CSV files or run Notebook 05."
        )
        return

    mp = calculated_products.copy()

    product_col = first_existing_column(
        mp,
        ["product_name", "product"],
    )

    category_col = first_existing_column(
        mp,
        ["category"],
    )

    quantity_col = first_existing_column(
        mp,
        ["quantity_sold", "total_quantity", "quantity"],
    )

    revenue_col = first_existing_column(
        mp,
        ["revenue", "total_revenue", "line_total"],
    )

    profit_col = first_existing_column(
        mp,
        ["gross_profit", "total_gross_profit"],
    )

    margin_col = first_existing_column(
        mp,
        ["gross_margin_pct", "gross_margin"],
    )

    if not all([product_col, quantity_col, revenue_col]):
        show_empty("Required menu performance columns are missing.")
        return

    mp[quantity_col] = numeric_series(mp, quantity_col)
    mp[revenue_col] = numeric_series(mp, revenue_col)

    if profit_col:
        mp[profit_col] = numeric_series(mp, profit_col)

    total_quantity = mp[quantity_col].sum()
    total_revenue = mp[revenue_col].sum()

    total_profit = (
        mp[profit_col].sum()
        if profit_col
        else 0
    )

    overall_margin = safe_divide(
        total_profit, total_revenue
    ) * 100

    # Menu KPIs

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        show_kpi(
            "MENU REVENUE",
            money(total_revenue),
            "Revenue from menu items",
        )

    with c2:
        show_kpi(
            "UNITS SOLD",
            integer(total_quantity),
            "Total quantity sold",
        )

    with c3:
        show_kpi(
            "GROSS PROFIT",
            money(total_profit),
            "Revenue less product cost",
        )

    with c4:
        show_kpi(
            "GROSS MARGIN",
            percentage(overall_margin),
            "Gross profit / revenue",
        )

    # Product performance

    section("Product Performance")

    left, right = st.columns(2)

    with left:

        top_products = mp.nlargest(10, revenue_col)

        fig = px.bar(
            top_products.sort_values(revenue_col),
            x=revenue_col,
            y=product_col,
            orientation="h",
            title="Top 10 Products by Revenue",
            color_discrete_sequence=[BLUE],
        )

        fig.update_layout(
            xaxis_title="Revenue (€)",
            yaxis_title="",
        )

        show_chart(fig, 400)

    with right:

        top_quantity = mp.nlargest(10, quantity_col)

        fig = px.bar(
            top_quantity.sort_values(quantity_col),
            x=quantity_col,
            y=product_col,
            orientation="h",
            title="Top 10 Best-Selling Products",
            color_discrete_sequence=[GREEN],
        )

        fig.update_layout(
            xaxis_title="Units Sold",
            yaxis_title="",
        )

        show_chart(fig, 400)

    # Profitability

    section("Product Profitability")

    if profit_col:

        profit_display = mp.nlargest(12, profit_col)

        fig = px.bar(
            profit_display.sort_values(profit_col),
            x=profit_col,
            y=product_col,
            orientation="h",
            title="Products by Gross Profit",
            color_discrete_sequence=[PURPLE],
        )

        show_chart(fig, 400)

    if margin_col:
        fig = px.scatter(
            mp,
            x=revenue_col,
            y=margin_col,
            size=quantity_col,
            color=category_col if category_col else None,
            hover_name=product_col,
            title="Product Revenue vs Gross Margin",
            color_discrete_sequence=CHART_COLORS,
        )

        fig.update_layout(
            xaxis_title="Revenue (€)",
            yaxis_title="Gross Margin (%)",
        )

        show_chart(fig, 430)

    # Category analysis

    section("Category Performance")

    if not calculated_categories.empty:

        cat = calculated_categories.copy()

        cat_revenue = first_existing_column(
            cat,
            ["revenue", "total_revenue"],
        )

        cat_profit = first_existing_column(
            cat,
            ["gross_profit", "total_gross_profit"],
        )

        cat_quantity = first_existing_column(
            cat,
            ["quantity_sold", "total_quantity"],
        )

        if cat_revenue:

            fig = px.bar(
                cat,
                x="category",
                y=cat_revenue,
                title="Revenue by Category",
                color_discrete_sequence=[BLUE],
            )

            show_chart(fig, 340)

        if cat_profit:
            fig = px.bar(
                cat,
                x="category",
                y=cat_profit,
                title="Gross Profit by Category",
                color_discrete_sequence=[GREEN],
            )

            show_chart(fig, 340)

        show_table(cat, 300)

    elif category_col:

        category_summary = (
            mp.groupby(category_col, as_index=False)
            .agg(
                revenue=(revenue_col, "sum"),
                quantity_sold=(quantity_col, "sum"),
            )
        )

        fig = px.bar(
            category_summary,
            x=category_col,
            y="revenue",
            title="Revenue by Category",
            color_discrete_sequence=[BLUE],
        )

        show_chart(fig, 340)

    # Menu engineering

    section("Menu Engineering Matrix")

    st.markdown(
        """
        <div class="insight-box">
        Menu engineering classifies products using two dimensions:
        <b>popularity</b> (sales mix) and
        <b>profitability</b> (contribution margin per unit).
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not menu_engineering.empty:

        engineering = menu_engineering.copy()

    else:
        # Build a fallback classification if Notebook 05 export
        # has not yet been created.

        engineering = mp.copy()

        contribution_col = first_existing_column(
            engineering,
            [
                "contribution_margin_per_unit",
                "contribution_margin",
            ],
        )

        if not contribution_col and profit_col:
            engineering["contribution_margin_per_unit"] = (
                engineering[profit_col]
                / engineering[quantity_col].replace(0, np.nan)
            ).fillna(0)

            contribution_col = "contribution_margin_per_unit"

        if contribution_col:

            engineering["sales_mix_pct"] = (
                engineering[quantity_col]
                / max(total_quantity, 1)
                * 100
            )

            popularity_threshold = (
                0.70 * 100 / max(len(engineering), 1)
            )

            profitability_threshold = engineering[
                contribution_col
            ].mean()

            engineering["Popularity"] = np.where(
                engineering["sales_mix_pct"] >= popularity_threshold,
                "High",
                "Low",
            )

            engineering["Profitability"] = np.where(
                engineering[contribution_col] >= profitability_threshold,
                "High",
                "Low",
            )

            def classify_menu(row):
                if (
                    row["Popularity"] == "High"
                    and row["Profitability"] == "High"
                ):
                    return "Star"

                if (
                    row["Popularity"] == "High"
                    and row["Profitability"] == "Low"
                ):
                    return "Plowhorse"

                if (
                    row["Popularity"] == "Low"
                    and row["Profitability"] == "High"
                ):
                    return "Puzzle"

                return "Dog"

            engineering["menu_class"] = engineering.apply(
                classify_menu,
                axis=1,
            )

    class_col = first_existing_column(
        engineering,
        ["menu_class", "Menu_Class", "classification", "class"],
    )

    if class_col:

        engineering[class_col] = (
            engineering[class_col].astype(str).str.title()
        )

        class_colors = {
            "Star": GREEN,
            "Plowhorse": BLUE,
            "Puzzle": PURPLE,
            "Dog": "#8D929B",
        }

        class_counts = (
            engineering[class_col]
            .value_counts()
            .reindex(
                ["Star", "Plowhorse", "Puzzle", "Dog"],
                fill_value=0,
            )
            .reset_index()
        )

        class_counts.columns = ["menu_class", "products"]

        col1, col2 = st.columns([1, 1.5])

        with col1:

            fig = px.pie(
                class_counts,
                names="menu_class",
                values="products",
                hole=0.58,
                title="Menu Classification",
                color="menu_class",
                color_discrete_map=class_colors,
            )

            show_chart(fig, 350)

        with col2:

            show_table(engineering, 350)

        # Class explanation

        st.markdown(
            """
            <div class="panel">
                <h4 style="color:#239B68;">★ Stars</h4>
                <b>Popular + profitable</b>
                <p>Customers order these frequently and they generate
                strong contribution.</p>
                <span style="color:#239B68;">
                Action: Protect quality and promote.
                </span>
            </div>

            <div class="panel">
                <h4 style="color:#3974D5;">🐴 Plowhorses</h4>
                <b>Popular + less profitable</b>
                <p>They sell frequently, but contribution per unit is
                relatively low.</p>
                <span style="color:#3974D5;">
                Action: Review pricing, portions and costs.
                </span>
            </div>

            <div class="panel">
                <h4 style="color:#8957C8;">? Puzzles</h4>
                <b>Less popular + profitable</b>
                <p>They generate good contribution, but relatively few
                customers order them.</p>
                <span style="color:#8957C8;">
                Action: Improve visibility and promotion.
                </span>
            </div>

            <div class="panel">
                <h4 style="color:#777777;">🐕 Dogs</h4>
                <b>Less popular + less profitable</b>
                <p>They sell relatively little and generate relatively
                low contribution.</p>
                <span style="color:#777777;">
                Action: Review, redesign or consider removal.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        show_empty(
            "Menu engineering classification is unavailable. "
            "Check the menu_engineering.csv export from Notebook 05."
        )

    # Monthly menu trends

    section("Menu Sales Trends")

    if not menu_monthly.empty:

        month_col = first_existing_column(
            menu_monthly,
            ["month", "order_month", "date"],
        )

        monthly_revenue_col = first_existing_column(
            menu_monthly,
            ["revenue", "total_revenue"],
        )

        if month_col and monthly_revenue_col:

            fig = px.line(
                menu_monthly,
                x=month_col,
                y=monthly_revenue_col,
                markers=True,
                title="Monthly Menu Revenue",
                color_discrete_sequence=[BLUE],
            )

            show_chart(fig, 360)

        else:
            show_table(menu_monthly, 300)

    else:
        show_empty(
            "Monthly menu export unavailable. "
            "Run Notebook 05 to generate it."
        )

    # Discount analysis

    section("Discount Performance")

    if not menu_discounts.empty:
        show_table(menu_discounts, 300)
    else:
        st.caption(
            "Discount analysis is available after running Notebook 05."
        )

    # Recommendations

    section("Menu Recommendations")

    if not menu_recommendations.empty:
        show_table(menu_recommendations, 350)

    else:
        st.markdown(
            """
            **Suggested management actions**

            - Protect Star products through consistent quality and availability.
            - Review the price and portion costs of Plowhorses.
            - Test menu placement and promotion for Puzzles.
            - Evaluate whether Dogs should be redesigned or removed.
            """
        )

    st.caption(
        "Gross profit here means menu revenue less product cost. "
        "It is not net profit and excludes labour, rent, utilities "
        "and other operating expenses. Menu engineering thresholds "
        "are analytical conventions, not universal rules."
    )


# ============================================================
# 16. APPLICATION ROUTER
# ============================================================

if navigation == "Executive Overview":
    executive_overview()

elif navigation == "Revenue Intelligence":
    revenue_intelligence()

elif navigation == "Workforce Intelligence":
    workforce_intelligence()

elif navigation == "Customer Intelligence":
    customer_intelligence()

elif navigation == "Menu Performance":
    menu_performance()


# ============================================================
# 17. FOOTER
# ============================================================

st.markdown("---")

st.markdown(
    """
    <div style="
        text-align:center;
        color:#8A94A4;
        font-size:11px;
        padding:8px;
    ">
        RESTRODINE · RESTAURANT INTELLIGENCE PLATFORM<br>
        Synthetic demonstration dataset · Built with Python and Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)