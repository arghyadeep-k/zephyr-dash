"""Overview tab — latest snapshot KPIs and sparklines."""
import streamlit as st
import plotly.express as px
from tabs.helpers import apply_axis_style
from theme import RenderCtx


def render(data: dict, ctx: RenderCtx) -> None:
    C            = ctx["C"]
    T            = ctx["T"]
    CHART_LAYOUT = ctx["CHART_LAYOUT"]
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
            apply_axis_style(fig, T)
            st.plotly_chart(fig, use_container_width=True)
        col_idx += 1
