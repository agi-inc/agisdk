import sys, json

# Strategy:
# 1) Locate the 'booking' object from initialfinaldiff (search added then updated).
# 2) Validate that bookingDetails contains at least one entry whose:
#    - time is between 8:00 PM and 10:00 PM inclusive,
#    - guests indicate 6 people (prefer bookingDetails.guests, fallback to booking.guests),
#    - optionals.occasion is Business Meal (case-insensitive match).
# If any entry satisfies all conditions -> SUCCESS; else FAILURE.

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_nested(dct, path_list, default=None):
    cur = dct
    for key in path_list:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def time_to_minutes(t):
    # Expect formats like '8:00 PM', '8 PM', '10:00 PM', possibly with spaces
    if not isinstance(t, str):
        return None
    s = t.strip().upper()
    # Remove extraneous spaces
    s = " ".join(s.split())
    # Ensure it ends with AM/PM
    if not (s.endswith('AM') or s.endswith('PM')):
        return None
    # Split meridiem
    try:
        parts = s.split(' ')
        if len(parts) == 2:
            time_part, mer = parts
        else:
            # If something odd like '8:00PM'
            mer = 'AM' if s.endswith('AM') else 'PM'
            time_part = s[:-2]
    except Exception:
        return None
    time_part = time_part.strip()
    # Split hour and minute
    if ':' in time_part:
        hh_str, mm_str = time_part.split(':', 1)
    else:
        hh_str, mm_str = time_part, '00'
    try:
        hh = int(hh_str)
        mm = int(''.join(ch for ch in mm_str if ch.isdigit()) or '0')
    except Exception:
        return None
    if not (1 <= hh <= 12) or not (0 <= mm < 60):
        return None
    if mer == 'AM':
        minutes = (0 if hh == 12 else hh * 60) + mm
    else:
        minutes = (12 * 60 if hh == 12 else (hh + 12) * 60) + mm
    return minutes


def guests_is_six(val):
    # Accept formats like '6', '6 people', '06', etc.
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return int(val) == 6
    if isinstance(val, str):
        s = val.strip().lower()
        # Extract first number if present
        num = ''
        for ch in s:
            if ch.isdigit():
                num += ch
            elif num:
                break
        if num:
            try:
                return int(num) == 6
            except Exception:
                return False
        # If no number, compare whole string just in case
        return s == 'six' or s == '6 people'
    return False


def occasion_is_business(val):
    if not isinstance(val, str):
        return False
    return val.strip().lower() == 'business meal'


def main():
    try:
        path = sys.argv[1]
        data = load_json(path)
    except Exception:
        print('FAILURE')
        return

    booking = None
    # Try to find booking in added, then updated, then at root if present
    booking = get_nested(data, ['initialfinaldiff', 'added', 'booking'])
    if booking is None:
        booking = get_nested(data, ['initialfinaldiff', 'updated', 'booking'])
    if booking is None:
        # Sometimes entire state might be flattened differently
        booking = get_nested(data, ['booking'])

    if not isinstance(booking, dict):
        print('FAILURE')
        return

    booking_details = booking.get('bookingDetails')
    # bookingDetails expected to be a dict with numeric-like keys
    if not isinstance(booking_details, dict) or len(booking_details) == 0:
        print('FAILURE')
        return

    # Fallback guests from top-level booking
    top_guests = booking.get('guests')

    target_start = 20 * 60  # 8:00 PM in minutes
    target_end = 22 * 60    # 10:00 PM in minutes

    success = False
    for entry in booking_details.values():
        if not isinstance(entry, dict):
            continue
        time_str = entry.get('time')
        minutes = time_to_minutes(time_str)
        if minutes is None or not (target_start <= minutes <= target_end):
            continue
        guests_val = entry.get('guests', top_guests)
        if not guests_is_six(guests_val):
            continue
        occ = get_nested(entry, ['optionals', 'occasion'])
        if not occasion_is_business(occ):
            continue
        # All conditions satisfied
        success = True
        break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
