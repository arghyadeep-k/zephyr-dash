"""Stress tab — daily stress band and summary stats."""
import streamlit as st
import plotly.graph_objects as go


def render(data: dict, C: dict, T: dict, CHART_LAYOUT: dict) -> None:
    st.subheader("Stress")

    if "stress" not in data or data["stress"].empty:
        st.info("No stress data in range.")
        return

    stress = data["stress"]

    if "stress_avg" not in stress.columns:
        st.info("Stress average column not found in this dataset.")
        return

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
