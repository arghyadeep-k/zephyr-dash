"""Comprehensive tests for data_utils.py."""
import io
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

# Patch st.cache_data to identity before any data_utils import
with patch("streamlit.cache_data", lambda f: f):
    from data_utils import (
        detect_columns, detect_type, normalize_df, aggregate_to_daily, load_file,
        add_hrv_anomalies, get_weekly_summary,
        get_hrv_readiness_corr, get_correlation_matrix,
        rolling_line,
    )


def make_df(csv_str):
    return pd.read_csv(io.StringIO(csv_str))


# ---------------------------------------------------------------------------
# detect_columns
# ---------------------------------------------------------------------------

class TestDetectColumns:
    def test_zepp_sleep_csv_headers_detect_all_9_canonical_columns(self):
        csv = (
            "Date,Sleep Score,Deep Sleep Duration(min),Light Sleep Duration(min),"
            "REM Sleep Duration(min),Awake Time(min),HRV(night),Resting Heart Rate(bpm),"
            "Breathing Rate(rpm)\n"
            "2024-01-15,82,90,200,110,25,48.2,58,14.9\n"
        )
        df = make_df(csv)
        col_map = detect_columns(df)
        for canon in ["date", "sleep_score", "deep_sleep", "light_sleep", "rem_sleep",
                      "awake_time", "hrv", "resting_hr", "breathing_rate"]:
            assert canon in col_map, f"Expected '{canon}' to be detected"

    def test_zepp_activity_headers_detect_all_activity_columns(self):
        csv = "Date,Steps,Calories(kcal),Active Minutes,Distance(km)\n2024-01-15,9000,2100,55,7.2\n"
        df = make_df(csv)
        col_map = detect_columns(df)
        for canon in ["date", "steps", "calories", "active_minutes", "distance"]:
            assert canon in col_map, f"Expected '{canon}' to be detected"

    def test_variant_hrv_score_header_detects_hrv(self):
        df = make_df("hrv score\n45.0\n")
        col_map = detect_columns(df)
        assert "hrv" in col_map

    def test_variant_rhr_header_detects_resting_hr(self):
        df = make_df("rhr\n58\n")
        col_map = detect_columns(df)
        assert "resting_hr" in col_map

    def test_variant_biocharge_detects_readiness_score(self):
        df = make_df("biocharge\n72\n")
        col_map = detect_columns(df)
        assert "readiness_score" in col_map

    def test_totally_unknown_columns_returns_empty_or_only_date(self):
        df = make_df("foo,bar,baz\n1,2,3\n")
        col_map = detect_columns(df)
        for canon in col_map:
            assert canon == "date", f"Unexpected canonical column: {canon}"

    def test_no_false_positive_for_identifier_column(self):
        df = make_df("identifier,value\n1,2\n")
        col_map = detect_columns(df)
        # "identifier" should NOT match any canonical column
        for canon, actual in col_map.items():
            assert actual != "identifier", (
                f"'identifier' was incorrectly detected as '{canon}'"
            )


# ---------------------------------------------------------------------------
# detect_type
# ---------------------------------------------------------------------------

class TestDetectType:
    def test_sleep_columns_return_sleep(self):
        col_map = {"sleep_score": "Sleep Score", "deep_sleep": "Deep", "rem_sleep": "REM"}
        assert detect_type(col_map) == "sleep"

    def test_activity_columns_return_activity(self):
        col_map = {"steps": "Steps", "calories": "Calories", "active_minutes": "Active"}
        assert detect_type(col_map) == "activity"

    def test_heart_rate_column_returns_heart_rate(self):
        col_map = {"heart_rate": "HR"}
        assert detect_type(col_map) == "heart_rate"

    def test_stress_columns_return_stress(self):
        col_map = {"stress_avg": "Stress", "stress_high": "H", "stress_low": "L"}
        assert detect_type(col_map) == "stress"

    def test_readiness_score_returns_readiness(self):
        col_map = {"readiness_score": "Readiness"}
        assert detect_type(col_map) == "readiness"

    def test_empty_dict_returns_unknown(self):
        assert detect_type({}) == "unknown"

    def test_only_date_returns_unknown(self):
        assert detect_type({"date": "Date"}) == "unknown"


# ---------------------------------------------------------------------------
# normalize_df
# ---------------------------------------------------------------------------

