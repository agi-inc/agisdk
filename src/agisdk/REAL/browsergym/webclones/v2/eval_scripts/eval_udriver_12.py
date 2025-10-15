import json, sys

def norm(s):
    if s is None:
        return None
    return str(s).strip().lower()

# Strategy inside code:
# - Load final_state_diff.json and locate the 'ride' object under initialfinaldiff.added (robustly falling back if missing).
# - Prefer bookedTrip details (pickup/destination/date/time) to validate the intended trip; otherwise, use root ride fields.
# - Check: pickup=333 Fremont Apartments, dropoff=201 Turk Street Apartments, date=7/18/2024, time=3:30 PM.
# - Ensure a price was computed (either ride.calculatedPrice.finalPrice or bookedTrip.car.finalPrice > 0).
# - Print SUCCESS only if all conditions hold; otherwise FAILURE.

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    ride = (
        data.get('initialfinaldiff', {})
            .get('added', {})
            .get('ride')
    )

    # If not in added, try updated just in case
    if ride is None:
        ride = (
            data.get('initialfinaldiff', {})
                .get('updated', {})
                .get('ride')
        )

    if not isinstance(ride, dict):
        print("FAILURE")
        sys.exit(0)

    booked = ride.get('bookedTrip') if isinstance(ride.get('bookedTrip'), dict) else None

    if booked is not None:
        pickup_name = booked.get('pickup', {}).get('name')
        dest_name = booked.get('destination', {}).get('name')
        date = booked.get('date')
        time = booked.get('time')
    else:
        pickup_name = ride.get('pickupLocation', {}).get('name')
        dest_name = ride.get('dropoffLocation', {}).get('name')
        date = ride.get('pickupDate')
        time = ride.get('pickupTime')

    # Normalize for comparison
    pickup_ok = norm(pickup_name) == norm('333 Fremont Apartments')
    dest_ok = norm(dest_name) == norm('201 Turk Street Apartments')

    date_ok = norm(date) == norm('7/18/2024')
    time_ok = norm(time) == norm('3:30 PM')

    # Price can come from calculatedPrice or bookedTrip car
    calc_price = None
    cp = ride.get('calculatedPrice')
    if isinstance(cp, dict):
        calc_price = cp.get('finalPrice')

    booked_price = None
    if booked is not None and isinstance(booked.get('car'), dict):
        booked_price = booked.get('car', {}).get('finalPrice')

    def valid_price(v):
        return isinstance(v, (int, float)) and v > 0

    price_ok = valid_price(calc_price) or valid_price(booked_price)

    if pickup_ok and dest_ok and date_ok and time_ok and price_ok:
        print("SUCCESS")
    else:
        print("FAILURE")

except Exception:
    # On any error, be conservative and mark as failure
    print("FAILURE")
