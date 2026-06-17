# Zephyr Dash — TO DO Fixes

Identified from codebase analysis. Grouped by priority.

---

## High Priority

### 1. `st.stop()` kills all subsequent tabs — BUG
**File:** `app.py:406`  
`st.stop()` inside `with tab_sleep:` halts the entire script, so Activity, Heart Rate, and all later tabs never render when sleep data is missing.  
**Fix:** Replace with an `else:` block that wraps the tab's content, so only that tab is affected.

```python
# current (broken)
with tab_sleep:
    if "sleep" not in data or data["sleep"].empty:
        st.info("...")
        st.stop()

# fix
with tab_sleep:
    if "sleep" not in data or data["sleep"].empty:
        st.info("...")
    else:
        # all sleep tab content here
```

---

### 2. Add `@st.cache_data` to all pure computations — PERFORMANCE
**File:** `data_utils.py`  
`add_hrv_anomalies`, `get_hrv_readiness_corr`, `get_weekly_summary`, and `global_date_bounds` (in `app.py`) are recomputed on every Streamlit rerun (every click, theme toggle, date change).  
**Fix:** Decorate each with `@st.cache_data`.

```python
@st.cache_data
def add_hrv_anomalies(df: pd.DataFrame, window: int = 7, drop_pct: float = 0.20) -> pd.DataFrame:
    ...
```

---

### 3. Add `.gitignore`
**File:** repo root  
No `.gitignore` exists. `__pycache__/` was manually excluded from the initial commit but will eventually slip in.  
**Fix:** Add a standard Python `.gitignore` covering `__pycache__/`, `*.pyc`, `.env`, `.DS_Store`, and `*.csv` (to avoid accidentally committing personal health data).

---

## Medium Priority

### 4. Weekly "this week" slice misses the current partial week — BUG
**File:** `data_utils.py:183`  
`this_start + pd.Timedelta(days=6)` always ends on Sunday. Mid-week runs (e.g. Wednesday) silently exclude Wed–Sat data.  
**Fix:**
```python
# current
this_week = df[df["date"].between(this_start, this_start + pd.Timedelta(days=6))]

# fix
today = pd.Timestamp.now().normalize()
this_week = df[df["date"].between(this_start, today)]
```

---

### 5. Split `app.py` into tab modules — ARCHITECTURE
**File:** `app.py` (869 lines)  
All 8 tabs are inlined in a single file, making it hard to navigate, test, or extend.  
**Fix:** Extract each tab into its own function or module:
```
tabs/
  __init__.py
  sleep.py
  activity.py
  heart_rate.py
  stress.py
  readiness.py
  correlations.py
  weekly_summary.py
```
`app.py` becomes a thin orchestrator that calls `tabs.sleep.render(data, CHART_LAYOUT, C, T)` etc.

---

### 6. Move correlation matrix build out of inline tab code — PERFORMANCE
**File:** `app.py:773–795`  
`pd.DataFrame(series_map).corr()` is built inline on every rerun. Should be extracted to `data_utils.py` as `get_correlation_matrix(data)` and decorated with `@st.cache_data`.

---

### 7. Add per-dataset removal in sidebar — UX
**File:** `app.py` sidebar section  
Currently only "Clear all" exists. Uploading a wrong file requires wiping all data and starting over.  
**Fix:** Add a ✕ button next to each loaded dataset in the sidebar:
```python
for dtype, df in list(st.session_state.data.items()):
    col_a, col_b = st.columns([5, 1])
    col_a.markdown(f"- **{dtype}** — {len(df)} rows")
    if col_b.button("✕", key=f"remove_{dtype}"):
        del st.session_state.data[dtype]
        st.rerun()
```

---

### 8. Make HRV anomaly threshold configurable — UX
**File:** `app.py:408`, `data_utils.py:152`  
The 20% drop threshold is hardcoded and invisible to the user. A power user might want to tighten or relax it.  
**Fix:** Add a sidebar slider (inside a collapsed expander to keep it tidy):
```python
with st.sidebar.expander("Advanced settings"):
    hrv_threshold = st.slider("HRV anomaly threshold (%)", 10, 40, 20) / 100
```
Then pass it: `add_hrv_anomalies(data["sleep"], drop_pct=hrv_threshold)`

---