class TestNormalizeDf:
    def _make_sleep_df(self, rows):
        """Helper to build a raw DF with Zepp-style headers."""
        return pd.DataFrame(rows, columns=[
            "Date", "Sleep Score", "HRV(night)", "Resting Heart Rate(bpm)"
        ])

    def _col_map(self):
        return {
            "date": "Date",
            "sleep_score": "Sleep Score",
            "hrv": "HRV(night)",
            "resting_hr": "Resting Heart Rate(bpm)",
        }

    def test_columns_are_renamed_to_canonical_names(self):
        df_raw = self._make_sleep_df([["2024-01-15", 82, 48.2, 58]])
        result = normalize_df(df_raw, self._col_map())
        assert "date" in result.columns
        assert "sleep_score" in result.columns
        assert "hrv" in result.columns
        assert "resting_hr" in result.columns

    def test_date_iso_format_parsed(self):
        df_raw = self._make_sleep_df([["2024-01-15", 82, 48.2, 58]])
        result = normalize_df(df_raw, self._col_map())
        assert result["date"].iloc[0] == pd.Timestamp("2024-01-15")

    def test_date_slash_format_parsed(self):
        df_raw = self._make_sleep_df([["15/01/2024", 82, 48.2, 58]])
        result = normalize_df(df_raw, self._col_map())
        assert result["date"].iloc[0] == pd.Timestamp("2024-01-15")

    def test_date_verbose_format_parsed(self):
        df_raw = self._make_sleep_df([["January 15, 2024", 82, 48.2, 58]])
        result = normalize_df(df_raw, self._col_map())
        assert result["date"].iloc[0] == pd.Timestamp("2024-01-15")

    def test_rows_with_unparseable_dates_are_dropped(self):
        df_raw = self._make_sleep_df([
            ["2024-01-15", 82, 48.2, 58],
            ["not-a-date", 75, 45.0, 60],
        ])
        result = normalize_df(df_raw, self._col_map())
        assert len(result) == 1
        assert result["date"].iloc[0] == pd.Timestamp("2024-01-15")

    def test_numeric_string_becomes_float(self):
        df_raw = self._make_sleep_df([["2024-01-15", "72.5", "48.2", "58"]])
        result = normalize_df(df_raw, self._col_map())
        assert result["sleep_score"].iloc[0] == pytest.approx(72.5)

    def test_non_numeric_becomes_nan(self):
        df_raw = self._make_sleep_df([["2024-01-15", "N/A", "48.2", "58"]])
        result = normalize_df(df_raw, self._col_map())
        assert pd.isna(result["sleep_score"].iloc[0])

    def test_result_sorted_ascending_by_date(self):
        df_raw = self._make_sleep_df([
            ["2024-01-20", 80, 48.0, 58],
            ["2024-01-15", 82, 48.2, 59],
            ["2024-01-18", 79, 47.5, 60],
        ])
        result = normalize_df(df_raw, self._col_map())
        dates = result["date"].tolist()
        assert dates == sorted(dates)

    def test_unrecognised_columns_are_dropped(self):
        df_raw = pd.DataFrame([["2024-01-15", 82, 99]], columns=["Date", "Sleep Score", "unknown_col"])
        col_map = {"date": "Date", "sleep_score": "Sleep Score"}
        result = normalize_df(df_raw, col_map)
        assert "unknown_col" not in result.columns


# ---------------------------------------------------------------------------
# aggregate_to_daily
# ---------------------------------------------------------------------------

