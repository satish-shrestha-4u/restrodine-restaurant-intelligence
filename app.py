# from __future__ import annotations

# import json
# from collections import defaultdict
# from datetime import date, timedelta
# from pathlib import Path

# import numpy as np
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# import requests
# import streamlit as st
# from dateutil.easter import easter
# from prophet.serialize import model_from_json


# # ============================================================
# # APP SETUP AND PROJECT FILES
# # ============================================================

# st.set_page_config(
#     page_title="RestroDine | Restaurant Intelligence",
#     page_icon="🍽️",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# ROOT = Path(__file__).resolve().parent
# DATA_DIR = ROOT / "data_clean"
# MODEL_DIR = ROOT / "models"
# OUTPUT_DIR = ROOT / "outputs"
# MODEL_PATH = MODEL_DIR / "restrodine_prophet_calendar_weather.json"
# METADATA_PATH = MODEL_DIR / "restrodine_prophet_calendar_weather_metadata.json"

# st.markdown(
#     """
#     <style>
#     .block-container {padding-top: 1.7rem; padding-bottom: 2.5rem; max-width: 1500px;}
#     [data-testid="stMetric"] {background: linear-gradient(135deg,#f7f8fc,#ffffff); border: 1px solid #e8ebf2; padding: 14px 16px; border-radius: 14px;}
#     [data-testid="stMetricLabel"] {font-weight: 600;}
#     .hero {padding: 1.2rem 1.4rem; border-radius: 18px; background: linear-gradient(115deg,#14213d,#2b5876); color: white; margin-bottom: 1rem;}
#     .hero h1 {margin:0 0 .25rem 0; color:white;}
#     .hero p {margin:0; opacity:.9; font-size:1rem;}
#     .small-note {color:#667085; font-size:.9rem;}
#     </style>
#     """,
#     unsafe_allow_html=True,
# )


# # ============================================================
# # DATA AND MODEL LOADING
# # ============================================================

# @st.cache_data(show_spinner=False)
# def read_csv(filename: str, date_columns: tuple[str, ...] = ()) -> pd.DataFrame:
#     path = DATA_DIR / filename
#     if not path.exists():
#         raise FileNotFoundError(f"Required project file not found: {path}")
#     frame = pd.read_csv(path)
#     for column in date_columns:
#         if column in frame:
#             frame[column] = pd.to_datetime(frame[column], errors="coerce")
#     return frame


# @st.cache_data(show_spinner=False)
# def load_daily_history() -> pd.DataFrame:
#     frame = read_csv("daily_model_table_clean.csv", ("date",))
#     for column in ("revenue", "orders", "average_order_value"):
#         if column in frame:
#             frame[column] = pd.to_numeric(frame[column], errors="coerce")
#     return frame.sort_values("date").reset_index(drop=True)


# @st.cache_data(show_spinner=False)
# def load_model_metadata() -> dict:
#     if not METADATA_PATH.exists():
#         return {}
#     return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


# @st.cache_resource(show_spinner=False)
# def load_model():
#     if not MODEL_PATH.exists():
#         raise FileNotFoundError(f"Production model is missing: {MODEL_PATH}")
#     return model_from_json(MODEL_PATH.read_text(encoding="utf-8"))


# @st.cache_data(ttl=3600, show_spinner=False)
# def fetch_weather(latitude: float, longitude: float, start: str, end: str) -> pd.DataFrame:
#     response = requests.get(
#         "https://api.open-meteo.com/v1/forecast",
#         params={
#             "latitude": latitude,
#             "longitude": longitude,
#             "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum",
#             "timezone": "Europe/Berlin",
#             "start_date": start,
#             "end_date": end,
#         },
#         timeout=30,
#     )
#     response.raise_for_status()
#     daily = response.json()["daily"]
#     weather = pd.DataFrame({
#         "date": pd.to_datetime(daily["time"]),
#         "temperature_avg_c": daily["temperature_2m_mean"],
#         "temp_max_c": daily["temperature_2m_max"],
#         "temp_min_c": daily["temperature_2m_min"],
#         "precipitation_mm": daily["precipitation_sum"],
#     })
#     weather["precipitation_mm"] = pd.to_numeric(weather["precipitation_mm"], errors="coerce").fillna(0)
#     return weather


# def nrw_holidays(year: int) -> dict[pd.Timestamp, str]:
#     easter_sunday = pd.Timestamp(easter(year))
#     return {
#         pd.Timestamp(year, 1, 1): "New Year's Day",
#         easter_sunday - pd.Timedelta(days=2): "Good Friday",
#         easter_sunday + pd.Timedelta(days=1): "Easter Monday",
#         easter_sunday + pd.Timedelta(days=39): "Ascension Day",
#         easter_sunday + pd.Timedelta(days=50): "Whit Monday",
#         easter_sunday + pd.Timedelta(days=60): "Corpus Christi",
#         pd.Timestamp(year, 5, 1): "Labour Day",
#         pd.Timestamp(year, 10, 3): "German Unity Day",
#         pd.Timestamp(year, 11, 1): "All Saints' Day",
#         pd.Timestamp(year, 12, 25): "Christmas Day",
#         pd.Timestamp(year, 12, 26): "Boxing Day",
#     }


# def make_revenue_forecast(
#     history: pd.DataFrame,
#     model,
#     metadata: dict,
#     start: pd.Timestamp,
#     horizon: int,
#     promotion_dates: list[pd.Timestamp] | None = None,
# ) -> pd.DataFrame:
#     end = start + pd.Timedelta(days=horizon - 1)
#     location = metadata.get("location", {})
#     latitude = float(location.get("latitude", 51.4324))
#     longitude = float(location.get("longitude", 7.00435))
#     weather = fetch_weather(latitude, longitude, start.date().isoformat(), end.date().isoformat())
#     dates = pd.date_range(start, end, freq="D")
#     if len(weather) != horizon or not weather["date"].dt.normalize().equals(dates):
#         weather = weather.set_index("date").reindex(dates).rename_axis("date").reset_index()
#     weather["precipitation_mm"] = weather["precipitation_mm"].fillna(0)

#     holiday_lookup: dict[pd.Timestamp, str] = {}
#     for year in weather["date"].dt.year.unique():
#         holiday_lookup.update(nrw_holidays(int(year)))
#     weather["is_weekend"] = (weather["date"].dt.dayofweek >= 5).astype(int)
#     weather["is_holiday"] = weather["date"].isin(holiday_lookup).astype(int)
#     rain_threshold = float(metadata.get("rain_threshold_mm", 1.0))
#     weather["is_rainy"] = (weather["precipitation_mm"] >= rain_threshold).astype(int)
#     promo_set = {pd.Timestamp(d).normalize() for d in (promotion_dates or [])}
#     weather["is_promo_day"] = weather["date"].dt.normalize().isin(promo_set).astype(int)

#     regressors = list(model.extra_regressors.keys())
#     missing = [name for name in regressors if name not in weather.columns]
#     if missing:
#         raise ValueError("Forecast is missing model inputs: " + ", ".join(missing))
#     predictions = model.predict(weather.rename(columns={"date": "ds"})[["ds"] + regressors])
#     result = pd.DataFrame({
#         "date": pd.to_datetime(predictions["ds"]),
#         "forecast_revenue": predictions["yhat"].clip(lower=0),
#         "lower_bound": predictions["yhat_lower"].clip(lower=0),
#         "upper_bound": predictions["yhat_upper"].clip(lower=0),
#     })
#     return result.merge(weather, on="date", how="left")


# # ============================================================
# # WORKFORCE PLANNING — KEEP NOTEBOOK POLICY AND TERMS
# # ============================================================

# STAFFING_REQUIREMENTS = {
#     "Low": [
#         ("Restaurant Manager", "Full", 1), ("Chef", "Lunch", 1), ("Chef", "Dinner", 1),
#         ("Kitchen Assistant", "Dinner", 1), ("Waiter", "Lunch", 2), ("Waiter", "Dinner", 2),
#         ("Bartender", "Dinner", 1), ("Dishwasher", "Dinner", 1),
#     ],
#     "Standard": [
#         ("Restaurant Manager", "Full", 1), ("Chef", "Lunch", 1), ("Chef", "Dinner", 2),
#         ("Kitchen Assistant", "Lunch", 1), ("Kitchen Assistant", "Dinner", 1),
#         ("Waiter", "Lunch", 2), ("Waiter", "Dinner", 3), ("Bartender", "Dinner", 1),
#         ("Dishwasher", "Lunch", 1), ("Dishwasher", "Dinner", 1),
#     ],
#     "High": [
#         ("Restaurant Manager", "Full", 1), ("Assistant Manager", "Dinner", 1),
#         ("Chef", "Lunch", 1), ("Chef", "Dinner", 2), ("Kitchen Assistant", "Lunch", 1),
#         ("Kitchen Assistant", "Dinner", 2), ("Waiter", "Lunch", 3), ("Waiter", "Dinner", 5),
#         ("Bartender", "Dinner", 2), ("Dishwasher", "Lunch", 1), ("Dishwasher", "Dinner", 1),
#     ],
#     "Very High": [
#         ("Restaurant Manager", "Full", 1), ("Assistant Manager", "Dinner", 1),
#         ("Chef", "Lunch", 2), ("Chef", "Dinner", 2), ("Kitchen Assistant", "Lunch", 1),
#         ("Kitchen Assistant", "Dinner", 2), ("Waiter", "Lunch", 4), ("Waiter", "Dinner", 6),
#         ("Bartender", "Lunch", 1), ("Bartender", "Dinner", 2),
#         ("Dishwasher", "Lunch", 1), ("Dishwasher", "Dinner", 2),
#     ],
# }
# TIER_BOUNDS = [(60, "Low"), (101, "Standard"), (151, "High")]
# SHIFT_DEFINITIONS = {
#     "Lunch": {"start": "10:30", "end": "16:00", "hours": 5.5},
#     "Dinner": {"start": "16:30", "end": "23:00", "hours": 6.5},
#     "Full": {"start": "11:30", "end": "20:00", "hours": 8.0},
# }
# WEEKLY_HOUR_CAP = {"Full-time": 40.0, "Part-time": 30.0, "Minijob": 12.0}
# MAX_DAILY_HOURS = 10.0


# def demand_tier(orders: int) -> str:
#     for bound, tier in TIER_BOUNDS:
#         if orders < bound:
#             return tier
#     return "Very High"


# def build_workforce_plan(
#     revenue_forecast: pd.DataFrame,
#     history: pd.DataFrame,
#     employees: pd.DataFrame,
#     availability: pd.DataFrame,
# ) -> dict[str, pd.DataFrame]:
#     """Apply the notebook's median-AOV, demand tier and roster policy."""
#     plan = revenue_forecast.copy()
#     aov = (history["revenue"] / history["orders"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).median()
#     if not np.isfinite(aov) or aov <= 0:
#         raise ValueError("Could not calculate a valid historical median order value.")
#     plan["expected_orders"] = (plan["forecast_revenue"] / aov).round().astype(int)
#     plan["demand_tier"] = plan["expected_orders"].map(demand_tier)

#     requirement_rows = []
#     for row in plan.itertuples(index=False):
#         for role, shift_type, count in STAFFING_REQUIREMENTS[row.demand_tier]:
#             requirement_rows.append({
#                 "date": pd.Timestamp(row.date), "expected_orders": int(row.expected_orders),
#                 "demand_tier": row.demand_tier, "role": role, "shift_type": shift_type,
#                 "required": int(count),
#             })
#     requirements = pd.DataFrame(requirement_rows)

#     staff = employees.copy()
#     staff["employment_start"] = pd.to_datetime(staff["employment_start"], errors="coerce")
#     staff["employment_end"] = pd.to_datetime(staff["employment_end"], errors="coerce")
#     staff["hourly_cost"] = pd.to_numeric(staff["hourly_cost"], errors="coerce").fillna(0)
#     staff["weekly_hour_cap"] = staff["employment_type"].map(WEEKLY_HOUR_CAP)
#     # Project convention is Monday=1 through Sunday=7.
#     availability_lookup = {
#         (r.employee_id, int(r.day_of_week_num)): r
#         for r in availability.itertuples(index=False)
#     }
#     weekly_hours: defaultdict[tuple, float] = defaultdict(float)
#     daily_hours: defaultdict[tuple, float] = defaultdict(float)
#     already_scheduled: set[tuple] = set()
#     roster_rows, gap_rows = [], []

