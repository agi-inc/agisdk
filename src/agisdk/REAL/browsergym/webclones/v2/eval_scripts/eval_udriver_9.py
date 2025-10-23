import json, sys, os

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Deep merge helper to combine "added" and "updated" sections if needed
def deep_merge(a, b):
    if not isinstance(a, dict) or not isinstance(b, dict):
        return b
    out = dict(a)
    for k, v in b.items():
        if k in out:
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_ride_data(data):
    initialfinal = data.get('initialfinaldiff', {})
    ride = {}
    for section in ['added', 'updated']:
        ride = deep_merge(ride, initialfinal.get(section, {}).get('ride', {}))
    # Fallback if structure differs
    if not ride and 'ride' in data:
        ride = data['ride']
    return ride or {}


def norm(s):
    return (s or '').strip().lower()

EXPECTED_PICKUP = '1 hotel san francisco'
EXPECTED_DEST = '1030 post street apartments'
EXPECTED_CAR = 'udriverxl'
EXPECTED_PAYMENT = 'cash'


def trip_matches_now(trip):
    if not isinstance(trip, dict):
        return False
    pickup_name = norm(trip.get('pickup', {}).get('name'))
    dest_name = norm(trip.get('destination', {}).get('name'))
    car_type = norm(trip.get('car', {}).get('type'))
    status = norm(trip.get('status'))
    payment_type = norm(trip.get('paymentMethod', {}).get('type'))

    if pickup_name != EXPECTED_PICKUP:
        return False
    if dest_name != EXPECTED_DEST:
        return False
    if car_type != EXPECTED_CAR:
        return False
    if payment_type != EXPECTED_PAYMENT:
        return False
    if status not in {'completed', 'in progress'}:
        return False
    return True


def booked_matches_scheduled(entry):
    if not isinstance(entry, dict):
        return False
    pickup_name = norm(entry.get('pickup', {}).get('name'))
    dest_name = norm(entry.get('destination', {}).get('name'))
    car_type = norm(entry.get('car', {}).get('type'))
    status = norm(entry.get('status'))
    payment_type = norm(entry.get('paymentMethod', {}).get('type'))

    if pickup_name != EXPECTED_PICKUP:
        return False
    if dest_name != EXPECTED_DEST:
        return False
    if car_type != EXPECTED_CAR:
        return False
    # Payment may or may not be present; if present, must be cash
    if payment_type and payment_type != EXPECTED_PAYMENT:
        return False
    if status not in {'pending', 'scheduled'}:
        return False
    return True


def main():
    # Strategy: Look for a matching immediate trip in ride.trips with correct addresses, car type UdriverXL, and cash payment. This indicates a "now" ride (status completed/in progress). Ignore scheduled bookings unless no qualifying immediate trip exists.
    path = sys.argv[1]
    data = load_json(path)
    ride = get_ride_data(data)

    trips = ride.get('trips') or []
    has_now_trip = any(trip_matches_now(t) for t in trips if isinstance(t, dict))

    # If no immediate trip, check if only scheduled booking exists (this should fail the "now" requirement)
    if not has_now_trip:
        booked_trip = ride.get('bookedTrip')
        booked_trips = ride.get('bookedTrips') or []
        has_scheduled = False
        if isinstance(booked_trip, dict) and booked_matches_scheduled(booked_trip):
            has_scheduled = True
        if any(booked_matches_scheduled(bt) for bt in booked_trips if isinstance(bt, dict)):
            has_scheduled = True
        # Regardless of scheduled presence, absence of now-trip means failure
        print('FAILURE')
        return

    print('SUCCESS')

if __name__ == '__main__':
    main()
