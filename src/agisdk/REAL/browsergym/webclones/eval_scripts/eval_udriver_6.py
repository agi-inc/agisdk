import json, sys

def get(d, *keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def to_str(x):
    return x if isinstance(x, str) else ""


def norm(s):
    return to_str(s).strip().lower()


def find_ride_data(data):
    # Try to locate the 'ride' object from common locations
    paths = [
        ("initialfinaldiff", "added", "ride"),
        ("initialfinaldiff", "updated", "ride"),
        ("added", "ride"),
        ("ride",),
    ]
    for p in paths:
        val = get(data, *p)
        if isinstance(val, dict):
            return val
    return {}


def is_pickup_22_irving(node):
    # Accept if name contains '22nd & Irving' or equals '22nd & Irving Market'
    name = norm(get(node, "name")) or norm(get(node, "pickup", "name"))
    fmt = norm(get(node, "formattedAddress")) or norm(get(node, "pickup", "formattedAddress"))
    street = norm(get(node, "addressComponents", "street")) or norm(get(node, "pickup", "addressComponents", "street"))
    # Primary name checks
    if name:
        if "22nd & irving" in name or name == "22nd & irving market":
            return True
    # Address-based checks (a bit robust but specific)
    if fmt:
        if "2101 irving st" in fmt and "san francisco" in fmt:
            return True
    if street:
        if "2101 irving" in street and "irving" in street:
            return True
    return False


def is_dest_7eleven(node):
    # Accept if name contains '7-eleven'
    name = norm(get(node, "name")) or norm(get(node, "destination", "name"))
    if name and "7-eleven" in name:
        return True
    return False


def trip_matches_criteria(trip):
    # Check a trip object has correct pickup and destination and is active/completed
    status = norm(get(trip, "status"))
    if status not in ("in progress", "completed"):
        return False
    pickup_ok = is_pickup_22_irving(get(trip, "pickup") or {})
    dest_ok = is_dest_7eleven(get(trip, "destination") or {})
    return pickup_ok and dest_ok


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    ride = find_ride_data(data) or {}

    # Immediate vs scheduled: must NOT be scheduled
    pickup_date = norm(get(ride, "pickupDate"))
    pickup_time = norm(get(ride, "pickupTime"))
    booked_trip = get(ride, "bookedTrip")
    if booked_trip is not None and booked_trip != None:
        # Any non-null bookedTrip means a scheduled ride
        print("FAILURE")
        return
    if pickup_date or pickup_time:
        print("FAILURE")
        return

    # Verify pickup and destination intent via ride-level OR trip-level
    # Use ride.* first, then trip.* as fallback
    pickup_node_candidates = []
    drop_node_candidates = []
    if isinstance(get(ride, "pickupLocation"), dict):
        pickup_node_candidates.append(get(ride, "pickupLocation"))
    if isinstance(get(ride, "dropoffLocation"), dict):
        drop_node_candidates.append(get(ride, "dropoffLocation"))
    if isinstance(get(ride, "trip"), dict):
        if isinstance(get(ride, "trip", "pickup"), dict):
            pickup_node_candidates.append(get(ride, "trip", "pickup"))
        if isinstance(get(ride, "trip", "destination"), dict):
            drop_node_candidates.append(get(ride, "trip", "destination"))

    pickup_ok = any(is_pickup_22_irving(node) for node in pickup_node_candidates if isinstance(node, dict))
    dest_ok = any(is_dest_7eleven(node) for node in drop_node_candidates if isinstance(node, dict))

    if not (pickup_ok and dest_ok):
        print("FAILURE")
        return

    # Ensure the ride is actually booked/initiated: check trips array contains matching entry
    trips = get(ride, "trips")
    booked_now = False
    if isinstance(trips, list):
        for t in trips:
            if isinstance(t, dict) and trip_matches_criteria(t):
                booked_now = True
                break

    if not booked_now:
        # As a fallback, if ride.trip itself matches criteria, consider it booked only if trips is missing or not a list
        trip_obj = get(ride, "trip") or {}
        if isinstance(trip_obj, dict) and trip_matches_criteria(trip_obj) and not isinstance(trips, list):
            booked_now = True

    if booked_now:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
