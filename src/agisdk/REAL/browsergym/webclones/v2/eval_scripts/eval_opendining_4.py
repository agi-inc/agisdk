import json, sys

# Strategy:
# - Load final_state_diff.json, locate the 'booking' object (with a recursive fallback).
# - Success if: booking.index exists (not null/empty), loading is False, time is 12 PM (normalized),
#   and bookingDetails contains restaurant.name == 'Sushi Zen' (case-insensitive).
# - Avoid relying on bookingCompleted or guest count; ensure wrong restaurant/time or missing reservation fails.

def get_booking(obj):
    # Try common path first
    booking = None
    if isinstance(obj, dict):
        booking = (
            obj.get('initialfinaldiff', {})
               .get('added', {})
               .get('booking')
        )
        if booking is not None:
            return booking
    # Fallback: recursive search for a dict under key 'booking'
    def rec_search(o):
        if isinstance(o, dict):
            if 'index' in o and 'time' in o and 'errors' in o and 'form' in o:
                # Likely the booking object shape
                return o
            for k, v in o.items():
                found = rec_search(v)
                if found is not None:
                    return found
        elif isinstance(o, list):
            for it in o:
                found = rec_search(it)
                if found is not None:
                    return found
        return None
    return rec_search(obj)


def normalize_time(s):
    if not isinstance(s, str):
        return ''
    t = s.strip().lower().replace('.', '')
    t = t.replace(' ', '')
    return t


def is_noon_12pm(time_str):
    t = normalize_time(time_str)
    return t in {'12pm', '12:00pm'}


def get_restaurant_name(booking):
    bd = booking.get('bookingDetails')
    if bd is None:
        return None
    entry = None
    if isinstance(bd, dict):
        # take first value
        for _, v in bd.items():
            entry = v
            break
    elif isinstance(bd, list) and bd:
        entry = bd[0]
    if not isinstance(entry, dict):
        return None
    rest = entry.get('restaurant') if isinstance(entry.get('restaurant'), dict) else None
    name = rest.get('name') if rest else None
    if isinstance(name, str):
        return name.strip()
    return None


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    booking = get_booking(data)
    if not isinstance(booking, dict):
        print('FAILURE')
        return

    index = booking.get('index')
    loading = booking.get('loading')
    time_str = booking.get('time')
    rest_name = get_restaurant_name(booking)

    # Validate conditions
    has_index = isinstance(index, str) and index.strip() != ''
    correct_time = is_noon_12pm(time_str)
    correct_restaurant = isinstance(rest_name, str) and rest_name.lower().strip() == 'sushi zen'
    loading_done = (loading is False)

    if has_index and loading_done and correct_time and correct_restaurant:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
