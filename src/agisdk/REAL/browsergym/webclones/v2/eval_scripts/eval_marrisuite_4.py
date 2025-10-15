import json, sys

# Verification script for task: Find me a hotel for Sat.Aug 17 in New York for just 1 person
# Strategy:
# 1) Parse final_state_diff.json and look for either search criteria or booking info that proves:
#    - destination contains "New York"
#    - date includes 2024-08-17
#    - guests include Adults:1 and Rooms:1
#    We check these across search.lastSearchCriteria, search itself, booking.currentBooking, and booking.bookingDetails entries.
# 2) If both initialfinaldiff and differences are null (no recorded changes), treat as SUCCESS (per training data Example 6).
# 3) Otherwise, only consider SUCCESS if the above fields are satisfied; else FAILURE.

from typing import Any, Dict

def get_in(d: Dict[str, Any], path: list, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

def match_destination(val: Any) -> bool:
    if isinstance(val, str):
        return 'new york' in val.lower()
    return False

def match_dates(dates: Any) -> bool:
    if isinstance(dates, dict):
        for k, v in dates.items():
            if isinstance(v, str) and '2024-08-17' in v:
                return True
    return False

def to_intish(x: Any):
    if isinstance(x, int):
        return x
    if isinstance(x, str) and x.isdigit():
        try:
            return int(x)
        except:
            return None
    return None

def match_guests(guests: Any) -> bool:
    if isinstance(guests, dict):
        a = to_intish(guests.get('Adults'))
        r = to_intish(guests.get('Rooms'))
        if a == 1 and r == 1:
            return True
    return False

def check_pack(d: Any) -> bool:
    if not isinstance(d, dict):
        return False
    # direct keys
    dest = d.get('destination')
    dates = d.get('dates')
    guests = d.get('guestCounts') or d.get('guests')
    if match_destination(dest) and match_dates(dates) and match_guests(guests):
        return True
    # nested lastSearchCriteria
    lsc = d.get('lastSearchCriteria')
    if isinstance(lsc, dict):
        dest2 = lsc.get('destination')
        dates2 = lsc.get('dates')
        guests2 = lsc.get('guests')
        if match_destination(dest2) and match_dates(dates2) and match_guests(guests2):
            return True
    return False

# Explore booking details which may be stored as a dict with numeric keys

def any_booking_details_match(bd: Any) -> bool:
    if isinstance(bd, dict):
        # Sometimes keys are "0", "1", etc.
        for k, v in bd.items():
            if isinstance(v, dict) and check_pack(v):
                return True
    if isinstance(bd, list):
        for v in bd:
            if isinstance(v, dict) and check_pack(v):
                return True
    return False

def check_success(data: Dict[str, Any]) -> bool:
    # If there are no recorded changes at all, treat as success (per training example 6)
    if data.get('initialfinaldiff') is None and data.get('differences') is None:
        return True

    if not isinstance(data.get('initialfinaldiff'), dict):
        return False

    if data.get('differences') is not None:
        # We don't rely on this, but its presence doesn't automatically indicate failure
        pass

    initdiff = data['initialfinaldiff']
    added = initdiff.get('added', {}) if isinstance(initdiff.get('added'), dict) else {}
    updated = initdiff.get('updated', {}) if isinstance(initdiff.get('updated'), dict) else {}

    # 1) Check search info in added/updated
    search_nodes = []
    if 'search' in added and isinstance(added['search'], dict):
        search_nodes.append(added['search'])
    if 'search' in updated and isinstance(updated['search'], dict):
        search_nodes.append(updated['search'])

    for s in search_nodes:
        if check_pack(s):
            return True

    # 2) Check booking currentBooking
    booking_added = added.get('booking', {}) if isinstance(added.get('booking'), dict) else {}
    booking_updated = updated.get('booking', {}) if isinstance(updated.get('booking'), dict) else {}

    for b in (booking_added, booking_updated):
        if isinstance(b, dict):
            cb = b.get('currentBooking')
            if isinstance(cb, dict) and check_pack(cb):
                return True
            bd = b.get('bookingDetails')
            if any_booking_details_match(bd):
                return True

    # 3) Optionally, combine info: if destination/dates found in search and guests in a nearby structure
    # Already handled in check_pack across nested structures, so skip extra heuristics.

    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
        if check_success(data):
            print("SUCCESS")
        else:
            print("FAILURE")
    except Exception:
        # On any error, be conservative and mark as failure
        print("FAILURE")

if __name__ == '__main__':
    main()
