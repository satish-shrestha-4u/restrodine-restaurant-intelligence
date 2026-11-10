
from pathlib import Path
import numpy as np
from collections import defaultdict
import os
import shutil
import tempfile
import json
import requests
import pandas as pd

from dateutil.easter import easter
from prophet.serialize import model_from_json


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent

MODEL_PATH = (
    ROOT / "models" / "restrodine_prophet_calendar_weather.json"
)

METADATA_PATH = (
    ROOT / "metadata" / "restrodine_prophet_calendar_weather_metadata.json"
)

OUTPUT_DIR = ROOT / "outputs"

FORECAST_HORIZON = 14

SELECTED_PROPHET_REGRESSORS = [
    "is_weekend",
    "is_holiday",
    "is_promo_day",
    "temperature_avg_c",
    "precipitation_mm",
    "is_rainy",
]

# Add planned promotion dates here (if any).
# Format: YYYY-MM-DD
PLANNED_PROMOTION_DATES = []


# ============================================================
# LOAD MODEL AND METADATA
# ============================================================

def load_forecasting_model():

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Prophet model not found: {MODEL_PATH}"
        )

    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            f"Model metadata not found: {METADATA_PATH}"
        )

    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    with open(MODEL_PATH, "r", encoding="utf-8") as file:
        model = model_from_json(file.read())

    actual_regressors = list(model.extra_regressors.keys())

    if actual_regressors != metadata["regressors"]:
        raise ValueError(
            "Model regressors do not match metadata."
        )

    if actual_regressors != SELECTED_PROPHET_REGRESSORS:
        raise ValueError(
            "Loaded model does not match the expected "
            "RestroDine forecasting configuration."
        )

    return model, metadata


# ============================================================
# NORTH RHINE-WESTPHALIA PUBLIC HOLIDAYS
# ============================================================

