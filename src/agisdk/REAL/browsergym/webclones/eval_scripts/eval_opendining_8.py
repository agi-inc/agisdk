import sys, json

# Strategy:
# - Load final_state_diff.json and navigate to initialfinaldiff.added.booking.bookingDetails
# - Verify at least one booking detail meets ALL criteria:
#   * Restaurant food_type is American (case-insensitive)
#   * Guests indicate 2 people (check both detail and top-level booking)
#   * Occasion is Birthday (case-insensitive) in optionals
#   * Time is between 7:00 PM and 8:00 PM inclusive (robust parsing of AM/PM)
# - Fall back to top-level booking fields when detail fields are missing. Print SUCCESS/FAILURE only.

def parse_time_to_minutes(t):
    if not t or not isinstance(t, str):
        return None
    s = t.strip()
    if not s:
        return None
    parts = s.split()
    if len(parts) == 1:
        # maybe format like 19:30 in 24h; handle as 24h
        time_part = parts[0]
        mer = None
    else:
        time_part = parts[0]
        mer = parts[1].upper()
    # split time part
    if ':' in time_part:
        hh_str, mm_str = time_part.split(':', 1)
        if not hh_str.isdigit():
            return None
        try:
            hh = int(hh_str)
            mm = int(''.join([c for c in mm_str if c.isdigit()]) or '0')
        except:
            return None
    else:
        if not time_part.isdigit():
            return None
        hh = int(time_part)
        mm = 0
    if mer is None:
        # assume 24h clock
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return None
        return hh * 60 + mm
    if mer not in ("AM", "PM"):
        return None
    if hh < 1 or hh > 12 or mm < 0 or mm > 59:
        return None
    if mer == 'AM':
        if hh == 12:
            hh = 0
    else:  # PM
        if hh != 12:
            hh += 12
    return hh * 60 + mm


def normalize_str(x):
    return (x or '').strip().lower()


def is_two_people(val):
    if val is None:
        return False
    s = normalize_str(str(val))
    # accept common variants
    if '2' in s:
        return True
    if 'two' in s:
        return True
    if s == 'couple':
        return True
    return False


def check_booking(booking):
    if not isinstance(booking, dict):
        return False
    details = booking.get('bookingDetails')
    # capture top-level fallbacks
    top_time = booking.get('time')
    top_guests = booking.get('guests')
    # iterate over all details if present
    candidates = []
    if isinstance(details, dict) and details:
        for k, v in details.items():
            if not isinstance(v, dict):
                continue
            candidates.append(v)
    else:
        # No details; try constructing a single candidate from top-level fields
        # This is a fallback and still enforces checks on available info
        candidates.append({
            'restaurant': booking.get('restaurant') or {},
            'time': top_time,
            'guests': top_guests,
            'optionals': booking.get('optionals') or {}
        })

    for entry in candidates:
        rest = entry.get('restaurant') or {}
        food_type = rest.get('food_type')
        if normalize_str(food_type) != 'american':
            continue
        # Guests
        guests_val = entry.get('guests')
        if not is_two_people(guests_val):
            # try top-level fallback
            if not is_two_people(top_guests):
                continue
        # Occasion
        optionals = entry.get('optionals') or {}
        occ = normalize_str(optionals.get('occasion'))
        if occ != 'birthday':
            continue
        # Time window check: 7:00 PM to 8:00 PM inclusive
        t_str = entry.get('time') or top_time
        minutes = parse_time_to_minutes(t_str)
        if minutes is None:
            continue
        if 19*60 <= minutes <= 20*60:
            return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return
    root = data.get('initialfinaldiff', {})
    added = root.get('added', {})
    booking = added.get('booking')
    if check_booking(booking):
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
