import json, sys, re

# Strategy:
# - Load final_state_diff.json and inspect booking.bookingDetails entries.
# - SUCCESS if any booking detail has restaurant rating >= 3.5 AND time around 9 PM (accept 9:00 PM, 9 PM, 9:30 PM). Otherwise FAILURE.


def is_time_around_9pm(t):
    if not t or not isinstance(t, str):
        return False
    s = t.strip().upper()
    # Accept exact common variants
    allowed = {"9 PM", "9:00 PM", "09:00 PM", "9:30 PM", "09:30 PM"}
    if s in allowed:
        return True
    # Try to parse patterns like H:MM AM/PM or H AM/PM
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$", s)
    if not m:
        return False
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) is not None else 0
    ampm = m.group(3)
    if ampm != 'PM':
        return False
    if hour == 9 and minute in (0, 30):
        return True
    return False


def parse_rating(val):
    # rating might be a string like "4.33"; safely parse to float
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # Remove any non-numeric trailing characters just in case
            cleaned = re.match(r"^[\d.]+", val)
            if cleaned:
                return float(cleaned.group(0))
    except Exception:
        pass
    return None


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Navigate to bookingDetails robustly
    booking = None
    try:
        booking = data.get('initialfinaldiff', {}).get('added', {}).get('booking', {})
    except Exception:
        booking = None

    if not booking or not isinstance(booking, dict):
        print("FAILURE")
        return

    details = booking.get('bookingDetails')
    if not details or not isinstance(details, dict) or len(details) == 0:
        # No booking created
        print("FAILURE")
        return

    success = False
    for item in details.values():
        if not isinstance(item, dict):
            continue
        time_str = item.get('time')
        rest = item.get('restaurant', {}) if isinstance(item.get('restaurant', {}), dict) else {}
        rating_val = parse_rating(rest.get('rating'))
        # Conditions: rating >= 3.5 and time ~ 9 PM
        if rating_val is not None and rating_val >= 3.5 and is_time_around_9pm(time_str):
            success = True
            break

    print("SUCCESS" if success else "FAILURE")

if __name__ == '__main__':
    main()
