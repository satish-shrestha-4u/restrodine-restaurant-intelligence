import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="RestroDine",
    page_icon="🍽️",
    layout="wide"
)


# ============================================================
# LOAD DATA
# ============================================================

DATA_PATH = "data_clean/daily_model_table_clean.csv"

try:
    df = pd.read_csv(
        DATA_PATH,
        parse_dates=["date"]
    )

    data_available = True

except FileNotFoundError:
    data_available = False

    # Demo data so you can see the UI
    dates = pd.date_range(
        start="2025-01-01",
        end="2025-12-31",
        freq="D"
    )

    np.random.seed(42)

    revenue = (
        2800
        + 500 * np.sin(np.arange(len(dates)) / 30)
        + np.random.normal(0, 300, len(dates))
    )

    df = pd.DataFrame({
        "date": dates,
        "revenue": revenue,
        "orders": np.maximum(
            (revenue / 37).astype(int),
            1
        ),
        "average_order_value": revenue / np.maximum(
            (revenue / 37).astype(int),
            1
        ),
        "is_weekend": dates.dayofweek >= 5,
        "is_holiday": False,
        "is_promo_day": False
    })


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🍽️ RestroDine")

st.sidebar.markdown(
    """
    **Restaurant Intelligence Platform**

    Predict demand → Plan resources → Understand customers
    """
)

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    [
        "Executive Overview",
        "Revenue Intelligence",
        "Workforce Intelligence",
        "Customer Intelligence"
    ]
)


# ============================================================
# HEADER
# ============================================================

st.title("🍽️ RestroDine")

st.caption(
    "Restaurant Intelligence & Weather-Aware Revenue Forecasting"
)

if not data_available:
    st.info(
        "Demo mode: daily_model_table_clean.csv was not found. "
        "The dashboard is using simulated data so you can preview the interface."
    )


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

