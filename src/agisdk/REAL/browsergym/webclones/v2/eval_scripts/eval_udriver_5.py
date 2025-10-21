import json, sys

# Strategy within code:
# - Load ride object from the diff (prefer added.ride, fallback to updated.ride).
# - Confirm: pickup name == 1 Hotel San Francisco, destination name == 1030 Post Street Apartments
# - Confirm car type is UdriverXL via ride.trip.car.type
# - Confirm ride is for now: no bookedTrip, empty pickupDate/time, and ride.status indicates in-progress
# - Confirm payment method selected is cash
# - If all conditions hold, print SUCCESS, else FAILURE

def get_nested(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    init = data.get('initialfinaldiff', {})
    ride = None
    # Prefer 'added.ride'
    ride = get_nested(init, ['added', 'ride'])
    if not isinstance(ride, dict) or not ride:
        # Fallback to 'updated.ride'
        ride = get_nested(init, ['updated', 'ride'], {})

    if not isinstance(ride, dict) or not ride:
        print('FAILURE')
        sys.exit(0)

    # Extract key fields safely
    pickup_name = get_nested(ride, ['trip', 'pickup', 'name'], '') or ''
    dest_name = get_nested(ride, ['trip', 'destination', 'name'], '') or ''
    car_type = get_nested(ride, ['trip', 'car', 'type'], '') or ''
    status = (ride.get('status') or '').strip().lower()

    pickup_date = (ride.get('pickupDate') or '').strip()
    pickup_time = (ride.get('pickupTime') or '').strip()
    booked_trip = ride.get('bookedTrip', None)

    sel_pay_type = (get_nested(ride, ['selectedPaymentMethod', 'type'], '') or '').strip().lower()

    # Conditions
    cond_pickup = pickup_name.strip().lower() == '1 hotel san francisco'
    cond_dest = dest_name.strip().lower() == '1030 post street apartments'
    cond_car = car_type.strip().lower() == 'udriverxl'

    # Now: no scheduled date/time, no bookedTrip, and status indicates active/in progress
    cond_now = (not booked_trip) and (pickup_date == '') and (pickup_time == '') and (status in {'in progress', 'searching', 'active'})

    cond_payment = sel_pay_type == 'cash'

    if cond_pickup and cond_dest and cond_car and cond_now and cond_payment:
        print('SUCCESS')
    else:
        print('FAILURE')

except Exception:
    # Any unexpected issue => conservative failure
    print('FAILURE')
