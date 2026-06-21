"""Manual smoke test — run locally with a real Zepp account to confirm login + fetch work.

Usage: python scripts/zepp_login_check.py <email> [days]

Prompts for the password via getpass so it's never on the command line or in shell
history. This is a one-off diagnostic script, not part of the app itself.
"""
import sys
from datetime import date, timedelta
from getpass import getpass

sys.path.insert(0, ".")
from zepp_api import login, fetch_band_data, parse_band_data, ZeppError


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/zepp_login_check.py <email> [days]")
        sys.exit(1)

    email = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    password = getpass("Zepp password: ")

    try:
        session = login(email, password)
        print(f"Login OK — user_id={session.user_id}")
    except ZeppError as exc:
        print(f"LOGIN FAILED: {exc}")
        sys.exit(1)

    end = date.today()
    start = end - timedelta(days=days)
    try:
        raw = fetch_band_data(session, start.isoformat(), end.isoformat())
        print(f"Fetched {len(raw)} day(s) of raw data")
    except ZeppError as exc:
        print(f"FETCH FAILED: {exc}")
        sys.exit(1)

    activity_df, sleep_df = parse_band_data(raw)
    print("\nActivity:\n", activity_df)
    print("\nSleep:\n", sleep_df)


if __name__ == "__main__":
    main()
