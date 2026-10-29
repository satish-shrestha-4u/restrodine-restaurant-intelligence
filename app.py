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


@st.cache_data
def load_data():
    df = pd.read_csv(
        DATA_PATH,
        parse_dates=["date"]
    )

    df = df.sort_values("date").reset_index(drop=True)

    # Make sure numeric columns are numeric
    numeric_columns = [
        "revenue",
        "orders",
        "average_order_value",
        "orders_lunch",
        "orders_afternoon",
        "orders_dinner",
        "orders_dine_in",
        "orders_delivery",
        "orders_takeaway",
        "drink_revenue",
        "temperature_avg_c",
        "temp_max_c",
        "temp_min_c",
        "precipitation_mm"
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # Boolean/integer flags
    flag_columns = [
        "is_weekend",
        "is_holiday",
        "is_rainy",
        "is_promo_day"
    ]

    for column in flag_columns:
        if column in df.columns:
            df[column] = df[column].astype(int)

    return df


# ============================================================
# LOAD DATA
# ============================================================

try:
    df = load_data()
    data_available = True

except FileNotFoundError:
    data_available = False
    st.error(
        "daily_model_table_clean.csv was not found. "
        "Please make sure the file is located in data_clean/."
    )
    st.stop()


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

    st.caption(
        f"Historical data: "
        f"{df['date'].min().date()} → {latest_date.date()}"
    )

    st.divider()

    # --------------------------------------------------------
    # Historical revenue
    # --------------------------------------------------------

    st.subheader("Historical Revenue")

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

    # --------------------------------------------------------
    # Revenue by weekday
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Average Revenue by Day")

        if "day_of_week" in df.columns:

            day_order = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday"
            ]

            day_revenue = (
                df.groupby("day_of_week")["revenue"]
                .mean()
                .reindex(day_order)
                .reset_index()
            )

            fig = px.bar(
                day_revenue,
                x="day_of_week",
                y="revenue",
                title="Average Revenue by Weekday"
            )

            fig.update_layout(
                xaxis_title="Day",
                yaxis_title="Average Revenue (€)"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    # --------------------------------------------------------
    # Promotion impact
    # --------------------------------------------------------

    with col2:

        st.subheader("Promotion Impact")

        promo = (
            df.groupby("is_promo_day")["revenue"]
            .mean()
            .reset_index()
        )

        promo["Promotion"] = promo["is_promo_day"].map({
            0: "No Promotion",
            1: "Promotion"
        })

        fig = px.bar(
            promo,
            x="Promotion",
            y="revenue",
            title="Average Revenue: Promotion vs No Promotion"
        )

        fig.update_layout(
            xaxis_title="",
            yaxis_title="Average Revenue (€)"
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
        ### Interactive Revenue Forecast

        Change the date, weather, promotion and holiday assumptions
        to explore how the revenue forecast changes.
        """
    )

    # ========================================================
    # HISTORICAL DATA
    # ========================================================

    st.subheader("Historical Revenue")

    fig = px.line(
        df,
        x="date",
        y="revenue",
        title="Historical Daily Revenue"
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

    st.divider()

    # ========================================================
    # FORECAST SETTINGS
    # ========================================================

    st.subheader("🔮 Forecast Settings")

    col1, col2, col3 = st.columns(3)

    latest_date = df["date"].max().date()

    with col1:

        forecast_start = st.date_input(
            "Forecast start date",
            value=(
                pd.Timestamp(latest_date)
                + pd.Timedelta(days=1)
            ).date(),
            min_value=(
                pd.Timestamp(latest_date)
                + pd.Timedelta(days=1)
            ).date()
        )

    with col2:

        forecast_days = st.selectbox(
            "Forecast horizon",
            [7, 14, 30],
            index=2
        )

    with col3:

        model_choice = st.selectbox(
            "Forecast model",
            [
                "Prophet",
                "Weekday Mean"
            ]
        )

    st.divider()

    # ========================================================
    # SCENARIO INPUTS
    # ========================================================

    st.subheader("🌦️ Business Scenario")

    st.markdown(
        """
        These inputs represent the conditions you want to test.
        For the current prototype, the selected weather and
        promotion conditions are applied across the forecast period.
        """
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        temperature = st.slider(
            "Average temperature (°C)",
            min_value=-5.0,
            max_value=35.0,
            value=float(
                df["temperature_avg_c"].mean()
            ),
            step=0.5
        )

    with col2:

        precipitation = st.slider(
            "Precipitation (mm)",
            min_value=0.0,
            max_value=30.0,
            value=0.0,
            step=0.5
        )

    with col3:

        is_holiday = st.checkbox(
            "Holiday",
            value=False
        )

    with col4:

        is_promo = st.checkbox(
            "Promotion",
            value=False
        )

    if precipitation >= 1:
        is_rainy = 1
        weather_condition = "Rain"
    else:
        is_rainy = 0
        weather_condition = "Clear"

    promotion_discount = 0.0

    if is_promo:

        promotion_discount = st.slider(
            "Promotion discount (%)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=1.0
        )

    st.info(
        f"Scenario: "
        f"{temperature:.1f}°C · "
        f"{precipitation:.1f} mm precipitation · "
        f"{weather_condition} · "
        f"{'Holiday' if is_holiday else 'Normal day'} · "
        f"{'Promotion' if is_promo else 'No promotion'}"
    )

    # ========================================================
    # BUILD FUTURE DATAFRAME
    # ========================================================

    forecast_dates = pd.date_range(
        start=forecast_start,
        periods=forecast_days,
        freq="D"
    )

    future_df = pd.DataFrame({
        "date": forecast_dates,
        "temperature_avg_c": temperature,
        "precipitation_mm": precipitation,
        "is_rainy": is_rainy,
        "is_holiday": int(is_holiday),
        "is_promo_day": int(is_promo)
    })

    # ========================================================
    # WEEKDAY MEAN FORECAST
    # ========================================================

    weekday_means = (
        df.groupby(
            df["date"].dt.dayofweek
        )["revenue"]
        .mean()
    )

    future_df["weekday_mean_forecast"] = (
        future_df["date"]
        .dt.dayofweek
        .map(weekday_means)
    )

    # ========================================================
    # PROPHET FORECAST
    # ========================================================

    prophet_available = True

    try:

        from prophet import Prophet

        prophet_train = df[
            [
                "date",
                "revenue",
                "temperature_avg_c",
                "precipitation_mm",
                "is_rainy",
                "is_holiday",
                "is_promo_day"
            ]
        ].copy()

        prophet_train = prophet_train.rename(
            columns={
                "date": "ds",
                "revenue": "y"
            }
        )

        model = Prophet(
            weekly_seasonality=True,
            yearly_seasonality=True,
            daily_seasonality=False
        )

        model.add_regressor(
            "temperature_avg_c"
        )

        model.add_regressor(
            "precipitation_mm"
        )

        model.add_regressor(
            "is_rainy"
        )

        model.add_regressor(
            "is_holiday"
        )

        model.add_regressor(
            "is_promo_day"
        )

        model.fit(prophet_train)

        prophet_future = future_df[
            [
                "date",
                "temperature_avg_c",
                "precipitation_mm",
                "is_rainy",
                "is_holiday",
                "is_promo_day"
            ]
        ].rename(
            columns={
                "date": "ds"
            }
        )

        prophet_prediction = model.predict(
            prophet_future
        )

        future_df["prophet_forecast"] = (
            prophet_prediction["yhat"]
            .clip(lower=0)
            .values
        )

    except Exception as e:

        prophet_available = False

        future_df["prophet_forecast"] = (
            future_df["weekday_mean_forecast"]
        )

        st.warning(
            "Prophet could not be used. "
            "The app is showing the Weekday Mean forecast instead."
        )

    # ========================================================
    # SELECT MODEL
    # ========================================================

    if model_choice == "Prophet" and prophet_available:

        future_df["forecast"] = (
            future_df["prophet_forecast"]
        )

        selected_model_name = "Prophet"

    else:

        future_df["forecast"] = (
            future_df["weekday_mean_forecast"]
        )

        selected_model_name = "Weekday Mean"

    # ========================================================
    # FORECAST KPIs
    # ========================================================

    total_forecast = future_df["forecast"].sum()

    average_forecast = future_df["forecast"].mean()

    historical_daily_average = df["revenue"].mean()

    change_vs_historical = (
        (average_forecast / historical_daily_average) - 1
    ) * 100

    # Estimate orders using historical AOV
    historical_aov = (
        df["average_order_value"].mean()
    )

    estimated_orders = (
        total_forecast / historical_aov
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Forecast Revenue",
        f"€{total_forecast:,.0f}"
    )

    col2.metric(
        "Average Daily Revenue",
        f"€{average_forecast:,.0f}"
    )

    col3.metric(
        "Expected Orders",
        f"{estimated_orders:,.0f}"
    )

    col4.metric(
        "vs Historical Average",
        f"{change_vs_historical:+.1f}%"
    )

    st.caption(
        f"Forecast model: **{selected_model_name}**"
    )

    st.divider()

    # ========================================================
    # FORECAST CHART
    # ========================================================

    st.subheader("📊 Revenue Forecast")

    historical_recent = df[
        df["date"] >= (
            pd.Timestamp(forecast_start)
            - pd.Timedelta(days=60)
        )
    ][
        ["date", "revenue"]
    ].copy()

    historical_recent["Type"] = "Historical"

    forecast_plot = future_df[
        ["date", "forecast"]
    ].copy()

    forecast_plot = forecast_plot.rename(
        columns={
            "forecast": "revenue"
        }
    )

    forecast_plot["Type"] = "Forecast"

    plot_df = pd.concat(
        [
            historical_recent,
            forecast_plot
        ],
        ignore_index=True
    )

    fig = px.line(
        plot_df,
        x="date",
        y="revenue",
        color="Type",
        title=(
            f"Historical Revenue + "
            f"{selected_model_name} Forecast"
        )
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

    # ========================================================
    # DAILY FORECAST TABLE
    # ========================================================

    st.subheader("📅 Daily Forecast")

    display_forecast = future_df[
        [
            "date",
            "temperature_avg_c",
            "precipitation_mm",
            "is_holiday",
            "is_promo_day",
            "forecast"
        ]
    ].copy()

    display_forecast["Holiday"] = (
        display_forecast["is_holiday"]
        .map({
            0: "No",
            1: "Yes"
        })
    )

    display_forecast["Promotion"] = (
        display_forecast["is_promo_day"]
        .map({
            0: "No",
            1: "Yes"
        })
    )

    display_forecast = display_forecast[
        [
            "date",
            "temperature_avg_c",
            "precipitation_mm",
            "Holiday",
            "Promotion",
            "forecast"
        ]
    ]

    display_forecast = display_forecast.rename(
        columns={
            "date": "Date",
            "temperature_avg_c"
            "precipitation_mm": "Precipitation (mm)",
            "forecast": "Forecast Revenue (€)"
        }
    )

    st.dataframe(
        display_forecast.style.format({
            "Temperature (°C)": "{:.1f}",
            "Precipitation (mm)": "{:.1f}",
            "Forecast Revenue (€)": "€{:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # WEEKDAY PATTERN
    # ========================================================

    st.subheader("Revenue Forecast by Day of Week")

    weekday_forecast = (
        future_df.assign(
            day_of_week=
            future_df["date"].dt.day_name()
        )
        .groupby("day_of_week")["forecast"]
        .mean()
        .reindex([
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ])
        .reset_index()
    )

    fig = px.bar(
        weekday_forecast,
        x="day_of_week",
        y="forecast",
        title="Average Forecast Revenue by Weekday"
    )

    fig.update_layout(
        xaxis_title="Day",
        yaxis_title="Forecast Revenue (€)"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ========================================================
    # MODEL COMPARISON
    # ========================================================

    st.divider()

    st.subheader("🏆 Current Baseline Validation")

    # Latest rolling validation results from your notebook
    model_results = pd.DataFrame({
        "Model": [
            "Weekday Mean",
            "Seasonal Naive",
            "Recent Mean",
            "Mean",
            "Drift",
            "Naive"
        ],
        "MAE": [
            431.64,
            556.35,
            959.34,
            946.32,
            1427.95,
            1439.36
        ],
        "RMSE": [
            563.71,
            720.18,
            1211.03,
            1213.95,
            1844.36,
            1854.49
        ],
        "MAPE (%)": [
            14.46,
            18.94,
            34.27,
            33.06,
            40.84,
            41.20
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

    best_model = model_results.loc[
        model_results["MAE"].idxmin(),
        "Model"
    ]

    st.success(
        f"Current benchmark: **{best_model}** "
        f"with MAPE of **14.46%**."
    )

    # ========================================================
    # MODEL STATUS
    # ========================================================

    st.subheader("Forecasting Model Development")

    st.markdown(
        """
        **Current status**

        - ✅ Naive baseline
        - ✅ Mean baseline
        - ✅ Recent Mean baseline
        - ✅ Drift baseline
        - ✅ Seasonal Naive baseline
        - ✅ Weekday Mean baseline
        - 🔄 Moving Average
        - 🔄 Autoregressive (AR)
        - 🔄 ARIMA
        - 🔄 SARIMA
        - 🔄 Prophet
        - 🔄 SARIMAX
        - 🔄 Random Forest

        The final production model will be selected using
        out-of-sample MAE, RMSE and MAPE.
        """
    )

    st.info(
        "The interactive Prophet forecast is currently a prototype. "
        "The final model will be selected after the complete "
        "forecasting model comparison is finished."
    )


# ============================================================
# WORKFORCE INTELLIGENCE
# ============================================================

elif page == "Workforce Intelligence":

    st.header("👥 Workforce Intelligence")

    st.markdown(
        """
        ### Forecast demand → Plan staffing → Build the roster

        This module will use the selected revenue forecast to
        calculate expected demand, staffing requirements,
        labour cost and roster recommendations.
        """
    )

    st.info(
        "Workforce Intelligence will be connected to the "
        "forecasting model after the revenue forecasting phase "
        "is finalized."
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Forecast Demand",
        "—"
    )

    col2.metric(
        "Recommended Staff",
        "—"
    )

    col3.metric(
        "Estimated Labour Cost",
        "—"
    )

    st.divider()

    st.subheader("Planned Workforce Features")

    workforce_features = pd.DataFrame({
        "Feature": [
            "Forecasted orders",
            "Required Waiters",
            "Required Chefs",
            "Kitchen Assistants",
            "Bartenders",
            "Dishwashers",
            "Employee Availability",
            "Labour Cost",
            "Roster Recommendation"
        ],
        "Status": [
            "Planned",
            "Planned",
            "Planned",
            "Planned",
            "Planned",
            "Planned",
            "Data available",
            "Data available",
            "Planned"
        ]
    })

    st.dataframe(
        workforce_features,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# CUSTOMER INTELLIGENCE
# ============================================================

elif page == "Customer Intelligence":

    st.header("💬 Customer Intelligence")

    st.markdown(
        """
        ### Understand what customers like — and what they dislike.

        This module will later connect the review data,
        aspect-level sentiment analysis and customer insights.
        """
    )

    st.info(
        "Customer Intelligence will be connected after the "
        "NLP and customer analysis phase is finalized."
    )

    st.subheader("Available Review Data")

    # These are the validated counts from Notebook 01
    review_count = 12147

    positive = 8903
    neutral = 1543
    negative = 1711

    positive_pct = positive / review_count * 100
    neutral_pct = neutral / review_count * 100
    negative_pct = negative / review_count * 100

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Reviews",
        f"{review_count:,}"
    )

    col2.metric(
        "Positive",
        f"{positive_pct:.1f}%"
    )

    col3.metric(
        "Neutral",
        f"{neutral_pct:.1f}%"
    )

    col4.metric(
        "Negative",
        f"{negative_pct:.1f}%"
    )

    sentiment_demo = pd.DataFrame({
        "Sentiment": [
            "Positive",
            "Neutral",
            "Negative"
        ],
        "Reviews": [
            positive,
            neutral,
            negative
        ]
    })

    fig = px.bar(
        sentiment_demo,
        x="Sentiment",
        y="Reviews",
        title="Current Review Sentiment Distribution"
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
        "The final version will add automated sentiment prediction, "
        "aspect-level sentiment and customer segmentation."
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