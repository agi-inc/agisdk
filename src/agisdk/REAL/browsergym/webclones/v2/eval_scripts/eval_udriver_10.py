import json, sys

def norm(s):
    if s is None:
        return ''
    return ' '.join(str(s).lower().strip().split())

def loc_matches(loc, expected_id=None, expected_name_substrings=None):
    if not isinstance(loc, dict):
        return False
    # Prefer exact id match when available
    if expected_id is not None:
        try:
            if int(loc.get('id')) == int(expected_id):
                return True
        except Exception:
            pass
    # Fallback to substring checks on name/address fields
    fields = [loc.get('name'), loc.get('formattedAddress'), loc.get('address')]
    fields_norm = ' \n '.join([norm(x) for x in fields if x])
    if not fields_norm:
        return False
    if expected_name_substrings:
        for substr in expected_name_substrings:
            if norm(substr) in fields_norm:
                return True
    return False


def get_ride(data):
    # Try common locations for the ride object
    ride = None
    initialfinaldiff = data.get('initialfinaldiff') or {}
    added = initialfinaldiff.get('added') or {}
    updated = initialfinaldiff.get('updated') or {}
    for container in (added, updated, data):
        ride = container.get('ride') if isinstance(container, dict) else None
        if isinstance(ride, dict):
            return ride
    return None


def is_scheduled(ride):
    # If pickupDate or pickupTime provided (non-empty), or bookedTrip exists, it's scheduled
    pickup_date = ride.get('pickupDate')
    pickup_time = ride.get('pickupTime')
    if isinstance(pickup_date, str) and pickup_date.strip() != '':
        return True
    if isinstance(pickup_time, str) and pickup_time.strip() != '':
        return True
    booked_trip = ride.get('bookedTrip')
    if isinstance(booked_trip, dict) and len(booked_trip) > 0:
        return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    ride = get_ride(data)
    if not isinstance(ride, dict):
        print('FAILURE')
        return

    # Expected endpoints
    EXPECTED_PICKUP_ID = 699
    EXPECTED_PICKUP_NAMES = ['1 Hotel San Francisco', '8 Mission St']
    EXPECTED_DROPOFF_ID = 717
    EXPECTED_DROPOFF_NAMES = ['100 Van Ness', '100 Van Ness Ave']

    pickup_loc = ride.get('pickupLocation')
    dropoff_loc = ride.get('dropoffLocation')

    pickup_ok = loc_matches(pickup_loc, expected_id=EXPECTED_PICKUP_ID, expected_name_substrings=EXPECTED_PICKUP_NAMES)
    dropoff_ok = loc_matches(dropoff_loc, expected_id=EXPECTED_DROPOFF_ID, expected_name_substrings=EXPECTED_DROPOFF_NAMES)

    # Need a matching in-progress trip in the trips array to confirm booking now
    trips = ride.get('trips') or []
    in_progress_match = False
    for t in trips:
        if not isinstance(t, dict):
            continue
        status = norm(t.get('status'))
        if status != 'in progress':
            continue
        t_pick = t.get('pickup') or {}
        t_drop = t.get('destination') or {}
        if loc_matches(t_pick, expected_id=EXPECTED_PICKUP_ID, expected_name_substrings=EXPECTED_PICKUP_NAMES) and \
           loc_matches(t_drop, expected_id=EXPECTED_DROPOFF_ID, expected_name_substrings=EXPECTED_DROPOFF_NAMES):
            in_progress_match = True
            break

    # Must not be a scheduled ride
    scheduled = is_scheduled(ride)

    if pickup_ok and dropoff_ok and in_progress_match and not scheduled:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
