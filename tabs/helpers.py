"""Shared chart helpers for tab render functions."""
import plotly.graph_objects as go


def apply_axis_style(fig: go.Figure, T: dict) -> None:
    """Apply themed grid and line colours to both axes."""
    style = dict(gridcolor=T["grid"], linecolor=T["grid"])
    fig.update_xaxes(**style)
    fig.update_yaxes(**style)