#     for requirement in requirements.itertuples(index=False):
#         day = pd.Timestamp(requirement.date).normalize()
#         role_staff = staff[staff["role"] == requirement.role]
#         shift = SHIFT_DEFINITIONS[requirement.shift_type]
#         weekday_number = day.dayofweek + 1
#         iso = day.isocalendar()
#         candidates, reasons = [], defaultdict(int)
#         for employee in role_staff.itertuples(index=False):
#             employee_id = employee.employee_id
#             day_key = (employee_id, day.date())
#             week_key = (employee_id, int(iso.year), int(iso.week))
#             avail = availability_lookup.get((employee_id, weekday_number))
#             reason = None
#             if pd.notna(employee.employment_start) and day < pd.Timestamp(employee.employment_start).normalize():
#                 reason = "not employed yet"
#             elif pd.notna(employee.employment_end) and day > pd.Timestamp(employee.employment_end).normalize():
#                 reason = "employment ended"
#             elif day_key in already_scheduled:
#                 reason = "already working that day"
#             elif daily_hours[day_key] + shift["hours"] > MAX_DAILY_HOURS:
#                 reason = "daily hour cap reached"
#             elif avail is None:
#                 reason = "availability record missing"
#             elif avail.availability_status == "Unavailable":
#                 reason = "unavailable that weekday"
#             elif float(avail.max_hours) < shift["hours"]:
#                 reason = "insufficient daily hours"
#             elif weekly_hours[week_key] + shift["hours"] > float(employee.weekly_hour_cap or 0):
#                 reason = "weekly hour cap reached"
#             if reason:
#                 reasons[reason] += 1
#             else:
#                 candidates.append((employee, weekly_hours[week_key]))

#         # Same selection rule as the notebook: assign employees with fewer hours this ISO week first.
#         candidates.sort(key=lambda item: item[1])
#         selected = candidates[: int(requirement.required)]
#         for employee, _ in selected:
#             employee_id = employee.employee_id
#             day_key = (employee_id, day.date())
#             week_key = (employee_id, int(iso.year), int(iso.week))
#             weekly_hours[week_key] += shift["hours"]
#             daily_hours[day_key] += shift["hours"]
#             already_scheduled.add(day_key)
#             roster_rows.append({
#                 "date": day, "role": requirement.role, "shift_type": requirement.shift_type,
#                 "employee_id": employee_id, "employee_name": employee.employee_name,
#                 "employment_type": employee.employment_type, "start_time": shift["start"],
#                 "end_time": shift["end"], "hours": shift["hours"],
#                 "hourly_cost": employee.hourly_cost,
#                 "labour_cost": shift["hours"] * employee.hourly_cost,
#             })
#         unfilled = int(requirement.required) - len(selected)
#         if unfilled:
#             reason_parts = []
#             if role_staff.empty:
#                 reason_parts.append("no employees with this role")
#             elif candidates:
#                 reason_parts.append(f"only {len(candidates)} eligible employee(s) for {requirement.required} required position(s)")
#             reason_parts.extend(f"{reason} ({count} employee(s))" for reason, count in reasons.items())
#             gap_rows.append({
#                 "date": day, "weekday": day.day_name(), "role": requirement.role,
#                 "shift_type": requirement.shift_type, "hours": shift["hours"],
#                 "required": int(requirement.required), "assigned": len(selected),
#                 "unfilled": unfilled, "reason": "; ".join(reason_parts),
#             })

#     roster = pd.DataFrame(roster_rows, columns=[
#         "date", "role", "shift_type", "employee_id", "employee_name", "employment_type",
#         "start_time", "end_time", "hours", "hourly_cost", "labour_cost",
#     ])
#     gaps = pd.DataFrame(gap_rows, columns=[
#         "date", "weekday", "role", "shift_type", "hours", "required", "assigned", "unfilled", "reason",
#     ])
#     if roster.empty:
#         assignments = pd.DataFrame(columns=["date", "role", "shift_type", "assigned"])
#     else:
#         assignments = roster.groupby(["date", "role", "shift_type"]).size().rename("assigned").reset_index()
#     coverage = requirements.merge(assignments, on=["date", "role", "shift_type"], how="left")
#     coverage["assigned"] = coverage["assigned"].fillna(0).astype(int)
#     coverage["shortfall"] = coverage["required"] - coverage["assigned"]
#     coverage["coverage_status"] = np.where(coverage["shortfall"] > 0, "Under-covered", "Covered")

#     daily_required = requirements.groupby("date", as_index=False).agg(
#         expected_orders=("expected_orders", "first"), demand_tier=("demand_tier", "first"), required_positions=("required", "sum")
#     )
#     if roster.empty:
#         daily_assigned = pd.DataFrame(columns=["date", "scheduled_people", "labour_hours", "labour_cost"])
#     else:
#         daily_assigned = roster.groupby("date", as_index=False).agg(
#             scheduled_people=("employee_id", "nunique"), labour_hours=("hours", "sum"), labour_cost=("labour_cost", "sum")
#         )
#     daily = plan.merge(daily_required, on=["date", "expected_orders", "demand_tier"], how="left")
#     daily = daily.merge(daily_assigned, on="date", how="left")
#     daily["scheduled_people"] = daily["scheduled_people"].fillna(0).astype(int)
#     daily[["labour_hours", "labour_cost"]] = daily[["labour_hours", "labour_cost"]].fillna(0)
#     daily["unfilled_positions"] = (daily["required_positions"] - daily["scheduled_people"]).clip(lower=0)
#     # Position count is per shift; daily scheduled people may work at most once per day.
#     gap_daily = gaps.groupby("date")["unfilled"].sum() if not gaps.empty else pd.Series(dtype=float)
#     daily["unfilled_positions"] = daily["date"].map(gap_daily).fillna(0).astype(int)
#     daily["labour_cost_pct_revenue"] = np.where(daily["forecast_revenue"] > 0, daily["labour_cost"] / daily["forecast_revenue"] * 100, 0)
#     daily["orders_per_labour_hour"] = np.where(daily["labour_hours"] > 0, daily["expected_orders"] / daily["labour_hours"], np.nan)
#     return {"plan": daily, "requirements": requirements, "roster": roster, "gaps": gaps, "coverage": coverage, "aov": pd.DataFrame({"median_aov": [aov]})}


# def forecast_controls(prefix: str = "plan") -> tuple[pd.Timestamp, int, list[pd.Timestamp]]:
#     tomorrow = pd.Timestamp.now(tz="Europe/Berlin").normalize().tz_localize(None) + pd.Timedelta(days=1)
#     c1, c2 = st.columns([1, 1])
#     with c1:
#         start_date = pd.Timestamp(st.date_input("Forecast start date", value=tomorrow.date(), key=f"{prefix}_start"))
#     with c2:
#         horizon = st.selectbox("Planning horizon", [7, 14], index=0, key=f"{prefix}_horizon")
#     promo_dates = st.date_input(
#         "Planned promotion dates (optional)", value=(), key=f"{prefix}_promos",
#         help="Selected dates are passed to the saved Prophet model as promotion days.",
#     )
#     if isinstance(promo_dates, date):
#         promo_dates = [pd.Timestamp(promo_dates)]
#     else:
#         promo_dates = [pd.Timestamp(item) for item in (promo_dates or [])]
#     return start_date, int(horizon), promo_dates


# def show_revenue_forecast(history: pd.DataFrame, forecast: pd.DataFrame) -> None:
#     recent = history.loc[history["date"] >= forecast["date"].min() - pd.Timedelta(days=60), ["date", "revenue"]].copy()
#     recent["Series"] = "Historical"
#     future = forecast[["date", "forecast_revenue"]].rename(columns={"forecast_revenue": "revenue"}).copy()
#     future["Series"] = "Forecast"
#     fig = px.line(pd.concat([recent, future], ignore_index=True), x="date", y="revenue", color="Series", markers=True)
#     fig.add_trace(go.Scatter(x=forecast["date"], y=forecast["upper_bound"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
#     fig.add_trace(go.Scatter(x=forecast["date"], y=forecast["lower_bound"], mode="lines", fill="tonexty", fillcolor="rgba(99,110,250,.14)", line=dict(width=0), name="80% prediction interval"))
#     fig.update_layout(title="Recent revenue and operational forecast", xaxis_title=None, yaxis_title="Revenue (€)", hovermode="x unified", legend_title=None)
#     st.plotly_chart(fig, use_container_width=True)


# def money(value: float) -> str:
#     return f"€{value:,.0f}"


# # ============================================================
# # APP SHELL
# # ============================================================

# st.sidebar.markdown("# 🍽️ RestroDine")
# st.sidebar.caption("Restaurant Intelligence Platform")
# st.sidebar.markdown("**Forecast demand → Plan staffing → Understand customers**")
# page = st.sidebar.radio("Explore", ["Overview", "Revenue Forecast", "Workforce Plan", "Customer Insights"], label_visibility="collapsed")
# st.sidebar.divider()
# st.sidebar.caption("Forecasts are planning recommendations. Review the roster and any coverage gaps before publishing.")

# try:
#     history = load_daily_history()
# except Exception as error:
#     st.error(f"Historical daily data could not be loaded: {error}")
#     st.stop()


# # ============================================================
# # EXECUTIVE OVERVIEW
# # ============================================================

# if page == "Overview":
#     st.markdown('<div class="hero"><h1>Restaurant intelligence, at a glance</h1><p>See the business clearly, then move from demand planning to a practical workforce recommendation.</p></div>', unsafe_allow_html=True)
#     latest = history["date"].max()
#     total_revenue = history["revenue"].sum()
#     total_orders = history["orders"].sum()
#     avg_order = total_revenue / total_orders if total_orders else 0
#     first, last = history["date"].min(), history["date"].max()
#     k = st.columns(4)
#     k[0].metric("Historical revenue", money(total_revenue))
#     k[1].metric("Orders recorded", f"{total_orders:,.0f}")
#     k[2].metric("Revenue per order", f"€{avg_order:,.2f}")
#     k[3].metric("Latest history date", latest.strftime("%d %b %Y"))
#     st.caption(f"Historical coverage: {first:%d %b %Y} to {last:%d %b %Y} · {len(history):,} daily records")
#     left, right = st.columns([1.7, 1])
#     with left:
#         st.subheader("Revenue over time")
#         fig = px.area(history, x="date", y="revenue", labels={"date": "", "revenue": "Revenue (€)"})
#         fig.update_traces(line_color="#2563eb", fillcolor="rgba(37,99,235,.15)")
#         fig.update_layout(hovermode="x unified", margin=dict(t=20))
#         st.plotly_chart(fig, use_container_width=True)
#     with right:
#         st.subheader("Demand by weekday")
#         weekday = history.assign(weekday=history["date"].dt.day_name()).groupby("weekday", as_index=False).agg(revenue=("revenue", "mean"), orders=("orders", "mean"))
#         weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
#         weekday["weekday"] = pd.Categorical(weekday["weekday"], weekday_order, ordered=True)
#         weekday = weekday.sort_values("weekday")
#         fig = px.bar(weekday, x="weekday", y="revenue", labels={"weekday": "", "revenue": "Average daily revenue (€)"}, color="revenue", color_continuous_scale="Blues")
#         fig.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(t=20))
#         st.plotly_chart(fig, use_container_width=True)
#     st.info("Open **Revenue Forecast** to generate a live forecast, then **Workforce Plan** to convert forecast revenue into expected orders, required positions, a recommended roster and explained staffing gaps.")


# # ============================================================
# # REVENUE FORECAST
# # ============================================================

