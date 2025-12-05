import json
import sys


def norm(s):
    if not isinstance(s, str):
        return ""
    return s.strip().lower()


# Strategy in code:
# - Load final_state_diff.json and merge 'added' and 'updated' sections.
# - Verify an actually booked trip exists in ride.trips with:
#   * pickup includes "golden gate" and "apart" (Golden Gate Apartments)
#   * destination includes both "chase" and "bank" (any Chase Bank)
#   * car.type == "UdriverX" (correct ride type)
# This distinguishes successes from failures such as wrong pickup, not booked, or wrong car type.


def get_nested(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


try:
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)

    base = data.get("initialfinaldiff", {})
    added = base.get("added", {}) or {}
    updated = base.get("updated", {}) or {}

    # Merge added over updated (prefer added values where present)
    state = {}
    for key in set(list(updated.keys()) + list(added.keys())):
        v = added.get(key, None)
        if v is None:
            v = updated.get(key)
        state[key] = v

    ride = state.get("ride", {}) or {}

    trips = ride.get("trips", []) or []
    success_found = False

    for trip in trips:
        # Extract fields safely
        pickup_name = norm(get_nested(trip, "pickup", "name"))
        dest_name = norm(get_nested(trip, "destination", "name"))
        car_type = get_nested(trip, "car", "type")
        car_type = car_type if isinstance(car_type, str) else ""

        # Conditions
        pickup_ok = ("golden gate" in pickup_name) and ("apart" in pickup_name)
        dest_ok = ("chase" in dest_name) and ("bank" in dest_name)
        car_ok = car_type == "UdriverX"

        if pickup_ok and dest_ok and car_ok:
            success_found = True
            break

    # As a fallback, if trips did not contain it, also inspect the current ride.trip
    if not success_found:
        cur_trip = ride.get("trip", {}) or {}
        pickup_name = norm(get_nested(cur_trip, "pickup", "name"))
        dest_name = norm(get_nested(cur_trip, "destination", "name"))
        car_type = get_nested(cur_trip, "car", "type")
        car_type = car_type if isinstance(car_type, str) else ""
        pickup_ok = ("golden gate" in pickup_name) and ("apart" in pickup_name)
        dest_ok = ("chase" in dest_name) and ("bank" in dest_name)
        car_ok = car_type == "UdriverX"
        # Consider it success only if all three hold on current trip too, indicating correct imminent booking
        if pickup_ok and dest_ok and car_ok:
            # To ensure it's actually booked (not just shown), look for a wallet transaction as secondary evidence
            user = state.get("user", {}) or {}
            wallet = user.get("wallet", {}) or {}
            txs = wallet.get("transactions", []) or []
            has_tx = False
            for tx in txs:
                desc = norm(tx.get("description"))
                amt = tx.get("amount")
                if (
                    isinstance(desc, str)
                    and ("trip to chase bank" in desc)
                    and isinstance(amt, (int, float))
                    and amt < 0
                ):
                    has_tx = True
                    break
            if has_tx:
                success_found = True

    print("SUCCESS" if success_found else "FAILURE")
except Exception:
    # On any error, be safe and mark as failure
    print("FAILURE")
