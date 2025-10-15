import json, sys, re

# Strategy:
# - Treat success as having at least one booked flight recorded in the final state diff.
# - Validate the booked flight matches one-way JFK -> SFO on 2024-12-18. If a "cheapest" indicator exists, require it; otherwise, don't enforce.
# - Robustly search in differences.initialfinaldiff for bookedFlights and interpret common field names for route/date.

TARGET_ORIGIN = "JFK"
TARGET_DEST = "SFO"
TARGET_DATE = "2024-12-18"

import datetime

def norm_date(s):
    if not s or not isinstance(s, str):
        return None
    # Extract YYYY-MM-DD from various formats
    # Try ISO first
    try:
        # Strip timezone if present
        if 'T' in s:
            # 2024-12-18T00:00:00.000Z
            return s.split('T')[0]
        # Maybe already YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return s
        # Try other common patterns like MM/DD/YYYY or YYYY/MM/DD
        m = re.match(r"^(\d{4})[/-](\d{2})[/-](\d{2})$", s)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        m = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})$", s)
        if m:
            return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
    except Exception:
        pass
    return None


def extract_code(val):
    # Return airport code if found in various shapes
    if val is None:
        return None
    if isinstance(val, str):
        # If looks like code
        if re.match(r"^[A-Za-z]{3}$", val.strip()):
            return val.strip().upper()
        # Might contain code within e.g., "New York/JFK" or "JFK - New York"
        m = re.search(r"\b([A-Za-z]{3})\b", val)
        if m:
            return m.group(1).upper()
        return None
    if isinstance(val, dict):
        for k in ["code", "iata", "iataCode", "airportCode", "short"]:
            if k in val and isinstance(val[k], str) and val[k].strip():
                c = val[k].strip().upper()
                if re.match(r"^[A-Z]{3}$", c):
                    return c
        # Sometimes nested name strings contain code
        for k, v in val.items():
            if isinstance(v, str):
                m = re.search(r"\b([A-Za-z]{3})\b", v)
                if m:
                    return m.group(1).upper()
        return None
    return None


def find_first_date_in_obj(obj):
    # search for any date-like string in obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                d = norm_date(v)
                if d:
                    return d
            elif isinstance(v, (dict, list)):
                d = find_first_date_in_obj(v)
                if d:
                    return d
    elif isinstance(obj, list):
        for it in obj:
            d = find_first_date_in_obj(it)
            if d:
                return d
    return None


def extract_route_from_flight(f):
    """Try to extract origin/destination airport codes and departure date from a flight entry.
    Returns (origin, dest, date_str or None)
    """
    origin = dest = dep_date = None

    # Common fields
    for key in ["from", "origin", "originAirport", "departure", "departureAirport", "start", "source"]:
        if key in f:
            origin = extract_code(f.get(key)) or origin
    for key in ["to", "destination", "destinationAirport", "arrival", "arrivalAirport", "end", "target"]:
        if key in f:
            dest = extract_code(f.get(key)) or dest

    # Date fields
    for key in ["date", "departureDate", "departDate", "outboundDate", "flightDate", "travelDate", "departingOn"]:
        if key in f and isinstance(f[key], str):
            dep_date = norm_date(f[key]) or dep_date

    # Segments fallback: first and last segment
    segments = None
    for key in ["segments", "legs", "itinerary", "outboundSegments"]:
        if key in f and isinstance(f[key], list) and f[key]:
            segments = f[key]
            break
    if segments:
        # origin from first, dest from last
        first = segments[0]
        last = segments[-1]
        # try extract from/from-like keys
        for key in ["from", "origin", "departure", "originAirport"]:
            if isinstance(first, dict) and key in first:
                origin = extract_code(first.get(key)) or origin
        for key in ["to", "destination", "arrival", "destinationAirport"]:
            if isinstance(last, dict) and key in last:
                dest = extract_code(last.get(key)) or dest
        # date from first segment departure
        for key in ["date", "departureDate", "departDate", "flightDate", "travelDate", "departTime", "departureTime"]:
            if isinstance(first, dict) and key in first and isinstance(first[key], str):
                dep_date = norm_date(first[key]) or dep_date

    # If still missing date, scan object for first date-like string
    if not dep_date:
        dep_date = find_first_date_in_obj(f)

    return origin, dest, dep_date


