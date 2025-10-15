import json, sys

def get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur

TARGET_PICKUP = "1001 Castro Street"
TARGET_DROPOFF = "1030 Post Street Apartments"

def norm(s):
    if s is None:
        return ""
    return str(s).strip().lower()


def loc_matches(pickup_obj, drop_obj):
    p_name = norm(get(pickup_obj, 'name'))
    d_name = norm(get(drop_obj, 'name'))
    return (TARGET_PICKUP.lower() in p_name) and (TARGET_DROPOFF.lower() in d_name)


def any_correct_route(data):
    ride = get(data, 'initialfinaldiff', 'added', 'ride') or {}

    # Check ride.trip
    trip = get(ride, 'trip') or {}
    if loc_matches(get(trip, 'pickup') or {}, get(trip, 'destination') or {}):
        return True

    # Check top-level pickup/dropoffLocation
    if loc_matches(get(ride, 'pickupLocation') or {}, get(ride, 'dropoffLocation') or {}):
        return True

    # Check in rides "trips" entries
    trips = get(ride, 'trips') or []
    for t in trips:
        if loc_matches(get(t, 'pickup') or {}, get(t, 'destination') or {}):
            return True

    return False


def trip_completed_or_booked(data):
    ride = get(data, 'initialfinaldiff', 'added', 'ride') or {}
    # 1) Check wallet transactions mentioning Trip to 1030 Post Street Apartments
    transactions = get(data, 'initialfinaldiff', 'added', 'user', 'wallet', 'transactions') or []
    for tr in transactions:
        desc = norm(tr.get('description'))
        if 'trip to' in desc and TARGET_DROPOFF.lower() in desc:
            return True

    # 2) Check any trips entry with matching route and status completed
    trips = get(ride, 'trips') or []
    for t in trips:
        if loc_matches(get(t, 'pickup') or {}, get(t, 'destination') or {}):
            status = norm(get(t, 'status'))
            if status == 'completed':
                return True

    return False


def get_final_price(data):
    ride = get(data, 'initialfinaldiff', 'added', 'ride') or {}
    # Prefer the explicit trip car price
    price = get(ride, 'trip', 'car', 'finalPrice')
    if isinstance(price, (int, float)):
        return price
    # Then calculatedPrice
    price = get(ride, 'calculatedPrice', 'finalPrice')
    if isinstance(price, (int, float)):
        return price
    # Then scan matching trip in trips array
    trips = get(ride, 'trips') or []
    for t in trips:
        if loc_matches(get(t, 'pickup') or {}, get(t, 'destination') or {}):
            p = get(t, 'car', 'finalPrice')
            if isinstance(p, (int, float)):
                return p
    return None


def wallet_balance(data):
    bal = get(data, 'initialfinaldiff', 'added', 'user', 'wallet', 'balance')
    return bal if isinstance(bal, (int, float)) else None


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Strategy:
    # 1) Ensure correct route direction (Castro -> Post Apts) exists anywhere (trip/top-level/trips entry)
    # 2) Consider success if either a) there's evidence of booking (wallet transaction or completed trip)
    #    or b) addresses match and user has enough wallet balance to cover the quoted fare.

    if not any_correct_route(data):
        print("FAILURE")
        return

    if trip_completed_or_booked(data):
        print("SUCCESS")
        return

    # Fallback: if the route is correct and the wallet can cover the price, assume reservation could be made
    price = get_final_price(data)
    bal = wallet_balance(data)

    if isinstance(price, (int, float)) and isinstance(bal, (int, float)):
        if bal + 1e-9 >= price:  # include tiny epsilon for float rounding
            print("SUCCESS")
            return

    print("FAILURE")

if __name__ == '__main__':
    main()
