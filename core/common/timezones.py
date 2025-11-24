from datetime import date
import re
import dateparser
import pytz
from functools import lru_cache
from datetime import datetime, timedelta
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable
import time


def is_valid_date(date_str: str, date_format="%Y-%m-%d") -> bool:
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False


# Initialize once at module level to reuse across calls
_geolocator = Nominatim(user_agent="timezone_finder", timeout=5)
_tf = TimezoneFinder()


@lru_cache(maxsize=128)
def get_timezone_from_country_city(country: str, city: str) -> str | None:
    """
    Get timezone string from country and city names.
    Results are cached to avoid repeated API calls for the same location.

    Args:
        country: Country name
        city: City name

    Returns:
        Timezone string (e.g., 'America/New_York') or None if not found
    """
    location = _geocode_with_retry(f"{city}, {country}")

    if location:
        return _tf.timezone_at(lat=location.latitude, lng=location.longitude)

    return None


def _geocode_with_retry(query: str, attempts: int = 3, initial_delay: float = 0.5):
    """
    Geocode a location with exponential backoff retry logic.

    Args:
        query: Location query string
        attempts: Number of retry attempts
        initial_delay: Initial delay in seconds for exponential backoff

    Returns:
        Location object or None if geocoding fails
    """
    for attempt in range(attempts):
        try:
            return _geolocator.geocode(query, timeout=5)
        except (GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable):
            if attempt == attempts - 1:
                return None
            time.sleep(initial_delay * (2**attempt))
        except Exception:
            # Catch unexpected errors to prevent 500s
            return None

    return None


# Optional: Function to clear cache if needed
def clear_timezone_cache():
    """Clear the timezone lookup cache."""
    get_timezone_from_country_city.cache_clear()


def parse_reservation_date(user_input: str, restaurant_timezone: str) -> date:
    """
    Simplified version focusing on manual parsing of common patterns
    """
    user_input_clean = user_input.lower().strip()

    # Get current time in restaurant timezone
    tz = pytz.timezone(restaurant_timezone)
    current_time = datetime.now(tz)

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    # Handle simple cases
    if user_input_clean == "today":
        return current_time.date()
    elif user_input_clean == "tomorrow":
        return (current_time + timedelta(days=1)).date()

    # Handle "next [weekday]"
    next_match = re.match(r"next\s+(\w+)", user_input_clean)
    if next_match:
        weekday_name = next_match.group(1)
        if weekday_name in weekdays:
            target_weekday = weekdays[weekday_name]
            current_weekday = current_time.weekday()
            days_ahead = target_weekday - current_weekday

            # Always get next week's occurrence for "next [weekday]"
            if days_ahead <= 0:
                days_ahead += 7

            return (current_time + timedelta(days=days_ahead)).date()

    # Handle just weekday names
    if user_input_clean in weekdays:
        target_weekday = weekdays[user_input_clean]
        current_weekday = current_time.weekday()

        # Get next occurrence (if it's today, assume next week)
        if target_weekday <= current_weekday:
            days_ahead = 7 - (current_weekday - target_weekday)
        else:
            days_ahead = target_weekday - current_weekday

        return (current_time + timedelta(days=days_ahead)).date()

    # Fallback to dateparser
    try:
        parsed_dt = dateparser.parse(
            user_input, settings={"PREFER_DATES_FROM": "future"}
        )
        if parsed_dt and parsed_dt.date() >= current_time.date():
            return parsed_dt.date()
    except:
        pass

    raise ValueError(f"Could not parse date from: '{user_input}'")


def convert_utc_to_restaurant_timezone(
    utc_dt: datetime, restaurant_timezone: str
) -> datetime:
    """Convert stored UTC datetime to the restaurant's local time"""
    tz = pytz.timezone(restaurant_timezone)
    return utc_dt.astimezone(tz)
