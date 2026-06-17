"""Readiness / BioCharge tab."""
import streamlit as st
import plotly.graph_objects as go

from data_utils import rolling_line
from tabs.helpers import apply_axis_style
from theme import RenderCtx


def render(data: dict, ctx: RenderCtx) -> None:
    C            = ctx["C"]
    T            = ctx["T"]
    CHART_LAYOUT = ctx["CHART_LAYOUT"]
    AVG_LINE     = ctx["AVG_LINE"]
    st.subheader("Readiness / BioCharge")

    if "readiness" not in data or data["readiness"].empty:
        st.info("No readiness data in range.")
        return

    rd = data["readiness"].dropna(subset=["readiness_score"])
    if rd.empty:
        st.info("No readiness scores in range.")
        return

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
    apply_axis_style(fig, T)
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
