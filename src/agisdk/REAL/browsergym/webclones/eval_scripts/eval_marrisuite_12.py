import json, sys

def extract_date_only(s):
    if isinstance(s, str) and len(s) >= 10:
        return s[:10]
    return None


def get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def normalize_str(x):
    if isinstance(x, str):
        return x.strip().lower()
    return None


def collect_guest_values(search, last):
    vals = {
        'Adults': [],
        'Rooms': [],
        'Children': []
    }
    for src in (search, last):
        if isinstance(src, dict):
            g = src.get('guests')
            if isinstance(g, dict):
                for k in list(vals.keys()):
                    if k in g:
                        vals[k].append(g.get(k))
    return vals


def collect_date_values(search, last):
    dates = []
    for src in (search, last):
        if isinstance(src, dict):
            d = src.get('dates')
            if isinstance(d, dict):
                sd = extract_date_only(d.get('startDate'))
                ed = extract_date_only(d.get('endDate'))
                if sd or ed:
                    dates.append((sd, ed))
    return dates


def collect_destination_values(search, last):
    dests = []
    for src in (search, last):
        if isinstance(src, dict):
            dest = src.get('destination')
            if isinstance(dest, str):
                dests.append(dest)
    return dests


def verify(data):
    updated = data.get('initialfinaldiff', {}) or {}
    if not isinstance(updated, dict):
        updated = {}
    updated = updated.get('updated', {}) or {}
    if not isinstance(updated, dict):
        updated = {}

    search = updated.get('search', {}) or {}
    if not isinstance(search, dict):
        search = {}
    last = search.get('lastSearchCriteria', {}) or {}
    if not isinstance(last, dict):
        last = {}

    # Destination check: must contain 'amsterdam' (case-insensitive) in any provided destination.
    dest_values = collect_destination_values(search, last)
    dest_present = len(dest_values) > 0
    dest_ok = dest_present and all(('amsterdam' in normalize_str(d) if normalize_str(d) else False) for d in dest_values)

    # Dates check: must be 2024-11-18 to 2024-11-22 in any provided dates source, and any present pair must match.
    date_values = collect_date_values(search, last)
    # Require at least one date pair present
    dates_present = len(date_values) > 0
    desired_start = '2024-11-18'
    desired_end = '2024-11-22'
    dates_ok = dates_present and all(sd == desired_start and ed == desired_end for sd, ed in date_values)

    # Guests check: Adults=4, Rooms=1; Children if present must be 0.
    guest_vals = collect_guest_values(search, last)
    adults_vals = guest_vals['Adults']
    rooms_vals = guest_vals['Rooms']
    children_vals = guest_vals['Children']

    # Ensure presence of at least one adults and one rooms value
    adults_present = len(adults_vals) > 0
    rooms_present = len(rooms_vals) > 0

    def to_int(x):
        if isinstance(x, int):
            return x
        try:
            return int(x)
        except Exception:
            return None

    adults_ok = adults_present and all(to_int(v) == 4 for v in adults_vals)
    rooms_ok = rooms_present and all(to_int(v) == 1 for v in rooms_vals)
    # Children if provided must be 0
    children_ok = all(to_int(v) == 0 for v in children_vals)

    all_ok = dest_ok and dates_ok and adults_ok and rooms_ok and children_ok
    return all_ok


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
        if verify(data):
            print('SUCCESS')
        else:
            print('FAILURE')
    except Exception:
        # Any error should be considered a failure
        print('FAILURE')

if __name__ == '__main__':
    main()