if page == "Executive Overview":

    st.header("Executive Overview")

    latest_date = df["date"].max()

    total_revenue = df["revenue"].sum()
    avg_daily_revenue = df["revenue"].mean()
    total_orders = df["orders"].sum()
    avg_order_value = df["average_order_value"].mean()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Revenue",
        f"€{total_revenue:,.0f}"
    )

    col2.metric(
        "Average Daily Revenue",
        f"€{avg_daily_revenue:,.0f}"
    )

    col3.metric(
        "Total Orders",
        f"{total_orders:,.0f}"
    )

    col4.metric(
        "Average Order Value",
        f"€{avg_order_value:,.2f}"
    )

    st.divider()

    # Revenue trend
    st.subheader("Revenue Trend")

    fig = px.line(
        df,
        x="date",
        y="revenue",
        title="Daily Revenue"
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Revenue (€)",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # Business snapshot
    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Revenue by Day Type")

        if "day_of_week" in df.columns:

            day_revenue = (
                df.groupby("day_of_week")["revenue"]
                .mean()
                .reset_index()
            )

            fig = px.bar(
                day_revenue,
                x="day_of_week",
                y="revenue",
                title="Average Revenue by Day"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    with col2:

        st.subheader("Promotion Impact")

        if "is_promo_day" in df.columns:

            promo = (
                df.groupby("is_promo_day")["revenue"]
                .mean()
                .reset_index()
            )

            promo["is_promo_day"] = promo[
                "is_promo_day"
            ].map({
                0: "No Promotion",
                1: "Promotion"
            })

            fig = px.bar(
                promo,
                x="is_promo_day",
                y="revenue",
                title="Average Revenue"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


# ============================================================
# REVENUE INTELLIGENCE
# ============================================================

elif page == "Revenue Intelligence":

    st.header("📈 Revenue Intelligence")

    st.markdown(
        """
        **Predict demand and identify the factors influencing restaurant revenue.**
        """
    )

    # Date filter
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    selected_dates = st.date_input(
        "Select analysis period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if isinstance(selected_dates, tuple):

        start_date, end_date = selected_dates

        filtered = df[
            (df["date"].dt.date >= start_date)
            &
            (df["date"].dt.date <= end_date)
        ].copy()

    else:
        filtered = df.copy()

    # KPIs
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Revenue",
        f"€{filtered['revenue'].sum():,.0f}"
    )

    col2.metric(
        "Orders",
        f"{filtered['orders'].sum():,.0f}"
    )

    col3.metric(
        "Average Order Value",
        f"€{filtered['average_order_value'].mean():,.2f}"
    )

    st.divider()

    # Historical revenue
    st.subheader("Historical Revenue")

    fig = px.line(
        filtered,
        x="date",
        y="revenue",
        title="Historical Daily Revenue"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # Forecast section
    st.subheader("Revenue Forecast")

    st.info(
        "Forecast model results will appear here after "
        "Prophet, SARIMA/SARIMAX and Random Forest are evaluated."
    )

    forecast_dates = pd.date_range(
        start=df["date"].max() + pd.Timedelta(days=1),
        periods=30
    )

    weekday_mean = (
        df.groupby(df["date"].dt.dayofweek)["revenue"]
        .mean()
    )

    forecast_values = [
        weekday_mean.get(
            date.dayofweek,
            df["revenue"].mean()
        )
        for date in forecast_dates
    ]

    forecast_df = pd.DataFrame({
        "date": forecast_dates,
        "forecast": forecast_values
    })

    fig = px.line(
        forecast_df,
        x="date",
        y="forecast",
        title="Demo 30-Day Revenue Forecast"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # Model comparison
    st.subheader("Model Comparison")

    model_results = pd.DataFrame({
        "Model": [
            "Weekday Mean",
            "Seasonal Naive - Previous Week",
            "Naive - Previous Day"
        ],
        "MAE": [
            375.624744,
            514.204000,
            913.811111
        ],
        "RMSE": [
            486.581958,
            691.989711,
            1165.487736
        ],
        "MAPE (%)": [
            14.478338,
            19.597877,
            33.918617
        ]
    })

    st.dataframe(
        model_results.style.format({
            "MAE": "€{:,.2f}",
            "RMSE": "€{:,.2f}",
            "MAPE (%)": "{:.2f}%"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.success(
        "Current benchmark: Weekday Mean — MAPE 14.48%"
    )

    st.markdown(
        """
        ### Models to be evaluated

        - Weekday Mean
        - Seasonal Naive
        - Prophet
        - SARIMA
        - SARIMAX
        - Random Forest Regressor

        The final model will be selected based on out-of-sample
        MAE, RMSE and MAPE.
        """
    )


# ============================================================
# WORKFORCE INTELLIGENCE
# ============================================================

elif page == "Workforce Intelligence":

    st.header("👥 Workforce Intelligence")

    st.markdown(
        """
        ### Forecast demand → Plan staffing → Build the roster
        """
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Forecast Demand",
        "82 orders"
    )

    col2.metric(
        "Recommended Staff",
        "9 employees"
    )

    col3.metric(
        "Estimated Labour Cost",
        "€412"
    )

    st.divider()

    st.subheader("Staffing Recommendation")

    workforce_demo = pd.DataFrame({
        "Role": [
            "Waiter",
            "Chef",
            "Kitchen Assistant",
            "Bartender",
            "Dishwasher"
        ],
        "Recommended": [
            4,
            2,
            1,
            1,
            1
        ]
    })

    fig = px.bar(
        workforce_demo,
        x="Role",
        y="Recommended",
        title="Recommended Staffing"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.info(
        "This section will use forecasted demand from Revenue Intelligence "
        "to calculate staffing requirements and roster recommendations."
    )


# ============================================================
# CUSTOMER INTELLIGENCE
# ============================================================

elif page == "Customer Intelligence":

    st.header("💬 Customer Intelligence")

    st.markdown(
        """
        ### Understand what customers like — and what they dislike.
        """
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Reviews",
        "4,306"
    )

    col2.metric(
        "Positive Sentiment",
        "73%"
    )

    col3.metric(
        "Negative Sentiment",
        "14%"
    )

    st.divider()

    sentiment_demo = pd.DataFrame({
        "Sentiment": [
            "Positive",
            "Neutral",
            "Negative"
        ],
        "Reviews": [
            8903,
            1543,
            1711
        ]
    })

    fig = px.bar(
        sentiment_demo,
        x="Sentiment",
        y="Reviews",
        title="Customer Sentiment"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader("Review Aspects")

    aspect_demo = pd.DataFrame({
        "Aspect": [
            "Food",
            "Service",
            "Waiting Time",
            "Atmosphere",
            "Staff",
            "Price",
            "Drinks",
            "Cleanliness"
        ],
        "Reviews": [
            3685,
            1810,
            1686,
            1388,
            1340,
            1149,
            637,
            462
        ]
    })

    fig = px.bar(
        aspect_demo,
        x="Aspect",
        y="Reviews",
        title="Customer Review Aspects"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.info(
        "This section will later connect review text, aspect-level sentiment "
        "and customer insights to operational decisions."
    )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "RestroDine • Restaurant Intelligence Platform"
)

st.sidebar.caption(
    "Data Science & AI Project"
)