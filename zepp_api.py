"""Unofficial Huami/Zepp cloud API client — used for on-demand manual sync only.

This talks to a reverse-engineered, undocumented API with no official support from
Xiaomi/Huami/Zepp. It may stop working at any time and is not guaranteed to work for
every account — newer Zepp accounts may use an encrypted login flow this plaintext
password exchange does not support.
"""
import base64
import json
from dataclasses import dataclass

import pandas as pd
import requests

LOGIN_URL_TMPL = "https://api-user.huami.com/registrations/{email}/tokens"
TOKEN_URL = "https://account.huami.com/v2/client/login"
BAND_DATA_URL = "https://api-mifit.huami.com/v1/data/band_data.json"

REQUEST_TIMEOUT = 15  # seconds


class ZeppError(Exception):
    """Base class for all zepp_api errors."""


class ZeppAuthError(ZeppError):
    """Login failed — bad credentials, account locked, or (most likely for newer
    Zepp accounts) an encrypted login flow this client does not support."""


class ZeppFetchError(ZeppError):
    """The authenticated band_data request failed (network error, non-200,
    unexpected JSON shape, or expired token)."""


@dataclass
class ZeppSession:
    """Short-lived tokens for one sync. Never persisted to disk or session_state
    beyond the lifetime of a single sync."""
    app_token: str
    user_id: str


def login(email: str, password: str) -> ZeppSession:
    """Two-step Huami auth: exchange email+password for an access code, then
    exchange the access code for an app_token + user_id.

    Raises ZeppAuthError on any failure (bad credentials, network error,
    unexpected response shape, or HTTP error status).
    """
    try:
        step1 = requests.post(
            LOGIN_URL_TMPL.format(email=email),
            data={
                "password": password,
                "client_id": "HuaMi",
                "redirect_uri": "https://s3-us-west-2.amazonws.com/hm-registration/successsignin.html",
                "token": "access",
                "state": "REDIRECTION",
            },
            allow_redirects=False,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ZeppAuthError(f"Could not reach Zepp login service: {exc}") from exc

    if step1.status_code not in (200, 302):
        raise ZeppAuthError(
            f"Login failed ({step1.status_code}) — check your email/password, or this "
            "Zepp account may use a newer login flow this app does not support."
        )

    access_code, country_code = _extract_access_code(step1)
    if not access_code:
        raise ZeppAuthError(
            "Login failed — check your email/password, or this Zepp account may use a "
            "newer login flow this app does not support."
        )

    try:
        step2 = requests.post(
            TOKEN_URL,
            data={
                "app_name": "com.xiaomi.hm.health",
                "device_id": "02:00:00:00:00:00",
                "grant_type": "access_token",
                "code": access_code,
                "country_code": country_code or "US",
                "app_version": "4.0.9",
                "device_model": "android_phone",
                "allow_registration": "false",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ZeppAuthError(f"Could not reach Zepp token service: {exc}") from exc

    if step2.status_code != 200:
        raise ZeppAuthError(f"Login failed at token exchange ({step2.status_code}).")

    try:
        body = step2.json()
    except ValueError as exc:
        raise ZeppAuthError("Login failed — unexpected response from Zepp.") from exc

    token_info = body.get("token_info") or {}
    app_token = token_info.get("app_token")
    user_id = token_info.get("user_id")
    if not app_token or not user_id:
        raise ZeppAuthError("Login failed — unexpected response shape from Zepp.")

    return ZeppSession(app_token=app_token, user_id=user_id)


def _extract_access_code(step1_response: "requests.Response") -> tuple[str | None, str | None]:
    """The first auth call replies either with a JSON body containing `access` and
    `country_code`, or (in some flows) a 302 redirect whose Location query string
    carries the same fields. Handle both."""
    try:
        body = step1_response.json()
        if isinstance(body, dict) and body.get("access"):
            return body.get("access"), body.get("country_code")
    except ValueError:
        pass

    location = step1_response.headers.get("Location", "")
    if location:
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(location).query)
        access = qs.get("access", [None])[0]
        country_code = qs.get("country_code", [None])[0]
        if access:
            return access, country_code

    return None, None


def fetch_band_data(session: ZeppSession, start_date: str, end_date: str) -> list[dict]:
    """GET band_data.json for the given inclusive date range (YYYY-MM-DD strings).
    Returns the raw `data` list from the JSON response (one dict per day, each with
    a base64 `summary` field, untouched).

    Raises ZeppFetchError on network/HTTP/shape errors.
    """
    try:
        resp = requests.get(
            BAND_DATA_URL,
            headers={"apptoken": session.app_token},
            params={
                "query_type": "summary",
                "device_type": "android_phone",
                "userid": session.user_id,
                "from_date": start_date,
                "to_date": end_date,
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ZeppFetchError(f"Network error while fetching data: {exc}") from exc

    if resp.status_code != 200:
        raise ZeppFetchError(f"Failed to fetch data ({resp.status_code}): {resp.reason}")

    try:
        body = resp.json()
    except ValueError as exc:
        raise ZeppFetchError("Unexpected (non-JSON) response from Zepp.") from exc

    data = body.get("data")
    if data is None:
        raise ZeppFetchError("Unexpected response shape from Zepp (missing 'data').")

    return data


def _decode_summary(raw_entry: dict) -> dict | None:
    """Base64-decode + json.loads a single day's `summary` field. Returns None
    (rather than raising) on bad base64/JSON or a missing `summary` key, so one
    bad day doesn't kill an entire range."""
    summary_b64 = raw_entry.get("summary")
    if not summary_b64:
        return None
    try:
        decoded = base64.b64decode(summary_b64)
        return json.loads(decoded)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def parse_band_data(raw_entries: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Decode every entry and split into two canonical-column DataFrames:
    (activity_df, sleep_df), each with a `date` column plus whichever of
    steps/calories/distance (activity) or deep_sleep/light_sleep/total_sleep
    (sleep) were present that day.

    Entries that fail to decode are skipped, not raised.
    """
    activity_rows = []
    sleep_rows = []

    for entry in raw_entries:
        date_str = entry.get("date_time")
        if not date_str:
            continue
        summary = _decode_summary(entry)
        if summary is None:
            continue

        date = pd.to_datetime(date_str, format="%Y%m%d", errors="coerce")
        if pd.isna(date):
            continue

        stp = summary.get("stp") or {}
        if "ttl" in stp or "dis" in stp or "cal" in stp:
            row = {"date": date}
            if "ttl" in stp:
                row["steps"] = stp["ttl"]
            if "dis" in stp:
                row["distance"] = stp["dis"] / 1000
            if "cal" in stp:
                row["calories"] = stp["cal"]
            activity_rows.append(row)

        slp = summary.get("slp") or {}
        if "dp" in slp or "lt" in slp:
            deep = slp.get("dp")
            light = slp.get("lt")
            row = {"date": date}
            if deep is not None:
                row["deep_sleep"] = deep
            if light is not None:
                row["light_sleep"] = light
            if deep is not None and light is not None:
                row["total_sleep"] = deep + light
            sleep_rows.append(row)

    activity_df = pd.DataFrame(activity_rows)
    if not activity_df.empty:
        activity_df = activity_df.sort_values("date").reset_index(drop=True)

    sleep_df = pd.DataFrame(sleep_rows)
    if not sleep_df.empty:
        sleep_df = sleep_df.sort_values("date").reset_index(drop=True)

    return activity_df, sleep_df
