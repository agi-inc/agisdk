import json, sys

# Strategy:
# - Load final_state_diff.json and inspect initialfinaldiff.added.booking.
# - Confirm a reservation exists (non-null booking.index and bookingDetails/time present).
# - Parse the reserved time and ensure it's between 7:00 AM and 10:00 AM inclusive.
# - Parse the restaurant rating and ensure it's >= 3.0.
# - Print SUCCESS only if all conditions hold; otherwise, print FAILURE.

def parse_time_to_minutes(t):
    if not t or not isinstance(t, str):
        return None
    s = t.strip().upper()
    # Expect formats like "7:30 AM" or "8:00 AM"
    parts = s.split()
    if len(parts) == 2:
        time_part, ampm = parts
    else:
        # Unexpected format
        return None
    if ':' in time_part:
        hh_str, mm_str = time_part.split(':', 1)
    else:
        hh_str, mm_str = time_part, '00'
    try:
        hh = int(hh_str)
        mm = int(mm_str)
    except ValueError:
        return None
    if ampm not in ('AM', 'PM'):
        return None
    if ampm == 'AM':
        if hh == 12:
            hh = 0
    else:  # PM
        if hh != 12:
            hh += 12
    return hh * 60 + mm


def get_first_booking_detail(booking_details):
    if isinstance(booking_details, dict) and booking_details:
        # keys like "0", "1"; sort to get deterministic first
        try:
            # try numeric sort of keys if possible
            keys = sorted(booking_details.keys(), key=lambda x: int(x) if str(x).isdigit() else str(x))
        except Exception:
            keys = list(booking_details.keys())
        return booking_details.get(keys[0])
    return None


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    root = data.get('initialfinaldiff', {})
    added = root.get('added', {}) or {}
    updated = root.get('updated', {}) or {}

    booking = added.get('booking') or updated.get('booking')
    if not isinstance(booking, dict):
        print("FAILURE")
        return

    index = booking.get('index')
    # Extract time: prefer top-level booking.time; fallback to first bookingDetails item
    time_str = booking.get('time')

    booking_details = booking.get('bookingDetails')
    first_detail = None
    if isinstance(booking_details, dict):
        first_detail = get_first_booking_detail(booking_details)
    if not time_str and isinstance(first_detail, dict):
        time_str = first_detail.get('time')

    # Extract rating from restaurant in first booking detail
    rating_val = None
    if isinstance(first_detail, dict):
        restaurant = first_detail.get('restaurant') or {}
        rating_raw = restaurant.get('rating')
        if rating_raw is not None:
            try:
                rating_val = float(rating_raw)
            except Exception:
                rating_val = None

    # Define conditions
    reservation_made = bool(index)  # non-null/non-empty

    # Parse and validate time window 7:00 AM to 10:00 AM inclusive
    minutes = parse_time_to_minutes(time_str)
    start = 7 * 60
    end = 10 * 60
    time_ok = minutes is not None and (start <= minutes <= end)

    rating_ok = (rating_val is not None) and (rating_val >= 3.0)

    if reservation_made and time_ok and rating_ok:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
