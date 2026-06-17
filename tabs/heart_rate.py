"""Heart Rate tab — avg and resting HR trends."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from data_utils import FRIENDLY_NAMES


def render(data: dict, C: dict, T: dict, CHART_LAYOUT: dict) -> None:
    st.subheader("Heart Rate")

    hr_df = data.get("heart_rate", pd.DataFrame())
    # Fall back to resting HR from sleep if no dedicated HR file
    if hr_df.empty and "sleep" in data and "resting_hr" in data["sleep"].columns:
        hr_df = data["sleep"][["date", "resting_hr"]].copy()

    if hr_df.empty:
        st.info("No heart rate data in range.")
        return

    plot_cols = [c for c in ["heart_rate", "resting_hr"] if c in hr_df.columns]
    if not plot_cols:
        st.info("No heart rate columns found in this dataset.")
        return

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
    for widget_col, field, label in [
        (col1, "resting_hr",  "Avg Resting HR"),
        (col2, "heart_rate",  "Avg Heart Rate"),
    ]:
        if field in hr_df.columns:
            with widget_col:
                st.metric(label, f"{hr_df[field].mean():.0f} bpm")
