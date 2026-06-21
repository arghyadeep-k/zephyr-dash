"""Tests for zepp_api.py — all network calls mocked, no real HTTP."""
import base64
import json
from unittest.mock import patch, Mock

import pandas as pd
import pytest

from zepp_api import (
    login, fetch_band_data, parse_band_data,
    ZeppAuthError, ZeppFetchError, ZeppSession,
)


def _make_summary(steps=8000, dist_m=6500, cal=2100, deep=80, light=200):
    return {
        "stp": {"ttl": steps, "dis": dist_m, "cal": cal},
        "slp": {"dp": deep, "lt": light},
    }


def _make_raw_entry(date_str, summary_dict):
    encoded = base64.b64encode(json.dumps(summary_dict).encode()).decode()
    return {"date_time": date_str, "summary": encoded}


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

class TestLogin:
    @patch("requests.post")
    def test_successful_two_step_login_returns_session(self, mock_post):
        step1_resp = Mock(status_code=200)
        step1_resp.json.return_value = {"access": "ACCESSCODE", "country_code": "US"}
        step2_resp = Mock(status_code=200)
        step2_resp.json.return_value = {
            "token_info": {"app_token": "APPTOKEN", "user_id": "USERID"}
        }
        mock_post.side_effect = [step1_resp, step2_resp]

        session = login("user@example.com", "hunter2")

        assert session.app_token == "APPTOKEN"
        assert session.user_id == "USERID"

    @patch("requests.post")
    def test_bad_credentials_raises_zepp_auth_error(self, mock_post):
        bad_resp = Mock(status_code=200, headers={})
        bad_resp.json.return_value = {"error": "invalid_grant"}
        mock_post.return_value = bad_resp

        with pytest.raises(ZeppAuthError):
            login("user@example.com", "wrongpass")

    @patch("requests.post")
    def test_non_200_on_first_step_raises_zepp_auth_error(self, mock_post):
        bad_resp = Mock(status_code=403, headers={})
        mock_post.return_value = bad_resp

        with pytest.raises(ZeppAuthError):
            login("user@example.com", "hunter2")

    @patch("requests.post")
    def test_network_error_raises_zepp_auth_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.ConnectionError("boom")

        with pytest.raises(ZeppAuthError):
            login("user@example.com", "hunter2")

    @patch("requests.post")
    def test_unexpected_token_response_shape_raises_zepp_auth_error(self, mock_post):
        step1_resp = Mock(status_code=200)
        step1_resp.json.return_value = {"access": "ACCESSCODE", "country_code": "US"}
        step2_resp = Mock(status_code=200)
        step2_resp.json.return_value = {"unexpected": "shape"}
        mock_post.side_effect = [step1_resp, step2_resp]

        with pytest.raises(ZeppAuthError):
            login("user@example.com", "hunter2")


# ---------------------------------------------------------------------------
# fetch_band_data
# ---------------------------------------------------------------------------

class TestFetchBandData:
    @patch("requests.get")
    def test_successful_fetch_returns_data_list(self, mock_get):
        resp = Mock(status_code=200)
        resp.json.return_value = {"data": [{"date_time": "20240115", "summary": "abc"}]}
        mock_get.return_value = resp

        session = ZeppSession(app_token="t", user_id="u")
        result = fetch_band_data(session, "2024-01-01", "2024-01-31")

        assert result == [{"date_time": "20240115", "summary": "abc"}]

    @patch("requests.get")
    def test_non_200_raises_zepp_fetch_error(self, mock_get):
        resp = Mock(status_code=401, reason="Unauthorized")
        mock_get.return_value = resp

        session = ZeppSession(app_token="expired", user_id="u")
        with pytest.raises(ZeppFetchError):
            fetch_band_data(session, "2024-01-01", "2024-01-31")

    @patch("requests.get")
    def test_network_error_raises_zepp_fetch_error(self, mock_get):
        import requests
        mock_get.side_effect = requests.Timeout("timed out")

        session = ZeppSession(app_token="t", user_id="u")
        with pytest.raises(ZeppFetchError):
            fetch_band_data(session, "2024-01-01", "2024-01-31")

    @patch("requests.get")
    def test_missing_data_key_raises_zepp_fetch_error(self, mock_get):
        resp = Mock(status_code=200)
        resp.json.return_value = {"unexpected": "shape"}
        mock_get.return_value = resp

        session = ZeppSession(app_token="t", user_id="u")
        with pytest.raises(ZeppFetchError):
            fetch_band_data(session, "2024-01-01", "2024-01-31")


# ---------------------------------------------------------------------------
# parse_band_data
# ---------------------------------------------------------------------------

class TestParseBandData:
    def test_single_day_maps_to_activity_and_sleep_rows(self):
        entry = _make_raw_entry("20240115", _make_summary())
        activity_df, sleep_df = parse_band_data([entry])

        assert len(activity_df) == 1
        assert len(sleep_df) == 1
        assert activity_df["steps"].iloc[0] == 8000
        assert activity_df["distance"].iloc[0] == pytest.approx(6.5)
        assert activity_df["calories"].iloc[0] == 2100
        assert sleep_df["deep_sleep"].iloc[0] == 80
        assert sleep_df["light_sleep"].iloc[0] == 200
        assert sleep_df["total_sleep"].iloc[0] == 280

    def test_distance_meters_converted_to_km(self):
        entry = _make_raw_entry("20240115", _make_summary(dist_m=12345))
        activity_df, _ = parse_band_data([entry])
        assert activity_df["distance"].iloc[0] == pytest.approx(12.345)

    def test_date_parsed_to_timestamp(self):
        entry = _make_raw_entry("20240115", _make_summary())
        activity_df, _ = parse_band_data([entry])
        assert activity_df["date"].iloc[0] == pd.Timestamp("2024-01-15")

    def test_malformed_base64_entry_is_skipped_not_raised(self):
        good = _make_raw_entry("20240115", _make_summary())
        bad = {"date_time": "20240116", "summary": "not-valid-base64!!!"}
        activity_df, sleep_df = parse_band_data([good, bad])
        assert len(activity_df) == 1  # bad day skipped, good day kept

    def test_entry_missing_date_time_is_skipped(self):
        good = _make_raw_entry("20240115", _make_summary())
        bad = {"summary": good["summary"]}
        activity_df, _ = parse_band_data([good, bad])
        assert len(activity_df) == 1

    def test_empty_input_returns_empty_dataframes(self):
        activity_df, sleep_df = parse_band_data([])
        assert activity_df.empty
        assert sleep_df.empty

    def test_multiple_days_sorted_by_date(self):
        e1 = _make_raw_entry("20240117", _make_summary())
        e2 = _make_raw_entry("20240115", _make_summary())
        activity_df, _ = parse_band_data([e1, e2])
        dates = activity_df["date"].tolist()
        assert dates == sorted(dates)

    def test_no_active_minutes_column_fabricated(self):
        entry = _make_raw_entry("20240115", _make_summary())
        activity_df, _ = parse_band_data([entry])
        assert "active_minutes" not in activity_df.columns
