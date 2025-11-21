import json
import sys
from datetime import datetime


def load_json(path):
    with open(path) as f:
        return json.load(f)


def get_from_sections(root, key):
    """Extract data from various sections of the state diff."""
    initial = root.get("initialfinaldiff", {})
    for section in ("added", "updated"):
        sec = initial.get(section)
        if isinstance(sec, dict) and key in sec:
            return sec.get(key)
    if key in root:
        return root.get(key)
    diffs = root.get("differences", {})
    if isinstance(diffs, dict) and key in diffs:
        return diffs.get(key)
    return None


def parse_time(time_str):
    """Parse time string like '7:30 AM' to hour (24-hour format)."""
    if not isinstance(time_str, str):
        return None
    try:
        # Parse time like "7:30 AM"
        time_obj = datetime.strptime(time_str.strip(), "%I:%M %p")
        return time_obj.hour
    except:
        return None


def check_booking_criteria(booking):
    """Check if booking matches breakfast time (7am-10am) and at least 3 stars."""
    if not isinstance(booking, dict):
        return False

    booking_details = booking.get("bookingDetails", {})
    if not isinstance(booking_details, dict) or len(booking_details) == 0:
        return False

    # Check the first booking
    for _key, details in booking_details.items():
        if not isinstance(details, dict):
            continue

        # Check time is between 7am and 10am
        time_str = details.get("time")
        hour = parse_time(time_str)

        if hour is None or hour < 7 or hour >= 10:
            return False

        # Check restaurant rating is at least 3 stars
        restaurant = details.get("restaurant", {})
        if not isinstance(restaurant, dict):
            return False

        rating_str = restaurant.get("rating")
        try:
            rating = float(rating_str)
            if rating < 3.0:
                return False
        except (ValueError, TypeError):
            return False

        # All checks passed
        return True

    return False


def main():
    try:
        path = sys.argv[1]
    except IndexError:
        print("FAILURE")
        return

    try:
        data = load_json(path)
    except Exception:
        print("FAILURE")
        return

    # Extract booking data
    booking = get_from_sections(data, "booking")

    if not booking:
        print("FAILURE")
        return

    # Check if booking criteria matches
    if check_booking_criteria(booking):
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
