"""Sleep tab — stages, score, HRV anomalies, resting HR, breathing rate."""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data_utils import add_hrv_anomalies, rolling_line


def render(data: dict, C: dict, T: dict, CHART_LAYOUT: dict, AVG_LINE: str,
           hrv_threshold: float = 0.20) -> None:
    st.subheader("Sleep Analysis")

    if "sleep" not in data or data["sleep"].empty:
        st.info("No sleep data in range — upload a sleep CSV or load sample data.")
        return

    sleep = add_hrv_anomalies(data["sleep"], drop_pct=hrv_threshold)

    # ── Sleep stage stacked area ───────────────────────────────────────────
    stage_cols = [c for c in ["deep_sleep", "rem_sleep", "light_sleep", "awake_time"]
                  if c in sleep.columns]
    if stage_cols:
        st.markdown("#### Sleep Stage Breakdown")
        stage_labels = {
            "deep_sleep": "Deep", "rem_sleep": "REM",
            "light_sleep": "Light", "awake_time": "Awake",
        }
        s_df = sleep[["date"] + stage_cols].dropna(subset=stage_cols, how="all")
        fig = go.Figure()
        for i, col in enumerate(stage_cols):
            fig.add_trace(go.Scatter(
                x=s_df["date"], y=s_df[col],
                name=stage_labels.get(col, col),
                mode="lines",
                line=dict(width=0, color=C.get(col, "#888")),
                fill="tozeroy" if i == 0 else "tonexty",
                fillcolor=C.get(col, "#888"),
                hovertemplate=f"<b>{stage_labels.get(col, col)}</b>: %{{y:.0f}} min<extra></extra>",
            ))
        fig.update_layout(
            **CHART_LAYOUT, height=320, yaxis_title="Duration (min)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Total sleep summary stats ─────────────────────────────────────────
    if "total_sleep" in sleep.columns:
        ts = sleep["total_sleep"].dropna()
        if not ts.empty:
            st.markdown("#### Total Sleep Duration")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Average", f"{ts.mean() / 60:.1f} h")
            with c2:
                st.metric("Median", f"{ts.median() / 60:.1f} h")
            with c3:
                st.metric("Best night", f"{ts.max() / 60:.1f} h")
            with c4:
                st.metric("Shortest night", f"{ts.min() / 60:.1f} h")

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
            anomalies = hv[hv["hrv_anomaly"]] if "hrv_anomaly" in hv.columns else pd.DataFrame()

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
                    mode="markers", name=f"Anomaly (>{hrv_threshold:.0%} drop)",
                    marker=dict(color=C["anomaly"], size=11, symbol="x-thin", line_width=2),
                ))
            fig.update_layout(**CHART_LAYOUT, height=280, yaxis_title="HRV",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, use_container_width=True)

            if not anomalies.empty:
                with st.expander(
                    f"⚠️ {len(anomalies)} anomalous night(s) — HRV dropped "
                    f">{hrv_threshold:.0%} from 7-day avg"
                ):
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
