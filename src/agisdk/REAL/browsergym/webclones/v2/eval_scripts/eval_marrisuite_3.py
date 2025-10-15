import json, sys

def safe_get(d, keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur.get(k)
    return cur


def get_from_diff(diff_root, keys):
    # Try 'updated' first, then 'added'
    updated = diff_root.get('updated') or {}
    added = diff_root.get('added') or {}
    v = safe_get(updated, keys)
    if v is None:
        v = safe_get(added, keys)
    return v


def to_int(val):
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        try:
            return int(val)
        except Exception:
            return None
    if isinstance(val, str):
        s = val.strip()
        if s.isdigit():
            try:
                return int(s)
            except Exception:
                return None
    return None


def norm_date(val):
    if not isinstance(val, str):
        return None
    # Expect ISO, take date part before 'T' if present
    if 'T' in val:
        return val.split('T', 1)[0]
    return val


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diff = data.get('initialfinaldiff')
    if not isinstance(diff, dict):
        print("FAILURE")
        return

    # Destination must be London
    dest_candidates = []
    for keys in [
        ['search', 'destination'],
        ['search', 'lastSearchCriteria', 'destination']
    ]:
        v = get_from_diff(diff, keys)
        if isinstance(v, str):
            dest_candidates.append(v)
    destination_ok = any(('london' in s.lower()) for s in dest_candidates)

    # Dates must be 2024-10-01 to 2024-10-05
    date_pairs = []
    sd = get_from_diff(diff, ['search', 'dates', 'startDate'])
    ed = get_from_diff(diff, ['search', 'dates', 'endDate'])
    lsd = get_from_diff(diff, ['search', 'lastSearchCriteria', 'dates', 'startDate'])
    led = get_from_diff(diff, ['search', 'lastSearchCriteria', 'dates', 'endDate'])
    date_pairs.append((sd, ed))
    date_pairs.append((lsd, led))
    desired_start = '2024-10-01'
    desired_end = '2024-10-05'
    dates_ok = False
    for s, e in date_pairs:
        ns = norm_date(s)
        ne = norm_date(e)
        if ns == desired_start and ne == desired_end:
            dates_ok = True
            break

    # Guests: 1 adult
    guests = get_from_diff(diff, ['search', 'lastSearchCriteria', 'guests'])
    if not isinstance(guests, dict):
        guests = get_from_diff(diff, ['search', 'guests'])
    adults_ok = False
    children_ok = True
    if isinstance(guests, dict):
        a = to_int(guests.get('Adults'))
        c = guests.get('Children')
        ci = to_int(c) if c is not None else None
        adults_ok = (a == 1)
        if ci is not None:
            children_ok = (ci == 0)

    # Booking completion indicators
    booking_number = get_from_diff(diff, ['guest', 'bookingNumber'])
    selected_room = get_from_diff(diff, ['guest', 'selectedRoom'])
    is_valid = get_from_diff(diff, ['guest', 'isGuestFormValid'])
    policy = get_from_diff(diff, ['guest', 'policyAgreement'])
    card_month = get_from_diff(diff, ['guest', 'cardForm', 'month'])
    card_year = get_from_diff(diff, ['guest', 'cardForm', 'year'])
    card_cvv = get_from_diff(diff, ['guest', 'cardForm', 'cvv'])

    def nonempty(x):
        return x is not None and (str(x).strip() != '')

    booking_complete = (
        nonempty(booking_number)
        and isinstance(selected_room, dict)
        and bool(is_valid is True)
        and bool(policy is True)
        and nonempty(card_month)
        and nonempty(card_year)
        and nonempty(card_cvv)
    )

    if destination_ok and dates_ok and adults_ok and children_ok and booking_complete:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
