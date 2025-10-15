import json, sys

def norm(s):
    if s is None:
        return ""
    return str(s).strip().lower()

# Matchers for pickup and dropoff
TARGET_PICKUP_ID = 742
TARGET_PICKUP_NAME = "1000 chestnut street apartments"
TARGET_PICKUP_ADDR_SNIPPET = "1000 chestnut st"

TARGET_DROPOFF_ID = 170
TARGET_DROPOFF_NAME = "rooftop 25"
TARGET_DROPOFF_ADDR_SNIPPET = "25 lusk st"


def is_target_location(loc: dict, target_id: int, target_name: str, addr_snippet: str) -> bool:
    if not isinstance(loc, dict):
        return False
    # ID match
    try:
        if int(loc.get("id", -1)) == target_id:
            return True
    except Exception:
        pass
    # Name match
    name = norm(loc.get("name", ""))
    if name == target_name:
        return True
    # Formatted address or address contains snippet
    formatted = norm(loc.get("formattedAddress", ""))
    address = norm(loc.get("address", ""))
    if addr_snippet in formatted or addr_snippet in address:
        return True
    return False


def match_pickup(loc):
    return is_target_location(loc, TARGET_PICKUP_ID, TARGET_PICKUP_NAME, TARGET_PICKUP_ADDR_SNIPPET)


def match_dropoff(loc):
    return is_target_location(loc, TARGET_DROPOFF_ID, TARGET_DROPOFF_NAME, TARGET_DROPOFF_ADDR_SNIPPET)


def get_nested(d, path, default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def floats_close(a, b, tol=0.05):
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Navigate to added.ride and added.user
    added = get_nested(data, ["initialfinaldiff", "added"], {}) or {}
    ride = added.get("ride", {}) or {}
    user = added.get("user", {}) or {}

    # 1) Verify rides shown: ride.trip pickup/destination must match targets
    trip = ride.get("trip", {}) or {}
    shown_pickup_ok = match_pickup(trip.get("pickup", {}))
    shown_dropoff_ok = match_dropoff(trip.get("destination", {}))
    rides_shown = shown_pickup_ok and shown_dropoff_ok

    # Fallback: if trip missing, try ride.pickupLocation / dropoffLocation (though successes use trip)
    if not rides_shown:
        shown_pickup_ok2 = match_pickup(ride.get("pickupLocation", {}))
        shown_dropoff_ok2 = match_dropoff(ride.get("dropoffLocation", {}))
        rides_shown = shown_pickup_ok2 and shown_dropoff_ok2

    # 2) Verify booking: need a completed trip in ride.trips with correct route
    trips_list = ride.get("trips", []) or []
    matching_completed_trips = []
    for t in trips_list:
        if not isinstance(t, dict):
            continue
        status = norm(t.get("status", ""))
        if status != "completed":
            continue
        if match_pickup(t.get("pickup", {})) and match_dropoff(t.get("destination", {})):
            # capture final price if available
            car = t.get("car", {}) or {}
            final_price = car.get("finalPrice")
            matching_completed_trips.append({"trip": t, "final_price": final_price})

    booked_by_trip_log = len(matching_completed_trips) > 0

    # 3) Cross-check wallet transaction for booking
    transactions = get_nested(user, ["wallet", "transactions"], []) or []
    matching_txn = None
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        desc = norm(tx.get("description", ""))
        amt = tx.get("amount")
        if "trip to rooftop 25" in desc and isinstance(amt, (int, float)) and amt < 0:
            matching_txn = tx
            break

    booked_by_txn = matching_txn is not None

    # 4) If both trip log and wallet transaction exist, ensure their amounts align (within tolerance)
    amounts_aligned = False
    if booked_by_trip_log and booked_by_txn:
        txn_amount_abs = abs(matching_txn.get("amount", 0))
        # Compare against any matching trip's final price
        for item in matching_completed_trips:
            fp = item.get("final_price")
            if fp is not None and floats_close(fp, txn_amount_abs):
                amounts_aligned = True
                break
        # If no final price present, still consider as aligned (some edge states may omit it)
        if not amounts_aligned and all(item.get("final_price") is None for item in matching_completed_trips):
            amounts_aligned = True

    # Final decision: rides shown + booked via both evidences and amounts aligned
    if rides_shown and booked_by_trip_log and booked_by_txn and amounts_aligned:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
