"""Activity tab — steps, calories, active minutes, distance."""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from data_utils import rolling_line

STEP_GOAL           = 10_000
ACTIVE_MINUTES_GOAL = 30


def render(data: dict, C: dict, T: dict, CHART_LAYOUT: dict, AVG_LINE: str) -> None:
    st.subheader("Activity")

    if "activity" not in data or data["activity"].empty:
        st.info("No activity data in range.")
        return

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
        fig.add_hline(y=STEP_GOAL, line_dash="dot", line_color="#546E7A",
                      annotation_text=f"{STEP_GOAL:,} goal",
                      annotation_position="bottom right",
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
            fig.add_hline(y=ACTIVE_MINUTES_GOAL, line_dash="dot", line_color="#546E7A",
                          annotation_text=f"{ACTIVE_MINUTES_GOAL} min goal",
                          annotation_position="bottom right",
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
