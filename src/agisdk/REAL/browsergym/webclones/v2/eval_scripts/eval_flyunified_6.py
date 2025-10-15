import json, sys

def find_booking_flight(obj):
    """Recursively search for a dict that looks like a bookingFlight config.
    We consider a dict with keys including: from, to, dates, travelers, tripType.
    Returns the first match found.
    """
    if isinstance(obj, dict):
        # Direct match if it looks like a bookingFlight
        required_keys = {"from", "to", "dates", "travelers", "tripType"}
        if required_keys.issubset(set(obj.keys())):
            return obj
        # If it has a specific key 'bookingFlight', check that
        if "bookingFlight" in obj and isinstance(obj["bookingFlight"], dict):
            candidate = obj["bookingFlight"]
            if required_keys.issubset(set(candidate.keys())):
                return candidate
        # Otherwise, recurse into values
        for v in obj.values():
            res = find_booking_flight(v)
            if res is not None:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_booking_flight(item)
            if res is not None:
                return res
    return None


def get_in(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def parse_mm_dd(date_str):
    if not isinstance(date_str, str):
        return None
    # Normalize to YYYY-MM-DD by slicing first 10 if ISO format
    core = date_str[:10]
    parts = core.split('-')
    if len(parts) != 3:
        return None
    try:
        mm = int(parts[1])
        dd = int(parts[2])
        return (mm, dd)
    except Exception:
        return None


def verify(data):
    # Strategy: find bookingFlight-like dict anywhere; then verify:
    # - tripType roundtrip
    # - from.code SFO
    # - to.code JFK
    # - travelClass Economy
    # - dates[0] is Oct 1 and dates[1] is Oct 8 (month/day check)
    # - travelers: exactly 1 adult, all others 0
    booking = None

    # Try likely path first
    booking = get_in(data, ["initialfinaldiff", "added", "booking", "bookingFlight"]) or \
              get_in(data, ["initialfinaldiff", "updated", "booking", "bookingFlight"]) or \
              find_booking_flight(data)

    if not isinstance(booking, dict):
        return False

    # Trip type
    if str(booking.get("tripType", "")).lower() != "roundtrip":
        return False

    # From/To codes
    from_code = (get_in(booking, ["from", "code"]) or "").upper()
    to_code = (get_in(booking, ["to", "code"]) or "").upper()
    if from_code != "SFO" or to_code != "JFK":
        return False

    # Travel class
    travel_class = str(booking.get("travelClass", ""))
    if travel_class.lower() != "economy":
        return False

    # Dates
    dates = booking.get("dates")
    if not isinstance(dates, list) or len(dates) < 2:
        return False
    d0 = parse_mm_dd(dates[0])
    d1 = parse_mm_dd(dates[1])
    if d0 is None or d1 is None:
        return False
    # Expect Oct 1 and Oct 8 specifically in order
    if not (d0 == (10, 1) and d1 == (10, 8)):
        return False

    # Travelers: one adult, others zero
    travelers = booking.get("travelers")
    if not isinstance(travelers, list) or len(travelers) == 0:
        return False
    adults_count = None
    other_sum = 0
    for t in travelers:
        if not isinstance(t, dict):
            continue
        key = str(t.get("key", ""))
        count = t.get("count", 0)
        try:
            count = int(count)
        except Exception:
            return False
        if key == "adults":
            adults_count = count
        else:
            other_sum += count
    if adults_count != 1:
        return False
    if other_sum != 0:
        return False

    return True


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if verify(data):
            print("SUCCESS")
        else:
            print("FAILURE")
    except Exception:
        # On any unexpected error, fail safely
        print("FAILURE")

if __name__ == "__main__":
    main()