class TestAggregateToDaily:
    def test_multiple_readings_per_day_collapsed_to_one_row(self):
        df = pd.DataFrame({
            "date": pd.to_datetime([
                "2024-01-15", "2024-01-15", "2024-01-15",
                "2024-01-16", "2024-01-16",
            ]),
            "heart_rate": [70, 80, 90, 60, 64],
            "resting_hr": [55, 58, 56, 50, 52],
        })
        result = aggregate_to_daily(df, "heart_rate")
        assert len(result) == 2

    def test_heart_rate_aggregated_with_mean(self):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-15"] * 3),
            "heart_rate": [70, 80, 90],
        })
        result = aggregate_to_daily(df, "heart_rate")
        assert result["heart_rate"].iloc[0] == pytest.approx(80.0)

    def test_resting_hr_aggregated_with_min(self):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-15"] * 3),
            "resting_hr": [55, 48, 62],
        })
        result = aggregate_to_daily(df, "heart_rate")
        assert result["resting_hr"].iloc[0] == 48

    def test_non_heart_rate_dtype_passed_through_unchanged(self):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-15", "2024-01-15"]),
            "sleep_score": [80, 85],
        })
        result = aggregate_to_daily(df, "sleep")
        pd.testing.assert_frame_equal(df, result)

    def test_already_daily_data_unchanged(self):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-15", "2024-01-16"]),
            "heart_rate": [70, 72],
        })
        result = aggregate_to_daily(df, "heart_rate")
        assert len(result) == 2
        assert result["heart_rate"].tolist() == [70, 72]

    def test_large_multi_month_high_frequency_file_collapses_correctly(self):
        n_days, per_day = 30, 50
        dates = pd.to_datetime(
            [d for d in pd.date_range("2024-01-01", periods=n_days) for _ in range(per_day)]
        )
        rng = np.random.default_rng(0)
        df = pd.DataFrame({
            "date": dates,
            "heart_rate": rng.normal(70, 5, n_days * per_day),
        })
        result = aggregate_to_daily(df, "heart_rate")
        assert len(result) == n_days


# ---------------------------------------------------------------------------
# load_file (pipeline ordering)
# ---------------------------------------------------------------------------

class TestLoadFilePipelineOrder:
    def test_high_frequency_heart_rate_csv_detected_and_collapsed_to_daily(self):
        rows = []
        for day in pd.date_range("2024-01-01", periods=5):
            for hr in [65, 70, 75, 80, 72]:
                rows.append(f"{day.date()},{hr}\n")
        csv = "Date,avg bpm\n" + "".join(rows)
        df, dtype, col_map = load_file(io.BytesIO(csv.encode()))
        assert dtype == "heart_rate"
        assert len(df) == 5  # collapsed from 25 raw readings to 5 days


# ---------------------------------------------------------------------------
# add_hrv_anomalies
# ---------------------------------------------------------------------------

class TestAddHrvAnomalies:
    def _sleep_df(self, hrv_values, start="2024-01-01"):
        dates = pd.date_range(start, periods=len(hrv_values))
        return pd.DataFrame({"date": dates, "hrv": hrv_values})

    def test_no_hrv_column_returned_unchanged(self):
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=5), "sleep_score": [80]*5})
        result = add_hrv_anomalies(df)
        assert "hrv_anomaly" not in result.columns
        assert "hrv_7d_avg" not in result.columns
        pd.testing.assert_frame_equal(df, result)

    def test_30_percent_drop_is_flagged(self):
        # Stable HRV at 50 for 10 days, then a 30% drop
        hrv = [50.0] * 10 + [35.0]  # 35 = 50 * 0.70, a 30% drop
        df = self._sleep_df(hrv)
        result = add_hrv_anomalies(df)
        assert result["hrv_anomaly"].iloc[-1] == True

    def test_10_percent_drop_not_flagged_with_default_threshold(self):
        # Default threshold is 20%; a 10% drop should NOT be flagged
        hrv = [50.0] * 10 + [45.0]  # 45 = 50 * 0.90, a 10% drop
        df = self._sleep_df(hrv)
        result = add_hrv_anomalies(df)
        assert result["hrv_anomaly"].iloc[-1] == False

    def test_10_percent_drop_flagged_with_custom_drop_pct_0_08(self):
        # With threshold of 8%, a 10% drop SHOULD be flagged
        hrv = [50.0] * 10 + [45.0]  # 10% drop
        df = self._sleep_df(hrv)
        result = add_hrv_anomalies(df, drop_pct=0.08)
        assert result["hrv_anomaly"].iloc[-1] == True

    def test_hrv_7d_avg_uses_shift_1_not_own_avg(self):
        # The row itself is never compared to an average that includes itself.
        # hrv_7d_avg at row i should be NaN or based on rows < i.
        hrv = [50.0] * 15
        df = self._sleep_df(hrv)
        result = add_hrv_anomalies(df)
        # First row must have NaN avg (shift(1) means row 0 gets NaN)
        assert pd.isna(result["hrv_7d_avg"].iloc[0])
        # Row 3 (index 3) has shift(1) of rolling(window=7, min_periods=3).
        # rolling at index 2 (rows 0,1,2) has 3 observations => not NaN.
        # shifted by 1, so index 3 should be the first non-NaN avg.
        assert pd.notna(result["hrv_7d_avg"].iloc[3])

    def test_fewer_than_3_data_points_no_anomaly(self):
        hrv = [50.0, 30.0]  # Only 2 data points
        df = self._sleep_df(hrv)
        result = add_hrv_anomalies(df)
        # With min_periods=3, rolling avg is NaN, so anomaly should be False
        assert result["hrv_anomaly"].iloc[-1] == False
        assert pd.isna(result["hrv_7d_avg"].iloc[-1])


