"""Shared chart helpers for tab render functions."""
import pandas as pd
import plotly.graph_objects as go


def apply_axis_style(fig: go.Figure, T: dict) -> None:
    """Apply themed grid and line colours to both axes."""
    style = dict(gridcolor=T["grid"], linecolor=T["grid"])
    fig.update_xaxes(**style)
    fig.update_yaxes(**style)


def downsample_for_plot(df: pd.DataFrame, date_col: str = "date", max_points: int = 2000) -> pd.DataFrame:
    """If df exceeds max_points rows, resample to daily means so Plotly stays responsive."""
    if len(df) <= max_points:
        return df
    numeric_cols = [c for c in df.columns if c != date_col and pd.api.types.is_numeric_dtype(df[c])]
    return df.set_index(date_col)[numeric_cols].resample("D").mean().dropna(how="all").reset_index()
