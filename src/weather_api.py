"""Weather for RestroDine from Open-Meteo (free, no API key).

* history  -> observed daily weather (ERA5 reanalysis) for a date range
* forecast -> next days (up to 16) for the forecast-model regressors (README section 18)

Output columns match the `weather` table: date, temperature_c, temp_max_c, temp_min_c,
precipitation_mm, is_rainy, weather_condition.

NOTE: the shipped data/weather.csv is synthetic (calibrated to the Rhineland climate) and the
synthetic sales were generated against it. Use `history` only if you knowingly want observed
weather; use `forecast` for future dates. Never rewrite the historical MySQL weather table on
every API call.

    python src/weather_api.py --mode forecast --days 7 --out outputs/weather_forecast.csv
    python src/weather_api.py --mode history --start 2024-01-01 --end 2025-12-31 --out outputs/weather_observed.csv
"""
import argparse
import pandas as pd
import requests

# Restaurant location - ASSUMPTION: Cologne (largest customer share). Change to your site, e.g. Bonn = 50.7374, 7.0982
LAT, LON, TZ = 50.9375, 6.9603, "Europe/Berlin"
DAILY = "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum"
URLS = {"forecast": "https://api.open-meteo.com/v1/forecast",
        "history": "https://archive-api.open-meteo.com/v1/archive"}


def classify(df: pd.DataFrame) -> pd.DataFrame:
    """Same rules that reproduce the labels in data/weather.csv."""
    df["is_rainy"] = (df["precipitation_mm"] >= 1.0).astype(int)
    cond = pd.Series("Normal", index=df.index)
    cond[df["temp_min_c"].notna() & (df["temperature_c"] <= 2.0)] = "Cold"
    cond[df["temp_max_c"] >= 28.0] = "Hot"
    cond[df["precipitation_mm"] >= 1.0] = "Rain"
    cond[df["precipitation_mm"] >= 10.0] = "Heavy Rain"
    df["weather_condition"] = cond
    return df


def parse(payload: dict) -> pd.DataFrame:
    d = payload["daily"]
    df = pd.DataFrame({"date": d["time"], "temperature_c": d["temperature_2m_mean"],
                       "temp_max_c": d["temperature_2m_max"], "temp_min_c": d["temperature_2m_min"],
                       "precipitation_mm": d["precipitation_sum"]})
    df["precipitation_mm"] = df["precipitation_mm"].fillna(0.0)
    df[["temperature_c", "temp_max_c", "temp_min_c", "precipitation_mm"]] = \
        df[["temperature_c", "temp_max_c", "temp_min_c", "precipitation_mm"]].round(1)
    return classify(df)


def fetch(mode: str, start=None, end=None, days=7, lat=LAT, lon=LON) -> pd.DataFrame:
    params = {"latitude": lat, "longitude": lon, "daily": DAILY, "timezone": TZ}
    if mode == "forecast":
        params["forecast_days"] = min(max(days, 1), 16)
    else:
        params.update(start_date=start, end_date=end)
    r = requests.get(URLS[mode], params=params, timeout=30)
    r.raise_for_status()
    return parse(r.json())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["forecast", "history"], default="forecast")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--start"); ap.add_argument("--end"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.mode == "history" and not (a.start and a.end):
        ap.error("--start and --end are required for history mode")
    out = fetch(a.mode, a.start, a.end, a.days)
    print(out.to_string(index=False))
    if a.out:
        out.to_csv(a.out, index=False)
