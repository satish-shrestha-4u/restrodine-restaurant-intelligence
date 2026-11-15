"""
RestroDine | Restaurant Intelligence & Weather-Aware Revenue Forecasting
=========================================================================
A multi-page Streamlit analytics application for a (synthetic) restaurant in
North Rhine-Westphalia, Germany.

Run:
    streamlit run app.py

Expected project layout (next to this file):
    data_clean/   *_clean.csv   cleaned operational tables
    outputs/      *.csv         analytical outputs (forecast, roster, RFM, menu, ...)
    models/       *.json        optional model metadata (Prophet) and summaries
                                (the app also finds these in outputs/ or the project root)

Optional: create .streamlit/config.toml to force the light theme this UI is designed for:
    [theme]
    base = "light"
    primaryColor = "#2F55D4"

All project data is synthetic. Forecasts and recommendations are analytical
estimates, not operational guarantees.
"""
from __future__ import annotations
from scipy import stats

import json # Reads model metadata and JSON files
from dataclasses import dataclass # Defines structured objects such as Context
from pathlib import Path # Handles project directories and file paths
from typing import Optional
from xml.parsers.expat import model # Type hints for optional values
import statsmodels.api as sm
import numpy as np # Numerical operations and NaN handling
import pandas as pd # Data manipulation and analysis
import plotly.express as px # Quick interactive charts
import plotly.graph_objects as go # Custom interactive charts
import streamlit as st # Web app framework for building interactive dashboards

from forecast_pipeline import (
    generate_revenue_forecast,
    generate_workforce_outputs,
    save_forecast_outputs,
)

# =============================================================================
# Configuration
# =============================================================================

ROOT = Path(__file__).resolve().parent # It automatically identifies the directory containing app.py
DATA_DIR = ROOT / "data_clean"
OUTPUT_DIR = ROOT / "outputs"
META_DIRS = [ROOT / "metadata", ROOT / "models", OUTPUT_DIR, DATA_DIR, ROOT]

APP_NAME = "RestroDine"
CURRENCY = "€"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEAL_ORDER = ["Lunch", "Afternoon", "Dinner"]

# =============================================================================
# Forest & Sage Design System
# =============================================================================

C = {
    # Main colours
    "ink": "#252B29",
    "muted": "#68766B",
    "line": "#DCE8D9",
    "paper": "#F4F6EF",
    "white": "#FFFFFF",

    # Brand colours
    "navy": "#172116",
    "blue": "#376B42",
    "blue_soft": "#49A17E",
    "teal": "#398D70",

    # Supporting colours
    "amber": "#D99A38",
    "red": "#C65B55",
    "grey": "#9AA79A",

    # Explicit design tokens
    "forest": "#376B42",
    "emerald": "#398D70",
    "emerald_light": "#49A17E",
    "sage": "#DCE8D9",
}

# Sentiment colours
SENTIMENT_COLORS = {
    "Positive": C["teal"],
    "Neutral": C["grey"],
    "Negative": C["red"],
}

# Menu engineering colours
CLASS_COLORS = {
    "Star": C["teal"],
    "Plowhorse": C["amber"],
    "Puzzle": C["blue"],
    "Dog": C["red"],
}

# General chart colour sequence
CATEGORY_SEQ = [
    C["forest"],
    C["emerald"],
    C["amber"],
    C["red"],
    C["blue_soft"],
    C["grey"],
    "#8E6BD1",
]

