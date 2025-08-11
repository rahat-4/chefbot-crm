from datetime import date

import dateparser
import pytz
from datetime import datetime
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim


def is_valid_date(date_str: str, date_format="%Y-%m-%d") -> bool:
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False


def get_timezone_from_country_city(country: str, city: str) -> str:

    geolocator = Nominatim(user_agent="timezone_finder")
    location = geolocator.geocode(f"{city}, {country}")

    if location:
        tf = TimezoneFinder()
        tz = tf.timezone_at(lat=location.latitude, lng=location.longitude)
        return tz
    return None


def parse_reservation_date(user_input: str, restaurant_timezone: str) -> date:
    """
    Parse a natural language date like 'tomorrow', 'next Friday', 'today'
    based on the restaurant's timezone and return only the date portion.
    """
    local_dt = dateparser.parse(
        user_input,
        settings={
            "TIMEZONE": restaurant_timezone,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
        },
    )

    if not local_dt:
        raise ValueError(f"Could not parse date from: {user_input}")

    # Return only the date portion (no time)
    return local_dt.date()


def convert_utc_to_restaurant_timezone(
    utc_dt: datetime, restaurant_timezone: str
) -> datetime:
    """Convert stored UTC datetime to the restaurant's local time"""
    tz = pytz.timezone(restaurant_timezone)
    return utc_dt.astimezone(tz)
