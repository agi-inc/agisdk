import json, sys

# Strategy inside code:
# 1) Require concrete booking evidence (bookedFlights added or purchaseDetails indicating confirmation/booking).
# 2) Validate route and dates: LAX->MIA (not flipped), roundtrip (either via tripType or opposing segments), and dates 2024-12-27 & 2024-12-31.
# 3) Validate cabin is Business or First by looking at travelClass/cabin/class-related fields, avoiding false positives like "First name".

TARGET_FROM_CODE = 'LAX'
TARGET_TO_CODE = 'MIA'
OUT_DATE = '2024-12-27'
RETURN_DATE = '2024-12-31'

# Helper functions

def safe_get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        if k not in cur:
            return None
        cur = cur[k]
    return cur


def any_string_in_structure_with_keys(obj, substrings, key_hints=None):
    """Search recursively for any string value containing any of substrings.
    If key_hints is provided (set of substrings), only consider values whose key name contains one of the hints.
    """
    found = False
    def rec(o, parent_key=''):
        nonlocal found
        if found:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                k_lower = str(k).lower()
                if isinstance(v, (dict, list)):
                    rec(v, k_lower)
                else:
                    if isinstance(v, str):
                        val_lower = v.lower()
                        if key_hints is None or any(h in k_lower for h in key_hints):
                            for s in substrings:
                                if s in val_lower:
                                    found = True
                                    return
        elif isinstance(o, list):
            for item in o:
                rec(item, parent_key)
    rec(obj)
    return found


def get_all_date_matches(obj, date_strs, key_hints=(
    'date','depart','return','outbound','inbound','arrival','arrivaldate','departuredate'
)):
    found = {d: False for d in date_strs}
    def rec(o):
        if isinstance(o, dict):
            for k, v in o.items():
                k_lower = str(k).lower()
                if isinstance(v, (dict, list)):
                    rec(v)
                elif isinstance(v, str):
                    if any(h in k_lower for h in key_hints):
                        for d in date_strs:
                            if d in v:
                                found[d] = True
        elif isinstance(o, list):
            for item in o:
                rec(item)
    rec(obj)
    return found


def extract_code_from_field(v):
    # Extract an airport code from a value that might be dict or string
    if isinstance(v, dict):
        for key in ['code','iata','airportCode','airport','id']:
            val = v.get(key)
            if isinstance(val, str):
                up = val.upper()
                if TARGET_FROM_CODE in up or TARGET_TO_CODE in up or len(up) == 3:
                    return up
    elif isinstance(v, str):
        up = v.upper()
        # Prefer exact 3-letter codes if present
        if len(up) == 3 and up.isalpha():
            return up
        # Fallback: detect target codes if embedded
        if TARGET_FROM_CODE in up:
            return TARGET_FROM_CODE
        if TARGET_TO_CODE in up:
            return TARGET_TO_CODE
    return None


def collect_segments(obj):
    segments = []
    pairs = [
        ('from','to'), ('origin','destination'), ('departure','arrival'),
        ('departureAirport','arrivalAirport'), ('fromAirport','toAirport')
    ]
    def rec(o):
        if isinstance(o, dict):
            # Try to extract a segment from this dict
            for a, b in pairs:
                if a in o and b in o:
                    fa = o.get(a)
                    fb = o.get(b)
                    from_code = extract_code_from_field(fa)
                    to_code = extract_code_from_field(fb)
                    if from_code and to_code:
                        segments.append((from_code, to_code, o))
            # Recurse
            for v in o.values():
                rec(v)
        elif isinstance(o, list):
            for item in o:
                rec(item)
    rec(obj)
    return segments


def has_booking_confirmation(differences):
    booked = differences.get('bookedFlights', {})
    if isinstance(booked, dict):
        added = booked.get('added')
        if isinstance(added, dict) and len(added) > 0:
            return True
    purchase = differences.get('purchaseDetails', {})
    # Look for confirmation terms in purchase details
    if any_string_in_structure_with_keys(purchase, substrings={'confirm','book','purchas','ticket'}, key_hints={'status','state','result','confirmation','number','code','purchase','payment'}):
        return True
    # Also, if purchase added/updated non-empty, consider as potential confirmation if contains typical fields
    if isinstance(purchase, dict):
        for k in ['added','updated']:
            v = purchase.get(k)
            if isinstance(v, dict) and len(v) > 0:
                # Still require at least some confirmation-like hint
                if any_string_in_structure_with_keys(v, substrings={'confirm','book','issu','ticket','success','complete'}, key_hints={'status','confirmation','ticket','result','state'}):
                    return True
    return False


