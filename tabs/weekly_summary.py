"""Weekly Summary tab — this week vs last week comparison."""
import streamlit as st
import plotly.graph_objects as go

from data_utils import get_weekly_summary
from tabs.helpers import apply_axis_style

_HIGHER_BETTER = {
    "Sleep Score", "HRV", "Deep Sleep (min)", "REM Sleep (min)",
    "Steps", "Calories", "Active Minutes", "Distance (km)", "Readiness Score",
}


def render(full_data: dict, C: dict, T: dict, CHART_LAYOUT: dict) -> None:
    st.subheader("Weekly Summary: This Week vs Last Week")
    st.caption("Uses full dataset, not filtered by date range above.")

    summary = get_weekly_summary(full_data)

    if summary.empty:
        st.info("Not enough data yet for a weekly comparison.")
        return

    # ── Metric cards ───────────────────────────────────────────────────────
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
                    delta_color="normal" if row["metric"] in _HIGHER_BETTER else "inverse",
                )

    # ── Side-by-side bar chart ─────────────────────────────────────────────
    st.markdown("#### Side-by-Side Comparison")
    plot_data = summary.dropna(subset=["this_week", "last_week"])
    if plot_data.empty:
        st.info(
            "No complete two-week window found in the loaded data. "
            "Try loading sample data to see this chart."
        )
        return

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
    apply_axis_style(fig, T)
    st.plotly_chart(fig, use_container_width=True)