# ---------------------------------------------------------------------------
# get_weekly_summary
# ---------------------------------------------------------------------------

class TestGetWeeklySummary:
    def _make_data(self):
        today = pd.Timestamp.now().normalize()
        this_start = today - pd.Timedelta(days=today.dayofweek)  # Monday
        last_start = this_start - pd.Timedelta(weeks=1)

        # Generate 14 days spanning current + prior week
        dates = pd.date_range(last_start, periods=14)
        sleep_df = pd.DataFrame({
            "date": dates,
            "sleep_score": [80.0] * 7 + [85.0] * 7,  # last=80, this=85
            "hrv": [45.0] * 14,
            "deep_sleep": [90.0] * 14,
            "rem_sleep": [100.0] * 14,
            "resting_hr": [58.0] * 14,
        })
        activity_df = pd.DataFrame({
            "date": dates,
            "steps": [8000.0] * 7 + [10000.0] * 7,
            "calories": [2200.0] * 14,
            "active_minutes": [45.0] * 14,
        })
        return {"sleep": sleep_df, "activity": activity_df}

    def test_returns_dataframe_with_metric_column(self):
        data = self._make_data()
        result = get_weekly_summary(data)
        assert isinstance(result, pd.DataFrame)
        assert "metric" in result.columns

    def test_metric_column_contains_friendly_names(self):
        data = self._make_data()
        result = get_weekly_summary(data)
        metrics = result["metric"].tolist()
        assert "Sleep Score" in metrics
        assert "Steps" in metrics

    def test_this_week_and_last_week_values_are_plausible(self):
        data = self._make_data()
        result = get_weekly_summary(data)
        sleep_row = result[result["metric"] == "Sleep Score"].iloc[0]
        # last week avg = 80, this week avg = 85
        assert sleep_row["last_week"] == pytest.approx(80.0, abs=1.0)
        assert sleep_row["this_week"] == pytest.approx(85.0, abs=1.0)

    def test_change_pct_formula(self):
        data = self._make_data()
        result = get_weekly_summary(data)
        # sleep: last=80, this=85 -> change = (85-80)/80*100 = 6.25 -> rounded to 6.2 or 6.3
        sleep_row = result[result["metric"] == "Sleep Score"].iloc[0]
        expected_change = round((85.0 - 80.0) / 80.0 * 100, 1)
        assert sleep_row["change_pct"] == pytest.approx(expected_change, abs=0.5)

    def test_absent_data_type_metrics_not_in_results(self):
        # Only sleep data, no stress or readiness
        data = self._make_data()
        result = get_weekly_summary(data)
        metrics = result["metric"].tolist()
        assert "Avg Stress" not in metrics
        assert "Readiness Score" not in metrics


# ---------------------------------------------------------------------------
# get_hrv_readiness_corr
# ---------------------------------------------------------------------------