def get_bookingflight_nodes(initialfinaldiff):
    nodes = []
    for section in ['added','updated']:
        sec = initialfinaldiff.get(section, {})
        if isinstance(sec, dict):
            b = safe_get(sec, 'booking', 'booking')
            if isinstance(b, dict) and 'bookingFlight' in b:
                bf = b.get('bookingFlight')
                if isinstance(bf, dict):
                    nodes.append(bf)
            # Some structures might directly have booking.bookingFlight
            bf2 = safe_get(sec, 'booking', 'bookingFlight')
            if isinstance(bf2, dict):
                nodes.append(bf2)
    return nodes


def route_and_dates_ok(data):
    initial = data.get('initialfinaldiff', {})
    differences = data.get('differences', {})

    # Try bookingFlight first
    bf_nodes = get_bookingflight_nodes(initial)
    have_correct_route = False
    have_roundtrip = False
    have_dates = False

    # Date matches tracker
    out_match = False
    ret_match = False

    for bf in bf_nodes:
        # tripType
        trip_type = str(bf.get('tripType','')).lower()
        if trip_type == 'roundtrip':
            have_roundtrip = True
        # from/to codes
        f = bf.get('from') or {}
        t = bf.get('to') or {}
        fcode = None
        tcode = None
        if isinstance(f, dict):
            fcode = str(f.get('code','') or f.get('iata','') or '').upper()
        if isinstance(t, dict):
            tcode = str(t.get('code','') or t.get('iata','') or '').upper()
        if fcode == TARGET_FROM_CODE and tcode == TARGET_TO_CODE:
            have_correct_route = True
        # dates
        dates = bf.get('dates')
        if isinstance(dates, list):
            ds = [str(x) for x in dates]
            out_match = any(OUT_DATE in x for x in ds) or out_match
            ret_match = any(RETURN_DATE in x for x in ds) or ret_match

    # If bookingFlight not present or incomplete, try to infer from bookedFlights
    if not have_correct_route or not have_roundtrip:
        booked = differences.get('bookedFlights', {})
        added = booked.get('added', {}) if isinstance(booked, dict) else {}
        segments = []
        if isinstance(added, dict):
            for v in added.values():
                segs = collect_segments(v)
                segments.extend(segs)
        # Check for segment presence LAX->MIA and MIA->LAX
        has_out = any(s[0] and s[1] and s[0].upper().endswith(TARGET_FROM_CODE) and s[1].upper().endswith(TARGET_TO_CODE) for s in segments)
        has_ret = any(s[0] and s[1] and s[0].upper().endswith(TARGET_TO_CODE) and s[1].upper().endswith(TARGET_FROM_CODE) for s in segments)
        if has_out:
            have_correct_route = True
        if has_out and has_ret:
            have_roundtrip = True

    # Dates: if not already confirmed, search broadly but limited to date-related keys
    if not (out_match and ret_match):
        # search in both initial and differences
        date_matches_initial = get_all_date_matches(initial, [OUT_DATE, RETURN_DATE])
        date_matches_diff = get_all_date_matches(differences, [OUT_DATE, RETURN_DATE])
        out_match = out_match or date_matches_initial.get(OUT_DATE, False) or date_matches_diff.get(OUT_DATE, False)
        ret_match = ret_match or date_matches_initial.get(RETURN_DATE, False) or date_matches_diff.get(RETURN_DATE, False)

    have_dates = out_match and ret_match

    return have_correct_route and have_roundtrip and have_dates


def cabin_ok(data):
    initial = data.get('initialfinaldiff', {})
    differences = data.get('differences', {})

    # Prefer explicit cabin/class fields
    key_hints = {'class','cabin','fare','service','travelclass','bookingclass'}
    substr_business = {'business'}
    substr_first = {'first'}

    # Check bookingFlight travelClass
    bf_nodes = get_bookingflight_nodes(initial)
    for bf in bf_nodes:
        v = bf.get('travelClass')
        if isinstance(v, str):
            lv = v.lower()
            if 'business' in lv or ('first' in lv and 'first ' == 'first ' or 'first' in lv):
                return True

    # Check differences/bookedFlights and purchaseDetails for cabin-related fields
    if any_string_in_structure_with_keys(differences, substr_business, key_hints):
        return True
    if any_string_in_structure_with_keys(differences, substr_first, key_hints):
        return True

    # Also check initial for such fields (in case selection captured there)
    if any_string_in_structure_with_keys(initial, substr_business, key_hints):
        return True
    if any_string_in_structure_with_keys(initial, substr_first, key_hints):
        return True

    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    differences = data.get('differences', {})

    # 1) Must have booking confirmation
    booked_confirmed = has_booking_confirmation(differences)

    # 2) Route and dates must match goal
    route_dates_match = route_and_dates_ok(data)

    # 3) Cabin must be business or first
    cabin_match = cabin_ok(data)

    if booked_confirmed and route_dates_match and cabin_match:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