def get_nrw_public_holidays(year):

    easter_sunday = pd.Timestamp(easter(year))

    holidays = {
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

    return holidays


# ============================================================
# FETCH FUTURE WEATHER FROM OPEN-METEO
# ============================================================

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
        "timezone": "Europe/Berlin",
        "start_date": pd.Timestamp(start_date).date().isoformat(),
        "end_date": pd.Timestamp(end_date).date().isoformat(),
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
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

    return weather


# ============================================================
# BUILD FUTURE PROPHET FEATURES
# ============================================================

def build_selected_prophet_future_features(
    weather,
    metadata,
    planned_promotion_dates=None
):

    weather = weather.copy()

    weather["date"] = pd.to_datetime(
        weather["date"]
    ).dt.normalize()

    if weather["date"].duplicated().any():
        raise ValueError("Weather data contains duplicate dates.")

    rain_threshold = metadata["rain_threshold_mm"]

    # Weekend
    weather["is_weekend"] = (
        weather["date"].dt.dayofweek >= 5
    ).astype(int)

    # Rain
    weather["is_rainy"] = (
        weather["precipitation_mm"] >= rain_threshold
    ).astype(int)

    # NRW public holidays
    holiday_lookup = {}

    for year in weather["date"].dt.year.unique():
        holiday_lookup.update(
            get_nrw_public_holidays(int(year))
        )

    weather["holiday_name"] = weather["date"].map(
        holiday_lookup
    )

    weather["is_holiday"] = (
        weather["date"].isin(holiday_lookup.keys())
    ).astype(int)

    # Planned promotions
    if planned_promotion_dates is None:
        planned_promotion_dates = []

    promotion_dates = pd.to_datetime(
        planned_promotion_dates
    ).normalize()

    weather["is_promo_day"] = (
        weather["date"].isin(promotion_dates)
    ).astype(int)

    required_columns = (
        ["date"] + SELECTED_PROPHET_REGRESSORS
    )

    features = weather[required_columns].copy()

    if features[SELECTED_PROPHET_REGRESSORS].isna().any().any():
        raise ValueError(
            "Future weather features contain missing values."
        )

    return features


# ============================================================
# GENERATE REVENUE FORECAST
# ============================================================

def generate_revenue_forecast(
    horizon=FORECAST_HORIZON,
    start_date=None,
    planned_promotion_dates=None
):

    if horizon != 14:
        raise ValueError(
            "This RestroDine pipeline currently expects "
            "a 14-day forecast."
        )

    model, metadata = load_forecasting_model()

    # Default: tomorrow through the following 13 days.
    if start_date is None:
        start_date = (
            pd.Timestamp.today().normalize()
            + pd.Timedelta(days=1)
        )
    else:
        start_date = pd.Timestamp(start_date).normalize()

    future_dates = pd.date_range(
        start=start_date,
        periods=horizon,
        freq="D"
    )

    # Historical data ends in 2025.
    training_end = pd.Timestamp(
        metadata["training_end"]
    )

    history_gap = (future_dates.min() - training_end).days - 1

    print("Loaded existing Prophet model.")
    print("Model training end:", training_end.date())
    print("Forecast starts:", future_dates.min().date())
    print("Forecast ends:", future_dates.max().date())
    print("Days without observed revenue:", history_gap)

    if history_gap > 30:
        print(
            "WARNING: This forecast is a synthetic-data "
            "scenario with a substantial gap from training history."
        )

    # Fetch future weather.
    location = metadata["location"]

    weather = fetch_openmeteo_daily_weather(
        latitude=location["latitude"],
        longitude=location["longitude"],
        start_date=future_dates.min(),
        end_date=future_dates.max()
    )

    # Build all required model features.
    future_features = build_selected_prophet_future_features(
        weather=weather,
        metadata=metadata,
        planned_promotion_dates=planned_promotion_dates
    )

    # Validate future feature dates.
    if not future_features["date"].reset_index(drop=True).equals(
        pd.Series(future_dates, name="date")
    ):
        raise ValueError(
            "Future weather dates do not match the "
            "14-day forecast horizon."
        )

    # Prepare Prophet input.
    future = (
        future_features
        .rename(columns={"date": "ds"})
        [["ds"] + SELECTED_PROPHET_REGRESSORS]
        .copy()
    )

    # Predict using the already fitted model.
    prediction = model.predict(future)

    forecast = pd.DataFrame({
        "date": pd.to_datetime(prediction["ds"]),
        "forecast_revenue": prediction["yhat"],
        "lower_bound": prediction["yhat_lower"],
        "upper_bound": prediction["yhat_upper"],
    })

    # Quality checks.
    if len(forecast) != horizon:
        raise ValueError(
            f"Expected {horizon} forecast rows; "
            f"received {len(forecast)}."
        )

    numeric_columns = [
        "forecast_revenue",
        "lower_bound",
        "upper_bound"
    ]

    if forecast[numeric_columns].isna().any().any():
        raise ValueError("Forecast contains missing predictions.")

    if not np.isfinite(forecast[numeric_columns]).all().all():
        raise ValueError("Forecast contains non-finite values.")

    if (forecast["forecast_revenue"] < 0).any():
        raise ValueError(
            "Forecast contains negative revenue predictions. "
            "Review before using the workforce pipeline."
        )

    if (forecast["lower_bound"] > forecast["upper_bound"]).any():
        raise ValueError("Forecast uncertainty bounds are invalid.")
    if (
        (forecast["forecast_revenue"] < forecast["lower_bound"])
        | (forecast["forecast_revenue"] > forecast["upper_bound"])
    ).any():
        raise ValueError(
        "Point forecast falls outside its prediction interval."
        )

    expected_dates = pd.Series(future_dates, name="date")

    if not forecast["date"].reset_index(drop=True).equals(expected_dates):
        raise ValueError("Forecast dates are not consecutive.")

    return forecast


# ============================================================
# WORKFORCE CONFIGURATION — FROM NOTEBOOK 03
# ============================================================

WORKFORCE_DATA_DIR = ROOT / "data_clean"

WEEKLY_HOUR_CAP = {
    "Full-time": 40.0,
    "Part-time": 30.0,
    "Minijob": 12.0
}

SHIFT_DEFINITIONS = {
    "Lunch": {
        "start": "10:30",
        "end": "16:00",
        "hours": 5.5
    },
    "Dinner": {
        "start": "16:30",
        "end": "23:00",
        "hours": 6.5
    },
    "Full": {
        "start": "11:30",
        "end": "20:00",
        "hours": 8.0
    }
}

MAX_DAILY_HOURS = 10.0

STAFFING_REQUIREMENTS = {
    "Low": [
        ("Restaurant Manager", "Full", 1),
        ("Chef", "Lunch", 1),
        ("Chef", "Dinner", 1),
        ("Kitchen Assistant", "Dinner", 1),
        ("Waiter", "Lunch", 2),
        ("Waiter", "Dinner", 2),
        ("Bartender", "Dinner", 1),
        ("Dishwasher", "Dinner", 1),
    ],

    "Standard": [
        ("Restaurant Manager", "Full", 1),
        ("Chef", "Lunch", 1),
        ("Chef", "Dinner", 2),
        ("Kitchen Assistant", "Lunch", 1),
        ("Kitchen Assistant", "Dinner", 1),
        ("Waiter", "Lunch", 2),
        ("Waiter", "Dinner", 3),
        ("Bartender", "Dinner", 1),
        ("Dishwasher", "Lunch", 1),
        ("Dishwasher", "Dinner", 1),
    ],

    "High": [
        ("Restaurant Manager", "Full", 1),
        ("Assistant Manager", "Dinner", 1),
        ("Chef", "Lunch", 1),
        ("Chef", "Dinner", 2),
        ("Kitchen Assistant", "Lunch", 1),
        ("Kitchen Assistant", "Dinner", 2),
        ("Waiter", "Lunch", 3),
        ("Waiter", "Dinner", 5),
        ("Bartender", "Dinner", 2),
        ("Dishwasher", "Lunch", 1),
        ("Dishwasher", "Dinner", 1),
    ],

    "Very High": [
        ("Restaurant Manager", "Full", 1),
        ("Assistant Manager", "Dinner", 1),
        ("Chef", "Lunch", 2),
        ("Chef", "Dinner", 2),
        ("Kitchen Assistant", "Lunch", 1),
        ("Kitchen Assistant", "Dinner", 2),
        ("Waiter", "Lunch", 4),
        ("Waiter", "Dinner", 6),
        ("Bartender", "Lunch", 1),
        ("Bartender", "Dinner", 2),
        ("Dishwasher", "Lunch", 1),
        ("Dishwasher", "Dinner", 2),
    ],
}


# ============================================================
# LOAD WORKFORCE INPUT DATA
# ============================================================

def load_workforce_data():

    employees_path = (
        WORKFORCE_DATA_DIR / "employees_clean.csv"
    )

    availability_path = (
        WORKFORCE_DATA_DIR / "employee_availability_clean.csv"
    )

    daily_model_path = (
        WORKFORCE_DATA_DIR / "daily_model_table_clean.csv"
    )

    for path in [
        employees_path,
        availability_path,
        daily_model_path
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required workforce input not found: {path}"
            )

    employees = pd.read_csv(
        employees_path,
        parse_dates=["employment_start", "employment_end"]
    )

    availability = pd.read_csv(
        availability_path
    )

    daily_model = pd.read_csv(
        daily_model_path,
        parse_dates=["date"]
    )

    # Numeric conversion
    employees["hourly_cost"] = pd.to_numeric(
        employees["hourly_cost"],
        errors="coerce"
    )

    availability["day_of_week_num"] = pd.to_numeric(
        availability["day_of_week_num"],
        errors="coerce"
    )

    availability["max_hours"] = pd.to_numeric(
        availability["max_hours"],
        errors="coerce"
    )

    daily_model["revenue"] = pd.to_numeric(
        daily_model["revenue"],
        errors="coerce"
    )

    daily_model["orders"] = pd.to_numeric(
        daily_model["orders"],
        errors="coerce"
    )

    # Required employee columns
    required_employee_columns = {
        "employee_id",
        "employee_name",
        "role",
        "employment_type",
        "hourly_cost",
        "employment_start",
        "employment_end"
    }

    missing = (
        required_employee_columns
        - set(employees.columns)
    )

    if missing:
        raise ValueError(
            f"Employees data missing columns: {sorted(missing)}"
        )

    if employees["employee_id"].duplicated().any():
        raise ValueError("Duplicate employee IDs found.")

    if employees[
        ["employee_id", "role", "hourly_cost",
         "employment_start", "employment_type"]
    ].isna().any().any():
        raise ValueError(
            "Employee records contain missing required values."
        )

    if employees["hourly_cost"].lt(0).any():
        raise ValueError("Negative employee hourly costs found.")

    if employees["employment_type"].map(
        WEEKLY_HOUR_CAP
    ).isna().any():
        raise ValueError(
            "Unknown employment type or missing weekly hour cap."
        )

    required_availability_columns = {
        "employee_id",
        "day_of_week_num",
        "availability_status",
        "max_hours"
    }

    missing = (
        required_availability_columns
        - set(availability.columns)
    )

    if missing:
        raise ValueError(
            f"Availability data missing columns: {sorted(missing)}"
        )

    if availability.duplicated(
        ["employee_id", "day_of_week_num"]
    ).any():
        raise ValueError(
            "Duplicate employee/day availability records found."
        )

    if not availability["employee_id"].isin(
        employees["employee_id"]
    ).all():
        raise ValueError(
            "Availability contains unknown employee IDs."
        )

    if availability[
        ["employee_id", "day_of_week_num",
         "availability_status", "max_hours"]
    ].isna().any().any():
        raise ValueError(
            "Availability data contains missing required values."
        )

    if not availability["day_of_week_num"].between(1, 7).all():
        raise ValueError(
            "Availability weekday must be between 1 and 7."
        )

    if not availability["max_hours"].between(0, 24).all():
        raise ValueError(
            "Invalid availability maximum hours."
        )

    # Validate historical AOV inputs.
    daily_model = daily_model.dropna(
        subset=["revenue", "orders"]
    )

    valid_days = daily_model.loc[
        daily_model["orders"] > 0
    ].copy()

    if valid_days.empty:
        raise ValueError(
            "Cannot calculate historical median AOV."
        )

    if valid_days["revenue"].lt(0).any():
        raise ValueError(
            "Negative historical revenue found."
        )

    return employees, availability, daily_model


# ============================================================
# HISTORICAL MEDIAN AOV
# ============================================================

def calculate_historical_median_aov(daily_model):

    historical_aov = (
        daily_model["revenue"]
        / daily_model["orders"].replace(0, np.nan)
    ).replace(
        [np.inf, -np.inf],
        np.nan
    ).median()

    if not np.isfinite(historical_aov) or historical_aov <= 0:
        raise ValueError(
            "Historical median AOV is invalid."
        )

    return float(historical_aov)


# ============================================================
# DEMAND TIERS — FROM NOTEBOOK 03
# ============================================================

TIER_BOUNDS = [
    (60, "Low"),
    (101, "Standard"),
    (151, "High")
]


def demand_tier(orders):

    for bound, name in TIER_BOUNDS:
        if orders < bound:
            return name

    return "Very High"


# ============================================================
# STAFFING REQUIREMENTS — FROM NOTEBOOK 03
# ============================================================

def get_staffing_requirements(orders):

    tier = demand_tier(orders)

    rows = []

    for role, shift_type, count in STAFFING_REQUIREMENTS[tier]:

        rows.append({
            "role": role,
            "shift_type": shift_type,
            "required": count
        })

    return pd.DataFrame(rows)


# ============================================================
# EMPLOYEE ELIGIBILITY — FROM NOTEBOOK 03
# ============================================================

def employee_ineligibility_reason(
    employee,
    availability_row,
    date,
    shift_hours,
    weekly_hours_used,
    already_scheduled_today,
    daily_hours_used
):

    if date < employee["employment_start"]:
        return "not employed yet"

    if (
        pd.notna(employee["employment_end"])
        and date > employee["employment_end"]
    ):
        return "employment ended"

    if already_scheduled_today:
        return "already working that day"

    if daily_hours_used + shift_hours > MAX_DAILY_HOURS:
        return "daily hour cap reached"

    if availability_row is None:
        return "availability record missing"

    if availability_row.availability_status == "Unavailable":
        return "unavailable that weekday"

    if availability_row.max_hours < shift_hours:
        return "insufficient daily hours"

    if weekly_hours_used + shift_hours > employee["weekly_hour_cap"]:
        return "weekly hour cap reached"

    return None


# ============================================================
# BUILD FORECAST ROSTER AND EXPLAIN GAPS
# ============================================================

def build_forecast_roster(
    forecast_staffing,
    employees,
    availability
):

    employees_local = employees.copy()
    availability_local = availability.copy()

    employees_local["weekly_hour_cap"] = (
        employees_local["employment_type"]
        .map(WEEKLY_HOUR_CAP)
    )

    availability_lookup = {
        (row.employee_id, int(row.day_of_week_num)): row
        for row in availability_local.itertuples(index=False)
    }

    weekly_hours_used = defaultdict(float)
    daily_hours_used = defaultdict(float)
    scheduled_dates = set()

    roster_rows = []
    gap_rows = []

    for _, requirement in forecast_staffing.iterrows():

        date = pd.Timestamp(requirement["date"])

        role = requirement["role"]
        shift_type = requirement["shift_type"]

        required_count = int(requirement["required"])

        shift_info = SHIFT_DEFINITIONS[shift_type]
        shift_hours = shift_info["hours"]

        weekday_key = date.dayofweek + 1

        iso = date.isocalendar()

        role_employees = employees_local[
            employees_local["role"] == role
        ]

        candidates = []
        reason_counts = {}

        for _, employee in role_employees.iterrows():

            employee_id = employee["employee_id"]

            employee_date_key = (
                employee_id,
                date.date()
            )

            week_key = (
                employee_id,
                int(iso.year),
                int(iso.week)
            )

            availability_row = availability_lookup.get(
                (employee_id, weekday_key)
            )

            reason = employee_ineligibility_reason(
                employee=employee,
                availability_row=availability_row,
                date=date,
                shift_hours=shift_hours,
                weekly_hours_used=weekly_hours_used[week_key],
                already_scheduled_today=(
                    employee_date_key in scheduled_dates
                ),
                daily_hours_used=daily_hours_used[
                    employee_date_key
                ]
            )

            if reason is None:

                candidates.append(
                    (employee, weekly_hours_used[week_key])
                )

            else:

                reason_counts[reason] = (
                    reason_counts.get(reason, 0) + 1
                )

        # Preserve original allocation policy:
        # employees with the fewest weekly hours first.
        candidates.sort(
            key=lambda item: item[1]
        )

        selected = candidates[:required_count]

        for employee, _ in selected:

            employee_id = employee["employee_id"]

            employee_date_key = (
                employee_id,
                date.date()
            )

            week_key = (
                employee_id,
                int(iso.year),
                int(iso.week)
            )

            weekly_hours_used[week_key] += shift_hours

            daily_hours_used[employee_date_key] += shift_hours

            scheduled_dates.add(employee_date_key)

            roster_rows.append({
                "date": date,
                "role": role,
                "shift_type": shift_type,
                "employee_id": employee_id,
                "employee_name": employee["employee_name"],
                "employment_type": employee["employment_type"],
                "start_time": shift_info["start"],
                "end_time": shift_info["end"],
                "hours": shift_hours,
                "hourly_cost": employee["hourly_cost"],
                "labour_cost": (
                    shift_hours * employee["hourly_cost"]
                )
            })

        unfilled_count = required_count - len(selected)

        if unfilled_count > 0:

            reason_parts = []

            if role_employees.empty:

                reason_parts.append(
                    "no employees with this role"
                )

            elif candidates:

                reason_parts.append(
                    f"only {len(candidates)} eligible employee(s) "
                    f"for {required_count} required position(s)"
                )

            reason_parts.extend(
                f"{reason} ({count} employee(s))"
                for reason, count in reason_counts.items()
            )

            gap_rows.append({
                "date": date,
                "weekday": date.day_name(),
                "role": role,
                "shift_type": shift_type,
                "hours": shift_hours,
                "required": required_count,
                "assigned": len(selected),
                "unfilled": unfilled_count,
                "reason": "; ".join(reason_parts)
            })

    roster_columns = [
        "date", "role", "shift_type", "employee_id",
        "employee_name", "employment_type", "start_time",
        "end_time", "hours", "hourly_cost", "labour_cost"
    ]

    gap_columns = [
        "date", "weekday", "role", "shift_type",
        "hours", "required", "assigned", "unfilled", "reason"
    ]

    roster = pd.DataFrame(
        roster_rows,
        columns=roster_columns
    )

    gaps = pd.DataFrame(
        gap_rows,
        columns=gap_columns
    )

    return roster, gaps


# ============================================================
# BUILD ALL WORKFORCE OUTPUTS FROM NEW REVENUE FORECAST
# ============================================================

def generate_workforce_outputs(revenue_forecast):

    employees, availability, daily_model = (
        load_workforce_data()
    )

    forecast = revenue_forecast.copy()

    forecast["date"] = pd.to_datetime(
        forecast["date"]
    ).dt.normalize()

    forecast = forecast.sort_values(
        "date"
    ).reset_index(drop=True)

    if len(forecast) != FORECAST_HORIZON:
        raise ValueError(
            "Workforce planning requires exactly 14 forecast dates."
        )

    if forecast["date"].duplicated().any():
        raise ValueError(
            "Revenue forecast contains duplicate dates."
        )

    expected_dates = pd.date_range(
        start=forecast["date"].min(),
        periods=FORECAST_HORIZON,
        freq="D"
    )

    if not forecast["date"].equals(
        pd.Series(expected_dates)
    ):
        raise ValueError(
            "Revenue forecast dates must be consecutive."
        )

    if (
        forecast["forecast_revenue"].isna().any()
        or not np.isfinite(
            forecast["forecast_revenue"]
        ).all()
        or forecast["forecast_revenue"].lt(0).any()
    ):
        raise ValueError(
            "Revenue forecast contains invalid values."
        )

    # --------------------------------------------------------
    # 1. Revenue -> expected orders
    # --------------------------------------------------------

    historical_aov = calculate_historical_median_aov(
        daily_model
    )

    forecast["expected_orders"] = (
        forecast["forecast_revenue"]
        / historical_aov
    ).round().astype(int)

    # --------------------------------------------------------
    # 2. Forecast demand features
    # --------------------------------------------------------

    forecast["day_of_week"] = (
        forecast["date"].dt.day_name()
    )

    forecast["is_weekend"] = (
        forecast["date"].dt.dayofweek >= 5
    ).astype(int)

    forecast["demand_tier"] = (
        forecast["expected_orders"]
        .apply(demand_tier)
    )

    # --------------------------------------------------------
    # 3. Role and shift requirements
    # --------------------------------------------------------

    staffing_rows = []

    for _, row in forecast.iterrows():

        requirements = get_staffing_requirements(
            row["expected_orders"]
        )

        for _, requirement in requirements.iterrows():

            staffing_rows.append({
                "date": row["date"],
                "expected_orders": row["expected_orders"],
                "demand_tier": row["demand_tier"],
                "role": requirement["role"],
                "shift_type": requirement["shift_type"],
                "required": requirement["required"]
            })

    forecast_staffing = pd.DataFrame(
        staffing_rows
    )

    # --------------------------------------------------------
    # 4. Daily staffing requirements
    # --------------------------------------------------------

    daily_required_staff = (
        forecast_staffing
        .groupby("date", as_index=False)
        .agg(
            expected_orders=("expected_orders", "first"),
            demand_tier=("demand_tier", "first"),
            required_staff=("required", "sum")
        )
    )

    # --------------------------------------------------------
    # 5. Allocate employees
    # --------------------------------------------------------

    recommended_roster, staffing_gaps = (
        build_forecast_roster(
            forecast_staffing,
            employees,
            availability
        )
    )

    # --------------------------------------------------------
    # 6. Staffing coverage
    # --------------------------------------------------------

    assigned_staffing = (
        recommended_roster
        .groupby(
            ["date", "role", "shift_type"]
        )
        .size()
        .reset_index(name="assigned")
    )

    staffing_coverage = forecast_staffing.merge(
        assigned_staffing,
        on=["date", "role", "shift_type"],
        how="left"
    )

    staffing_coverage["assigned"] = (
        staffing_coverage["assigned"]
        .fillna(0)
        .astype(int)
    )

    staffing_coverage["shortfall"] = (
        staffing_coverage["required"]
        - staffing_coverage["assigned"]
    )

    staffing_coverage["coverage_status"] = np.where(
        staffing_coverage["shortfall"] > 0,
        "Under-covered",
        "Covered"
    )

    # --------------------------------------------------------
    # 7. Daily forecast labour
    # --------------------------------------------------------

    daily_forecast_labour = (
        recommended_roster
        .groupby("date")
        .agg(
            scheduled_employees=(
                "employee_id", "nunique"
            ),
            labour_hours=("hours", "sum"),
            labour_cost=("labour_cost", "sum")
        )
        .reset_index()
    )

    # Include all forecast dates, including days with
    # no assigned employees.
    daily_forecast_labour = (
        pd.DataFrame({"date": expected_dates})
        .merge(
            daily_forecast_labour,
            on="date",
            how="left"
        )
    )

    daily_forecast_labour[
        ["scheduled_employees", "labour_hours", "labour_cost"]
    ] = daily_forecast_labour[
        ["scheduled_employees", "labour_hours", "labour_cost"]
    ].fillna(0)

    # --------------------------------------------------------
    # 8. Final workforce forecast
    # --------------------------------------------------------

    workforce_forecast = (
        daily_required_staff
        .merge(
            daily_forecast_labour,
            on="date",
            how="left"
        )
        .merge(
            forecast[
                ["date", "forecast_revenue"]
            ],
            on="date",
            how="left"
        )
    )

    workforce_forecast["labour_cost_pct_revenue"] = (
        workforce_forecast["labour_cost"]
        / workforce_forecast["forecast_revenue"].replace(0, np.nan)
        * 100
    )

    workforce_forecast["forecast_orders_per_labour_hour"] = (
        workforce_forecast["expected_orders"]
        / workforce_forecast["labour_hours"].replace(0, np.nan)
    )

    # --------------------------------------------------------
    # 9. Final constraint and reconciliation checks
    # --------------------------------------------------------

    if not np.isclose(
        staffing_gaps["unfilled"].sum(),
        staffing_coverage["shortfall"].sum()
    ):
        raise AssertionError(
            "Staffing gaps do not reconcile with coverage shortfalls."
        )

    if recommended_roster.duplicated(
        ["date", "employee_id"]
    ).any():
        raise AssertionError(
            "An employee has been assigned more than once per day."
        )

    if not recommended_roster["employee_id"].isin(
        employees["employee_id"]
    ).all():
        raise AssertionError(
            "Unknown employee found in recommended roster."
        )

    # Weekly hours
    if not recommended_roster.empty:

        weekly = recommended_roster.copy()

        iso = weekly["date"].dt.isocalendar()

        weekly["iso_year"] = iso.year.astype(int)
        weekly["iso_week"] = iso.week.astype(int)

        weekly_hours = (
            weekly.groupby(
                ["employee_id", "iso_year", "iso_week"]
            )
            .agg(
                hours=("hours", "sum"),
                employment_type=("employment_type", "first")
            )
            .reset_index()
        )

        weekly_hours["weekly_cap"] = (
            weekly_hours["employment_type"]
            .map(WEEKLY_HOUR_CAP)
        )

        if not (
            weekly_hours["hours"]
            <= weekly_hours["weekly_cap"]
        ).all():
            raise AssertionError(
                "Weekly contract hour limit exceeded."
            )

    # Daily hours
    daily_employee_hours = (
        recommended_roster
        .groupby(["date", "employee_id"])["hours"]
        .sum()
    )

    if not daily_employee_hours.le(
        MAX_DAILY_HOURS
    ).all():
        raise AssertionError(
            "Daily employee hour limit exceeded."
        )

    # Labour cost
    if not np.isclose(
        recommended_roster["labour_cost"],
        recommended_roster["hours"]
        * recommended_roster["hourly_cost"]
    ).all():
        raise AssertionError(
            "Roster labour cost calculation failed."
        )

    # --------------------------------------------------------
    # Return outputs without saving them yet
    # --------------------------------------------------------

    return {
        "forecast": forecast,
        "forecast_staffing": forecast_staffing,
        "workforce_forecast": workforce_forecast,
        "recommended_roster": recommended_roster,
        "staffing_coverage": staffing_coverage,
        "staffing_gaps": staffing_gaps,
        "historical_median_aov": historical_aov
    }


# ============================================================
# SAVE FORECAST OUTPUTS
# ============================================================

def save_forecast_outputs(workforce):
    """
    Save all revenue and workforce forecast outputs.

    Files are staged before replacement. Existing files are
    backed up so a failed replacement can be rolled back.
    """

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_files = {
        "revenue_forecast_next_14_days.csv":
            workforce["forecast"],

        "workforce_forecast_next_14_days.csv":
            workforce["workforce_forecast"],

        "recommended_roster.csv":
            workforce["recommended_roster"],

        "staffing_coverage.csv":
            workforce["staffing_coverage"],

        "staffing_gaps.csv":
            workforce["staffing_gaps"],
    }

    with tempfile.TemporaryDirectory(dir=OUTPUT_DIR) as temp_dir:

        staged_dir = Path(temp_dir) / "staged"
        backup_dir = Path(temp_dir) / "backups"

        staged_dir.mkdir()
        backup_dir.mkdir()

        # 1. Stage all CSV files first
        for filename, df in output_files.items():

            # An empty staffing-gaps file is valid:
            # it means there are no unfilled positions.
            if df.empty and filename != "staffing_gaps.csv":
                raise ValueError(
                    f"Cannot save empty output: {filename}"
                )

            df.to_csv(
                staged_dir / filename,
                index=False
            )

        # 2. Back up existing files
        existing_files = []

        for filename in output_files:

            destination = OUTPUT_DIR / filename

            if destination.exists():

                shutil.copy2(
                    destination,
                    backup_dir / filename
                )

                existing_files.append(filename)

        replaced_files = []

        try:

            # 3. Replace existing outputs
            for filename in output_files:

                os.replace(
                    staged_dir / filename,
                    OUTPUT_DIR / filename
                )

                replaced_files.append(filename)

        except Exception:

            # 4. Roll back if replacement fails
            for filename in replaced_files:

                destination = OUTPUT_DIR / filename

                if filename in existing_files:

                    shutil.copy2(
                        backup_dir / filename,
                        destination
                    )

                elif destination.exists():

                    destination.unlink()

            raise

    print("\nFORECAST OUTPUTS SAVED")
    print("=" * 60)

    for filename in output_files:
        print(f"Saved: {filename}")


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # 1. Generate revenue forecast
    # --------------------------------------------------------

    revenue_forecast = generate_revenue_forecast()

    print("\nREVENUE FORECAST")

    print(
        revenue_forecast.round(2).to_string(index=False)
    )

    # --------------------------------------------------------
    # 2. Generate workforce outputs
    # --------------------------------------------------------

    workforce = generate_workforce_outputs(
        revenue_forecast
    )

    # --------------------------------------------------------
    # 3. Final output validation
    # --------------------------------------------------------

    outputs_to_validate = {
        "revenue_forecast": workforce["forecast"],
        "workforce_forecast": workforce["workforce_forecast"],
        "recommended_roster": workforce["recommended_roster"],
        "staffing_coverage": workforce["staffing_coverage"],
        "staffing_gaps": workforce["staffing_gaps"],
    }

    print("\nFINAL OUTPUT VALIDATION")
    print("=" * 60)

    for name, df in outputs_to_validate.items():

        print(f"\n{name}")
        print(f"Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")

        # Empty staffing gaps are valid.
        if df.empty and name != "staffing_gaps":
            raise ValueError(
                f"{name} is empty."
            )

        if df.isna().all(axis=1).any():
            raise ValueError(
                f"{name} contains completely empty rows."
            )

        print("Status: PASSED")

    print("\nAll output DataFrames passed basic validation.")

    # --------------------------------------------------------
    # 4. Additional workforce validation
    # --------------------------------------------------------

    roster = workforce["recommended_roster"].copy()

    employees, availability, _ = load_workforce_data()

    # Availability validation
    roster["weekday_num"] = (
        roster["date"].dt.dayofweek + 1
    )

    availability_check = roster.merge(
        availability[
            [
                "employee_id",
                "day_of_week_num",
                "availability_status",
                "max_hours"
            ]
        ],
        left_on=["employee_id", "weekday_num"],
        right_on=["employee_id", "day_of_week_num"],
        how="left"
    )

    print("\nAVAILABILITY VALIDATION")

    print(
        availability_check["availability_status"]
        .value_counts(dropna=False)
    )

    availability_check["hours_exceed_availability"] = (
        availability_check["hours"]
        > availability_check["max_hours"]
    )

    print(
        "Shifts exceeding availability:",
        availability_check["hours_exceed_availability"].sum()
    )

    # Limited availability assignments
    print("\nLIMITED AVAILABILITY ASSIGNMENTS")

    print(
        availability_check.loc[
            availability_check["availability_status"] == "Limited",
            [
                "date",
                "employee_name",
                "role",
                "shift_type",
                "hours",
                "max_hours"
            ]
        ].to_string(index=False)
    )

    # Weekly hour limits
    iso = roster["date"].dt.isocalendar()

    roster["iso_year"] = iso.year.astype(int)
    roster["iso_week"] = iso.week.astype(int)

    weekly = (
        roster.groupby(
            ["employee_id", "iso_year", "iso_week"]
        )
        .agg(
            weekly_hours=("hours", "sum"),
            employment_type=("employment_type", "first")
        )
        .reset_index()
    )

    weekly["weekly_limit"] = (
        weekly["employment_type"]
        .map(WEEKLY_HOUR_CAP)
    )

    weekly["exceeds_limit"] = (
        weekly["weekly_hours"] > weekly["weekly_limit"]
    )

    print("\nWEEKLY HOURS VALIDATION")

    print(
        "Employees exceeding weekly limits:",
        weekly["exceeds_limit"].sum()
    )

    print(
        weekly.loc[
            weekly["exceeds_limit"]
        ].to_string(index=False)
    )

    # Duplicate employee assignments per day
    duplicates = roster.duplicated(
        ["date", "employee_id"]
    ).sum()

    print("\nDUPLICATE ASSIGNMENTS:", duplicates)

    # --------------------------------------------------------
    # 5. Display workforce results
    # --------------------------------------------------------

    print("\nWORKFORCE FORECAST")

    print(
        workforce["workforce_forecast"]
        .round(2)
        .to_string(index=False)
    )

    print("\nRECOMMENDED ROSTER")

    print(
        workforce["recommended_roster"]
        .head(20)
        .to_string(index=False)
    )

    print("\nSTAFFING GAPS")

    print(
        workforce["staffing_gaps"]
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # 6. Pipeline summary
    # --------------------------------------------------------

    print("\nPIPELINE SUMMARY")
    print("-" * 50)

    print(
        "Historical median AOV:",
        f"€{workforce['historical_median_aov']:.2f}"
    )

    print(
        "Expected orders:",
        workforce["workforce_forecast"]["expected_orders"].sum()
    )

    print(
        "Required staff positions:",
        workforce["workforce_forecast"]["required_staff"].sum()
    )

    print(
        "Assigned employee shifts:",
        len(workforce["recommended_roster"])
    )

    print(
        "Unfilled positions:",
        workforce["staffing_gaps"]["unfilled"].sum()
    )

    print(
        "Forecast labour cost:",
        f"€{workforce['workforce_forecast']['labour_cost'].sum():,.2f}"
    )

    print("\nAll workforce calculations completed.")

    # --------------------------------------------------------
    # 7. Save all five outputs
    # --------------------------------------------------------

    save_forecast_outputs(workforce)
