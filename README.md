# Zepp Health Dashboard

A Streamlit dashboard for visualising health data exported from Zepp / Amazfit devices (e.g. Helio Band).

## Features

- **CSV upload** — drop one or more Zepp CSV exports; the app auto-detects the data type and column names even if Zepp changes their headers
- **Date range filter** — all charts respond to a sidebar date picker
- **8 interactive tabs** — Overview, Sleep, Activity, Heart Rate, Stress, Readiness, Correlations, Weekly Summary
- **Sleep stage breakdown** — stacked area chart (deep / REM / light / awake)
- **HRV anomaly detection** — highlights nights where HRV dropped >20% from the 7-day rolling average
- **Correlation analysis** — scatter plot + Pearson r for overnight HRV vs next-day readiness; full metric correlation heatmap
- **Weekly summary** — this week vs last week comparison with % change for every key metric
- **Sample data** — one-click demo mode with 60 days of synthetic data (no device required)

## Supported CSV types

| Type | Key columns detected |
|---|---|
| Sleep | Sleep Score, Deep/Light/REM/Awake duration, HRV, Resting HR, Breathing Rate |
| Activity | Steps, Calories, Active Minutes, Distance |
| Heart Rate | Heart Rate, Resting HR |
| Stress | Avg / High / Low stress |
| Readiness | Readiness / BioCharge score |

Column names are matched fuzzily, so minor header changes between Zepp app versions are handled automatically.

## Setup

```bash
git clone <repo>
cd health-dash

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Deactivate the virtual environment when you're done with `deactivate`.

Requires Python 3.10+.

## Exporting data from Zepp

1. Open the **Zepp** app on your phone
2. Go to **Profile → My Data → Export Data**
3. Select the date range and data types you want
4. Download the ZIP and extract the CSV files
5. Upload them via the sidebar file uploader

## Project structure

```
health-dash/
├── app.py            # Streamlit UI (8 tabs)
├── data_utils.py     # Data loading, column detection, analytics
├── requirements.txt
└── .streamlit/
    └── config.toml   # Dark theme
```
