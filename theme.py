"""Theme configuration and CSS injection for the Zepp Health Dashboard."""
from typing import TypedDict

import streamlit as st

THEMES: dict[str, dict] = {
    "dark": {
        "bg":          "#0E1117",
        "sidebar_bg":  "#1e2130",
        "card_bg":     "#1e2130",
        "card_border": "none",
        "text":        "#e0e0e0",
        "subtext":     "#a0a0a0",
        "divider":     "#333",
        "primary":     "#4ECDC4",
        "font_color":  "#e0e0e0",
        "grid":        "rgba(255,255,255,0.08)",
        "avg_line":    "#ffffff",
        "plot_bg":     "rgba(0,0,0,0)",
        "paper_bg":    "rgba(0,0,0,0)",
    },
    "light": {
        "bg":          "#f8f9fa",
        "sidebar_bg":  "#eef0f5",
        "card_bg":     "#eef0f5",
        "card_border": "1px solid #dde1ec",
        "text":        "#1a1a1a",
        "subtext":     "#555555",
        "divider":     "#cccccc",
        "primary":     "#0d8a82",
        "font_color":  "#1a1a1a",
        "grid":        "rgba(0,0,0,0.08)",
        "avg_line":    "#333333",
        "plot_bg":     "rgba(0,0,0,0)",
        "paper_bg":    "rgba(0,0,0,0)",
    },
}

C = {
    "deep_sleep":      "#1565C0",
    "light_sleep":     "#90CAF9",
    "rem_sleep":       "#7B1FA2",
    "awake_time":      "#EF9A9A",
    "sleep_score":     "#26C6DA",
    "hrv":             "#66BB6A",
    "resting_hr":      "#EF5350",
    "breathing_rate":  "#AB47BC",
    "steps":           "#FFA726",
    "calories":        "#EC407A",
    "active_minutes":  "#26A69A",
    "distance":        "#78909C",
    "heart_rate":      "#FF7043",
    "stress_avg":      "#FF8A65",
    "stress_high":     "#D84315",
    "stress_low":      "#FFCC80",
    "readiness_score": "#5C6BC0",
    "anomaly":         "#E53935",
}


class RenderCtx(TypedDict):
    C: dict
    T: dict
    CHART_LAYOUT: dict
    AVG_LINE: str


def _inject_css(theme: str) -> None:
    t = THEMES[theme]
    if theme == "dark":
        st.markdown(f"""
        <style>
        div[data-testid="metric-container"] {{
            background: {t["card_bg"]};
            border-radius: 10px;
            padding: 12px 16px;
        }}
        </style>
        """, unsafe_allow_html=True)
        return

    st.markdown(f"""
    <style>
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section[data-testid="stMain"],
    .main .block-container {{
        background-color: {t["bg"]} !important;
    }}
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {{
        background-color: {t["sidebar_bg"]} !important;
    }}
    .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    .stApp span:not([data-testid]),
    .stApp label, .stApp li, .stMarkdown,
    [data-testid="stText"], [data-testid="stHeadingWithActionElements"] {{
        color: {t["text"]} !important;
    }}
    [data-testid="stCaptionContainer"],
    .stCaption {{ color: {t["subtext"]} !important; }}
    div[data-testid="metric-container"] {{
        background: {t["card_bg"]} !important;
        border: {t["card_border"]} !important;
        border-radius: 10px;
        padding: 12px 16px;
    }}
    [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"] {{ color: {t["text"]} !important; }}
    button[data-baseweb="tab"] {{ color: {t["subtext"]} !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {t["primary"]} !important; }}
    [data-testid="stTabs"] [data-baseweb="tab-border"] {{
        background-color: {t["primary"]} !important;
    }}
    [data-testid="stAlert"] {{
        background-color: #ddeeff !important;
        color: #1a1a1a !important;
    }}
    [data-testid="stAlert"] p {{ color: #1a1a1a !important; }}
    [data-testid="stExpander"] summary {{ color: {t["text"]} !important; }}
    hr {{ border-color: {t["divider"]} !important; }}
    [data-testid="stFileUploader"] section {{
        background-color: {t["card_bg"]} !important;
        border-color: {t["divider"]} !important;
    }}
    [data-testid="stButton"] button {{
        background: {t["card_bg"]} !important;
        color: {t["text"]} !important;
        border: 1px solid {t["divider"]} !important;
    }}
    [data-testid="stButton"] button:hover {{
        border-color: {t["primary"]} !important;
        color: {t["primary"]} !important;
    }}
    [data-testid="stDateInput"] input {{
        background: #fff !important;
        color: {t["text"]} !important;
    }}
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] li {{ color: {t["text"]} !important; }}
    </style>
    """, unsafe_allow_html=True)
