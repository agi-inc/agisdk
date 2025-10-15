import json, sys

# Strategy in code comments:
# 1) Load final_state_diff.json and locate the booking object from either added or updated.
# 2) Ensure a reservation was actually selected: booking.index must be non-null/Truthy.
# 3) Confirm the reservation matches July 18 and exactly 1:30 PM by checking both top-level booking fields
#    and any entry in booking.bookingDetails. Accept common format variants (e.g., 01:30 PM, 13:30) and
#    flexible date representations containing July 18 (e.g., ISO dates with timezone or text month formats).
# 4) Print SUCCESS only if both date and time match together in the same context; otherwise print FAILURE.

def is_130_pm(t):
    if not isinstance(t, str):
        return False
    s = t.strip().lower()
    # remove extra spaces
    s_no_space = s.replace(' ', '')
    candidates = {
        '1:30pm', '01:30pm', '1:30p.m.', '01:30p.m.', '1:30', '01:30'
    }
    # We prefer explicit PM or 24h 13:30; avoid bare '1:30' unless paired with explicit PM/24h.
    # But to be robust, treat bare '1:30' as 1:30 PM only if there's an explicit pm indicator somewhere.
    # Hence, we check explicit patterns:
    explicit = {'1:30pm', '01:30pm', '1:30p.m.', '01:30p.m.'}
    if s_no_space in explicit:
        return True
    # 24-hour format acceptance
    if s_no_space.startswith('13:30'):
        # allow '13:30', '13:30pm', '13:30:00', etc.
        return True
    # Some UIs might omit colon spacing like '1:30 PM' vs '1:30PM'
    if s_no_space == '1:30pm' or s_no_space == '01:30pm':
        return True
    return False


def is_july_18(d):
    if not isinstance(d, str):
        return False
    s = d.strip().lower()
    # ISO-like: YYYY-07-18
    if '-07-18' in s:
        return True
    # US format: 07/18 or 7/18
    if '07/18' in s or '7/18' in s:
        return True
    # Text month: July 18
    if 'july 18' in s:
        return True
    # Sometimes date may be just YYYY-07-18T...
    if '07-18' in s:
        return True
    return False


def get_booking(obj):
    if not isinstance(obj, dict):
        return None
    init = obj.get('initialfinaldiff') or obj.get('initial_final_diff') or obj.get('final_state_diff') or obj
    if not isinstance(init, dict):
        return None
    added = init.get('added') or {}
    updated = init.get('updated') or {}
    booking = None
    if isinstance(added, dict):
        booking = added.get('booking')
    if booking is None and isinstance(updated, dict):
        booking = updated.get('booking')
    return booking


def any_detail_matches(booking):
    details = booking.get('bookingDetails') if isinstance(booking, dict) else None
    if not isinstance(details, dict):
        return False
    for _k, v in details.items():
        if not isinstance(v, dict):
            continue
        d = v.get('date')
        t = v.get('time')
        if is_july_18(d) and is_130_pm(t):
            return True
    return False


def top_level_matches(booking):
    d = booking.get('date') if isinstance(booking, dict) else None
    t = booking.get('time') if isinstance(booking, dict) else None
    return is_july_18(d) and is_130_pm(t)


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    booking = get_booking(data)
    if not isinstance(booking, dict):
        print('FAILURE')
        return

    index_ok = booking.get('index') is not None and booking.get('index') != ''
    # Ensure a reservation target exists; if no index, consider it not made
    if not index_ok:
        print('FAILURE')
        return

    match = top_level_matches(booking) or any_detail_matches(booking)

    if match:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
