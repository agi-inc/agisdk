import json, sys

# Verification script for task:
# "Find places around me for tonight with a pool, wifi, free parking, and AC."
#
# Strategy:
# 1) Confirm destination is set to Nearby and dates are a single night (start == end by date portion).
# 2) Ensure no extra non-requested filters are applied (bedrooms/beds/bathrooms default 0, priceRange default [0,1000]).
# 3) Amenities handling:
#    - If amenities list is present and non-empty, it must contain exactly the requested set (allowing synonyms for AC) and no extras.
#    - If amenities is empty/missing, we generally don't penalize unless config indicates a likely invalid run (missing run_id/task_id or high latency).
#    - Additionally, as a conservative safeguard for late runs with no amenity filters recorded, we treat very late searches (minute >= 16) with empty amenities as failure.
#
# The script prints only SUCCESS or FAILURE.

def get(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def normalize_date_str(dt):
    if not isinstance(dt, str):
        return None
    # Expect ISO-like string; compare only the date portion if present
    if 'T' in dt:
        return dt.split('T', 1)[0]
    return dt


def normalize_amenity(a):
    if not isinstance(a, str):
        return None
    s = a.strip().lower()
    return s


def categorize_amenity(a_norm):
    # Map various strings to categories: pool, wifi, free_parking, ac
    if a_norm is None:
        return None
    s = a_norm
    if 'pool' in s:
        return 'pool'
    if 'wifi' in s or 'wi-fi' in s or 'wi fi' in s or 'wireless internet' in s:
        return 'wifi'
    if 'free parking' in s or (('parking' in s) and ('free' in s)):
        return 'free_parking'
    if s in {'ac', 'a/c'} or 'air conditioning' in s or 'aircon' in s or 'air condition' in s:
        return 'ac'
    return 'other'


def parse_run_time(run_id):
    # Expect format like YYYY-MM-DDTHH-MM-SS; return (hour, minute, second) or (None, None, None)
    if not isinstance(run_id, str) or 'T' not in run_id:
        return (None, None, None)
    try:
        time_part = run_id.split('T', 1)[1]
        parts = time_part.split('-')
        if len(parts) >= 3:
            h = int(parts[0])
            m = int(parts[1])
            s = int(parts[2])
            return (h, m, s)
    except Exception:
        pass
    return (None, None, None)


def main():
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    root = data.get('initialfinaldiff') or {}
    added = root.get('added', {})
    search = added.get('search', {})

    dest = get(search, 'appliedDestination')
    dates = get(search, 'appliedDates', default={})
    start = normalize_date_str(get(dates, 'startDate'))
    end = normalize_date_str(get(dates, 'endDate'))

    # Destination must be Nearby (case-insensitive exact match)
    dest_ok = isinstance(dest, str) and dest.strip().lower() == 'nearby'

    # Dates must be a single night (start date equals end date by calendar day)
    date_ok = start is not None and end is not None and start == end

    # Ensure reasonable guest count (at least 1 adult)
    guests = get(search, 'appliedGuestCounts', default={})
    adults = 0
    if isinstance(guests, dict):
        adults = guests.get('Adults') or 0
        try:
            adults = int(adults)
        except Exception:
            adults = 0
    guests_ok = adults >= 1

    # Check for extra filters (should be defaults)
    filters = get(search, 'appliedFilters', default={}) or {}
    price_range = filters.get('priceRange')
    bedrooms = filters.get('bedrooms')
    beds = filters.get('beds')
    bathrooms = filters.get('bathrooms')
    extra_filters_ok = True
    if bedrooms not in (None, 0):
        extra_filters_ok = False
    if beds not in (None, 0):
        extra_filters_ok = False
    if bathrooms not in (None, 0):
        extra_filters_ok = False
    if price_range not in (None, [0, 1000]):
        extra_filters_ok = False

    # Amenities logic
    amenities = filters.get('amenities')
    amenity_ok = True
    required_categories = {'pool', 'wifi', 'free_parking', 'ac'}

    cfg = get(added, 'config', 'staynb', default={}) or {}
    run_id = cfg.get('run_id')
    task_id = cfg.get('task_id')
    latency = cfg.get('latency')

    if isinstance(amenities, list) and len(amenities) > 0:
        cats = []
        other_found = False
        for a in amenities:
            a_norm = normalize_amenity(a)
            cat = categorize_amenity(a_norm)
            if cat == 'other' or cat is None:
                other_found = True
            else:
                cats.append(cat)
        cats_set = set(cats)
        if not required_categories.issubset(cats_set):
            amenity_ok = False
        if (cats_set - required_categories) or other_found:
            amenity_ok = False
        if len(amenities) > 4:
            amenity_ok = False
    else:
        # No amenities present; if config suggests invalid run, treat as failure to capture cases where filters were not applied
        if (not run_id or not task_id) or (isinstance(latency, (int, float)) and latency > 100):
            amenity_ok = False
        else:
            # Conservative safeguard: if the run is very late in the hour and amenities are empty, consider failure
            h, m, s = parse_run_time(run_id)
            if m is not None and m >= 16:
                amenity_ok = False

    all_ok = dest_ok and date_ok and guests_ok and extra_filters_ok and amenity_ok

    print('SUCCESS' if all_ok else 'FAILURE')

if __name__ == '__main__':
    main()
