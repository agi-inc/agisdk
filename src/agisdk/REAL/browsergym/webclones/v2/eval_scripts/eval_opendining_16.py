import json, sys

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Recursive search to find the 'booking' object anywhere in the JSON

def find_booking(obj):
    if isinstance(obj, dict):
        if 'booking' in obj and isinstance(obj['booking'], dict):
            return obj['booking']
        for v in obj.values():
            res = find_booking(v)
            if res is not None:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_booking(item)
            if res is not None:
                return res
    return None

# Normalize time like "12:30 PM" -> "12:30pm" for robust comparison

def norm_time(t):
    if t is None:
        return None
    s = str(t).strip().lower().replace(' ', '')
    # also normalize periods in am/pm if any
    s = s.replace('.', '')
    return s


def is_italian(food_type):
    if not food_type:
        return False
    return 'italian' in str(food_type).strip().lower()


def extract_booking_details(booking):
    details = booking.get('bookingDetails')
    if not isinstance(details, dict):
        return []
    # bookingDetails is keyed by strings like "0", "1", etc.
    entries = []
    for k, v in details.items():
        if isinstance(v, dict):
            entries.append(v)
    return entries


def main():
    path = sys.argv[1]
    data = load_json(path)

    booking = None
    # Try common path first for efficiency
    try:
        booking = data['initialfinaldiff']['added']['booking']
        if not isinstance(booking, dict):
            booking = None
    except Exception:
        booking = None

    if booking is None:
        booking = find_booking(data)

    if not isinstance(booking, dict):
        print('FAILURE')
        return

    # Basic sanity: a concrete booking exists (index truthy) and not currently loading
    index = booking.get('index')
    loading = booking.get('loading')
    if not index or index in ("", None):
        print('FAILURE')
        return
    if loading is True:
        print('FAILURE')
        return

    # Time must be 12:30 PM either at root or in details
    target_time = '12:30pm'
    times = []
    times.append(norm_time(booking.get('time')))

    details_entries = extract_booking_details(booking)
    for ent in details_entries:
        times.append(norm_time(ent.get('time')))

    has_time = any(t == target_time for t in times if t is not None)

    # Restaurant must be Italian based on food_type in any detail entry
    is_italian_any = False
    for ent in details_entries:
        rest = ent.get('restaurant') if isinstance(ent, dict) else None
        if isinstance(rest, dict):
            if is_italian(rest.get('food_type')):
                is_italian_any = True
                break

    # If there are no details, we cannot verify cuisine; treat as failure
    if not details_entries:
        print('FAILURE')
        return

    if has_time and is_italian_any:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