def collect_booked_flights(data):
    flights = []
    # From differences.bookedFlights.{added,updated}
    diffs = data.get("differences") or {}
    bf = diffs.get("bookedFlights") or {}
    for sub in ("added", "updated"):
        subval = bf.get(sub)
        if isinstance(subval, dict):
            for _, v in subval.items():
                flights.append(v)
        elif isinstance(subval, list):
            flights.extend(subval)
    # Also check initialfinaldiff for any bookedFlights structures
    initdiff = data.get("initialfinaldiff") or {}
    def recurse_collect(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "bookedFlights":
                    if isinstance(v, dict):
                        for _, vv in v.items():
                            flights.append(vv)
                    elif isinstance(v, list):
                        flights.extend(v)
                elif isinstance(v, (dict, list)):
                    recurse_collect(v)
        elif isinstance(obj, list):
            for it in obj:
                recurse_collect(it)
    recurse_collect(initdiff)
    return flights


def get_booking_form(data):
    # Try to retrieve the search/booking form details to validate oneway JFK->SFO and date
    initdiff = data.get("initialfinaldiff") or {}
    added = initdiff.get("added") or {}
    booking = None
    # Navigate typical path
    if isinstance(added, dict):
        b = added.get("booking") or added.get("book") or added.get("reservation")
        if isinstance(b, dict):
            booking = b.get("bookingFlight") or b.get("flight") or b.get("search") or b
    return booking if isinstance(booking, dict) else None


def is_oneway_context(data):
    booking = get_booking_form(data)
    if booking and isinstance(booking.get("tripType"), str):
        return booking.get("tripType").replace("-", "").lower() in ("oneway", "onewaytrip")
    # Fallback: absence of return date in dates array
    if booking and isinstance(booking.get("dates"), list):
        dates = booking.get("dates")
        if dates and len(dates) >= 2:
            # Often [depart, return]
            return dates[1] in (None, "", 0)
    return True  # default to True to not over-reject when info missing


def booking_form_route_date(data):
    booking = get_booking_form(data)
    origin = dest = dep_date = None
    if booking:
        if isinstance(booking.get("from"), (dict, str)):
            origin = extract_code(booking.get("from"))
        if isinstance(booking.get("to"), (dict, str)):
            dest = extract_code(booking.get("to"))
        # dates may be array [depart, return]
        dates = booking.get("dates")
        if isinstance(dates, list) and dates:
            dep_date = norm_date(dates[0]) if isinstance(dates[0], str) else None
        # alternative fields
        for key in ["date", "departureDate", "departDate"]:
            if key in booking and isinstance(booking[key], str):
                dep_date = norm_date(booking[key]) or dep_date
    return origin, dest, dep_date


def has_cheapest_indicator_ok(f):
    # If any cheapest indicator exists, enforce it; otherwise return True
    # Common flags
    for key in ["isCheapest", "cheapest", "lowest", "isLowestPrice", "lowestFare", "bestPrice"]:
        if key in f:
            val = f.get(key)
            if isinstance(val, bool):
                return val is True
            # handle strings like "true"/"false"
            if isinstance(val, str):
                return val.strip().lower() in ("true", "yes", "1")
            # numeric
            if isinstance(val, (int, float)):
                return bool(val)
    # Rank-based indicators
    for key in ["priceRank", "rank", "fareRank"]:
        if key in f and isinstance(f.get(key), (int, float)):
            return int(f.get(key)) == 1
    return True


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        print("FAILURE")
        return

    # Collect booked flights
    flights = collect_booked_flights(data)

    # If no explicit bookedFlights, consider it a failure (no booking evidence)
    if not flights:
        print("FAILURE")
        return

    # Validate one-way context from form if available
    if not is_oneway_context(data):
        print("FAILURE")
        return

    # Booking form route/date as fallback comparison
    form_origin, form_dest, form_dep_date = booking_form_route_date(data)

    # Evaluate each flight candidate
    success_found = False
    for f in flights:
        if not isinstance(f, dict):
            continue
        origin, dest, dep_date = extract_route_from_flight(f)
        # Fallback to form values if missing in flight record
        if not origin and form_origin:
            origin = form_origin
        if not dest and form_dest:
            dest = form_dest
        if not dep_date and form_dep_date:
            dep_date = form_dep_date

        # Route/date checks
        if origin != TARGET_ORIGIN or dest != TARGET_DEST:
            continue
        if dep_date != TARGET_DATE:
            # allow when dep_date missing but form has correct date and flight lacks date
            if dep_date is None and form_dep_date == TARGET_DATE:
                pass
            else:
                continue

        # Cheapest indicator if present
        if not has_cheapest_indicator_ok(f):
            continue

        # Booking status if available (should not be negative)
        status = None
        for key in ["status", "bookingStatus", "confirmationStatus"]:
            if key in f and isinstance(f[key], str):
                status = f[key].strip().lower()
                break
        if status and status not in ("booked", "confirmed", "ticketed", "completed", "success"):
            # if status explicitly indicates not booked
            continue

        success_found = True
        break

    print("SUCCESS" if success_found else "FAILURE")

if __name__ == "__main__":
    main()
