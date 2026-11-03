from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from dateutil.easter import easter
from prophet.serialize import model_from_json


# ============================================================
# APP SETUP AND PROJECT FILES
# ============================================================

st.set_page_config(
    page_title="RestroDine | Restaurant Intelligence",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data_clean"
MODEL_DIR = ROOT / "models"
OUTPUT_DIR = ROOT / "outputs"
MODEL_PATH = MODEL_DIR / "restrodine_prophet_calendar_weather.json"
METADATA_PATH = MODEL_DIR / "restrodine_prophet_calendar_weather_metadata.json"

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.7rem; padding-bottom: 2.5rem; max-width: 1500px;}
    [data-testid="stMetric"] {background: linear-gradient(135deg,#f7f8fc,#ffffff); border: 1px solid #e8ebf2; padding: 14px 16px; border-radius: 14px;}
    [data-testid="stMetricLabel"] {font-weight: 600;}
    .hero {padding: 1.2rem 1.4rem; border-radius: 18px; background: linear-gradient(115deg,#14213d,#2b5876); color: white; margin-bottom: 1rem;}
    .hero h1 {margin:0 0 .25rem 0; color:white;}
    .hero p {margin:0; opacity:.9; font-size:1rem;}
    .small-note {color:#667085; font-size:.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA AND MODEL LOADING
# ============================================================

@st.cache_data(show_spinner=False)
def read_csv(filename: str, date_columns: tuple[str, ...] = ()) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Required project file not found: {path}")
    frame = pd.read_csv(path)
    for column in date_columns:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


@st.cache_data(show_spinner=False)
def load_daily_history() -> pd.DataFrame:
    frame = read_csv("daily_model_table_clean.csv", ("date",))
    for column in ("revenue", "orders", "average_order_value"):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_model_metadata() -> dict:
    if not METADATA_PATH.exists():
        return {}
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


@st.cache_resource(show_spinner=False)
def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Production model is missing: {MODEL_PATH}")
    return model_from_json(MODEL_PATH.read_text(encoding="utf-8"))


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_weather(latitude: float, longitude: float, start: str, end: str) -> pd.DataFrame:
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "Europe/Berlin",
            "start_date": start,
            "end_date": end,
        },
        timeout=30,
    )
    response.raise_for_status()
    daily = response.json()["daily"]
    weather = pd.DataFrame({
        "date": pd.to_datetime(daily["time"]),
        "temperature_avg_c": daily["temperature_2m_mean"],
        "temp_max_c": daily["temperature_2m_max"],
        "temp_min_c": daily["temperature_2m_min"],
        "precipitation_mm": daily["precipitation_sum"],
    })
    weather["precipitation_mm"] = pd.to_numeric(weather["precipitation_mm"], errors="coerce").fillna(0)
    return weather


def nrw_holidays(year: int) -> dict[pd.Timestamp, str]:
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
        pd.Timestamp(year, 12, 26): "Boxing Day",
    }


def make_revenue_forecast(
    history: pd.DataFrame,
    model,
    metadata: dict,
    start: pd.Timestamp,
    horizon: int,
    promotion_dates: list[pd.Timestamp] | None = None,
) -> pd.DataFrame:
    end = start + pd.Timedelta(days=horizon - 1)
    location = metadata.get("location", {})
    latitude = float(location.get("latitude", 51.4324))
    longitude = float(location.get("longitude", 7.00435))
    weather = fetch_weather(latitude, longitude, start.date().isoformat(), end.date().isoformat())
    dates = pd.date_range(start, end, freq="D")
    if len(weather) != horizon or not weather["date"].dt.normalize().equals(dates):
        weather = weather.set_index("date").reindex(dates).rename_axis("date").reset_index()
    weather["precipitation_mm"] = weather["precipitation_mm"].fillna(0)

    holiday_lookup: dict[pd.Timestamp, str] = {}
    for year in weather["date"].dt.year.unique():
        holiday_lookup.update(nrw_holidays(int(year)))
    weather["is_weekend"] = (weather["date"].dt.dayofweek >= 5).astype(int)
    weather["is_holiday"] = weather["date"].isin(holiday_lookup).astype(int)
    rain_threshold = float(metadata.get("rain_threshold_mm", 1.0))
    weather["is_rainy"] = (weather["precipitation_mm"] >= rain_threshold).astype(int)
    promo_set = {pd.Timestamp(d).normalize() for d in (promotion_dates or [])}
    weather["is_promo_day"] = weather["date"].dt.normalize().isin(promo_set).astype(int)

    regressors = list(model.extra_regressors.keys())
    missing = [name for name in regressors if name not in weather.columns]
    if missing:
        raise ValueError("Forecast is missing model inputs: " + ", ".join(missing))
    predictions = model.predict(weather.rename(columns={"date": "ds"})[["ds"] + regressors])
    result = pd.DataFrame({
        "date": pd.to_datetime(predictions["ds"]),
        "forecast_revenue": predictions["yhat"].clip(lower=0),
        "lower_bound": predictions["yhat_lower"].clip(lower=0),
        "upper_bound": predictions["yhat_upper"].clip(lower=0),
    })
    return result.merge(weather, on="date", how="left")


# ============================================================
# WORKFORCE PLANNING — KEEP NOTEBOOK POLICY AND TERMS
# ============================================================

STAFFING_REQUIREMENTS = {
    "Low": [
        ("Restaurant Manager", "Full", 1), ("Chef", "Lunch", 1), ("Chef", "Dinner", 1),
        ("Kitchen Assistant", "Dinner", 1), ("Waiter", "Lunch", 2), ("Waiter", "Dinner", 2),
        ("Bartender", "Dinner", 1), ("Dishwasher", "Dinner", 1),
    ],
    "Standard": [
        ("Restaurant Manager", "Full", 1), ("Chef", "Lunch", 1), ("Chef", "Dinner", 2),
        ("Kitchen Assistant", "Lunch", 1), ("Kitchen Assistant", "Dinner", 1),
        ("Waiter", "Lunch", 2), ("Waiter", "Dinner", 3), ("Bartender", "Dinner", 1),
        ("Dishwasher", "Lunch", 1), ("Dishwasher", "Dinner", 1),
    ],
    "High": [
        ("Restaurant Manager", "Full", 1), ("Assistant Manager", "Dinner", 1),
        ("Chef", "Lunch", 1), ("Chef", "Dinner", 2), ("Kitchen Assistant", "Lunch", 1),
        ("Kitchen Assistant", "Dinner", 2), ("Waiter", "Lunch", 3), ("Waiter", "Dinner", 5),
        ("Bartender", "Dinner", 2), ("Dishwasher", "Lunch", 1), ("Dishwasher", "Dinner", 1),
    ],
    "Very High": [
        ("Restaurant Manager", "Full", 1), ("Assistant Manager", "Dinner", 1),
        ("Chef", "Lunch", 2), ("Chef", "Dinner", 2), ("Kitchen Assistant", "Lunch", 1),
        ("Kitchen Assistant", "Dinner", 2), ("Waiter", "Lunch", 4), ("Waiter", "Dinner", 6),
        ("Bartender", "Lunch", 1), ("Bartender", "Dinner", 2),
        ("Dishwasher", "Lunch", 1), ("Dishwasher", "Dinner", 2),
    ],
}
TIER_BOUNDS = [(60, "Low"), (101, "Standard"), (151, "High")]
SHIFT_DEFINITIONS = {
    "Lunch": {"start": "10:30", "end": "16:00", "hours": 5.5},
    "Dinner": {"start": "16:30", "end": "23:00", "hours": 6.5},
    "Full": {"start": "11:30", "end": "20:00", "hours": 8.0},
}
WEEKLY_HOUR_CAP = {"Full-time": 40.0, "Part-time": 30.0, "Minijob": 12.0}
MAX_DAILY_HOURS = 10.0


def demand_tier(orders: int) -> str:
    for bound, tier in TIER_BOUNDS:
        if orders < bound:
            return tier
    return "Very High"


def build_workforce_plan(
    revenue_forecast: pd.DataFrame,
    history: pd.DataFrame,
    employees: pd.DataFrame,
    availability: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Apply the notebook's median-AOV, demand tier and roster policy."""
    plan = revenue_forecast.copy()
    aov = (history["revenue"] / history["orders"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).median()
    if not np.isfinite(aov) or aov <= 0:
        raise ValueError("Could not calculate a valid historical median order value.")
    plan["expected_orders"] = (plan["forecast_revenue"] / aov).round().astype(int)
    plan["demand_tier"] = plan["expected_orders"].map(demand_tier)

    requirement_rows = []
    for row in plan.itertuples(index=False):
        for role, shift_type, count in STAFFING_REQUIREMENTS[row.demand_tier]:
            requirement_rows.append({
                "date": pd.Timestamp(row.date), "expected_orders": int(row.expected_orders),
                "demand_tier": row.demand_tier, "role": role, "shift_type": shift_type,
                "required": int(count),
            })
    requirements = pd.DataFrame(requirement_rows)

    staff = employees.copy()
    staff["employment_start"] = pd.to_datetime(staff["employment_start"], errors="coerce")
    staff["employment_end"] = pd.to_datetime(staff["employment_end"], errors="coerce")
    staff["hourly_cost"] = pd.to_numeric(staff["hourly_cost"], errors="coerce").fillna(0)
    staff["weekly_hour_cap"] = staff["employment_type"].map(WEEKLY_HOUR_CAP)
    # Project convention is Monday=1 through Sunday=7.
    availability_lookup = {
        (r.employee_id, int(r.day_of_week_num)): r
        for r in availability.itertuples(index=False)
    }
    weekly_hours: defaultdict[tuple, float] = defaultdict(float)
    daily_hours: defaultdict[tuple, float] = defaultdict(float)
    already_scheduled: set[tuple] = set()
    roster_rows, gap_rows = [], []

    for requirement in requirements.itertuples(index=False):
        day = pd.Timestamp(requirement.date).normalize()
        role_staff = staff[staff["role"] == requirement.role]
        shift = SHIFT_DEFINITIONS[requirement.shift_type]
        weekday_number = day.dayofweek + 1
        iso = day.isocalendar()
        candidates, reasons = [], defaultdict(int)
        for employee in role_staff.itertuples(index=False):
            employee_id = employee.employee_id
            day_key = (employee_id, day.date())
            week_key = (employee_id, int(iso.year), int(iso.week))
            avail = availability_lookup.get((employee_id, weekday_number))
            reason = None
            if pd.notna(employee.employment_start) and day < pd.Timestamp(employee.employment_start).normalize():
                reason = "not employed yet"
            elif pd.notna(employee.employment_end) and day > pd.Timestamp(employee.employment_end).normalize():
                reason = "employment ended"
            elif day_key in already_scheduled:
                reason = "already working that day"
            elif daily_hours[day_key] + shift["hours"] > MAX_DAILY_HOURS:
                reason = "daily hour cap reached"
            elif avail is None:
                reason = "availability record missing"
            elif avail.availability_status == "Unavailable":
                reason = "unavailable that weekday"
            elif float(avail.max_hours) < shift["hours"]:
                reason = "insufficient daily hours"
            elif weekly_hours[week_key] + shift["hours"] > float(employee.weekly_hour_cap or 0):
                reason = "weekly hour cap reached"
            if reason:
                reasons[reason] += 1
            else:
                candidates.append((employee, weekly_hours[week_key]))

        # Same selection rule as the notebook: assign employees with fewer hours this ISO week first.
        candidates.sort(key=lambda item: item[1])
        selected = candidates[: int(requirement.required)]
        for employee, _ in selected:
            employee_id = employee.employee_id
            day_key = (employee_id, day.date())
            week_key = (employee_id, int(iso.year), int(iso.week))
            weekly_hours[week_key] += shift["hours"]
            daily_hours[day_key] += shift["hours"]
            already_scheduled.add(day_key)
            roster_rows.append({
                "date": day, "role": requirement.role, "shift_type": requirement.shift_type,
                "employee_id": employee_id, "employee_name": employee.employee_name,
                "employment_type": employee.employment_type, "start_time": shift["start"],
                "end_time": shift["end"], "hours": shift["hours"],
                "hourly_cost": employee.hourly_cost,
                "labour_cost": shift["hours"] * employee.hourly_cost,
            })
        unfilled = int(requirement.required) - len(selected)
        if unfilled:
            reason_parts = []
            if role_staff.empty:
                reason_parts.append("no employees with this role")
            elif candidates:
                reason_parts.append(f"only {len(candidates)} eligible employee(s) for {requirement.required} required position(s)")
            reason_parts.extend(f"{reason} ({count} employee(s))" for reason, count in reasons.items())
            gap_rows.append({
                "date": day, "weekday": day.day_name(), "role": requirement.role,
                "shift_type": requirement.shift_type, "hours": shift["hours"],
                "required": int(requirement.required), "assigned": len(selected),
                "unfilled": unfilled, "reason": "; ".join(reason_parts),
            })

    roster = pd.DataFrame(roster_rows, columns=[
        "date", "role", "shift_type", "employee_id", "employee_name", "employment_type",
        "start_time", "end_time", "hours", "hourly_cost", "labour_cost",
    ])
    gaps = pd.DataFrame(gap_rows, columns=[
        "date", "weekday", "role", "shift_type", "hours", "required", "assigned", "unfilled", "reason",
    ])
    if roster.empty:
        assignments = pd.DataFrame(columns=["date", "role", "shift_type", "assigned"])
    else:
        assignments = roster.groupby(["date", "role", "shift_type"]).size().rename("assigned").reset_index()
    coverage = requirements.merge(assignments, on=["date", "role", "shift_type"], how="left")
    coverage["assigned"] = coverage["assigned"].fillna(0).astype(int)
    coverage["shortfall"] = coverage["required"] - coverage["assigned"]
    coverage["coverage_status"] = np.where(coverage["shortfall"] > 0, "Under-covered", "Covered")

    daily_required = requirements.groupby("date", as_index=False).agg(
        expected_orders=("expected_orders", "first"), demand_tier=("demand_tier", "first"), required_positions=("required", "sum")
    )
    if roster.empty:
        daily_assigned = pd.DataFrame(columns=["date", "scheduled_people", "labour_hours", "labour_cost"])
    else:
        daily_assigned = roster.groupby("date", as_index=False).agg(
            scheduled_people=("employee_id", "nunique"), labour_hours=("hours", "sum"), labour_cost=("labour_cost", "sum")
        )
    daily = plan.merge(daily_required, on=["date", "expected_orders", "demand_tier"], how="left")
    daily = daily.merge(daily_assigned, on="date", how="left")
    daily["scheduled_people"] = daily["scheduled_people"].fillna(0).astype(int)
    daily[["labour_hours", "labour_cost"]] = daily[["labour_hours", "labour_cost"]].fillna(0)
    daily["unfilled_positions"] = (daily["required_positions"] - daily["scheduled_people"]).clip(lower=0)
    # Position count is per shift; daily scheduled people may work at most once per day.
    gap_daily = gaps.groupby("date")["unfilled"].sum() if not gaps.empty else pd.Series(dtype=float)
    daily["unfilled_positions"] = daily["date"].map(gap_daily).fillna(0).astype(int)
    daily["labour_cost_pct_revenue"] = np.where(daily["forecast_revenue"] > 0, daily["labour_cost"] / daily["forecast_revenue"] * 100, 0)
    daily["orders_per_labour_hour"] = np.where(daily["labour_hours"] > 0, daily["expected_orders"] / daily["labour_hours"], np.nan)
    return {"plan": daily, "requirements": requirements, "roster": roster, "gaps": gaps, "coverage": coverage, "aov": pd.DataFrame({"median_aov": [aov]})}


def forecast_controls(prefix: str = "plan") -> tuple[pd.Timestamp, int, list[pd.Timestamp]]:
    tomorrow = pd.Timestamp.now(tz="Europe/Berlin").normalize().tz_localize(None) + pd.Timedelta(days=1)
    c1, c2 = st.columns([1, 1])
    with c1:
        start_date = pd.Timestamp(st.date_input("Forecast start date", value=tomorrow.date(), key=f"{prefix}_start"))
    with c2:
        horizon = st.selectbox("Planning horizon", [7, 14], index=0, key=f"{prefix}_horizon")
    promo_dates = st.date_input(
        "Planned promotion dates (optional)", value=(), key=f"{prefix}_promos",
        help="Selected dates are passed to the saved Prophet model as promotion days.",
    )
    if isinstance(promo_dates, date):
        promo_dates = [pd.Timestamp(promo_dates)]
    else:
        promo_dates = [pd.Timestamp(item) for item in (promo_dates or [])]
    return start_date, int(horizon), promo_dates


def show_revenue_forecast(history: pd.DataFrame, forecast: pd.DataFrame) -> None:
    recent = history.loc[history["date"] >= forecast["date"].min() - pd.Timedelta(days=60), ["date", "revenue"]].copy()
    recent["Series"] = "Historical"
    future = forecast[["date", "forecast_revenue"]].rename(columns={"forecast_revenue": "revenue"}).copy()
    future["Series"] = "Forecast"
    fig = px.line(pd.concat([recent, future], ignore_index=True), x="date", y="revenue", color="Series", markers=True)
    fig.add_trace(go.Scatter(x=forecast["date"], y=forecast["upper_bound"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=forecast["date"], y=forecast["lower_bound"], mode="lines", fill="tonexty", fillcolor="rgba(99,110,250,.14)", line=dict(width=0), name="80% prediction interval"))
    fig.update_layout(title="Recent revenue and operational forecast", xaxis_title=None, yaxis_title="Revenue (€)", hovermode="x unified", legend_title=None)
    st.plotly_chart(fig, use_container_width=True)


def money(value: float) -> str:
    return f"€{value:,.0f}"


# ============================================================
# APP SHELL
# ============================================================

st.sidebar.markdown("# 🍽️ RestroDine")
st.sidebar.caption("Restaurant Intelligence Platform")
st.sidebar.markdown("**Forecast demand → Plan staffing → Understand customers**")
page = st.sidebar.radio("Explore", ["Overview", "Revenue Forecast", "Workforce Plan", "Customer Insights"], label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption("Forecasts are planning recommendations. Review the roster and any coverage gaps before publishing.")

try:
    history = load_daily_history()
except Exception as error:
    st.error(f"Historical daily data could not be loaded: {error}")
    st.stop()


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================

if page == "Overview":
    st.markdown('<div class="hero"><h1>Restaurant intelligence, at a glance</h1><p>See the business clearly, then move from demand planning to a practical workforce recommendation.</p></div>', unsafe_allow_html=True)
    latest = history["date"].max()
    total_revenue = history["revenue"].sum()
    total_orders = history["orders"].sum()
    avg_order = total_revenue / total_orders if total_orders else 0
    first, last = history["date"].min(), history["date"].max()
    k = st.columns(4)
    k[0].metric("Historical revenue", money(total_revenue))
    k[1].metric("Orders recorded", f"{total_orders:,.0f}")
    k[2].metric("Revenue per order", f"€{avg_order:,.2f}")
    k[3].metric("Latest history date", latest.strftime("%d %b %Y"))
    st.caption(f"Historical coverage: {first:%d %b %Y} to {last:%d %b %Y} · {len(history):,} daily records")
    left, right = st.columns([1.7, 1])
    with left:
        st.subheader("Revenue over time")
        fig = px.area(history, x="date", y="revenue", labels={"date": "", "revenue": "Revenue (€)"})
        fig.update_traces(line_color="#2563eb", fillcolor="rgba(37,99,235,.15)")
        fig.update_layout(hovermode="x unified", margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Demand by weekday")
        weekday = history.assign(weekday=history["date"].dt.day_name()).groupby("weekday", as_index=False).agg(revenue=("revenue", "mean"), orders=("orders", "mean"))
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday["weekday"] = pd.Categorical(weekday["weekday"], weekday_order, ordered=True)
        weekday = weekday.sort_values("weekday")
        fig = px.bar(weekday, x="weekday", y="revenue", labels={"weekday": "", "revenue": "Average daily revenue (€)"}, color="revenue", color_continuous_scale="Blues")
        fig.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)
    st.info("Open **Revenue Forecast** to generate a live forecast, then **Workforce Plan** to convert forecast revenue into expected orders, required positions, a recommended roster and explained staffing gaps.")


# ============================================================
# REVENUE FORECAST
# ============================================================

elif page == "Revenue Forecast":
    st.markdown('<div class="hero"><h1>Revenue Forecast</h1><p>Weather-aware daily revenue estimates from the selected production Prophet model.</p></div>', unsafe_allow_html=True)
    try:
        model = load_model()
        metadata = load_model_metadata()
    except Exception as error:
        st.error(f"The production model could not be loaded. Check the files in {MODEL_DIR}: {error}")
        st.stop()
    start, horizon, promos = forecast_controls("revenue")
    with st.spinner("Preparing weather inputs and generating the revenue forecast…"):
        try:
            forecast = make_revenue_forecast(history, model, metadata, start, horizon, promos)
        except Exception as error:
            st.error(f"The live forecast could not be generated: {error}")
            st.caption("Check internet access, the production model files and their regressors, then reload this page.")
            st.stop()
    total = forecast["forecast_revenue"].sum()
    historical_aov = (history["revenue"] / history["orders"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).median()
    expected_orders = int((total / historical_aov).round())
    k = st.columns(4)
    k[0].metric("Forecast revenue", money(total))
    k[1].metric("Daily average", money(forecast["forecast_revenue"].mean()))
    k[2].metric("Expected orders", f"{expected_orders:,}", help="Revenue divided by the historical median average order value; this is an estimate.")
    k[3].metric("Planning window", f"{start:%d %b} – {forecast.date.max():%d %b}")
    show_revenue_forecast(history, forecast)
    st.subheader("Daily forecast and context")
    display = forecast[["date", "forecast_revenue", "lower_bound", "upper_bound", "temperature_avg_c", "precipitation_mm", "is_rainy", "is_holiday", "is_promo_day"]].copy()
    display = display.rename(columns={"date":"Date", "forecast_revenue":"Forecast (€)", "lower_bound":"Low estimate (€)", "upper_bound":"High estimate (€)", "temperature_avg_c":"Temperature (°C)", "precipitation_mm":"Rain (mm)", "is_rainy":"Rainy", "is_holiday":"Holiday", "is_promo_day":"Promotion"})
    st.dataframe(display.style.format({"Forecast (€)":"€{:,.0f}", "Low estimate (€)":"€{:,.0f}", "High estimate (€)":"€{:,.0f}", "Temperature (°C)":"{:.1f}", "Rain (mm)":"{:.1f}"}), use_container_width=True, hide_index=True)
    with st.expander("About this forecast"):
        st.write("The app loads the saved production Prophet model and prepares the same calendar and weather regressors recorded in its metadata. Expected orders are estimated from the historical median average order value.")
        st.caption(f"Model: {metadata.get('model', 'Prophet production model')} · training history: {metadata.get('training_start', '—')} to {metadata.get('training_end', '—')} · location: {metadata.get('location', {}).get('region', 'configured restaurant location')}")
    st.download_button("Download revenue forecast CSV", forecast.to_csv(index=False).encode("utf-8"), file_name="revenue_forecast.csv", mime="text/csv")


# ============================================================
# WORKFORCE PLAN
# ============================================================

elif page == "Workforce Plan":
    st.markdown('<div class="hero"><h1>Workforce Plan</h1><p>Translate forecast revenue into expected orders, staffing demand, a feasible suggested roster and transparent gaps.</p></div>', unsafe_allow_html=True)
    st.markdown("**Required** is the number of positions defined by the notebook’s demand tier policy. **Scheduled** is how many positions this roster builder can fill after checking role, employment dates, weekday availability, daily limits and weekly hour caps. Any remaining positions appear below with reasons.")
    try:
        model = load_model()
        metadata = load_model_metadata()
        employees = read_csv("employees_clean.csv", ("employment_start", "employment_end"))
        availability = read_csv("employee_availability_clean.csv")
    except Exception as error:
        st.error(f"Workforce planning inputs could not be loaded: {error}")
        st.stop()
    start, horizon, promos = forecast_controls("workforce")
    with st.spinner("Forecasting demand and building the roster…"):
        try:
            revenue = make_revenue_forecast(history, model, metadata, start, horizon, promos)
            result = build_workforce_plan(revenue, history, employees, availability)
        except Exception as error:
            st.error(f"The workforce plan could not be generated: {error}")
            st.caption("Confirm that model files and cleaned employee, availability and daily history files are present.")
            st.stop()
    daily, roster, gaps = result["plan"], result["roster"], result["gaps"]
    required_positions = int(result["requirements"]["required"].sum())
    filled_positions = len(roster)
    unfilled_positions = int(gaps["unfilled"].sum()) if not gaps.empty else 0
    k = st.columns(5)
    k[0].metric("Expected orders", f"{daily['expected_orders'].sum():,}")
    k[1].metric("Required positions", f"{required_positions:,}", help="Person-shifts from the staffing policy. A person can fill at most one shift per date.")
    k[2].metric("Scheduled positions", f"{filled_positions:,}")
    k[3].metric("Unfilled positions", f"{unfilled_positions:,}", delta="Needs manager review" if unfilled_positions else "All positions covered", delta_color="inverse" if unfilled_positions else "normal")
    k[4].metric("Estimated labour cost", money(daily["labour_cost"].sum()), help="Cost of positions actually assigned in this suggested roster.")
    cost_pct = daily["labour_cost"].sum() / daily["forecast_revenue"].sum() * 100 if daily["forecast_revenue"].sum() else 0
    st.caption(f"Forecast labour cost is {cost_pct:.1f}% of forecast revenue for this period. This is an estimate based on scheduled shifts and employee hourly costs.")

    st.subheader("Daily staffing coverage")
    coverage_plot = daily.melt(id_vars="date", value_vars=["required_positions", "scheduled_people"], var_name="Measure", value_name="People / positions")
    coverage_plot["Measure"] = coverage_plot["Measure"].map({"required_positions":"Required positions", "scheduled_people":"Scheduled employees"})
    fig = px.bar(coverage_plot, x="date", y="People / positions", color="Measure", barmode="group", color_discrete_map={"Required positions":"#a6adb8", "Scheduled employees":"#3182ce"}, labels={"date":"", "People / positions":"People / positions"})
    if unfilled_positions:
        fig.add_trace(go.Scatter(x=daily["date"], y=daily["required_positions"], mode="markers", marker=dict(size=8, color="#e4572e", symbol="x"), name="Unfilled positions are the gap", hovertemplate="%{x|%a %d %b}<br>Required: %{y}<extra></extra>"))
    fig.update_layout(hovermode="x unified", legend_title=None, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Required positions come from the forecast demand tier. Scheduled employees are unique people assigned for the day; one person can fill only one shift per calendar day.")

    date_values = pd.to_datetime(daily["date"]).dt.normalize().tolist()
    weeks = [date_values[i:i + 7] for i in range(0, len(date_values), 7)]
    week_labels = [f"Week {i + 1}: {days[0]:%d %b} – {days[-1]:%d %b}" for i, days in enumerate(weeks)]
    selected_week_idx = st.selectbox("Roster week", range(len(weeks)), format_func=lambda i: week_labels[i], key="roster_week")
    selected_dates = weeks[selected_week_idx]
    selected_week_roster = roster[roster["date"].isin(selected_dates)].copy()
    selected_week_gaps = gaps[gaps["date"].isin(selected_dates)].copy() if not gaps.empty else gaps.copy()

    st.subheader("Suggested weekly roster")
    st.caption("Shift times: Lunch 10:30–16:00 · Dinner 16:30–23:00 · Full 11:30–20:00. A blank cell means no shift is assigned that day.")
    if selected_week_roster.empty:
        st.info("No shifts were assigned in this week.")
    else:
        selected_week_roster["employee"] = selected_week_roster["role"] + " · " + selected_week_roster["employee_name"]
        selected_week_roster["shift"] = selected_week_roster.apply(lambda row: f"{row['shift_type']} {row['start_time']}–{row['end_time']}", axis=1)
        calendar = selected_week_roster.pivot_table(index=["role", "employee"], columns="date", values="shift", aggfunc="first", fill_value="")
        calendar = calendar.reindex(columns=pd.DatetimeIndex(selected_dates), fill_value="")
        calendar.columns = [d.strftime("%a %d %b") for d in calendar.columns]
        st.dataframe(calendar.reset_index(), use_container_width=True, hide_index=True, height=min(620, 42 + 38 * len(calendar)))
        st.download_button("Download this week’s roster", selected_week_roster.drop(columns=["employee", "shift"], errors="ignore").to_csv(index=False).encode("utf-8"), file_name=f"recommended_roster_week_{selected_week_idx + 1}.csv", mime="text/csv")

        st.subheader("Daily shift timeline")
        selected_day = st.selectbox("Choose a day", selected_dates, format_func=lambda d: d.strftime("%A, %d %B %Y"), key="roster_day")
        day_roster = selected_week_roster[selected_week_roster["date"].dt.normalize() == selected_day].copy()
        if not day_roster.empty:
            day_roster["employee_label"] = day_roster["role"] + " · " + day_roster["employee_name"]
            day_roster["start"] = pd.to_datetime(day_roster["date"].dt.strftime("%Y-%m-%d") + " " + day_roster["start_time"])
            day_roster["end"] = pd.to_datetime(day_roster["date"].dt.strftime("%Y-%m-%d") + " " + day_roster["end_time"])
            day_roster["shift_label"] = day_roster["shift_type"] + " · " + day_roster["start_time"] + "–" + day_roster["end_time"]
            fig = px.timeline(day_roster, x_start="start", x_end="end", y="employee_label", color="shift_type", text="shift_label", color_discrete_map={"Lunch":"#61a5c2", "Dinner":"#f4a261", "Full":"#7b6dca"}, hover_data={"role":True, "employee_name":True, "hours":True, "start":False, "end":False})
            fig.update_yaxes(autorange="reversed", title=None)
            fig.update_xaxes(tickformat="%H:%M", title="Shift time")
            fig.update_layout(height=max(360, 32 * len(day_roster)), legend_title=None, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No shifts are scheduled for this day.")

    st.subheader("Unfilled positions and reasons")
    if selected_week_gaps.empty:
        st.success("No uncovered positions in the selected week.")
    else:
        gaps_view = selected_week_gaps[["date", "weekday", "role", "shift_type", "hours", "required", "assigned", "unfilled", "reason"]].copy()
        gaps_view["date"] = gaps_view["date"].dt.strftime("%a %d %b")
        st.dataframe(gaps_view.rename(columns={"date":"Date", "weekday":"Weekday", "role":"Role", "shift_type":"Shift", "hours":"Hours", "required":"Required", "assigned":"Scheduled", "unfilled":"Unfilled", "reason":"Why it could not be filled"}), use_container_width=True, hide_index=True)
        st.download_button("Download gap details", gaps.to_csv(index=False).encode("utf-8"), file_name="staffing_gaps.csv", mime="text/csv")

    st.subheader("Period summary")
    summary = daily[["date", "forecast_revenue", "expected_orders", "demand_tier", "required_positions", "scheduled_people", "unfilled_positions", "labour_hours", "labour_cost", "labour_cost_pct_revenue"]].copy()
    summary = summary.rename(columns={"date":"Date", "forecast_revenue":"Forecast revenue (€)", "expected_orders":"Expected orders", "demand_tier":"Demand tier", "required_positions":"Required positions", "scheduled_people":"Scheduled employees", "unfilled_positions":"Unfilled positions", "labour_hours":"Labour hours", "labour_cost":"Labour cost (€)", "labour_cost_pct_revenue":"Labour cost / revenue (%)"})
    st.dataframe(summary.style.format({"Forecast revenue (€)":"€{:,.0f}", "Labour cost (€)":"€{:,.0f}", "Labour hours":"{:.1f}", "Labour cost / revenue (%)":"{:.1f}%"}), use_container_width=True, hide_index=True)
    st.download_button("Download workforce forecast", daily.to_csv(index=False).encode("utf-8"), file_name="workforce_forecast.csv", mime="text/csv")

    with st.expander("How this staffing forecast is calculated"):
        st.markdown(
            "1. Prophet forecasts revenue using the saved model and upcoming weather/calendar inputs.\n"
            "2. Revenue is divided by the historical **median** average order value to estimate orders.\n"
            "3. Notebook thresholds place those orders into Low (<60), Standard (60–100), High (101–150) or Very High (151+) demand.\n"
            "4. The notebook’s role-and-shift policy sets required positions. The roster builder assigns eligible staff with the fewest hours in the ISO week first, observing the one-shift-per-person-per-day rule and hour caps.\n"
            "5. Positions that cannot be assigned are listed with employee eligibility reasons. Availability uses Monday=1 through Sunday=7."
        )


# ============================================================
# CUSTOMER INSIGHTS — USE PROJECT REVIEW FILES
# ============================================================

elif page == "Customer Insights":
    st.markdown('<div class="hero"><h1>Customer Insights</h1><p>Explore review ratings and the topics customers mention, using the project’s cleaned review labels.</p></div>', unsafe_allow_html=True)
    try:
        reviews = read_csv("reviews_clean.csv", ("review_date",))
    except Exception as error:
        st.error(f"Review data could not be loaded: {error}")
        st.stop()
    reviews["rating"] = pd.to_numeric(reviews["rating"], errors="coerce")
    reviews = reviews.dropna(subset=["rating"])
    aspect_path = DATA_DIR / "review_aspect_labels_clean.csv"
    aspects = pd.read_csv(aspect_path) if aspect_path.exists() else pd.DataFrame(columns=["review_id", "aspect", "sentiment"])
    ratings = reviews["rating"]
    positive = int((ratings >= 4).sum())
    neutral = int((ratings == 3).sum())
    negative = int((ratings <= 2).sum())
    k = st.columns(4)
    k[0].metric("Reviews", f"{len(reviews):,}")
    k[1].metric("Average rating", f"{ratings.mean():.2f} / 5")
    k[2].metric("Positive ratings", f"{positive / len(reviews) * 100:.1f}%" if len(reviews) else "—")
    k[3].metric("Negative ratings", f"{negative / len(reviews) * 100:.1f}%" if len(reviews) else "—")
    left, right = st.columns(2)
    with left:
        st.subheader("Rating distribution")
        rating_counts = reviews.groupby("rating").size().reindex([1, 2, 3, 4, 5], fill_value=0).rename("Reviews").reset_index()
        fig = px.bar(rating_counts, x="rating", y="Reviews", color="rating", color_continuous_scale="RdYlGn", labels={"rating":"Rating (out of 5)"})
        fig.update_layout(showlegend=False, coloraxis_showscale=False, xaxis=dict(dtick=1), margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Ratings over time")
        monthly = reviews.dropna(subset=["review_date"]).assign(month=lambda x: x["review_date"].dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False).agg(average_rating=("rating", "mean"), review_count=("rating", "size"))
        fig = px.line(monthly, x="month", y="average_rating", markers=True, labels={"month":"", "average_rating":"Average rating"})
        fig.update_yaxes(range=[1, 5])
        fig.update_layout(margin=dict(t=20), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    if not aspects.empty and {"aspect", "sentiment"}.issubset(aspects.columns):
        st.subheader("What customers mention")
        sentiment_order = ["Negative", "Neutral", "Positive"]
        aspect_summary = aspects.groupby(["aspect", "sentiment"]).size().rename("Reviews").reset_index()
        fig = px.bar(aspect_summary, x="Reviews", y="aspect", color="sentiment", orientation="h", barmode="stack", category_orders={"sentiment":sentiment_order}, color_discrete_map={"Positive":"#2a9d8f", "Neutral":"#adb5bd", "Negative":"#e76f51"}, labels={"aspect":"", "sentiment":"Review tone"})
        fig.update_layout(yaxis={"categoryorder":"total ascending"}, legend_title=None, margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Aspect sentiment uses the project’s saved labels; this page does not infer new sentiment from review text.")
    else:
        st.info("Aspect-level review labels are not available yet. The rating charts above use the cleaned review records.")
    with st.expander("Review data coverage"):
        st.write(f"Review dates: {reviews['review_date'].min():%d %b %Y} to {reviews['review_date'].max():%d %b %Y}" if reviews["review_date"].notna().any() else "Review dates are unavailable.")
        st.write(f"Positive: {positive:,} · Neutral: {neutral:,} · Negative: {negative:,}")


# ============================================================
# FOOTER
# ============================================================

st.sidebar.caption("RestroDine")
