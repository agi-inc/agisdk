import json, sys, re

def parse_time_12h(t):
    """Parse a 12-hour time string like '7:30 PM' or '8 PM' to minutes since midnight.
    Returns integer minutes or None if unparsable.
    """
    if not t or not isinstance(t, str):
        return None
    t = t.strip()
    # Normalize possible formats like '7:30PM' (missing space)
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*([AaPp][Mm])$", t)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) is not None else 0
    ampm = m.group(3).lower()
    if hour == 12:
        hour = 0
    if ampm == 'pm':
        hour += 12
    return hour * 60 + minute


def get_nested(d, keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def extract_booking_objects(state):
    objs = []
    root = state if isinstance(state, dict) else {}
    for section in ('added', 'updated'):
        b = get_nested(root, ['initialfinaldiff', section, 'booking'])
        if isinstance(b, dict):
            objs.append(b)
    # Also consider if booking is directly under root (fallback)
    b2 = get_nested(root, ['booking'])
    if isinstance(b2, dict):
        objs.append(b2)
    return objs


def normalize_iterable(value):
    # bookingDetails may be dict with numeric keys or a list
    if value is None:
        return []
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, list):
        return value
    return []


def is_two_guests(guest_str):
    if not isinstance(guest_str, str):
        return False
    # extract first integer from string
    m = re.search(r"(\d+)", guest_str)
    if not m:
        return False
    try:
        return int(m.group(1)) == 2
    except:
        return False


def matches_criteria(entry, top_level_booking):
    # Cuisine American
    food_type = get_nested(entry, ['restaurant', 'food_type'])
    if not isinstance(food_type, str) or 'american' not in food_type.lower():
        return False

    # Guests = 2
    guests = entry.get('guests')
    if guests is None:
        guests = get_nested(top_level_booking, ['guests'])
    if not is_two_guests(guests):
        return False

    # Occasion = Birthday
    occasion = get_nested(entry, ['optionals', 'occasion'])
    if not isinstance(occasion, str) or occasion.strip().lower() != 'birthday':
        return False

    # Time between 7:00 PM and 8:00 PM inclusive
    time_str = entry.get('time')
    if not time_str:
        time_str = get_nested(top_level_booking, ['time'])
    minutes = parse_time_12h(time_str)
    if minutes is None:
        return False
    start = 19 * 60  # 7:00 PM
    end = 20 * 60    # 8:00 PM
    if not (start <= minutes <= end):
        return False

    return True


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    booking_objs = extract_booking_objects(data)
    # Must have bookingDetails to count as reserved
    for b in booking_objs:
        booking_details = b.get('bookingDetails')
        for entry in normalize_iterable(booking_details):
            if isinstance(entry, dict) and matches_criteria(entry, b):
                print('SUCCESS')
                return
    # If no matching entry found
    print('FAILURE')

if __name__ == '__main__':
    # Strategy in code comments: We require bookingDetails presence and validate cuisine, guests, occasion, and time window (7-8 PM inclusive).
    # We parse 12-hour times robustly and iterate all bookingDetails entries to find any that match.
    main()
