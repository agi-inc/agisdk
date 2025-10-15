import json
import sys

# Verification script for task:
# "Get me a udriverXL from AVA Nob Hill to Alamo Rent a Car right now."
#
# Strategy:
# 1) Confirm the selected/booked car type is UdriverXL and the route is AVA Nob Hill -> Alamo Rent A Car
#    using ride.trip fields (fallback to ride.pickupLocation/dropoffLocation if needed, though trip is primary).
# 2) Ensure booking actually happened "right now": find a matching trip in ride.trips with status in progress or completed.
#    This prevents false positives where user selected options but did not book.

EXPECTED_PICKUP_NAME = "ava nob hill"
EXPECTED_PICKUP_ID = 724
EXPECTED_DROPOFF_NAME = "alamo rent a car"
EXPECTED_DROPOFF_ID = 609
EXPECTED_CAR = "udriverxl"
VALID_STATUSES = {"in progress", "completed"}


def deep_find_first(obj, key):
    """Recursively find the first occurrence of key in a nested dict/list structure."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for k, v in obj.items():
            found = deep_find_first(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = deep_find_first(item, key)
            if found is not None:
                return found
    return None


def get_ride(data):
    # Try typical path initialfinaldiff.added.ride, else search deeply
    ride = None
    try:
        ride = data.get("initialfinaldiff", {}).get("added", {}).get("ride")
    except Exception:
        ride = None
    if ride is None:
        try:
            ride = data.get("initialfinaldiff", {}).get("updated", {}).get("ride")
        except Exception:
            ride = None
    if ride is None:
        ride = deep_find_first(data, "ride")
    return ride if isinstance(ride, dict) else None


def norm(s):
    return str(s).strip().lower() if s is not None else ""


def id_matches(val, expected_id):
    try:
        return int(val) == int(expected_id)
    except Exception:
        return str(val) == str(expected_id)


def location_matches(loc, expected_name, expected_id):
    if not isinstance(loc, dict):
        return False
    # Prefer ID match for robustness
    if "id" in loc and id_matches(loc.get("id"), expected_id):
        return True
    name = norm(loc.get("name", ""))
    if expected_name in name:
        return True
    # Fallback to formattedAddress/address if name is missing
    for k in ("formattedAddress", "address"):
        val = norm(loc.get(k, ""))
        if expected_name in val:
            return True
    return False


def trip_matches(trip):
    if not isinstance(trip, dict):
        return False
    car = trip.get("car", {}) or {}
    car_type = norm(car.get("type"))
    if car_type != EXPECTED_CAR:
        return False
    pickup_ok = location_matches(trip.get("pickup", {}), EXPECTED_PICKUP_NAME, EXPECTED_PICKUP_ID)
    dropoff_ok = location_matches(trip.get("destination", {}), EXPECTED_DROPOFF_NAME, EXPECTED_DROPOFF_ID)
    if not (pickup_ok and dropoff_ok):
        return False
    return True


def was_booked_now(trips_list):
    # A booking exists if a matching trip entry is present with status in progress or completed
    if not isinstance(trips_list, list):
        return False
    for t in trips_list:
        if not isinstance(t, dict):
            continue
        if not trip_matches(t):
            continue
        status = norm(t.get("status", ""))
        if status in VALID_STATUSES:
            return True
    return False


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    ride = get_ride(data)
    if not ride:
        print("FAILURE")
        return

    trip = ride.get("trip", {}) or {}

    # Verify selected/booked car and route in ride.trip
    if not trip_matches(trip):
        print("FAILURE")
        return

    # Verify booking took place right now by ensuring a corresponding active/completed trip exists
    trips_list = ride.get("trips", [])
    if not was_booked_now(trips_list):
        print("FAILURE")
        return

    print("SUCCESS")

if __name__ == "__main__":
    main()