class TestGetHrvReadinessCorr:
    def _make_dfs(self, n=10, start="2024-01-01"):
        dates = pd.date_range(start, periods=n)
        sleep_df = pd.DataFrame({"date": dates, "hrv": np.linspace(40, 60, n)})
        # readiness on day N should pair with HRV on day N-1
        # so readiness_df dates = hrv dates + 1 day
        read_df = pd.DataFrame({
            "date": dates + pd.Timedelta(days=1),
            "readiness_score": np.linspace(60, 80, n),
        })
        return sleep_df, read_df

    def test_hrv_pairs_with_next_morning_readiness(self):
        sleep_df, read_df = self._make_dfs(n=10)
        result = get_hrv_readiness_corr(sleep_df, read_df)
        assert not result.empty
        assert "hrv" in result.columns
        assert "readiness_score" in result.columns
        # All rows should have both values (no NaN in the join)
        assert result["hrv"].notna().all()
        assert result["readiness_score"].notna().all()

    def test_rows_with_nan_hrv_or_readiness_excluded(self):
        sleep_df, read_df = self._make_dfs(n=5)
        sleep_df.loc[2, "hrv"] = np.nan
        read_df.loc[3, "readiness_score"] = np.nan
        result = get_hrv_readiness_corr(sleep_df, read_df)
        assert result["hrv"].notna().all()
        assert result["readiness_score"].notna().all()

    def test_no_date_overlap_returns_empty_dataframe(self):
        sleep_df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=5), "hrv": [45.0]*5})
        read_df = pd.DataFrame({
            "date": pd.date_range("2024-06-01", periods=5),
            "readiness_score": [70.0]*5,
        })
        result = get_hrv_readiness_corr(sleep_df, read_df)
        assert result.empty

    def test_missing_hrv_column_returns_empty_dataframe(self):
        sleep_df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "sleep_score": [80]*3})
        read_df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "readiness_score": [70]*3})
        result = get_hrv_readiness_corr(sleep_df, read_df)
        assert result.empty

    def test_missing_readiness_score_column_returns_empty_dataframe(self):
        sleep_df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "hrv": [45.0]*3})
        read_df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "steps": [8000]*3})
        result = get_hrv_readiness_corr(sleep_df, read_df)
        assert result.empty


# ---------------------------------------------------------------------------
# get_correlation_matrix
# ---------------------------------------------------------------------------

class TestGetCorrelationMatrix:
    def _make_data(self, n=30):
        dates = pd.date_range("2024-01-01", periods=n)
        sleep_df = pd.DataFrame({
            "date": dates,
            "hrv": np.linspace(40, 60, n),
            "sleep_score": np.linspace(70, 90, n),
            "resting_hr": np.linspace(55, 65, n),
        })
        return {"sleep": sleep_df}

    def test_returns_n_by_n_dataframe(self):
        data = self._make_data()
        result = get_correlation_matrix(data)
        n = len(result)
        assert result.shape == (n, n)
        assert n == 3  # hrv, sleep_score, resting_hr

    def test_diagonal_is_all_ones(self):
        data = self._make_data()
        result = get_correlation_matrix(data)
        diag = np.diag(result.values)
        np.testing.assert_allclose(diag, 1.0)

    def test_returns_empty_when_fewer_than_3_metrics(self):
        dates = pd.date_range("2024-01-01", periods=10)
        data = {"sleep": pd.DataFrame({"date": dates, "hrv": np.ones(10), "sleep_score": np.ones(10)})}
        result = get_correlation_matrix(data)
        assert result.empty

    def test_non_numeric_columns_are_excluded(self):
        dates = pd.date_range("2024-01-01", periods=10)
        df = pd.DataFrame({
            "date": dates,
            "hrv": np.linspace(40, 60, 10),
            "sleep_score": np.linspace(70, 90, 10),
            "resting_hr": np.linspace(55, 65, 10),
            "label": ["good"] * 10,  # string column — must be excluded
        })
        data = {"sleep": df}
        result = get_correlation_matrix(data)
        # "label" should not appear in index or columns
        assert "label" not in result.index
        assert "label" not in result.columns

    def test_friendly_names_used_as_index_and_columns(self):
        data = self._make_data()
        result = get_correlation_matrix(data)
        # Should use friendly names, not canonical names
        assert "HRV" in result.index
        assert "hrv" not in result.index


# ---------------------------------------------------------------------------
# rolling_line
# ---------------------------------------------------------------------------

class TestRollingLine:
    def test_returns_series_with_correct_rolling_mean(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        result = rolling_line(s)
        # At index 9 (last), window is [4,5,6,7,8,9,10], mean = 7.0
        assert result.iloc[9] == pytest.approx(7.0)

    def test_first_2_values_are_nan(self):
        s = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        result = rolling_line(s)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])

    def test_third_value_onwards_is_computed(self):
        s = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        result = rolling_line(s)
        # Index 2: window = [10, 20, 30], mean = 20.0 (min_periods=3 satisfied)
        assert result.iloc[2] == pytest.approx(20.0)
        assert pd.notna(result.iloc[2])
        assert pd.notna(result.iloc[3])
        assert pd.notna(result.iloc[4])