# elif page == "Revenue Forecast":
#     st.markdown('<div class="hero"><h1>Revenue Forecast</h1><p>Weather-aware daily revenue estimates from the selected production Prophet model.</p></div>', unsafe_allow_html=True)
#     try:
#         model = load_model()
#         metadata = load_model_metadata()
#     except Exception as error:
#         st.error(f"The production model could not be loaded. Check the files in {MODEL_DIR}: {error}")
#         st.stop()
#     start, horizon, promos = forecast_controls("revenue")
#     with st.spinner("Preparing weather inputs and generating the revenue forecast…"):
#         try:
#             forecast = make_revenue_forecast(history, model, metadata, start, horizon, promos)
#         except Exception as error:
#             st.error(f"The live forecast could not be generated: {error}")
#             st.caption("Check internet access, the production model files and their regressors, then reload this page.")
#             st.stop()
#     total = forecast["forecast_revenue"].sum()
#     historical_aov = (history["revenue"] / history["orders"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).median()
#     expected_orders = int((total / historical_aov).round())
#     k = st.columns(4)
#     k[0].metric("Forecast revenue", money(total))
#     k[1].metric("Daily average", money(forecast["forecast_revenue"].mean()))
#     k[2].metric("Expected orders", f"{expected_orders:,}", help="Revenue divided by the historical median average order value; this is an estimate.")
#     k[3].metric("Planning window", f"{start:%d %b} – {forecast.date.max():%d %b}")
#     show_revenue_forecast(history, forecast)
#     st.subheader("Daily forecast and context")
#     display = forecast[["date", "forecast_revenue", "lower_bound", "upper_bound", "temperature_avg_c", "precipitation_mm", "is_rainy", "is_holiday", "is_promo_day"]].copy()
#     display = display.rename(columns={"date":"Date", "forecast_revenue":"Forecast (€)", "lower_bound":"Low estimate (€)", "upper_bound":"High estimate (€)", "temperature_avg_c":"Temperature (°C)", "precipitation_mm":"Rain (mm)", "is_rainy":"Rainy", "is_holiday":"Holiday", "is_promo_day":"Promotion"})
#     st.dataframe(display.style.format({"Forecast (€)":"€{:,.0f}", "Low estimate (€)":"€{:,.0f}", "High estimate (€)":"€{:,.0f}", "Temperature (°C)":"{:.1f}", "Rain (mm)":"{:.1f}"}), use_container_width=True, hide_index=True)
#     with st.expander("About this forecast"):
#         st.write("The app loads the saved production Prophet model and prepares the same calendar and weather regressors recorded in its metadata. Expected orders are estimated from the historical median average order value.")
#         st.caption(f"Model: {metadata.get('model', 'Prophet production model')} · training history: {metadata.get('training_start', '—')} to {metadata.get('training_end', '—')} · location: {metadata.get('location', {}).get('region', 'configured restaurant location')}")
#     st.download_button("Download revenue forecast CSV", forecast.to_csv(index=False).encode("utf-8"), file_name="revenue_forecast.csv", mime="text/csv")


# # ============================================================
# # WORKFORCE PLAN
# # ============================================================

# elif page == "Workforce Plan":
#     st.markdown('<div class="hero"><h1>Workforce Plan</h1><p>Translate forecast revenue into expected orders, staffing demand, a feasible suggested roster and transparent gaps.</p></div>', unsafe_allow_html=True)
#     st.markdown("**Required** is the number of positions defined by the notebook’s demand tier policy. **Scheduled** is how many positions this roster builder can fill after checking role, employment dates, weekday availability, daily limits and weekly hour caps. Any remaining positions appear below with reasons.")
#     try:
#         model = load_model()
#         metadata = load_model_metadata()
#         employees = read_csv("employees_clean.csv", ("employment_start", "employment_end"))
#         availability = read_csv("employee_availability_clean.csv")
#     except Exception as error:
#         st.error(f"Workforce planning inputs could not be loaded: {error}")
#         st.stop()
#     start, horizon, promos = forecast_controls("workforce")
#     with st.spinner("Forecasting demand and building the roster…"):
#         try:
#             revenue = make_revenue_forecast(history, model, metadata, start, horizon, promos)
#             result = build_workforce_plan(revenue, history, employees, availability)
#         except Exception as error:
#             st.error(f"The workforce plan could not be generated: {error}")
#             st.caption("Confirm that model files and cleaned employee, availability and daily history files are present.")
#             st.stop()
#     daily, roster, gaps = result["plan"], result["roster"], result["gaps"]
#     required_positions = int(result["requirements"]["required"].sum())
#     filled_positions = len(roster)
#     unfilled_positions = int(gaps["unfilled"].sum()) if not gaps.empty else 0
#     k = st.columns(5)
#     k[0].metric("Expected orders", f"{daily['expected_orders'].sum():,}")
#     k[1].metric("Required positions", f"{required_positions:,}", help="Person-shifts from the staffing policy. A person can fill at most one shift per date.")
#     k[2].metric("Scheduled positions", f"{filled_positions:,}")
#     k[3].metric("Unfilled positions", f"{unfilled_positions:,}", delta="Needs manager review" if unfilled_positions else "All positions covered", delta_color="inverse" if unfilled_positions else "normal")
#     k[4].metric("Estimated labour cost", money(daily["labour_cost"].sum()), help="Cost of positions actually assigned in this suggested roster.")
#     cost_pct = daily["labour_cost"].sum() / daily["forecast_revenue"].sum() * 100 if daily["forecast_revenue"].sum() else 0
#     st.caption(f"Forecast labour cost is {cost_pct:.1f}% of forecast revenue for this period. This is an estimate based on scheduled shifts and employee hourly costs.")

#     st.subheader("Daily staffing coverage")
#     coverage_plot = daily.melt(id_vars="date", value_vars=["required_positions", "scheduled_people"], var_name="Measure", value_name="People / positions")
#     coverage_plot["Measure"] = coverage_plot["Measure"].map({"required_positions":"Required positions", "scheduled_people":"Scheduled employees"})
#     fig = px.bar(coverage_plot, x="date", y="People / positions", color="Measure", barmode="group", color_discrete_map={"Required positions":"#a6adb8", "Scheduled employees":"#3182ce"}, labels={"date":"", "People / positions":"People / positions"})
#     if unfilled_positions:
#         fig.add_trace(go.Scatter(x=daily["date"], y=daily["required_positions"], mode="markers", marker=dict(size=8, color="#e4572e", symbol="x"), name="Unfilled positions are the gap", hovertemplate="%{x|%a %d %b}<br>Required: %{y}<extra></extra>"))
#     fig.update_layout(hovermode="x unified", legend_title=None, margin=dict(t=20))
#     st.plotly_chart(fig, use_container_width=True)
#     st.caption("Required positions come from the forecast demand tier. Scheduled employees are unique people assigned for the day; one person can fill only one shift per calendar day.")

#     date_values = pd.to_datetime(daily["date"]).dt.normalize().tolist()
#     weeks = [date_values[i:i + 7] for i in range(0, len(date_values), 7)]
#     week_labels = [f"Week {i + 1}: {days[0]:%d %b} – {days[-1]:%d %b}" for i, days in enumerate(weeks)]
#     selected_week_idx = st.selectbox("Roster week", range(len(weeks)), format_func=lambda i: week_labels[i], key="roster_week")
#     selected_dates = weeks[selected_week_idx]
#     selected_week_roster = roster[roster["date"].isin(selected_dates)].copy()
#     selected_week_gaps = gaps[gaps["date"].isin(selected_dates)].copy() if not gaps.empty else gaps.copy()

#     st.subheader("Suggested weekly roster")
#     st.caption("Shift times: Lunch 10:30–16:00 · Dinner 16:30–23:00 · Full 11:30–20:00. A blank cell means no shift is assigned that day.")
#     if selected_week_roster.empty:
#         st.info("No shifts were assigned in this week.")
#     else:
#         selected_week_roster["employee"] = selected_week_roster["role"] + " · " + selected_week_roster["employee_name"]
#         selected_week_roster["shift"] = selected_week_roster.apply(lambda row: f"{row['shift_type']} {row['start_time']}–{row['end_time']}", axis=1)
#         calendar = selected_week_roster.pivot_table(index=["role", "employee"], columns="date", values="shift", aggfunc="first", fill_value="")
#         calendar = calendar.reindex(columns=pd.DatetimeIndex(selected_dates), fill_value="")
#         calendar.columns = [d.strftime("%a %d %b") for d in calendar.columns]
#         st.dataframe(calendar.reset_index(), use_container_width=True, hide_index=True, height=min(620, 42 + 38 * len(calendar)))
#         st.download_button("Download this week’s roster", selected_week_roster.drop(columns=["employee", "shift"], errors="ignore").to_csv(index=False).encode("utf-8"), file_name=f"recommended_roster_week_{selected_week_idx + 1}.csv", mime="text/csv")

#         st.subheader("Daily shift timeline")
#         selected_day = st.selectbox("Choose a day", selected_dates, format_func=lambda d: d.strftime("%A, %d %B %Y"), key="roster_day")
#         day_roster = selected_week_roster[selected_week_roster["date"].dt.normalize() == selected_day].copy()
#         if not day_roster.empty:
#             day_roster["employee_label"] = day_roster["role"] + " · " + day_roster["employee_name"]
#             day_roster["start"] = pd.to_datetime(day_roster["date"].dt.strftime("%Y-%m-%d") + " " + day_roster["start_time"])
#             day_roster["end"] = pd.to_datetime(day_roster["date"].dt.strftime("%Y-%m-%d") + " " + day_roster["end_time"])
#             day_roster["shift_label"] = day_roster["shift_type"] + " · " + day_roster["start_time"] + "–" + day_roster["end_time"]
#             fig = px.timeline(day_roster, x_start="start", x_end="end", y="employee_label", color="shift_type", text="shift_label", color_discrete_map={"Lunch":"#61a5c2", "Dinner":"#f4a261", "Full":"#7b6dca"}, hover_data={"role":True, "employee_name":True, "hours":True, "start":False, "end":False})
#             fig.update_yaxes(autorange="reversed", title=None)
#             fig.update_xaxes(tickformat="%H:%M", title="Shift time")
#             fig.update_layout(height=max(360, 32 * len(day_roster)), legend_title=None, margin=dict(l=10, r=10, t=20, b=10))
#             st.plotly_chart(fig, use_container_width=True)
#         else:
#             st.info("No shifts are scheduled for this day.")

#     st.subheader("Unfilled positions and reasons")
#     if selected_week_gaps.empty:
#         st.success("No uncovered positions in the selected week.")
#     else:
#         gaps_view = selected_week_gaps[["date", "weekday", "role", "shift_type", "hours", "required", "assigned", "unfilled", "reason"]].copy()
#         gaps_view["date"] = gaps_view["date"].dt.strftime("%a %d %b")
#         st.dataframe(gaps_view.rename(columns={"date":"Date", "weekday":"Weekday", "role":"Role", "shift_type":"Shift", "hours":"Hours", "required":"Required", "assigned":"Scheduled", "unfilled":"Unfilled", "reason":"Why it could not be filled"}), use_container_width=True, hide_index=True)
#         st.download_button("Download gap details", gaps.to_csv(index=False).encode("utf-8"), file_name="staffing_gaps.csv", mime="text/csv")

#     st.subheader("Period summary")
#     summary = daily[["date", "forecast_revenue", "expected_orders", "demand_tier", "required_positions", "scheduled_people", "unfilled_positions", "labour_hours", "labour_cost", "labour_cost_pct_revenue"]].copy()
#     summary = summary.rename(columns={"date":"Date", "forecast_revenue":"Forecast revenue (€)", "expected_orders":"Expected orders", "demand_tier":"Demand tier", "required_positions":"Required positions", "scheduled_people":"Scheduled employees", "unfilled_positions":"Unfilled positions", "labour_hours":"Labour hours", "labour_cost":"Labour cost (€)", "labour_cost_pct_revenue":"Labour cost / revenue (%)"})
#     st.dataframe(summary.style.format({"Forecast revenue (€)":"€{:,.0f}", "Labour cost (€)":"€{:,.0f}", "Labour hours":"{:.1f}", "Labour cost / revenue (%)":"{:.1f}%"}), use_container_width=True, hide_index=True)
#     st.download_button("Download workforce forecast", daily.to_csv(index=False).encode("utf-8"), file_name="workforce_forecast.csv", mime="text/csv")

#     with st.expander("How this staffing forecast is calculated"):
#         st.markdown(
#             "1. Prophet forecasts revenue using the saved model and upcoming weather/calendar inputs.\n"
#             "2. Revenue is divided by the historical **median** average order value to estimate orders.\n"
#             "3. Notebook thresholds place those orders into Low (<60), Standard (60–100), High (101–150) or Very High (151+) demand.\n"
#             "4. The notebook’s role-and-shift policy sets required positions. The roster builder assigns eligible staff with the fewest hours in the ISO week first, observing the one-shift-per-person-per-day rule and hour caps.\n"
#             "5. Positions that cannot be assigned are listed with employee eligibility reasons. Availability uses Monday=1 through Sunday=7."
#         )


# # ============================================================
# # CUSTOMER INSIGHTS — USE PROJECT REVIEW FILES
# # ============================================================

