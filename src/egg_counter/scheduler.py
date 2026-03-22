"""Daylight scheduling using astral for sunrise/sunset calculation."""

import time
from datetime import datetime, timezone

from astral import LocationInfo
from astral.sun import sun


def _utcnow() -> datetime:
    """Return the current UTC time. Extracted for easy mocking in tests."""
    return datetime.now(tz=timezone.utc)


def is_daylight(lat: float, lon: float) -> bool:
    """Check whether the current time is between sunrise and sunset.

    Uses the *astral* library to compute sun times for the given
    coordinates and today's date.  For locations with large UTC offsets,
    astral may return a sunset time that is earlier than sunrise (because
    local sunset wraps past midnight UTC).  We handle this by also
    checking the previous day's sun window.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        True if the current UTC time falls between sunrise and sunset.
    """
    from datetime import timedelta

    location = LocationInfo(latitude=lat, longitude=lon)
    now = _utcnow()

    # Check today and yesterday (covers UTC day-boundary wrap)
    for offset in (0, -1):
        check_date = now.date() + timedelta(days=offset)
        s = sun(location.observer, date=check_date, tzinfo=timezone.utc)
        sunrise = s["sunrise"]
        sunset = s["sunset"]

        # If sunset < sunrise, astral wrapped it to the wrong side of
        # midnight UTC. Push sunset forward by one day.
        if sunset < sunrise:
            sunset = sunset + timedelta(days=1)

        if sunrise <= now <= sunset:
            return True

    return False


def wait_for_daylight(
    lat: float, lon: float, check_interval: int = 60
) -> None:
    """Block until daylight at the given coordinates.

    Prints a waiting message on the first check, then sleeps in a loop
    checking every *check_interval* seconds.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        check_interval: Seconds between daylight checks.
    """
    first = True
    while not is_daylight(lat, lon):
        if first:
            print("Waiting for daylight...")
            first = False
        time.sleep(check_interval)
