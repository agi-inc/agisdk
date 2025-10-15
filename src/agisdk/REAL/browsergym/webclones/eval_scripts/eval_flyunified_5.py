import json, sys, re

# Strategy:
# 1) Confirm booking completion by checking bookedFlights/purchaseDetails/confirmation indicators.
# 2) Validate route (LAS -> LAX), oneway, and Jan 3 date from bookingFlight or global strings.
# 3) Verify aisle seat via explicit 'aisle' markers, isAisle True, or common aisle seat letters (C/D) in seat codes.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def deep_items(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            for ik, iv in deep_items(v):
                yield ik, iv
    elif isinstance(obj, list):
        for item in obj:
            for ik, iv in deep_items(item):
                yield ik, iv


def deep_values(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from deep_values(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from deep_values(item)
    else:
        yield obj


def get_path(obj, path_list, default=None):
    cur = obj
    for p in path_list:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def non_empty(d):
    if d is None:
        return False
    if isinstance(d, dict) or isinstance(d, list) or isinstance(d, str):
        return len(d) > 0
    return bool(d)


def has_booking_confirmation(data):
    # Primary signals in differences
    diff = data.get('differences', {})
    booked_added = get_path(diff, ['bookedFlights', 'added'], {})
    purchase_added = get_path(diff, ['purchaseDetails', 'added'], {})
    # Sometimes selection cart IDs indicate selection but not purchase; don't use alone
    booked_ok = non_empty(booked_added) or non_empty(purchase_added)

    # Secondary signals: confirmation codes, status, ticketing
    if not booked_ok:
        for k, v in deep_items(data):
            kl = str(k).lower()
            if kl in {'confirmation', 'confirmationcode', 'confirmation_number', 'confirmationnumber', 'recordlocator', 'pnr', 'ticket', 'ticketnumber', 'eticket', 'e-ticket'}:
                if v not in (None, '', [], {}):
                    booked_ok = True
                    break
            if kl == 'status' and isinstance(v, str) and v.lower() in {'booked', 'confirmed', 'purchased', 'ticketed'}:
                booked_ok = True
                break
            if 'payment' in kl and v not in (None, '', [], {}):
                booked_ok = True
                break
    return booked_ok


def route_and_date_ok(data):
    # Prefer bookingFlight context
    bf = get_path(data, ['initialfinaldiff', 'added', 'booking', 'bookingFlight'], {}) or \
         get_path(data, ['initialfinaldiff', 'updated', 'booking', 'bookingFlight'], {}) or {}

    def check_bf(bf):
        if not isinstance(bf, dict):
            return False
        tt = str(bf.get('tripType', '')).lower()
        oneway_ok = (tt == 'oneway')
        fr = bf.get('from', {}) if isinstance(bf.get('from', {}), dict) else {}
        to = bf.get('to', {}) if isinstance(bf.get('to', {}), dict) else {}
        fr_ok = (str(fr.get('code', '')).upper() == 'LAS') or ('las vegas' in str(fr.get('city', '')).lower())
        to_ok = (str(to.get('code', '')).upper() == 'LAX') or ('los angeles' in str(to.get('city', '')).lower())
        # Date: accept any year but must be Jan 3
        dates = bf.get('dates', []) if isinstance(bf.get('dates', []), list) else [bf.get('dates')]
        date_ok = False
        for d in dates:
            if isinstance(d, str):
                if re.search(r'\b\d{4}-01-0?3', d):
                    date_ok = True
                    break
        return oneway_ok and fr_ok and to_ok and date_ok

    if check_bf(bf):
        return True

    # Fallback: global evidence
    # oneway
    oneway_found = False
    las_found = False
    lax_found = False
    date_found = False
    for k, v in deep_items(data):
        if isinstance(v, str):
            vs = v.lower()
            if v.upper() == 'LAS' or 'las vegas' in vs:
                las_found = True
            if v.upper() == 'LAX' or 'los angeles' in vs:
                lax_found = True
            if re.search(r'\b\d{4}-01-0?3', v):
                date_found = True
            if vs.strip() == 'oneway' or vs.strip() == 'one-way' or vs.strip() == 'one way':
                oneway_found = True
        elif isinstance(v, bool):
            # no-op
            pass
    return oneway_found and las_found and lax_found and date_found


def has_aisle_seat(data):
    # Explicit aisle markers
    for k, v in deep_items(data):
        kl = str(k).lower()
        if isinstance(v, str) and 'aisle' in v.lower():
            return True
        if 'aisle' in kl and isinstance(v, bool) and v is True:
            return True
        if (('seat' in kl) or (kl in {'seat', 'seatpreference', 'seat_type', 'seatlocation'})) and isinstance(v, str):
            if 'aisle' in v.lower():
                return True
    # Try to infer from seat codes (common 3-3 layout: C/D are aisles)
    seat_code_pattern = re.compile(r'\b\d{1,2}[A-Z]\b')
    for val in deep_values(data):
        if isinstance(val, str):
            m = seat_code_pattern.findall(val)
            for code in m:
                letter = code[-1]
                if letter in {'C', 'D'}:
                    return True
    return False


def main():
    try:
        path = sys.argv[1]
        data = load_json(path)
        booked = has_booking_confirmation(data)
        route_ok = route_and_date_ok(data)
        aisle_ok = has_aisle_seat(data)
        if booked and route_ok and aisle_ok:
            print('SUCCESS')
        else:
            print('FAILURE')
    except Exception:
        # On any error, return FAILURE to be safe
        print('FAILURE')

if __name__ == '__main__':
    main()
