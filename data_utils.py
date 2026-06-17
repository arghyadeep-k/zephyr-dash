"""Data processing utilities for the Zepp Health Dashboard."""
import re
import io
import pandas as pd
import numpy as np
from difflib import SequenceMatcher
import streamlit as st

COLUMN_ALIASES: dict[str, list[str]] = {
    "date":            ["date", "day", "timestamp", "time", "datetime", "record date", "log date"],
    "sleep_score":     ["sleep score", "sleep quality", "sleep_score", "sleep quality score", "overall score"],
    "deep_sleep":      ["deep sleep", "deep_sleep", "deep sleep duration", "deep(min)", "deep"],
    "light_sleep":     ["light sleep", "light_sleep", "light sleep duration", "light(min)", "light"],
    "rem_sleep":       ["rem", "rem sleep", "rem_sleep", "rem sleep duration", "rem(min)", "rem duration"],
    "awake_time":      ["awake", "wake", "awake time", "awake(min)", "waking time", "awake duration"],
    "total_sleep":     ["total sleep", "sleep duration", "total sleep duration", "total(min)", "sleep time"],
    "hrv":             ["hrv", "heart rate variability", "hrv score", "overnight hrv", "avg hrv", "hrv(night)", "hrv avg"],
    "resting_hr":      ["resting hr", "resting heart rate", "resting_hr", "rhr", "resting bpm", "min hr"],
    "breathing_rate":  ["breathing rate", "breath rate", "respiratory rate", "breathing rate(rpm)", "respiration rate"],
    "steps":           ["steps", "step count", "total steps", "daily steps", "step_count"],
    "calories":        ["calories", "calorie", "kcal", "total calories", "calories(kcal)"],
    "active_minutes":  ["active minutes", "active time", "exercise minutes", "active_minutes", "active time(min)"],
    "distance":        ["distance", "distance(km)", "distance(m)", "total distance"],
    "heart_rate":      ["heart rate", "avg heart rate", "average heart rate", "bpm", "avg bpm"],
    "stress_high":     ["stress high", "max stress", "high stress", "stress max", "peak stress"],
    "stress_low":      ["stress low", "min stress", "low stress", "stress min"],
    "stress_avg":      ["stress avg", "average stress", "avg stress", "stress", "stress level", "stress score"],
    "readiness_score": ["readiness", "readiness score", "biocharge", "bio charge", "recovery score", "bio_charge"],
}

_TYPE_SIGNATURES: dict[str, list[str]] = {
    "sleep":      ["sleep_score", "deep_sleep", "rem_sleep", "light_sleep", "hrv", "breathing_rate"],
    "activity":   ["steps", "calories", "active_minutes", "distance"],
    "heart_rate": ["heart_rate"],
    "stress":     ["stress_avg", "stress_high", "stress_low"],
    "readiness":  ["readiness_score"],
}

FRIENDLY_NAMES: dict[str, str] = {
    "sleep_score":     "Sleep Score",
    "deep_sleep":      "Deep Sleep (min)",
    "light_sleep":     "Light Sleep (min)",
    "rem_sleep":       "REM Sleep (min)",
    "awake_time":      "Awake Time (min)",
    "total_sleep":     "Total Sleep (min)",
    "hrv":             "HRV",
    "resting_hr":      "Resting HR (bpm)",
    "breathing_rate":  "Breathing Rate (rpm)",
    "steps":           "Steps",
    "calories":        "Calories",
    "active_minutes":  "Active Minutes",
    "distance":        "Distance (km)",
    "heart_rate":      "Heart Rate (bpm)",
    "stress_high":     "Stress High",
    "stress_low":      "Stress Low",
    "stress_avg":      "Avg Stress",
    "readiness_score": "Readiness Score",
}


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[_\-/\\]+", " ", s)
    s = re.sub(r"\([^)]*\)", "", s)  # strip parenthetical units like (min), (bpm)
    return re.sub(r"\s+", " ", s).strip()