# elif page == "Customer Insights":
#     st.markdown('<div class="hero"><h1>Customer Insights</h1><p>Explore review ratings and the topics customers mention, using the project’s cleaned review labels.</p></div>', unsafe_allow_html=True)
#     try:
#         reviews = read_csv("reviews_clean.csv", ("review_date",))
#     except Exception as error:
#         st.error(f"Review data could not be loaded: {error}")
#         st.stop()
#     reviews["rating"] = pd.to_numeric(reviews["rating"], errors="coerce")
#     reviews = reviews.dropna(subset=["rating"])
#     aspect_path = DATA_DIR / "review_aspect_labels_clean.csv"
#     aspects = pd.read_csv(aspect_path) if aspect_path.exists() else pd.DataFrame(columns=["review_id", "aspect", "sentiment"])
#     ratings = reviews["rating"]
#     positive = int((ratings >= 4).sum())
#     neutral = int((ratings == 3).sum())
#     negative = int((ratings <= 2).sum())
#     k = st.columns(4)
#     k[0].metric("Reviews", f"{len(reviews):,}")
#     k[1].metric("Average rating", f"{ratings.mean():.2f} / 5")
#     k[2].metric("Positive ratings", f"{positive / len(reviews) * 100:.1f}%" if len(reviews) else "—")
#     k[3].metric("Negative ratings", f"{negative / len(reviews) * 100:.1f}%" if len(reviews) else "—")
#     left, right = st.columns(2)
#     with left:
#         st.subheader("Rating distribution")
#         rating_counts = reviews.groupby("rating").size().reindex([1, 2, 3, 4, 5], fill_value=0).rename("Reviews").reset_index()
#         fig = px.bar(rating_counts, x="rating", y="Reviews", color="rating", color_continuous_scale="RdYlGn", labels={"rating":"Rating (out of 5)"})
#         fig.update_layout(showlegend=False, coloraxis_showscale=False, xaxis=dict(dtick=1), margin=dict(t=20))
#         st.plotly_chart(fig, use_container_width=True)
#     with right:
#         st.subheader("Ratings over time")
#         monthly = reviews.dropna(subset=["review_date"]).assign(month=lambda x: x["review_date"].dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False).agg(average_rating=("rating", "mean"), review_count=("rating", "size"))
#         fig = px.line(monthly, x="month", y="average_rating", markers=True, labels={"month":"", "average_rating":"Average rating"})
#         fig.update_yaxes(range=[1, 5])
#         fig.update_layout(margin=dict(t=20), hovermode="x unified")
#         st.plotly_chart(fig, use_container_width=True)
#     if not aspects.empty and {"aspect", "sentiment"}.issubset(aspects.columns):
#         st.subheader("What customers mention")
#         sentiment_order = ["Negative", "Neutral", "Positive"]
#         aspect_summary = aspects.groupby(["aspect", "sentiment"]).size().rename("Reviews").reset_index()
#         fig = px.bar(aspect_summary, x="Reviews", y="aspect", color="sentiment", orientation="h", barmode="stack", category_orders={"sentiment":sentiment_order}, color_discrete_map={"Positive":"#2a9d8f", "Neutral":"#adb5bd", "Negative":"#e76f51"}, labels={"aspect":"", "sentiment":"Review tone"})
#         fig.update_layout(yaxis={"categoryorder":"total ascending"}, legend_title=None, margin=dict(t=20))
#         st.plotly_chart(fig, use_container_width=True)
#         st.caption("Aspect sentiment uses the project’s saved labels; this page does not infer new sentiment from review text.")
#     else:
#         st.info("Aspect-level review labels are not available yet. The rating charts above use the cleaned review records.")
#     with st.expander("Review data coverage"):
#         st.write(f"Review dates: {reviews['review_date'].min():%d %b %Y} to {reviews['review_date'].max():%d %b %Y}" if reviews["review_date"].notna().any() else "Review dates are unavailable.")
#         st.write(f"Positive: {positive:,} · Neutral: {neutral:,} · Negative: {negative:,}")


# # ============================================================
# # FOOTER
# # ============================================================

# st.sidebar.caption("RestroDine")





# """RestroDine - decision-support app (Streamlit).

# Run from the project root:   streamlit run app.py
# The app only READS files produced by the notebooks - no model training happens here:
#   data_clean/daily_model_table_clean.csv                 (notebook 01/02)
#   outputs/revenue_forecast_next_14_days.csv              (notebook 02)
#   outputs/workforce_forecast_next_*_days.csv, recommended_roster.csv,
#   outputs/staffing_coverage.csv, outputs/staffing_gaps.csv   (notebook 03 workforce)
# Optional (menu / customer pages): products, order_items, reviews CSVs in data_clean/ or data/.
# """
# import json
# from pathlib import Path

# import numpy as np
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# import streamlit as st

# st.set_page_config(page_title="RestroDine", page_icon="🍽️", layout="wide")

# HERE = Path(__file__).resolve().parent
# ROOT = HERE.parent if HERE.name == "app" else HERE
# OUT, MODELS = ROOT / "outputs", ROOT / "models"
# DATA_DIRS = [ROOT / "data_clean", ROOT / "data", ROOT / "data" / "raw"]
# ROLE_ORDER = ["Restaurant Manager", "Assistant Manager", "Chef", "Bartender", "Kitchen Assistant", "Waiter", "Dishwasher"]
# TIER_COLORS = {"Low": "#9ecae1", "Standard": "#6baed6", "High": "#3182bd", "Very High": "#08519c"}


# # ------------------------------------------------------------------ loading helpers
# @st.cache_data(show_spinner=False)
# def _read(path, parse_dates=None):
#     return pd.read_csv(path, parse_dates=parse_dates)


# def load(names, folders=None, parse_dates=None):
#     """First existing CSV among `names` in `folders`; None if nothing is found."""
#     names = [names] if isinstance(names, str) else names
#     for folder in (folders or DATA_DIRS):
#         for n in names:
#             p = Path(folder) / f"{n}.csv"
#             if p.exists():
#                 return _read(str(p), parse_dates)
#     return None


# def latest(pattern):
#     files = sorted(OUT.glob(pattern), key=lambda p: p.stat().st_mtime)
#     return _read(str(files[-1]), ["date"]) if files else None


# def need(df, what, how):
#     if df is None:
#         st.warning(f"**{what}** not found. {how}")
#         st.stop()
#     return df


# hist = load(["daily_model_table_clean", "daily_model"], parse_dates=["date"])
# rev_fc = load("revenue_forecast_next_14_days", [OUT], ["date"])
# wf = latest("workforce_forecast_next_*_days.csv")
# roster = load("recommended_roster", [OUT], ["date"])
# coverage = load("staffing_coverage", [OUT], ["date"])
# gaps = load("staffing_gaps", [OUT], ["date"])


# def eur(x):
#     return f"€{x:,.0f}"


# # ------------------------------------------------------------------ pages
# def page_dashboard():
#     st.title("🍽️ RestroDine - Dashboard")
#     hist_ = need(hist, "Historical daily table", "Run notebook 01/02 first (data_clean/daily_model_table_clean.csv).")
#     last28 = hist_.sort_values("date").tail(28)
#     c = st.columns(4)
#     c[0].metric("Revenue, last 28 days of history", eur(last28.revenue.sum()))
#     c[1].metric("Avg orders / day", f"{last28.orders.mean():.0f}")
#     c[2].metric("Avg order value", f"€{last28.revenue.sum() / last28.orders.sum():.2f}")
#     if rev_fc is not None:
#         c[3].metric(f"Forecast revenue, next {len(rev_fc)} days", eur(rev_fc.forecast_revenue.sum()))
#         gap_days = (rev_fc.date.min() - hist_.date.max()).days - 1
#         if gap_days > 7:
#             st.info(f"History ends {hist_.date.max().date()}, but the forecast starts {rev_fc.date.min().date()} "
#                     f"({gap_days} days later). The simulation step will close this gap; until then the forecast demonstrates the pipeline.")
#     if wf is not None:
#         w = st.columns(4)
#         w[0].metric("Planned labour cost", eur(wf.labour_cost.sum()))
#         pct = wf.labour_cost.sum() / wf.forecast_revenue.sum() * 100
#         w[1].metric("Labour cost % of revenue", f"{pct:.1f}%")
#         short = int(coverage.shortfall.sum()) if coverage is not None else 0
#         w[2].metric("Unfilled positions", short)
#         w[3].metric("Busiest day", f"{wf.loc[wf.expected_orders.idxmax(), 'date']:%a %d.%m}")
#     fig = go.Figure()
#     h = hist_.sort_values("date").tail(60)
#     fig.add_trace(go.Scatter(x=h.date, y=h.revenue, name="observed revenue", line=dict(color="#2b7bba")))
#     if rev_fc is not None:
#         fig.add_trace(go.Scatter(x=rev_fc.date, y=rev_fc.upper_bound, line=dict(width=0), showlegend=False, hoverinfo="skip"))
#         fig.add_trace(go.Scatter(x=rev_fc.date, y=rev_fc.lower_bound, fill="tonexty", fillcolor="rgba(231,76,60,.2)", line=dict(width=0), name="80% interval"))
#         fig.add_trace(go.Scatter(x=rev_fc.date, y=rev_fc.forecast_revenue, name="forecast", line=dict(color="#e74c3c", dash="dash")))
#     fig.update_layout(title="Revenue: last 60 days and forecast", yaxis_title="EUR", height=380, margin=dict(t=50, b=10))
#     st.plotly_chart(fig)

#     st.subheader("Alerts")
#     alerts = []
#     if coverage is not None:
#         s = coverage[coverage.shortfall > 0].groupby("date").shortfall.sum()
#         for d, n in s.items():
#             alerts.append(f"🔴 **{d:%a %d.%m}**: {int(n)} required position(s) cannot be filled")
#     if wf is not None:
#         for _, r in wf[(wf.labour_cost / wf.forecast_revenue) > 0.55].iterrows():
#             alerts.append(f"🟠 **{r.date:%a %d.%m}**: labour cost is {r.labour_cost / r.forecast_revenue * 100:.0f}% of forecast revenue")
#         for _, r in wf[wf.demand_tier.isin(["High", "Very High"])].iterrows():
#             alerts.append(f"🔵 **{r.date:%a %d.%m}**: {r.demand_tier} demand expected ({r.expected_orders:.0f} orders)")
#     if alerts:
#         for a in alerts[:14]:
#             st.markdown(a)
#     else:
#         st.success("No alerts for the planning window.")


# def page_revenue():
#     st.title("📈 Revenue forecast")
#     fc = need(rev_fc, "Revenue forecast", "Run notebook 02 until it saves outputs/revenue_forecast_next_14_days.csv.")
#     fig = go.Figure()
#     fig.add_trace(go.Bar(x=fc.date, y=fc.forecast_revenue, name="forecast", marker_color="#e74c3c",
#                          error_y=dict(type="data", symmetric=False, array=fc.upper_bound - fc.forecast_revenue, arrayminus=fc.forecast_revenue - fc.lower_bound)))
#     fig.update_layout(title="Forecast revenue with 80% interval", yaxis_title="EUR", height=400)
#     st.plotly_chart(fig)
#     t = fc.assign(weekday=fc.date.dt.day_name())
#     num = ["forecast_revenue", "lower_bound", "upper_bound"]
#     t[num] = t[num].round(0)
#     st.dataframe(t[["date", "weekday"] + num], hide_index=True)
#     meta = MODELS / "restrodine_prophet_calendar_weather_metadata.json"
#     if meta.exists():
#         m = json.loads(meta.read_text())
#         st.subheader("Selected model")
#         st.write(f"**{m.get('model', 'Prophet')}** - weekly seasonality, additive; regressors: " + ", ".join(m.get("regressors", [])))
#         st.caption("Selected on rolling validation and checked once on an untouched test period (notebook 02). Synthetic data.")


# def page_workforce():
#     st.title("👥 Workforce & roster")
#     w = need(wf, "Workforce forecast", "Run the workforce notebook until it saves outputs/workforce_forecast_next_*_days.csv.")
#     r = need(roster, "Recommended roster", "Run the workforce notebook (save step).")
#     d0, d1 = w.date.min().date(), w.date.max().date()
#     sel = st.date_input("Planning window", (d0, d1), min_value=d0, max_value=d1)
#     a, b = (pd.Timestamp(sel[0]), pd.Timestamp(sel[-1])) if isinstance(sel, (tuple, list)) and len(sel) else (pd.Timestamp(d0), pd.Timestamp(d1))
#     ws, rs = w[w.date.between(a, b)], r[r.date.between(a, b)]
#     c = st.columns(4)
#     c[0].metric("Labour cost", eur(ws.labour_cost.sum()))
#     c[1].metric("Labour cost % revenue", f"{ws.labour_cost.sum() / ws.forecast_revenue.sum() * 100:.1f}%")
#     c[2].metric("Labour hours", f"{ws.labour_hours.sum():,.0f}")
#     c[3].metric("Orders per labour hour", f"{ws.expected_orders.sum() / ws.labour_hours.sum():.2f}")

