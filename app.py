"""Zepp / Amazfit Health Dashboard — Streamlit app."""
import streamlit as st
import pandas as pd

from theme import THEMES, C, _inject_css

import tabs.overview
import tabs.sleep
import tabs.activity
import tabs.heart_rate
import tabs.stress
import tabs.readiness
import tabs.correlations
import tabs.weekly_summary

from data_utils import load_file, make_sample_data, filter_by_date, global_date_bounds

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Zepp Health Dashboard",
    page_icon="💓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state ──────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "data" not in st.session_state:
    st.session_state.data: dict[str, pd.DataFrame] = {}

T = THEMES[st.session_state.theme]

_inject_css(st.session_state.theme)

# ── Derived theme values ───────────────────────────────────────────────────
AVG_LINE     = T["avg_line"]
CHART_LAYOUT = dict(
    plot_bgcolor  = T["plot_bg"],
    paper_bgcolor = T["paper_bg"],
    font_color    = T["font_color"],
    hovermode     = "x unified",
    margin        = dict(t=16, b=4, l=4, r=4),
)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    # Title + theme toggle
    title_col, toggle_col = st.columns([4, 1])
    with title_col:
        st.title("💓 Zepp Health")
    with toggle_col:
        st.markdown("<div style='margin-top:18px'>", unsafe_allow_html=True)
        icon = "☀️" if st.session_state.theme == "dark" else "🌙"
        tip  = "Switch to Light Mode" if st.session_state.theme == "dark" else "Switch to Dark Mode"
        if st.button(icon, help=tip, use_container_width=True):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.caption("Amazfit / Zepp CSV Dashboard")
    st.divider()

    # ── File upload ────────────────────────────────────────────────────────
    st.subheader("Upload Data")
    uploaded = st.file_uploader(
        "Drop Zepp CSV exports here",
        type=["csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Upload sleep, activity, heart rate, stress, or readiness CSVs from the Zepp app.",
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
                st.success(f"**{f.name}** → *{dtype}*\n\n`{', '.join(col_map.keys())}`")
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
        # ── Loaded datasets with per-item removal (#7) ─────────────────────
        st.subheader("Loaded datasets")
        for dtype in list(st.session_state.data.keys()):
            df      = st.session_state.data[dtype]
            la, lb  = st.columns([5, 1])
            la.markdown(f"**{dtype.replace('_', ' ').title()}** — {len(df)} rows")
            if lb.button("✕", key=f"remove_{dtype}", help=f"Remove {dtype} data"):
                del st.session_state.data[dtype]
                st.rerun()

        st.divider()

        # ── Date range ─────────────────────────────────────────────────────
        st.subheader("Date range")
        lo, hi = global_date_bounds(st.session_state.data)
        d1 = st.date_input("From", value=lo.date(), min_value=lo.date(), max_value=hi.date())
        d2 = st.date_input("To",   value=hi.date(), min_value=lo.date(), max_value=hi.date())
        START = pd.Timestamp(d1)
        END   = pd.Timestamp(d2) + pd.Timedelta(hours=23, minutes=59, seconds=59)

        if START > END:
            st.error("'From' date must be before 'To' date.")
            st.stop()

        # ── Advanced settings (#8) ─────────────────────────────────────────
        with st.expander("⚙️ Advanced settings"):
            hrv_threshold = st.slider(
                "HRV anomaly threshold (%)",
                min_value=10, max_value=40, value=20, step=5,
                help="Nights where HRV drops more than this % below the 7-day rolling average are flagged.",
            ) / 100.0
    else:
        START         = pd.Timestamp.now() - pd.Timedelta(days=30)
        END           = pd.Timestamp.now()
        hrv_threshold = 0.20


# ── Guard ──────────────────────────────────────────────────────────────────
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

with tab_overview:
    tabs.overview.render(data, C, T, CHART_LAYOUT)

with tab_sleep:
    tabs.sleep.render(data, C, T, CHART_LAYOUT, AVG_LINE, hrv_threshold=hrv_threshold)

with tab_activity:
    tabs.activity.render(data, C, T, CHART_LAYOUT, AVG_LINE)

with tab_hr:
    tabs.heart_rate.render(data, C, T, CHART_LAYOUT)

with tab_stress:
    tabs.stress.render(data, C, T, CHART_LAYOUT)

with tab_readiness:
    tabs.readiness.render(data, C, T, CHART_LAYOUT, AVG_LINE)

with tab_corr:
    tabs.correlations.render(data, C, T, CHART_LAYOUT)

with tab_weekly:
    tabs.weekly_summary.render(st.session_state.data, C, T, CHART_LAYOUT)