WORKFORCE_PALETTE = px.colors.qualitative.Pastel
st.set_page_config(
    page_title=f"{APP_NAME} | Restaurant Intelligence",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlit renamed `use_container_width` to `width="stretch"` in 1.50.
try:
    _major, _minor = (int(p) for p in st.__version__.split(".")[:2])
    STRETCH = {"width": "stretch"} if (_major, _minor) >= (1, 50) else {"use_container_width": True}
except Exception:  # pragma: no cover
    STRETCH = {"use_container_width": True}



# =============================================================================
# Styling — Forest & Sage Design System
# =============================================================================

st.markdown(
    """
    <style>

    /* -------------------------------------------------
       1. GLOBAL COLOUR VARIABLES
    ------------------------------------------------- */

    :root {
        --forest: #172116;
        --primary: #376B42;
        --emerald: #398D70;
        --emerald-light: #49A17E;
        --sage: #DCE8D9;
        --paper: #F4F6EF;
        --white: #FFFFFF;
        --ink: #252B29;
        --muted: #68766B;
        --line: #DCE8D9;
    }

    /* -------------------------------------------------
       2. APPLICATION BACKGROUND & TYPOGRAPHY
    ------------------------------------------------- */

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont,
            "Segoe UI", Inter, Roboto, Arial, sans-serif;
    }

    .stApp {
        background: var(--paper);
        color: var(--ink);
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    footer {
        visibility: hidden;
    }

    h1, h2, h3, h4 {
        color: var(--ink);
        letter-spacing: -0.02em;
        font-weight: 700;
    }

    h3 {
        font-size: 1.02rem !important;
        margin-bottom: 0.15rem !important;
    }

    /* -------------------------------------------------
       3. SIDEBAR
    ------------------------------------------------- */

    [data-testid="stSidebar"] {
        background: var(--forest);
    }

    [data-testid="stSidebar"] * {
        color: #E8EFE8;
    }

    [data-testid="stSidebar"] hr {
        border-color: #344536;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        padding: 9px 12px;
        border-radius: 9px;
        margin-bottom: 4px;
        transition: background 0.2s ease;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: #293C2B;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: var(--primary);
        color: #FFFFFF;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] * {
        color: var(--ink);
    }

    [data-testid="stSidebar"] input {
        color: var(--ink);
    }

    /* -------------------------------------------------
       4. KPI METRIC CARDS
    ------------------------------------------------- */

    /* KPI cards — Forest & Sage */
    [data-testid="stMetric"] {
        background: #F0F4EB;
        border: 1px solid #DCE8D9;
        border-left: 4px solid #376B42;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(23, 33, 22, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 14px rgba(23, 33, 22, 0.09);
    }

    /* KPI label */
    [data-testid="stMetricLabel"] {
        color: #526B54 !important;
    }

    /* KPI value */
    [data-testid="stMetricValue"] {
        color: #233B2A !important;
    }

    /* KPI delta — positive and negative */
    [data-testid="stMetricDelta"] {
        font-weight: 600;
    }

    /* -------------------------------------------------
       5. BUTTONS
    ------------------------------------------------- */

    .stButton > button,
    .stDownloadButton > button {
        background: var(--primary);
        color: #FFFFFF;
        border: 1px solid var(--primary);
        border-radius: 9px;
        padding: 0.45rem 1rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: var(--forest);
        border-color: var(--forest);
        color: #FFFFFF;
    }

    .stButton > button:focus,
    .stDownloadButton > button:focus {
        border-color: var(--emerald);
        color: #FFFFFF;
        box-shadow: 0 0 0 2px rgba(57, 141, 112, 0.2);
    }

    /* -------------------------------------------------
       6. CHARTS & DATA TABLES
    ------------------------------------------------- */

    div[data-testid="stPlotlyChart"],
    div[data-testid="stDataFrame"] {
        background: var(--white);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 8px;
        box-shadow: 0 2px 5px rgba(23, 33, 22, 0.04);
    }

    /* -------------------------------------------------
    7. TABS
    ------------------------------------------------- */

    .stTabs [data-baseweb="tab-list"] {
        gap: 12px !important;
        border-bottom: none !important;
        margin-bottom: 18px !important;
    }

    .stTabs button[data-baseweb="tab"] {
        background: #E5EDE3 !important;
        border: 1px solid #D2DFD0 !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        min-height: 48px !important;
        transition: all 0.2s ease-in-out !important;
    }

    .stTabs button[data-baseweb="tab"] p {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #355B40 !important;
        margin: 0 !important;
    }

    .stTabs button[data-baseweb="tab"]:hover {
        background: #D5E5D4 !important;
        border-color: #376B42 !important;
    }

    .stTabs button[data-baseweb="tab"][aria-selected="true"] {
        background: #376B42 !important;
        border: 1px solid #376B42 !important;
    }

    .stTabs button[data-baseweb="tab"][aria-selected="true"] p {
        color: #FFFFFF !important;
        font-weight: 800 !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    /* -------------------------------------------------
       8. HERO HEADER
    ------------------------------------------------- */

    .hero {
        background: linear-gradient(
            115deg,
            var(--forest) 0%,
            var(--primary) 60%,
            var(--emerald) 100%
        );
        padding: 24px 28px;
        border-radius: 16px;
        color: #FFFFFF;
        margin: 2px 0 18px 0;
        box-shadow: 0 8px 24px rgba(23, 33, 22, 0.12);
    }

    .hero .kicker {
        color: #C8E1CC;
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }

    .hero .title {
        color: #FFFFFF;
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin: 4px 0 2px 0;
    }

    .hero .copy {
        color: #E3EFE5;
        font-size: 0.88rem;
    }

    /* -------------------------------------------------
       9. INFORMATION & WARNING BOXES
    ------------------------------------------------- */

    .note {
        background: #FFF7E8;
        border: 1px solid #F0DDAF;
        color: #76551B;
        padding: 11px 15px;
        border-radius: 10px;
        font-size: 0.82rem;
        margin: 8px 0;
    }

    .info {
        background: #EAF2EA;
        border: 1px solid #D0E2D0;
        color: #31583A;
        padding: 11px 15px;
        border-radius: 10px;
        font-size: 0.82rem;
        margin: 8px 0;
    }

    .section-note {
        color: var(--muted);
        font-size: 0.8rem;
        margin: -2px 0 10px 0;
    }

    /* -------------------------------------------------
       10. BUSINESS SIGNAL CARDS
    ------------------------------------------------- */

    .signal {
        background: var(--white);
        border: 1px solid var(--line);
        border-left: 4px solid var(--primary);
        border-radius: 10px;
        padding: 11px 14px;
        margin-bottom: 10px;
    }

    .signal .s-title {
        color: var(--muted);
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .signal .s-text {
        color: var(--ink);
        font-size: 0.88rem;
        margin-top: 3px;
        line-height: 1.4;
    }

    .signal.warn {
        border-left-color: #D99A38;
    }

    .signal.good {
        border-left-color: var(--emerald);
    }

    .signal.risk {
        border-left-color: #C65B55;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# Data access
# =============================================================================

MISSING: list[str] = [] # creates an empty list for tracking files that are missing or cannot be read
@st.cache_data(show_spinner=False) # caches the results of the function to avoid reloading the same data multiple times

# Reads CSV files and converts specified date columns
def _read_csv(path: str, mtime: float, date_cols: tuple[str, ...]) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

# Checks whether a file exists and loads it safely
def load(folder: Path, name: str, dates: tuple[str, ...] = ()) -> pd.DataFrame:
    path = folder / name
    if not path.exists():
        MISSING.append(f"{folder.name}/{name}")
        return pd.DataFrame()
    try:
        return _read_csv(str(path), path.stat().st_mtime, dates)
    except Exception as exc:  # corrupt or unreadable file should not crash the app
        MISSING.append(f"{folder.name}/{name} (unreadable: {exc})")
        return pd.DataFrame()

# Loads cleaned data tables from the `data_clean` directory 
def data(name: str, *dates: str) -> pd.DataFrame:
    return load(DATA_DIR, name, tuple(dates))

# Loads analytical outputs from the `outputs` directory
def output(name: str, *dates: str) -> pd.DataFrame:
    return load(OUTPUT_DIR, name, tuple(dates))

@st.cache_data(show_spinner=False) # caches the results of the function to avoid reloading the same data multiple times

# Reads JSON files and returns a dictionary
def _read_json(path: str, mtime: float) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

# Loads metadata from JSON files in the `metadata`, `models`, `outputs`, or `data_clean` directories
def meta(name: str) -> dict:
    for folder in META_DIRS:
        path = folder / name
        if path.exists():
            try:
                return _read_json(str(path), path.stat().st_mtime)
            except Exception:
                return {}
    return {}


# =============================================================================
# Formatting & helpers
# =============================================================================

# Formats euro values using compact notation for large amounts
def money(v, d: int = 0) -> str:
    if v is None or pd.isna(v):
        return "—"

    value = float(v)
    sign = "-" if value < 0 else ""
    value = abs(value)

    if value >= 1_000_000_000:
        return f"{sign}€{value / 1_000_000_000:.1f}B"

    elif value >= 1_000_000:
        return f"{sign}€{value / 1_000_000:.1f}M"

    return f"{sign}€{value:,.{d}f}"


# Formats a numeric value as an integer with thousands separators, without decimal places
def integer(v) -> str:
    return "—" if v is None or pd.isna(v) else f"{v:,.0f}"

# Formats a numeric value as a percentage with optional decimal places
def pct(v, d: int = 1) -> str:
    return "—" if v is None or pd.isna(v) else f"{v:,.{d}f}%"

# Safely divides two numbers, returning NaN if the denominator is None, NaN, or zero
def safe_div(a, b):
    return np.nan if b is None or pd.isna(b) or b == 0 else a / b

# Calculates the percentage change between two values, returning None if the previous value is None, NaN, or zero
def change_pct(cur, prev) -> Optional[float]:
    if prev is None or pd.isna(prev) or prev == 0 or cur is None or pd.isna(cur):
        return None
    return (cur / prev - 1) * 100

# Convert the numerical percentage change into a readable KPI indicator 
def delta_label(chg: Optional[float]) -> Optional[str]:
    return None if chg is None else f"{chg:+.1f}%"

# Checks if a DataFrame is not empty and contains the specified columns
def has_cols(df: pd.DataFrame, *cols: str) -> bool:
    return (not df.empty) and set(cols).issubset(df.columns)

# Creates a dictionary mapping KPI metrics to their numeric values, handling missing or non-numeric values gracefully
def kpi_lookup(df: pd.DataFrame) -> dict:
    if not has_cols(df, "Metric", "Value"):
        return {}
    return dict(zip(df["Metric"], pd.to_numeric(df["Value"], errors="coerce")))

# Creates a visually appealing hero section with a kicker, title, and copy text
def hero(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="hero"><div class="kicker">{kicker}</div><div class="title">{title}</div>'
        f'<div class="copy">{copy}</div></div>',
        unsafe_allow_html=True,
    )

# Creates a section header with an optional note, using Markdown for styling
def section(title: str, note: Optional[str] = None) -> None:
    st.markdown(f"### {title}")
    if note:
        st.markdown(f'<div class="section-note">{note}</div>', unsafe_allow_html=True)

# Creates a callout box with a specified text and kind (e.g., info, note, warning), using Markdown for styling
def callout(text: str, kind: str = "info") -> None:
    st.markdown(f'<div class="{kind}">{text}</div>', unsafe_allow_html=True)

# Creates a row of KPI metric cards, each displaying a label, value, and delta, with optional additional keyword arguments for customization
def kpis(items: list[tuple]) -> None:
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value, delta = item[:3]
        kwargs = item[3] if len(item) > 3 else {}
        col.metric(label, value, delta, **kwargs)

# Displays a consistent informational message when a particular dataset or analysis is unavailable
def unavailable(what: str) -> None:
    st.info(f"{what} is not available for the current selection or its source file is missing.")

# Applies a consistent visual style to Plotly figures, including layout, colors, fonts, and hover behavior
def style(fig: go.Figure, height: int = 340, unified: bool = True) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=14, r=14, t=30, b=14),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Segoe UI, Inter, Arial, sans-serif", color="#34445B", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        hoverlabel=dict(bgcolor=C["ink"], font_color="white"),
        hovermode="x unified" if unified else "closest",
        colorway=CATEGORY_SEQ,
    )
    fig.update_xaxes(showgrid=False, linecolor=C["line"], tickfont=dict(color=C["muted"]))
    fig.update_yaxes(gridcolor="#EDF1F6", zeroline=False, tickfont=dict(color=C["muted"]))
    return fig

# Displays a Plotly figure in Streamlit with a consistent style, height, and hover behavior, while disabling the mode bar and allowing for optional key assignment
def chart(fig: go.Figure, height: int = 340, unified: bool = True, key: Optional[str] = None) -> None:
    st.plotly_chart(style(fig, height, unified), config={"displayModeBar": False}, key=key, **STRETCH)

# Displays a Pandas DataFrame in Streamlit with a consistent height, optional column configuration, and a message when the DataFrame is empty
def table(df: pd.DataFrame, height: int = 360, column_config: Optional[dict] = None) -> None:
    if df.empty:
        st.info("No records match the current selection.")
        return
    st.dataframe(df, height=height, hide_index=True, column_config=column_config, **STRETCH)

# Provides a download button for a Pandas DataFrame in Streamlit, allowing users to download the DataFrame as a CSV file with a specified label, filename, and key. If the DataFrame is empty, the function does nothing.
def download(df: pd.DataFrame, label: str, filename: str, key: str) -> None:
    if df.empty:
        return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), filename, "text/csv", key=key)

# Creates a reusable Streamlit column configuration for displaying monetary values in data tables.
def money_col(label: str, d: int = 0):
    return st.column_config.NumberColumn(label, format=f"{CURRENCY}%.{d}f")

# Creates a reusable Streamlit column configuration for displaying percentage values in data tables.
def pct_col(label: str, d: int = 1):
    return st.column_config.NumberColumn(label, format=f"%.{d}f%%")

# Creates a reusable Streamlit column configuration for displaying numeric values in data tables.
def num_col(label: str, d: int = 0):
    return st.column_config.NumberColumn(label, format=f"%.{d}f")


# =============================================================================
# Load core tables
# =============================================================================

orders = data("orders_clean.csv", "order_datetime", "order_date")
if orders.empty or not has_cols(orders, "order_id", "order_date", "order_total"):
    st.error(
        "**Core data not found.** Place `orders_clean.csv` and the other cleaned tables in "
        f"`{DATA_DIR.name}/` and the analytical outputs in `{OUTPUT_DIR.name}/`, next to `app.py`."
    )
    st.stop()

orders = orders.dropna(subset=["order_date"]).copy()
orders["weekday"] = orders["order_date"].dt.day_name()
if "order_datetime" in orders:
    orders["hour"] = orders["order_datetime"].dt.hour

items = data("order_items_clean.csv")
products = data("products_clean.csv")
payments = data("payments_clean.csv")
shifts_data = data("shifts_clean.csv", "shift_date")
employees = data("employees_clean.csv", "employment_start", "employment_end")
employee_availability = data("employee_availability_clean.csv")
reviews = data("reviews_clean.csv", "review_date")
promotions = data("promotions_clean.csv", "start_date", "end_date")
daily_ctx = data("daily_model_table_clean.csv", "date")
daily_hist = data("daily_revenue_clean.csv", "date")

DATA_MIN, DATA_MAX = orders["order_date"].min().date(), orders["order_date"].max().date()

# =============================================================================
# Sidebar: navigation and global filters
# =============================================================================

# List of pages in the Streamlit app, each representing a different aspect of restaurant intelligence and analytics 
PAGES = [
    "Executive Overview", # Overall restaurant performance
    "Revenue & Forecast", # Revenue trends and future projections
    "Workforce Planning", # Staffing and labor cost analysis
    "Customer Intelligence", # Customer behavior and feedback analysis
    "Menu Performance", # Menu item sales and profitability analysis
    "Data & Methodology", # Data sources, cleaning, and analytical methods
]

# Sidebar header with the app name and description, using Markdown for styling 
st.sidebar.markdown(
    f"""
    <div style="padding:6px 2px 14px 2px">
      <div style="font-size:2.5rem;font-weight:800;letter-spacing:-.03em">🍽️ {APP_NAME}</div>
      <div style="font-size:1.0rem;color:#9FB0CC;letter-spacing:.14em;text-transform:uppercase;margin-top:3px">Restaurant intelligence</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar radio buttons for page navigation, allowing users to switch between different pages of the app
page = st.sidebar.radio("Navigation", PAGES, label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.markdown("**Historical filters**")
st.sidebar.caption("Apply to trading, revenue and live menu views.")

# Sidebar date input for selecting a custom date range, with validation to ensure the selected dates are within the available data range
# This function does not display anything. It calculates and returns date ranges. 

def preset_range(choice: str) -> tuple:
    last = DATA_MAX
    year_end = pd.Timestamp(last).year

    presets = {
        "Full history": (DATA_MIN, last),

        f"Calendar {year_end}": (
            max(DATA_MIN, pd.Timestamp(year_end, 1, 1).date()),
            last,
        ),

        f"Calendar {year_end - 1}": (
            max(DATA_MIN, pd.Timestamp(year_end - 1, 1, 1).date()),
            min(last, pd.Timestamp(year_end - 1, 12, 31).date()),
        ),

        "Last available 90 days": (
            max(DATA_MIN, (pd.Timestamp(last) - pd.Timedelta(days=89)).date()),
            last,
        ),

        "Last available 30 days": (
            max(DATA_MIN, (pd.Timestamp(last) - pd.Timedelta(days=29)).date()),
            last,
        ),
    }

    return presets.get(choice, (DATA_MIN, last))


# Sidebar selectbox for choosing a preset date range, with an option for a custom range.
# If "Custom range" is selected, a date input widget is displayed for the user to pick start and end dates. 
# The selected dates are validated to ensure they fall within the available data range.
preset_options = [
    "Full history",
    f"Calendar {DATA_MAX.year}",
    f"Calendar {DATA_MAX.year - 1}",
    "Last available 90 days",
    "Last available 30 days",
    "Next 14 days",
    "Custom range",
]
preset = st.sidebar.selectbox("Period", preset_options, index=1)
if preset == "Next 14 days":
    forecast_mode = True
    start_d, end_d = DATA_MIN, DATA_MAX

elif preset == "Custom range":
    forecast_mode = False
    picked = st.sidebar.date_input(
        "Dates",
        value=(DATA_MIN, DATA_MAX),
        min_value=DATA_MIN,
        max_value=DATA_MAX,
    )
    if isinstance(picked, (tuple, list)) and len(picked) == 2:
        start_d, end_d = picked
    else:
        start_d, end_d = DATA_MIN, DATA_MAX

else:
    forecast_mode = False
    start_d, end_d = preset_range(preset)

# Sidebar multiselects for filtering by order type and meal period, with default selections based on the available data.
type_options = sorted(orders["order_type"].dropna().unique()) if "order_type" in orders else []
meal_options = [m for m in MEAL_ORDER if "meal_period" in orders and m in set(orders["meal_period"].dropna())]
sel_types = st.sidebar.multiselect("Order type", type_options, default=type_options) or type_options
sel_meals = st.sidebar.multiselect("Meal period", meal_options, default=meal_options) or meal_options

# =============================================================================
# Forecast refresh
# =============================================================================

st.sidebar.markdown("### Forecast management")

if st.sidebar.button(
    "↻ Refresh Forecast",
    type="primary",
    **STRETCH,
    help="Generate a fresh 14-day revenue and workforce forecast.",
):
    try:
        with st.spinner("Generating revenue and workforce forecasts..."):

            # 1. Generate the revenue forecast
            revenue_forecast = generate_revenue_forecast(horizon=14)

            # 2. Generate workforce planning outputs
            workforce = generate_workforce_outputs(revenue_forecast)

            # 3. Save all five forecast output files
            save_forecast_outputs(workforce)

            # Save the timestamp of the last successful refresh
            refresh_metadata = { "last_successful_refresh": pd.Timestamp.now
                                ( tz="Europe/Berlin" ).isoformat() }

            with open("metadata/forecast_refresh_metadata.json", "w") as f:
                json.dump(refresh_metadata, f, indent=4)

            # Clear cached CSV data only after successful saving
            st.cache_data.clear()

            st.sidebar.success("Forecast refreshed successfully!")
            st.rerun()

    except Exception as exc:
        st.sidebar.error(f"Forecast refresh failed: {exc}")

# Display the last successful forecast refresh
refresh_metadata_path = Path("metadata/forecast_refresh_metadata.json")

if refresh_metadata_path.exists():
    with open(refresh_metadata_path, "r") as f:
        refresh_metadata = json.load(f)

    last_refresh = pd.to_datetime(
        refresh_metadata["last_successful_refresh"]
    )

    st.sidebar.caption(
        f"Last successful refresh: {last_refresh:%d %b %Y, %H:%M} (Berlin time)"
    )
else:
    st.sidebar.caption("No successful refresh recorded yet.")

st.sidebar.markdown("---")
st.sidebar.caption("DATA")
st.sidebar.markdown("**Synthetic restaurant dataset**")
st.sidebar.caption(f"History · {DATA_MIN:%b %Y} – {DATA_MAX:%b %Y}")
forecast_df = output("revenue_forecast_next_14_days.csv", "date")

forecast_available = (
    has_cols(forecast_df, "date", "forecast_revenue")
    and not forecast_df.empty
)

if forecast_available:
    forecast_start = forecast_df["date"].min().date()
    forecast_end = forecast_df["date"].max().date()

    st.sidebar.caption(
        f"Forecast · {forecast_start:%d %b} - {forecast_end:%d %b %Y}"
    )
else:
    forecast_start = None
    forecast_end = None
    st.sidebar.warning("Forecast data is unavailable.")
st.sidebar.markdown("---")
st.sidebar.caption("DISCLAIMER")
st.sidebar.markdown("Analytical demonstration!!")
st.sidebar.markdown("Forecasts and recommendations are estimates, not operational guarantees!!"
)

# =============================================================================
# Filtered context
# =============================================================================
@dataclass # dataclass is a convenient way to define a class whose main purpose is to store related data
class Context:
    start: pd.Timestamp
    end: pd.Timestamp
    cur: pd.DataFrame          # orders in the selected period & filters
    prev: pd.DataFrame         # equally long period immediately before (may be empty)
    has_prev: bool
    items: pd.DataFrame        # enriched order lines for `cur`
    reviews: pd.DataFrame      # reviews tied to `cur` orders
    daily: pd.DataFrame        # daily revenue / orders / AOV for `cur`

    @property # @property lets you access a method like an attribute
    def label(self) -> str:
        return f"{self.start:%d %b %Y} – {self.end:%d %b %Y}"

# Builds a Context object containing filtered data based on the selected date range and filters for order type and meal period.
def build_context() -> Context:
    start, end = pd.Timestamp(start_d), pd.Timestamp(end_d)
    mask = pd.Series(True, index=orders.index)
    if "order_type" in orders:
        mask &= orders["order_type"].isin(sel_types)
    if "meal_period" in orders:
        mask &= orders["meal_period"].isin(sel_meals)
    base = orders[mask]
    cur = base[base["order_date"].between(start, end)]
    
    # Calculate the previous period for comparison, ensuring it does not go before the minimum available data date 
    n_days = (end - start).days + 1
    prev_end = start - pd.Timedelta(days=1)
    prev_start = prev_end - pd.Timedelta(days=n_days - 1)
    has_prev = prev_start.date() >= DATA_MIN
    prev = base[base["order_date"].between(prev_start, prev_end)] if has_prev else base.iloc[0:0]

    # Order lines with product economics
    if has_cols(items, "order_id", "product_id", "quantity", "line_total") and not cur.empty:
        keep = [c for c in ["order_id", "order_date", "order_type", "meal_period"] if c in cur]
        lines = items.merge(cur[keep], on="order_id", how="inner")
        if has_cols(products, "product_id", "product_cost"):
            lines = lines.merge(
                products[[c for c in ["product_id", "product_name", "category", "product_cost"] if c in products]],
                on="product_id", how="left",
            )
            lines["cost"] = lines["quantity"] * lines["product_cost"]
            lines["gross_profit"] = lines["line_total"] - lines["cost"]
        if "unit_price" in lines:
            lines["discount_value"] = (lines["quantity"] * lines["unit_price"] - lines["line_total"]).clip(lower=0)
    else:
        lines = pd.DataFrame()

    rev = reviews[reviews["order_id"].isin(cur["order_id"])] if has_cols(reviews, "order_id") else pd.DataFrame()

    if cur.empty:
        daily = pd.DataFrame(columns=["order_date", "revenue", "orders", "aov"])
    else:
        daily = cur.groupby("order_date", as_index=False).agg(revenue=("order_total", "sum"), orders=("order_id", "nunique"))
        daily["aov"] = daily["revenue"] / daily["orders"]
    return Context(start, end, cur, prev, has_prev, lines, rev, daily)


ctx = build_context()

# =============================================================================
# Shared analytics
# =============================================================================

# Computes the average revenue by weekday from the daily revenue DataFrame, returning a DataFrame with weekdays and their corresponding average revenue.
def weekday_profile(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame(columns=["weekday", "avg_revenue"])
    d = daily.assign(weekday=daily["order_date"].dt.day_name())
    out = d.groupby("weekday", as_index=False)["revenue"].mean().rename(columns={"revenue": "avg_revenue"})
    out["weekday"] = pd.Categorical(out["weekday"], WEEKDAYS, ordered=True)
    return out.sort_values("weekday")

# Computes key forecast signals from the revenue forecast, workforce forecast, and staffing gaps outputs, returning a dictionary with relevant metrics such as total forecast revenue, peak day and value, labor cost ratio, and unfilled staffing gaps by role.
def forecast_signals() -> dict:
    fc = output("revenue_forecast_next_14_days.csv", "date")
    wf = output("workforce_forecast_next_14_days.csv", "date")
    gaps = output("staffing_gaps.csv", "date")
    out: dict = {}
    if has_cols(fc, "date", "forecast_revenue"):
        out["fc_total"] = fc["forecast_revenue"].sum()
        peak = fc.loc[fc["forecast_revenue"].idxmax()]
        out["fc_peak_day"], out["fc_peak_val"] = peak["date"], peak["forecast_revenue"]
        out["fc_start"], out["fc_end"] = fc["date"].min(), fc["date"].max()
    if has_cols(wf, "labour_cost", "forecast_revenue"):
        out["labour_ratio"] = safe_div(wf["labour_cost"].sum(), wf["forecast_revenue"].sum()) * 100
    if has_cols(gaps, "unfilled", "role"):
        out["unfilled"] = gaps["unfilled"].sum()
        by_role = gaps.groupby("role")["unfilled"].sum().sort_values(ascending=False)
        out["gap_role"] = by_role.index[0] if len(by_role) else None
    return out

# Displays a warning message if there is a significant gap between the end of the model's training data and the start of the forecast, indicating that the forecast may be based on synthetic data rather than validated operational predictions.
def forecast_reliability_warning() -> None:
    fc = output("revenue_forecast_next_14_days.csv", "date")

    if not has_cols(fc, "date") or fc.empty:
        return

    model = meta("restrodine_prophet_calendar_weather_metadata.json")

    training_end = pd.to_datetime( model.get("training_end"), errors="coerce" )

    forecast_start = fc["date"].min()

    if pd.notna(training_end):
        history_gap = (forecast_start - training_end).days - 1

        if history_gap > 30:
            callout(
                f"**Forecast scenario warning:** The model's training data ends on "
                f"{training_end:%d %B %Y}, while this forecast starts on "
                f"{forecast_start:%d %B %Y}. There are {history_gap} days without "
                "observed revenue between these dates. Treat this forecast as a "
                "synthetic-data scenario, not a validated operational prediction.",
                "note",
            )


# =============================================================================
# Page: Executive Overview
# =============================================================================
# Creates a visually distinct card for displaying key signals, with a title, text, and optional kind (e.g., warning, good, risk) for styling purposes.
def signal_card(title: str, text: str, kind: str = "") -> str:
    return f'<div class="signal {kind}"><div class="s-title">{title}</div><div class="s-text">{text}</div></div>'

# Creates the executive overview page with key performance indicators and signals.
def page_executive() -> None:
    hero("Management snapshot", "Executive Overview",
         "Trading performance, customer experience and the near-term operating outlook at a glance.")
    callout("<b>Data transparency:</b> all restaurant, customer, employee, order, review and weather records are "
            "synthetic. Results demonstrate an analytical workflow and are not real business performance.", "note")

    # Future-period view: show forecast information instead of historical trading data.
    if forecast_mode:
        section(
            "Next 14 days",
            "Revenue and workforce outlook based on the saved forecast outputs."
        )

        if not forecast_available:
            st.warning("The 14-day forecast is unavailable. Refresh the forecast first.")
            return

        forecast_reliability_warning()

        sig = forecast_signals()

        if "fc_total" in sig:
            kpis([
                (
                    "Forecast revenue",
                    money(sig["fc_total"]),
                    f"{sig['fc_start']:%d %b} – {sig['fc_end']:%d %b}"
                ),
                (
                    "Peak forecast day",
                    f"{sig['fc_peak_day']:%a %d %b}",
                    money(sig["fc_peak_val"])
                ),
                (
                    "Labour cost / revenue",
                    pct(sig.get("labour_ratio", np.nan)),
                    "Forecast ratio"
                ),
                (
                    "Unfilled positions",
                    integer(sig.get("unfilled", np.nan)),
                    "Across roles and shifts"
                ),
            ])

            fc = forecast_df.sort_values("date").copy()

            section(
                "Daily revenue forecast",
                "Expected revenue for each of the next 14 days."
            )

            fig = px.bar(
                fc,
                x="date",
                y="forecast_revenue",
                labels={
                    "date": "Forecast date",
                    "forecast_revenue": f"Forecast revenue ({CURRENCY})"
                }
            )

            fig.update_traces(marker_color=C["blue"])
            fig.update_xaxes(tickformat="%a %d %b")
            chart(fig, 350)

        else:
            unavailable("The 14-day forecast")

        return


    
    if ctx.cur.empty: # if the current filtered orders DataFrame is empty, display a warning message and return early
        st.warning("No orders match the selected period and filters. Adjust the filters in the sidebar.")
        return

    cur, prev = ctx.cur, ctx.prev
    revenue, n_orders = cur["order_total"].sum(), cur["order_id"].nunique()
    aov = safe_div(revenue, n_orders)
    per_day = safe_div(revenue, ctx.daily["order_date"].nunique())
    rating = pd.to_numeric(ctx.reviews["rating"], errors="coerce").mean() if has_cols(ctx.reviews, "rating") else np.nan

    p_rev = prev["order_total"].sum() if ctx.has_prev and not prev.empty else None
    p_orders = prev["order_id"].nunique() if ctx.has_prev and not prev.empty else None
    p_aov = safe_div(p_rev, p_orders) if p_rev is not None else None
    p_day = safe_div(p_rev, prev["order_date"].nunique()) if p_rev is not None else None

    kpis([
        ("Revenue", money(revenue), delta_label(change_pct(revenue, p_rev))),
        ("Orders", integer(n_orders), delta_label(change_pct(n_orders, p_orders))),
        ("Average order value", money(aov, 2), delta_label(change_pct(aov, p_aov))),
        ("Revenue per trading day", money(per_day), delta_label(change_pct(per_day, p_day))),
        ("Average guest rating", f"{rating:.2f} / 5" if pd.notna(rating) else "—", f"{integer(len(ctx.reviews))} reviews"),
    ])
    st.caption(f"Period: {ctx.label}" + (" · deltas compare with the equally long preceding period." if ctx.has_prev
                                         else " · no preceding period of equal length exists in the data."))
    st.write("")

    left, right = st.columns([1.75, 1])
    with left:
        section("Revenue trend", "Daily revenue with a 7-day moving average.")
        d = ctx.daily.sort_values("order_date").copy()
        d["ma7"] = d["revenue"].rolling(7, min_periods=3).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d["order_date"], y=d["revenue"], name="Daily revenue", mode="lines",
                                 line=dict(color=C["blue_soft"], width=1), opacity=.55))
        fig.add_trace(go.Scatter(x=d["order_date"], y=d["ma7"], name="7-day rolling average", mode="lines",
                                 line=dict(color=C["blue"], width=2.8)))
        fig.update_layout(yaxis_title=f"Revenue ({CURRENCY})")
        chart(fig, 340)
    with right:
        section("Key signals", "Automatically derived from the current selection and saved outputs.")
        cards = []
        wd = weekday_profile(ctx.daily)
        if not wd.empty:
            best = wd.loc[wd["avg_revenue"].idxmax()]
            lift = change_pct(best["avg_revenue"], wd["avg_revenue"].mean())
            cards.append(signal_card("Peak trading day",
                                     f"{best['weekday']} averages {money(best['avg_revenue'])}, "
                                     f"{lift:+.0f}% versus the average weekday.", "good"))
        if "order_type" in cur:
            share = cur.groupby("order_type")["order_total"].sum().sort_values(ascending=False)
            cards.append(signal_card("Channel mix",
                                     f"{share.index[0]} is the largest channel at {share.iloc[0] / share.sum() * 100:.0f}% of revenue."))
        if has_cols(ctx.items, "category", "line_total"):
            cat = ctx.items.groupby("category")["line_total"].sum().sort_values(ascending=False)
            cards.append(signal_card("Top category",
                                     f"{cat.index[0]} leads with {cat.iloc[0] / cat.sum() * 100:.0f}% of item revenue."))
        imp = output("customer_improvement_areas.csv")
        if has_cols(imp, "Aspect", "Negative Share (%)"):
            top = imp.sort_values("Negative Share (%)", ascending=False).iloc[0]
            cards.append(signal_card("Guest friction",
                                     f"{top['Aspect']} draws the highest negative share ({top['Negative Share (%)']:.0f}% of mentions).",
                                     "warn"))
        sig = forecast_signals()
        if "unfilled" in sig:
            kind = "risk" if sig["unfilled"] > 0 else "good"
            role = f", mostly {sig['gap_role']}" if sig.get("gap_role") and sig["unfilled"] > 0 else ""
            cards.append(signal_card("Staffing outlook", f"{integer(sig['unfilled'])} unfilled positions in the next 14 days{role}.", kind))
        st.markdown("".join(cards) or "<div class='section-note'>No signals available.</div>", unsafe_allow_html=True)

    st.write("")
    a, b, c = st.columns(3)
    with a:
        section("Average revenue by weekday")
        wd = weekday_profile(ctx.daily)

        weekday_colors = [
            "#6BAF92",  # Monday
            "#4C9B78",  # Tuesday
            "#378565",  # Wednesday
            "#E0A34A",  # Thursday
            "#D88745",  # Friday
            "#C96B55",  # Saturday
            "#7895B2",  # Sunday
        ]

        fig = px.bar(
            wd,
            x="weekday",
            y="avg_revenue",
            labels={
                "weekday": "",
                "avg_revenue": f"Avg revenue ({CURRENCY})"
            }
        )

        fig.update_traces(marker_color=weekday_colors)
        chart(fig, 300, unified=False)
    with b:
        section("Revenue by order type")
        if "order_type" in cur:
            mix = cur.groupby("order_type", as_index=False)["order_total"].sum()
            fig = px.pie(mix, names="order_type", values="order_total", hole=.62)
            fig.update_traces(textinfo="percent", textposition="inside", marker=dict(line=dict(color="white", width=2)))
            fig.update_layout(legend=dict(orientation="h", y=-0.05))
            chart(fig, 300, unified=False)
    with c:
        section("Revenue by meal period")
        if "meal_period" in cur:
            mix = cur.groupby("meal_period", as_index=False)["order_total"].sum()
            mix["meal_period"] = pd.Categorical(
                mix["meal_period"], MEAL_ORDER, ordered=True
            )

            meal_colors = {
                "Lunch": "#E0A34A",
                "Afternoon": "#7895B2",
                "Dinner": "#378565",
            }

            fig = px.bar(
                mix.sort_values("meal_period"),
                x="meal_period",
                y="order_total",
                color="meal_period",
                color_discrete_map=meal_colors,
                labels={
                    "meal_period": "",
                    "order_total": f"Revenue ({CURRENCY})"
                }
            )

            fig.update_layout(showlegend=False)
            chart(fig, 300, unified=False)

    st.write("")
    section("Next 14 days", "Saved forecast and roster recommendation; independent of the historical filters.")
    forecast_reliability_warning()
    sig = forecast_signals()
    if "fc_total" in sig:
        kpis([
            ("Forecast revenue", money(sig["fc_total"]), f"{sig['fc_start']:%d %b} – {sig['fc_end']:%d %b}"),
            ("Peak forecast day", f"{sig['fc_peak_day']:%a %d %b}", money(sig["fc_peak_val"])),
            ("Labour cost / revenue", pct(sig.get("labour_ratio", np.nan)), "Forecast ratio"),
            ("Unfilled positions", integer(sig.get("unfilled", np.nan)), "Across roles & shifts"),
        ])
    else:
        unavailable("The 14-day outlook")


# =============================================================================
# Page: Revenue & Forecast
# =============================================================================

def page_revenue() -> None:
    hero("Trading & forecasting", "Revenue & Forecast",
         "Understand what drives sales and review the 14-day weather-aware revenue forecast.")
    if forecast_mode:
        tab_fc, tab_hist, tab_drivers = st.tabs([
            "14-day forecast",
            "Historical performance",
            "Weather & Holiday Impact",
        ])
    else:
        tab_hist,  tab_fc, tab_drivers = st.tabs([
            "Historical performance",
            "14-day forecast",
            "Weather & Holiday Impact"
        ])

    # ---- Historical -------------------------------------------------------
    with tab_hist:
        if ctx.cur.empty:
            st.warning("No orders match the selected period and filters.")
        else:
            cur = ctx.cur
            total, n = cur["order_total"].sum(), cur["order_id"].nunique()
            best_day = ctx.daily.loc[ctx.daily["revenue"].idxmax()]
            kpis([
                ("Revenue", money(total), ctx.label),
                ("Orders", integer(n), None),
                ("Average order value", money(safe_div(total, n), 2), None),
                #("Average party size", f"{cur['party_size'].mean():.1f}" if "party_size" in cur else "—", None),
                ("Best trading day", money(best_day["revenue"]), f"{best_day['order_date']:%d %b %Y}"),
            ])
            st.write("")
            
            
            section(
                "Monthly average daily revenue",
                "Comparison of average daily revenue for each calendar month across years."
            )

            # Aggregate daily revenue by calendar month and year
            monthly_revenue = (
                ctx.daily
                .assign(
                    month=ctx.daily["order_date"].dt.month,
                    year=ctx.daily["order_date"].dt.year
                )
                .groupby(["year", "month"], as_index=False)
                .agg(avg_daily_revenue=("revenue", "mean"))
            )

            # Month labels
            month_names = {
                1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
                5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
                9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
            }

            monthly_revenue["month_name"] = monthly_revenue["month"].map(month_names)

            # Year-on-year line chart
            fig = px.line(
                monthly_revenue,
                x="month",
                y="avg_daily_revenue",
                color="year",
                markers=True,
                color_discrete_map={
                    2024: "#4C78A8",
                    2025: "#E07A5F"
                },
                labels={
                    "month": "Month",
                    "avg_daily_revenue": f"Average daily revenue ({CURRENCY})",
                    "year": "Year"
                }
            )

            fig.update_xaxes(
                tickmode="array",
                tickvals=list(range(1, 13)),
                ticktext=list(month_names.values())
            )

            fig.update_layout(
                hovermode="x unified",
                legend_title_text="Year"
            )

            chart(fig, 360, unified=False)


            left, right = st.columns([1.3, 1])
            with left:
                section(
                    "When do guests visit the most?",
                    "Average orders per hour for each weekday across the selected period."
                )

                if "hour" in cur:
                    heat = (
                        cur.groupby(["weekday", "hour"])
                        .size()
                        .rename("n")
                        .reset_index()
                    )

                    days = cur.groupby("weekday")["order_date"].nunique()

                    heat["avg"] = heat["n"] / heat["weekday"].map(days)

                    pivot = (
                        heat.pivot(index="weekday", columns="hour", values="avg")
                        .reindex(WEEKDAYS)
                        .fillna(0)
                    )

                    # Display hour labels in HH:00 format
                    hour_labels = [
                        f"{int(hour):02d}:00"
                        for hour in pivot.columns
                    ]

                    fig = px.imshow(
                        pivot,
                        aspect="auto",
                        text_auto=".1f",
                        color_continuous_scale=["#F1F5FF", C["blue"]],
                        labels={
                            "x": "Hour of day",
                            "y": "",
                            "color": "Avg orders/hour"
                        }
                    )

                    # Show every available hour on the x-axis
                    fig.update_xaxes(
                        tickmode="array",
                        tickvals=list(pivot.columns)[::2],
                        ticktext=hour_labels[::2],
                        tickangle=0,
                        tickfont=dict(size=10)
                    )

                    fig.update_layout(
                        height=390,
                        margin=dict(l=10, r=10, t=35, b=55)
                    )

                    chart(fig, 390, unified=False)

            with right:
                section("Payment methods", "Total order value by payment method.")
                if has_cols(payments, "order_id", "payment_method", "amount"):
                    pay = payments[payments["order_id"].isin(cur["order_id"])]
                    pm = pay.groupby("payment_method", as_index=False)["amount"].sum().sort_values("amount")
                    fig = px.bar(pm, x="amount", y="payment_method", orientation="h",
                                 labels={"amount": f"Order value ({CURRENCY})", "payment_method": ""})
                    payment_colors = {
                        "Card": "#376B42",
                        "Mobile Pay": "#39977A",
                        "Cash": "#E5A132",
                        "PayPal": "#5576A8",
                        "Voucher": "#9B7BB5",
                    }

                    fig.update_traces(
                        marker_color=[
                            payment_colors.get(method, "#8A9690")
                            for method in pm["payment_method"]
                        ]
                    )
                    chart(fig, 390, unified=False)
                else:
                    unavailable("Payment data")


    # ---- Forecast ---------------------------------------------------------
    with tab_fc:
        fc = output("revenue_forecast_next_14_days.csv", "date")
        if not has_cols(fc, "date", "forecast_revenue", "lower_bound", "upper_bound"):
            unavailable("The revenue forecast")
            return
        fc = fc.sort_values("date").reset_index(drop=True)
        total, low, high = fc["forecast_revenue"].sum(), fc["lower_bound"].sum(), fc["upper_bound"].sum()
        peak = fc.loc[fc["forecast_revenue"].idxmax()]
        model = meta("restrodine_prophet_calendar_weather_metadata.json")
        pj = meta("restrodine_prophet_calendar_weather.json")
        width = pj.get("interval_width")

        forecast_reliability_warning()

        kpis([
            ("Forecast revenue", money(total), f"{fc['date'].min():%d %b} – {fc['date'].max():%d %b %Y}"),
            ("Average per day", money(total / len(fc)), None),
            ("Peak day", f"{peak['date']:%a %d %b}", money(peak["forecast_revenue"])),
             ])

        st.write("")
        section("Forecast with uncertainty band", "Saved model output; the app displays it and does not retrain the model.")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=fc["date"], y=fc["upper_bound"], mode="lines", line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=fc["date"], y=fc["lower_bound"], mode="lines", line=dict(width=0), fill="tonexty",
                                 fillcolor="rgba(47,85,212,.15)", name="Uncertainty range"))
        fig.add_trace(go.Scatter(x=fc["date"], y=fc["forecast_revenue"], mode="lines+markers", name="Forecast revenue",
                                 line=dict(color=C["blue"], width=3), marker=dict(size=7)))
        fig.update_layout(yaxis_title=f"Revenue ({CURRENCY})")
        fig.update_xaxes(tickformat="%a %d %b")
        chart(fig, 360)

        # Plausibility check against recent same-weekday history
        if has_cols(daily_hist, "date", "revenue"):
            recent = daily_hist[daily_hist["date"] >= daily_hist["date"].max() - pd.Timedelta(days=364)]
            typical = recent.assign(wd=recent["date"].dt.day_name()).groupby("wd")["revenue"].mean()
            bench = fc.assign(Weekday=fc["date"].dt.day_name())
            bench["typical"] = bench["Weekday"].map(typical)
            bench["vs_typical"] = (bench["forecast_revenue"] / bench["typical"] - 1) * 100
            section("Forecast vs. Historical Weekday Benchmark", "Forecast compared with the average of the same weekday over the last 12 months of history.")
            fig = go.Figure()
            fig.add_bar(x=bench["date"], y=bench["typical"], name="Typical same weekday (last 12 months)", marker_color=C["grey"])
            fig.add_bar(x=bench["date"], y=bench["forecast_revenue"], name="Forecast", marker_color=C["blue"])
            fig.update_layout(barmode="group", yaxis_title=f"Revenue ({CURRENCY})")
            fig.update_xaxes(tickformat="%a %d %b")
            chart(fig, 300)
            avg_dev = bench["vs_typical"].mean()
            if pd.notna(avg_dev) and abs(avg_dev) > 20:
                callout(f"On average the forecast is {avg_dev:+.0f}% versus typical weekday revenue. "
                        "Review seasonality, weather inputs and promotions before relying on it.", "note")


        with st.expander("Daily forecast table"):
            show = fc.rename(columns={
                "date": "Date",
                "forecast_revenue": f"Forecast ({CURRENCY})",
                "lower_bound": f"Lower bound ({CURRENCY})",
                "upper_bound": f"Upper bound ({CURRENCY})",
                "expected_orders": "Expected orders",
                "day_of_week": "Weekday",
                "is_weekend": "Weekend",
                "demand_tier": "Demand tier"
            }).copy()

            show["Date"] = show["Date"].dt.strftime(
                "%a %d %b %Y"
            )

            if "Weekend" in show.columns:
                show["Weekend"] = show["Weekend"].map({
                    1: "Yes",
                    0: "No",
                    True: "Yes",
                    False: "No"
                })

            forecast_columns = [
                f"Forecast ({CURRENCY})",
                f"Lower bound ({CURRENCY})",
                f"Upper bound ({CURRENCY})"
            ]

            column_config = {
                col: money_col(col, 0)
                for col in forecast_columns
                if col in show.columns
            }

            if "Expected orders" in show.columns:
                column_config["Expected orders"] = (
                    st.column_config.NumberColumn(
                        "Expected orders",
                        format="%.0f"
                    )
                )

            # Style the daily forecast table for management readability
            def style_demand(value):
                colours = {
                    "Low": "background-color: #EEF1EE; color: #59665B;",
                    "Standard": "background-color: #E8F0FA; color: #315D91;",
                    "High": "background-color: #DCEFE2; color: #27643C; font-weight: 700;",
                }
                return colours.get(value, "")

            styled = (
                show.style
                .map(style_demand, subset=["Demand tier"])
                .bar(
                    subset=["Expected orders"],
                    color="#DCE8D9",
                    vmin=0
                )
                .map(
                    lambda _: "font-weight: 700; color: #27643C;",
                    subset=[f"Forecast ({CURRENCY})"]
                )
            )

            st.dataframe(
                styled,
                height=380,
                hide_index=True,
                column_config=column_config,
                **STRETCH
            )

            download(
                fc,
                "Download forecast (CSV)",
                "revenue_forecast_next_14_days.csv",
                "dl_fc"
            )


        with st.expander("Model card"):
            if model:
                regs = ", ".join(model.get("regressors", [])) or "—"
                loc = model.get("location", {})
                st.markdown(
                    f"- **Model:** {model.get('model', 'Prophet')}\n"
                    f"- **Seasonality:** weekly = {model.get('weekly_seasonality')}, yearly = {model.get('yearly_seasonality')}, "
                    f"mode = {model.get('seasonality_mode')}\n"
                    f"- **External regressors:** {regs}\n"
                    f"- **Training window:** {model.get('training_start')} to {model.get('training_end')}\n"
                    f"- **Weather location:** {loc.get('region', '—')} ({loc.get('latitude', '—')}, {loc.get('longitude', '—')})"
                )
            else:
                st.caption("Model metadata file not found.")
        callout("Forecast values are estimates, not guaranteed revenue. Lower and upper bounds express model "
                "uncertainty and are not guaranteed minimum or maximum outcomes.", "note")  


    

    # ---- Weather & Holiday Impact ----------------------------------------
    with tab_drivers:
        section(
            "Weather & Holiday Impact",
            "Explore how historical weather and calendar conditions relate to daily restaurant revenue."
        )

        if forecast_mode:
            st.info(
                "Weather and holiday impact analysis uses historical revenue "
                "and observed weather data. It is not available for the future "
                "14-day forecast period."
            )

        else:
            callout(
                "These comparisons are descriptive associations, not proof. "
                "Weather can be correlated with season, weekday and other "
                "trading conditions. All data in this project is synthetic.",
                "info"
            )

            weather_columns = [
                "date",
                "temperature_avg_c",
                "precipitation_mm",
                "is_rainy",
                "is_holiday"
            ]

            if (
                not has_cols(daily_hist, "date", "revenue")
                or not has_cols(daily_ctx, *weather_columns)
            ):
                unavailable("Historical weather and revenue data")

            else:
                # Use total daily restaurant revenue, independent of
                # order-type and meal-period sidebar filters.
                weather_data = daily_hist[
                    ["date", "revenue"]
                ].merge(
                    daily_ctx[weather_columns],
                    on="date",
                    how="inner"
                )

                weather_data = weather_data[
                    weather_data["date"].between(
                        pd.Timestamp(start_d),
                        pd.Timestamp(end_d)
                    )
                ].copy()

                weather_data = weather_data.dropna(
                    subset=[
                        "revenue",
                        "temperature_avg_c",
                        "precipitation_mm"
                    ]
                )

                if weather_data.empty:
                    st.info(
                        "No matching historical weather and revenue "
                        "observations are available for this period."
                    )

                else:
                    # Prepare categorical variables
                    weather_data["is_rainy"] = (
                        weather_data["is_rainy"]
                        .fillna(False)
                        .astype(bool)
                    )

                    weather_data["is_holiday"] = (
                        weather_data["is_holiday"]
                        .fillna(False)
                        .astype(bool)
                    )

                    weather_data["Weather"] = np.where(
                        weather_data["is_rainy"],
                        "Rainy day",
                        "Dry day"
                    )

                    weather_data["Day type"] = np.where(
                        weather_data["is_holiday"],
                        "Public holiday",
                        "Regular day"
                    )

                    # ----------------------------------------------------
                    # IMPACT SUMMARY
                    # ----------------------------------------------------

                    rain_stats = (
                        weather_data
                        .groupby("Weather")["revenue"]
                        .agg(["mean", "size"])
                    )

                    rainy_avg = rain_stats["mean"].get(
                        "Rainy day", np.nan
                    )
                    dry_avg = rain_stats["mean"].get(
                        "Dry day", np.nan
                    )

                    rainy_days = int(
                        rain_stats["size"].get("Rainy day", 0)
                    )
                    dry_days = int(
                        rain_stats["size"].get("Dry day", 0)
                    )

                    rain_difference = (
                        (rainy_avg / dry_avg - 1) * 100
                        if pd.notna(rainy_avg)
                        and pd.notna(dry_avg)
                        and dry_avg != 0
                        else np.nan
                    )

                    holiday_stats = (
                        weather_data
                        .groupby("Day type")["revenue"]
                        .agg(["mean", "size"])
                    )

                    holiday_avg = holiday_stats["mean"].get(
                        "Public holiday", np.nan
                    )
                    regular_avg = holiday_stats["mean"].get(
                        "Regular day", np.nan
                    )

                    holiday_days = int(
                        holiday_stats["size"].get("Public holiday", 0)
                    )
                    regular_days = int(
                        holiday_stats["size"].get("Regular day", 0)
                    )

                    holiday_difference = (
                        (holiday_avg / regular_avg - 1) * 100
                        if pd.notna(holiday_avg)
                        and pd.notna(regular_avg)
                        and regular_avg != 0
                        else np.nan
                    )

                    section(
                        "Revenue impact summary",
                        "Quantifying the average revenue differences between weather and calendar conditions."
                    )

                    kpis([
                        (
                            "Average revenue · rainy",
                            money(rainy_avg),
                            f"{rainy_days:,} rainy days"
                        ),
                        (
                            "Rain vs. dry difference",
                            f"{rain_difference:+.1f}%"
                            if pd.notna(rain_difference) else "—",
                            f"Dry-day average: {money(dry_avg)} · {dry_days:,} days"
                        ),
                        (
                            "Average revenue · holidays",
                            money(holiday_avg),
                            f"{holiday_days:,} public holidays"
                        ),
                        (
                            "Holiday vs. regular difference",
                            f"{holiday_difference:+.1f}%"
                            if pd.notna(holiday_difference) else "—",
                            f"Regular avg. {money(regular_avg)}"
                        ),
                    ])

                    st.caption(
                        "Percentage differences use dry days and regular days "
                        "as their respective baselines. Positive values indicate "
                        "higher average revenue; negative values indicate lower "
                        "average revenue. These are descriptive comparisons, "
                        "not causal estimates."
                    )

                    st.caption(
                        f"Analysis period: {start_d:%d %b %Y} – "
                        f"{end_d:%d %b %Y} · "
                        f"{len(weather_data):,} daily observations."
                    )

                    # ----------------------------------------------------
                    # ROW 1: RAINFALL AND TEMPERATURE
                    # ----------------------------------------------------

                    left, right = st.columns(2)

                    with left:
                        section(
                            "Rainy vs. dry days",
                            "Average daily revenue and number of observations."
                        )

                        rain_summary = (
                            weather_data
                            .groupby("Weather", as_index=False)
                            .agg(
                                avg_revenue=("revenue", "mean"),
                                days=("revenue", "size")
                            )
                        )

                        fig = px.bar(
                            rain_summary,
                            x="Weather",
                            y="avg_revenue",
                            color="Weather",
                            text=rain_summary["days"].map(
                                lambda v: f"{v} days"
                            ),
                            color_discrete_map={
                                "Rainy day": C["blue"],
                                "Dry day": C["grey"]
                            },
                            labels={
                                "Weather": "",
                                "avg_revenue": f"Average revenue ({CURRENCY})"
                            }
                        )

                        fig.update_traces(textposition="outside")
                        fig.update_layout(showlegend=False)
                        chart(fig, 330, unified=False)

                    with right:
                        section(
                            "Revenue by average temperature",
                            "Average daily revenue across temperature bands."
                        )

                        bins = [
                            -np.inf, 5, 10, 15, 20, 25, np.inf
                        ]

                        labels = [
                            "< 5 °C",
                            "5–10 °C",
                            "10–15 °C",
                            "15–20 °C",
                            "20–25 °C",
                            "≥ 25 °C"
                        ]

                        weather_data["Temperature band"] = pd.cut(
                            weather_data["temperature_avg_c"],
                            bins=bins,
                            labels=labels,
                            right=False
                        )

                        temp_summary = (
                            weather_data
                            .groupby(
                                "Temperature band",
                                observed=True,
                                as_index=False
                            )
                            .agg(
                                avg_revenue=("revenue", "mean"),
                                days=("revenue", "size")
                            )
                        )

                        fig = px.bar(
                            temp_summary,
                            x="Temperature band",
                            y="avg_revenue",
                            color="Temperature band",
                            text=temp_summary["days"].map(
                                lambda v: f"{v} days"
                            ),
                            color_discrete_sequence=CATEGORY_SEQ,
                            labels={
                                "Temperature band": "",
                                "avg_revenue": f"Average revenue ({CURRENCY})"
                            }
                        )

                        fig.update_traces(textposition="outside")
                        fig.update_layout(showlegend=False)
                        chart(fig, 330, unified=False)

                    # ----------------------------------------------------
                    # ROW 2: HOLIDAYS AND PRECIPITATION
                    # ----------------------------------------------------

                    left, right = st.columns(2)

                    with left:
                        section(
                            "Public holiday vs. regular days",
                            "Compare average daily revenue on NRW public holidays and other days."
                        )

                        holiday_summary = (
                            weather_data
                            .groupby("Day type", as_index=False)
                            .agg(
                                avg_revenue=("revenue", "mean"),
                                days=("revenue", "size")
                            )
                        )

                        fig = px.bar(
                            holiday_summary,
                            x="Day type",
                            y="avg_revenue",
                            color="Day type",
                            text=holiday_summary["days"].map(
                                lambda v: f"{v} days"
                            ),
                            color_discrete_map={
                                "Public holiday": C["amber"],
                                "Regular day": C["blue"]
                            },
                            labels={
                                "Day type": "",
                                "avg_revenue": f"Average revenue ({CURRENCY})"
                            }
                        )

                        fig.update_traces(textposition="outside")
                        fig.update_layout(showlegend=False)
                        chart(fig, 330, unified=False)

                    with right:
                        section(
                            "Precipitation vs. revenue",
                            "Each point represents one historical trading day."
                        )

                        fig = px.scatter(
                            weather_data,
                            x="precipitation_mm",
                            y="revenue",
                            color="Weather",
                            opacity=0.65,
                            color_discrete_map={
                                "Rainy day": C["blue"],
                                "Dry day": C["grey"]
                            },
                            labels={
                                "precipitation_mm": "Precipitation (mm)",
                                "revenue": f"Daily revenue ({CURRENCY})"
                            }
                        )

                        chart(fig, 330, unified=False)

                    
                    # ----------------------------------------------------
                    # STATISTICAL EVIDENCE
                    # ----------------------------------------------------

                    section(
                        "Statistical evidence",
                        "Test whether observed revenue differences are statistically significant."
                    )

                    # Welch's t-test and 95% confidence interval
                    def welch_comparison(group_a, group_b):
                        a = pd.Series(group_a).dropna().astype(float)
                        b = pd.Series(group_b).dropna().astype(float)

                        if len(a) < 2 or len(b) < 2:
                            return None

                        mean_difference = a.mean() - b.mean()

                        variance_a = a.var(ddof=1)
                        variance_b = b.var(ddof=1)

                        se_squared = (
                            variance_a / len(a)
                            + variance_b / len(b)
                        )

                        if se_squared <= 0:
                            return None

                        se = np.sqrt(se_squared)

                        df = se_squared ** 2 / (
                            (variance_a / len(a)) ** 2 / (len(a) - 1)
                            + (variance_b / len(b)) ** 2 / (len(b) - 1)
                        )

                        test = stats.ttest_ind(
                            a,
                            b,
                            equal_var=False,
                            nan_policy="omit"
                        )

                        critical_value = stats.t.ppf(
                            0.975,
                            df
                        )

                        margin = critical_value * se

                        return {
                            "difference": mean_difference,
                            "ci_lower": mean_difference - margin,
                            "ci_upper": mean_difference + margin,
                            "p_value": test.pvalue,
                            "n_a": len(a),
                            "n_b": len(b)
                        }

                    def format_p_value(p):
                        if pd.isna(p):
                            return "Not available"
                        if p < 0.001:
                            return "< 0.001"
                        return f"{p:.3f}"

                    # ----------------------------------------------------
                    # TEST 1: RAINY VS. DRY DAYS
                    # ----------------------------------------------------

                    rain_test = welch_comparison(
                        weather_data.loc[
                            weather_data["Weather"] == "Rainy day",
                            "revenue"
                        ],
                        weather_data.loc[
                            weather_data["Weather"] == "Dry day",
                            "revenue"
                        ]
                    )

                    # ----------------------------------------------------
                    # TEST 2: PUBLIC HOLIDAYS VS. REGULAR DAYS
                    # ----------------------------------------------------

                    holiday_test = welch_comparison(
                        weather_data.loc[
                            weather_data["Day type"] == "Public holiday",
                            "revenue"
                        ],
                        weather_data.loc[
                            weather_data["Day type"] == "Regular day",
                            "revenue"
                        ]
                    )

                    # ----------------------------------------------------
                    # TEST 3: TEMPERATURE VS. REVENUE
                    # Spearman rank correlation
                    # ----------------------------------------------------

                    temperature_data = weather_data.dropna(
                        subset=["temperature_avg_c", "revenue"]
                    )

                    if (
                        len(temperature_data) >= 3
                        and temperature_data["temperature_avg_c"].nunique() > 1
                        and temperature_data["revenue"].nunique() > 1
                    ):
                        temperature_corr = stats.spearmanr(
                            temperature_data["temperature_avg_c"],
                            temperature_data["revenue"]
                        )

                        spearman_rho = temperature_corr.statistic
                        spearman_p = temperature_corr.pvalue
                    else:
                        spearman_rho = np.nan
                        spearman_p = np.nan

                    # ----------------------------------------------------
                    # TEST 4: REVENUE ACROSS TEMPERATURE BANDS
                    # Kruskal-Wallis test
                    # ----------------------------------------------------

                    temperature_groups = [
                        group["revenue"].dropna().values
                        for _, group in weather_data.groupby(
                            "Temperature band",
                            observed=True
                        )
                        if len(group["revenue"].dropna()) >= 2
                    ]

                    if len(temperature_groups) >= 2:
                        temperature_test = stats.kruskal(
                            *temperature_groups
                        )

                        temperature_band_stat = temperature_test.statistic
                        temperature_band_p = temperature_test.pvalue
                    else:
                        temperature_band_stat = np.nan
                        temperature_band_p = np.nan

                    # ----------------------------------------------------
                    # DISPLAY STATISTICAL RESULTS
                    # ----------------------------------------------------

                    results = []

                    if rain_test is not None:
                        results.append({
                            "Comparison": "Rainy vs. dry days",
                            "Mean difference (€)": money(
                                rain_test["difference"], 2
                            ),
                            "95% confidence interval": (
                                f"{money(rain_test['ci_lower'], 2)} to "
                                f"{money(rain_test['ci_upper'], 2)}"
                            ),
                            "p-value": format_p_value(
                                rain_test["p_value"]
                            ),
                            "Observations": (
                                f"{rain_test['n_a']} vs. {rain_test['n_b']}"
                            )
                        })

                    if holiday_test is not None:
                        results.append({
                            "Comparison": "Public holidays vs. regular days",
                            "Mean difference (€)": money(
                                holiday_test["difference"], 2
                            ),
                            "95% confidence interval": (
                                f"{money(holiday_test['ci_lower'], 2)} to "
                                f"{money(holiday_test['ci_upper'], 2)}"
                            ),
                            "p-value": format_p_value(
                                holiday_test["p_value"]
                            ),
                            "Observations": (
                                f"{holiday_test['n_a']} vs. "
                                f"{holiday_test['n_b']}"
                            )
                        })

                    results.append({
                        "Comparison": "Temperature vs. revenue (Spearman)",
                        "Mean difference (€)": (
                            f"ρ = {spearman_rho:.3f}"
                            if pd.notna(spearman_rho) else "—"
                        ),
                        "95% confidence interval": "Not calculated",
                        "p-value": format_p_value(spearman_p),
                        "Observations": str(len(temperature_data))
                    })

                    results.append({
                        "Comparison": "Revenue across temperature bands",
                        "Mean difference (€)": (
                            f"H = {temperature_band_stat:.3f}"
                            if pd.notna(temperature_band_stat) else "—"
                        ),
                        "95% confidence interval": "Not calculated",
                        "p-value": format_p_value(temperature_band_p),
                        "Observations": str(len(temperature_data))
                    })

                    st.dataframe( pd.DataFrame(results), **STRETCH, hide_index=True )

                    st.caption(
                        "Welch's t-test compares group means without assuming "
                        "equal variances. Spearman measures monotonic association. "
                        "Kruskal–Wallis compares the distributions across "
                        "temperature bands. A p-value below 0.05 is conventionally "
                        "considered statistically significant, but does not "
                        "establish causation."
                    )


                    # ----------------------------------------------------
                    # ADJUSTED REVENUE REGRESSION
                    # ----------------------------------------------------

                    section(
                        "Adjusted weather & calendar regression",
                        "Estimate the relationship between weather, holidays and promotions while controlling for weekday and seasonality."
                    )

                    # Add promotion information to the daily dataset.
                    promotion_data = daily_ctx[
                        ["date", "is_promo_day"]
                    ].drop_duplicates("date")

                    regression_data = weather_data.merge(
                        promotion_data,
                        on="date",
                        how="left"
                    )

                    regression_data = regression_data.sort_values(
                        "date"
                    ).copy()

                    # Remove observations with missing model inputs.
                    regression_data = regression_data.dropna(
                        subset=[
                            "revenue",
                            "temperature_avg_c",
                            "precipitation_mm",
                            "is_holiday",
                            "is_promo_day"
                        ]
                    )

                    # Convert binary variables to numeric indicators.
                    regression_data["is_holiday"] = (
                        regression_data["is_holiday"].astype(int)
                    )

                    regression_data["is_promo_day"] = (
                        regression_data["is_promo_day"].astype(int)
                    )

                    # Create calendar controls.
                    regression_data["weekday"] = (
                        regression_data["date"].dt.day_name()
                    )

                    regression_data["month"] = (
                        regression_data["date"].dt.month.astype(str)
                    )

                    # Predictors of interest.
                    candidate_predictors = [
                        "temperature_avg_c",
                        "precipitation_mm",
                        "is_holiday",
                        "is_promo_day"
                    ]

                    # Exclude predictors with no variation in the
                    # selected period. Their effects cannot be estimated.
                    active_predictors = [
                        col
                        for col in candidate_predictors
                        if regression_data[col].nunique() > 1
                    ]

                    # Create weekday and month fixed effects.
                    calendar_controls = pd.get_dummies(
                        regression_data[["weekday", "month"]],
                        columns=["weekday", "month"],
                        drop_first=True,
                        dtype=float
                    )

                    X = regression_data[
                        active_predictors
                    ].astype(float)

                    X = pd.concat(
                        [X, calendar_controls],
                        axis=1
                    )

                    X = sm.add_constant(
                        X,
                        has_constant="add"
                    )

                    y = regression_data["revenue"].astype(float)

                    # Require sufficient observations and a full-rank
                    # design matrix before estimating the model.
                    if (
                        len(regression_data) < 40
                        or np.linalg.matrix_rank(X.to_numpy()) < X.shape[1]
                        or len(regression_data) <= X.shape[1] + 7
                    ):
                        st.warning(
                            "There are insufficient observations or "
                            "variation to estimate a reliable adjusted "
                            "regression for this selected period. "
                            "Try a longer historical period."
                        )

                    else:
                        # OLS with Newey-West HAC standard errors.
                        regression_model = sm.OLS(y, X).fit(
                            cov_type="HAC",
                            cov_kwds={"maxlags": 7}
                        )

                        # ------------------------------------------------
                        # MODEL PERFORMANCE
                        # ------------------------------------------------

                        st.write("")

                        kpis([
                            (
                                "Observations",
                                str(integer(int(regression_model.nobs))),
                                "Daily records"
                            ),
                            (
                                "R-squared",
                                f"{regression_model.rsquared:.3f}",
                                "Explained revenue variation"
                            ),
                            (
                                "Adjusted R-squared",
                                f"{regression_model.rsquared_adj:.3f}",
                                "Adjusted for model complexity"
                            )
                        ])

                        # ------------------------------------------------
                        # COEFFICIENT RESULTS
                        # ------------------------------------------------

                        coefficient_labels = {
                            "temperature_avg_c": "Temperature (per °C)",
                            "precipitation_mm": "Precipitation (per mm)",
                            "is_holiday": "Public holiday",
                            "is_promo_day": "Promotion day"
                        }

                        coefficient_rows = []

                        confidence = regression_model.conf_int(
                            alpha=0.05
                        )

                        for variable in candidate_predictors:

                            if variable not in active_predictors:
                                continue

                            coefficient = regression_model.params[variable]
                            lower = confidence.loc[variable, 0]
                            upper = confidence.loc[variable, 1]
                            p_value = regression_model.pvalues[variable]

                            coefficient_rows.append({
                                "Factor": coefficient_labels[variable],
                                "Revenue coefficient (€)": coefficient,
                                "95% CI lower (€)": lower,
                                "95% CI upper (€)": upper,
                                "p-value": p_value
                            })

                        coefficient_df = pd.DataFrame(
                            coefficient_rows
                        )

                        if not coefficient_df.empty:

                            st.markdown("**Adjusted coefficient results**")

                            display_df = coefficient_df.copy()

                            for col in [
                                "Revenue coefficient (€)",
                                "95% CI lower (€)",
                                "95% CI upper (€)"
                            ]:
                                display_df[col] = display_df[col].map(
                                    lambda v: f"€{v:,.2f}"
                                )

                            display_df["p-value"] = (
                                coefficient_df["p-value"]
                                .map(format_p_value)
                            )

                            st.dataframe(
                                display_df,
                                **STRETCH,
                                hide_index=True
                            )

                            # --------------------------------------------
                            # COEFFICIENT CHART
                            # --------------------------------------------

                            section(
                                "Adjusted revenue associations",
                                "Estimated revenue change after controlling for weekday, month and other included factors. Error bars show 95% confidence intervals."
                            )

                            plot_df = coefficient_df.copy()

                            plot_df["label"] = plot_df["Factor"]

                            plot_df["colour"] = np.where(
                                plot_df["Revenue coefficient (€)"] >= 0,
                                C["teal"],
                                C["red"]
                            )

                            fig = go.Figure()

                            fig.add_trace(
                                go.Bar(
                                    x=plot_df["Revenue coefficient (€)"],
                                    y=plot_df["label"],
                                    orientation="h",
                                    marker_color=plot_df["colour"],
                                    error_x=dict(
                                        type="data",
                                        symmetric=False,
                                        array=(
                                            plot_df["95% CI upper (€)"]
                                            - plot_df["Revenue coefficient (€)"]
                                        ),
                                        arrayminus=(
                                            plot_df["Revenue coefficient (€)"]
                                            - plot_df["95% CI lower (€)"]
                                        ),
                                        visible=True
                                    ),
                                    hovertemplate=(
                                        "%{y}<br>"
                                        "Estimated change: €%{x:,.2f}"
                                        "<extra></extra>"
                                    )
                                )
                            )

                            fig.add_vline(
                                x=0,
                                line_dash="dash",
                                line_color=C["grey"]
                            )

                            fig.update_layout(
                                xaxis_title="Adjusted revenue difference (€)",
                                yaxis_title="",
                                showlegend=False
                            )

                            chart(fig, 350, unified=False)

                        # ------------------------------------------------
                        # INTERPRETATION
                        # ------------------------------------------------

                        st.markdown("**Model interpretation**")

                        significant_factors = coefficient_df[
                            coefficient_df["p-value"] < 0.05
                        ]

                        if significant_factors.empty:
                            st.info(
                                "None of the included weather or calendar "
                                "factors show a statistically significant "
                                "adjusted association at the 5% level."
                            )

                        else:
                            for _, row in significant_factors.iterrows():
                                direction = (
                                    "positive"
                                    if row["Revenue coefficient (€)"] > 0
                                    else "negative"
                                )

                                st.write(
                                    f"- **{row['Factor']}** has a "
                                    f"{direction} adjusted association "
                                    f"with revenue "
                                    f"(coefficient: "
                                    f"{money(row['Revenue coefficient (€)'], 2)}, "
                                    f"p-value: "
                                    f"{format_p_value(row['p-value'])})."
                                )

                        omitted = [
                            coefficient_labels[col]
                            for col in candidate_predictors
                            if col not in active_predictors
                        ]

                        if omitted:
                            st.caption(
                                "These factors could not be estimated "
                                "because they had no variation in the "
                                "selected period: "
                                + ", ".join(omitted)
                            )

                        st.caption(
                            "Model: ordinary least squares with Newey-West "
                            "HAC standard errors (7-day maximum lag), "
                            "weekday and month fixed effects. Coefficients "
                            "represent adjusted associations, not causal "
                            "effects. R-squared describes in-sample fit, "
                            "not out-of-sample predictive performance."
                        )


    


