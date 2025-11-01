import json, sys

def normalize_time(t):
    if not isinstance(t, str):
        return None
    s = t.strip().upper().replace(" ", "")
    return s


def is_time_130(t):
    s = normalize_time(t)
    if not s:
        return False
    # Accept common variants
    if s in {"1:30PM", "01:30PM", "1:30P M", "01:30P M"}:
        return True
    # Also accept 24-hour format
    if s in {"13:30", "13:30PM", "13:30P M"}:
        return True
    # Additional leniency: some UIs might omit colon in AM/PM
    if s in {"1:30", "01:30"}:
        # If no AM/PM, we can't be sure; assume 1:30 (ambiguous). Reject to avoid false positives.
        return False
    return False


def is_july_18(date_str):
    if not isinstance(date_str, str):
        return False
    # Expect ISO-like string: YYYY-MM-DD...
    # We only verify month-day == 07-18
    # Be robust to different separators/timezones; check substring '-07-18'
    if "-07-18" in date_str:
        return True
    # Fallback: split by 'T' and inspect the date part
    try:
        date_part = date_str.split('T')[0]
        parts = date_part.split('-')
        if len(parts) >= 3:
            mm, dd = parts[1], parts[2]
            if mm == '07' and dd == '18':
                return True
    except Exception:
        pass
    return False


def extract_booking(obj):
    # Try to find booking under added or updated
    b = None
    try:
        b = obj.get('initialfinaldiff', {}).get('added', {}).get('booking')
        if b is None:
            b = obj.get('initialfinaldiff', {}).get('updated', {}).get('booking')
    except Exception:
        b = None
    return b if isinstance(b, dict) else None


def iter_booking_details(booking):
    details = booking.get('bookingDetails')
    if not details:
        return []
    # Could be dict with numeric keys as strings, or a list
    if isinstance(details, dict):
        return list(details.values())
    if isinstance(details, list):
        return list(details)
    return []


def main():
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    booking = extract_booking(data)
    if not booking:
        print("FAILURE")
        return

    # If loading is explicitly true, reservation not completed
    if isinstance(booking.get('loading'), bool) and booking.get('loading') is True:
        print("FAILURE")
        return

    # Prefer details-level fields for validation
    details_list = iter_booking_details(booking)

    # Also capture top-level fields as fallback
    top_date = booking.get('date')
    top_time = booking.get('time')

    success = False

    if details_list:
        for det in details_list:
            if not isinstance(det, dict):
                continue
            d_date = det.get('date', top_date)
            d_time = det.get('time', top_time)
            if is_july_18(d_date) and is_time_130(d_time):
                success = True
                break
    else:
        # No details present; fallback to top-level only if strongly indicative
        # Require both date July 18 and exact 1:30 time
        if is_july_18(top_date) and is_time_130(top_time):
            success = True

    print("SUCCESS" if success else "FAILURE")

if __name__ == "__main__":
    main()
