import sys, json

# Revised strategy addition:
# On top of date/time/guest checks, require that booking.index is null/absent to reflect "looking for times" rather than finalizing a (possibly wrong) selection.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_nested(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def normalize_booking_details(bd):
    if isinstance(bd, list):
        return bd
    if isinstance(bd, dict):
        return list(bd.values())
    return []


def parse_date_str(s):
    if not s or not isinstance(s, str):
        return (None, None, None)
    s = s.strip()
    try:
        if 'T' in s:
            date_part = s.split('T', 1)[0]
        else:
            date_part = s
        parts = date_part.split('-')
        if len(parts) >= 3:
            y = int(parts[0]); m = int(parts[1]); d = int(parts[2])
            return (y, m, d)
    except Exception:
        pass
    try:
        import re
        m = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s*(\d{4})?', s, re.IGNORECASE)
        if m:
            month_name = m.group(1).lower(); day = int(m.group(2)); year = int(m.group(3)) if m.group(3) else None
            month_map = {'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,'july':7,'august':8,'september':9,'october':10,'november':11,'december':12}
            return (year, month_map.get(month_name), day)
    except Exception:
        pass
    return (None, None, None)


def parse_time_to_minutes(s):
    if not s or not isinstance(s, str):
        return None
    t = s.strip().upper().replace('.', '')
    if t.endswith('AM') and ' AM' not in t:
        t = t[:-2] + ' AM'
    if t.endswith('PM') and ' PM' not in t:
        t = t[:-2] + ' PM'
    try:
        if 'AM' in t or 'PM' in t:
            ampm = 'AM' if 'AM' in t else 'PM'
            clock = t.replace('AM','').replace('PM','').strip()
            if ':' in clock:
                hh, mm = clock.split(':', 1)
                mm = ''.join(ch for ch in mm if ch.isdigit())
            else:
                hh, mm = clock, '0'
            hh = int(''.join(ch for ch in hh if ch.isdigit())) if hh else 0
            mm = int(mm) if mm else 0
            if hh == 12:
                base = 0 if ampm == 'AM' else 12*60
            else:
                base = hh*60 + (12*60 if ampm == 'PM' else 0)
            return base + mm
        else:
            if ':' in t:
                hh, mm = t.split(':', 1)
                hh = int(''.join(ch for ch in hh if ch.isdigit()))
                mm = int(''.join(ch for ch in mm if ch.isdigit()))
                return hh*60 + mm
            if t.isdigit():
                hh = int(t)
                return hh*60
    except Exception:
        return None
    return None


def is_july_18(date_str):
    _, m, d = parse_date_str(date_str)
    return (m == 7 and d == 18)


def is_around_7ish(time_str):
    mins = parse_time_to_minutes(time_str)
    if mins is None:
        return False
    return 18*60 + 30 <= mins <= 19*60 + 45


def is_two_guests(guests):
    if guests is None:
        return False
    if isinstance(guests, (int, float)):
        return int(guests) == 2
    if isinstance(guests, str):
        g = guests.strip().lower()
        if '2' in g and ('people' in g or 'person' in g or 'for' in g or 'party' in g or g == '2'):
            return True
        if g in ('2 people', '2', '2 persons'):
            return True
    return False


def get_best_date(detail, booking_root):
    d = detail.get('date') if isinstance(detail, dict) else None
    if not d:
        d = get_nested(booking_root, ['date'])
    return d


def get_best_time(detail, booking_root):
    t = detail.get('time') if isinstance(detail, dict) else None
    if not t:
        t = get_nested(booking_root, ['time'])
    return t


def get_best_guests(detail, booking_root):
    g = detail.get('guests') if isinstance(detail, dict) else None
    if not g:
        g = get_nested(booking_root, ['guests'])
    return g


def verify(data):
    root = get_nested(data, ['initialfinaldiff', 'added', 'booking']) or {}
    # Additional constraint: for this "look for times" task, we consider success only if no specific selection index is set
    idx = root.get('index', None)
    if idx not in (None, ''):
        index_set = True
    else:
        index_set = False

    details_raw = get_nested(root, ['bookingDetails'])
    details = normalize_booking_details(details_raw) or [{}]

    found = False
    for det in details:
        date_str = get_best_date(det, root)
        time_str = get_best_time(det, root)
        guests_val = get_best_guests(det, root)
        if not date_str or not time_str or guests_val is None:
            continue
        if not is_july_18(date_str):
            continue
        if not is_around_7ish(time_str):
            continue
        if not is_two_guests(guests_val):
            continue
        found = True
        break

    if not found:
        return False

    # Enforce the index constraint: must not be set
    if index_set:
        return False

    return True


def main():
    try:
        path = sys.argv[1]
        data = load_json(path)
        ok = verify(data)
        print('SUCCESS' if ok else 'FAILURE')
    except Exception:
        print('FAILURE')

if __name__ == '__main__':
    main()
