"""Correlations tab — HRV vs readiness scatter and full metric heatmap."""
import streamlit as st
import plotly.express as px

from data_utils import get_hrv_readiness_corr, get_correlation_matrix
from tabs.helpers import apply_axis_style


def render(data: dict, C: dict, T: dict, CHART_LAYOUT: dict) -> None:
    st.subheader("Correlation Analysis")

    sleep_d     = data.get("sleep",     None)
    readiness_d = data.get("readiness", None)

    # ── HRV → next-day readiness scatter ──────────────────────────────────
    if sleep_d is not None and not sleep_d.empty and \
       readiness_d is not None and not readiness_d.empty:
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
            apply_axis_style(fig, T)
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

    # ── Full metric correlation heatmap (#6) ──────────────────────────────
    st.markdown("#### Full Metric Correlation Matrix")
    corr_mat = get_correlation_matrix(data)
    if corr_mat.empty:
        st.info("Load data from multiple data types to see a correlation matrix.")
        return

    fig = px.imshow(
        corr_mat,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1, zmax=1,
        aspect="auto",
    )
    fig.update_layout(**CHART_LAYOUT, height=520)
    apply_axis_style(fig, T)
    st.plotly_chart(fig, use_container_width=True)
