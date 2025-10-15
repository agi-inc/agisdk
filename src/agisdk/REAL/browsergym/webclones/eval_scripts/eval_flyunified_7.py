import json, sys

def get_nested(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def norm(s):
    if isinstance(s, str):
        return s.strip().lower()
    return s


def extract_date_mmdd(date_str):
    if not isinstance(date_str, str):
        return None
    # Expect formats like YYYY-MM-DD or ISO YYYY-MM-DDThh:mm:ssZ
    if 'T' in date_str:
        date_part = date_str.split('T', 1)[0]
    else:
        date_part = date_str
    if len(date_part) >= 10 and date_part[4] == '-' and date_part[7] == '-':
        return date_part[5:10]
    return None


def code_or_city(info_side):
    # info_side is expected to be something like info['from'] or info['to'] containing destination
    if not isinstance(info_side, dict):
        return None, None
    dest = info_side.get('destination', {}) if isinstance(info_side.get('destination'), dict) else {}
    code = dest.get('code')
    city = dest.get('city')
    return (norm(code), norm(city))


def flight_matches_leg(flight_info, from_code_expect, from_city_expect, to_code_expect, to_city_expect, target_mmdd):
    # Validate origin/destination and date for a leg
    if not isinstance(flight_info, dict):
        return False
    from_info = flight_info.get('from', {})
    to_info = flight_info.get('to', {})

    from_code, from_city = code_or_city(from_info)
    to_code, to_city = code_or_city(to_info)

    origin_ok = (from_code == norm(from_code_expect)) or (from_city == norm(from_city_expect))
    dest_ok = (to_code == norm(to_code_expect)) or (to_city == norm(to_city_expect))

    date_str = from_info.get('date')
    mmdd = extract_date_mmdd(date_str)
    date_ok = (mmdd == target_mmdd)

    return origin_ok and dest_ok and date_ok


def is_business_selected(flight_leg):
    if not isinstance(flight_leg, dict):
        return False
    sp = flight_leg.get('selectedPrice')
    if isinstance(sp, dict):
        t = sp.get('type')
        if isinstance(t, str) and t.strip().lower() == 'business':
            return True
    return False


def payment_is_paypal(booking):
    pinfo = booking.get('paymentInfo', {}) if isinstance(booking, dict) else {}
    pm = pinfo.get('paymentMethod')
    return isinstance(pm, str) and pm.strip().lower() == 'paypal'


def collect_bookings(data):
    bookings = {}
    # Primary path inside booking
    b1 = get_nested(data, ['initialfinaldiff', 'added', 'booking', 'bookedFlights'])
    if isinstance(b1, dict):
        bookings.update(b1)
    # Differences path
    b2 = get_nested(data, ['differences', 'bookedFlights', 'added'])
    if isinstance(b2, dict):
        # don't overwrite existing keys but that's fine
        for k, v in b2.items():
            bookings.setdefault(k, v)
    # Sometimes directly under added
    b3 = get_nested(data, ['initialfinaldiff', 'added', 'bookedFlights'])
    if isinstance(b3, dict):
        for k, v in b3.items():
            bookings.setdefault(k, v)
    return bookings


def verify(data):
    bookings = collect_bookings(data)
    if not isinstance(bookings, dict) or len(bookings) == 0:
        return False

    # Target parameters
    from_code = 'SFO'
    to_code = 'LAS'
    from_city = 'San Francisco'
    to_city = 'Las Vegas'
    outbound_mmdd = '09-26'
    return_mmdd = '09-30'

    for _, booking in bookings.items():
        if not isinstance(booking, dict):
            continue
        if not payment_is_paypal(booking):
            continue
        flight = booking.get('flight', {}) if isinstance(booking.get('flight'), dict) else {}
        out_leg = flight.get('outboundFlight')
        ret_leg = flight.get('returnFlight')
        if not isinstance(out_leg, dict) or not isinstance(ret_leg, dict):
            # Must be roundtrip
            continue
        out_info = out_leg.get('info', {}) if isinstance(out_leg.get('info'), dict) else {}
        ret_info = ret_leg.get('info', {}) if isinstance(ret_leg.get('info'), dict) else {}

        # Check leg directions and dates
        out_ok = flight_matches_leg(out_info, from_code, from_city, to_code, to_city, outbound_mmdd)
        ret_ok = flight_matches_leg(ret_info, to_code, to_city, from_code, from_city, return_mmdd)
        if not (out_ok and ret_ok):
            continue

        # Check Business class selection for both legs
        if not (is_business_selected(out_leg) and is_business_selected(ret_leg)):
            continue

        return True

    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
        result = verify(data)
        print('SUCCESS' if result else 'FAILURE')
    except Exception:
        # In case of any parsing or missing data error, mark as failure
        print('FAILURE')

if __name__ == '__main__':
    main()
