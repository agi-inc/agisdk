import json, sys

def get_path(d, path):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def get_merged_path(diff, path):
    # Try updated first (most authoritative), then added
    updated = (diff or {}).get('updated') or {}
    added = (diff or {}).get('added') or {}
    val = get_path(updated, path)
    if val is None:
        val = get_path(added, path)
    return val


def normalize_date_str(s):
    if not isinstance(s, str):
        return None
    # Extract YYYY-MM-DD part if possible
    if 'T' in s:
        return s.split('T', 1)[0]
    return s


def contains_all(text, subs):
    if not isinstance(text, str):
        return False
    t = text.lower()
    return all(sub.lower() in t for sub in subs)


def parse_float(x):
    try:
        return float(x)
    except Exception:
        return None


def main():
    # Analysis strategy:
    # SUCCESS requires: (1) a completed booking (guest.bookingNumber present), (2) destination in Miami, Florida,
    # (3) dates Sept 17-20, 2024 (check date parts), and (4) selectedRoom nightly price <= 400.
    # We read fields from initialfinaldiff.updated/added safely and handle missing or null structures robustly.

    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diff = data.get('initialfinaldiff') or {}

    # 1) Booking completed
    booking_number = get_merged_path(diff, ['guest', 'bookingNumber'])
    has_booking = isinstance(booking_number, str) and len(booking_number.strip()) > 0

    # 2) Destination check (prefer search.destination, fallback to lastSearchCriteria.destination)
    dest_candidates = []
    dest_candidates.append(get_merged_path(diff, ['search', 'destination']))
    dest_candidates.append(get_merged_path(diff, ['search', 'lastSearchCriteria', 'destination']))
    dest_ok = any(contains_all(d or '', ['miami', 'florida']) for d in dest_candidates if isinstance(d, str))

    # 3) Date check (either search.dates or lastSearchCriteria.dates match)
    start_candidates = []
    end_candidates = []
    for base in (['search', 'dates'], ['search', 'lastSearchCriteria', 'dates']):
        start_candidates.append(get_merged_path(diff, base + ['startDate']))
        end_candidates.append(get_merged_path(diff, base + ['endDate']))

    target_start = '2024-09-17'
    target_end = '2024-09-20'

    def pair_ok(s, e):
        s_norm = normalize_date_str(s)
        e_norm = normalize_date_str(e)
        return (s_norm == target_start) and (e_norm == target_end)

    dates_ok = False
    for s, e in zip(start_candidates, end_candidates):
        if pair_ok(s, e):
            dates_ok = True
            break

    # 4) Nightly price check <= 400
    price_val = get_merged_path(diff, ['guest', 'selectedRoom', 'price'])
    price = parse_float(price_val)
    price_ok = (price is not None) and (price <= 400)

    success = has_booking and dest_ok and dates_ok and price_ok

    print("SUCCESS" if success else "FAILURE")

if __name__ == '__main__':
    main()
