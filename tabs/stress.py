"""Stress tab — daily stress band and summary stats."""
import streamlit as st
import plotly.graph_objects as go
from tabs.helpers import apply_axis_style, downsample_for_plot
from theme import RenderCtx


def render(data: dict, ctx: RenderCtx) -> None:
    C            = ctx["C"]
    T            = ctx["T"]
    CHART_LAYOUT = ctx["CHART_LAYOUT"]
    st.subheader("Stress")

    if "stress" not in data or data["stress"].empty:
        st.info("No stress data in range.")
        return

    stress = downsample_for_plot(data["stress"])

    if "stress_avg" not in stress.columns:
        st.info("Stress average column not found in this dataset.")
        return

    st.markdown("#### Daily Stress Level")
    s_avg = stress.dropna(subset=["stress_avg"])
    fig = go.Figure()

    if "stress_high" in stress.columns and "stress_low" in stress.columns:
        band = stress.dropna(subset=["stress_high", "stress_low"])
        fig.add_trace(go.Scatter(
            x=band["date"], y=band["stress_low"],
            mode="lines", line=dict(color="rgba(0,0,0,0)"),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=band["date"], y=band["stress_high"],
            mode="lines", line=dict(color="rgba(0,0,0,0)"),
            fill="tonexty", fillcolor="rgba(255,138,101,0.18)",
            name="Daily range", hoverinfo="skip",
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
    apply_axis_style(fig, T)
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
