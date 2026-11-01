import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import json
from pathlib import Path
from dateutil.easter import easter

from prophet.serialize import model_from_json


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
        ### Weather-Aware Revenue Forecast

        The dashboard uses the **final production Prophet model** from
        the revenue forecasting notebook. It combines weekly seasonality
        with calendar/business effects and weather information.
        """
    )

    # ========================================================
    # PRODUCTION MODEL CONFIGURATION
    # ========================================================

    # IMPORTANT: these must match the regressors stored in the
    # serialized production Prophet model.
    SELECTED_PROPHET_REGRESSORS = [
        "is_weekend",
        "is_holiday",
        "is_promo_day",
        "temperature_avg_c",
        "precipitation_mm",
        "is_rainy"
    ]

    RAIN_THRESHOLD_MM = 1.0
    RESTAURANT_LATITUDE = 51.4324
    RESTAURANT_LONGITUDE = 7.00435
    WEATHER_TIMEZONE = "Europe/Berlin"
    PLANNED_PROMOTION_DATES = []

    MODEL_DIR = Path("models")
    MODEL_PATH = MODEL_DIR / "restrodine_prophet_calendar_weather.json"
    METADATA_PATH = (
        MODEL_DIR /
        "restrodine_prophet_calendar_weather_metadata.json"
    )

    # ========================================================
    # LOAD PRODUCTION MODEL
    # ========================================================

    @st.cache_resource
    def load_production_model(model_path):
        if not model_path.exists():
            raise FileNotFoundError(
                f"Production model not found: {model_path}"
            )

        with open(model_path, "r") as file:
            return model_from_json(file.read())

    @st.cache_data
    def load_model_metadata(metadata_path):
        if not metadata_path.exists():
            return {}

        with open(metadata_path, "r") as file:
            return json.load(file)

    try:
        production_model = load_production_model(MODEL_PATH)
        model_metadata = load_model_metadata(METADATA_PATH)
        model_available = True
    except Exception as e:
        model_available = False
        st.error(
            "The production forecasting model could not be loaded. "
            f"Expected: {MODEL_PATH}"
        )
        st.exception(e)
        st.stop()

    # ========================================================
    # NRW PUBLIC HOLIDAYS
    # ========================================================

    def get_nrw_public_holidays(year):
        easter_sunday = pd.Timestamp(easter(year))

        return {
            pd.Timestamp(year, 1, 1): "New Year's Day",
            easter_sunday - pd.Timedelta(days=2): "Good Friday",
            easter_sunday + pd.Timedelta(days=1): "Easter Monday",
            easter_sunday + pd.Timedelta(days=39): "Ascension Day",
            easter_sunday + pd.Timedelta(days=50): "Whit Monday",
            easter_sunday + pd.Timedelta(days=60): "Corpus Christi",
            pd.Timestamp(year, 5, 1): "Labour Day",
            pd.Timestamp(year, 10, 3): "German Unity Day",
            pd.Timestamp(year, 11, 1): "All Saints' Day",
            pd.Timestamp(year, 12, 25): "Christmas Day",
            pd.Timestamp(year, 12, 26): "Boxing Day"
        }

    # ========================================================
    # OPEN-METEO WEATHER API
    # ========================================================

    @st.cache_data(ttl=60 * 60)
    def fetch_openmeteo_daily_weather(
        latitude,
        longitude,
        start_date,
        end_date
    ):
        url = "https://api.open-meteo.com/v1/forecast"

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": (
                "temperature_2m_mean,"
                "temperature_2m_max,"
                "temperature_2m_min,"
                "precipitation_sum"
            ),
            "timezone": WEATHER_TIMEZONE,
            "start_date": pd.Timestamp(start_date).date().isoformat(),
            "end_date": pd.Timestamp(end_date).date().isoformat()
        }

        response = requests.get(
            url,
            params=params,
            timeout=30
        )
        response.raise_for_status()

        daily = response.json()["daily"]

        return pd.DataFrame({
            "date": pd.to_datetime(daily["time"]),
            "temperature_avg_c": daily["temperature_2m_mean"],
            "temp_max_c": daily["temperature_2m_max"],
            "temp_min_c": daily["temperature_2m_min"],
            "precipitation_mm": daily["precipitation_sum"]
        })

    # ========================================================
    # BUILD PRODUCTION FEATURES
    # ========================================================

    def build_selected_prophet_future_features(weather):
        weather = weather.copy()
        weather["date"] = pd.to_datetime(weather["date"])

        holiday_lookup = {}

        years = weather["date"].dt.year.unique()

        for year in years:
            holiday_lookup.update(
                get_nrw_public_holidays(int(year))
            )

        weather["holiday_name"] = weather["date"].map(
            holiday_lookup
        )

        weather["is_weekend"] = (
            weather["date"].dt.dayofweek >= 5
        ).astype(int)

        weather["is_holiday"] = (
            weather["date"].isin(holiday_lookup.keys())
        ).astype(int)

        weather["is_rainy"] = (
            weather["precipitation_mm"] >= RAIN_THRESHOLD_MM
        ).astype(int)

        promotion_dates = pd.to_datetime(
            PLANNED_PROMOTION_DATES
        )

        weather["is_promo_day"] = (
            weather["date"].isin(promotion_dates)
        ).astype(int)

        return weather[
            ["date"] + SELECTED_PROPHET_REGRESSORS
        ].copy()

    # ========================================================
    # FORECAST SETTINGS
    # ========================================================

    st.subheader("🔮 Forecast Settings")

    col1, col2 = st.columns(2)

    today = pd.Timestamp.now(tz=WEATHER_TIMEZONE).normalize().tz_localize(None)

    with col1:
        forecast_horizon = st.selectbox(
            "Forecast horizon",
            [7, 14],
            index=0
        )

    with col2:
        forecast_start = today + pd.Timedelta(days=1)
        st.metric(
            "Forecast starts",
            forecast_start.strftime("%d %b %Y")
        )

    st.divider()

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

    # ========================================================
    # OPERATIONAL FORECAST
    # ========================================================

    forecast_dates = pd.date_range(
        start=forecast_start,
        periods=forecast_horizon,
        freq="D"
    )

    try:
        future_weather = fetch_openmeteo_daily_weather(
            RESTAURANT_LATITUDE,
            RESTAURANT_LONGITUDE,
            forecast_dates.min(),
            forecast_dates.max()
        )

        future_features = build_selected_prophet_future_features(
            future_weather
        )

        prophet_future = (
            future_features
            .rename(columns={"date": "ds"})
            .copy()
        )

        # Verify that the future dataframe contains exactly the
        # regressors expected by the serialized Prophet model.
        model_regressors = list(
            production_model.extra_regressors.keys()
        )

        missing_regressors = [
            col for col in model_regressors
            if col not in prophet_future.columns
        ]

        if missing_regressors:
            raise ValueError(
                "Future forecast data is missing model regressors: "
                + ", ".join(missing_regressors)
            )

        forecast = production_model.predict(
            prophet_future[
                ["ds"] + model_regressors
            ]
        )

        future_forecast = pd.DataFrame({
            "date": pd.to_datetime(forecast["ds"]),
            "forecast_revenue": forecast["yhat"].clip(lower=0),
            "lower_bound": forecast["yhat_lower"].clip(lower=0),
            "upper_bound": forecast["yhat_upper"].clip(lower=0)
        })

        future_forecast = future_forecast.merge(
            future_features,
            on="date",
            how="left"
        )

    except Exception as e:
        st.error(
            "The operational forecast could not be generated."
        )
        st.exception(e)
        st.stop()

    # ========================================================
    # HISTORY GAP CHECK
    # ========================================================

    last_observed_date = df["date"].max()
    history_gap_days = (
        forecast_start - last_observed_date
    ).days - 1

    if history_gap_days > 0:
        st.warning(
            f"The historical revenue data ends on "
            f"{last_observed_date.date()}, while the operational "
            f"forecast starts on {forecast_start.date()}. "
            f"There are {history_gap_days} days without observed "
            f"revenue. The model can forecast mathematically, but "
            f"the dashboard should use updated operational revenue "
            f"data for a true live deployment."
        )

    # ========================================================
    # FORECAST QUALITY CHECK
    # ========================================================

    expected_rows = forecast_horizon
    actual_rows = len(future_forecast)
    missing_forecasts = future_forecast[
        "forecast_revenue"
    ].isna().sum()

    if actual_rows != expected_rows or missing_forecasts > 0:
        st.error(
            "Forecast quality check failed. "
            f"Expected {expected_rows} rows, got {actual_rows}; "
            f"missing forecasts: {missing_forecasts}."
        )
        st.stop()

    # ========================================================
    # FORECAST KPIs
    # ========================================================

    total_forecast = future_forecast[
        "forecast_revenue"
    ].sum()

    average_forecast = future_forecast[
        "forecast_revenue"
    ].mean()

    historical_daily_average = df["revenue"].mean()

    change_vs_historical = (
        (average_forecast / historical_daily_average) - 1
    ) * 100

    historical_aov = df["average_order_value"].mean()

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
        "Forecast model: **Prophet — Calendar + Weather**"
    )

    # ========================================================
    # MODEL INFORMATION
    # ========================================================

    with st.expander("Model configuration"):
        st.write(
            "The dashboard loads the serialized production model "
            "created in the revenue forecasting notebook."
        )

        model_info = {
            "Model": "Prophet — Calendar + Weather",
            "Weekly seasonality": "Enabled",
            "Yearly seasonality": "Disabled",
            "Daily seasonality": "Disabled",
            "Seasonality mode": "Additive",
            "Prediction interval": "80%",
            "Rain threshold": f"{RAIN_THRESHOLD_MM:.1f} mm",
            "Training start": model_metadata.get(
                "training_start", "Not available"
            ),
            "Training end": model_metadata.get(
                "training_end", "Not available"
            ),
            "Model file": str(MODEL_PATH)
        }

        st.dataframe(
            pd.DataFrame(
                model_info.items(),
                columns=["Setting", "Value"]
            ),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("**Production regressors**")
        st.write(", ".join(SELECTED_PROPHET_REGRESSORS))

    # ========================================================
    # FORECAST CHART
    # ========================================================

    st.subheader("📊 Operational Revenue Forecast")

    historical_recent = df[
        df["date"] >= (
            forecast_start - pd.Timedelta(days=60)
        )
    ][
        ["date", "revenue"]
    ].copy()

    historical_recent["Type"] = "Historical"

    forecast_plot = future_forecast[
        ["date", "forecast_revenue"]
    ].rename(
        columns={"forecast_revenue": "revenue"}
    )

    forecast_plot["Type"] = "Forecast"

    plot_df = pd.concat(
        [historical_recent, forecast_plot],
        ignore_index=True
    )

    fig = px.line(
        plot_df,
        x="date",
        y="revenue",
        color="Type",
        title=(
            "Historical Revenue + "
            f"{forecast_horizon}-Day Operational Forecast"
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
    # PREDICTION INTERVAL
    # ========================================================

    st.subheader("Forecast Uncertainty")

    interval_fig = px.line(
        future_forecast,
        x="date",
        y="forecast_revenue",
        title="Forecast Revenue with 80% Prediction Interval"
    )

    interval_fig.add_scatter(
        x=future_forecast["date"],
        y=future_forecast["upper_bound"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip"
    )

    interval_fig.add_scatter(
        x=future_forecast["date"],
        y=future_forecast["lower_bound"],
        mode="lines",
        fill="tonexty",
        line=dict(width=0),
        name="80% interval"
    )

    interval_fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Revenue (€)",
        hovermode="x unified"
    )

    st.plotly_chart(
        interval_fig,
        use_container_width=True
    )

    # ========================================================
    # DAILY FORECAST TABLE
    # ========================================================

    st.subheader("📅 Daily Operational Forecast")

    display_forecast = future_forecast[
        [
            "date",
            "temperature_avg_c",
            "precipitation_mm",
            "is_rainy",
            "is_holiday",
            "is_promo_day",
            "forecast_revenue",
            "lower_bound",
            "upper_bound"
        ]
    ].copy()

    display_forecast["Holiday"] = display_forecast[
        "is_holiday"
    ].map({
        0: "No",
        1: "Yes"
    })

    display_forecast["Promotion"] = display_forecast[
        "is_promo_day"
    ].map({
        0: "No",
        1: "Yes"
    })

    display_forecast["Rain"] = display_forecast[
        "is_rainy"
    ].map({
        0: "No",
        1: "Yes"
    })

    display_forecast = display_forecast.rename(
        columns={
            "date": "Date",
            "temperature_avg_c": "Temperature (°C)",
            "precipitation_mm": "Precipitation (mm)",
            "forecast_revenue": "Forecast Revenue (€)",
            "lower_bound": "Lower Bound (€)",
            "upper_bound": "Upper Bound (€)"
        }
    )

    display_forecast = display_forecast[
        [
            "Date",
            "Temperature (°C)",
            "Precipitation (mm)",
            "Rain",
            "Holiday",
            "Promotion",
            "Forecast Revenue (€)",
            "Lower Bound (€)",
            "Upper Bound (€)"
        ]
    ]

    st.dataframe(
        display_forecast.style.format({
            "Temperature (°C)": "{:.1f}",
            "Precipitation (mm)": "{:.1f}",
            "Forecast Revenue (€)": "€{:,.2f}",
            "Lower Bound (€)": "€{:,.2f}",
            "Upper Bound (€)": "€{:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # WEATHER AND CALENDAR CONTEXT
    # ========================================================

    st.subheader("🌦️ Forecast Context")

    context_col1, context_col2 = st.columns(2)

    with context_col1:
        rainy_days = int(
            future_forecast["is_rainy"].sum()
        )
        holiday_days = int(
            future_forecast["is_holiday"].sum()
        )

        st.metric("Rainy Days", rainy_days)
        st.metric("NRW Public Holidays", holiday_days)

    with context_col2:
        average_temperature = future_forecast[
            "temperature_avg_c"
        ].mean()
        total_precipitation = future_forecast[
            "precipitation_mm"
        ].sum()

        st.metric(
            "Average Temperature",
            f"{average_temperature:.1f} °C"
        )
        st.metric(
            "Total Precipitation",
            f"{total_precipitation:.1f} mm"
        )

    # ========================================================
    # MODEL VALIDATION RESULTS
    # ========================================================

    st.divider()
    st.subheader("🏆 Model Validation Results")

    model_results = pd.DataFrame({
        "Model": [
            "Prophet — Calendar + Weather",
            "Prophet — Weather + Calendar + Holiday + Promotion",
            "SARIMA — Weekly",
            "Prophet — Weekly Seasonality",
            "Prophet — Revenue + Calendar",
            "Gradient Boosting — Lag + Calendar",
            "Weekday Mean",
            "Random Forest — Weather + Calendar + Holiday + Promotion",
            "AR — 7 Lags",
            "Seasonal Naive"
        ],
        "MAE": [
            400.86,
            406.78,
            407.98,
            418.27,
            418.53,
            429.30,
            429.43,
            429.93,
            526.05,
            552.67
        ],
        "RMSE": [
            525.20,
            532.60,
            532.29,
            538.31,
            544.50,
            np.nan,
            559.83,
            np.nan,
            703.82,
            717.66
        ],
        "MAPE (%)": [
            14.85,
            15.26,
            14.87,
            14.94,
            14.96,
            np.nan,
            14.76,
            np.nan,
            18.65,
            19.76
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
        "Selected production model: **Prophet — Calendar + Weather** "
        "with rolling-validation MAE of **€400.86/day**."
    )

    st.info(
        "Weather information provides incremental predictive value, "
        "but the improvement cannot be attributed to rainfall alone. "
        "The selected model combines weather, calendar/business effects "
        "and weekly seasonality."
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