#     left, right = st.columns(2)
#     with left:
#         fig = px.bar(ws, x="date", y="expected_orders", color="demand_tier", color_discrete_map=TIER_COLORS, title="Expected orders and staffing tier")
#         st.plotly_chart(fig)
#     with right:
#         if coverage is not None:
#             cv = coverage[coverage.date.between(a, b)].groupby("date").agg(required=("required", "sum"), assigned=("assigned", "sum")).reset_index()
#             fig = go.Figure([go.Bar(x=cv.date, y=cv.required, name="required", marker_color="#bdbdbd"), go.Bar(x=cv.date, y=cv.assigned, name="scheduled", marker_color="#3182bd")])
#             fig.add_trace(go.Scatter(x=ws.date, y=ws.labour_cost, name="labour cost EUR", yaxis="y2", mode="lines+markers", line=dict(color="#e6550d")))
#             fig.update_layout(barmode="group", title="Required vs scheduled positions", yaxis2=dict(overlaying="y", side="right", title="EUR"))
#             st.plotly_chart(fig)

#     st.subheader("Roster calendar")
#     st.caption("L = lunch shift, D = dinner shift, F = full day")
#     g = rs.assign(code=rs.shift_type.str[0]).pivot_table(index=["role", "employee_name"], columns="date", values="code", aggfunc="first")
#     g.columns = [c.strftime("%a %d.%m") for c in g.columns]
#     g = g.reindex(sorted(g.index, key=lambda i: (ROLE_ORDER.index(i[0]) if i[0] in ROLE_ORDER else 99, i[1]))).fillna("")
#     st.dataframe(g)

#     st.subheader("Unfilled positions")
#     if gaps is not None and len(gaps):
#         gg = gaps[gaps.date.between(a, b)]
#         cols = [c for c in ["date", "weekday", "role", "shift_type", "required", "assigned", "unfilled", "reason"] if c in gg.columns]
#         st.dataframe(gg[cols], hide_index=True)
#     elif coverage is not None:
#         st.dataframe(coverage[(coverage.shortfall > 0) & coverage.date.between(a, b)][["date", "role", "shift_type", "required", "assigned", "shortfall"]], hide_index=True)
#     else:
#         st.success("Every required position is covered.")

#     st.subheader("Hours per employee")
#     eh = rs.groupby(["employee_name", "role", "employment_type"]).agg(shifts=("hours", "size"), hours=("hours", "sum"), cost=("labour_cost", "sum")).reset_index().sort_values("hours", ascending=False)
#     st.dataframe(eh.round(1), hide_index=True)
#     st.download_button("⬇️ Download roster (CSV)", rs.to_csv(index=False).encode("utf-8"), file_name="recommended_roster.csv", mime="text/csv")


# def page_menu():
#     st.title("🍕 Menu intelligence")
#     items = load("order_items")
#     prod = load("products")
#     if items is None or prod is None:
#         st.info("Add `order_items.csv` and `products.csv` to `data_clean/` (or `data/`) to enable this page.")
#         return
#     m = items.merge(prod[["product_id", "category", "product_name", "product_cost"]], on="product_id")
#     m["margin"] = m.line_total - m.quantity * m.product_cost
#     cats = st.multiselect("Categories", sorted(m.category.unique()), default=sorted(m.category.unique()))
#     m = m[m.category.isin(cats)]
#     top = m.groupby(["category", "product_name"], as_index=False).agg(units=("quantity", "sum"), revenue=("line_total", "sum"), margin=("margin", "sum"))
#     top["margin_%"] = (top.margin / top.revenue * 100).round(1)
#     n = st.slider("Top N products", 5, 30, 10)
#     c1, c2 = st.columns(2)
#     c1.plotly_chart(px.bar(top.nlargest(n, "revenue").sort_values("revenue"), x="revenue", y="product_name", color="category", orientation="h", title="Top products by revenue"))
#     c = top.groupby("category", as_index=False).agg(revenue=("revenue", "sum"), margin=("margin", "sum"))
#     c["margin_%"] = (c.margin / c.revenue * 100).round(1)
#     c2.plotly_chart(px.bar(c.sort_values("revenue"), x="revenue", y="category", orientation="h", color="margin_%", title="Revenue by category (colour = margin %)"))
#     st.dataframe(top.sort_values("revenue", ascending=False).round(1), hide_index=True)
#     st.caption("Margin proxy = line total minus units x product cost.")


# def page_customers():
#     st.title("💬 Customer intelligence")
#     rv = load("reviews", parse_dates=["review_date"])
#     if rv is None:
#         st.info("Add `reviews.csv` to `data_clean/` (or `data/`) to enable this page.")
#         return
#     c = st.columns(3)
#     c[0].metric("Reviews", f"{len(rv):,}")
#     c[1].metric("Average rating", f"{rv.rating.mean():.2f}")
#     c[2].metric("Share of 1-2 star reviews", f"{(rv.rating <= 2).mean() * 100:.0f}%")
#     l, r = st.columns(2)
#     monthly = rv.set_index("review_date").rating.resample("MS").mean().reset_index()
#     l.plotly_chart(px.line(monthly, x="review_date", y="rating", markers=True, title="Average rating per month"))
#     dist = rv.rating.value_counts().sort_index().reset_index(); dist.columns = ["rating", "reviews"]
#     r.plotly_chart(px.bar(dist, x="rating", y="reviews", title="Rating distribution"))
#     st.subheader("What guests mention (simple keyword count)")
#     keywords = {"Food": "food|dish|pizza|pasta|taste|flavour", "Service": "service", "Staff": "staff|waiter|team", "Waiting": "wait", "Price": "price|expensive|value",
#                 "Atmosphere": "atmosphere|ambience|loud|noisy|cosy", "Drinks": "drink", "Cleanliness": "clean|sticky|spotless"}
#     low = rv[rv.rating <= 2]
#     rows = [{"aspect": k, "all reviews %": round(rv.review_text.str.contains(p, case=False).mean() * 100, 1),
#              "1-2 star reviews %": round(low.review_text.str.contains(p, case=False).mean() * 100, 1) if len(low) else 0} for k, p in keywords.items()]
#     kw = pd.DataFrame(rows)
#     st.plotly_chart(px.bar(kw.melt("aspect"), x="aspect", y="value", color="variable", barmode="group", title="Share of reviews mentioning each topic (%)"))
#     st.caption("Keyword matching is a placeholder. The sentiment / aspect-analysis notebook will replace it with a proper model.")
#     st.subheader("Latest low-rated reviews")
#     st.dataframe(low.sort_values("review_date", ascending=False).head(10)[["review_date", "rating", "review_text"]], hide_index=True)


# PAGES = {"Dashboard": page_dashboard, "Revenue forecast": page_revenue, "Workforce & roster": page_workforce,
#          "Menu intelligence": page_menu, "Customer intelligence": page_customers}
# st.sidebar.title("RestroDine")
# choice = st.sidebar.radio("Page", list(PAGES))
# st.sidebar.caption("Synthetic data · decision-support prototype")
# PAGES[choice]()







# ============================================================
# RESTRODINE
# Restaurant Intelligence & Weather-Aware Revenue Forecasting
# ============================================================

from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="RestroDine | Restaurant Intelligence",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 2. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

DATA_PATH = PROJECT_ROOT / "data"
DATA_CLEAN_PATH = PROJECT_ROOT / "data_clean"
OUTPUT_PATH = PROJECT_ROOT / "outputs"
MODEL_PATH = PROJECT_ROOT / "models"
METADATA_PATH = PROJECT_ROOT / "metadata"


# ============================================================
# 3. DASHBOARD THEME
# ============================================================

