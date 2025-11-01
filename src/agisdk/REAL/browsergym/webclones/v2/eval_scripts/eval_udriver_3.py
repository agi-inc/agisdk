import sys, json

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Helper: safely get nested ride/user from either added or updated blocks

def get_section(data, key):
    d = data.get('initialfinaldiff', {})
    for container in ('added', 'updated'):
        section = d.get(container, {}).get(key)
        if section is not None:
            return section
    # Fallback: sometimes top-level under initialfinaldiff
    return d.get(key)


def norm(s):
    return (s or '').strip().lower()


def location_matches(loc, expected_name, expected_street, alt_substrings=None):
    if not isinstance(loc, dict):
        return False
    name = norm(loc.get('name'))
    fa = norm(loc.get('formattedAddress'))
    addr = norm(loc.get('address'))
    street = norm((loc.get('addressComponents') or {}).get('street'))

    # Exact name match
    if name == norm(expected_name):
        return True

    # Exact street match from components
    if expected_street and street == norm(expected_street):
        return True

    # Substring match on formatted/address
    if alt_substrings:
        alts = [norm(s) for s in alt_substrings]
        if any(alt and (alt in fa or alt in addr) for alt in alts):
            return True

    return False


def verify(data):
    ride = get_section(data, 'ride') or {}

    trips = ride.get('trips')
    if not isinstance(trips, list):
        trips = []

    # Expected endpoints
    pickup_expected_name = '1001 Castro Street'
    pickup_expected_street = '1001 Castro Street'
    pickup_alt = ['1001 Castro St', '1001 Castro Street']

    dest_expected_name = '1030 Post Street Apartments'
    dest_expected_street = '1030 Post Street'
    dest_alt = ['1030 Post St', '1030 Post Street']

    # Look for a completed trip matching both endpoints
    for t in trips:
        status = norm(t.get('status'))
        if status != 'completed':
            continue
        pickup = t.get('pickup') or {}
        dest = t.get('destination') or {}
        pickup_ok = location_matches(pickup, pickup_expected_name, pickup_expected_street, pickup_alt)
        dest_ok = location_matches(dest, dest_expected_name, dest_expected_street, dest_alt)
        if pickup_ok and dest_ok:
            return True

    return False


def main():
    try:
        path = sys.argv[1]
        data = load_json(path)
        if verify(data):
            print('SUCCESS')
        else:
            print('FAILURE')
    except Exception:
        # Any error defaults to failure
        print('FAILURE')

if __name__ == '__main__':
    main()