## Low Priority

### 9. Date range: no validation when From > To — UX
**File:** `app.py` sidebar  
If the user sets "From" after "To", all filtered DataFrames are empty and every tab silently shows "No data in range" with no explanation.  
**Fix:** Add a check after the date inputs:
```python
if START > END:
    st.sidebar.error("'From' date must be before 'To' date.")
    st.stop()
```

---

### 10. Redundant boolean comparison — CODE QUALITY
**File:** `app.py:467`  
```python
# current
anomalies = hv[hv["hrv_anomaly"] == True]

# fix
anomalies = hv[hv["hrv_anomaly"]]
```

---

### 11. Hardcoded step and activity goals — CODE QUALITY
**File:** `app.py:549`, `app.py:572`  
`10000` (step goal) and `30` (active minutes goal) are magic numbers inline in chart code.  
**Fix:** Define as module-level constants:
```python
STEP_GOAL            = 10_000
ACTIVE_MINUTES_GOAL  = 30
```

---

### 12. `"cal"` alias too broad — DATA HANDLING
**File:** `data_utils.py:20`  
The alias `"cal"` for `calories` scores 0.9 (substring match) against columns like `"calender"`, `"local"`, or `"recall"`. Short tokens are risky in the substring-based scorer.  
**Fix:** Remove `"cal"` from the alias list; the other aliases (`"calories"`, `"kcal"`, `"calorie"`) are specific enough.

---

### 13. `total_sleep` column detected but never rendered — CODE QUALITY
**File:** `data_utils.py:15`, `app.py` (all tabs)  
`total_sleep` is in `COLUMN_ALIASES` and `FRIENDLY_NAMES` but no chart or summary ever uses it.  
**Fix:** Either add it to the Sleep tab (e.g. as a summary stat or overlay on the stage breakdown chart) or remove it from the alias registry entirely.

---

### 14. `CHART_LAYOUT` `xaxis`/`yaxis` keys silently drop per-chart axis settings — CODE QUALITY
**File:** `app.py:180–181`  
Spreading `**CHART_LAYOUT` into `fig.update_layout()` replaces the full `xaxis`/`yaxis` config objects, which can silently drop per-chart settings (like `yaxis_range`) added in the same call depending on key ordering.  
**Fix:** Remove `xaxis` and `yaxis` from `CHART_LAYOUT` and apply grid/line colors separately via:
```python
fig.update_xaxes(gridcolor=T["grid"], linecolor=T["grid"])
fig.update_yaxes(gridcolor=T["grid"], linecolor=T["grid"])
```

---

### 15. Add unit tests for `data_utils.py` — TESTING
**File:** new `tests/test_data_utils.py`  
`detect_columns` and `detect_type` are the core of the auto-detection logic and have zero test coverage. A regression here silently breaks all CSV uploads.  
**Fix:** Add a `pytest` suite with fixtures covering:
- Exact Zepp header formats (current known exports)
- Headers with units stripped/changed
- Ambiguous columns (e.g. a file with both `"stress"` and `"calories"`)
- Completely unrecognised files (should return `dtype == "unknown"`)

---

## Tracking

| # | Title | Priority | Status |
|---|---|---|---|
| 1 | `st.stop()` bug in sleep tab | High | ✅ Done |
| 2 | Cache pure computations | High | ✅ Done |
| 3 | Add `.gitignore` | High | ✅ Done |
| 4 | Weekly slice misses current week | Medium | ✅ Done |
| 5 | Split `app.py` into tab modules | Medium | ✅ Done |
| 6 | Move correlation matrix to `data_utils` | Medium | ✅ Done |
| 7 | Per-dataset removal in sidebar | Medium | ✅ Done |
| 8 | Configurable HRV anomaly threshold | Medium | ✅ Done |
| 9 | Date range From > To validation | Low | ✅ Done |
| 10 | Redundant `== True` comparison | Low | ✅ Done |
| 11 | Hardcoded step/activity goals | Low | ✅ Done |
| 12 | `"cal"` alias too broad | Low | ✅ Done |
| 13 | `total_sleep` unused | Low | ✅ Done |
| 14 | `CHART_LAYOUT` axis key conflict | Low | ⬜ Open |
| 15 | Unit tests for `data_utils.py` | Low | ⬜ Open |