st.markdown(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap'
    );

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background-color: #F5F7FB;
    }

    [data-testid="stSidebar"] {
        background-color: #101B35;
    }

    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }

    [data-testid="stSidebar"] .stRadio label {
        color: #E5EAF4 !important;
    }

    h1, h2, h3 {
        color: #17243E;
        font-weight: 700;
    }

    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E6EAF1;
        padding: 18px 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(20, 35, 60, 0.04);
    }

    [data-testid="stMetricLabel"] {
        color: #68758B;
        font-size: 13px;
    }

    [data-testid="stMetricValue"] {
        color: #17243E;
        font-weight: 700;
    }

    div[data-testid="stPlotlyChart"] {
        background-color: #FFFFFF;
        border: 1px solid #E6EAF1;
        border-radius: 12px;
        padding: 10px;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 10px;
    }

    .main-subtitle {
        color: #68758B;
        font-size: 15px;
        margin-top: -12px;
        margin-bottom: 25px;
    }

    .synthetic-banner {
        background-color: #FFF4DB;
        color: #76520A;
        padding: 11px 15px;
        border-radius: 8px;
        border: 1px solid #F1D99D;
        font-size: 13px;
        margin-bottom: 20px;
    }

    .section-note {
        color: #68758B;
        font-size: 13px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 4. GENERAL HELPER FUNCTIONS
# ============================================================

def load_csv(filename, folder=OUTPUT_PATH, parse_dates=None):
    """
    Load a CSV file safely.
    Return None if the file does not exist.
    """

    path = folder / filename

    if not path.exists():
        return None

    try:
        return pd.read_csv(
            path,
            parse_dates=parse_dates or []
        )

    except Exception as error:
        st.warning(
            f"Could not load {filename}: {error}"
        )
        return None


def load_json(filename, folder=METADATA_PATH):

    path = folder / filename

    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return None


def money(value):
    if pd.isna(value):
        return "—"

    return f"€{value:,.2f}"


def number(value):
    if pd.isna(value):
        return "—"

    return f"{value:,.0f}"


def percentage(value):
    if pd.isna(value):
        return "—"

    return f"{value:.1f}%"


def show_missing(message, filename=None):

    if filename:
        st.warning(
            f"{message}\n\nExpected file: `{filename}`"
        )
    else:
        st.warning(message)


def date_filter(df, date_column, key):

    if df is None or df.empty or date_column not in df.columns:
        return df

    df = df.copy()

    df[date_column] = pd.to_datetime(
        df[date_column],
        errors="coerce"
    )

    df = df.dropna(subset=[date_column])

    if df.empty:
        return df

    min_date = df[date_column].min().date()
    max_date = df[date_column].max().date()

    selected = st.date_input(
        "Select analysis period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key=key
    )

    if isinstance(selected, (tuple, list)) and len(selected) == 2:

        start_date, end_date = selected

        return df[
            (df[date_column].dt.date >= start_date)
            & (df[date_column].dt.date <= end_date)
        ].copy()

    return df


def metric_row(items):

    columns = st.columns(len(items))

    for col, item in zip(columns, items):

        label, value = item[0], item[1]

        with col:
            st.metric(label, value)


def plotly_chart(fig, height=400):

    fig.update_layout(
        height=height,
        margin=dict(l=25, r=25, t=55, b=25),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(
            family="DM Sans",
            color="#33415C"
        ),
        title_font=dict(
            size=17,
            color="#17243E"
        ),
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


def empty_message():
    st.info("No records are available for this selection.")


# ============================================================
# 5. LOAD PROJECT DATA
# ============================================================

@st.cache_data
def load_project_data():

    data = {}

    # Historical revenue
    data["daily_model"] = load_csv(
        "daily_model_table_clean.csv",
        folder=DATA_CLEAN_PATH,
        parse_dates=["date"]
    )

    # Revenue forecast
    data["revenue_forecast"] = load_csv(
        "revenue_forecast_next_14_days.csv",
        parse_dates=["date"]
    )

    # Workforce outputs
    data["workforce_forecast"] = load_csv(
        "workforce_forecast_next_14_days.csv",
        parse_dates=["date"]
    )

    data["roster"] = load_csv(
        "recommended_roster.csv",
        parse_dates=["date"]
    )

    data["staffing_coverage"] = load_csv(
        "staffing_coverage.csv",
        parse_dates=["date"]
    )

    data["staffing_gaps"] = load_csv(
        "staffing_gaps.csv",
        parse_dates=["date"]
    )

    # Customer intelligence outputs
    customer_files = {
        "customer_kpis": "customer_intelligence_kpis.csv",
        "aspect_sentiment": "customer_aspect_sentiment_summary.csv",
        "improvement_areas": "customer_improvement_areas.csv",
        "monthly_sentiment": "customer_monthly_sentiment.csv",
        "customer_type": "customer_feedback_by_type.csv",
        "customer_ratings": "customer_ratings_by_type.csv",
        "rfm": "customer_rfm_segments.csv",
        "rfm_profile": "customer_segment_profile.csv",
        "feedback_segment": "customer_feedback_by_segment.csv",
        "negative_feedback": "high_value_negative_feedback.csv",
        "feedback_detail": "customer_review_aspect_detail.csv"
    }

    for key, filename in customer_files.items():

        data[key] = load_csv(
            filename,
            parse_dates=["review_date"]
            if key in ["negative_feedback", "feedback_detail"]
            else None
        )

    # Clean source data for menu analysis
    data["orders"] = load_csv(
        "orders_clean.csv",
        folder=DATA_CLEAN_PATH,
        parse_dates=["order_datetime", "order_date"]
    )

    data["order_items"] = load_csv(
        "order_items_clean.csv",
        folder=DATA_CLEAN_PATH
    )

    data["products"] = load_csv(
        "products_clean.csv",
        folder=DATA_CLEAN_PATH
    )

    data["customers"] = load_csv(
        "customers_clean.csv",
        folder=DATA_CLEAN_PATH
    )

    data["reviews"] = load_csv(
        "reviews_clean.csv",
        folder=DATA_CLEAN_PATH,
        parse_dates=["review_date"]
    )

    data["employees"] = load_csv(
        "employees_clean.csv",
        folder=DATA_CLEAN_PATH
    )

    data["shifts"] = load_csv(
        "shifts_clean.csv",
        folder=DATA_CLEAN_PATH,
        parse_dates=["shift_date"]
    )

    data["weather"] = load_csv(
        "weather_clean.csv",
        folder=DATA_CLEAN_PATH,
        parse_dates=["date"]
    )

    data["calendar"] = load_csv(
        "calendar_clean.csv",
        folder=DATA_CLEAN_PATH,
        parse_dates=["date"]
    )

    # Model metadata
    data["model_metadata"] = load_json(
        "restrodine_prophet_calendar_weather_metadata.json"
    )

    data["customer_metadata"] = load_json(
        "customer_intelligence_summary.json"
    )

    return data


data = load_project_data()


# ============================================================
# 6. PREPARE HISTORICAL REVENUE
# ============================================================

daily_model = data["daily_model"]

if daily_model is not None:

    daily_model["date"] = pd.to_datetime(
        daily_model["date"],
        errors="coerce"
    )

    daily_model = daily_model.dropna(
        subset=["date", "revenue"]
    )

    for col in ["revenue", "orders", "average_order_value"]:
        if col in daily_model.columns:
            daily_model[col] = pd.to_numeric(
                daily_model[col],
                errors="coerce"
            )

    data["daily_model"] = daily_model


# ============================================================
# 7. PREPARE REVENUE FORECAST
# ============================================================

revenue_forecast = data["revenue_forecast"]

if revenue_forecast is not None:

    revenue_forecast["date"] = pd.to_datetime(
        revenue_forecast["date"],
        errors="coerce"
    )

    revenue_forecast = revenue_forecast.dropna(
        subset=["date", "forecast_revenue"]
    )

    data["revenue_forecast"] = revenue_forecast


# ============================================================
# 8. MENU PERFORMANCE DATA PREPARATION
# ============================================================

@st.cache_data
def build_menu_performance(orders, order_items, products):

    if orders is None or order_items is None or products is None:
        return None

    required_items = {
        "order_id",
        "product_id",
        "quantity",
        "line_total"
    }

    required_products = {
        "product_id",
        "product_name",
        "category",
        "product_cost"
    }

    if not required_items.issubset(order_items.columns):
        return None

    if not required_products.issubset(products.columns):
        return None

    items = order_items.copy()
    product_data = products.copy()
    order_data = orders.copy()

    items["quantity"] = pd.to_numeric(
        items["quantity"],
        errors="coerce"
    )

    items["line_total"] = pd.to_numeric(
        items["line_total"],
        errors="coerce"
    )

    product_data["product_cost"] = pd.to_numeric(
        product_data["product_cost"],
        errors="coerce"
    )

    if "order_datetime" in order_data.columns:
        order_data["order_datetime"] = pd.to_datetime(
            order_data["order_datetime"],
            errors="coerce"
        )

        order_data["order_date"] = (
            order_data["order_datetime"].dt.normalize()
        )

    elif "order_date" in order_data.columns:
        order_data["order_date"] = pd.to_datetime(
            order_data["order_date"],
            errors="coerce"
        )

    else:
        return None

    menu = items.merge(
        product_data[
            [
                "product_id",
                "product_name",
                "category",
                "product_cost"
            ]
        ],
        on="product_id",
        how="left"
    )

    menu = menu.merge(
        order_data[
            ["order_id", "order_date"]
        ],
        on="order_id",
        how="left"
    )

    menu = menu.dropna(
        subset=[
            "product_name",
            "quantity",
            "line_total",
            "product_cost"
        ]
    )

    menu["gross_profit"] = (
        menu["line_total"]
        - menu["quantity"] * menu["product_cost"]
    )

    menu["gross_margin_pct"] = np.where(
        menu["line_total"] > 0,
        menu["gross_profit"] / menu["line_total"] * 100,
        np.nan
    )

    menu["month"] = (
        menu["order_date"].dt.to_period("M").astype(str)
    )

    product_summary = (
        menu.groupby(
            ["product_id", "product_name", "category"],
            as_index=False
        )
        .agg(
            quantity_sold=("quantity", "sum"),
            revenue=("line_total", "sum"),
            gross_profit=("gross_profit", "sum"),
            total_cost=("product_cost", lambda x: 0)
        )
    )

    # Calculate total cost correctly from line quantities
    menu["total_product_cost"] = (
        menu["quantity"] * menu["product_cost"]
    )

    cost_summary = (
        menu.groupby("product_id")["total_product_cost"]
        .sum()
        .reset_index()
    )

    product_summary = product_summary.drop(
        columns=["total_cost"]
    ).merge(
        cost_summary,
        on="product_id",
        how="left"
    )

    product_summary["gross_margin_pct"] = np.where(
        product_summary["revenue"] > 0,
        product_summary["gross_profit"]
        / product_summary["revenue"] * 100,
        np.nan
    )

    # Menu engineering
    popularity_threshold = product_summary[
        "quantity_sold"
    ].median()

    profitability_threshold = product_summary[
        "gross_profit"
    ].median()

    def classify_menu_item(row):

        popular = row["quantity_sold"] >= popularity_threshold

        profitable = row["gross_profit"] >= profitability_threshold

        if popular and profitable:
            return "Star"

        if popular and not profitable:
            return "Plowhorse"

        if not popular and profitable:
            return "Puzzle"

        return "Dog"

    product_summary["menu_category"] = (
        product_summary.apply(
            classify_menu_item,
            axis=1
        )
    )

    category_summary = (
        menu.groupby("category", as_index=False)
        .agg(
            quantity_sold=("quantity", "sum"),
            revenue=("line_total", "sum"),
            gross_profit=("gross_profit", "sum")
        )
    )

    monthly_menu = (
        menu.groupby(
            ["month", "category"],
            as_index=False
        )
        .agg(
            revenue=("line_total", "sum"),
            quantity_sold=("quantity", "sum"),
            gross_profit=("gross_profit", "sum")
        )
    )

    return {
        "detail": menu,
        "products": product_summary,
        "categories": category_summary,
        "monthly": monthly_menu,
        "popularity_threshold": popularity_threshold,
        "profitability_threshold": profitability_threshold
    }


menu_data = build_menu_performance(
    data["orders"],
    data["order_items"],
    data["products"]
)


# ============================================================
# 9. SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="padding: 10px 0 20px 0;">

            <div style="font-size: 32px;">🍽️</div>

            <div style="
                font-size: 25px;
                font-weight: 700;
                letter-spacing: -0.5px;
            ">
                RestroDine
            </div>

            <div style="
                font-size: 12px;
                color: #AAB8D0;
                margin-top: 4px;
            ">
                RESTAURANT INTELLIGENCE PLATFORM
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Executive Overview",
            "Revenue Intelligence",
            "Workforce Intelligence",
            "Customer Intelligence",
            "Menu Performance"
        ],
        label_visibility="visible"
    )

    st.divider()

    st.caption("PROJECT INFORMATION")

    st.markdown(
        """
        **RestroDine**

        Data Science & AI

        Restaurant analytics, forecasting
        and operational intelligence.
        """
    )

    st.divider()

    st.caption("All data is synthetic.")


# ============================================================
# 10. APPLICATION HEADER
# ============================================================

st.title("🍽️ RestroDine")