# =============================================================================
# Page: Workforce Planning
# =============================================================================

def page_workforce() -> None:
    hero("Capacity & labour", "Workforce Planning",
         "Compare forecast demand with the recommended roster and find uncovered role and shift combinations.")
    if forecast_mode:
        if forecast_available:
            st.info(
                f"Showing workforce planning for "
                f"{forecast_start:%d %b %Y} – {forecast_end:%d %b %Y}, "
                "based on the saved 14-day revenue and workforce forecasts."
            )
        else:
            st.warning(
                "The 14-day forecast is unavailable. Refresh the forecast first."
            )

    if forecast_mode:
        tab_fc, tab_hist = st.tabs([
            "14-day forecast",
            "Historical performance"
        ])
    else:
        tab_hist, tab_fc = st.tabs([
            "Historical performance",
            "14-day forecast"
        ])
    
    wf = output("workforce_forecast_next_14_days.csv", "date")

    with tab_hist:
        # Historical workforce performance
        section(
            "Historical workforce performance",
            f"Recorded shift activity from {start_d:%d %b %Y} to {end_d:%d %b %Y}."
        )

        if has_cols(shifts_data, "shift_date", "employee_id", "hours_worked", "labour_cost"):
            hist = shifts_data[
                shifts_data["shift_date"].between(
                    pd.Timestamp(start_d),
                    pd.Timestamp(end_d)
                )
            ].copy()

            if not hist.empty:
                hist = hist.merge(
                    employees[[
                        "employee_id",
                        "employee_name",
                        "role",
                        "employment_type"
                    ]],
                    on="employee_id",
                    how="left"
                )

                kpis([
                    ("Recorded shifts", integer(len(hist)), "Historical shift records"),
                    ("Employees scheduled", integer(hist["employee_id"].nunique()), "Unique employees"),
                    ("Total hours worked", f"{hist['hours_worked'].sum():,.1f}", "Recorded shift hours"),
                    ("Historical labour cost", money(hist["labour_cost"].sum()), "Recorded shift costs"),
                ])

                st.write("")

                
                # Row 1: Monthly trends
                left, right = st.columns(2)

                with left:
                    section(
                        "Monthly labour cost as % of revenue",
                        "Share of monthly restaurant revenue spent on recorded labour costs."
                    )

                    monthly_labour = (
                        hist.assign(
                            month=hist["shift_date"].dt.to_period("M").dt.to_timestamp()
                        )
                        .groupby("month", as_index=False)
                        .agg(
                            labour_cost=("labour_cost", "sum"),
                            hours_worked=("hours_worked", "sum")
                        )
                    )
                                        
                    # Monthly total restaurant revenue
                    monthly_revenue = (
                        daily_hist[
                            daily_hist["date"].between(
                                pd.Timestamp(start_d),
                                pd.Timestamp(end_d)
                            )
                        ]
                        .assign(
                            month=lambda df: df["date"].dt.to_period("M").dt.to_timestamp()
                        )
                        .groupby("month", as_index=False)
                        .agg(revenue=("revenue", "sum"))
                    )

                    # Combine monthly labour cost and monthly revenue
                    monthly_ratio = monthly_labour.merge(
                        monthly_revenue,
                        on="month",
                        how="left"
                    )

                    # Calculate labour cost as a percentage of revenue
                    monthly_ratio["labour_cost_pct"] = np.where(
                        monthly_ratio["revenue"] > 0,
                        monthly_ratio["labour_cost"] / monthly_ratio["revenue"] * 100,
                        np.nan
                    )

                    # Plot monthly labour cost ratio
                    fig = px.line(
                        monthly_ratio,
                        x="month",
                        y="labour_cost_pct",
                        markers=True,
                        labels={
                            "month": "Month",
                            "labour_cost_pct": "Labour cost / revenue (%)"
                        }
                    )

                    fig.update_traces(
                        line_color=C["teal"],
                        line_width=3,
                        marker_size=7
                    )

                    fig.update_yaxes(ticksuffix="%")
                    fig.update_xaxes(tickformat="%b %Y")

                    chart(fig, 330)


                with right:
                    section(
                        "Monthly working hours",
                        "Total recorded employee working hours per month."
                    )

                    fig = px.line(
                        monthly_labour,
                        x="month",
                        y="hours_worked",
                        markers=True,
                        labels={
                            "month": "Month",
                            "hours_worked": "Working hours"
                        }
                    )
                    fig.update_traces(
                        line_color=C["teal"],
                        line_width=3
                    )
                    fig.update_xaxes(tickformat="%b %Y")
                    chart(fig, 330)

                # Row 2: Employee workload
                left, right = st.columns(2)

                with left:
                    employee_hours = (
                        hist.groupby("employee_name", as_index=False)
                        .agg(
                            hours_worked=("hours_worked", "sum"),
                            shifts=("employee_id", "size"),
                            labour_cost=("labour_cost", "sum")
                        )
                        .sort_values("hours_worked", ascending=False)
                        .head(10)
                    )

                    section(
                        "Top 10 employees by working hours",
                        "Employees with the highest recorded working hours in the selected period."
                    )

                    fig = px.bar(
                        employee_hours.sort_values("hours_worked", ascending=False),
                        x="hours_worked",
                        y="employee_name",
                        orientation="h",
                        color="employee_name",
                        color_discrete_sequence=[
                            "#39865F",  # Green
                            "#319B83",  # Teal
                            "#78B7A0",  # Light teal
                            "#E3A13B",  # Amber
                            "#E58A55",  # Orange
                            "#6C91C2",  # Blue
                            "#9A82B8",  # Purple
                            "#D47F9B",  # Rose
                            "#8A9B65",  # Olive
                            "#A5A5A5"   # Grey
                        ],
                        labels={
                            "hours_worked": "Working hours",
                            "employee_name": "Employee"
                        }
                    )
                    fig.update_layout(showlegend=False)
                    chart(fig, 380)

                    st.caption(
                        "This ranking describes recorded shift hours, "
                        "not employee productivity or performance."
                    )

                with right:
                    weekday_hours = (
                        hist.assign(
                            weekday=hist["shift_date"].dt.day_name()
                        )
                        .groupby("weekday", as_index=False)
                        .agg(
                            hours_worked=("hours_worked", "sum"),
                            shifts=("employee_id", "size")
                        )
                    )

                    weekday_hours["weekday"] = pd.Categorical(
                        weekday_hours["weekday"],
                        categories=WEEKDAYS,
                        ordered=True
                    )
                    weekday_hours = weekday_hours.sort_values("weekday")

                    section(
                        "Workforce demand by weekday",
                        "Recorded working hours and shifts across the days of the week."
                    )

                    fig = px.bar(
                        weekday_hours,
                        x="weekday",
                        y="hours_worked",
                        labels={
                            "weekday": "Day",
                            "hours_worked": "Working hours"
                        }
                    )
                    fig.update_traces( marker_color=WORKFORCE_PALETTE[:len(weekday_hours)] )
                    chart(fig, 330)

                # Row 3: Role analysis
                ROLE_COLORS = {
                    "Waiter": "#E5A23B",
                    "Chef": "#38845F",
                    "Kitchen Assistant": "#7DB8A4",
                    "Bartender": "#528CCB",
                    "Dishwasher": "#329B87",
                    "Assistant Manager": "#9673B9",
                    "Restaurant Manager": "#40577D",
                }
                left, right = st.columns(2)

                with left:
                    role_hours = ( hist.groupby("role", as_index=False)["hours_worked"] .sum() .sort_values("hours_worked", ascending=True) )

                    section(
                        "Working hours by role",
                        "Total recorded working hours for each employee role."
                    )

                    fig = px.bar(
                        role_hours,
                        x="hours_worked",
                        y="role",
                        orientation="h",
                        labels={
                            "hours_worked": "Hours worked",
                            "role": "Employee role"
                        }
                    )
                    fig.update_traces( marker_color=[ ROLE_COLORS.get(role, "#808080") for role in role_hours["role"] ] )
                    chart(fig, 330)

                with right:
                    role_cost = ( hist.groupby("role", as_index=False)["labour_cost"] .sum() .sort_values("labour_cost", ascending=True) )

                    section(
                        "Labour cost by role",
                        "Total recorded labour expenditure across employee roles."
                    )

                    fig = px.bar(
                        role_cost,
                        x="labour_cost",
                        y="role",
                        orientation="h",
                        labels={
                            "labour_cost": f"Labour cost ({CURRENCY})",
                            "role": "Employee role"
                        }
                    )
                    fig.update_traces( marker_color=[ ROLE_COLORS.get(role, "#808080") for role in role_cost["role"] ] )
                    chart(fig, 330)

                # Row 4: Employee composition and average shift duration
                left, right = st.columns(2)

                with left:
                    employee_type = (
                        hist.groupby("employment_type", as_index=False)
                        .agg(
                            employees=("employee_id", "nunique")
                        )
                    )

                    # Keep a consistent display order
                    employment_order = [
                        "Full-time",
                        "Part-time",
                        "Minijob"
                    ]

                    employee_type["employment_type"] = pd.Categorical(
                        employee_type["employment_type"],
                        categories=employment_order,
                        ordered=True
                    )
                    employee_type = employee_type.sort_values("employment_type")

                    section(
                        "Employees by employment type",
                        "Number of unique employees with recorded shifts in the selected period."
                    )

                    fig = px.bar(
                        employee_type,
                        x="employment_type",
                        y="employees",
                        text="employees",
                        color="employment_type",
                        category_orders={
                            "employment_type": employment_order
                        },
                        color_discrete_sequence=[
                            "#39865F",
                            "#73B7A0",
                            "#E3A13B"
                        ],
                        labels={
                            "employment_type": "Employment type",
                            "employees": "Number of employees"
                        }
                    )

                    fig.update_traces(
                        textposition="outside",
                        textfont_size=13
                    )

                    fig.update_layout(
                        showlegend=False,
                        yaxis=dict(
                            rangemode="tozero",
                            dtick=2
                        )
                    )

                    chart(fig, 330)

                with right:
                    shift_summary = (
                                        hist.groupby("shift_type", as_index=False)
                                        .agg(
                                            shifts=("employee_id", "size"),
                                            hours=("hours_worked", "sum")
                                        )
                                    )
                    
                    shift_summary["avg_hours"] = (
                        shift_summary["hours"] / shift_summary["shifts"]
                        )
                    
                    section(
                        "Average shift duration",
                        "Average recorded working hours per shift type."
                    )

                    fig = px.bar(
                        shift_summary.sort_values("avg_hours"),
                        x="avg_hours",
                        y="shift_type",
                        orientation="h",
                        color="shift_type",
                        color_discrete_map={
                            "Lunch": "#39865F",
                            "Dinner": "#319B83",
                            "Full": "#E3A13B"
                        },
                        labels={
                            "avg_hours": "Average hours per shift",
                            "shift_type": "Service period"
                        }
                    )

                    fig.update_layout(showlegend=False)
                    fig.update_traces(
                        texttemplate="%{x:.1f} hrs",
                        textposition="outside"
                    )

                    chart(fig, 330)


            else:
                st.info("No historical shifts are available for the selected period.")
        else:
            st.warning("Historical shift data is missing required columns.")
        st.write("")
        
    with tab_fc:
        roster = output("recommended_roster.csv", "date")
        coverage = output("staffing_coverage.csv", "date")
        gaps = output("staffing_gaps.csv", "date")

        need = {"date", "required_staff", "scheduled_employees", "labour_cost", "forecast_revenue"}
        if not has_cols(wf, *need):
            unavailable("The workforce forecast")
        else:
            wf = wf.sort_values("date").reset_index(drop=True)
            forecast_reliability_warning()
            if "labour_cost_pct_revenue" not in wf:
                wf["labour_cost_pct_revenue"] = np.where(
                    wf["forecast_revenue"] > 0,
                    wf["labour_cost"] / wf["forecast_revenue"] * 100,
                    np.nan
                )
            target = st.slider("Target labour cost / revenue (%)", 20, 50, 33, 1,
                            help="Management target used to flag forecast days above the threshold.")
            total_cost, total_rev = wf["labour_cost"].sum(), wf["forecast_revenue"].sum()
            ratio = safe_div(total_cost, total_rev) * 100
            over = int((wf["labour_cost_pct_revenue"] > target).sum())
            unfilled = gaps["unfilled"].sum() if has_cols(gaps, "unfilled") else np.nan
            cov_rate = (coverage["coverage_status"].eq("Covered").mean() * 100) if has_cols(coverage, "coverage_status") else np.nan

            kpis([
                ("Forecast labour cost", money(total_cost), f"{wf['date'].min():%d %b} – {wf['date'].max():%d %b}"),
                ("Labour cost / revenue", pct(ratio), f"Target {target}%", {"delta_color": "off"}),
                ("Days above target", f"{over} of {len(wf)}", None),
                ("Unfilled positions", integer(unfilled), None, {"delta_color": "off"}),
                ("Role/shift coverage", pct(cov_rate), "Slots fully covered"),
            ])
            st.write("")

            l, r = st.columns([1.3, 1])
            with l:
                section("Required vs. scheduled employees", "Daily staffing requirement against the recommended roster headcount.")
                fig = go.Figure()
                fig.add_bar(x=wf["date"], y=wf["required_staff"], name="Required", marker_color=C["blue"])
                fig.add_bar(x=wf["date"], y=wf["scheduled_employees"], name="Scheduled", marker_color=C["teal"])
                fig.update_layout(barmode="group", yaxis_title="Employees")
                fig.update_xaxes(tickformat="%a %d")
                chart(fig, 330)
            with r:
                section("Labour cost ratio vs. target", "Bars above the dashed line exceed the selected target.")
                colors = np.where(wf["labour_cost_pct_revenue"] > target, C["red"], C["teal"])
                fig = go.Figure(go.Bar(x=wf["date"], y=wf["labour_cost_pct_revenue"], marker_color=colors, name="Labour / revenue"))
                fig.add_hline(y=target, line_dash="dash", line_color=C["ink"])
                fig.update_layout(yaxis_title="Labour cost / revenue (%)", showlegend=False)
                fig.update_xaxes(tickformat="%a %d")
                chart(fig, 330)

            l, r = st.columns(2)
            with l:
                section("Expected demand", "Expected orders and demand tier per day.")
                if has_cols(wf, "expected_orders"):
                    fig = px.bar(wf, x="date", y="expected_orders", color="demand_tier" if "demand_tier" in wf else None,
                                color_discrete_map={"High": C["blue"], "Standard": C["blue_soft"], "Low": C["grey"]},
                                labels={"date": "", "expected_orders": "Expected orders", "demand_tier": "Demand tier"})
                    fig.update_xaxes(tickformat="%a %d")
                    chart(fig, 300)
            with r:
                section("Labour productivity", "Forecast orders handled per labour hour.")
                if has_cols(wf, "forecast_orders_per_labour_hour"):
                    fig = px.line(wf, x="date", y="forecast_orders_per_labour_hour", markers=True,
                                labels={"date": "", "forecast_orders_per_labour_hour": "Orders / labour hour"})
                    fig.update_traces(line_color=C["teal"], line_width=3)
                    fig.update_xaxes(tickformat="%a %d")
                    chart(fig, 300)

            # =========================================================
            # WHERE GAPS OCCUR
            # =========================================================
            section(
                "Where gaps occur",
                "Unfilled positions by role, plus the day-by-day staffing shortfall."
            )

            l, r = st.columns([1, 1.3])

            # ---------------------------------------------------------
            # LEFT: UNFILLED POSITIONS BY ROLE
            # ---------------------------------------------------------
            with l:
                section(
                    "Unfilled positions by role",
                    "Total number of positions that could not be filled for each employee role."
                )

                if has_cols(gaps, "role", "unfilled"):
                    g = (
                        gaps.groupby("role", as_index=False)["unfilled"]
                        .sum()
                    )

                    role_colors = {
                        "Chef": "#38845F",
                        "Dishwasher": "#329B87",
                        "Kitchen Assistant": "#7DB8A4",
                        "Waiter": "#E5A23B",
                    }

                    fig = px.bar(
                        g,
                        y="role",
                        x="unfilled",
                        orientation="h",
                        color="role",
                        color_discrete_map=role_colors,
                        text="unfilled",
                        labels={
                            "unfilled": "Unfilled positions",
                            "role": "Employee role"
                        }
                    )

                    fig.update_traces(
                        textposition="outside",
                        cliponaxis=False,
                        showlegend=False
                    )

                    fig.update_layout(
                        xaxis_title="Unfilled positions",
                        yaxis_title="Employee role",
                        margin=dict(l=10, r=35, t=10, b=10)
                    )

                    chart(fig, 330, unified=False)

                else:
                    st.success("No staffing gaps recorded in the saved roster.")

            # ---------------------------------------------------------
            # RIGHT: DAILY STAFFING SHORTFALL HEAT MAP
            # ---------------------------------------------------------
            with r:
                section(
                    "Daily staffing shortfall by role",
                    "Darker red cells indicate more unfilled positions for a role on a particular day."
                )

                if has_cols(coverage, "date", "role", "shortfall"):

                    piv = (
                        coverage.groupby(["role", "date"])["shortfall"]
                        .sum()
                        .reset_index()
                        .pivot(
                            index="role",
                            columns="date",
                            values="shortfall"
                        )
                        .fillna(0)
                    )

                    piv = piv.reindex(
                        ["Assistant Manager", "Bartender", "Chef",
                         "Dishwasher", "Kitchen Assistant",
                         "Restaurant Manager", "Waiter"]
                    ).dropna(how="all")

                    piv.columns = [
                        c.strftime("%a %d") for c in piv.columns
                    ]

                    fig = px.imshow(
                        piv,
                        aspect="auto",
                        color_continuous_scale=[
                            "#F9EEEE",
                            "#E9B8B8",
                            "#C95B55"
                        ],
                        labels={
                            "x": "Date",
                            "y": "Employee role",
                            "color": "Shortfall"
                        }
                    )
                    fig.update_xaxes(
                        tickangle=50
                    )
                    fig.update_layout(
                        margin=dict(l=10, r=10, t=10, b=10)
                    )

                    chart(fig, 330, unified=False)

                else:
                    st.caption("Staffing coverage data is unavailable.")
            
            # Weekly employee hour-cap monitoring
            if not roster.empty and has_cols(
                roster,
                "employee_id",
                "employee_name",
                "date",
                "hours",
                "employment_type"
            ):
                weekly = roster.copy()

                iso = weekly["date"].dt.isocalendar()
                weekly["iso_year"] = iso.year.astype(int)
                weekly["iso_week"] = iso.week.astype(int)

                weekly = (
                    weekly.groupby(
                        [
                            "employee_id",
                            "employee_name",
                            "employment_type",
                            "iso_year",
                            "iso_week"
                        ],
                        as_index=False
                    )
                    .agg(weekly_hours=("hours", "sum"))
                )

                weekly_cap_map = {
                    "Full-time": 40.0,
                    "Part-time": 30.0,
                    "Minijob": 12.0
                }

                weekly["weekly_cap"] = (
                    weekly["employment_type"].map(weekly_cap_map)
                )

                weekly = weekly.dropna(subset=["weekly_cap"])

                weekly["remaining_hours"] = (
                    weekly["weekly_cap"] - weekly["weekly_hours"]
                ).clip(lower=0)

                weekly["utilisation_pct"] = (
                    weekly["weekly_hours"] / weekly["weekly_cap"] * 100
                )

                weekly["employee_week"] = (
                    weekly["employee_name"]
                    + " (W"
                    + weekly["iso_week"].astype(str)
                    + ")"
                )

                # Show the 10 employees closest to their weekly cap
                # grouped by calendar week.
                weekly = (
                    weekly.sort_values("utilisation_pct", ascending=False)
                    .head(15)
                    .sort_values(["iso_year", "iso_week", "utilisation_pct"],
                                 ascending=[True, False, False]))

                section(
                    "Weekly employee capacity utilisation",
                    "Recommended roster hours compared with each employee's weekly contractual limit."
                )

                fig = go.Figure()

                fig.add_bar(
                    y=weekly["employee_week"],
                    x=weekly["weekly_hours"],
                    name="Recommended hours",
                    orientation="h",
                    marker_color=C["red"]
                )

                fig.add_bar(
                    y=weekly["employee_week"],
                    x=weekly["remaining_hours"],
                    name="Hours remaining to cap",
                    orientation="h",
                    marker_color=C["teal"]
                )

                fig.update_layout(
                    barmode="stack",
                    xaxis_title="Hours in forecast week",
                    yaxis_title="",
                    legend=dict(
                        orientation="h",
                        y=1.12,
                        x=0
                    )
                )

                for _, row in weekly.iterrows():
                    fig.add_annotation(
                        x=row["weekly_cap"],
                        y=row["employee_week"],
                        text=(
                            f"{row['weekly_hours']:.1f}/"
                            f"{row['weekly_cap']:.0f} hrs "
                            f"({row['utilisation_pct']:.0f}%)"
                        ),
                        showarrow=False,
                        xshift=55,
                        font=dict(size=11, color=C["ink"])
                    )

                fig.update_xaxes(range=[
                    0,
                    float(weekly["weekly_cap"].max()) * 1.35
                ])

                chart(fig, 380)

            
            # ============================================================
            # WEEKLY STAFF ROSTER
            # ============================================================

            if not roster.empty and has_cols(
                roster, "date", "employee_name", "role", "shift_type", "hours"
            ):
                section(
                    "Weekly Staff Roster",
                    "Employee assignments and shift times across the selected week."
                )

                # Ensure dates are datetime values
                roster["date"] = pd.to_datetime(roster["date"])

                # Create ISO week labels
                roster["iso_year"] = roster["date"].dt.isocalendar().year
                roster["iso_week"] = roster["date"].dt.isocalendar().week

                week_options = (
                    roster[["iso_year", "iso_week"]]
                    .drop_duplicates()
                    .sort_values(["iso_year", "iso_week"])
                )

                week_options["label"] = week_options.apply(
                    lambda row: (
                        f"Week {int(row['iso_week'])} "
                        f"({row['iso_year']})"
                    ),
                    axis=1
                )

                week_labels = week_options["label"].tolist()

                selected_week = st.selectbox(
                    "Select week",
                    week_labels,
                    index=len(week_labels) - 1,
                    key="weekly_roster_selector"
                )

                selected = week_options[
                    week_options["label"] == selected_week
                ].iloc[0]

                week_roster = roster[
                    (roster["iso_year"] == selected["iso_year"]) &
                    (roster["iso_week"] == selected["iso_week"])
                ].copy()

                # Monday to Sunday dates
                week_start = (
                    week_roster["date"].min()
                    - pd.to_timedelta(
                        week_roster["date"].min().weekday(), unit="D"
                    )
                ).normalize()

                week_dates = pd.date_range(
                    start=week_start,
                    periods=7,
                    freq="D"
                )

                # Sort employees by role, then employee name
                role_order = [
                    "Assistant Manager",
                    "Bartender",
                    "Chef",
                    "Dishwasher",
                    "Kitchen Assistant",
                    "Restaurant Manager",
                    "Waiter"
                ]

                week_roster["role_order"] = (
                    week_roster["role"]
                    .map({role: i for i, role in enumerate(role_order)})
                    .fillna(len(role_order))
                )

                roster_employees = (
                    week_roster[
                        ["role", "employee_name", "role_order"]
                    ]
                    .drop_duplicates()
                    .sort_values(
                        ["role_order", "role", "employee_name"]
                    )
                    .reset_index(drop=True)
                )

                # Shift colours
                shift_colors = {
                    "Lunch": "#D9EEF8",
                    "Dinner": "#FCE6CF",
                    "Full": "#E8E0F2"
                }

                shift_text_colors = {
                    "Lunch": "#15577A",
                    "Dinner": "#98500F",
                    "Full": "#594477"
                }

                # Build heatmap values and labels
                z_values = []
                cell_text = []
                hover_text = []

                shift_codes = {
                    "Off": 0,
                    "Lunch": 1,
                    "Dinner": 2,
                    "Full": 3
                }

                for _, employee in roster_employees.iterrows():
                    employee_rows = week_roster[
                        (week_roster["employee_name"] == employee["employee_name"]) &
                        (week_roster["role"] == employee["role"])
                    ]

                    row_values = []
                    row_text = []
                    row_hover = []

                    for day in week_dates:
                        day_rows = employee_rows[
                            employee_rows["date"].dt.normalize() == day
                        ]

                        if day_rows.empty:
                            row_values.append(0)
                            row_text.append("—")
                            row_hover.append(
                                f"{employee['employee_name']}<br>"
                                f"{employee['role']}<br>"
                                f"{day:%A %d %b}<br>Day off"
                            )
                        else:
                            shift = day_rows.iloc[0]["shift_type"]
                            hours = day_rows.iloc[0]["hours"]

                            shift_code = shift_codes.get(shift, 0)

                            start = str(day_rows.iloc[0]["start_time"])[:5]
                            end = str(day_rows.iloc[0]["end_time"])[:5]

                            row_values.append(shift_code)

                            row_text.append(
                                f"{shift}<br>{start}–{end}"
                            )

                            row_hover.append(
                                f"{employee['employee_name']}<br>"
                                f"{employee['role']}<br>"
                                f"{day:%A %d %b}<br>"
                                f"{shift}<br>{start} – {end}"
                            )

                    z_values.append(row_values)
                    cell_text.append(row_text)
                    hover_text.append(row_hover)

                # Discrete colour scale
                colorscale = [
                    [0.00, "#F0F2F0"],
                    [0.2499, "#F0F2F0"],
                    [0.25, shift_colors["Lunch"]],
                    [0.4999, shift_colors["Lunch"]],
                    [0.50, shift_colors["Dinner"]],
                    [0.7499, shift_colors["Dinner"]],
                    [0.75, shift_colors["Full"]],
                    [1.00, shift_colors["Full"]]
                ]

                # Employee labels
                employee_labels = [
                    f"{row['role']}  |  {row['employee_name']}"
                    for _, row in roster_employees.iterrows()
                ]

                fig = go.Figure(
                    go.Heatmap(
                        z=z_values,
                        x=[day.strftime("%a %d %b") for day in week_dates],
                        y=employee_labels,
                        text=cell_text,
                        customdata=hover_text,
                        colorscale=colorscale,
                        zmin=0,
                        zmax=3,
                        showscale=False,
                        xgap=2,
                        ygap=2,
                        texttemplate="%{text}",
                        textfont=dict(size=10, color=C["ink"]),
                        hovertemplate="%{customdata}<extra></extra>"
                    )
                )

                fig.update_layout(
                    height=max(450, len(employees) * 38 + 130),
                    margin=dict(l=10, r=10, t=20, b=20),
                    xaxis=dict(
                        side="top",
                        title="",
                        tickangle=0,
                        tickfont=dict(size=11),
                        showgrid=False
                    ),
                    yaxis=dict(
                        title="",
                        autorange="reversed",
                        tickfont=dict(size=10),
                        showgrid=False
                    ),
                    plot_bgcolor="white",
                    paper_bgcolor="white"
                )

                chart(fig, max(450, len(employees) * 38 + 130), unified=False)

                # Shift legend
                st.markdown(
                    f"""
                    <div style="display:flex; gap:22px; flex-wrap:wrap;
                                margin: 4px 0 12px 4px; font-size:13px;">
                        <span>
                            <span style="background:{shift_colors['Lunch']};
                            padding:4px 12px; border-radius:4px;"></span>
                            Lunch
                        </span>
                        <span>
                            <span style="background:{shift_colors['Dinner']};
                            padding:4px 12px; border-radius:4px;"></span>
                            Dinner
                        </span>
                        <span>
                            <span style="background:{shift_colors['Full']};
                            padding:4px 12px; border-radius:4px;"></span>
                            Full
                        </span>
                        <span>
                            <span style="background:#F0F2F0;
                            padding:4px 12px; border-radius:4px;"></span>
                            Day off
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Download selected week's roster
                weekly_download = (
                    week_roster
                    .drop(
                        columns=["iso_year", "iso_week", "role_order"],
                        errors="ignore"
                    )
                    .sort_values(
                        ["date", "role", "employee_name"]
                    )
                    .reset_index(drop=True)
                )

                download(
                    weekly_download,
                    "Download weekly roster (CSV)",
                    "weekly_roster.csv",
                    "dl_weekly_roster"
                )


            else:
                st.info("Weekly roster data is not available.")

            


            # ---------------------------------------------------------
            # ROSTER PLANNER
            # ---------------------------------------------------------
            with st.expander("Roster explorer", expanded=False):
                if roster.empty:
                    unavailable("The recommended roster")
                else:
                    roster = roster.copy()

                    # Create ISO week labels
                    iso = roster["date"].dt.isocalendar()
                    roster["week"] = (
                        iso["year"].astype(str)
                        + "-W"
                        + iso["week"].astype(str).str.zfill(2)
                    )

                    # Filters
                    f1, f2, f3, f4 = st.columns(4)

                    roles = f1.multiselect(
                        "Role",
                        sorted(roster["role"].dropna().unique())
                        if "role" in roster else []
                    )

                    shifts = f2.multiselect(
                        "Shift",
                        sorted(roster["shift_type"].dropna().unique())
                        if "shift_type" in roster else []
                    )

                    weeks = f3.multiselect(
                        "Week",
                        sorted(roster["week"].unique())
                    )

                    days = f4.multiselect(
                        "Date",
                        sorted(roster["date"].dt.strftime("%Y-%m-%d").unique())
                    )

                    # Apply filters
                    view = roster.copy()

                    if roles:
                        view = view[view["role"].isin(roles)]

                    if shifts:
                        view = view[view["shift_type"].isin(shifts)]

                    if weeks:
                        view = view[view["week"].isin(weeks)]

                    if days:
                        view = view[
                            view["date"].dt.strftime("%Y-%m-%d").isin(days)
                        ]

                    view = view.sort_values(
                        ["date", "start_time", "employee_name"]
                    )

                    # Summary
                    st.caption(
                        f"{len(view):,} shifts · "
                        f"{view['hours'].sum():,.1f} hours · "
                        f"{money(view['labour_cost'].sum())} labour cost"
                    )

                    # Prepare display table
                    shown = view.assign(
                        date=view["date"].dt.strftime("%a %d %b")
                    )

                    cols = [
                        c for c in [
                            "date", "week", "employee_name", "role",
                            "employment_type", "shift_type",
                            "start_time", "end_time", "hours", "labour_cost"
                        ]
                        if c in shown
                    ]

                    display = shown[cols].rename(columns={
                        "date": "Date",
                        "week": "Week",
                        "employee_name": "Employee",
                        "role": "Role",
                        "employment_type": "Contract",
                        "shift_type": "Shift",
                        "start_time": "Start",
                        "end_time": "End",
                        "hours": "Hours",
                        "labour_cost": "Labour cost"
                    })

                    # Colour-coded table
                    styled = (
                        display.style
                        .map(
                            lambda x: (
                                "background-color: #E3F1E9; color: #286344; font-weight: 600"
                                if x == "Lunch"
                                else "background-color: #DDF1EC; color: #267D70; font-weight: 600"
                                if x == "Dinner"
                                else "background-color: #FFF0D5; color: #98651D; font-weight: 600"
                                if x == "Full"
                                else ""
                            ),
                            subset=["Shift"]
                        )
                        .map(
                            lambda x: (
                                "background-color: #E8F0FA; color: #315C88"
                                if x == "Full-time"
                                else "background-color: #F3EAF8; color: #79518E"
                                if x == "Part-time"
                                else ""
                            ),
                            subset=["Contract"]
                        )
                        .format({
                            "Hours": "{:.1f}",
                            "Labour cost": "€{:,.2f}"
                        })
                    )

                    st.dataframe(
                        styled,
                        **STRETCH,
                        hide_index=True,
                        height=420
                    )

                    download(
                        view.drop(columns=["week"], errors="ignore"),
                        "Download roster (CSV)",
                        "recommended_roster.csv",
                        "dl_roster"
                    )

            # ---------------------------------------------------------
            # STAFFING GAP DETAILS
            # ---------------------------------------------------------
            
            with st.expander("Staffing gap details", expanded=False):
                if has_cols(gaps, "date"):
                    if gaps.empty:
                        st.success("No staffing gaps recorded.")
                    else:
                        g = gaps.copy()

                        # Human-readable explanations
                        
                        def explain_gap_reason(reason):
                            if pd.isna(reason) or not str(reason).strip():
                                return "No reason recorded"

                            import re

                            reason = str(reason)
                            explanations = []

                            patterns = [
                                (
                                    r"only (\d+) eligible employee\(s\) for (\d+) required position\(s\)",
                                    lambda m: (
                                        f"Insufficient qualified staff: "
                                        f"{m.group(1)} available, {m.group(2)} needed"
                                    )
                                ),
                                (
                                    r"unavailable that weekday(?: \((\d+) employee\(s\)\))?",
                                    lambda m: (
                                        f"{m.group(1) + ' ' if m.group(1) else ''}"
                                        f"employee(s) unavailable on this day"
                                    )
                                ),
                                (
                                    r"already working that day(?: \((\d+) employee\(s\)\))?",
                                    lambda m: (
                                        f"{m.group(1) + ' ' if m.group(1) else ''}"
                                        f"employee(s) already assigned"
                                    )
                                ),
                                (
                                    r"employment ended(?: \((\d+) employee\(s\)\))?",
                                    lambda m: "Former employees excluded from scheduling"
                                ),
                                (
                                    r"insufficient daily hours(?: \((\d+) employee\(s\)\))?",
                                    lambda m: "Employees lack sufficient remaining daily hours"
                                ),
                                (
                                    r"weekly hour cap reached(?: \((\d+) employee\(s\)\))?",
                                    lambda m: (
                                        f"Weekly working-hour limit reached"
                                        f"{f' ({m.group(1)} employees)' if m.group(1) else ''}"
                                    )
                                ),
                            ]

                            for part in reason.split(";"):
                                part = part.strip()
                                matched = False

                                for pattern, explanation in patterns:
                                    match = re.search(pattern, part, flags=re.IGNORECASE)

                                    if match:
                                        explanations.append(explanation(match))
                                        matched = True
                                        break

                                if not matched and part:
                                    explanations.append(part)

                            # Remove duplicate explanations
                            explanations = list(dict.fromkeys(explanations))

                            if not explanations:
                                return "No specific constraint identified"

                            return " | ".join(explanations)


                        # Prepare management-facing table
                        g["date"] = pd.to_datetime(g["date"]).dt.strftime("%a %d %b")

                        if "reason" in g.columns:
                            g["management_reason"] = g["reason"].apply(
                                explain_gap_reason
                            )
                        else:
                            g["management_reason"] = "No explanation recorded"

                        display = g.rename(columns={
                            "date": "Date",
                            "weekday": "Weekday",
                            "role": "Role",
                            "shift_type": "Shift",
                            "hours": "Shift hours",
                            "required": "Staff required",
                            "assigned": "Staff assigned",
                            "unfilled": "Unfilled positions",
                            "management_reason": "Why the gap occurred"
                        })

                        display_cols = [
                            "Date",
                            "Weekday",
                            "Role",
                            "Shift",
                            "Shift hours",
                            "Staff required",
                            "Staff assigned",
                            "Unfilled positions",
                            "Why the gap occurred"
                        ]

                        display_cols = [
                            col for col in display_cols if col in display.columns
                        ]

                        display = display[display_cols]

                        # Colour-code unfilled positions
                        def highlight_gaps(row):
                            styles = [""] * len(row)

                            if "Unfilled positions" in row.index:
                                idx = row.index.get_loc("Unfilled positions")
                                value = row["Unfilled positions"]

                                if pd.notna(value) and value >= 3:
                                    styles[idx] = (
                                        "background-color: #F8D7DA; "
                                        "color: #842029; font-weight: bold"
                                    )
                                elif pd.notna(value) and value > 0:
                                    styles[idx] = (
                                        "background-color: #FFF0CC; "
                                        "color: #8A5700; font-weight: bold"
                                    )

                            return styles

                        styled = display.style.apply(
                            highlight_gaps, axis=1
                        )

                        st.caption(
                            f"{len(display):,} staffing gap records · "
                            f"{int(gaps['unfilled'].sum())} total unfilled positions"
                        )

                        st.dataframe(
                            styled,
                            **STRETCH,
                            hide_index=True,
                            height=380,
                            column_config={
                                "Shift hours": st.column_config.NumberColumn(
                                    "Shift hours",
                                    format="%.1f"
                                ),
                                "Staff required": st.column_config.NumberColumn(
                                    "Required",
                                    format="%d"
                                ),
                                "Staff assigned": st.column_config.NumberColumn(
                                    "Assigned",
                                    format="%d"
                                ),
                                "Unfilled positions": st.column_config.NumberColumn(
                                    "Unfilled",
                                    format="%d"
                                ),
                                "Why the gap occurred": st.column_config.TextColumn(
                                    "Management explanation",
                                    width="large",
                                    help="Constraints that prevented the required positions from being filled."
                                )
                            }
                        )

                        download(
                            gaps,
                            "Download staffing gaps (CSV)",
                            "staffing_gaps.csv",
                            "dl_gaps"
                        )
                else:
                    st.caption("No staffing gap records.")


            callout("The roster is a model recommendation, not a confirmed schedule. Verify availability, contracts, labour law, "
                    "qualifications and manager approval before operational use. Labour cost excludes other operating costs.", "note")


# =============================================================================
# Page: Customer Intelligence
# =============================================================================

def page_customers() -> None:
    hero("Voice of customer", "Customer Intelligence",
         "Review sentiment, customer value segments and recurring experience themes.")
    if forecast_mode:
        st.info(
            "Customer Intelligence is based on historical customer and review data. "
            "There are no customer forecasts for the next 14 days."
        )
        return
    callout("Customer outputs summarise the full historical dataset and are not affected by the sidebar filters. "
            "Aspect sentiments are supplied synthetic annotations, not predictions from a trained NLP model.", "info")

    kv = kpi_lookup(output("customer_intelligence_kpis.csv"))
    summary = meta("customer_intelligence_summary.json")
    segments = output("customer_segment_profile.csv")
    aspects = output("customer_aspect_sentiment_summary.csv")
    monthly = output("customer_monthly_sentiment.csv")
    improve = output("customer_improvement_areas.csv")
    by_type = output("customer_feedback_by_type.csv")
    ratings = output("customer_ratings_by_type.csv")
    detail = output("customer_review_aspect_detail.csv", "review_date")
    high_neg = output("high_value_negative_feedback.csv", "review_date")
    rfm = output("customer_rfm_segments.csv")

    avg_rating = kv.get("Average Rating", np.nan)
    kpis([
        ("Reviews", integer(kv.get("Total Reviews", np.nan)), None),
        ("Reviewing customers", integer(kv.get("Customers Who Reviewed", np.nan)), None),
        ("Average rating", f"{avg_rating:.2f} / 5" if pd.notna(avg_rating) else "—", None),
        ("Positive mentions", pct(kv.get("Positive Sentiment (%)", np.nan)), None),
        ("Negative mentions", pct(kv.get("Negative Sentiment (%)", np.nan)), None),
    ])
    st.write("")

    t_sent, t_seg, t_voice, t_risk = st.tabs(["Sentiment", "Segments", "Review explorer", "High-value risk"])

    with t_sent:
        l, r = st.columns(2)
        with l:
            section("Negative share over time", "Share of aspect mentions that are negative, by month.")
            if has_cols(monthly, "review_month", "Negative (%)"):
                m = monthly.assign(month=pd.to_datetime(monthly["review_month"], format="%Y-%m", errors="coerce"))
                fig = px.line(m, x="month", y="Negative (%)", markers=True, labels={"month": "", "Negative (%)": "Negative mentions (%)"})
                fig.update_traces(line_color=C["red"], line_width=3)
                chart(fig, 330)
            else:
                unavailable("Monthly sentiment")
        with r:
            section("Sentiment by experience aspect", "Mix of positive, neutral and negative mentions per aspect.")
            if has_cols(aspects, "aspect", "Positive (%)", "Neutral (%)", "Negative (%)"):
                a = aspects.sort_values("Negative (%)")
                fig = go.Figure()
                for s in ["Positive", "Neutral", "Negative"]:
                    fig.add_bar(y=a["aspect"], x=a[f"{s} (%)"], name=s, orientation="h", marker_color=SENTIMENT_COLORS[s])
                fig.update_layout(barmode="stack", xaxis_title="Share of mentions (%)")
                chart(fig, 330, unified=False)
            else:
                unavailable("Aspect sentiment")
        l, r = st.columns(2)
        with l:
            section("Sentiment by customer type")
            if has_cols(by_type, "customer_type", "Positive (%)", "Neutral (%)", "Negative (%)"):
                fig = go.Figure()
                for s in ["Positive", "Neutral", "Negative"]:
                    fig.add_bar(x=by_type["customer_type"], y=by_type[f"{s} (%)"], name=s, marker_color=SENTIMENT_COLORS[s])
                fig.update_layout(barmode="stack", yaxis_title="Share of mentions (%)")
                chart(fig, 300)
        with r:
            section("Average rating by customer type")
            if has_cols(ratings, "customer_type", "Average_Rating"):
                fig = px.bar(ratings, x="customer_type", y="Average_Rating", text="Average_Rating",
                             labels={"customer_type": "", "Average_Rating": "Average rating"})
                fig.update_traces(marker_color=C["blue"], textposition="outside")
                fig.update_yaxes(range=[0, 5])
                chart(fig, 300, unified=False)

    with t_seg:
        l, r = st.columns([1.2, 1])
        with l:
            section("RFM segments", "Tile size = customers; colour = revenue contribution.")
            if has_cols(segments, "RFM_Segment", "Customer_Count", "Total_Revenue"):
                fig = px.treemap(segments, path=["RFM_Segment"], values="Customer_Count", color="Total_Revenue",
                                 color_continuous_scale=["#DCE6FF", C["blue"]])
                fig.update_traces(texttemplate="<b>%{label}</b><br>%{value:,} customers")
                chart(fig, 340, unified=False)
            else:
                unavailable("Segment profile")
        with r:
            section("Revenue concentration", "Revenue share by segment.")
            if has_cols(segments, "RFM_Segment", "Total_Revenue"):
                s = segments.assign(share=segments["Total_Revenue"] / segments["Total_Revenue"].sum() * 100).sort_values("share")
                fig = px.bar(s, x="share", y="RFM_Segment", orientation="h", text=s["share"].map(lambda v: f"{v:.0f}%"),
                             labels={"share": "Share of revenue (%)", "RFM_Segment": ""})
                fig.update_traces(marker_color=C["teal"], textposition="outside")
                chart(fig, 340, unified=False)
        if not segments.empty:
            table(segments, 260, {
                "Average_Recency": num_col("Avg recency (days)", 0), "Average_Frequency": num_col("Avg orders", 1),
                "Average_Monetary": money_col("Avg spend", 0), "Total_Revenue": money_col("Total revenue", 0),
                "Customer_Count": num_col("Customers", 0), "RFM_Segment": "Segment"})
        if has_cols(rfm, "Frequency", "Monetary", "RFM_Segment"):
            section("Customer value map", "Random sample of up to 1,500 customers.")
            sample = rfm.sample(min(1500, len(rfm)), random_state=7)
            fig = px.scatter(sample, x="Frequency", y="Monetary", color="RFM_Segment", opacity=.6,
                             labels={"Frequency": "Orders", "Monetary": f"Lifetime spend ({CURRENCY})", "RFM_Segment": "Segment"})
            chart(fig, 360, unified=False)

    with t_voice:
        section("Improvement priorities", "Aspects ranked by negative mentions.")
        if has_cols(improve, "Aspect", "Negative Mentions", "Negative Share (%)"):
            imp = improve.sort_values("Negative Mentions")
            fig = px.bar(imp, x="Negative Mentions", y="Aspect", orientation="h", color="Negative Share (%)",
                         color_continuous_scale=["#F6CDCF", C["red"]])
            chart(fig, 320, unified=False)
        section("Review explorer", "Filter aspect-level review records. Showing up to 300 rows.")
        if has_cols(detail, "aspect", "sentiment", "rating", "review_text"):
            f1, f2, f3, f4 = st.columns(4)
            asp = f1.multiselect("Aspect", sorted(detail["aspect"].dropna().unique()))
            sen = f2.multiselect("Sentiment", ["Positive", "Neutral", "Negative"])
            typ = f3.multiselect("Customer type", sorted(detail["customer_type"].dropna().unique()) if "customer_type" in detail else [])
            rat = f4.slider("Rating", 1, 5, (1, 5))
            q = st.text_input("Search review text", placeholder="e.g. waiting, pizza, friendly")
            v = detail[detail["rating"].between(*rat)]
            if asp:
                v = v[v["aspect"].isin(asp)]
            if sen:
                v = v[v["sentiment"].isin(sen)]
            if typ:
                v = v[v["customer_type"].isin(typ)]
            if q.strip():
                v = v[v["review_text"].str.contains(q.strip(), case=False, na=False, regex=False)]
            st.caption(f"{len(v):,} matching aspect mentions")
            cols = [c for c in ["review_date", "aspect", "sentiment", "rating", "customer_type", "order_type", "review_text"] if c in v]
            table(v[cols].sort_values("review_date", ascending=False).head(300), 380,
                  {"review_date": st.column_config.DateColumn("Date"), "review_text": st.column_config.TextColumn("Review", width="large")})
        else:
            unavailable("Review detail")

    with t_risk:
        thr = summary.get("rfm", {}).get("high_value_spending_threshold")
        n_hv = summary.get("rfm", {}).get("high_value_customers_with_negative_feedback")
        callout("High-value customers who left negative feedback deserve a personal follow-up."
                + (f" The high-value threshold is lifetime spend above {money(thr)}." if thr else ""), "info")
        if has_cols(high_neg, "RFM_Segment", "aspect"):
            if n_hv:
                st.metric("High-value customers with negative feedback", integer(n_hv))
            f1, f2 = st.columns(2)
            seg = f1.multiselect("Segment", sorted(high_neg["RFM_Segment"].dropna().unique()), key="hv_seg")
            asp = f2.multiselect("Aspect", sorted(high_neg["aspect"].dropna().unique()), key="hv_asp")
            v = high_neg
            if seg:
                v = v[v["RFM_Segment"].isin(seg)]
            if asp:
                v = v[v["aspect"].isin(asp)]
            cols = [c for c in ["customer_id", "review_date", "aspect", "rating", "RFM_Segment", "Frequency", "Monetary", "review_text"] if c in v]
            table(v[cols].sort_values("Monetary", ascending=False) if "Monetary" in v else v[cols], 420,
                  {"Monetary": money_col("Lifetime spend", 0), "review_date": st.column_config.DateColumn("Date"),
                   "review_text": st.column_config.TextColumn("Review", width="large")})
            download(v, "Download follow-up list (CSV)", "high_value_negative_feedback.csv", "dl_hv")
        else:
            unavailable("High-value negative feedback")


# =============================================================================
# Page: Menu Performance
# =============================================================================

def boundary(df: pd.DataFrame, flag: str, value: str) -> Optional[float]:
    """Infer the threshold that separates 'High' from 'Low' classes in the saved menu engineering output."""
    if not has_cols(df, flag, value):
        return None
    hi, lo = df.loc[df[flag] == "High", value], df.loc[df[flag] == "Low", value]
    if hi.empty or lo.empty:
        return None
    return float((hi.min() + lo.max()) / 2)


def page_menu() -> None:
    hero("Product & menu economics", "Menu Performance",
         "Product contribution, category mix, discounting and menu-engineering actions.")
    if forecast_mode:
        st.info(
            "Menu Performance is based on historical product sales and costs. "
            "There are no future menu or product sales forecasts for the next 14 days."
        )
        return
    callout("<b>Gross profit</b> = item revenue less product cost only. It excludes labour, rent, utilities, delivery "
            "fees and other operating expenses. Performance views respect the sidebar filters; the menu-engineering "
            "classification is a saved full-period analysis.", "info")

    L = ctx.items
    if has_cols(L, "category", "gross_profit"):
        rev, gp, units = L["line_total"].sum(), L["gross_profit"].sum(), L["quantity"].sum()
        disc = L["discount_value"].sum() if "discount_value" in L else np.nan
        kpis([
            ("Units sold", integer(units), None),
            ("Item revenue", money(rev), ctx.label),
            ("Gross profit", money(gp), "Before operating costs"),
            ("Gross margin", pct(safe_div(gp, rev) * 100), None),
            ("Discounts given", money(disc), pct(safe_div(disc, rev + disc) * 100) + " of list value"),
        ])
    else:
        kv = kpi_lookup(output("menu_intelligence_kpis.csv"))
        kpis([
            ("Units sold", integer(kv.get("Total units sold", np.nan)), None),
            ("Item revenue", money(kv.get("Total item revenue", np.nan)), None),
            ("Gross profit", money(kv.get("Total gross profit", np.nan)), None),
            ("Gross margin", pct(kv.get("Overall gross margin (%)", np.nan)), None),
            ("Products sold", integer(kv.get("Unique products sold", np.nan)), None),
        ])
    st.write("")

    t_perf, t_eng, t_disc = st.tabs(["Category & product performance", "Menu engineering", "Discounts & trends"])

    with t_perf:
        if not has_cols(L, "category", "gross_profit"):
            unavailable("Item-level data")
        else:
            cat = L.groupby("category", as_index=False).agg(revenue=("line_total", "sum"), gross_profit=("gross_profit", "sum"), units=("quantity", "sum"))
            cat["margin"] = cat["gross_profit"] / cat["revenue"] * 100
            a, b = st.columns(2)
            with a:
                section("Revenue and gross profit by category")
                c = cat.sort_values("revenue")
                fig = go.Figure()
                fig.add_bar(y=c["category"], x=c["revenue"], name="Revenue", orientation="h", marker_color=C["blue"])
                fig.add_bar(y=c["category"], x=c["gross_profit"], name="Gross profit", orientation="h", marker_color=C["teal"])
                fig.update_layout(barmode="group", xaxis_title=CURRENCY)
                chart(fig, 340, unified=False)
            with b:
                section("Gross margin by category")
                fig = px.bar(cat.sort_values("margin"), x="margin", y="category", orientation="h",
                             text=cat.sort_values("margin")["margin"].map(lambda v: f"{v:.0f}%"),
                             labels={"margin": "Gross margin (%)", "category": ""})
                fig.update_traces(marker_color=C["amber"], textposition="outside")
                chart(fig, 340, unified=False)

            prod = L.groupby(["product_name", "category"], as_index=False).agg(
                units=("quantity", "sum"), revenue=("line_total", "sum"), gross_profit=("gross_profit", "sum"))
            prod["margin"] = prod["gross_profit"] / prod["revenue"] * 100
            n = st.slider("Products shown", 5, min(20, len(prod)), min(10, len(prod)), key="menu_topn") if len(prod) > 5 else len(prod)
            metric = st.radio("Rank by", ["Gross profit", "Revenue", "Units"], horizontal=True)
            col = {"Gross profit": "gross_profit", "Revenue": "revenue", "Units": "units"}[metric]
            top = prod.nlargest(n, col).sort_values(col)
            section(f"Top {n} products by {metric.lower()}")
            fig = px.bar(top, x=col, y="product_name", color="category", orientation="h",
                         labels={col: metric, "product_name": "", "category": "Category"}, color_discrete_sequence=CATEGORY_SEQ)
            chart(fig, max(320, 26 * n + 80), unified=False)
            with st.expander("Full product table"):
                table(prod.sort_values("revenue", ascending=False), 420, {
                    "product_name": "Product", "category": "Category", "units": num_col("Units"),
                    "revenue": money_col("Revenue"), "gross_profit": money_col("Gross profit"), "margin": pct_col("Margin")})
                download(prod, "Download product performance (CSV)", "menu_product_performance_filtered.csv", "dl_prod")

    with t_eng:
        eng = output("menu_engineering.csv")
        classes = output("menu_class_summary.csv")
        if not has_cols(eng, "sales_mix_pct", "contribution_margin", "product_name", "menu_class"):
            unavailable("Menu engineering output")
        else:
            section("Menu engineering matrix", "Popularity (sales mix) against profitability (contribution margin per unit). "
                                               "Thresholds are project-specific, not universal industry standards.")
            fig = px.scatter(eng, x="sales_mix_pct", y="contribution_margin", color="menu_class", hover_name="product_name",
                             size="quantity_sold" if "quantity_sold" in eng else None, size_max=34,
                             color_discrete_map=CLASS_COLORS,
                             labels={"sales_mix_pct": "Sales mix (%)", "contribution_margin": f"Contribution margin ({CURRENCY} / unit)", "menu_class": "Class"})
            xb, yb = boundary(eng, "popularity", "sales_mix_pct"), boundary(eng, "profitability", "contribution_margin")
            if xb is not None:
                fig.add_vline(x=xb, line_dash="dot", line_color=C["grey"])
            if yb is not None:
                fig.add_hline(y=yb, line_dash="dot", line_color=C["grey"])
            chart(fig, 430, unified=False)

            l, r = st.columns([1, 1.4])
            with l:
                section("Class summary")
                if has_cols(classes, "menu_class", "number_of_products"):
                    table(classes[[c for c in ["menu_class", "number_of_products", "sales_share_pct", "profit_share_pct"] if c in classes]], 220, {
                        "menu_class": "Class", "number_of_products": num_col("Products"),
                        "sales_share_pct": pct_col("Sales share"), "profit_share_pct": pct_col("Profit share")})
            with r:
                section("Recommended actions")
                sel = st.multiselect("Filter by class", sorted(eng["menu_class"].unique()), key="eng_class")
                v = eng if not sel else eng[eng["menu_class"].isin(sel)]
                cols = [c for c in ["product_name", "category", "menu_class", "gross_margin_pct", "recommended_action"] if c in v]
                table(v[cols].sort_values("menu_class"), 300, {
                    "product_name": "Product", "category": "Category", "menu_class": "Class",
                    "gross_margin_pct": pct_col("Margin"), "recommended_action": st.column_config.TextColumn("Recommended action", width="large")})
            callout("Actions are analytical suggestions. Validate against recipe cost, brand strategy, supplier terms and "
                    "customer demand before changing the menu.", "note")

    with t_disc:
        if not has_cols(L, "line_total", "gross_profit", "discount_pct"):
            unavailable("Discount data")
        else:
            d = L.assign(Group=np.where(L["discount_pct"] > 0, "Discounted", "Full price"))
            g = d.groupby("Group", as_index=False).agg(revenue=("line_total", "sum"), gross_profit=("gross_profit", "sum"), units=("quantity", "sum"))
            g["margin"] = g["gross_profit"] / g["revenue"] * 100
            a, b = st.columns(2)
            with a:
                section("Discounted vs. full-price sales", "Share of units sold and margin earned.")
                fig = px.bar(g, x="Group", y="units", text=g["margin"].map(lambda v: f"{v:.1f}% margin"),
                             labels={"units": "Units sold", "Group": ""})
                fig.update_traces(marker_color=[C["amber"], C["blue"]][: len(g)], textposition="outside")
                chart(fig, 310, unified=False)
            with b:
                section("Monthly revenue and gross profit")
                mm = L.assign(month=L["order_date"].dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False).agg(
                    revenue=("line_total", "sum"), gross_profit=("gross_profit", "sum"))
                fig = go.Figure()
                fig.add_scatter(x=mm["month"], y=mm["revenue"], name="Revenue", mode="lines", line=dict(color=C["blue"], width=2.6))
                fig.add_scatter(x=mm["month"], y=mm["gross_profit"], name="Gross profit", mode="lines", line=dict(color=C["teal"], width=2.6))
                fig.update_layout(yaxis_title=CURRENCY)
                chart(fig, 310)

            if has_cols(L, "promotion_id") and has_cols(promotions, "promotion_id", "promotion_name"):
                section("Promotion performance", "Order lines tagged to each promotion within the selected period.")
                p = L.dropna(subset=["promotion_id"]).groupby("promotion_id", as_index=False).agg(
                    units=("quantity", "sum"), revenue=("line_total", "sum"), gross_profit=("gross_profit", "sum"),
                    discount_value=("discount_value", "sum"))
                p = p.merge(promotions, on="promotion_id", how="left")
                p["margin"] = p["gross_profit"] / p["revenue"] * 100
                if p.empty:
                    st.info("No promotional sales in the selected period.")
                else:
                    cols = ["promotion_name", "product_category", "discount_percentage", "start_date", "end_date",
                            "units", "revenue", "gross_profit", "margin", "discount_value"]
                    p = p[[c for c in cols if c in p]].sort_values("start_date")
                    table(p, 330, {
                        "promotion_name": "Promotion", "product_category": "Category", "discount_percentage": pct_col("Discount", 0),
                        "start_date": st.column_config.DateColumn("Start"), "end_date": st.column_config.DateColumn("End"),
                        "units": num_col("Units"), "revenue": money_col("Revenue"), "gross_profit": money_col("Gross profit"),
                        "margin": pct_col("Margin"), "discount_value": money_col("Discount given")})
                    st.caption("Revenue shown is for promoted lines only; it does not measure incremental sales versus a no-promotion baseline.")


# =============================================================================
# Page: Data & Methodology
# =============================================================================

def page_methodology() -> None:
    hero("Governance", "Data & Methodology",
         "Data coverage, reconciliation checks, model documentation and known limitations.")

    section(
        "Analytical workflow",
        "How the project transforms synthetic restaurant data into operational insights."
    )

    workflow = [
        {
            "Stage": "01 · Data preparation",
            "Description": "Load cleaned restaurant, order, customer, product, payment, "
                           "review and weather datasets."
        },
        {
            "Stage": "02 · Data validation & reconciliation",
            "Description": "Validate data quality, check duplicate order IDs and "
                           "reconcile financial totals across independent source tables."
        },
        {
            "Stage": "03 · Business performance analytics",
            "Description": "Analyse revenue, orders, trading patterns, sales channels, "
                           "meal periods, promotions and weather associations."
        },
        {
            "Stage": "04 · Customer segmentation (RFM)",
            "Description": "Segment customers using Recency, Frequency and Monetary "
                           "metrics; evaluate customer value and revenue concentration."
        },
        {
            "Stage": "05 · Customer experience analytics",
            "Description": "Analyse review ratings, sentiment, experience aspects, "
                           "improvement priorities and high-value customer feedback risks."
        },
        {
            "Stage": "06 · Menu intelligence & engineering",
            "Description": "Evaluate product and category performance, gross profit, "
                           "contribution margin and sales mix; classify menu items "
                           "as Star, Plowhorse, Puzzle or Dog."
        },
        {
            "Stage": "07 · Revenue forecasting",
            "Description": "Use Prophet with calendar and weather regressors to produce "
                           "14-day revenue forecasts and uncertainty intervals."
        },
        {
            "Stage": "08 · Workforce optimisation",
            "Description": "Translate forecast demand into staffing requirements, "
                           "shift allocations, recommended rosters and staffing gaps."
        },
        {
            "Stage": "09 · Dashboard delivery & decision support",
            "Description": "Present interactive KPIs, visualisations, downloadable "
                           "outputs and operational recommendations through Streamlit."
        },
    ]

    table(pd.DataFrame(workflow), 360)

    section("Reconciliation checks", "Independent totals from different source tables should agree.")

    section(
        "Analytical methods",
        "Methods used to generate the customer, menu and forecasting insights."
    )

    methods = [
        {
            "Analysis": "RFM customer segmentation",
            "Method": "Recency, Frequency and Monetary analysis",
            "Purpose": "Understand customer value, purchasing behaviour and revenue concentration."
        },
        {
            "Analysis": "Customer experience analytics",
            "Method": "Review ratings and aspect-level sentiment annotations",
            "Purpose": "Identify positive and negative experience themes and improvement priorities."
        },
        {
            "Analysis": "Menu engineering",
            "Method": "Sales mix (popularity) versus contribution margin per unit",
            "Purpose": "Classify products into Star, Plowhorse, Puzzle and Dog categories."
        },
        {
            "Analysis": "Revenue forecasting",
            "Method": "Prophet with calendar and weather regressors",
            "Purpose": "Estimate revenue over a 14-day forecast horizon with uncertainty intervals."
        },
    ]

    table(pd.DataFrame(methods), 300)
    checks = []
    full_orders = orders["order_total"].sum()
    checks.append(("Orders vs. daily revenue table", full_orders,
                   daily_hist["revenue"].sum() if has_cols(daily_hist, "revenue") else np.nan))
    checks.append(("Orders vs. order-line revenue", full_orders, items["line_total"].sum() if has_cols(items, "line_total") else np.nan))
    checks.append(("Orders vs. payments received", full_orders, payments["amount"].sum() if has_cols(payments, "amount") else np.nan))
    rows = []
    for name, a, b in checks:
        if pd.isna(b):
            rows.append({"Check": name, "Orders total": a, "Comparison total": np.nan, "Difference": np.nan, "Status": "Not available"})
        else:
            rows.append({"Check": name, "Orders total": a, "Comparison total": b, "Difference": a - b,
                         "Status": "✓ Reconciled" if abs(a - b) < 1.0 else "⚠ Review"})
    table(pd.DataFrame(rows), 175, {"Orders total": money_col("Orders total", 2), "Comparison total": money_col("Comparison total", 2),
                                    "Difference": money_col("Difference", 2)})

    c1, c2, c3, c4 = st.columns(4)
    guest = orders["customer_id"].isna().mean() * 100 if "customer_id" in orders else np.nan
    c1.metric("Order records", integer(len(orders)))
    c2.metric("History", f"{DATA_MIN:%b %Y} – {DATA_MAX:%b %Y}")
    c3.metric("Guest (unidentified) orders", pct(guest))
    c4.metric("Duplicate order IDs", integer(orders["order_id"].duplicated().sum()))

    st.write("")
    section("Data inventory", "Files discovered in the project folders.")
    inv = []
    for folder, label in [(DATA_DIR, "Operational"), (OUTPUT_DIR, "Analytical output")]:
        if folder.exists():
            for f in sorted(folder.glob("*.csv")):
                try:
                    with open(f, "rb") as fh:
                        n = max(sum(1 for _ in fh) - 1, 0)
                    cols = len(pd.read_csv(f, nrows=0).columns)
                except Exception:
                    n, cols = np.nan, np.nan
                inv.append({"Layer": label, "File": f"{folder.name}/{f.name}", "Rows": n, "Columns": cols})
    table(pd.DataFrame(inv), 340, {"Rows": num_col("Rows"), "Columns": num_col("Columns")})
    if MISSING:
        st.warning("Missing or unreadable files: " + ", ".join(sorted(set(MISSING))))

    st.write("")
    l, r = st.columns(2)
    with l:
        section("Forecasting model")
        model = meta("restrodine_prophet_calendar_weather_metadata.json")
        pj = meta("restrodine_prophet_calendar_weather.json")
        if model:
            st.markdown(
                f"- **Model:** {model.get('model', 'Prophet')} (additive, weekly seasonality)\n"
                f"- **Regressors:** {', '.join(model.get('regressors', []))}\n"
                f"- **Rain threshold:** {model.get('rain_threshold_mm', '—')} mm\n"
                f"- **Training window:** {model.get('training_start')} to {model.get('training_end')}\n"
                f"- **Interval width:** {int(pj['interval_width'] * 100)}%" if pj.get("interval_width") else
                f"- **Model:** {model.get('model', 'Prophet')}\n- **Regressors:** {', '.join(model.get('regressors', []))}"
            )
        else:
            st.caption("Model metadata not found.")
    with r:
        section("Customer analytics")
        s = meta("customer_intelligence_summary.json")
        if s:
            st.markdown(
                f"- **Customers analysed (RFM):** {integer(s.get('rfm', {}).get('customers_analysed'))}\n"
                f"- **Aspect mentions:** {integer(s.get('total_aspect_mentions'))}\n"
                f"- **Reference period:** {s.get('reference_period', {}).get('start')} to {s.get('reference_period', {}).get('end')}\n"
                f"- **Method:** {s.get('methodology_note', '—')}"
            )
        else:
            st.caption("Customer summary not found.")

    section("Limitations")
    st.markdown(
        "- All data is **synthetic**; patterns reflect the generating process, not a real restaurant.\n"
        "- The forecast is trained on 2024–2025 history and projected to a later horizon; forecast weather inputs "
        "are not stored with the exports, so weather sensitivity cannot be re-audited here.\n"
        "- Prediction intervals express model uncertainty; they are not guaranteed bounds.\n"
        "- Gross profit covers product cost only. Labour, rent, utilities and fees are excluded.\n"
        "- The roster is an optimisation suggestion and ignores factors not in the data (training, preferences, legal rest rules).\n"
        "- Weather and calendar views show associations, not causal effects."
    )


# =============================================================================
# Router
# =============================================================================

ROUTES = {
    "Executive Overview": page_executive,
    "Revenue & Forecast": page_revenue,
    "Workforce Planning": page_workforce,
    "Customer Intelligence": page_customers,
    "Menu Performance": page_menu,
    "Data & Methodology": page_methodology,
}
ROUTES[page]()

st.markdown("---")
st.caption(f"{APP_NAME} · Restaurant Intelligence & Weather-Aware Revenue Forecasting · Synthetic demonstration dataset")

