import json, sys

def normalize_time(t: str):
    if not isinstance(t, str):
        return None
    s = t.strip().lower()
    # Normalize variations like '9 pm', '9:00 pm', '09:00 PM'
    s = s.replace('.','')
    # remove leading zeros in hour
    if s.startswith('09'):
        s = '9' + s[2:]
    return s


def is_nine_pm(t: str) -> bool:
    """Check if time is in the 9 PM hour (9:00 PM - 9:59 PM)"""
    s = normalize_time(t)
    if not s:
        return False
    
    # Accept any time starting with "9" or "09" and ending with "pm"
    if s.endswith('pm'):
        # Extract the hour part
        if s.startswith('9:') or s.startswith('9 ') or s == '9 pm':
            return True
        if s.startswith('09:') or s.startswith('09 '):
            return True
    
    return False

def parse_rating(val):
    try:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            return float(val.strip())
    except Exception:
        return None
    return None


def get_first_booking_detail(booking):
    bd = booking.get('bookingDetails')
    if not bd:
        return None
    # bookingDetails might be a dict keyed by string indices or a list
    if isinstance(bd, dict):
        # Sort keys numerically if possible to get the first one
        try:
            items = sorted(bd.items(), key=lambda kv: int(kv[0]))
        except Exception:
            items = list(bd.items())
        for _, v in items:
            return v
    elif isinstance(bd, list):
        return bd[0] if bd else None
    return None


def main():
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    booking = (
        data.get('initialfinaldiff', {})
            .get('added', {})
            .get('booking', {})
    )

    # Must have concrete booking details (proof of reservation) with a restaurant
    bd = get_first_booking_detail(booking)
    if not bd or not isinstance(bd, dict):
        print('FAILURE')
        return

    # Verify time is 9 PM, prefer bookingDetails time then fallback to top-level
    time_val = bd.get('time') if bd.get('time') else booking.get('time')
    if not is_nine_pm(time_val):
        print('FAILURE')
        return

    # Verify restaurant is top-rated: rating >= 3.5
    restaurant = bd.get('restaurant') if isinstance(bd.get('restaurant'), dict) else None
    rating = parse_rating(restaurant.get('rating') if restaurant else None)
    if rating is None or rating < 3.5:
        print('FAILURE')
        return

    print('SUCCESS')

if __name__ == '__main__':
    main()