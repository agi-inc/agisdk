import json, sys

# Strategy:
# - Load final_state_diff.json and read search parameters from search and search.lastSearchCriteria
# - Success if: destination contains 'las vegas' (case-insensitive), dates are 2024-09-26 to 2024-09-29,
#   and at least one guests object has Rooms >= 2 and (Adults >= 3 or Adults+Children >= 4).
#   This aligns with training where Adults can be 3 and still considered success.

REQ_START = "2024-09-26"
REQ_END = "2024-09-29"

def safe_get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur

def norm_int(x):
    if x is None:
        return None
    if isinstance(x, bool):
        return int(x)
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return None


def date_matches(date_str, expected_prefix):
    if not isinstance(date_str, str):
        return False
    return date_str.startswith(expected_prefix)


def check_destination(search_obj):
    dests = []
    d1 = safe_get(search_obj, 'destination')
    if d1: dests.append(d1)
    d2 = safe_get(search_obj, 'lastSearchCriteria', 'destination')
    if d2: dests.append(d2)
    for d in dests:
        if isinstance(d, str) and 'las vegas' in d.lower():
            return True
    return False


def check_dates(search_obj):
    date_objs = []
    d1 = safe_get(search_obj, 'dates')
    if isinstance(d1, dict):
        date_objs.append(d1)
    d2 = safe_get(search_obj, 'lastSearchCriteria', 'dates')
    if isinstance(d2, dict):
        date_objs.append(d2)
    for dobj in date_objs:
        sd = dobj.get('startDate')
        ed = dobj.get('endDate')
        if date_matches(sd, REQ_START) and date_matches(ed, REQ_END):
            return True
    return False


def check_guests(search_obj):
    guests_list = []
    g1 = safe_get(search_obj, 'guests')
    if isinstance(g1, dict):
        guests_list.append(g1)
    g2 = safe_get(search_obj, 'lastSearchCriteria', 'guests')
    if isinstance(g2, dict):
        guests_list.append(g2)
    for g in guests_list:
        rooms = norm_int(g.get('Rooms'))
        adults = norm_int(g.get('Adults'))
        children = norm_int(g.get('Children'))
        if children is None:
            children = 0
        rooms_ok = rooms is not None and rooms >= 2
        # Accept if Adults >= 3 (seen in successful training data) OR total people >= 4
        people_ok = (adults is not None and adults >= 3) or ((adults is not None) and (adults + children >= 4))
        if rooms_ok and people_ok:
            return True
    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    updated = safe_get(data, 'initialfinaldiff', 'updated')
    if not isinstance(updated, dict):
        print("FAILURE")
        return

    search_obj = updated.get('search', {}) if isinstance(updated.get('search', {}), dict) else {}

    dest_ok = check_destination(search_obj)
    dates_ok = check_dates(search_obj)
    guests_ok = check_guests(search_obj)

    if dest_ok and dates_ok and guests_ok:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