def _score(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.9
    return SequenceMatcher(None, a, b).ratio()


def detect_columns(df: pd.DataFrame) -> dict[str, str]:
    """Returns {canonical_name -> actual_column_name} for columns we can match."""
    norm_to_actual = {_norm(c): c for c in df.columns}
    used: set[str] = set()
    result: dict[str, str] = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        best_actual, best_score = None, 0.0
        for normed_actual, actual in norm_to_actual.items():
            if actual in used:
                continue
            for alias in aliases:
                s = _score(normed_actual, _norm(alias))
                if s > best_score:
                    best_score = s
                    best_actual = actual
        if best_actual and best_score >= 0.72:
            result[canonical] = best_actual
            used.add(best_actual)

    return result


def normalize_df(df: pd.DataFrame, col_map: dict[str, str]) -> pd.DataFrame:
    """Rename detected columns to canonical names, drop unrecognised columns."""
    rename = {actual: canon for canon, actual in col_map.items()}
    df = df.rename(columns=rename)
    keep = [c for c in df.columns if c in COLUMN_ALIASES]
    df = df[keep].copy()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["date"] = df["date"].dt.normalize()
        df = df.sort_values("date").reset_index(drop=True)

    for col in df.columns:
        if col != "date":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def detect_type(col_map: dict[str, str]) -> str:
    """Guess the data type (sleep/activity/heart_rate/stress/readiness) from detected columns."""
    detected = set(col_map.keys())
    scores = {
        dtype: sum(1 for c in sigs if c in detected)
        for dtype, sigs in _TYPE_SIGNATURES.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def read_csv_safe(file_obj) -> pd.DataFrame:
    """Try multiple encodings and separators until one produces a multi-column frame."""
    raw = file_obj.read()
    for enc in ("utf-8", "latin-1", "cp1252"):
        for sep in (",", ";", "\t"):
            try:
                df = pd.read_csv(io.BytesIO(raw), sep=sep, encoding=enc)
                if len(df.columns) > 1:
                    return df
            except Exception:
                continue
    raise ValueError("Could not parse CSV — check the file format.")


def load_file(file_obj) -> tuple[pd.DataFrame, str, dict[str, str]]:
    """Full pipeline: read → detect columns → normalize → detect type."""
    df_raw = read_csv_safe(file_obj)
    col_map = detect_columns(df_raw)
    df = normalize_df(df_raw, col_map)
    dtype = detect_type(col_map)
    return df, dtype, col_map


@st.cache_data
def rolling_line(series: pd.Series, window: int = 7) -> pd.Series:
    """Rolling mean with a minimum of 3 observations."""
    return series.rolling(window, min_periods=3).mean()


@st.cache_data
def add_hrv_anomalies(df: pd.DataFrame, window: int = 7, drop_pct: float = 0.20) -> pd.DataFrame:
    """Add hrv_7d_avg, hrv_drop_pct, and hrv_anomaly columns to a sleep DataFrame."""
    if "hrv" not in df.columns:
        return df
    df = df.copy()
    df["hrv_7d_avg"] = df["hrv"].rolling(window, min_periods=3).mean().shift(1)
    df["hrv_drop_pct"] = (df["hrv"] - df["hrv_7d_avg"]) / df["hrv_7d_avg"]
    df["hrv_anomaly"] = df["hrv_drop_pct"] < -drop_pct
    return df


@st.cache_data
def get_weekly_summary(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compare this calendar week (Mon–today) vs the full prior week."""
    today = pd.Timestamp.now().normalize()
    this_start = today - pd.Timedelta(days=today.dayofweek)
    last_start = this_start - pd.Timedelta(weeks=1)

    metrics_map: dict[str, list[str]] = {
        "sleep":     ["sleep_score", "hrv", "deep_sleep", "rem_sleep", "resting_hr"],
        "activity":  ["steps", "calories", "active_minutes"],
        "stress":    ["stress_avg"],
        "readiness": ["readiness_score"],
    }

    rows = []
    for dtype, cols in metrics_map.items():
        if dtype not in data:
            continue
        df = data[dtype]
        if "date" not in df.columns:
            continue
        this_week = df[df["date"].between(this_start, today)]
        last_week = df[df["date"].between(last_start, last_start + pd.Timedelta(days=6))]
        for col in cols:
            if col not in df.columns:
                continue
            tw = this_week[col].mean() if not this_week.empty else np.nan
            lw = last_week[col].mean() if not last_week.empty else np.nan
            chg = ((tw - lw) / lw * 100) if (pd.notna(tw) and pd.notna(lw) and lw != 0) else np.nan
            rows.append({
                "metric":     FRIENDLY_NAMES.get(col, col),
                "this_week":  round(tw, 1) if pd.notna(tw) else None,
                "last_week":  round(lw, 1) if pd.notna(lw) else None,
                "change_pct": round(chg, 1) if pd.notna(chg) else None,
            })

    return pd.DataFrame(rows)


@st.cache_data
def get_hrv_readiness_corr(sleep_df: pd.DataFrame, readiness_df: pd.DataFrame) -> pd.DataFrame:
    """Join overnight HRV with the *next morning's* readiness score."""
    if "hrv" not in sleep_df.columns or "readiness_score" not in readiness_df.columns:
        return pd.DataFrame()
    hrv = sleep_df[["date", "hrv"]].dropna()
    read = readiness_df[["date", "readiness_score"]].dropna().copy()
    # shift readiness date back 1 day so it aligns with the preceding night's HRV
    read["date"] = read["date"] - pd.Timedelta(days=1)
    return pd.merge(hrv, read, on="date", how="inner")


@st.cache_data
def get_correlation_matrix(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Pearson correlation matrix across all numeric metrics from all data types."""
    series_map: dict[str, pd.Series] = {}
    for df in data.values():
        if df.empty or "date" not in df.columns:
            continue
        for col in df.columns:
            if col == "date":
                continue
            if df[col].dtype in (float, int, np.float64, np.int64, np.float32, np.int32):
                label = FRIENDLY_NAMES.get(col, col)
                series_map[label] = df.set_index("date")[col]
    if len(series_map) < 3:
        return pd.DataFrame()
    return pd.DataFrame(series_map).corr()


def make_sample_data() -> dict[str, pd.DataFrame]:
    """Generate 60 days of plausible Zepp-style data for demo purposes."""
    rng = np.random.default_rng(42)
    n = 60
    dates = pd.date_range(end=pd.Timestamp.now().normalize(), periods=n)

    hrv_base     = 45 + np.cumsum(rng.normal(0, 0.5, n)).clip(-15, 15)
    readiness_b  = 70 + np.cumsum(rng.normal(0, 0.8, n)).clip(-20, 20)

    sleep = pd.DataFrame({
        "date":           dates,
        "sleep_score":    (readiness_b * 0.8 + rng.normal(0, 5, n)).clip(30, 100).astype(int),
        "deep_sleep":     (80  + rng.normal(0, 15, n)).clip(20, 150).astype(int),
        "light_sleep":    (200 + rng.normal(0, 30, n)).clip(80, 300).astype(int),
        "rem_sleep":      (100 + rng.normal(0, 20, n)).clip(30, 180).astype(int),
        "awake_time":     (30  + rng.integers(0, 30, n)).astype(int),
        "hrv":            (hrv_base + rng.normal(0, 3, n)).clip(20, 90).round(1),
        "resting_hr":     (58 - hrv_base * 0.1 + rng.normal(0, 2, n)).clip(45, 80).round(0),
        "breathing_rate": (15 + rng.normal(0, 0.5, n)).clip(12, 20).round(1),
    })
    # Inject three clear HRV anomalies
    for idx in [15, 30, 45]:
        sleep.loc[idx, "hrv"] = float(sleep["hrv"].iloc[max(0, idx - 7):idx].mean() * 0.70)

    activity = pd.DataFrame({
        "date":           dates,
        "steps":          (8000 + rng.normal(0, 2000, n)).clip(1000, 20000).astype(int),
        "calories":       (2200 + rng.normal(0,  300, n)).clip(1200,  3500).astype(int),
        "active_minutes": (45   + rng.normal(0,   15, n)).clip(5,      120).astype(int),
        "distance":       (6.5  + rng.normal(0,  1.5, n)).clip(0.5,     15).round(2),
    })

    heart_rate = pd.DataFrame({
        "date":       dates,
        "heart_rate": (72 + rng.normal(0, 5, n)).clip(55, 100).round(0),
        "resting_hr": sleep["resting_hr"].values,
    })

    stress = pd.DataFrame({
        "date":       dates,
        "stress_avg": (40 + rng.normal(0, 10, n)).clip(10, 90).astype(int),
        "stress_high":(65 + rng.normal(0, 10, n)).clip(30, 95).astype(int),
        "stress_low": (20 + rng.normal(0,  8, n)).clip(5,  50).astype(int),
    })

    readiness = pd.DataFrame({
        "date":            dates,
        "readiness_score": (readiness_b + rng.normal(0, 5, n)).clip(20, 100).astype(int),
    })

    return {
        "sleep":      sleep,
        "activity":   activity,
        "heart_rate": heart_rate,
        "stress":     stress,
        "readiness":  readiness,
    }
