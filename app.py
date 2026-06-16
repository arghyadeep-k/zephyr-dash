"""Zepp / Amazfit Health Dashboard — Streamlit app."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from data_utils import (
    load_file,
    add_hrv_anomalies,
    get_weekly_summary,
    get_hrv_readiness_corr,
    make_sample_data,
    FRIENDLY_NAMES,
)

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Zepp Health Dashboard",
    page_icon="💓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme config ───────────────────────────────────────────────────────────
THEMES: dict[str, dict] = {
    "dark": {
        "bg":          "#0E1117",
        "sidebar_bg":  "#1e2130",
        "card_bg":     "#1e2130",
        "card_border": "none",
        "text":        "#e0e0e0",
        "subtext":     "#a0a0a0",
        "divider":     "#333",
        "primary":     "#4ECDC4",
        "font_color":  "#e0e0e0",
        "grid":        "rgba(255,255,255,0.08)",
        "avg_line":    "#ffffff",
        "plot_bg":     "rgba(0,0,0,0)",
        "paper_bg":    "rgba(0,0,0,0)",
    },
    "light": {
        "bg":          "#f8f9fa",
        "sidebar_bg":  "#eef0f5",
        "card_bg":     "#eef0f5",
        "card_border": "1px solid #dde1ec",
        "text":        "#1a1a1a",
        "subtext":     "#555555",
        "divider":     "#cccccc",
        "primary":     "#0d8a82",
        "font_color":  "#1a1a1a",
        "grid":        "rgba(0,0,0,0.08)",
        "avg_line":    "#333333",
        "plot_bg":     "rgba(0,0,0,0)",
        "paper_bg":    "rgba(0,0,0,0)",
    },
}

# ── Session state ──────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "data" not in st.session_state:
    st.session_state.data: dict[str, pd.DataFrame] = {}

T = THEMES[st.session_state.theme]


# ── CSS injection ──────────────────────────────────────────────────────────
def _inject_css(theme: str) -> None:
    t = THEMES[theme]
    if theme == "dark":
        # Dark is the config.toml base; only inject the metric-card tweak
        st.markdown(f"""
        <style>
        div[data-testid="metric-container"] {{
            background: {t["card_bg"]};
            border-radius: 10px;
            padding: 12px 16px;
        }}
        </style>
        """, unsafe_allow_html=True)
        return

    # Light mode: override the dark base theme comprehensively
    st.markdown(f"""
    <style>
    /* ── backgrounds ───────────────────────────────────── */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section[data-testid="stMain"],
    .main .block-container {{
        background-color: {t["bg"]} !important;
    }}
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {{
        background-color: {t["sidebar_bg"]} !important;
    }}
    /* ── text ──────────────────────────────────────────── */
    .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    .stApp span:not([data-testid]),
    .stApp label, .stApp li, .stMarkdown,
    [data-testid="stText"], [data-testid="stHeadingWithActionElements"] {{
        color: {t["text"]} !important;
    }}
    [data-testid="stCaptionContainer"],
    .stCaption {{ color: {t["subtext"]} !important; }}
    /* ── metric cards ──────────────────────────────────── */
    div[data-testid="metric-container"] {{
        background: {t["card_bg"]} !important;
        border: {t["card_border"]} !important;
        border-radius: 10px;
        padding: 12px 16px;
    }}
    [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"] {{
        color: {t["text"]} !important;
    }}
    /* ── tabs ──────────────────────────────────────────── */
    button[data-baseweb="tab"] {{ color: {t["subtext"]} !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {t["primary"]} !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab-border"] {{
        background-color: {t["primary"]} !important;
    }}
    /* ── alerts / info boxes ───────────────────────────── */
    [data-testid="stAlert"] {{
        background-color: #ddeeff !important;
        color: #1a1a1a !important;
    }}
    [data-testid="stAlert"] p {{ color: #1a1a1a !important; }}
    /* ── expander ──────────────────────────────────────── */
    [data-testid="stExpander"] summary {{
        color: {t["text"]} !important;
    }}
    /* ── divider ───────────────────────────────────────── */
    hr {{ border-color: {t["divider"]} !important; }}
    /* ── file uploader ─────────────────────────────────── */
    [data-testid="stFileUploader"] section {{
        background-color: {t["card_bg"]} !important;
        border-color: {t["divider"]} !important;
    }}
    /* ── buttons ───────────────────────────────────────── */
    [data-testid="stButton"] button {{
        background: {t["card_bg"]} !important;
        color: {t["text"]} !important;
        border: 1px solid {t["divider"]} !important;
    }}
    [data-testid="stButton"] button:hover {{
        border-color: {t["primary"]} !important;
        color: {t["primary"]} !important;
    }}
    /* ── date input ────────────────────────────────────── */
    [data-testid="stDateInput"] input {{
        background: #fff !important;
        color: {t["text"]} !important;
    }}
    /* ── sidebar text ──────────────────────────────────── */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] li {{
        color: {t["text"]} !important;
    }}
    </style>
    """, unsafe_allow_html=True)


_inject_css(st.session_state.theme)

# ── Derived theme values (used throughout) ─────────────────────────────────
AVG_LINE  = T["avg_line"]
CHART_LAYOUT = dict(
    plot_bgcolor  = T["plot_bg"],
    paper_bgcolor = T["paper_bg"],
    font_color    = T["font_color"],
    hovermode     = "x unified",
    margin        = dict(t=16, b=4, l=4, r=4),
    xaxis         = dict(gridcolor=T["grid"], linecolor=T["grid"]),
    yaxis         = dict(gridcolor=T["grid"], linecolor=T["grid"]),
)

# ── Color palette (same for both themes) ───────────────────────────────────
C = {
    "deep_sleep":      "#1565C0",
    "light_sleep":     "#90CAF9",
    "rem_sleep":       "#7B1FA2",
    "awake_time":      "#EF9A9A",
    "sleep_score":     "#26C6DA",
    "hrv":             "#66BB6A",
    "resting_hr":      "#EF5350",
    "breathing_rate":  "#AB47BC",
    "steps":           "#FFA726",
    "calories":        "#EC407A",
    "active_minutes":  "#26A69A",
    "distance":        "#78909C",
    "heart_rate":      "#FF7043",
    "stress_avg":      "#FF8A65",
    "stress_high":     "#D84315",
    "stress_low":      "#FFCC80",
    "readiness_score": "#5C6BC0",
    "anomaly":         "#E53935",
}


# ── Helpers ────────────────────────────────────────────────────────────────
def filter_by_date(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if "date" not in df.columns or df.empty:
        return df
    return df[df["date"].between(start, end)].reset_index(drop=True)


def global_date_bounds() -> tuple[pd.Timestamp, pd.Timestamp]:
    all_dates: list[pd.Timestamp] = []
    for df in st.session_state.data.values():
        if "date" in df.columns:
            all_dates.extend(df["date"].dropna().tolist())
    if not all_dates:
        today = pd.Timestamp.now().normalize()
        return today - pd.Timedelta(days=30), today
    return min(all_dates), max(all_dates)


def rolling_line(series: pd.Series, window: int = 7) -> pd.Series:
    return series.rolling(window, min_periods=3).mean()


# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    # Title row with theme toggle
    title_col, toggle_col = st.columns([4, 1])
    with title_col:
        st.title("💓 Zepp Health")
    with toggle_col:
        st.markdown("<div style='margin-top:18px'>", unsafe_allow_html=True)
        icon  = "☀️" if st.session_state.theme == "dark" else "🌙"
        tip   = "Switch to Light Mode" if st.session_state.theme == "dark" else "Switch to Dark Mode"
        if st.button(icon, help=tip, use_container_width=True):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.caption("Amazfit / Zepp CSV Dashboard")
    st.divider()

    st.subheader("Upload Data")
    uploaded = st.file_uploader(
        "Drop Zepp CSV exports here",
        type=["csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Upload sleep, activity, heart rate, stress, or readiness CSVs exported from the Zepp app.",
    )

    if uploaded:
        for f in uploaded:
            try:
                df, dtype, col_map = load_file(f)
                if dtype == "unknown" or df.empty:
                    st.warning(f"Could not detect data type in **{f.name}**")
                    continue
                if dtype in st.session_state.data:
                    existing = st.session_state.data[dtype]
                    merged = (
                        pd.concat([existing, df])
                        .drop_duplicates(subset=["date"])
                        .sort_values("date")
                        .reset_index(drop=True)
                    )
                    st.session_state.data[dtype] = merged
                else:
                    st.session_state.data[dtype] = df
                detected_list = ", ".join(col_map.keys())
                st.success(f"**{f.name}** → *{dtype}*\n\n`{detected_list}`")
            except Exception as exc:
                st.error(f"Error reading **{f.name}**: {exc}")

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🎲 Sample data", use_container_width=True):
            st.session_state.data = make_sample_data()
            st.rerun()
    with btn_col2:
        if st.button("🗑 Clear", use_container_width=True, disabled=not st.session_state.data):
            st.session_state.data = {}
            st.rerun()

    st.divider()

    if st.session_state.data:
        st.subheader("Loaded datasets")
        for dtype, df in st.session_state.data.items():
            st.markdown(f"- **{dtype.replace('_', ' ').title()}** — {len(df)} rows")

        st.divider()
        st.subheader("Date range")
        lo, hi = global_date_bounds()
        d1 = st.date_input("From", value=lo.date(), min_value=lo.date(), max_value=hi.date())
        d2 = st.date_input("To",   value=hi.date(), min_value=lo.date(), max_value=hi.date())
        START = pd.Timestamp(d1)
        END   = pd.Timestamp(d2) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    else:
        START = pd.Timestamp.now() - pd.Timedelta(days=30)
        END   = pd.Timestamp.now()


# ── Guard: nothing loaded ──────────────────────────────────────────────────
st.title("Zepp Health Dashboard")

if not st.session_state.data:
    st.info(
        "Upload your Zepp CSV exports in the sidebar, "
        "or click **🎲 Sample data** to explore the dashboard with demo data."
    )
    st.stop()

# Apply date filter globally
data = {dtype: filter_by_date(df, START, END) for dtype, df in st.session_state.data.items()}


# ── Tabs ───────────────────────────────────────────────────────────────────
tab_overview, tab_sleep, tab_activity, tab_hr, tab_stress, tab_readiness, tab_corr, tab_weekly = st.tabs([
    "Overview", "Sleep", "Activity", "Heart Rate",
    "Stress", "Readiness", "Correlations", "Weekly Summary",
])


# ═══════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
with tab_overview:
    st.subheader("Latest Snapshot")

    kpi_specs = [
        ("sleep",     "sleep_score",     "Sleep Score", "💤"),
        ("sleep",     "hrv",             "HRV",         "💚"),
        ("sleep",     "resting_hr",      "Resting HR",  "❤️"),
        ("activity",  "steps",           "Steps",       "👟"),
        ("activity",  "calories",        "Calories",    "🔥"),
        ("readiness", "readiness_score", "Readiness",   "⚡"),
        ("stress",    "stress_avg",      "Avg Stress",  "🧠"),
    ]
    kpis = []
    for dtype, col, label, icon in kpi_specs:
        if dtype in data and not data[dtype].empty and col in data[dtype].columns:
            val = data[dtype][col].dropna()
            if not val.empty:
                kpis.append((f"{icon} {label}", val.iloc[-1]))

    if kpis:
        cols = st.columns(len(kpis))
        for col, (label, val) in zip(cols, kpis):
            with col:
                fmt = f"{val:,.0f}" if val >= 100 else f"{val:.1f}"
                st.metric(label, fmt)
    else:
        st.info("No data in the selected date range.")

    st.divider()

    spark_specs = [
        ("sleep",     "sleep_score",     "Sleep Score",     "bar"),
        ("sleep",     "hrv",             "HRV",             "line"),
        ("activity",  "steps",           "Daily Steps",     "bar"),
        ("readiness", "readiness_score", "Readiness Score", "color_bar"),
    ]
    cols = st.columns(2)
    col_idx = 0
    for dtype, col, title, kind in spark_specs:
        if dtype not in data or data[dtype].empty or col not in data[dtype].columns:
            continue
        df_s = data[dtype].dropna(subset=[col])
        if df_s.empty:
            continue
        with cols[col_idx % 2]:
            st.markdown(f"**{title}**")
            if kind == "bar":
                fig = px.bar(df_s, x="date", y=col,
                             color_discrete_sequence=[C.get(col, T["primary"])])
            elif kind == "line":
                fig = px.line(df_s, x="date", y=col,
                              color_discrete_sequence=[C.get(col, T["primary"])])
                fig.update_traces(line_width=2)
            else:
                fig = px.bar(
                    df_s, x="date", y=col,
                    color=col,
                    color_continuous_scale=[[0, "#E53935"], [0.5, "#FFA726"], [1, "#43A047"]],
                    range_color=[0, 100],
                )
                fig.update_layout(coloraxis_showscale=False)
            fig.update_layout(**CHART_LAYOUT, height=220, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        col_idx += 1


# ═══════════════════════════════════════════════════════════════════════════
# SLEEP
# ═══════════════════════════════════════════════════════════════════════════
with tab_sleep:
    st.subheader("Sleep Analysis")

    if "sleep" not in data or data["sleep"].empty:
        st.info("No sleep data in range — upload a sleep CSV or load sample data.")
        st.stop()

    sleep = add_hrv_anomalies(data["sleep"])

    # ── Sleep stage stacked area ──────────────────────────────────────────
    stage_cols = [c for c in ["deep_sleep", "rem_sleep", "light_sleep", "awake_time"] if c in sleep.columns]
    if stage_cols:
        st.markdown("#### Sleep Stage Breakdown")
        stage_labels = {
            "deep_sleep":  "Deep",
            "rem_sleep":   "REM",
            "light_sleep": "Light",
            "awake_time":  "Awake",
        }
        s_df = sleep[["date"] + stage_cols].dropna(subset=stage_cols, how="all")
        fig = go.Figure()
        for i, col in enumerate(stage_cols):
            fig.add_trace(go.Scatter(
                x=s_df["date"],
                y=s_df[col],
                name=stage_labels.get(col, col),
                mode="lines",
                line=dict(width=0, color=C.get(col, "#888")),
                fill="tozeroy" if i == 0 else "tonexty",
                fillcolor=C.get(col, "#888"),
                hovertemplate=f"<b>{stage_labels.get(col, col)}</b>: %{{y:.0f}} min<extra></extra>",
            ))
        fig.update_layout(
            **CHART_LAYOUT,
            height=320,
            yaxis_title="Duration (min)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Sleep score + HRV ─────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        if "sleep_score" in sleep.columns:
            st.markdown("#### Sleep Score")
            sc = sleep.dropna(subset=["sleep_score"])
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=sc["date"], y=sc["sleep_score"],
                name="Score", marker_color=C["sleep_score"], opacity=0.65,
                hovertemplate="<b>Sleep Score</b>: %{y:.0f}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=sc["date"], y=rolling_line(sc["sleep_score"]),
                name="7-day avg", line=dict(color=AVG_LINE, width=2, dash="dash"),
                hovertemplate="7-day avg: %{y:.1f}<extra></extra>",
            ))
            fig.update_layout(**CHART_LAYOUT, height=280, yaxis_range=[0, 105],
                               legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "hrv" in sleep.columns:
            st.markdown("#### HRV & Anomalies")
            hv = sleep.dropna(subset=["hrv"])
            anomalies = hv[hv["hrv_anomaly"] == True] if "hrv_anomaly" in hv.columns else pd.DataFrame()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hv["date"], y=hv["hrv"],
                mode="lines+markers", name="HRV",
                line=dict(color=C["hrv"], width=2), marker_size=4,
                hovertemplate="<b>HRV</b>: %{y:.1f}<extra></extra>",
            ))
            if "hrv_7d_avg" in hv.columns:
                fig.add_trace(go.Scatter(
                    x=hv["date"], y=hv["hrv_7d_avg"],
                    mode="lines", name="7-day avg",
                    line=dict(color=AVG_LINE, width=1.5, dash="dot"),
                ))
            if not anomalies.empty:
                fig.add_trace(go.Scatter(
                    x=anomalies["date"], y=anomalies["hrv"],
                    mode="markers", name="Anomaly (>20% drop)",
                    marker=dict(color=C["anomaly"], size=11, symbol="x-thin", line_width=2),
                ))
            fig.update_layout(**CHART_LAYOUT, height=280, yaxis_title="HRV",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, use_container_width=True)

            if not anomalies.empty:
                with st.expander(f"⚠️ {len(anomalies)} anomalous night(s) — HRV dropped >20% from 7-day avg"):
                    for _, row in anomalies.iterrows():
                        drop = abs(row.get("hrv_drop_pct", 0)) * 100
                        avg  = row.get("hrv_7d_avg", float("nan"))
                        st.markdown(
                            f"- **{row['date'].date()}** — HRV: {row['hrv']:.1f} "
                            f"(↓{drop:.0f}% from rolling avg {avg:.1f})"
                        )

    # ── Resting HR + Breathing Rate ───────────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        if "resting_hr" in sleep.columns:
            st.markdown("#### Resting Heart Rate")
            rh = sleep.dropna(subset=["resting_hr"])
            fig = px.line(rh, x="date", y="resting_hr",
                          color_discrete_sequence=[C["resting_hr"]])
            fig.update_traces(line_width=2, mode="lines+markers", marker_size=4)
            fig.update_layout(**CHART_LAYOUT, height=260, yaxis_title="bpm")
            st.plotly_chart(fig, use_container_width=True)

    with col4:
        if "breathing_rate" in sleep.columns:
            st.markdown("#### Breathing Rate")
            br = sleep.dropna(subset=["breathing_rate"])
            fig = px.line(br, x="date", y="breathing_rate",
                          color_discrete_sequence=[C["breathing_rate"]])
            fig.update_traces(line_width=2, mode="lines+markers", marker_size=4)
            fig.update_layout(**CHART_LAYOUT, height=260, yaxis_title="rpm")
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════
with tab_activity:
    st.subheader("Activity")

    if "activity" not in data or data["activity"].empty:
        st.info("No activity data in range.")
    else:
        act = data["activity"]

        if "steps" in act.columns:
            st.markdown("#### Daily Steps")
            sp = act.dropna(subset=["steps"])
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=sp["date"], y=sp["steps"],
                name="Steps", marker_color=C["steps"], opacity=0.8,
                hovertemplate="<b>Steps</b>: %{y:,}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=sp["date"], y=rolling_line(sp["steps"]),
                name="7-day avg", line=dict(color=AVG_LINE, width=2, dash="dash"),
            ))
            fig.add_hline(y=10000, line_dash="dot", line_color="#546E7A",
                          annotation_text="10k goal", annotation_position="bottom right",
                          annotation_font_color=T["subtext"])
            fig.update_layout(**CHART_LAYOUT, height=300, yaxis_title="Steps",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if "calories" in act.columns:
                st.markdown("#### Calories Burned")
                ca = act.dropna(subset=["calories"])
                fig = px.area(ca, x="date", y="calories",
                              color_discrete_sequence=[C["calories"]])
                fig.update_layout(**CHART_LAYOUT, height=270, yaxis_title="kcal")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            if "active_minutes" in act.columns:
                st.markdown("#### Active Minutes")
                am = act.dropna(subset=["active_minutes"])
                fig = px.bar(am, x="date", y="active_minutes",
                             color_discrete_sequence=[C["active_minutes"]])
                fig.add_hline(y=30, line_dash="dot", line_color="#546E7A",
                              annotation_text="30 min goal", annotation_position="bottom right",
                              annotation_font_color=T["subtext"])
                fig.update_layout(**CHART_LAYOUT, height=270, yaxis_title="minutes")
                st.plotly_chart(fig, use_container_width=True)

        if "distance" in act.columns:
            st.markdown("#### Distance")
            di = act.dropna(subset=["distance"])
            fig = px.line(di, x="date", y="distance",
                          color_discrete_sequence=[C["distance"]])
            fig.update_traces(line_width=2, fill="tozeroy", fillcolor="rgba(120,144,156,0.2)")
            fig.update_layout(**CHART_LAYOUT, height=240, yaxis_title="km")
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# HEART RATE
# ═══════════════════════════════════════════════════════════════════════════
with tab_hr:
    st.subheader("Heart Rate")

    hr_df = data.get("heart_rate", pd.DataFrame())
    if hr_df.empty and "sleep" in data and "resting_hr" in data["sleep"].columns:
        hr_df = data["sleep"][["date", "resting_hr"]].copy()

    if hr_df.empty:
        st.info("No heart rate data in range.")
    else:
        plot_cols = [c for c in ["heart_rate", "resting_hr"] if c in hr_df.columns]
        if plot_cols:
            fig = go.Figure()
            for col in plot_cols:
                df_c = hr_df.dropna(subset=[col])
                fig.add_trace(go.Scatter(
                    x=df_c["date"], y=df_c[col],
                    name=FRIENDLY_NAMES.get(col, col),
                    mode="lines+markers", marker_size=4,
                    line=dict(color=C.get(col, "#999"), width=2),
                    hovertemplate=f"<b>{FRIENDLY_NAMES.get(col, col)}</b>: %{{y:.0f}} bpm<extra></extra>",
                ))
            fig.update_layout(**CHART_LAYOUT, height=400, yaxis_title="bpm",
                               legend=dict(orientation="h"))
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, _ = st.columns(3)
            for widget_col, field, label in [(col1, "resting_hr", "Avg Resting HR"),
                                             (col2, "heart_rate", "Avg Heart Rate")]:
                if field in hr_df.columns:
                    with widget_col:
                        st.metric(label, f"{hr_df[field].mean():.0f} bpm")


# ═══════════════════════════════════════════════════════════════════════════
# STRESS
# ═══════════════════════════════════════════════════════════════════════════
with tab_stress:
    st.subheader("Stress")

    if "stress" not in data or data["stress"].empty:
        st.info("No stress data in range.")
    else:
        stress = data["stress"]

        if "stress_avg" in stress.columns:
            st.markdown("#### Daily Stress Level")
            s_avg = stress.dropna(subset=["stress_avg"])
            fig = go.Figure()

            if "stress_high" in stress.columns and "stress_low" in stress.columns:
                band = stress.dropna(subset=["stress_high", "stress_low"])
                fig.add_trace(go.Scatter(
                    x=band["date"].tolist() + band["date"].tolist()[::-1],
                    y=band["stress_high"].tolist() + band["stress_low"].tolist()[::-1],
                    fill="toself",
                    fillcolor="rgba(255,138,101,0.18)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="Daily range",
                    hoverinfo="skip",
                ))

            fig.add_trace(go.Scatter(
                x=s_avg["date"], y=s_avg["stress_avg"],
                name="Avg Stress", mode="lines+markers", marker_size=5,
                line=dict(color=C["stress_avg"], width=2.5),
                hovertemplate="<b>Stress</b>: %{y:.0f}<extra></extra>",
            ))
            fig.update_layout(
                **CHART_LAYOUT, height=350,
                yaxis_title="Stress Level", yaxis_range=[0, 100],
                legend=dict(orientation="h"),
            )
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Stress", f"{s_avg['stress_avg'].mean():.0f}")
            with col2:
                if "stress_high" in stress.columns:
                    st.metric("Avg Peak Stress", f"{stress['stress_high'].mean():.0f}")
            with col3:
                high_days = int((s_avg["stress_avg"] > 60).sum())
                st.metric("High-Stress Days (>60)", str(high_days))


# ═══════════════════════════════════════════════════════════════════════════
# READINESS
# ═══════════════════════════════════════════════════════════════════════════
with tab_readiness:
    st.subheader("Readiness / BioCharge")

    if "readiness" not in data or data["readiness"].empty:
        st.info("No readiness data in range.")
    else:
        rd = data["readiness"].dropna(subset=["readiness_score"])

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=rd["date"], y=rd["readiness_score"],
            name="Readiness",
            marker=dict(
                color=rd["readiness_score"],
                colorscale=[[0, "#E53935"], [0.4, "#FFA726"], [0.7, "#FDD835"], [1, "#43A047"]],
                cmin=0, cmax=100, showscale=True,
                colorbar=dict(
                    title="Score",
                    tickvals=[0, 25, 50, 75, 100],
                    tickfont=dict(color=T["font_color"]),
                    titlefont=dict(color=T["font_color"]),
                ),
            ),
            hovertemplate="<b>Readiness</b>: %{y:.0f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=rd["date"], y=rolling_line(rd["readiness_score"]),
            name="7-day avg", line=dict(color=AVG_LINE, width=2, dash="dash"),
        ))
        fig.update_layout(
            **CHART_LAYOUT, height=400,
            yaxis_title="Readiness Score", yaxis_range=[0, 105],
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Average Readiness", f"{rd['readiness_score'].mean():.0f}")
        with col2:
            peak = rd.loc[rd["readiness_score"].idxmax()]
            st.metric("Peak Readiness", f"{peak['readiness_score']:.0f}",
                      delta=str(peak["date"].date()))
        with col3:
            low = rd.loc[rd["readiness_score"].idxmin()]
            st.metric("Lowest Readiness", f"{low['readiness_score']:.0f}",
                      delta=str(low["date"].date()), delta_color="inverse")


# ═══════════════════════════════════════════════════════════════════════════
# CORRELATIONS
# ═══════════════════════════════════════════════════════════════════════════
with tab_corr:
    st.subheader("Correlation Analysis")

    sleep_d     = data.get("sleep",     pd.DataFrame())
    readiness_d = data.get("readiness", pd.DataFrame())

    if not sleep_d.empty and not readiness_d.empty:
        corr_df = get_hrv_readiness_corr(sleep_d, readiness_d)
        if len(corr_df) > 3:
            st.markdown("#### HRV (night) vs Next-Day Readiness")
            r = corr_df["hrv"].corr(corr_df["readiness_score"])
            try:
                fig = px.scatter(
                    corr_df, x="hrv", y="readiness_score",
                    trendline="ols",
                    labels={"hrv": "Overnight HRV", "readiness_score": "Next-Day Readiness"},
                    color_discrete_sequence=[C["hrv"]],
                    hover_data={"date": "|%Y-%m-%d"},
                )
            except Exception:
                fig = px.scatter(
                    corr_df, x="hrv", y="readiness_score",
                    labels={"hrv": "Overnight HRV", "readiness_score": "Next-Day Readiness"},
                    color_discrete_sequence=[C["hrv"]],
                )
            fig.update_layout(**CHART_LAYOUT, height=380)
            st.plotly_chart(fig, use_container_width=True)

            strength  = "strong" if abs(r) > 0.6 else "moderate" if abs(r) > 0.3 else "weak"
            direction = "positive" if r > 0 else "negative"
            st.info(
                f"Pearson r = **{r:.3f}** — {strength} {direction} correlation "
                f"between overnight HRV and next-day readiness score "
                f"({len(corr_df)} matched days)."
            )
        else:
            st.info("Need >3 days with both HRV and readiness data to show this chart.")
    else:
        st.info("Upload both **sleep** and **readiness** CSVs to see HRV → readiness correlation.")

    st.markdown("#### Full Metric Correlation Matrix")
    series_map: dict[str, pd.Series] = {}
    for dtype, df in data.items():
        if df.empty or "date" not in df.columns:
            continue
        for col in df.columns:
            if col == "date":
                continue
            if df[col].dtype in (float, int, np.float64, np.int64, np.float32, np.int32):
                label = FRIENDLY_NAMES.get(col, col)
                series_map[label] = df.set_index("date")[col]

    if len(series_map) >= 3:
        combined  = pd.DataFrame(series_map)
        corr_mat  = combined.corr()
        fig = px.imshow(
            corr_mat,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1, zmax=1,
            aspect="auto",
        )
        fig.update_layout(**CHART_LAYOUT, height=520)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Load data from multiple data types to see a correlation matrix.")


# ═══════════════════════════════════════════════════════════════════════════
# WEEKLY SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
with tab_weekly:
    st.subheader("Weekly Summary: This Week vs Last Week")
    st.caption("Uses full dataset, not filtered by date range above.")

    summary = get_weekly_summary(st.session_state.data)

    if summary.empty:
        st.info("Not enough data yet for a weekly comparison.")
    else:
        higher_better = {
            "Sleep Score", "HRV", "Deep Sleep (min)", "REM Sleep (min)",
            "Steps", "Calories", "Active Minutes", "Distance (km)", "Readiness Score",
        }

        st.markdown("#### Key Metric Averages")
        chunk_size = 4
        for chunk_start in range(0, len(summary), chunk_size):
            chunk = summary.iloc[chunk_start : chunk_start + chunk_size]
            cols  = st.columns(len(chunk))
            for col_widget, (_, row) in zip(cols, chunk.iterrows()):
                with col_widget:
                    tw  = row["this_week"]
                    chg = row["change_pct"]
                    if tw is None:
                        st.metric(row["metric"], "—")
                        continue
                    delta_str = None
                    if chg is not None:
                        sign = "+" if chg > 0 else ""
                        delta_str = f"{sign}{chg:.1f}%"
                    st.metric(
                        label=row["metric"],
                        value=f"{tw:.1f}",
                        delta=delta_str,
                        delta_color="normal" if row["metric"] in higher_better else "inverse",
                    )

        st.markdown("#### Side-by-Side Comparison")
        plot_data = summary.dropna(subset=["this_week", "last_week"])
        if not plot_data.empty:
            fig = go.Figure([
                go.Bar(
                    name="Last Week",
                    x=plot_data["metric"], y=plot_data["last_week"],
                    marker_color="#546E7A", opacity=0.8,
                ),
                go.Bar(
                    name="This Week",
                    x=plot_data["metric"], y=plot_data["this_week"],
                    marker_color=T["primary"], opacity=0.9,
                ),
            ])
            fig.update_layout(
                **CHART_LAYOUT,
                barmode="group",
                height=400,
                xaxis_tickangle=-30,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(t=20, b=90, l=4, r=4),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "No complete two-week window found in the loaded data. "
                "Try loading sample data to see this chart."
            )