st.markdown(
    '<div class="main-subtitle">'
    'Restaurant Intelligence & Weather-Aware Revenue Forecasting'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="synthetic-banner">
        <strong>DEMONSTRATION PROJECT</strong> &nbsp;|
        All customers, transactions, reviews, workforce records
        and analytical findings are based on synthetic data.
        They do not represent real restaurant operations.
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 11. EXECUTIVE OVERVIEW
# ============================================================

if page == "Executive Overview":

    st.header("Executive Overview")

    st.caption(
        "A consolidated view of restaurant performance, "
        "customer experience and operational planning."
    )

    if daily_model is None:

        show_missing(
            "Historical revenue data is unavailable.",
            "data_clean/daily_model_table_clean.csv"
        )

    else:

        overview = daily_model.copy()

        overview = date_filter(
            overview,
            "date",
            "overview_date"
        )

        if overview.empty:
            empty_message()

        else:

            total_revenue = overview["revenue"].sum()

            total_orders = overview["orders"].sum()

            average_aov = (
                total_revenue / total_orders
                if total_orders > 0 else np.nan
            )

            average_daily_revenue = overview["revenue"].mean()

            customer_kpis = data["customer_kpis"]

            review_count = np.nan
            average_rating = np.nan

            if customer_kpis is not None:

                kpi_lookup = dict(
                    zip(
                        customer_kpis["Metric"],
                        customer_kpis["Value"]
                    )
                )

                review_count = kpi_lookup.get(
                    "Total Reviews",
                    np.nan
                )

            shifts = data["shifts"]

            labour_cost = np.nan

            if shifts is not None and "labour_cost" in shifts.columns:

                labour_cost = pd.to_numeric(
                    shifts["labour_cost"],
                    errors="coerce"
                ).sum()

            metric_row([
                ("Total Revenue", money(total_revenue)),
                ("Total Orders", number(total_orders)),
                ("Average Order Value", money(average_aov)),
                ("Average Daily Revenue", money(average_daily_revenue))
            ])

            st.divider()

            col1, col2 = st.columns(2)

            with col1:

                st.subheader("Revenue Performance")

                fig = px.area(
                    overview,
                    x="date",
                    y="revenue",
                    title="Daily Revenue"
                )

                plotly_chart(fig)

            with col2:

                st.subheader("Orders Over Time")

                fig = px.line(
                    overview,
                    x="date",
                    y="orders",
                    title="Daily Order Volume"
                )

                plotly_chart(fig)

            col1, col2 = st.columns(2)

            with col1:

                st.subheader("Revenue by Weekday")

                if "day_of_week" in overview.columns:

                    weekday = (
                        overview.groupby("day_of_week", as_index=False)
                        .agg(
                            average_revenue=("revenue", "mean")
                        )
                    )

                    weekday_order = [
                        "Monday", "Tuesday", "Wednesday",
                        "Thursday", "Friday", "Saturday", "Sunday"
                    ]

                    weekday["day_of_week"] = pd.Categorical(
                        weekday["day_of_week"],
                        categories=weekday_order,
                        ordered=True
                    )

                    weekday = weekday.sort_values("day_of_week")

                    fig = px.bar(
                        weekday,
                        x="day_of_week",
                        y="average_revenue",
                        title="Average Daily Revenue by Weekday"
                    )

                    plotly_chart(fig)

            with col2:

                st.subheader("Promotion Performance")

                if "is_promo_day" in overview.columns:

                    promo = (
                        overview.groupby("is_promo_day", as_index=False)
                        .agg(
                            average_revenue=("revenue", "mean")
                        )
                    )

                    promo["Promotion"] = promo[
                        "is_promo_day"
                    ].map({
                        0: "No Promotion",
                        1: "Promotion"
                    })

                    fig = px.bar(
                        promo,
                        x="Promotion",
                        y="average_revenue",
                        title="Average Revenue: Promotion vs No Promotion"
                    )

                    plotly_chart(fig)

            st.divider()

            st.subheader("Business Performance Snapshot")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Customer Reviews",
                number(review_count)
            )

            col2.metric(
                "Historical Labour Cost",
                money(labour_cost)
            )

            col3.metric(
                "Average Daily Revenue",
                money(average_daily_revenue)
            )

            st.divider()

            st.subheader("Upcoming Revenue Forecast")

            forecast = data["revenue_forecast"]

            if forecast is not None and not forecast.empty:

                total_forecast = forecast[
                    "forecast_revenue"
                ].sum()

                metric_row([
                    ("Forecast Revenue", money(total_forecast)),
                    (
                        "Forecast Daily Average",
                        money(forecast["forecast_revenue"].mean())
                    ),
                    ("Forecast Days", number(len(forecast)))
                ])

                fig = px.line(
                    forecast,
                    x="date",
                    y="forecast_revenue",
                    markers=True,
                    title="Upcoming Revenue Forecast"
                )

                plotly_chart(fig, height=350)

            else:

                show_missing(
                    "The saved operational forecast is not available.",
                    "outputs/revenue_forecast_next_14_days.csv"
                )

            st.divider()

            st.subheader("Menu Highlights")

            if menu_data is not None:

                top_products = (
                    menu_data["products"]
                    .sort_values("revenue", ascending=False)
                    .head(5)
                )

                st.dataframe(
                    top_products[
                        [
                            "product_name",
                            "category",
                            "quantity_sold",
                            "revenue",
                            "gross_profit",
                            "gross_margin_pct"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "Menu performance will appear when the cleaned "
                    "product and order-item datasets are available."
                )


# ============================================================
# 12. REVENUE INTELLIGENCE
# ============================================================

elif page == "Revenue Intelligence":

    st.header("📈 Revenue Intelligence")

    st.caption(
        "Understand historical revenue, identify business patterns "
        "and review the selected Prophet forecast."
    )

    if daily_model is None:

        show_missing(
            "Historical revenue data is unavailable.",
            "data_clean/daily_model_table_clean.csv"
        )

    else:

        revenue = daily_model.copy()

        revenue = date_filter(
            revenue,
            "date",
            "revenue_date"
        )

        if revenue.empty:

            empty_message()

        else:

            total_revenue = revenue["revenue"].sum()

            total_orders = revenue["orders"].sum()

            aov = (
                total_revenue / total_orders
                if total_orders > 0 else np.nan
            )

            metric_row([
                ("Revenue", money(total_revenue)),
                ("Orders", number(total_orders)),
                ("Average Order Value", money(aov)),
                ("Daily Average Revenue", money(revenue["revenue"].mean()))
            ])

            st.divider()

            st.subheader("Historical Revenue Trend")

            fig = px.line(
                revenue,
                x="date",
                y="revenue",
                title="Daily Revenue",
                markers=False
            )

            plotly_chart(fig, height=450)

            col1, col2 = st.columns(2)

            with col1:

                st.subheader("Revenue by Month")

                monthly = (
                    revenue.assign(
                        month=revenue["date"].dt.to_period("M").astype(str)
                    )
                    .groupby("month", as_index=False)
                    .agg(
                        revenue=("revenue", "sum")
                    )
                )

                fig = px.bar(
                    monthly,
                    x="month",
                    y="revenue",
                    title="Monthly Revenue"
                )

                plotly_chart(fig)

            with col2:

                st.subheader("Revenue by Meal Period")

                if "restaurant_day_type" in revenue.columns:

                    day_type = (
                        revenue.groupby(
                            "restaurant_day_type",
                            as_index=False
                        )
                        .agg(
                            average_revenue=("revenue", "mean")
                        )
                    )

                    fig = px.bar(
                        day_type,
                        x="restaurant_day_type",
                        y="average_revenue",
                        title="Average Revenue by Day Type"
                    )

                    plotly_chart(fig)

                elif "day_of_week" in revenue.columns:

                    weekday = (
                        revenue.groupby(
                            "day_of_week",
                            as_index=False
                        )
                        .agg(
                            average_revenue=("revenue", "mean")
                        )
                    )

                    fig = px.bar(
                        weekday,
                        x="day_of_week",
                        y="average_revenue",
                        title="Average Revenue by Weekday"
                    )

                    plotly_chart(fig)

            col1, col2 = st.columns(2)

            with col1:

                st.subheader("Order Type Performance")

                if "order_type" in revenue.columns:

                    order_type = (
                        revenue.groupby(
                            "order_type",
                            as_index=False
                        )
                        .agg(
                            revenue=("revenue", "sum")
                        )
                    )

                    fig = px.pie(
                        order_type,
                        names="order_type",
                        values="revenue",
                        hole=0.55,
                        title="Revenue Distribution by Order Type"
                    )

                    plotly_chart(fig)

                else:

                    st.info(
                        "Order type is not included in the daily model table."
                    )

            with col2:

                st.subheader("Weather and Revenue")

                if "weather_condition" in revenue.columns:

                    weather = (
                        revenue.groupby(
                            "weather_condition",
                            as_index=False
                        )
                        .agg(
                            average_revenue=("revenue", "mean")
                        )
                    )

                    fig = px.bar(
                        weather,
                        x="weather_condition",
                        y="average_revenue",
                        title="Average Revenue by Weather Condition"
                    )

                    plotly_chart(fig)

                elif "temperature_avg_c" in revenue.columns:

                    fig = px.scatter(
                        revenue,
                        x="temperature_avg_c",
                        y="revenue",
                        title="Temperature vs Revenue",
                        trendline="ols"
                    )

                    plotly_chart(fig)

                else:

                    st.info(
                        "Weather variables are not available in the daily model."
                    )

            st.divider()

            st.subheader("Promotion Impact")

            if "is_promo_day" in revenue.columns:

                promo = (
                    revenue.groupby("is_promo_day", as_index=False)
                    .agg(
                        average_revenue=("revenue", "mean"),
                        total_revenue=("revenue", "sum"),
                        days=("date", "count")
                    )
                )

                promo["Promotion"] = promo[
                    "is_promo_day"
                ].map({
                    0: "No Promotion",
                    1: "Promotion"
                })

                fig = px.bar(
                    promo,
                    x="Promotion",
                    y="average_revenue",
                    title="Average Daily Revenue by Promotion Status"
                )

                plotly_chart(fig)

                st.dataframe(
                    promo[
                        [
                            "Promotion",
                            "days",
                            "average_revenue",
                            "total_revenue"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "Promotion information is not available."
                )

    # Revenue forecast
    st.divider()

    st.subheader("🔮 Revenue Forecast")

    forecast = data["revenue_forecast"]

    if forecast is None or forecast.empty:

        show_missing(
            "Operational forecast not found. Run Notebook 02 first.",
            "outputs/revenue_forecast_next_14_days.csv"
        )

    else:

        forecast = forecast.sort_values("date")

        forecast_total = forecast[
            "forecast_revenue"
        ].sum()

        forecast_aov = (
            daily_model["average_order_value"].median()
            if daily_model is not None
            else np.nan
        )

        expected_orders = (
            forecast_total / forecast_aov
            if pd.notna(forecast_aov) and forecast_aov > 0
            else np.nan
        )

        metric_row([
            ("Forecast Revenue", money(forecast_total)),
            (
                "Average Daily Forecast",
                money(forecast["forecast_revenue"].mean())
            ),
            ("Expected Orders (estimated)", number(expected_orders)),
            ("Forecast Horizon", f"{len(forecast)} days")
        ])

        history = data["daily_model"]

        if history is not None:

            recent_history = history.tail(60)[
                ["date", "revenue"]
            ].copy()

            recent_history["Type"] = "Historical"

            future_plot = forecast[
                ["date", "forecast_revenue"]
            ].rename(
                columns={
                    "forecast_revenue": "revenue"
                }
            )

            future_plot["Type"] = "Forecast"

            combined = pd.concat(
                [recent_history, future_plot],
                ignore_index=True
            )

            fig = px.line(
                combined,
                x="date",
                y="revenue",
                color="Type",
                markers=True,
                title="Historical Revenue and Future Forecast"
            )

            plotly_chart(fig, height=430)

        if {"lower_bound", "upper_bound"}.issubset(forecast.columns):

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=forecast["date"],
                    y=forecast["upper_bound"],
                    line=dict(width=0),
                    showlegend=False,
                    name="Upper bound"
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=forecast["date"],
                    y=forecast["lower_bound"],
                    fill="tonexty",
                    fillcolor="rgba(52, 152, 219, 0.15)",
                    line=dict(width=0),
                    name="80% prediction interval"
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=forecast["date"],
                    y=forecast["forecast_revenue"],
                    mode="lines+markers",
                    name="Forecast revenue",
                    line=dict(width=3)
                )
            )

            fig.update_layout(
                title="Forecast with Prediction Interval",
                yaxis_title="Revenue (€)",
                xaxis_title="Date"
            )

            plotly_chart(fig)

        st.subheader("Daily Forecast Table")

        st.dataframe(
            forecast,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Revenue Forecast",
            forecast.to_csv(index=False),
            file_name="revenue_forecast.csv",
            mime="text/csv"
        )

        metadata = data["model_metadata"]

        if metadata:

            st.caption(
                f"Forecast model: {metadata.get('model', 'Prophet')}"
            )

            st.caption(
                f"Training period: "
                f"{metadata.get('training_start', '—')} "
                f"to {metadata.get('training_end', '—')}"
            )

            st.caption(
                "The dashboard displays the saved forecast output. "
                "It does not refit the Prophet model during app execution."
            )


# ============================================================
# 13. WORKFORCE INTELLIGENCE
# ============================================================

elif page == "Workforce Intelligence":

    st.header("👥 Workforce Intelligence")

    st.caption(
        "Forecast demand → Plan staffing → Build the roster."
    )

    workforce = data["workforce_forecast"]

    roster = data["roster"]

    coverage = data["staffing_coverage"]

    gaps = data["staffing_gaps"]

    if workforce is None:

        show_missing(
            "Workforce forecast is unavailable. "
            "Run Notebook 02 and Notebook 03 first.",
            "outputs/workforce_forecast_next_14_days.csv"
        )

    else:

        workforce = workforce.sort_values("date")

        metric_row([
            (
                "Forecast Revenue",
                money(workforce["forecast_revenue"].sum())
            ),
            (
                "Expected Orders",
                number(workforce["expected_orders"].sum())
            ),
            (
                "Estimated Labour Cost",
                money(workforce["labour_cost"].sum())
            ),
            (
                "Labour Cost / Revenue",
                percentage(
                    workforce["labour_cost"].sum()
                    / workforce["forecast_revenue"].sum() * 100
                    if workforce["forecast_revenue"].sum() > 0
                    else np.nan
                )
            )
        ])

        st.divider()

        st.subheader("Daily Workforce Forecast")

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=workforce["date"],
                y=workforce["expected_orders"],
                name="Expected Orders"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=workforce["date"],
                y=workforce["scheduled_employees"],
                name="Scheduled Employees",
                yaxis="y2",
                mode="lines+markers"
            )
        )

        fig.update_layout(
            title="Expected Demand and Scheduled Employees",
            yaxis=dict(title="Expected Orders"),
            yaxis2=dict(
                title="Employees",
                overlaying="y",
                side="right"
            )
        )

        plotly_chart(fig)

        col1, col2 = st.columns(2)

        with col1:

            st.subheader("Labour Cost by Day")

            fig = px.bar(
                workforce,
                x="date",
                y="labour_cost",
                title="Forecast Labour Cost"
            )

            plotly_chart(fig)

        with col2:

            st.subheader("Labour Cost as % of Revenue")

            fig = px.line(
                workforce,
                x="date",
                y="labour_cost_pct_revenue",
                markers=True,
                title="Labour Cost Percentage"
            )

            plotly_chart(fig)

        st.divider()

        st.subheader("Daily Workforce Requirements")

        display_columns = [
            col for col in [
                "date",
                "expected_orders",
                "demand_tier",
                "required_staff",
                "scheduled_employees",
                "labour_hours",
                "labour_cost",
                "labour_cost_pct_revenue"
            ]
            if col in workforce.columns
        ]

        st.dataframe(
            workforce[display_columns],
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        st.subheader("Recommended Staffing by Role")

        if roster is not None and not roster.empty:

            role_summary = (
                roster.groupby("role")
                .agg(
                    assigned_shifts=("employee_id", "count"),
                    employees=("employee_id", "nunique"),
                    total_hours=("hours", "sum"),
                    labour_cost=("labour_cost", "sum")
                )
                .reset_index()
            )

            col1, col2 = st.columns(2)

            with col1:

                fig = px.bar(
                    role_summary,
                    x="role",
                    y="assigned_shifts",
                    title="Recommended Shifts by Role"
                )

                plotly_chart(fig)

            with col2:

                fig = px.pie(
                    role_summary,
                    names="role",
                    values="labour_cost",
                    hole=0.55,
                    title="Labour Cost Distribution by Role"
                )

                plotly_chart(fig)

            st.dataframe(
                role_summary,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No recommended roster assignments are available."
            )

        st.divider()

        st.subheader("Recommended Weekly Roster")

        if roster is not None and not roster.empty:

            roster = roster.copy()

            roster["date"] = pd.to_datetime(
                roster["date"]
            )

            available_weeks = sorted(
                roster["date"].dt.to_period("W").astype(str).unique()
            )

            selected_week = st.selectbox(
                "Select roster week",
                available_weeks
            )

            weekly_roster = roster[
                roster["date"].dt.to_period("W").astype(str)
                == selected_week
            ].copy()

            st.dataframe(
                weekly_roster[
                    [
                        col for col in [
                            "date",
                            "employee_name",
                            "role",
                            "shift_type",
                            "start_time",
                            "end_time",
                            "hours",
                            "labour_cost"
                        ]
                        if col in weekly_roster.columns
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Weekly Roster",
                weekly_roster.to_csv(index=False),
                file_name="weekly_roster.csv",
                mime="text/csv"
            )

        else:

            st.info("Recommended roster is not available.")

        st.divider()

        st.subheader("Staffing Coverage")

        if coverage is not None and not coverage.empty:

            st.dataframe(
                coverage,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info("Staffing coverage data is unavailable.")

        st.subheader("Staffing Gaps")

        if gaps is not None and not gaps.empty:

            total_unfilled = gaps["unfilled"].sum()

            st.metric(
                "Unfilled Staffing Positions",
                number(total_unfilled)
            )

            st.dataframe(
                gaps,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.success(
                "No staffing gaps were recorded in the saved forecast."
            )

        if roster is not None:

            st.download_button(
                "Download Full Recommended Roster",
                roster.to_csv(index=False),
                file_name="recommended_roster.csv",
                mime="text/csv"
            )


# ============================================================
# 14. CUSTOMER INTELLIGENCE
# ============================================================

elif page == "Customer Intelligence":

    st.header("💬 Customer Intelligence")

    st.caption(
        "Understand customer feedback, identify service issues "
        "and prioritise customer relationships."
    )

    customer_kpis = data["customer_kpis"]

    if customer_kpis is not None:

        kpi_values = dict(
            zip(
                customer_kpis["Metric"],
                customer_kpis["Value"]
            )
        )

        metric_row([
            (
                "Total Reviews",
                number(kpi_values.get("Total Reviews", np.nan))
            ),
            (
                "Customers Reviewed",
                number(
                    kpi_values.get(
                        "Customers Who Reviewed",
                        np.nan
                    )
                )
            ),
            (
                "Average Rating",
                f"{kpi_values.get('Average Rating', np.nan):.2f} / 5"
                if pd.notna(
                    kpi_values.get("Average Rating", np.nan)
                )
                else "—"
            ),
            (
                "Aspect Mentions",
                number(
                    kpi_values.get(
                        "Aspect Mentions",
                        np.nan
                    )
                )
            )
        ])

    else:

        show_missing(
            "Customer KPI file is unavailable.",
            "outputs/customer_intelligence_kpis.csv"
        )

    st.divider()

    aspect = data["aspect_sentiment"]

    if aspect is not None and not aspect.empty:

        st.subheader("Customer Sentiment by Aspect")

        sentiment_columns = [
            "Positive (%)",
            "Neutral (%)",
            "Negative (%)"
        ]

        if all(col in aspect.columns for col in sentiment_columns):

            aspect_plot = aspect.melt(
                id_vars="aspect",
                value_vars=sentiment_columns,
                var_name="Sentiment",
                value_name="Percentage"
            )

            fig = px.bar(
                aspect_plot,
                x="aspect",
                y="Percentage",
                color="Sentiment",
                barmode="stack",
                title="Sentiment Distribution Across Restaurant Aspects"
            )

            plotly_chart(fig)

        st.dataframe(
            aspect,
            use_container_width=True,
            hide_index=True
        )

    else:

        show_missing(
            "Aspect sentiment analysis is unavailable.",
            "outputs/customer_aspect_sentiment_summary.csv"
        )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Areas for Improvement")

        improvement = data["improvement_areas"]

        if improvement is not None:

            st.dataframe(
                improvement,
                use_container_width=True,
                hide_index=True
            )

        else:

            show_missing(
                "Improvement priorities are unavailable.",
                "outputs/customer_improvement_areas.csv"
            )

    with col2:

        st.subheader("Monthly Sentiment Trends")

        monthly = data["monthly_sentiment"]

        if monthly is not None and not monthly.empty:

            sentiment_cols = [
                col for col in [
                    "Positive",
                    "Neutral",
                    "Negative"
                ]
                if col in monthly.columns
            ]

            fig = px.line(
                monthly,
                x="review_month",
                y=sentiment_cols,
                markers=True,
                title="Monthly Sentiment Mentions"
            )

            plotly_chart(fig)

        else:

            show_missing(
                "Monthly sentiment data is unavailable.",
                "outputs/customer_monthly_sentiment.csv"
            )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Feedback by Customer Type")

        customer_type = data["customer_type"]

        if customer_type is not None:

            sentiment_cols = [
                col for col in [
                    "Positive (%)",
                    "Neutral (%)",
                    "Negative (%)"
                ]
                if col in customer_type.columns
            ]

            fig = px.bar(
                customer_type,
                x="customer_type",
                y=sentiment_cols,
                barmode="stack",
                title="Sentiment by Customer Type"
            )

            plotly_chart(fig)

        else:

            show_missing(
                "Customer type sentiment data is unavailable.",
                "outputs/customer_feedback_by_type.csv"
            )

    with col2:

        st.subheader("Customer Segment Profile")

        profile = data["rfm_profile"]

        if profile is not None:

            fig = px.bar(
                profile,
                x="RFM_Segment",
                y="Customer_Count",
                title="Customers by RFM Segment"
            )

            plotly_chart(fig)

        else:

            show_missing(
                "RFM segment profile is unavailable.",
                "outputs/customer_segment_profile.csv"
            )

    st.divider()

    st.subheader("High-Value Customers with Negative Feedback")

    negative = data["negative_feedback"]

    if negative is not None and not negative.empty:

        st.caption(
            "These customers are flagged for potential service recovery. "
            "This is a prioritisation list, not a churn prediction."
        )

        st.dataframe(
            negative,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Negative Feedback List",
            negative.to_csv(index=False),
            file_name="high_value_negative_feedback.csv",
            mime="text/csv"
        )

    else:

        st.info(
            "No high-value negative feedback records are available "
            "for display, or the export is empty."
        )

    st.divider()

    st.subheader("Customer Review Explorer")

    feedback = data["feedback_detail"]

    if feedback is not None and not feedback.empty:

        filtered_feedback = feedback.copy()

        if "aspect" in filtered_feedback.columns:

            aspects = sorted(
                filtered_feedback["aspect"].dropna().unique()
            )

            selected_aspects = st.multiselect(
                "Filter by aspect",
                aspects,
                default=aspects
            )

            filtered_feedback = filtered_feedback[
                filtered_feedback["aspect"].isin(selected_aspects)
            ]

        if "sentiment" in filtered_feedback.columns:

            sentiments = sorted(
                filtered_feedback["sentiment"].dropna().unique()
            )

            selected_sentiments = st.multiselect(
                "Filter by sentiment",
                sentiments,
                default=sentiments
            )

            filtered_feedback = filtered_feedback[
                filtered_feedback["sentiment"].isin(selected_sentiments)
            ]

        if "customer_type" in filtered_feedback.columns:

            customer_types = sorted(
                filtered_feedback["customer_type"].dropna().unique()
            )

            selected_types = st.multiselect(
                "Filter by customer type",
                customer_types,
                default=customer_types
            )

            filtered_feedback = filtered_feedback[
                filtered_feedback["customer_type"].isin(selected_types)
            ]

        st.dataframe(
            filtered_feedback,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Filtered Customer Feedback",
            filtered_feedback.to_csv(index=False),
            file_name="customer_feedback_detail.csv",
            mime="text/csv"
        )

    else:

        show_missing(
            "Detailed review data is unavailable.",
            "outputs/customer_review_aspect_detail.csv"
        )

    st.caption(
        "Sentiment values are supplied synthetic annotations, "
        "not predictions from a trained NLP model."
    )


# ============================================================
# 15. MENU PERFORMANCE
# ============================================================

elif page == "Menu Performance":

    st.header("🍕 Menu Performance")

    st.caption(
        "Understand product sales, revenue contribution, profitability "
        "and menu engineering."
    )

    if menu_data is None:

        show_missing(
            "Menu data could not be prepared. "
            "Check the cleaned products, order items and orders datasets.",
            "data_clean/products_clean.csv, "
            "data_clean/order_items_clean.csv, "
            "data_clean/orders_clean.csv"
        )

    else:

        products = menu_data["products"].copy()

        categories = menu_data["categories"].copy()

        monthly = menu_data["monthly"].copy()

        detail = menu_data["detail"].copy()

        metric_row([
            (
                "Menu Revenue",
                money(products["revenue"].sum())
            ),
            (
                "Units Sold",
                number(products["quantity_sold"].sum())
            ),
            (
                "Gross Profit",
                money(products["gross_profit"].sum())
            ),
            (
                "Gross Margin",
                percentage(
                    products["gross_profit"].sum()
                    / products["revenue"].sum() * 100
                    if products["revenue"].sum() > 0
                    else np.nan
                )
            )
        ])

        st.divider()

        st.subheader("Product Performance")

        col1, col2 = st.columns(2)

        with col1:

            fig = px.bar(
                products.sort_values(
                    "revenue",
                    ascending=False
                ).head(10),
                x="revenue",
                y="product_name",
                orientation="h",
                title="Top 10 Products by Revenue"
            )

            fig.update_layout(
                yaxis={"categoryorder": "total ascending"}
            )

            plotly_chart(fig)

        with col2:

            fig = px.bar(
                products.sort_values(
                    "gross_profit",
                    ascending=False
                ).head(10),
                x="gross_profit",
                y="product_name",
                orientation="h",
                title="Top 10 Products by Gross Profit"
            )

            fig.update_layout(
                yaxis={"categoryorder": "total ascending"}
            )

            plotly_chart(fig)

        st.divider()

        st.subheader("Category Performance")

        col1, col2 = st.columns(2)

        with col1:

            fig = px.pie(
                categories,
                names="category",
                values="revenue",
                hole=0.55,
                title="Revenue Contribution by Category"
            )

            plotly_chart(fig)

        with col2:

            fig = px.bar(
                categories.sort_values(
                    "gross_profit",
                    ascending=False
                ),
                x="category",
                y="gross_profit",
                title="Gross Profit by Category"
            )

            plotly_chart(fig)

        st.divider()

        st.subheader("Menu Engineering Matrix")

        st.caption(
            "Classification uses the median product quantity sold "
            "and median total gross profit as transparent project "
            "benchmarks. This is an exploratory menu-engineering "
            "classification, not a universal restaurant standard."
        )

        fig = px.scatter(
            products,
            x="quantity_sold",
            y="gross_profit",
            color="menu_category",
            size="revenue",
            hover_name="product_name",
            hover_data=[
                "category",
                "gross_margin_pct"
            ],
            title="Menu Engineering: Popularity vs Profitability"
        )

        fig.add_vline(
            x=menu_data["popularity_threshold"],
            line_dash="dash",
            line_color="grey"
        )

        fig.add_hline(
            y=menu_data["profitability_threshold"],
            line_dash="dash",
            line_color="grey"
        )

        plotly_chart(fig, height=550)

        segment_descriptions = pd.DataFrame({
            "Menu Category": [
                "Star",
                "Plowhorse",
                "Puzzle",
                "Dog"
            ],
            "Interpretation": [
                "Popular products with high total gross profit.",
                "Popular products with lower total gross profit.",
                "Less popular products with high total gross profit.",
                "Less popular products with lower total gross profit."
            ],
            "Potential Management Action": [
                "Maintain quality and visibility.",
                "Review costs, portions and pricing.",
                "Improve promotion and menu placement.",
                "Review whether to redesign or remove."
            ]
        })

        st.dataframe(
            segment_descriptions,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        st.subheader("Monthly Menu Trends")

        fig = px.line(
            monthly,
            x="month",
            y="revenue",
            color="category",
            markers=True,
            title="Monthly Revenue by Product Category"
        )

        plotly_chart(fig)

        st.divider()

        st.subheader("Complete Product Performance Table")

        category_filter = st.multiselect(
            "Filter product categories",
            sorted(products["category"].dropna().unique()),
            default=sorted(products["category"].dropna().unique())
        )

        filtered_products = products[
            products["category"].isin(category_filter)
        ].copy()

        st.dataframe(
            filtered_products.sort_values(
                "revenue",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Product Performance",
            filtered_products.to_csv(index=False),
            file_name="menu_product_performance.csv",
            mime="text/csv"
        )


# ============================================================
# 16. FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="
        text-align: center;
        color: #8994A8;
        font-size: 12px;
        padding: 10px;
    ">
        RestroDine | Restaurant Intelligence Platform

        <br>

        Data Science & AI Project

        <br>

        Synthetic demonstration data — not real restaurant results.
    </div>
    """,
    unsafe_allow_html=True
)
